"""Keeps every test away from the real sign-ins in the user's data dir."""

from __future__ import annotations

import pytest

from modstaller.apple import session as session_mod


@pytest.fixture(autouse=True)
def _private_accounts(tmp_path, monkeypatch):
    secrets = tmp_path / "secrets"
    monkeypatch.setattr(session_mod, "SESSION_FILE", secrets / "session.json")
    monkeypatch.setattr(session_mod, "ACCOUNTS_DIR", secrets / "accounts")
    monkeypatch.setattr(session_mod, "ACCOUNTS_INDEX",
                        secrets / "accounts.json")
