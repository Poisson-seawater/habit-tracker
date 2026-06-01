import pytest
from src.database.models import User
from src.services.score_service import add_user_xp

def test_add_xp_exponential_no_level_up():
    user = User(username="Gabriel", xp=0, level=1, gold=0)
    
    levels = add_user_xp(user, 5)
    
    assert levels == []
    assert user.level == 1
    assert user.xp == 5
    assert user.gold == 0

def test_add_xp_exponential_single_level_up():
    user = User(username="Gabriel", xp=5, level=1, gold=0)
    
    # Level 1 -> 2 requires 10 XP
    levels = add_user_xp(user, 5)
    
    assert levels == [2]
    assert user.level == 2
    assert user.xp == 0  # 5 + 5 - 10 = 0 residual

def test_add_xp_exponential_multi_level_up():
    user = User(username="Gabriel", xp=0, level=1, gold=0)
    
    # Gain 35 XP
    # Level 1 -> 2 takes 10 XP (residual 25)
    # Level 2 -> 3 takes 20 XP (residual 5)
    # Level 3 -> 4 takes 40 XP (requires 40, user has 5)
    # Expected: level = 3, xp = 5, levels_gained = [2, 3]
    levels = add_user_xp(user, 35)
    
    assert levels == [2, 3]
    assert user.level == 3
    assert user.xp == 5
