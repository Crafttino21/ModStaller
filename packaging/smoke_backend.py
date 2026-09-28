#!/usr/bin/env python3
"""Smoke test for a built backend: one pass of what the GUI does.

    python packaging/smoke_backend.py <program> [method ...]

Starts ``<program> serve`` and sends each method as a JSON-RPC request.
stdin stays open meanwhile: on EOF the server aborts running work, so an
``echo ... | backend serve`` would never answer slower methods.

Defaults are ``info`` and ``doctor``. ``doctor`` is the only method that
actually touches pymobiledevice3, anisette, unicorn and cryptography - and up
to 1.1.0-beta.3 it killed the Windows program natively (0xC0000409, see
:func:`build_backend.clear_cfg`) without the pipeline noticing.

Exit 1 if a reply is missing, an error comes back or the process dies.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

DEFAULT_METHODS = ("info", "doctor")

#: A doctor check that only fails when the build left something out - the
#: JIT engine is imported lazily, so nothing else would notice (the label
#: is ``doctor.JIT_ENGINE``).
MUST_PASS = "JIT engine (QuickJS)"


def _reply(proc: subprocess.Popen, req_id: int) -> dict | None:
    """The reply to ``req_id`` - None if the process dies first."""
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            print(f"    unreadable line: {line[:200]}")
            continue
        if msg.get("id") == req_id:
            return msg
        # Notifications (ready, log, progress) don't belong here.
    return None


def smoke(exe: Path, methods: list[str]) -> int:
    print(f"Smoke test: {exe}")
    proc = subprocess.Popen(
        [str(exe), "serve"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace")
    bad: list[str] = []
    try:
        for req_id, method in enumerate(methods, start=1):
            proc.stdin.write(json.dumps(
                {"jsonrpc": "2.0", "id": req_id, "method": method}) + "\n")
            proc.stdin.flush()

            msg = _reply(proc, req_id)
            if msg is None:
                proc.wait()
                print(f"  {method}: no reply, process exited "
                      f"(Exit {proc.returncode})")
                bad.append(method)
                break
            if "error" in msg:
                print(f"  {method}: error {msg['error']}")
                bad.append(method)
                continue
            print(f"  {method}: ok")
            _show(method, msg["result"])
            if method == "doctor" and not _bundled(msg["result"]):
                bad.append(f"{method} ({MUST_PASS})")
    finally:
        if proc.poll() is None:
            proc.stdin.close()
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()

    if bad:
        print(f"Failed: {', '.join(bad)}")
        return 1
    return 0


def _bundled(result: object) -> bool:
    """Whether the ``MUST_PASS`` check is there and green."""
    return isinstance(result, list) and any(
        c.get("label") == MUST_PASS and c.get("ok") for c in result)


def _show(method: str, result: object) -> None:
    """Show the result in a way that is useful in a pipeline log."""
    if method == "doctor" and isinstance(result, list):
        for check in result:
            mark = "+" if check.get("ok") else "-"
            print(f"    {mark} {check.get('label')}: {check.get('detail')}")
    else:
        print(f"    {json.dumps(result, ensure_ascii=False)[:300]}")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.strip().split("\n\n")[1], file=sys.stderr)
        return 2
    exe = Path(sys.argv[1])
    if not exe.is_file():
        print(f"Not found: {exe}", file=sys.stderr)
        return 2
    return smoke(exe, list(sys.argv[2:]) or list(DEFAULT_METHODS))


if __name__ == "__main__":
    sys.exit(main())
