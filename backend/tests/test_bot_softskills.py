import pytest
import html
import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base
from src.database.models import User, UserSoftskillProgress
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
        gabriel = User(
            id=1, username="Gabriel", chat_id="111", xp=100, level=2, gold=40
        )
        session.add(gabriel)

        # Seed progress for a test skill
        progress = UserSoftskillProgress(
            user_id=1,
            softskill_id="active_listening",
            success_criteria_test="Ecouter sans interrompre pendant 5 minutes.",
            completed=False,
            current_level=0,
        )
        session.add(progress)
        session.commit()

        # Mock tree config
        mock_tree = {
            "branches": {
                "Communication": {"color": "#ff0000", "pale_color": "#ffcccc"},
                "Leadership": {"color": "#00ff00", "pale_color": "#ccffcc"},
            },
            "skills": [
                {
                    "id": "active_listening",
                    "name": "Écoute Active",
                    "description": "Prêter attention sans juger",
                    "branch": "Communication",
                    "prerequisites": [],
                    "related": [],
                    "execution_order": 1,
                    "x": 100,
                    "y": 80,
                }
            ],
        }

        # Create temporary config file and mock it
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(mock_tree, f)

        monkeypatch.setattr(
            "src.services.softskill_service._get_config_path", lambda: tmp_path
        )

        # Monkeypatch DB session and configs in listener.py
        monkeypatch.setattr("src.bot.listener.SessionLocal", lambda: session)
        monkeypatch.setattr("src.bot.listener.TELEGRAM_GROUP_ID", "")

        yield session
    finally:
        session.close()
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_softskill_command_shows_branches(db_session):
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = "/softskill"
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
    assert "Arbre des Softskills" in args[0]

    reply_markup = kwargs["reply_markup"]
    buttons = reply_markup.inline_keyboard
    assert len(buttons) == 1
    assert buttons[0][0].text == "Communication"
    assert buttons[0][0].callback_data == "ss_branch:Communication"
    assert buttons[0][1].text == "Leadership"
    assert buttons[0][1].callback_data == "ss_branch:Leadership"


@pytest.mark.asyncio
async def test_callback_ss_branch(db_session):
    update = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.data = "ss_branch:Communication"
    query.message = MagicMock()
    query.message.reply_text = AsyncMock()
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
    assert "Branche : Communication" in args[0]
    assert "Écoute Active" in args[0]
    assert "En cours" in args[0]

    reply_markup = kwargs["reply_markup"]
    buttons = reply_markup.inline_keyboard
    assert len(buttons) == 2
    assert buttons[0][0].text == "➕ Ajouter un Softskill"
    assert buttons[0][0].callback_data == "ss_add_select:Communication"
    assert buttons[0][1].text == "✅ Valider un Softskill"
    assert buttons[0][1].callback_data == "ss_val_select:Communication"


@pytest.mark.asyncio
async def test_callback_ss_add_select_starts_wizard(db_session):
    update = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.data = "ss_add_select:Communication"
    query.message = MagicMock()
    from_user = MagicMock()
    from_user.username = "Gabriel"
    from_user.id = 111
    query.from_user = from_user
    update.callback_query = query
    context = MagicMock()
    context.user_data = {}

    reply_mock = AsyncMock()
    query.message.reply_text = reply_mock

    await handle_callback(update, context)

    reply_mock.assert_called_once()
    assert "Étape 1/4" in reply_mock.call_args[0][0]
    assert context.user_data["pending_ss_create"] == {
        "step": 1,
        "branch": "Communication",
    }


@pytest.mark.asyncio
async def test_route_command_wizard_steps(db_session):
    context = MagicMock()
    context.user_data = {"pending_ss_create": {"step": 1, "branch": "Communication"}}

    async def send_msg(text):
        update = MagicMock()
        update.message = MagicMock()
        update.message.text = text
        update.effective_chat.id = 111
        from_user = MagicMock()
        from_user.username = "Gabriel"
        from_user.id = 111
        update.message.from_user = from_user

        reply_mock = AsyncMock()
        update.message.reply_text = reply_mock
        await route_command(update, context)
        return reply_mock.call_args[0][0] if reply_mock.call_args else None

    # Step 1: ID
    reply = await send_msg("negotiation")
    assert "Étape 2/4" in reply
    assert context.user_data["pending_ss_create"]["id"] == "negotiation"
    assert context.user_data["pending_ss_create"]["step"] == 2

    # Step 2: Name
    reply = await send_msg("Négociation Active")
    assert "Étape 3/4" in reply
    assert context.user_data["pending_ss_create"]["name"] == "Négociation Active"
    assert context.user_data["pending_ss_create"]["step"] == 3

    # Step 3: Description
    reply = await send_msg("Négocier des accords")
    assert "Étape 4/4" in reply
    assert (
        context.user_data["pending_ss_create"]["description"] == "Négocier des accords"
    )
    assert context.user_data["pending_ss_create"]["step"] == 4

    # Step 4: Execution Order
    reply = await send_msg("2")
    assert "Softskill créé avec succès" in reply
    assert "pending_ss_create" not in context.user_data


@pytest.mark.asyncio
async def test_callback_ss_val_select(db_session):
    update = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.data = "ss_val_select:Communication"
    query.message = MagicMock()
    query.message.reply_text = AsyncMock()
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
    assert "Validation — Communication" in edit_mock.call_args[0][0]

    reply_markup = edit_mock.call_args[1]["reply_markup"]
    buttons = reply_markup.inline_keyboard
    assert len(buttons) == 2
    assert buttons[0][0].text == "⏳ Écoute Active"
    assert buttons[0][0].callback_data == "ss_test_val:active_listening"


@pytest.mark.asyncio
async def test_callback_ss_test_val(db_session):
    update = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.data = "ss_test_val:active_listening"
    query.message = MagicMock()
    query.message.reply_text = AsyncMock()
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
    text = edit_mock.call_args[0][0]
    assert "Validation — Écoute Active" in text
    assert "Ecouter sans interrompre pendant 5 minutes." in text

    reply_markup = edit_mock.call_args[1]["reply_markup"]
    buttons = reply_markup.inline_keyboard
    assert buttons[0][0].text == "✅ Valider"
    assert buttons[0][0].callback_data == "ss_confirm_val:active_listening"
    assert buttons[0][1].text == "❌ Annuler"
    assert buttons[0][1].callback_data == "ss_branch:Communication"


@pytest.mark.asyncio
async def test_callback_ss_confirm_val_success(db_session):
    update = MagicMock()
    query = MagicMock()
    query.answer = AsyncMock()
    query.data = "ss_confirm_val:active_listening"
    query.message = MagicMock()
    query.message.reply_text = AsyncMock()
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
    assert "validé avec succès" in edit_mock.call_args[0][0]

    # Verify progress in DB
    progress = (
        db_session.query(UserSoftskillProgress)
        .filter_by(user_id=1, softskill_id="active_listening")
        .first()
    )
    assert progress.completed is True
