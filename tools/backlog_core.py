#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""backlog.json 로드/저장과 검증 헬퍼 (CLI 인자 처리와 분리된 데이터 계층)."""
import json
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG_PATH = ROOT / "backlog.json"
ID_PATTERN = re.compile(r"^T(\d+)$")


def today() -> str:
    return date.today().isoformat()


def load_backlog() -> dict:
    if not BACKLOG_PATH.exists():
        sys.exit(f"backlog.json을 찾을 수 없습니다: {BACKLOG_PATH}")
    with open(BACKLOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_backlog(data: dict) -> None:
    # 저장 중 프로세스가 죽어도 backlog.json이 깨지지 않도록 임시 파일에 쓰고 교체한다.
    fd, tmp_path = tempfile.mkstemp(dir=str(ROOT), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp_path, BACKLOG_PATH)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def find_task(data: dict, task_id: str) -> dict:
    for t in data["tasks"]:
        if t["id"] == task_id:
            return t
    sys.exit(f"작업 id를 찾을 수 없습니다: {task_id}")


def next_id(data: dict) -> str:
    nums = []
    width = 3
    for t in data["tasks"]:
        m = ID_PATTERN.match(t["id"])
        if m:
            nums.append(int(m.group(1)))
            width = max(width, len(m.group(1)))
    n = (max(nums) + 1) if nums else 1
    return f"T{n:0{width}d}"


def parse_csv(value: str) -> list:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def require_status(data: dict, status: str) -> None:
    if status not in data["status_legend"]:
        valid = ", ".join(data["status_legend"].keys())
        sys.exit(f"알 수 없는 status '{status}'. 사용 가능: {valid}")


def require_phase(data: dict, phase: str, new_phase_title: str | None) -> None:
    if phase in data["phase_legend"]:
        return
    if new_phase_title:
        data["phase_legend"][phase] = new_phase_title
        return
    valid = ", ".join(data["phase_legend"].keys())
    sys.exit(
        f"알 수 없는 phase '{phase}'. 사용 가능: {valid}\n"
        f"새 phase를 추가하려면 --new-phase-title 을 함께 지정하세요."
    )


def require_depends_exist(data: dict, ids: list) -> None:
    existing = {t["id"] for t in data["tasks"]}
    missing = [i for i in ids if i not in existing]
    if missing:
        sys.exit(f"존재하지 않는 depends-on id: {', '.join(missing)}")
