# AGENTS.md — Graphify 공통 작업 규칙

이 저장소에서 작업하는 모든 에이전트(Claude, Codex, 서브에이전트 포함)가
공통으로 따라야 할 규칙을 모은 문서다. `CLAUDE.md`는 이 문서를 가리키기만
한다. 문제 정의/업무 결정은 `problem.md`, 작업 목록은 `backlog.json`을
참고한다.

## 핵심 원칙

- 회사 데이터는 외부로 반출하지 않는다. 이 저장소의 개발·검증은 가상
  데이터로 하고, 실제 회사 데이터 테스트는 사용자가 회사 환경(Codex)에서
  직접 수행한다.
- **모르는 회사 데이터 구조·정책을 추정해서 확정하지 않는다.** problem.md에
  "미확인"/"미정"이라고 적힌 부분은 그대로 미확인이라고 말한다.
- 개발은 Claude로, 실제 실행은 Codex로 한다 (목표: 2026-09-21 실제 환경
  실행·검증). 코드와 문서만으로 인수인계 가능해야 한다.
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
5. 완료되면 `python tools/backlog_cli.py set-status T0xx done` — 자동으로
   완료 요약 커밋 + push.
6. 다른 작업으로 넘어갈 땐 `clear-active` 하거나, 새 task-briefer 호출이
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
  Edit/Write가 차단된다.
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

## 가상 데이터 원칙 (problem.md 8절)

- 가상 데이터 스키마는 회사 실제 스키마와 구분해서 문서화한다.
- 초기 가상 데이터 규모 제안: lot 10,000 / 설비 80 / resource 24
  (개발용 제안치이며 확정된 기준이 아니다).

## 아직 없는 문서

`README.md`(프로젝트 개요), `HANDOFF.md`(현재 상태·가정·다음 작업)는 아직
정식으로 작성되지 않았다 — backlog의 T002, T005가 이 작업이다. 이 문서
(AGENTS.md)와 `CLAUDE.md`는 서브에이전트/훅 도입에 맞춰 먼저 만들었다.
