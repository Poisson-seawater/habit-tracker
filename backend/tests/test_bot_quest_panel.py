import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.bot.listener import handle_callback, route_command
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
    query.message.reply_text = AsyncMock()
    update.callback_query = query
    return update


def _labels(markup):
    return [button.text for row in markup.inline_keyboard for button in row]


@pytest.mark.parametrize("text", ["/quetes", "/habitudes", "/habits", "/quests"])
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
        "quest:do:1",
        "quest:do:2",
        "quest:do:3",
        "quest:refresh",
    ]
    assert _labels(kwargs["reply_markup"])[:3] == [
        "⬜ Routine Matin",
        "⬜ Lecture (à logger)",
        "⬜ Pompes (0/3)",
    ]


@pytest.mark.asyncio
async def test_tapping_binary_quest_logs_it_and_refreshes_panel(db_session):
    update = _callback_update("quest:do:1")

    await handle_callback(update, MagicMock(user_data={}))

    log = db_session.query(HabitLog).filter_by(habit_id=1).one()
    assert log.log_type == "done"
    assert log.timestamp.date() == datetime.date.today()

    args, kwargs = update.callback_query.edit_message_text.call_args
    assert "Quête validée : <b>Routine Matin</b>" in args[0]
    assert "1/3 validées" in args[0]
    assert "✅ Routine Matin" in _labels(kwargs["reply_markup"])


@pytest.mark.asyncio
async def test_tapping_a_quest_twice_reports_it_as_already_done(db_session):
    await handle_callback(_callback_update("quest:do:1"), MagicMock(user_data={}))
    second = _callback_update("quest:do:1")

    await handle_callback(second, MagicMock(user_data={}))

    assert db_session.query(HabitLog).filter_by(habit_id=1).count() == 1
    args, _ = second.callback_query.edit_message_text.call_args
    assert "était déjà validée" in args[0]


@pytest.mark.asyncio
async def test_quest_with_daily_target_shows_progress(db_session):
    await handle_callback(_callback_update("quest:do:3"), MagicMock(user_data={}))
    second = _callback_update("quest:do:3")

    await handle_callback(second, MagicMock(user_data={}))

    assert db_session.query(HabitLog).filter_by(habit_id=3).count() == 2
    markup = second.callback_query.edit_message_text.call_args.kwargs["reply_markup"]
    assert "⬜ Pompes (2/3)" in _labels(markup)


@pytest.mark.asyncio
async def test_tapping_quantitative_quest_asks_for_a_value_then_resends_panel(
    db_session,
):
    context = MagicMock(user_data={})
    tap = _callback_update("quest:do:2")

    await handle_callback(tap, context)

    assert context.user_data["pending_log_habit_id"] == 2
    assert context.user_data["pending_log_from_panel"] is True
    assert "Envoie la valeur" in tap.callback_query.message.reply_text.call_args.args[0]

    typed = _command_update("30 min")
    await route_command(typed, context)

    log = db_session.query(HabitLog).filter_by(habit_id=2).one()
    assert (log.log_type, log.amount, log.unit) == ("log", 30, "min")
    assert "pending_log_from_panel" not in context.user_data

    panel_args, panel_kwargs = typed.message.reply_text.call_args
    assert "Quêtes du jour" in panel_args[0]
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

    labels = _labels(update.message.reply_text.call_args.kwargs["reply_markup"])
    assert "❌ Routine Matin (ratée)" in labels
    assert "⏭️ Pompes (skippée)" in labels


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
    update = _callback_update("quest:do:1")

    await handle_callback(update, MagicMock(user_data={}))

    done_logs = db_session.query(HabitLog).filter_by(habit_id=1, log_type="done")
    assert done_logs.count() == 0
    assert "⚠️" in update.callback_query.edit_message_text.call_args.args[0]


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
    update = _callback_update("quest:refresh")

    await handle_callback(update, MagicMock(user_data={}))

    args, kwargs = update.callback_query.edit_message_text.call_args
    assert "Mis à jour à" in args[0]
    assert [row[0].callback_data for row in kwargs["reply_markup"].inline_keyboard] == [
        "quest:do:1",
        "quest:do:2",
        "quest:do:3",
        "quest:refresh",
    ]
