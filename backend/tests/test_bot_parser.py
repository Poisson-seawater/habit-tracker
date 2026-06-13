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

def test_parse_app_success():
    result = parse_command("/app")
    assert result["command"] == "app"

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
