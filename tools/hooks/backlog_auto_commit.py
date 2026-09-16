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

    prev_show = run(["git", "show", "HEAD:backlog.json"])
    previous = load_json_str(prev_show.stdout) if prev_show.returncode == 0 else {"tasks": []}
    prev_status = {t["id"]: t["status"] for t in previous.get("tasks", [])}

    newly_done = [
        t for t in current.get("tasks", [])
        if t.get("status") == "done" and prev_status.get(t["id"]) != "done"
    ]

    add = run(["git", "add", "--"] + TRACKED_PATHS)
    if add.returncode != 0:
        print(json.dumps({
            "systemMessage": f"backlog 변경 stage 실패: {add.stderr.strip()}"
        }, ensure_ascii=False))
        return

    if newly_done:
        bullet_lines = "\n".join(f"- {t['id']}: {t['title']}" for t in newly_done)
        subject = (
            f"Complete backlog task(s): {', '.join(t['id'] for t in newly_done)}"
        )
        message = f"{subject}\n\n{bullet_lines}\n\ndate: {date.today().isoformat()}"
    else:
        changed_ids = sorted(
            t["id"] for t in current.get("tasks", [])
            if prev_status.get(t["id"]) != t.get("status")
        )
        if changed_ids:
            subject = f"Update backlog.json ({', '.join(changed_ids)})"
        else:
            subject = "Update backlog.json"
        message = subject

    commit = run(["git", "commit", "-m", message])
    if commit.returncode != 0:
        print(json.dumps({
            "systemMessage": f"backlog 자동 커밋 실패: {commit.stderr.strip()}"
        }, ensure_ascii=False))
        return

    result_msg = f"backlog.json 변경사항 자동 커밋됨: {subject}"

    if newly_done:
        push = run(["git", "push"])
        if push.returncode == 0:
            result_msg += " (push 완료)"
        else:
            result_msg += f" (push 실패: {push.stderr.strip()})"

    print(json.dumps({"systemMessage": result_msg}, ensure_ascii=False))


if __name__ == "__main__":
    main()
