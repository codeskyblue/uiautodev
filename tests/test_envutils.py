from uiautodev.utils.envutils import get_int


def test_get_int_parses_valid_value(monkeypatch):
    monkeypatch.setenv("TEST_INT_VAR", "9009")
    assert get_int("TEST_INT_VAR") == 9009


def test_get_int_returns_none_when_unset(monkeypatch):
    monkeypatch.delenv("TEST_INT_VAR", raising=False)
    assert get_int("TEST_INT_VAR") is None


def test_get_int_returns_none_on_non_numeric_value(monkeypatch):
    monkeypatch.setenv("TEST_INT_VAR", "abc")
    assert get_int("TEST_INT_VAR") is None
