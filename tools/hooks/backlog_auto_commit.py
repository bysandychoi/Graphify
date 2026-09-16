#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PostToolUse(Bash) 훅: backlog.json 변경을 자동 커밋한다.

status가 'done'으로 바뀐 작업이 있으면 변경 내역을 요약해 커밋 메시지에 담고
push까지 수행한다. 그 외 변경은 커밋만 하고 push는 하지 않는다.

의존성: 표준 라이브러리만 사용. git 명령은 subprocess로 직접 호출한다
(hook은 harness가 실행하는 별도 프로세스이므로 Claude의 PreToolUse 훅을
다시 거치지 않는다).
"""
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
TRACKED_PATHS = ["backlog.json", "backlog"]


def run(args):
    return subprocess.run(
        args, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8"
    )


def load_json_str(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"tasks": []}


def _load_previous() -> dict:
    prev_show = run(["git", "show", "HEAD:backlog.json"])
    return load_json_str(prev_show.stdout) if prev_show.returncode == 0 else {"tasks": []}


def _newly_done(current: dict, prev_status: dict) -> list:
    return [
        t for t in current.get("tasks", [])
        if t.get("status") == "done" and prev_status.get(t["id"]) != "done"
    ]


def _build_message(current: dict, prev_status: dict, newly_done: list):
    if newly_done:
        bullet_lines = "\n".join(f"- {t['id']}: {t['title']}" for t in newly_done)
        subject = f"Complete backlog task(s): {', '.join(t['id'] for t in newly_done)}"
        message = f"{subject}\n\n{bullet_lines}\n\ndate: {date.today().isoformat()}"
        return subject, message
    changed_ids = sorted(
        t["id"] for t in current.get("tasks", [])
        if prev_status.get(t["id"]) != t.get("status")
    )
    subject = f"Update backlog.json ({', '.join(changed_ids)})" if changed_ids else "Update backlog.json"
    return subject, subject


def _report(message: str) -> None:
    print(json.dumps({"systemMessage": message}, ensure_ascii=False))


def main():
    try:
        json.load(sys.stdin)
    except json.JSONDecodeError:
        pass

    status = run(["git", "status", "--porcelain", "--"] + TRACKED_PATHS)
    if status.returncode != 0 or not status.stdout.strip():
        return

    cur_path = ROOT / "backlog.json"
    if not cur_path.exists():
        return
    current = load_json_str(cur_path.read_text(encoding="utf-8"))
    previous = _load_previous()
    prev_status = {t["id"]: t["status"] for t in previous.get("tasks", [])}
    newly_done = _newly_done(current, prev_status)

    add = run(["git", "add", "--"] + TRACKED_PATHS)
    if add.returncode != 0:
        _report(f"backlog 변경 stage 실패: {add.stderr.strip()}")
        return

    subject, message = _build_message(current, prev_status, newly_done)
    commit = run(["git", "commit", "-m", message])
    if commit.returncode != 0:
        _report(f"backlog 자동 커밋 실패: {commit.stderr.strip()}")
        return

    result_msg = f"backlog.json 변경사항 자동 커밋됨: {subject}"
    if newly_done:
        push = run(["git", "push"])
        result_msg += " (push 완료)" if push.returncode == 0 else f" (push 실패: {push.stderr.strip()})"

    _report(result_msg)


if __name__ == "__main__":
    main()
