"""Hermetic test environment. Set before any `app.*` import triggers Settings().

Uses os.environ (which pydantic-settings prioritizes over .env), so tests never
depend on real secrets or a reachable database. DB-touching code is monkeypatched
in the tests, so the sqlite URL is never actually connected to.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("AGENT_TOOL_SECRET", "test_secret_at_least_16_chars_long")
