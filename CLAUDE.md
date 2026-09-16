# CLAUDE.md

이 저장소에서 작업하기 전에 **AGENTS.md**를 먼저 읽어라. 공통 작업 규칙
(코드 작성 규칙, backlog.json 다루는 법, 서브에이전트 사용법, 훅 동작)이
모두 거기 정리돼 있다.

너무 급하면 최소한 이것만 기억해라:

- `backlog.json`은 절대 직접 Read/Edit/Write 하지 않는다. 항상
  `python tools/backlog_cli.py ...`로 조회·수정·추가한다.
- 작업을 시작할 때는 `task-briefer` 서브에이전트를, 변경분을 검토받을
  때는 `adversarial-reviewer` 서브에이전트를 호출한다. 자세한 흐름은
  AGENTS.md의 "작업 흐름" 절 참고.
- problem.md에 "미확인"/"미정"이라고 적힌 회사 데이터 구조·정책을 추정해서
  채우지 않는다.

문제 정의는 `problem.md`, 작업 목록은 `backlog.json` (CLI로만 조회).
