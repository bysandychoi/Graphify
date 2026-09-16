# 가상 resource_data 스키마 (T008)

> **이 문서는 개발·검증용 가상 스키마이며 회사 실제 데이터 구조가 아니다.**
> 실제 `resource_data`의 필드와 연결 키는 **미확인**이다(problem.md 3절:
> "resource_data의 실제 필드와 연결 키는 미확인이다"). 직렬화 형식(중첩
> 배열)도 개발 편의상 선택일 뿐 실제 입력 파일 형식을 가정하지 않는다.

## 목적

`docs/virtual_schema/lot_data.md`(`candidate_pairs`)와
`docs/virtual_schema/eqp_step_run_spec.md`(`resource_id`)가 참조할 최소한의
resource 마스터를 정의한다. 실제 연결 키 구조를 추정해 확정하지 않고,
가상 스키마 내부에서만 유효한 임시 식별자·속성을 둔다.

## 연결 방식

- 연결 키는 `resource_id`(문자열) 하나뿐이다. 별도 FK나 숫자 ID, 코드
  테이블은 두지 않는다.
- `lot_data`의 `candidate_pairs[].resource`와 `eqp_step`의 `resource_id`는
  이 표의 `resource_id` 값과 문자열 일치로 참조한다 — 인덱스나 대리키가
  아니라 문자열 자체가 참조 수단이다. `lot_data.md`(`candidate_pairs[].resource`
  설명)와 `eqp_step_run_spec.md`(`resource_id` 설명)도 동일한 방식을
  전제한다고 적어뒀다 — 세 문서가 같은 방식을 **일관되게** 쓰는 것이
  완료 기준이며, 이 문서 혼자 "이름으로만 참조한다"고 선언하는 것만으로
  완료 기준이 증명되지는 않는다.
- **문자열 일치의 정의:** 대소문자를 구분하고, 앞뒤 공백을 trim하지 않는
  정확한 일치(exact match)로 가정한다. `"R01"`과 `"r01"`, `"R01 "`은 서로
  다른 resource로 취급한다. 이 가정이 실제 데이터에서도 맞는지는 미확인이며,
  틀렸다면 참조 무결성 검증(존재하지 않는 참조 탐지, T054) 결과가 달라진다.
- 이 표는 `resource_id`마다 정확히 한 행만 있다고 가정한다. 중복
  `resource_id`가 있는 경우의 처리 정책은 이 문서에서 정하지 않는다 —
  problem.md 7절 "아직 정하지 않은 오류 정책"(중복 ID)에 속하는 사례로,
  T054(기타 입력 오류 탐지 로직, 정책 미정)로 남겨둔다.
- **`resource_id`는 ID 변경 대상이다.** problem.md 5절: "변경하는 모든
  ID의 원본↔변경 대응표를 실행 환경 안에 별도로 남긴다"(T049)이고,
  "변경 대상의 ID를 일관되게 바꾸고, 데이터 간 참조도 함께 갱신한다"(T048).
  `resource_id`를 바꿀 때는 이 표의 행뿐 아니라 `lot_data.candidate_pairs[].resource`와
  `eqp_step.resource_id`도 같은 새 값으로 함께 갱신해야 하며, 그래야
  이 문서의 "일관되게 참조됨"이 변경 후에도 유지된다. 원본↔변경 대응표
  자체는 이 문서가 아니라 T048/T049의 산출물이다.

## 필드

| 필드명 | 타입 | 설명 | 비고 |
| --- | --- | --- | --- |
| `resource_id` | string | 유일 식별자, 다른 가상 스키마와의 유일한 연결 수단. **ID 변경 대상**(위 "연결 방식" 참고). | 가상 예시: `"R01"`, `"R02"` — 이 형식이 실제 id 체계라고 가정하지 않는다. |
| `resource_type` | string (선택, 개발용 예시) | resource 분류값. **이것은 ID가 아니다** — problem.md 5절 "공통 코드나 분류값을 임의로 ID로 취급하지 않는다"에 따라, ID 변경(T048) 대상에서 제외하고 값 자체를 그대로 유지한다. | 가상 예시: `"tool"`, `"fixture"` 중 하나. 실제로 이런 분류 필드가 있는지는 미확인 — 없다면 로직이 이 필드 존재를 전제하면 안 된다(problem.md 5절 "실제로 없는 속성은 사용하지 않는다"). |
| `resource_name` | string (선택, 개발용 예시) | 사람이 읽는 표시용 이름. **`resource_id`에서 기계적으로 유도하지 않는다** — 유도된 이름(예: id가 `R01`이라 이름도 `Resource 01`)은 ID 변경 후 이름과 id가 서로 모순되게 되고, 원본 id의 흔적이 이름에 남아 대응표 분리 취지를 해친다. | 가상 예시: `"Coating Head"`, `"Wafer Clamp"`처럼 id와 무관한 이름을 쓴다. |

`resource_type`과 `resource_name`은 최소 속성 예시일 뿐이며, 실제 회사
`resource_data`에 이런 필드가 존재한다고 가정하지 않는다.

## 예시 JSON

```json
{
  "resources": [
    { "resource_id": "R01", "resource_type": "tool", "resource_name": "Coating Head" },
    { "resource_id": "R02", "resource_type": "tool", "resource_name": "Etch Head" },
    { "resource_id": "R03", "resource_type": "fixture", "resource_name": "Wafer Clamp" }
  ]
}
```

빈 배열(`"resources": []`)도 유효한 값이다 — 축소 과정에서 어떤 lot도
참조하지 않는 resource 행은 제외될 수 있다(problem.md 5절 "선택한 lot과
연결되지 않는 항목은 제외한다", T047). 반대로 `lot_data`/`eqp_step`이
참조하는 `resource_id`가 이 표에서 빠지면 안 된다 — 그 경우는 아래
"실제 스키마와의 차이 / 미확인 사항"의 존재하지 않는 참조 문제가 된다.

## 실제 스키마와의 차이 / 미확인 사항

- 실제 `resource_data`의 필드 구성, 연결 키(문자열/숫자/복합키 여부),
  `eqp_step`/`lot_data`와의 실제 참조 방향은 **미확인**이다(problem.md
  3절, 10절). 이 문서는 그 구조를 추정해 채우지 않는다.
- `resource_type` 같은 분류값이 실제로 존재하는지, 존재한다면 값 체계가
  무엇인지도 미확인이다. 여기 적힌 값(`tool`/`fixture`)은 테스트 데이터를
  다양화하기 위한 개발용 placeholder다.
- **`lot_data`/`eqp_step`이 참조하는 `resource_id`가 이 표에 없는 경우의
  검증/처리 정책은 정하지 않는다.** — problem.md 7절 "아직 정하지 않은
  오류 정책"(존재하지 않는 resource·설비 참조)에 해당하며, T054(기타
  입력 오류 탐지 로직, 정책 미정)로 남겨둔다.
- 이 가상 스키마는 `resource_id` 문자열 일치(위 정의한 exact match)만으로
  연결이 성립한다고 가정한다 — 실제 환경에서는 이 가정 자체가 틀릴 수
  있다(예: 대소문자 무시, 복합키 등). 이 문서는 그 가능성을 열어두기만
  하며, 실제 확인은 회사 환경에서 사용자가 한다.
- `resource_id`가 가리키는 대상이 설비(`eqp`)와 별개 개념이라는 점만
  전제한다 — `eqp` 마스터 스키마는 이 문서 범위 밖이다
  (`docs/virtual_schema/eqp_step_run_spec.md` "표현하지 않는 것" 참고).
