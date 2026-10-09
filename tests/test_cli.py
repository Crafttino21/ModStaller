"""Command line: options where people actually put them."""

from __future__ import annotations

import pytest

from modstaller import cli


@pytest.mark.parametrize("argv, expected", [
    (["--debug", "login"], True),
    (["login", "--debug"], True),     # issue #3: this used to be an error
    (["login"], False),
])
def test_debug_works_before_and_after_login(argv, expected):
    assert cli.build_parser().parse_args(argv).debug is expected


async def test_login_takes_the_apple_id_from_account(monkeypatch):
    """-a/--account names an Apple ID everywhere else, so login uses it too
    instead of asking again."""
    import builtins
    import getpass

    def no_prompt(_):
        raise AssertionError("asked for the Apple ID although -a gave it")

    monkeypatch.setattr(builtins, "input", no_prompt)
    monkeypatch.setattr(getpass, "getpass", lambda _: "")
    seen = {}

    def fake_login(apple_id, password, ani, code_prompt=None, debug=False):
        seen["apple_id"] = apple_id
        raise RuntimeError("stop here")

    monkeypatch.setattr("modstaller.apple.session.login", fake_login)
    monkeypatch.setattr(cli, "_anisette", lambda: None)
    args = cli.build_parser().parse_args(["-a", "someone@example.com", "login"])
    with pytest.raises(RuntimeError, match="stop here"):
        await cli._login(args)
    assert seen["apple_id"] == "someone@example.com"
