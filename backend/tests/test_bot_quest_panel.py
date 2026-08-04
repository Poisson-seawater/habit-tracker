import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram.error import BadRequest

from src.bot.listener import _quest_callback_data, handle_callback, route_command
from src.bot.parser import parse_command
from src.database.models import Habit, HabitLog, User
from src.database.session import Base


@pytest.fixture
def db_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    try:
        session.add(
            User(id=1, username="Gabriel", chat_id="111", xp=0, level=1, gold=0)
        )
        session.add(User(id=2, username="Jeanne", chat_id="222", xp=0, level=1, gold=0))
        session.add(
            Habit(id=1, user_id=1, name="Routine Matin", type="binary", is_active=True)
        )
        session.add(
            Habit(
                id=2,
                user_id=1,
                name="Lecture",
                type="quantitative",
                unit="min",
                is_active=True,
            )
        )
        session.add(
            Habit(
                id=3,
                user_id=1,
                name="Pompes",
                type="binary",
                daily_target=3,
                is_active=True,
            )
        )
        # Archived and inactive quests must stay out of the panel.
        session.add(
            Habit(
                id=4,
                user_id=1,
                name="Ancienne quête",
                type="binary",
                is_active=True,
                archived_at=datetime.datetime.now(),
            )
        )
        session.add(
            Habit(id=5, user_id=1, name="Snooze", type="binary", is_active=False)
        )
        session.commit()

        monkeypatch.setattr("src.bot.listener.SessionLocal", lambda: session)
        monkeypatch.setattr("src.bot.listener.TELEGRAM_GROUP_ID", "")
        yield session
    finally:
        session.close()


def _command_update(text):
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = text
    update.effective_chat.id = 111
    update.message.from_user = MagicMock(username="Gabriel", id=111)
    update.message.reply_text = AsyncMock()
    return update


def _callback_update(data):
    update = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.data = data
    query.from_user = MagicMock(username="Gabriel", id=111)
    query.edit_message_text = AsyncMock()
    query.message = MagicMock()
    query.message.chat_id = 111
    query.message.message_id = 42
    query.message.reply_text = AsyncMock()
    update.callback_query = query
    return update


def _context(user_data=None):
    context = MagicMock()
    context.user_data = user_data or {}
    context.bot = MagicMock()
    context.bot.edit_message_text = AsyncMock()
    return context


def _labels(markup):
    return [button.text for row in markup.inline_keyboard for button in row]


@pytest.mark.parametrize(
    "text",
    [
        "/quetes",
        "/habitudes",
        "/habits",
        "/quests",
        "/quêtes",
        "/quetes@habit_bot",
    ],
)
def test_parse_quest_panel_aliases(text):
    assert parse_command(text) == {"command": "quetes"}


@pytest.mark.asyncio
async def test_quetes_lists_one_button_per_active_habit(db_session):
    update = _command_update("/quetes")

    await route_command(update, MagicMock(user_data={}))

    args, kwargs = update.message.reply_text.call_args
    assert "Quêtes du jour" in args[0]
    assert "0/3 validées" in args[0]

    keyboard = kwargs["reply_markup"].inline_keyboard
    assert [row[0].callback_data for row in keyboard] == [
        "quest:do:1:1:0",
        "quest:do:1:2:0",
        "quest:do:1:3:0",
        "quest:refresh:1:0",
    ]
    assert _labels(kwargs["reply_markup"])[:3] == [
        "⬜ Routine Matin",
        "⬜ Lecture (à logger)",
        "⬜ Pompes (0/3)",
    ]


@pytest.mark.asyncio
async def test_tapping_binary_quest_logs_it_and_refreshes_panel(db_session):
    update = _callback_update("quest:do:1:1:0")

    await handle_callback(update, MagicMock(user_data={}))

    log = db_session.query(HabitLog).filter_by(habit_id=1).one()
    assert log.log_type == "done"
    assert log.timestamp.date() == datetime.date.today()

    args, kwargs = update.callback_query.edit_message_text.call_args
    assert "Quête validée : <b>Routine Matin</b>" in args[0]
    assert "1/3 validées" in args[0]
    assert "✅ Routine Matin" in _labels(kwargs["reply_markup"])
    assert kwargs["reply_markup"].inline_keyboard[0][0].callback_data == (
        "quest:noop:1:0"
    )


@pytest.mark.asyncio
async def test_tapping_a_quest_twice_reports_it_as_already_done(db_session):
    await handle_callback(_callback_update("quest:do:1:1:0"), MagicMock(user_data={}))
    second = _callback_update("quest:do:1:1:0")

    await handle_callback(second, MagicMock(user_data={}))

    assert db_session.query(HabitLog).filter_by(habit_id=1).count() == 1
    assert "déjà traitée" in second.callback_query.answer.call_args.args[0]
    assert "✅ Routine Matin" in _labels(
        second.callback_query.edit_message_text.call_args.kwargs["reply_markup"]
    )


@pytest.mark.asyncio
async def test_quest_with_daily_target_shows_progress(db_session):
    for _ in range(3):
        await handle_callback(
            _callback_update("quest:do:1:3:0"), MagicMock(user_data={})
        )

    stale = _callback_update("quest:do:1:3:0")
    await handle_callback(stale, MagicMock(user_data={}))

    assert db_session.query(HabitLog).filter_by(habit_id=3).count() == 3
    markup = stale.callback_query.edit_message_text.call_args.kwargs["reply_markup"]
    assert "✅ Pompes (3/3)" in _labels(markup)
    assert markup.inline_keyboard[2][0].callback_data == "quest:noop:1:0"


@pytest.mark.asyncio
async def test_tapping_quantitative_quest_asks_for_a_value_then_resends_panel(
    db_session,
):
    context = _context()
    tap = _callback_update("quest:do:1:2:0")

    await handle_callback(tap, context)

    assert context.user_data["pending_log_habit_id"] == 2
    assert context.user_data["pending_log_panel"] == {
        "owner_id": 1,
        "chat_id": 111,
        "message_id": 42,
        "page": 0,
    }
    assert "Envoie la valeur" in tap.callback_query.message.reply_text.call_args.args[0]

    typed = _command_update("30 min")
    await route_command(typed, context)

    log = db_session.query(HabitLog).filter_by(habit_id=2).one()
    assert (log.log_type, log.amount, log.unit) == ("log", 30, "min")
    assert "pending_log_panel" not in context.user_data

    edit_kwargs = context.bot.edit_message_text.call_args.kwargs
    assert edit_kwargs["chat_id"] == 111
    assert edit_kwargs["message_id"] == 42
    assert "Quêtes du jour" in edit_kwargs["text"]
    assert "✅ Lecture (30min)" in _labels(edit_kwargs["reply_markup"])


@pytest.mark.asyncio
async def test_invalid_quantitative_value_keeps_panel_flow_pending(db_session):
    context = _context()
    tap = _callback_update("quest:do:1:2:0")
    await handle_callback(tap, context)

    typed = _command_update("beaucoup")
    await route_command(typed, context)

    assert db_session.query(HabitLog).filter_by(habit_id=2).count() == 0
    assert context.user_data["pending_log_habit_id"] == 2
    assert context.user_data["pending_log_panel"]["message_id"] == 42
    context.bot.edit_message_text.assert_not_called()
    assert "Format invalide" in typed.message.reply_text.call_args.args[0]


@pytest.mark.asyncio
async def test_quantitative_panel_falls_back_to_new_message_if_edit_fails(db_session):
    context = _context()
    context.bot.edit_message_text.side_effect = BadRequest("message can't be edited")
    await handle_callback(_callback_update("quest:do:1:2:0"), context)

    typed = _command_update("30 min")
    await route_command(typed, context)

    panel_text, panel_kwargs = typed.message.reply_text.call_args
    assert "Quêtes du jour" in panel_text[0]
    assert "✅ Lecture (30min)" in _labels(panel_kwargs["reply_markup"])


@pytest.mark.asyncio
async def test_partially_logged_quantitative_quest_shows_its_total(db_session):
    db_session.query(Habit).filter_by(id=2).one().daily_target = 2
    db_session.add(
        HabitLog(
            user_id=1,
            habit_id=2,
            log_type="log",
            amount=30,
            unit="min",
            timestamp=datetime.datetime.now(),
        )
    )
    db_session.commit()
    update = _command_update("/quetes")

    await route_command(update, MagicMock(user_data={}))

    labels = _labels(update.message.reply_text.call_args.kwargs["reply_markup"])
    assert "📊 Lecture (30min)" in labels


@pytest.mark.asyncio
async def test_failed_and_skipped_quests_keep_their_state_in_the_panel(db_session):
    db_session.add(
        HabitLog(
            user_id=1,
            habit_id=1,
            log_type="failed",
            timestamp=datetime.datetime.now(),
            xp_penalty=5,
        )
    )
    db_session.add(
        HabitLog(
            user_id=1,
            habit_id=3,
            log_type="skip",
            reason="fatigue",
            timestamp=datetime.datetime.now(),
        )
    )
    db_session.commit()
    update = _command_update("/quetes")

    await route_command(update, MagicMock(user_data={}))

    markup = update.message.reply_text.call_args.kwargs["reply_markup"]
    labels = _labels(markup)
    assert "❌ Routine Matin (ratée)" in labels
    assert "⏭️ Pompes (skippée)" in labels
    assert markup.inline_keyboard[0][0].callback_data == "quest:noop:1:0"
    assert markup.inline_keyboard[2][0].callback_data == "quest:noop:1:0"


@pytest.mark.asyncio
async def test_failed_quest_cannot_be_validated_from_the_panel(db_session):
    db_session.add(
        HabitLog(
            user_id=1,
            habit_id=1,
            log_type="failed",
            timestamp=datetime.datetime.now(),
            xp_penalty=5,
        )
    )
    db_session.commit()
    update = _callback_update("quest:do:1:1:0")

    await handle_callback(update, MagicMock(user_data={}))

    done_logs = db_session.query(HabitLog).filter_by(habit_id=1, log_type="done")
    assert done_logs.count() == 0
    assert "déjà traitée" in update.callback_query.answer.call_args.args[0]


@pytest.mark.asyncio
async def test_private_quest_name_is_masked_in_the_panel(db_session):
    db_session.query(Habit).filter_by(id=1).one().is_private = True
    db_session.commit()
    update = _command_update("/quetes")

    await route_command(update, MagicMock(user_data={}))

    labels = _labels(update.message.reply_text.call_args.kwargs["reply_markup"])
    assert "⬜ Chose secrète 🔒" in labels
    assert not any("Routine Matin" in label for label in labels)


@pytest.mark.asyncio
async def test_refresh_button_rerenders_the_panel(db_session):
    update = _callback_update("quest:refresh:1:0")

    await handle_callback(update, MagicMock(user_data={}))

    args, kwargs = update.callback_query.edit_message_text.call_args
    assert "Mis à jour à" in args[0]
    assert [row[0].callback_data for row in kwargs["reply_markup"].inline_keyboard] == [
        "quest:do:1:1:0",
        "quest:do:1:2:0",
        "quest:do:1:3:0",
        "quest:refresh:1:0",
    ]


@pytest.mark.asyncio
async def test_empty_panel_has_only_refresh(db_session):
    db_session.query(Habit).filter(Habit.id.in_([1, 2, 3])).update(
        {Habit.is_active: False}, synchronize_session=False
    )
    db_session.commit()
    update = _command_update("/quetes")

    await route_command(update, MagicMock(user_data={}))

    text, markup = update.message.reply_text.call_args.args[0], (
        update.message.reply_text.call_args.kwargs["reply_markup"]
    )
    assert "Aucune quête prévue aujourd'hui" in text
    assert _labels(markup) == ["🔄 Rafraîchir"]
    assert markup.inline_keyboard[0][0].callback_data == "quest:refresh:1:0"


@pytest.mark.asyncio
async def test_off_schedule_quest_is_hidden_until_touched(db_session):
    habit = db_session.query(Habit).filter_by(id=1).one()
    habit.day_types = ["rest"]
    db_session.commit()

    first = _command_update("/quetes")
    await route_command(first, MagicMock(user_data={}))
    assert not any(
        "Routine Matin" in label
        for label in _labels(first.message.reply_text.call_args.kwargs["reply_markup"])
    )

    db_session.add(
        HabitLog(
            user_id=1,
            habit_id=1,
            log_type="done",
            timestamp=datetime.datetime.now(),
        )
    )
    db_session.commit()
    second = _command_update("/quetes")
    await route_command(second, MagicMock(user_data={}))
    assert "✅ Routine Matin" in _labels(
        second.message.reply_text.call_args.kwargs["reply_markup"]
    )


@pytest.mark.asyncio
async def test_panel_paginates_after_twenty_quests(db_session):
    for habit_id in range(6, 24):
        db_session.add(
            Habit(
                id=habit_id,
                user_id=1,
                name=f"Quête {habit_id}",
                type="binary",
                is_active=True,
            )
        )
    db_session.commit()

    first = _command_update("/quetes")
    await route_command(first, MagicMock(user_data={}))
    first_markup = first.message.reply_text.call_args.kwargs["reply_markup"]
    assert "Page 1/2" in _labels(first_markup)
    assert "⬜ Quête 22" in _labels(first_markup)
    assert "⬜ Quête 23" not in _labels(first_markup)

    second = _callback_update("quest:page:1:1")
    await handle_callback(second, MagicMock(user_data={}))
    second_markup = second.callback_query.edit_message_text.call_args.kwargs[
        "reply_markup"
    ]
    assert "⬜ Quête 23" in _labels(second_markup)
    assert "quest:refresh:1:1" == second_markup.inline_keyboard[-1][0].callback_data


@pytest.mark.asyncio
async def test_other_user_cannot_operate_or_replace_panel(db_session):
    update = _callback_update("quest:do:1:1:0")
    update.callback_query.from_user = MagicMock(username="Jeanne", id=222)

    await handle_callback(update, MagicMock(user_data={}))

    assert db_session.query(HabitLog).count() == 0
    update.callback_query.edit_message_text.assert_not_called()
    assert update.callback_query.answer.call_args.kwargs["show_alert"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("data", ["quest:do:1", "quest:refresh", "quest:broken"])
async def test_legacy_or_malformed_callbacks_expire_without_mutation(db_session, data):
    update = _callback_update(data)

    await handle_callback(update, MagicMock(user_data={}))

    assert db_session.query(HabitLog).count() == 0
    update.callback_query.edit_message_text.assert_not_called()
    assert "Relance /quetes" in update.callback_query.answer.call_args.args[0]


def test_quest_callback_payloads_fit_telegram_limit():
    maximum_id = 2**63 - 1
    payloads = [
        _quest_callback_data("do", maximum_id, maximum_id, 9_999_999_999),
        _quest_callback_data("noop", maximum_id, 9_999_999_999),
        _quest_callback_data("page", maximum_id, 9_999_999_999),
        _quest_callback_data("refresh", maximum_id, 9_999_999_999),
    ]
    assert all(len(payload.encode("utf-8")) <= 64 for payload in payloads)
