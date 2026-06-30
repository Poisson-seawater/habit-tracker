import pytest
import datetime
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base
from src.database.models import User, Habit, HabitLog, Todo
from src.bot.listener import route_command, handle_callback
from src.bot.parser import parse_command


@pytest.fixture
def db_session(monkeypatch):
    # Use an in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Seed Gabriel (User ID 1)
        gabriel = User(
            id=1, username="Gabriel", chat_id="111", xp=100, level=2, gold=40
        )
        session.add(gabriel)

        # Seed Habits
        # 1. Active binary habit
        h1 = Habit(
            id=1,
            user_id=1,
            name="Routine Matin",
            type="binary",
            is_active=True,
        )
        session.add(h1)

        # 2. Active quantitative habit
        h2 = Habit(
            id=2,
            user_id=1,
            name="Lecture",
            type="quantitative",
            unit="min",
            is_active=True,
        )
        session.add(h2)

        # 3. Inactive habit (should not show up)
        h3 = Habit(
            id=3,
            user_id=1,
            name="Snooze",
            type="binary",
            is_active=False,
        )
        session.add(h3)

        # Seed Todos
        # 1. Incomplete Todo
        t1 = Todo(
            id=10,
            user_id=1,
            title="Faire la vaisselle",
            is_completed=False,
            xp_reward=15,
        )
        session.add(t1)

        # 2. Completed Todo (should not show up)
        t2 = Todo(
            id=11, user_id=1, title="Acheter du pain", is_completed=True, xp_reward=10
        )
        session.add(t2)

        session.commit()

        # Monkeypatch DB session and configs in listener.py
        monkeypatch.setattr("src.bot.listener.SessionLocal", lambda: session)
        monkeypatch.setattr("src.bot.listener.TELEGRAM_GROUP_ID", "")

        yield session
    finally:
        session.close()


def test_parse_log_no_arguments():
    # Verify parser support for empty arguments
    result = parse_command("/log")
    assert result["command"] == "log"
    assert result["habit_name"] is None
    assert result["value"] is None
    assert result["unit"] is None


@pytest.mark.asyncio
async def test_log_command_without_args_shows_choices(db_session):
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = "/log"
    update.effective_chat.id = 111

    from_user = MagicMock()
    from_user.username = "Gabriel"
    from_user.id = 111
    update.message.from_user = from_user

    reply_mock = AsyncMock()
    update.message.reply_text = reply_mock
    context = MagicMock()

    await route_command(update, context)

    reply_mock.assert_called_once()
    args, kwargs = reply_mock.call_args
    assert "Qu'est-ce que tu veux logger ?" in args[0]

    reply_markup = kwargs["reply_markup"]
    buttons = reply_markup.inline_keyboard
    assert len(buttons) == 1
    assert buttons[0][0].text == "🎯 Habitude"
    assert buttons[0][0].callback_data == "log_select:habit"
    assert buttons[0][1].text == "📝 Todo"
    assert buttons[0][1].callback_data == "log_select:todo"


@pytest.mark.asyncio
async def test_callback_log_select_habit(db_session):
    update = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.data = "log_select:habit"
    from_user = MagicMock()
    from_user.username = "Gabriel"
    from_user.id = 111
    query.from_user = from_user
    update.callback_query = query
    context = MagicMock()

    edit_mock = AsyncMock()
    query.edit_message_text = edit_mock

    await handle_callback(update, context)

    edit_mock.assert_called_once()
    args, kwargs = edit_mock.call_args
    assert "Choisis une habitude à logger" in args[0]

    reply_markup = kwargs["reply_markup"]
    buttons = reply_markup.inline_keyboard
    # Should list active habits: Routine Matin (binary) and Lecture (quant)
    assert len(buttons) == 2
    assert "Routine Matin" in buttons[0][0].text
    assert buttons[0][0].callback_data == "log_habit:1"
    assert "Lecture" in buttons[1][0].text
    assert buttons[1][0].callback_data == "log_habit:2"


@pytest.mark.asyncio
async def test_callback_log_select_todo(db_session):
    update = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.data = "log_select:todo"
    from_user = MagicMock()
    from_user.username = "Gabriel"
    from_user.id = 111
    query.from_user = from_user
    update.callback_query = query
    context = MagicMock()

    edit_mock = AsyncMock()
    query.edit_message_text = edit_mock

    await handle_callback(update, context)

    edit_mock.assert_called_once()
    args, kwargs = edit_mock.call_args
    assert "Choisis un Todo à compléter" in args[0]

    reply_markup = kwargs["reply_markup"]
    buttons = reply_markup.inline_keyboard
    # Should list incomplete todo: Faire la vaisselle
    assert len(buttons) == 1
    assert "Faire la vaisselle" in buttons[0][0].text
    assert buttons[0][0].callback_data == "log_todo:10"


@pytest.mark.asyncio
async def test_callback_log_habit_binary_done_immediately(db_session):
    update = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.data = "log_habit:1"  # Routine Matin (binary)
    from_user = MagicMock()
    from_user.username = "Gabriel"
    from_user.id = 111
    query.from_user = from_user
    update.callback_query = query
    context = MagicMock()

    edit_mock = AsyncMock()
    query.edit_message_text = edit_mock

    await handle_callback(update, context)

    edit_mock.assert_called_once()
    args, _ = edit_mock.call_args
    assert 'a complété la routine "Routine Matin"' in args[0]

    # Verify log entry in DB
    logs = db_session.query(HabitLog).filter_by(habit_id=1).all()
    assert len(logs) == 1
    assert logs[0].log_type == "done"


@pytest.mark.asyncio
async def test_callback_log_habit_quant_prompts_value(db_session):
    update = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.data = "log_habit:2"  # Lecture (quantitative)
    from_user = MagicMock()
    from_user.username = "Gabriel"
    from_user.id = 111
    query.from_user = from_user
    update.callback_query = query
    context = MagicMock()
    context.user_data = {}

    edit_mock = AsyncMock()
    query.edit_message_text = edit_mock

    await handle_callback(update, context)

    edit_mock.assert_called_once()
    args, _ = edit_mock.call_args
    assert "Envoie la valeur pour l'habitude" in args[0]
    assert "Lecture" in args[0]
    assert context.user_data["pending_log_habit_id"] == 2


@pytest.mark.asyncio
async def test_route_command_receives_typed_value_for_quant(db_session):
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = "45 min"
    update.effective_chat.id = 111

    from_user = MagicMock()
    from_user.username = "Gabriel"
    from_user.id = 111
    update.message.from_user = from_user

    reply_mock = AsyncMock()
    update.message.reply_text = reply_mock

    context = MagicMock()
    context.user_data = {"pending_log_habit_id": 2}  # Lecture

    await route_command(update, context)

    reply_mock.assert_called_once()
    args, _ = reply_mock.call_args
    assert 'a loggé 45min pour la quête "Lecture"' in args[0]
    assert "pending_log_habit_id" not in context.user_data

    # Verify log entry in DB
    logs = db_session.query(HabitLog).filter_by(habit_id=2).all()
    assert len(logs) == 1
    assert logs[0].log_type == "log"
    assert logs[0].amount == 45
    assert logs[0].unit == "min"


@pytest.mark.asyncio
async def test_callback_log_todo_completes_and_rewards_xp(db_session):
    update = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.data = "log_todo:10"  # Faire la vaisselle
    from_user = MagicMock()
    from_user.username = "Gabriel"
    from_user.id = 111
    query.from_user = from_user
    update.callback_query = query
    context = MagicMock()

    edit_mock = AsyncMock()
    query.edit_message_text = edit_mock

    await handle_callback(update, context)

    edit_mock.assert_called_once()
    args, _ = edit_mock.call_args
    assert "Todo complété : <b>Faire la vaisselle</b>" in args[0]
    assert "+15 XP" in args[0]

    # Verify Todo is completed in DB
    todo = db_session.query(Todo).filter_by(id=10).first()
    assert todo.is_completed is True
    assert todo.completed_at is not None

    # Verify User XP was rewarded (levels up from 2 to 4)
    user = db_session.query(User).filter_by(id=1).first()
    assert user.xp == 55
    assert user.level == 4
