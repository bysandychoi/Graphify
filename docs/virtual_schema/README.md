# 가상 데이터 스키마 (T006~T010)

**이 폴더에 있는 스키마 문서(이 README 제외)는 모두 개발·검증용
가상 스키마다. 회사 실제 데이터 구조가 아니다.** 회사 데이터는 외부로
반출할 수 없으므로(problem.md 2절), 이 저장소의 개발·검증은 여기 정의한
가상 스키마로 하고, 실제 회사 데이터에 대한 테스트와 스키마 적합성
확인은 사용자가 회사 환경에서 직접 수행한다(problem.md 8절, AGENTS.md
"가상 데이터 원칙"). 이 한 문단이 이 README의 구분 문구다 — 아래 4개
문서도 각자 상단에 같은 취지의 배너를 따로 갖고 있으며, 그 문구 자체를
여기서 다시 옮겨 적지는 않는다.

이 폴더의 문서 목록은 `AGENTS.md`의 "문서 구조" 표에도 있다 — 새 가상
스키마 문서를 추가하면 두 곳 모두 갱신해야 한다(아직 자동으로 동기화되지
않는다).

## 문서 목록

각 문서가 실제로 무엇을 보장하는지는 이 표가 아니라 **문서 원문과
`python tools/backlog_cli.py show T0xx`의 완료 기준**을 따른다 — 아래는
탐색을 돕는 한 줄 설명일 뿐이다.

| 문서 | 정의 대상 |
| --- | --- |
| [`lot_data.md`](lot_data.md) | lot의 현재 step·가능 (eqp, resource) 쌍·선택 속성 (T006) |
| [`eqp_step_run_spec.md`](eqp_step_run_spec.md) | 공정·step별 resource-설비 가능 관계(`eqp_step`만; `run_spec` 필드는 다루지 않음) (T007) |
| [`resource_data.md`](resource_data.md) | resource id와 최소 속성 (T008) |
| [`location_floor.md`](location_floor.md) | lot 현재 위치·설비 층 연결 (T009) |

## 문서 간 관계 — 실제로 적혀 있는 것만

- `lot_data`가 분석의 기준이다. `eqp_step_run_spec`은 lot이 필요할 때
  조회하는 참조 테이블로 다루지만, **"1-hop 조회로 충분한지"는
  `eqp_step_run_spec.md`가 스스로 미결 사항으로 남겨뒀다** — 이 README도
  확정하지 않는다.
- `resource_data`는 `lot_data`와 `eqp_step_run_spec` **양쪽 모두**에서
  참조된다(둘 중 하나가 아니다).
- 문자열 참조 규칙(대소문자 구분, exact match)은 `resource_data.md`가
  정의했고, `location_floor.md`는 그 규칙을 명시적으로 채택한다고
  적었다. **`lot_data.md`와 `eqp_step_run_spec.md`는 "문자열로 참조한다"고만
  하고 이 exact-match 규칙 자체를 선언하지는 않는다** — 네 문서가
  같은 규칙을 쓴다고 아직 다 같이 명시된 것은 아니다.
- `resource_id`(`resource_data.md`)와 `lot_id`/`eqp_id`(`location_floor.md`)는
  ID 변경(T048/T049) 대상이라고 해당 문서에 적혀 있다. **`lot_data.md`와
  `eqp_step_run_spec.md`에는 이 내용이 없다** — `eqp_step_run_spec`이
  들고 있는 `resource_id`/`eligible_eqp_ids`도 ID 변경 시 갱신 대상일
  가능성이 높지만, 그 문서 자신은 아직 언급하지 않은 공백이다.
- `location_floor.md`는 오류·누락 처리를 두 갈래로 나눈다: **이미
  정해진 정책**(위치·층 정보를 못 찾으면 표본 선택을 진행하지 않고
  확인을 요청, T053)과 **아직 정하지 않은 정책**(중복 lookup 값, 설비
  마스터가 생겼을 때의 존재 여부 검증 등, T054). 나머지 세 문서가
  problem.md 7절로 미룬 항목들은 대부분 후자(T054)에 속한다 — 예를
  들어 `lot_data.md`는 빈 `candidate_pairs`를 이미 유효한 값으로
  확정했으므로, "빈 가능 쌍"이 전부 미결인 것은 아니다.
- 설비 마스터 스키마와 `run_spec`의 세부 필드는 정의하는 문서가 없다
  (`eqp_step_run_spec.md` "표현하지 않는 것" 참고) — 이 공백을 이
  README가 메우지 않는다.

## 아직 결정적으로 구현할 수 없는 것 (가장 비용이 큰 미결)

- `lot_data`와 `eqp_step_run_spec`을 잇는 실제 조인 키(step 단독인지
  (공정, step) 조합인지)가 미확인이다. `lot_data.md`는 이를 별도 미결
  사항으로 남긴다고만 적었고, `eqp_step_run_spec.md`는 더 강하게 —
  **이 키가 확정되기 전까지는 이 스키마를 소비하는 충돌 탐지 로직을
  결정적으로 구현할 수 없다**고 적었다. 이 README도 그 조인 키를
  확정하지 않는다.

## 이 문서가 확정하지 않는 것

- 실제 회사 데이터의 필드, 키, 값 체계 — 4개 문서 전부 problem.md
  3절/10절 기준 미확인 상태를 유지한다.
- 위 "문서 간 관계"·"아직 결정적으로 구현할 수 없는 것"에 나열한 모든
  공백과 미결 사항 — 이 README가 대신 정하지 않는다.
