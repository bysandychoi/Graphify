#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""현재 '작업 중'으로 표시한 backlog task(활성 작업)를 추적한다.

.claude/state/active_task.json 한 파일에 {id, started_at}만 기록한다.
공유 규칙(backlog.json)과 달리 세션별 임시 상태이므로 git에 커밋하지 않는다
(.gitignore에 .claude/state/ 추가됨).
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / ".claude" / "state"
ACTIVE_PATH = STATE_DIR / "active_task.json"


def get_active() -> dict | None:
    if not ACTIVE_PATH.exists():
        return None
    try:
        return json.loads(ACTIVE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def set_active(task_id: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_PATH.write_text(
        json.dumps({"id": task_id, "started_at": date.today().isoformat()}, ensure_ascii=False),
        encoding="utf-8",
    )


def clear_active() -> None:
    if ACTIVE_PATH.exists():
        ACTIVE_PATH.unlink()
