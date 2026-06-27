import pytest
from src.bot.parser import parse_command, ParserError


def test_parse_done_success():
    result = parse_command("/done routine_matin")
    assert result["command"] == "done"
    assert result["habit_name"] == "routine_matin"


def test_parse_done_missing_argument():
    with pytest.raises(ParserError) as exc_info:
        parse_command("/done")
    assert "Usage : /done [nom_habitude]" in str(exc_info.value)


def test_parse_log_success():
    result = parse_command("/log lecture 30min")
    assert result["command"] == "log"
    assert result["habit_name"] == "lecture"
    assert result["value"] == 30
    assert result["unit"] == "min"


def test_parse_log_with_spaces():
    result = parse_command("/log lecture 45 min")
    assert result["command"] == "log"
    assert result["habit_name"] == "lecture"
    assert result["value"] == 45
    assert result["unit"] == "min"


def test_parse_log_invalid_format():
    with pytest.raises(ParserError) as exc_info:
        parse_command("/log lecture abc")
    assert "Usage : /log [nom_habitude] [valeur][unité]" in str(exc_info.value)


def test_parse_skip_success():
    result = parse_command("/skip nage raison: fatigue extreme")
    assert result["command"] == "skip"
    assert result["habit_name"] == "nage"
    assert result["reason"] == "fatigue extreme"


def test_parse_skip_missing_reason():
    with pytest.raises(ParserError) as exc_info:
        parse_command("/skip nage")
    assert "Usage : /skip [nom_habitude] raison: [votre raison]" in str(exc_info.value)


def test_parse_status_success():
    result = parse_command("/status today")
    assert result["command"] == "status"
    assert result["target"] == "today"


def test_parse_set_day_success():
    result = parse_command("/set-day sick")
    assert result["command"] == "set-day"
    assert result["template_name"] == "sick"


def test_parse_help_aliases_aide():
    assert parse_command("/aide") == {"command": "aide"}
    assert parse_command("/help") == {"command": "aide"}


def test_parse_buy_success_with_args():
    result = parse_command("/buy Netflix")
    assert result["command"] == "buy"
    assert result["reward_name"] == "Netflix"


def test_parse_buy_success_no_args():
    result = parse_command("/buy")
    assert result["command"] == "buy"
    assert result["reward_name"] is None


def test_parse_unknown_command():
    with pytest.raises(ParserError) as exc_info:
        parse_command("/unknown")
    assert "Commande inconnue" in str(exc_info.value)


def test_parse_command_with_bot_username():
    result = parse_command("/shop@MyHabitRPGTrackerBot")
    assert result["command"] == "shop"
    assert result["filter"] == "toutes"

    result2 = parse_command("/buy@MyHabitRPGTrackerBot Netflix")
    assert result2["command"] == "buy"
    assert result2["reward_name"] == "Netflix"


def test_parse_todo_text_with_dates():
    from src.bot.listener import parse_todo_text
    import datetime

    # Test no dates
    title, do_d, due_d = parse_todo_text("Acheter du pain")
    assert title == "Acheter du pain"
    assert do_d is None
    assert due_d is None

    # Test do date
    title, do_d, due_d = parse_todo_text("Acheter du pain do:today")
    assert title == "Acheter du pain"
    assert do_d == datetime.date.today()
    assert due_d is None

    # Test due date
    title, do_d, due_d = parse_todo_text("Acheter du pain due:tomorrow")
    assert title == "Acheter du pain"
    assert do_d is None
    assert due_d == datetime.date.today() + datetime.timedelta(days=1)

    # Test both do and due dates
    title, do_d, due_d = parse_todo_text("Acheter du pain do:2026-12-25 due:2026-12-31")
    assert title == "Acheter du pain"
    assert do_d == datetime.date(2026, 12, 25)
    assert due_d == datetime.date(2026, 12, 31)

    # Test DD/MM format
    today = datetime.date.today()
    title, do_d, due_d = parse_todo_text("Faire les courses do:15/08")
    assert title == "Faire les courses"
    assert do_d == datetime.date(today.year, 8, 15)
