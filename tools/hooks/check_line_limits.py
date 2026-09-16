#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PostToolUse(Edit|Write) 훅: 파일/함수 최대 줄 수를 검사한다.

기준(tools/hooks/limits.json)의 85% 이상이면 경고, 100% 이상이면 재작업을
요청한다. Python(.py) 파일에만 적용한다 (limits.json의 scope).
"""
import ast
import json
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
LIMITS_PATH = Path(__file__).resolve().parent / "limits.json"


def load_limits():
    with open(LIMITS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_file_path(payload: dict) -> str:
    tool_input = payload.get("tool_input", {})
    if tool_input.get("file_path"):
        return tool_input["file_path"]
    tool_response = payload.get("tool_response", {})
    return tool_response.get("filePath", "")


def max_function_length(source: str):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None, None
    worst_len = 0
    worst_name = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno)
            length = end - node.lineno + 1
            if length > worst_len:
                worst_len = length
                worst_name = node.name
    return worst_len, worst_name


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

    limits = load_limits()
    max_file = limits["max_file_lines"]
    max_func = limits["max_function_lines"]
    warn_ratio = limits["warn_ratio"]

    source = path.read_text(encoding="utf-8")
    total_lines = len(source.splitlines())
    file_ratio = total_lines / max_file

    func_len, func_name = max_function_length(source)
    func_ratio = (func_len / max_func) if func_len else 0.0

    worst_ratio = max(file_ratio, func_ratio)
    rel_path = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path

    if worst_ratio >= 1.0:
        detail = []
        if file_ratio >= 1.0:
            detail.append(f"파일 {total_lines}/{max_file}줄")
        if func_ratio >= 1.0:
            detail.append(f"함수 '{func_name}' {func_len}/{max_func}줄")
        reason = (
            f"{rel_path}: 최대 코드 줄 수 기준(100%↑)을 초과했습니다 "
            f"({', '.join(detail)}). 함수를 분리하거나 파일을 나눠서 다시 작성하세요."
        )
        print(json.dumps({
            "decision": "block",
            "reason": reason,
            "systemMessage": reason,
        }, ensure_ascii=False))
        return

    if worst_ratio >= warn_ratio:
        detail = []
        if file_ratio >= warn_ratio:
            detail.append(f"파일 {total_lines}/{max_file}줄 ({file_ratio*100:.0f}%)")
        if func_ratio >= warn_ratio:
            detail.append(f"함수 '{func_name}' {func_len}/{max_func}줄 ({func_ratio*100:.0f}%)")
        print(json.dumps({
            "systemMessage": f"경고 - {rel_path}: {', '.join(detail)} — 기준의 85% 이상 사용",
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
