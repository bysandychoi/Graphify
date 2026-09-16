#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stop 훅: Claude 응답이 끝날 때마다 Windows 팝업으로 완료를 알린다.

현재 활성 작업(.claude/state/active_task.json)이 있으면 어떤 backlog
작업을 보고 있었는지 함께 보여준다. 이 스크립트는 hook 프로세스이므로
backlog.json을 직접 읽어도 guard_backlog_*.py에 걸리지 않는다
(guard_task_in_progress.py와 동일한 근거).

MessageBoxW는 사용자가 닫기 전까지 호출자를 막으므로, 실제 표시는
_popup_worker.py를 분리된 프로세스로 띄워서 하고 이 훅 자체는 곧바로
반환한다. Windows 전용(user32.dll)이며 표준 라이브러리만 사용한다.
"""
import json
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
ACTIVE_PATH = ROOT / ".claude" / "state" / "active_task.json"
BACKLOG_PATH = ROOT / "backlog.json"
WORKER_PATH = Path(__file__).resolve().parent / "_popup_worker.py"

DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000000


def active_task_line():
    if not ACTIVE_PATH.exists() or not BACKLOG_PATH.exists():
        return None
    try:
        active = json.loads(ACTIVE_PATH.read_text(encoding="utf-8"))
        backlog = json.loads(BACKLOG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    task_id = active.get("id")
    task = next((t for t in backlog.get("tasks", []) if t["id"] == task_id), None)
    if not task:
        return None
    return f"{task['id']}: {task['title']} ({task['status']})"


def build_message():
    line = active_task_line()
    if line:
        return "Claude 작업 완료!\n활성 작업: " + line
    return "Claude 작업 완료!\n(활성 작업 없음 - backlog와 무관한 작업)"


def main():
    message = build_message()
    subprocess.Popen(
        [sys.executable, str(WORKER_PATH), message],
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
        close_fds=True,
    )


if __name__ == "__main__":
    main()
