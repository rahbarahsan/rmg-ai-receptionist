import pytest

from app.phone import normalize_phone


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+8801700000000", "+8801700000000"),
        (" +880 1700-000000 ", "+8801700000000"),
        ("01700000000", "+8801700000000"),  # BD local mobile -> +880
        ("008801700000000", "+8801700000000"),  # 00 international prefix -> +
        ("8801700000000", "+8801700000000"),  # country code, no +
        ("+1 (415) 555-2671", "+14155552671"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_normalize_phone(raw: str, expected: str) -> None:
    assert normalize_phone(raw) == expected
