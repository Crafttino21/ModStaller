#!/usr/bin/env python3
"""Rauchtest fuer ein gebautes Backend: einmal das, was die Oberflaeche tut.

    python packaging/smoke_backend.py <programm> [methode ...]

Startet ``<programm> serve`` und stellt jede Methode als JSON-RPC-Anfrage.
stdin bleibt dabei offen: bei EOF bricht der Server laufende Arbeit ab, ein
``echo ... | backend serve`` beantwortete langsamere Methoden also nie.

Default sind ``info`` und ``doctor``. ``doctor`` ist die einzige Methode, die
pymobiledevice3, anisette, unicorn und cryptography wirklich anfasst - und bis
1.1.0-beta.3 beendete sie das Windows-Programm nativ (0xC0000409, siehe
:func:`build_backend.clear_cfg`), ohne dass es in der Pipeline auffiel.

Exit 1, wenn eine Antwort ausbleibt, ein Fehler kommt oder der Prozess stirbt.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

DEFAULT_METHODS = ("info", "doctor")


def _reply(proc: subprocess.Popen, req_id: int) -> dict | None:
    """Die Antwort auf ``req_id`` - None, wenn der Prozess vorher wegbricht."""
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            print(f"    unlesbare Zeile: {line[:200]}")
            continue
        if msg.get("id") == req_id:
            return msg
        # Notifications (ready, log, progress) gehoeren nicht hierher.
    return None


def smoke(exe: Path, methods: list[str]) -> int:
    print(f"Rauchtest: {exe}")
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
                print(f"  {method}: keine Antwort, Prozess beendet "
                      f"(Exit {proc.returncode})")
                bad.append(method)
                break
            if "error" in msg:
                print(f"  {method}: Fehler {msg['error']}")
                bad.append(method)
                continue
            print(f"  {method}: ok")
            _show(method, msg["result"])
    finally:
        if proc.poll() is None:
            proc.stdin.close()
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()

    if bad:
        print(f"Fehlgeschlagen: {', '.join(bad)}")
        return 1
    return 0


def _show(method: str, result: object) -> None:
    """Das Ergebnis so zeigen, dass ein Pipeline-Log etwas davon hat."""
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
        print(f"Nicht gefunden: {exe}", file=sys.stderr)
        return 2
    return smoke(exe, list(sys.argv[2:]) or list(DEFAULT_METHODS))


if __name__ == "__main__":
    sys.exit(main())
