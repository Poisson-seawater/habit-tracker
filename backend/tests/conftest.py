import os

# Clear authentication settings to run the test suite in standard development/testing mode
# Specific tests (e.g., test_auth.py) will override or monkeypatch these as needed.
os.environ["AUTH_BOOTSTRAP_CODE"] = ""
os.environ["HABIT_API_TOKEN"] = ""
