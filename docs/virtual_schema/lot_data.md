# 가상 lot_data 스키마 (T006)

> **이 문서는 개발·검증용 가상 스키마이며 회사 실제 데이터 구조가 아니다.**
> 회사 실제 `lot_data`의 필드, 키, 값 체계는 미확인 상태다(problem.md 10절).
> 이 문서의 목적은 축소 로직을 가상 데이터로 개발·검증하기 위함이며,
> 여기 정의한 필드명·타입은 전부 개발용 예시다(AGENTS.md "가상 데이터 원칙",
> problem.md 8절 참고).

## 전제

- 입력 lot은 이미 필요한 step으로 필터링된 상태로 들어온다. 즉 이 스키마의
  한 행은 "어떤 lot이 현재 처리해야 할 하나의 step"을 가리킨다.
- lot에는 **현재 진행할 step**에서 할당 가능한 `(eqp, resource)` 쌍의
  목록이 있다. 이 쌍 목록이 이 스키마의 핵심이다.

## 필드

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| `lot_id` | string | lot 식별자, **이 스키마 안에서 유일 키로 가정한다**(중복 없음). 원본 lot_id와 축소본 lot_id는 별도 대응표(problem.md 5절)로 관리하며, 이 문서는 그 대응표의 존재만 전제한다. 실제 데이터의 중복 ID 처리 정책은 problem.md 7절 기준 미정(테스트 대상, T054). |
| `current_step` | string | 이 lot이 현재 처리해야 할 step id. lot이 이미 이 step으로 필터링된 상태라는 전제를 표현한다. **공정(process) 식별자는 이 필드에 포함하지 않는다** — lot이 `eqp_step`을 조회할 때 step만으로 조인하는지 (공정, step) 조합으로 조인하는지는 미확인이며, 이 문서는 그 조인 키를 확정하지 않는다(아래 "표현하지 않는 것" 참고). |
| `candidate_pairs` | array of `{eqp: string, resource: string}` | 현재 step에서 할당 가능한 `(eqp, resource)` 쌍의 목록. `eqp`/`resource` 값은 각각 설비 마스터, `resource_data`(T008 문서)의 id를 문자열로 참조한다고 가정한다 — 존재하지 않는 id를 참조하는 경우의 처리 정책은 별도 미정(problem.md 7절, T054). 예: `[{"eqp":"M01","resource":"R01"},{"eqp":"M02","resource":"R02"}]`. 빈 배열 `[]`도 유효한 값이다(할당 가능 쌍이 없는 lot) — 이 경우 `eligible_eqp_count`는 0이다. 목록 순서에는 의미를 두지 않는다(집합으로 취급). 완전히 동일한 `{eqp, resource}` 쌍이 두 번 나타나는 경우의 처리(중복 제거 여부)는 이 문서에서 정하지 않는다 — 생성기가 중복을 만들지 않도록 하거나, 만든다면 그 정책을 생성 로직 문서(T014 이후)에 별도로 적는다. |
| `attributes` | object (선택, 개발용 예시) | 표본 선택에 반영할 수 있는 속성을 담는 확장 슬롯. **필드명·값 체계는 미확인이며, 여기 넣는 `priority` 등은 실제 필드가 아니라 개발용 예시다.** 실제 존재 여부는 problem.md 10절 미결 사항. **이 필드 안에 `eligible_eqp_count` 등 아래 파생값을 다시 저장하지 않는다** — 파생값은 항상 `candidate_pairs`에서 계산하고 별도 필드로 두지 않는다(완료 기준). |

`candidate_pairs`에서 파생되는 값(저장하지 않음):

| 파생값 | 계산 방법 |
| --- | --- |
| `eligible_eqp_count` | `candidate_pairs`의 `eqp` 값 중 **중복 없는 개수**. 같은 설비가 여러 resource와 짝지어져 나타나도 한 번만 센다. problem.md에서 말하는 "할당 가능 설비 수"(3절)와 같은 개념이다. |

## 예시 JSON

```json
{
  "lot_id": "LOT_V0001",
  "current_step": "S01",
  "candidate_pairs": [
    {"eqp": "M01", "resource": "R01"},
    {"eqp": "M02", "resource": "R02"}
  ],
  "attributes": {
    "priority": "HIGH"
  }
}
```

`attributes.priority`는 값 체계가 정해지지 않은 필드를 개발 중 채워보기 위한
예시일 뿐이다 — 이 값을 넣는 것과, 축소/생성 로직이 "모든 lot에 priority가
있다"고 전제하는 것은 다르다. 실제로 없는 속성은 로직에서 사용하지 않는다
(problem.md 5절: "실제로 없는 속성은 사용하지 않는다").

두 번째 예시 — 같은 설비에 여러 resource가 매칭되는 경우(설비 수 중복
계산 방지를 검증하기 위한 케이스):

```json
{
  "lot_id": "LOT_V0002",
  "current_step": "S01",
  "candidate_pairs": [
    {"eqp": "M03", "resource": "R01"},
    {"eqp": "M03", "resource": "R02"}
  ],
  "attributes": {}
}
```

이 예시에서 `eligible_eqp_count`는 2가 아니라 **1**이다(`M03` 하나만 존재).

## 이 문서가 표현하지 않는 것

- **쌍의 임의 조합을 암시하지 않는다.** `candidate_pairs`에 `(M01,R01)`과
  `(M02,R02)`만 있다면, `(M01,R02)`가 가능하다는 뜻이 아니다. 목록에 명시된
  쌍만 유효하다 — 이 스키마도, 이 스키마를 쓰는 로직도 명시되지 않은 조합을
  만들어내면 안 된다.
- **다음 step의 가능 쌍을 추론하지 않는다.** `current_step`의
  `candidate_pairs`만으로 이후 step에서 어떤 쌍이 가능할지 알 수 있다고
  가정하지 않는다. 다음 step 정보가 필요하면 `docs/virtual_schema/eqp_step_run_spec.md`를
  통해 별도로 조회해야 한다.
- **lot과 eqp_step을 잇는 실제 조인 키를 확정하지 않는다.** 이 문서는
  `current_step`(step id)만 두지만, 실제 `eqp_step`은 공정·step별로 관계가
  달라질 수 있다(problem.md 3절). lot이 `eqp_step`을 조회할 때 step 단독으로
  조인하는지, (공정, step) 조합이 필요한지는 미확인이며, 이 문서도
  `docs/virtual_schema/eqp_step_run_spec.md`도 그 키 구조를 확정한 것이
  아니다 — 필요하면 조회 키 자체를 별도 미결 사항으로 남긴다.
- **직렬화 형식(중첩 JSON)은 개발 편의상 선택일 뿐, 확정이 아니다.** 실제
  입력 파일 형식은 미확인이다(problem.md 10절). 원본이 `(lot, eqp, resource)`
  한 행짜리 평면 테이블일 수도 있다 — 이 문서의 중첩 배열 구조를 실제 파일
  형식으로 가정하지 않는다.
- **납기(due date) 필드가 없다.** problem.md 3절에 따르면 lot 데이터에
  납기는 없다. 우선순위 같은 속성은 대화에서 분석용으로 논의됐을 뿐 실제
  필드 존재 여부와 값 체계는 미확인이다 — 이 문서의 `attributes.priority`는
  그 미확인 사항을 확정한 것이 아니라 개발 중 값을 채워보기 위한 예시일
  뿐이다.
- **위치·층 정보를 포함하지 않는다.** lot의 현재 위치나 설비 층은 이 문서의
  범위가 아니며 별도 데이터(`docs/virtual_schema/location_floor.md`)를
  연결해야 한다(problem.md 3절 "위치와 층").
