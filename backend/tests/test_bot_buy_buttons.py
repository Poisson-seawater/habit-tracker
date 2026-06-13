import pytest
import datetime
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base
from src.database.models import User, Reward
from src.bot.listener import route_command, handle_callback

@pytest.fixture
def db_session(monkeypatch):
    # Use an in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Seed Gabriel (User ID 1)
        gabriel = User(id=1, username="Gabriel", chat_id="111", xp=100, level=2, gold=40)
        session.add(gabriel)

        # Seed rewards
        # 1. Available daily allostasis reward
        r1 = Reward(
            id=1,
            user_id=1,
            title="TV Show 25m",
            category="allostasis_daily",
            gold_cost=0,
            purchased_count=0
        )
        session.add(r1)

        # 2. Already redeemed daily allostasis reward (should not show up as available)
        r2 = Reward(
            id=2,
            user_id=1,
            title="Bière du soir",
            category="allostasis_daily",
            gold_cost=0,
            purchased_count=1,
            last_purchased_at=datetime.datetime.now()
        )
        session.add(r2)

        # 3. Regular reward too expensive (cost: 50, gold: 40) - should not show up
        r3 = Reward(
            id=3,
            user_id=1,
            title="Expensive Reward",
            category="regular",
            gold_cost=50,
            purchased_count=0
        )
        session.add(r3)

        # 4. Regular reward affordable (cost: 30, gold: 40) - should show up
        r4 = Reward(
            id=4,
            user_id=1,
            title="Affordable Reward",
            category="regular",
            gold_cost=30,
            purchased_count=0
        )
        session.add(r4)

        session.commit()

        # Monkeypatch DB session and configs in listener.py
        monkeypatch.setattr("src.bot.listener.SessionLocal", lambda: session)
        monkeypatch.setattr("src.bot.listener.TELEGRAM_GROUP_ID", "")

        yield session
    finally:
        session.close()

@pytest.mark.asyncio
async def test_buy_command_without_args_shows_categories(db_session):
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = "/buy"
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
    assert "Boutique — Choisissez une catégorie" in args[0]
    
    reply_markup = kwargs["reply_markup"]
    buttons = reply_markup.inline_keyboard
    # Should have 2 rows:
    # Row 1: Allostasie Day, Allostasie Week
    # Row 2: Shop Basic
    assert len(buttons) == 2
    assert buttons[0][0].text == "🔄 Allostasie Day"
    assert buttons[0][0].callback_data == "buy_cat:allostasis_daily"
    assert buttons[0][1].text == "📅 Allostasie Week"
    assert buttons[0][1].callback_data == "buy_cat:allostasis_weekly"
    assert buttons[1][0].text == "💎 Shop Basic"
    assert buttons[1][0].callback_data == "buy_cat:regular"

@pytest.mark.asyncio
async def test_callback_buy_category_allostasis_daily(db_session):
    update = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.data = "buy_cat:allostasis_daily"
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
    assert "Items disponibles — Allostasie Day" in args[0]
    
    reply_markup = kwargs["reply_markup"]
    buttons = reply_markup.inline_keyboard
    # Only r1 ("TV Show 25m") is available (r2 already redeemed today)
    assert len(buttons) == 1
    assert buttons[0][0].text == "✨ TV Show 25m"
    assert buttons[0][0].callback_data == "buy_item:1"

@pytest.mark.asyncio
async def test_callback_buy_category_regular(db_session):
    update = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.data = "buy_cat:regular"
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
    assert "Items disponibles — Boutique Classique" in args[0]
    
    reply_markup = kwargs["reply_markup"]
    buttons = reply_markup.inline_keyboard
    # Only r4 ("Affordable Reward") is available because user only has 40 gold and r3 costs 50
    assert len(buttons) == 1
    assert buttons[0][0].text == "💰 Affordable Reward (30 Or)"
    assert buttons[0][0].callback_data == "buy_item:4"

@pytest.mark.asyncio
async def test_callback_buy_item_allostasis_success(db_session):
    update = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.data = "buy_item:1"
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
    assert "Allostasie validée !" in args[0]
    assert "TV Show 25m" in args[0]

    # Verify state in DB
    r1 = db_session.query(Reward).filter_by(id=1).first()
    assert r1.purchased_count == 1
    assert r1.last_purchased_at is not None

@pytest.mark.asyncio
async def test_callback_buy_item_regular_success(db_session):
    update = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.data = "buy_item:4"
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
    assert "Achat réussi !" in args[0]
    assert "Affordable Reward" in args[0]
    assert "10 Or" in args[0] # 40 - 30 = 10

    # Verify state in DB
    r4 = db_session.query(Reward).filter_by(id=4).first()
    assert r4.purchased_count == 1
    gabriel = db_session.query(User).filter_by(id=1).first()
    assert gabriel.gold == 10
