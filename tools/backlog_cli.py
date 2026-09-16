#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Graphify backlog.json 조회/수정/추가 CLI.

의존성: Python 표준 라이브러리만 사용.
backlog.json의 status_legend / phase_legend를 그대로 검증 기준으로 사용한다.
(값을 이 스크립트에 중복 정의하지 않음 — legend는 backlog.json이 유일한 출처.)

사용 예:
    python tools/backlog_cli.py list
    python tools/backlog_cli.py list --status todo --phase P2
    python tools/backlog_cli.py show T014
    python tools/backlog_cli.py add --phase P2 --title "..." --description "..." \
        --acceptance "기준1" --acceptance "기준2" --depends-on T013,T014
    python tools/backlog_cli.py update T014 --status in_progress
    python tools/backlog_cli.py set-status T014 review
    python tools/backlog_cli.py validate
"""
import argparse
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

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")


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


def doc_markdown(task: dict, status_legend: dict, phase_legend: dict) -> str:
    deps = ", ".join(task["depends_on"]) if task["depends_on"] else "없음"
    sections = (
        ", ".join(f"{s}절" for s in task["problem_md_sections"])
        if task["problem_md_sections"]
        else "-"
    )
    acc = "\n".join(f"- {a}" for a in task["acceptance_criteria"]) or "- (미정)"
    phase_title = phase_legend.get(task["phase"], task["phase"])
    status_title = status_legend.get(task["status"], task["status"])
    lines = [
        f"# {task['id']} {task['title']}",
        "",
        f"- 단계: {task['phase']} ({phase_title})",
        f"- 상태: {task['status']} ({status_title})",
        f"- 예상 소요: {task['estimated_minutes']}분",
        f"- 선행 작업: {deps}",
        f"- 참고 problem.md: {sections}",
        "",
        "## 설명",
        "",
        task["description"],
        "",
        "## 완료 기준",
        "",
        acc,
    ]
    if task.get("notes"):
        lines += ["", "## 비고", "", task["notes"]]
    lines.append("")
    return "\n".join(lines)


def write_doc(data: dict, task: dict) -> None:
    doc_path = ROOT / task["doc"]
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(
        doc_markdown(task, data["status_legend"], data["phase_legend"]),
        encoding="utf-8",
    )


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


# ---------------------------------------------------------------------------
# 하위 명령
# ---------------------------------------------------------------------------

def cmd_list(args, data):
    tasks = data["tasks"]
    if args.status:
        tasks = [t for t in tasks if t["status"] == args.status]
    if args.phase:
        tasks = [t for t in tasks if t["phase"] == args.phase]
    if args.depends_on:
        tasks = [t for t in tasks if args.depends_on in t["depends_on"]]
    if args.q:
        needle = args.q.lower()
        tasks = [
            t for t in tasks
            if needle in t["title"].lower() or needle in t["description"].lower()
        ]

    tasks = sorted(tasks, key=lambda t: t["id"])

    if args.json:
        print(json.dumps(tasks, ensure_ascii=False, indent=2))
        return

    if not tasks:
        print("(조건에 맞는 작업 없음)")
        return

    id_w = max(len(t["id"]) for t in tasks)
    status_w = max(len(t["status"]) for t in tasks)
    for t in tasks:
        print(
            f"{t['id']:<{id_w}}  {t['phase']:<4} "
            f"{t['status']:<{status_w}}  {t['estimated_minutes']:>3}분  {t['title']}"
        )
    print(f"\n총 {len(tasks)}건")


def cmd_show(args, data):
    t = find_task(data, args.id)
    print(json.dumps(t, ensure_ascii=False, indent=2))
    doc_path = ROOT / t["doc"]
    print(f"\n--- 문서 ({doc_path}) ---\n")
    if doc_path.exists():
        print(doc_path.read_text(encoding="utf-8"))
    else:
        print("(문서 파일 없음 — validate로 확인하세요)")


def cmd_add(args, data):
    require_status(data, args.status)
    require_phase(data, args.phase, args.new_phase_title)
    depends_on = parse_csv(args.depends_on)
    require_depends_exist(data, depends_on)
    sections = parse_csv(args.sections)
    acceptance = args.acceptance or []
    if not acceptance:
        sys.exit("최소 1개 이상의 --acceptance (완료 기준)를 지정하세요.")

    task_id = next_id(data)
    task = {
        "id": task_id,
        "phase": args.phase,
        "phase_title": data["phase_legend"][args.phase],
        "title": args.title,
        "description": args.description,
        "status": args.status,
        "doc": f"backlog/{task_id}.md",
        "estimated_minutes": args.minutes,
        "depends_on": depends_on,
        "problem_md_sections": sections,
        "acceptance_criteria": acceptance,
        "notes": args.notes,
        "created_at": today(),
        "updated_at": today(),
    }
    data["tasks"].append(task)
    data["updated_at"] = today()
    write_doc(data, task)
    save_backlog(data)
    print(f"추가됨: {task_id}  ({task['doc']})")


def cmd_update(args, data):
    t = find_task(data, args.id)
    changed = False

    if args.status is not None:
        require_status(data, args.status)
        t["status"] = args.status
        changed = True
    if args.title is not None:
        t["title"] = args.title
        changed = True
    if args.description is not None:
        t["description"] = args.description
        changed = True
    if args.minutes is not None:
        t["estimated_minutes"] = args.minutes
        changed = True
    if args.phase is not None:
        require_phase(data, args.phase, args.new_phase_title)
        t["phase"] = args.phase
        t["phase_title"] = data["phase_legend"][args.phase]
        changed = True
    if args.sections is not None:
        t["problem_md_sections"] = parse_csv(args.sections)
        changed = True
    if args.notes is not None:
        t["notes"] = args.notes if args.notes != "" else None
        changed = True

    if args.add_depends:
        new_ids = parse_csv(args.add_depends)
        require_depends_exist(data, new_ids)
        for i in new_ids:
            if i == t["id"]:
                sys.exit("작업은 자기 자신에 의존할 수 없습니다.")
            if i not in t["depends_on"]:
                t["depends_on"].append(i)
        changed = True
    if args.remove_depends:
        for i in parse_csv(args.remove_depends):
            if i in t["depends_on"]:
                t["depends_on"].remove(i)
        changed = True

    if args.add_acceptance:
        t["acceptance_criteria"].append(args.add_acceptance)
        changed = True
    if args.remove_acceptance_index is not None:
        idx = args.remove_acceptance_index
        if 0 <= idx < len(t["acceptance_criteria"]):
            t["acceptance_criteria"].pop(idx)
            changed = True
        else:
            sys.exit(f"acceptance_criteria 인덱스 범위 초과: {idx}")

    if not changed:
        print("변경 사항 없음 (옵션을 지정하세요: --status, --title, --add-depends 등)")
        return

    t["updated_at"] = today()
    data["updated_at"] = today()
    write_doc(data, t)
    save_backlog(data)
    print(f"갱신됨: {t['id']}")


def cmd_set_status(args, data):
    t = find_task(data, args.id)
    require_status(data, args.status)
    t["status"] = args.status
    if args.note:
        t["notes"] = (t["notes"] + "\n" + args.note) if t.get("notes") else args.note
    t["updated_at"] = today()
    data["updated_at"] = today()
    write_doc(data, t)
    save_backlog(data)
    print(f"{t['id']} 상태 변경 -> {args.status}")


def cmd_validate(args, data):
    problems = []
    ids = [t["id"] for t in data["tasks"]]
    seen = set()
    for i in ids:
        if i in seen:
            problems.append(f"중복 id: {i}")
        seen.add(i)

    id_set = set(ids)
    for t in data["tasks"]:
        if t["status"] not in data["status_legend"]:
            problems.append(f"{t['id']}: 알 수 없는 status '{t['status']}'")
        if t["phase"] not in data["phase_legend"]:
            problems.append(f"{t['id']}: 알 수 없는 phase '{t['phase']}'")
        for dep in t["depends_on"]:
            if dep not in id_set:
                problems.append(f"{t['id']}: 존재하지 않는 depends_on '{dep}'")
            if dep == t["id"]:
                problems.append(f"{t['id']}: 자기 자신에 의존함")
        doc_path = ROOT / t["doc"]
        if not doc_path.exists():
            problems.append(f"{t['id']}: 문서 파일 없음 ({t['doc']})")

    if problems:
        print(f"문제 {len(problems)}건 발견:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    else:
        print(f"정상: 작업 {len(data['tasks'])}건, 문제 없음")


def cmd_sync_docs(args, data):
    for t in data["tasks"]:
        write_doc(data, t)
    print(f"문서 재생성 완료: {len(data['tasks'])}건")


# ---------------------------------------------------------------------------
# argparse 구성
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Graphify backlog.json CLI")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("list", help="작업 목록 조회")
    sp.add_argument("--status")
    sp.add_argument("--phase")
    sp.add_argument("--depends-on", help="이 id에 의존하는 작업만 표시")
    sp.add_argument("--q", help="title/description 부분 검색")
    sp.add_argument("--json", action="store_true", help="JSON 원본 출력")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("show", help="작업 상세 + 문서 내용 조회")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("add", help="새 작업 추가 (id는 자동 부여)")
    sp.add_argument("--phase", required=True)
    sp.add_argument("--new-phase-title", help="phase가 새 값이면 legend에 등록할 제목")
    sp.add_argument("--title", required=True)
    sp.add_argument("--description", required=True)
    sp.add_argument("--status", default="todo")
    sp.add_argument("--minutes", type=int, default=30)
    sp.add_argument("--depends-on", default="", help="쉼표로 구분된 선행 작업 id")
    sp.add_argument("--sections", default="", help="쉼표로 구분된 problem.md 섹션 번호")
    sp.add_argument("--acceptance", action="append", help="완료 기준 (여러 번 지정 가능)")
    sp.add_argument("--notes", default=None)
    sp.set_defaults(func=cmd_add)

    sp = sub.add_parser("update", help="기존 작업 필드 수정")
    sp.add_argument("id")
    sp.add_argument("--status")
    sp.add_argument("--title")
    sp.add_argument("--description")
    sp.add_argument("--minutes", type=int)
    sp.add_argument("--phase")
    sp.add_argument("--new-phase-title")
    sp.add_argument("--sections", help="쉼표로 구분, 전체 교체")
    sp.add_argument("--notes", help="전체 교체 (빈 문자열이면 삭제)")
    sp.add_argument("--add-depends", help="쉼표로 구분된 추가할 선행 작업 id")
    sp.add_argument("--remove-depends", help="쉼표로 구분된 제거할 선행 작업 id")
    sp.add_argument("--add-acceptance", help="완료 기준 1개 추가")
    sp.add_argument("--remove-acceptance-index", type=int, help="완료 기준 인덱스(0부터) 제거")
    sp.set_defaults(func=cmd_update)

    sp = sub.add_parser("set-status", help="상태만 빠르게 변경")
    sp.add_argument("id")
    sp.add_argument("status")
    sp.add_argument("--note", help="notes에 추가할 한 줄 사유")
    sp.set_defaults(func=cmd_set_status)

    sp = sub.add_parser("validate", help="backlog.json 무결성 검사")
    sp.set_defaults(func=cmd_validate)

    sp = sub.add_parser("sync-docs", help="모든 backlog/<id>.md를 backlog.json 기준으로 재생성")
    sp.set_defaults(func=cmd_sync_docs)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    data = load_backlog()
    args.func(args, data)


if __name__ == "__main__":
    main()
