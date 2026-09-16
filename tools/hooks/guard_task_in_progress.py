#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PreToolUse(Edit|Write) 훅: 활성 작업(active task)이 in_progress 상태일 때만
파일 수정을 허용한다.

.claude/state/active_task.json에 활성 작업이 없으면 아무 것도 하지 않는다
(backlog_cli.py start를 쓰지 않는 일반 편집을 막지 않기 위함 — 옵트인 방식).
backlog.json/backlog/*.md, .claude/**, tools/hooks/**는 검사 대상에서 뺀다:
task 문서 갱신이나 훅/에이전트 자체 정비는 작업 상태와 무관하게 항상 가능해야
하기 때문이다. HANDOFF.md는 예외에 넣지 않는다 — T005(HANDOFF.md 작성)도
다른 작업과 똑같이 task-briefer로 시작해야 하고, phase 완료 시 갱신도 해당
작업이 in_progress인 동안 끝내도록 작업 흐름을 짠다(AGENTS.md "작업 흐름"
참고). 이 스크립트는 hook 프로세스이므로 backlog.json을 직접 읽어도
guard_backlog_*.py에 걸리지 않는다.
"""
import json
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
ACTIVE_PATH = ROOT / ".claude" / "state" / "active_task.json"
EXEMPT_PREFIXES = ("backlog/", ".claude/", "tools/hooks/")
EXEMPT_FILES = ("backlog.json",)


def is_exempt(rel_path: str) -> bool:
    if rel_path in EXEMPT_FILES:
        return True
    return any(rel_path.startswith(p) for p in EXEMPT_PREFIXES)


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    file_path = str(payload.get("tool_input", {}).get("file_path", ""))
    rel_path = file_path.replace("\\", "/")
    if rel_path.startswith(str(ROOT).replace("\\", "/") + "/"):
        rel_path = rel_path[len(str(ROOT).replace("\\", "/")) + 1:]
    if is_exempt(rel_path):
        return

    if not ACTIVE_PATH.exists():
        return

    try:
        active = json.loads(ACTIVE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    task_id = active.get("id")

    backlog_path = ROOT / "backlog.json"
    if not backlog_path.exists():
        return
    try:
        backlog = json.loads(backlog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    task = next((t for t in backlog.get("tasks", []) if t.get("id") == task_id), None)

    if task is None:
        reason = (
            f"활성 작업 {task_id}을(를) backlog.json에서 찾을 수 없습니다. "
            "'python tools/backlog_cli.py clear-active'로 정리하세요."
        )
    elif task["status"] != "in_progress":
        reason = (
            f"활성 작업 {task_id}의 상태가 '{task['status']}'입니다 (in_progress 아님). "
            f"'python tools/backlog_cli.py start {task_id}'로 먼저 in_progress로 전환하세요. "
            f"(대상 파일: {rel_path})"
        )
    else:
        return

    print(json.dumps({
        "systemMessage": reason,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
