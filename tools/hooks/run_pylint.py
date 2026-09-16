#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PostToolUse(Edit|Write) 훅: 수정/작성된 .py 파일에 pylint를 강제한다.

fatal/error 등급(pylint 종료코드 bit 1,2) 이슈가 있으면 재작업을 요청하고,
warning/refactor/convention 등급은 경고만 표시한다. docstring 관련 규칙은
프로젝트의 '불필요한 주석/문서화 금지' 방침과 충돌하므로 비활성화한다.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
DISABLED_CHECKS = (
    "missing-module-docstring,missing-function-docstring,missing-class-docstring,"
    "missing-docstring"
)
FATAL_OR_ERROR_MASK = 0b11  # pylint exit code bit1=fatal, bit2=error


def get_file_path(payload: dict) -> str:
    tool_input = payload.get("tool_input", {})
    if tool_input.get("file_path"):
        return tool_input["file_path"]
    return payload.get("tool_response", {}).get("filePath", "")


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    file_path = get_file_path(payload)
    if not file_path.endswith(".py"):
        return

    path = Path(file_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        return

    if shutil.which("pylint") is None:
        print(json.dumps({
            "systemMessage": (
                "pylint이 설치되어 있지 않아 검사를 건너뜁니다. "
                "'pip install pylint'로 설치하세요."
            )
        }, ensure_ascii=False))
        return

    proc = subprocess.run(
        ["pylint", f"--disable={DISABLED_CHECKS}", "--output-format=text", str(path)],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    output = (proc.stdout + proc.stderr).strip()
    rc = proc.returncode

    if rc == 0:
        return

    rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    truncated = output[:2000]

    if rc & FATAL_OR_ERROR_MASK:
        reason = f"{rel}: pylint에서 fatal/error가 발견되었습니다.\n{truncated}\n수정 후 다시 시도하세요."
        print(json.dumps({
            "decision": "block",
            "reason": reason,
            "systemMessage": reason,
        }, ensure_ascii=False))
    else:
        print(json.dumps({
            "systemMessage": f"pylint 경고(warning/refactor/convention) - {rel}\n{truncated}",
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
