# AGENTS.md — Graphify 공통 작업 규칙

이 저장소에서 작업하는 모든 에이전트(Claude, Codex, 서브에이전트 포함)가
공통으로 따라야 할 규칙을 모은 문서다. `CLAUDE.md`는 이 문서를 가리키기만
한다. 문제 정의/업무 결정은 `problem.md`, 작업 목록은 `backlog.json`을
참고한다.

## 문서 구조

**`AGENTS.md`(이 문서)가 공통 작업 규칙의 단일 출처(source of truth)다.**
다른 문서는 규칙 전문을 복제하지 않고 이 문서를 가리키기만 한다(`CLAUDE.md`
포함 — 예외 없음).

아래 순서는 **사람이 프로젝트를 처음 인수인계 받을 때** 읽는 순서다. Claude
Code는 세션 시작 시 `CLAUDE.md`를 프로젝트 지침으로 자동 로드한다(도구
자체 동작이며 `SessionStart` 훅과는 별개다 — 그 훅은 현재 git 브랜치만
알려준다, 아래 "세션 시작 시" 참고). Codex는 `CLAUDE.md`를 자동으로 읽지
않으므로 `AGENTS.md`가 두 실행 환경 모두에 필요한 공통 출처다.

각 문서의 작성 여부(작성됨/미작성)는 이 표 한 곳에서만 관리한다. 표의
구성 요소 열은 지금 확정한 목차다 — README/HANDOFF는 아직 내용이 없지만
목차는 이미 정해졌고, 실제 작성은 이 목차를 채우는 일이다. 문서를 실제로
채운 사람이 그 자리에서 "(미작성)" 표시를 지운다(다른 곳에 완료 표시를
만들지 않는다).

| 순서 | 문서 | 역할 | 구성 요소 |
| --- | --- | --- | --- |
| 1 | `problem.md` | 문제 정의/업무 결정 (harness 문서 아님, 가장 먼저 읽는다) | 1.해결하려는 문제 · 2.사용자와 업무 상황 · 3.인터뷰에서 확인한 데이터의 의미 · 4.목표와 1차 범위 · 5.사용자가 확정한 축소 원칙 · 6.사용자가 판단하는 흐름 · 7.오류·불일치 처리 정책 · 8.가상 데이터 검증 계획 · 9.개발·실행 환경과 일정 · 10.미결 질문과 구현 전 확인 사항 |
| 2 | `README.md` | 프로젝트 개요, 저장소 진입점 (미작성 — 현재는 내용 없는 26바이트 placeholder 파일만 tracked돼 있음) | 프로젝트 목적 · 1차 범위/제외 범위 · 실행 방법 개요(정해지지 않았다면 '미정'이라고 명시) · 문서 구조 안내(이 절 링크, 표 복제 금지) |
| 3 | `AGENTS.md` | 공통 작업 규칙의 단일 출처 | 문서 구조 · 핵심 원칙 · backlog.json은 CLI로만 다룬다 · 작업 흐름: task-briefer → 구현 → adversarial-reviewer → 완료 · in_progress 훅 (`guard_task_in_progress.py`) · 코드 작성 규칙 · 세션 시작 시 · 응답 종료 알림 (`notify_stop_popup.py`) · 가상 데이터 원칙 (problem.md 8절) |
| 4 | `CLAUDE.md` | Claude 전용 최소 안내 (사람은 건너뛰어도 됨. 규칙 전문 없음, 링크만) | AGENTS.md 링크 안내 · problem.md/backlog.json 위치 안내 |
| 5 | `HANDOFF.md` | 현재 상태 스냅샷 (미작성). 한 phase가 전부 done되면, 그 작업이 아직 in_progress인 동안 갱신하고 같이 커밋한다(아래 "작업 흐름" 참고 — `guard_task_in_progress.py`의 예외 대상이 아니다) | 현재 상태 · 검증 결과 · 가정 · 다음 작업 · 미결 사항(problem.md 10.미결 질문과 구현 전 확인 사항 반영) |
| - | `backlog.json` / `backlog/*.md` | 작업 목록 (CLI 전용 접근) | `tools/backlog_cli.py`로만 조회 (직접 열지 않음) |

AGENTS.md/problem.md 행의 구성 요소는 실제 `##` 절 제목을 그대로 나열한
것이다. README/CLAUDE/HANDOFF 행은 아직 절이 없거나(README, HANDOFF) 절
형식이 아니므로(CLAUDE, 안내문 2문단) 지금 확정한 구성 요소를 나열했다.

## 핵심 원칙

- 회사 데이터는 외부로 반출하지 않는다. 이 저장소의 개발·검증은 가상
  데이터로 하고, 실제 회사 데이터 테스트는 사용자가 회사 환경(Codex)에서
  직접 수행한다.
- **모르는 회사 데이터 구조·정책을 추정해서 확정하지 않는다.** problem.md에
  "미확인"/"미정"이라고 적힌 부분은 그대로 미확인이라고 말한다.
- 개발은 Claude로, 실제 실행은 Codex로 한다 (목표: 2026-09-21 실제 환경
  실행·검증, problem.md 9절). 코드와 문서만으로 인수인계 가능해야 한다.
- 간단한 구조, 최소 의존성을 우선한다. Python 표준 라이브러리를 우선 쓴다.

## backlog.json은 CLI로만 다룬다

- `backlog.json`을 Read/Edit/Write로 직접 열거나 셸에서 `cat`/`type` 등으로
  보지 않는다 — 훅(`guard_backlog_direct_access.py`, `guard_backlog_bash.py`)이
  차단한다.
- 조회·수정·추가는 전부 `python tools/backlog_cli.py ...`로 한다:
  `list / show / add / update / set-status / start / active / clear-active /
  validate / sync-docs`.
- `backlog.json`이 바뀌면 훅(`backlog_auto_commit.py`)이 자동으로 커밋한다.
  작업 status가 `done`으로 바뀌면 변경 내역을 요약해 자동으로 커밋 + push까지
  한다.

## 작업 흐름: task-briefer → 구현 → adversarial-reviewer → 완료

1. 다음 작업 고르기: `python tools/backlog_cli.py list --status todo`
2. **task-briefer** 서브에이전트(Haiku)를 호출해 작업을 시작한다.
   예: "T0xx 작업 시작해줘"
   - 작업을 쉬운 말로 설명하고 관련 파일을 찾아 `backlog/<id>.md`에 기록한다.
   - 마지막에 `start <id>`를 실행해 상태를 `in_progress`로 바꾸고 활성
     작업으로 지정한다.
   - **이 단계 없이는 관련 코드 파일을 Edit/Write할 수 없다** (아래 in_progress
     훅 참고). 즉 작업은 반드시 task-briefer로 시작해야 한다.
3. 실제 구현 작업을 한다.
4. 의미 있는 변경이 쌓이면 **adversarial-reviewer** 서브에이전트(Opus)를
   호출해 비판적으로 검토받는다. 예: "T0xx 변경사항 리뷰해줘"
   - 지적 사항은 `backlog/<id>.md`의 피드백 로그에 자동으로 남는다.
   - 지적을 반영하거나, 반영하지 않기로 했다면 그 이유를 남긴다(notes 등).
5. **`set-status done`을 실행하기 전에, 이번 작업에서 바꾼 backlog.json/
   `backlog/` 외의 모든 파일을 직접 커밋한다** (`git add <파일들>` +
   `git commit`). `backlog_auto_commit.py`는 `backlog.json`과 `backlog/`만
   자동으로 stage/커밋하므로, 그 외 소스·문서 변경분은 이 단계에서 커밋하지
   않으면 backlog는 done인데 실제 파일은 저장소에 반영되지 않은 상태로
   남는다. 이 phase(P0, P1, ...)의 마지막 작업이라 `HANDOFF.md`를 갱신해야
   한다면, 그 작업이 아직 `in_progress`인 이 시점에 갱신해서 같이 커밋한다
   (in_progress 훅은 활성 작업이 `in_progress`일 때 모든 파일의 Edit/Write를
   허용하므로 `HANDOFF.md`도 별도 예외 없이 그냥 편집할 수 있다).
6. 완료되면 `python tools/backlog_cli.py set-status T0xx done` — backlog.json
   변경을 자동으로 커밋(+ push)한다. 5단계를 건너뛰면 이 커밋에는 상태값만
   들어가고 실제 작업 내용은 빠진다.
7. 다른 작업으로 넘어갈 땐 `clear-active` 하거나, 새 task-briefer 호출이
   자동으로 활성 작업을 교체한다.

### 서브에이전트

| 이름 | 모델 | 역할 | 도구 |
| --- | --- | --- | --- |
| `task-briefer` | Haiku | 작업을 쉬운 말로 설명, 관련 파일 탐색·기록, 상태 in_progress 전환 | Read, Grep, Glob, Bash, Edit |
| `adversarial-reviewer` | Opus | 변경분을 의도적으로 비판적으로 검토, 결함 지적 | Read, Grep, Glob, Bash |

두 서브에이전트 모두 소스 코드를 직접 고치지 않는다. `adversarial-reviewer`는
Edit/Write 도구 자체가 없어 코드를 고칠 수 없다 — 비판만 하고 반영은
작업자 몫이다.

## in_progress 훅 (`guard_task_in_progress.py`)

- 활성 작업이 지정돼 있는데 그 작업 status가 `in_progress`가 아니면,
  `backlog.json`, `backlog/`, `.claude/`, `tools/hooks/`를 제외한 모든 파일의
  Edit/Write가 차단된다. `HANDOFF.md`는 예외 목록에 없다 — 갱신은 항상 어떤
  작업이 `in_progress`인 동안(작업 흐름 5단계) 끝낸다.
- 활성 작업이 아예 없으면 이 제약은 적용되지 않는다 (옵트인 — task-briefer로
  시작하지 않은 잡일까지 막지 않기 위함).
- 활성 작업 상태는 `.claude/state/active_task.json`에 세션 로컬로 저장되며
  git에 커밋하지 않는다(`.gitignore`).

## 코드 작성 규칙

- 파일 500줄 / 함수 60줄 기준. 85% 이상이면 경고, 100% 이상이면 분리해서
  다시 작성하라는 안내가 뜬다 (`check_line_limits.py`, 기준은
  `tools/hooks/limits.json`).
- `.py` 파일은 pylint를 통과해야 한다. fatal/error 등급은 차단, 그 외
  (warning/refactor/convention)는 경고만 표시된다. docstring류 규칙은 꺼져
  있다 — 이 프로젝트는 WHY가 아니면 주석/문서를 쓰지 않는다는 방침이라서다.

## 세션 시작 시

- `SessionStart` 훅이 현재 git 브랜치를 알려준다. `main`이면 `dev`로 전환할
  것을 권고한다 (자동 전환은 하지 않는다).

## 응답 종료 알림 (`notify_stop_popup.py`)

- `Stop` 훅이 Claude 응답이 끝날 때마다 Windows 팝업으로 알려준다. 활성
  작업이 있으면 `.claude/state/active_task.json` + `backlog.json`을 읽어
  "T0xx: 제목 (status)"를 같이 보여준다.
- Windows 전용(`user32.dll`, `ctypes`)이며, 실패해도 훅 등록 시 `|| true`로
  세션에 영향을 주지 않는다. 표준 라이브러리만 사용한다.

## 가상 데이터 원칙 (problem.md 8절)

- 가상 데이터 스키마는 회사 실제 스키마와 구분해서 문서화한다.
- 초기 가상 데이터 규모 제안: lot 10,000 / 설비 80 / resource 24
  (개발용 제안치이며 확정된 기준이 아니다).
