#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PreToolUse(Read|Edit|Write) 훅: backlog.json 직접 조회/수정을 막는다.

의존성: 표준 라이브러리만 사용.
"""
import json
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

GUIDANCE = (
    "backlog.json은 직접 읽거나 수정할 수 없습니다. "
    "tools/backlog_cli.py를 사용하세요.\n"
    "  조회: python tools/backlog_cli.py list [--status ...] [--phase ...]\n"
    "  상세: python tools/backlog_cli.py show <id>\n"
    "  추가: python tools/backlog_cli.py add --phase ... --title ... --description ... --acceptance ...\n"
    "  수정: python tools/backlog_cli.py update <id> --status ...\n"
)


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    file_path = str(payload.get("tool_input", {}).get("file_path", ""))
    normalized = file_path.replace("\\", "/")
    if normalized.endswith("/backlog.json") or normalized == "backlog.json":
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
