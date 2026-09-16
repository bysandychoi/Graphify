#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""backlog task -> backlog/<id>.md 문서 렌더링."""
from backlog_core import ROOT


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
    if task.get("plain_explanation"):
        lines += ["", "## 쉬운 설명", "", task["plain_explanation"]]
    if task.get("related_files"):
        lines += ["", "## 관련 파일", ""]
        lines += [f"- `{rf['path']}` — {rf['reason']}" for rf in task["related_files"]]
    if task.get("feedback_log"):
        lines += ["", "## 피드백 로그", ""]
        for entry in task["feedback_log"]:
            lines += [f"### {entry.get('date', '')}", "", entry.get("text", ""), ""]
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
