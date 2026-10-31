"""Smoke tests for QuantEdge: authentication storage and the Streamlit login page."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

# Use a throw-away database so tests never touch real user data.
os.environ["AUTH_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_auth.db")

import pytest  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

import auth_db  # noqa: E402


@pytest.fixture(autouse=True, scope="module")
def database():
    auth_db.init_db()
    yield


def test_create_and_verify_user():
    auth_db.create_user("alice", "Str0ng!pw")
    assert auth_db.verify_user("alice", "Str0ng!pw") is True


def test_wrong_password_is_rejected():
    auth_db.create_user("bob", "Str0ng!pw")
    assert auth_db.verify_user("bob", "wrong") is False


def test_unknown_user_is_rejected():
    assert auth_db.verify_user("nobody", "whatever") is False


def test_duplicate_user_is_rejected():
    auth_db.create_user("carol", "Str0ng!pw")
    with pytest.raises(ValueError):
        auth_db.create_user("carol", "Another1!")


def test_password_is_not_stored_in_plain_text():
    auth_db.create_user("dave", "Str0ng!pw")
    with auth_db.SessionLocal() as session:
        stored = session.query(auth_db.User).filter_by(username="dave").first().password_hash
    assert stored != "Str0ng!pw" and stored.startswith("$pbkdf2-sha256$")


def test_search_history_round_trip():
    auth_db.create_user("erin", "Str0ng!pw")
    auth_db.add_search("erin", "AAPL", "2021-01-01 to 2026-01-01 (Daily)", "MACD",
                       "2026-01-01T10:00:00", "Buy")
    history = auth_db.get_searches("erin")
    assert len(history) == 1
    assert history[0]["symbol"] == "AAPL" and history[0]["action"] == "Buy"


def test_unknown_user_has_no_history():
    assert auth_db.get_searches("ghost") == []


def test_login_page_renders():
    at = AppTest.from_file(str(ROOT / "src" / "app.py"), default_timeout=60).run()
    assert not at.exception
    assert any("Please log in" in i.value for i in at.info)


def test_user_can_log_in_through_the_app():
    auth_db.create_user("frank", "Str0ng!pw")
    at = AppTest.from_file(str(ROOT / "src" / "app.py"), default_timeout=60).run()
    at.text_input(key="login_user").input("frank")
    at.text_input(key="login_pass").input("Str0ng!pw")
    at.button[0].click()
    at.run()
    assert not at.exception
    assert any("Logged in as frank" in s.value for s in at.success)
