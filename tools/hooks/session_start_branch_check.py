#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SessionStart 훅: 현재 git 브랜치를 안내하고, main이면 dev 전환을 권고한다."""
import json
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        return
    branch = proc.stdout.strip()

    message = f"현재 브랜치: {branch}"
    if branch == "main":
        message += (
            "\nmain 브랜치입니다. 작업 전 dev 브랜치로 전환하세요: "
            "git checkout -b dev  (또는 이미 있다면 git checkout dev)"
        )
    print(json.dumps({"systemMessage": message}, ensure_ascii=False))


if __name__ == "__main__":
    main()
