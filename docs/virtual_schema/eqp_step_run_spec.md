# 가상 eqp_step / run_spec 스키마 (T007)

> **이 문서는 개발·검증용 가상 스키마이며 회사 실제 데이터 구조가 아니다.**
> 회사 실제 `eqp_step`/`run_spec`의 필드, 키, 값 체계는 미확인 상태다
> (problem.md 10절). 직렬화 형식(중첩 배열)도 개발 편의상 선택일 뿐 실제
> 입력 파일 형식을 가정하지 않는다 — 원본이 평면 테이블일 수도 있다.

## run_spec과 eqp_step의 관계

- problem.md 3절은 "`run_spec`과 `eqp_step`은 전체 사양이며"라고 **둘을
  나란히** 언급할 뿐, 어느 쪽이 상위인지·포함 관계인지는 말하지 않는다.
  **이 문서는 `run_spec`이 `eqp_step`을 포함한다거나 그 상위 개념이라고
  확정하지 않는다** — 그런 계층 관계는 미확인이다. 이 문서는 `eqp_step`
  (공정·step별 resource-설비 가능 관계)만 정의하고, `run_spec`의 필드는
  전혀 다루지 않는다. `run_spec` 스키마를 정의하는 backlog 작업은 현재
  없다 — 이 공백은 T007의 범위로 메우지 않았고, 별도로 확인이 필요한
  채로 남는다.
- `eqp_step`은 **전체 사양**이다. 모든 행을 축소 결과에 표현할 필요는
  없다. 이번 분석의 기준은 `lot_data`(`docs/virtual_schema/lot_data.md`)이고,
  `eqp_step`은 lot이 참조할 때 조회하는 참조 테이블로 다룬다. **다만
  "lot이 필요한 사양을 찾을 때 eqp_step을 1-hop만 조회하면 충분한지"는
  이 문서가 정하는 게 아니다** — 연결 탐색 범위 자체가 미결 사항이다
  (problem.md 10절 "필요한 사양 항목을 보존하는 정확한 단위와 연결 탐색
  범위").
- `resource`의 세부 속성은 이 문서에서 정의하지 않는다
  (`docs/virtual_schema/resource_data.md`에서 별도 정의, 중복 방지).
  여기서는 `resource_id`를 문자열 키로만 참조한다.
- **`eqp_step` 행과 (eqp, resource) 쌍의 관계.** 한 행
  `{process_id, step_id, resource_id, eligible_eqp_ids}` 는 개념적으로
  `eligible_eqp_ids`의 각 원소 `e`에 대한 `(e, resource_id)` 쌍의 집합과
  같다 — `lot_data.md`가 말하는 "가능 쌍"과 같은 단위다. 이 동치 관계가
  있어야 "lot의 어떤 쌍이 `eqp_step`에 있는지/없는지"를 판정할 수 있다.

## 필드 정의: eqp_step

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| `process_id` | string | 공정 id (가상). 실제로 이 필드가 존재하는지, `lot_data`가 이 값을 알고 있는지는 미확인이다(아래 "표현하지 않는 것" 참고). |
| `step_id` | string | 공정 내 step id (가상). 같은 `step_id`가 여러 `process_id`에 나타날 수 있음. |
| `resource_id` | string | 이 step에서 사용 가능한 resource id (가상 키. 속성은 `docs/virtual_schema/resource_data.md` 참고). |
| `eligible_eqp_ids` | array of string | 이 (`process_id`, `step_id`, `resource_id`) 조합에서 가능한 설비(eqp) id 목록. 순서에는 의미를 두지 않는다(집합으로 취급). |

**빈 배열 vs 행 자체의 부재 — 구분되지 않는다(미결).** `eligible_eqp_ids`가
빈 배열인 행("이 조합은 명시적으로 불가")과, 그 조합의 행 자체가
`eqp_step`에 없는 경우("사양에 정의돼 있지 않음")를 이 문서는 같은
것으로도 다른 것으로도 확정하지 않는다. 두 상태를 같게 볼지 다르게 볼지에
따라 "lot의 가능 쌍이 eqp_step과 충돌하는가"의 판정이 달라진다
(problem.md 7절 "아직 정하지 않은 오류 정책"에 "빈 가능 쌍"이 테스트
대상으로 명시된 사례) — 이 구분은 충돌 탐지 로직을 만들 때 반드시 먼저
정해야 한다.

**유일성 가정과 그 한계:** 동일한 (`process_id`, `step_id`, `resource_id`)
조합은 `eqp_step` 안에서 한 번만 나타난다고 가정한다. 같은 조합이 여러
행에 중복해서 나타나는 경우의 처리 정책은 **이 문서에서 정하지 않는다**
— problem.md 7절 "아직 정하지 않은 오류 정책"(중복 ID 등, 실제 처리
정책은 별도로 확정해야 한다)에 속하는 사례로 남겨둔다. `lot_data.md`가
lot_id 중복 정책을 T054로 미룬 것과 같은 방식이다.

동일한 (`process_id`, `step_id`) 아래 여러 `resource_id` 행이 있을 수
있고, 각 행의 `eligible_eqp_ids`는 서로 다를 수 있다 — 즉 같은 step이라도
resource별로 가능한 설비 집합이 다르다.

**`step_id` 단독 조회의 비결정성(미결, 차단 사항).** `step_id`가 여러
`process_id`에 걸쳐 나타날 수 있다는 것과, `lot_data.current_step`에
`process_id`가 없어 조인 키가 미확인이라는 것을 함께 보면: `lot_data`가
`step_id`만으로 `eqp_step`을 조회하면 서로 다른 `eligible_eqp_ids`를 가진
여러 행이 나올 수 있다. 이 경우 그 행들을 합칠지, 오류로 볼지, 공정별로
분리해서 다룰지는 이 문서도 다른 어떤 문서도 정하지 않았다. **조인 키가
확정되기 전까지, 이 스키마를 실제로 소비하는 로직(예: 충돌 탐지)은
결정적으로 구현할 수 없다** — problem.md 10절의 미결 사항이며, 임의로
합집합/우선순위 등을 정해 넘기지 않는다.

## 예시 JSON

```json
{
  "eqp_step": [
    { "process_id": "P01", "step_id": "S01", "resource_id": "R01", "eligible_eqp_ids": ["M01", "M02"] },
    { "process_id": "P01", "step_id": "S01", "resource_id": "R02", "eligible_eqp_ids": ["M03"] }
  ]
}
```

이 예시는 problem.md 3절의 사례("같은 S01이라도 R01은 M01·M02에서
가능하고, R02는 M03에서만 가능")를 그대로 반영한다.

## 이 문서가 표현하지 않는 것

- `run_spec`의 세부 필드(공정 순서, 상위 라우팅 등) — 정의하는 backlog
  작업이 현재 없는 공백이다(위 "run_spec과 eqp_step의 관계" 참고).
- `resource_id`가 가리키는 resource의 속성 —
  `docs/virtual_schema/resource_data.md`에서 정의.
- **`eqp_id`(설비)의 마스터 스키마.** `eqp_step`도 `lot_data.md`도
  `eqp_id`를 "설비 마스터를 참조하는 문자열"이라고만 적고, 그 마스터
  자체를 정의하는 문서가 없다 — P1 스키마 작업 목록에 설비 마스터
  스키마 정의 작업이 없는 공백이다. 생성 로직(T012)이 실제로 이 마스터를
  어떤 구조로 만들지는 이 문서 범위 밖이다.
- **lot_data와 잇는 실제 조인 키를 확정하지 않는다.**
  `docs/virtual_schema/lot_data.md`의 `current_step`은 `step_id`만 두고
  `process_id`가 없다 — lot이 이 테이블을 조회할 때 `step_id` 단독으로
  조인하는지 (`process_id`, `step_id`) 조합이 필요한지는 미확인이며, 이
  문서는 그 조인 키를 확정한 것이 아니다. 실제로는 이 필드가 존재하지
  않거나 이름이 다를 수 있다. 이 미확정의 실질적 귀결은 위 "`step_id`
  단독 조회의 비결정성" 절 참고.
- `eqp_step`에 없는 (eqp, resource) 조합이 `lot_data`에 나타나는 경우의
  처리 정책 — problem.md 7절("lot 정보와 전체 사양의 충돌": lot 정보를
  우선 유지하고 충돌 내역만 표시) 참고, 이 스키마 문서 범위 밖. 이런
  불일치를 탐지하는 로직은 별도 작업(lot-eqp_step 사양 불일치 케이스
  주입, 사양 충돌 내역 표시 — backlog에서 검색)의 몫이며, 그 로직은 위
  "빈 배열 vs 행 자체의 부재" 구분을 먼저 확정해야 구현 가능하다.
- **존재하지 않는 참조 두 가지를 구분한다.** (i) `resource_id`가
  `resource_data`에 없는 경우(행 자체의 무결성 문제)와 (ii)
  `eligible_eqp_ids` 안의 어떤 `eqp_id`가 설비 마스터에 없는 경우(목록
  원소의 무결성 문제)는 서로 다른 문제이며, 이 문서는 둘 다 검증/처리
  정책을 정하지 않는다 — problem.md 7절 "아직 정하지 않은 오류 정책"에
  해당한다.
- 위치·층 정보 — `docs/virtual_schema/location_floor.md`에서 별도
  테이블로 정의.
