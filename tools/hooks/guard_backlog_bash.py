#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PreToolUse(Bash) 훅: backlog.json을 CLI 없이 직접 다루는 셸 명령을 막는다.

backlog_cli.py를 거치지 않고 backlog.json을 언급하는 명령(cat/type/Get-Content,
리다이렉션, git show 등)을 전부 차단한다. 오탐(false positive)보다 원칙을
우선한다 — 필요하면 CLI에 명령을 추가하는 쪽으로 해결한다.
"""
import json
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

GUIDANCE = (
    "backlog.json을 셸에서 직접 다루지 마세요. "
    "tools/backlog_cli.py (list/show/add/update/set-status/validate)만 사용하세요."
)


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    command = str(payload.get("tool_input", {}).get("command", ""))
    if "backlog.json" not in command:
        return
    if "backlog_cli" in command:
        return
    print(json.dumps({
        "systemMessage": GUIDANCE,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": GUIDANCE,
        },
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
