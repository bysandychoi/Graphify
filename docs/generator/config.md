# 가상 데이터 생성기 config 설계 (T011)

> 이 문서는 **생성기**(가상 lot_data/eqp_step/resource_data/location_floor를
> 만드는 도구, T012~T022)가 받는 config 구조를 정의한다. **표본 선택**
> (원본에서 lot을 고르는 축소 단계, P4: T033 이후)의 config와는 다른
> 별개의 설정이다 — 이 문서는 표본 선택 config를 다루지 않는다.
>
> 이 문서는 T077([결정 필요] config 구조·실행 인터페이스·결과 파일
> 구성)이 다루는 세 가지 중 **생성기 config 구조** 한 가지만 다루는
> 개발측 설계 초안이다. 표본 선택(P4) config, 실행 CLI 인터페이스,
> 결과 파일 구성은 이 문서 범위 밖이며, 이 문서가 확정됐다고 해서
> T077 전체가 닫히는 것은 아니다.
>
> **이 문서는 두 종류의 규칙을 구분한다.** (1) "잘못된 config에 대한
> 최소 규칙"은 config 파일 하나만 보고 생성 실행 전에 기계적으로
> 판정할 수 있는 **정적 검증**이다. (2) "값 선택 지침"은 각 값이
> 실제로 실현 가능한 데이터를 만드는지에 대한 **설계 가이드**이며,
> 실현 가능 여부가 다른 `case_ratios`의 생성 결과(난수 배정)에
> 좌우되는 경우가 많아 config 파일만 보고 기계적으로 판정할 수
> 없다 — 이런 항목을 정적 검증 규칙인 것처럼 섞어 두면 스스로
> 모순되는 규칙이 된다(이전 버전의 결함). 이 둘을 구분해 표시한다.

## 전제

- 규모 기본값(lot 10,000 / 설비 80 / resource 24)은 problem.md 8절의
  **개발용 제안치**이며 회사 기준이 아니다(이 config의 기본값도 마찬가지).
- 이 config가 몇 %/몇 개 같은 구체적인 숫자를 가진 것은 이 문서가
  값 체계를 확정했다는 뜻이 아니다 — 아래 각 항목에 실제 값의 근거와
  미확인 여부를 표시한다.
- 직렬화 형식은 JSON으로 정한다(표준 라이브러리 `json`만 사용, AGENTS.md
  "최소 의존성" 원칙). YAML 등 다른 형식을 배제하는 것은 아니지만, 이
  프로젝트는 JSON을 기본으로 한다.
- **이 config의 정적 검증 규칙(아래 "잘못된 config" 절) 자체는 회사
  데이터 구조와 무관하게 이 생성기 도구가 스스로 정하는 것이다** —
  AGENTS.md "모르는 회사 데이터 구조·정책을 추정해서 확정하지
  않는다"는 원칙은 회사 실제 데이터/정책에 적용되며, 우리가 만드는
  도구 자체의 입력 검증 규칙에는 적용되지 않는다.
- **유효 lot 수.** lot 단위 비율 필드의 분모로 쓰는 "유효 lot 수"는
  `scale.factor`가 있으면 `round(scale.lot_count × scale.factor)`,
  없으면 `scale.lot_count`다. 아래 모든 "분모 = 유효 lot 수" 서술은
  실제로 생성될 lot 수를 가리키며, `scale.lot_count`(factor 적용 전
  값)를 가리키지 않는다.
- **반올림 규칙(전역).** 비율(ratio)을 실제 건수로 바꿀 때는
  "비율 × 모집단 크기"를 **사사오입(0.5 이상을 올림)** 해서 정수로
  만든다. `min_count`가 함께 있으면, 이 반올림 결과가 `min_count`보다
  작을 때만 `min_count`로 끌어올린다(그 반대로 깎지는 않는다). 같은
  필드 안의 여러 카테고리(예: `single_floor`/`multi_floor`)를 각각
  반올림하면 합이 모집단 크기와 정확히 일치하지 않을 수 있다 — 이
  오차를 어느 카테고리에서 보정할지(최대잔여법 등)는 이 문서가
  정하지 않으며, 실제 정수 배분 알고리즘은 T012 이후 구현이 정한다.
  이 문서의 비율 값은 "목표 비율"이며, 정수 단위 정확한 일치를
  보장하는 계약이 아니다.
- **"비율 또는 최소 건수" 값의 공통 형식.** 이 문서에서 "min_count
  지원"이라고 표시한 필드는 아래 네 형태 중 하나로 값을 받는다:
  1. 숫자 하나(`0.02`) — 비율만 지정, 최소 건수 보장 없음.
  2. `{"ratio": 0.02}` — 위와 동일, 객체 형태로 쓴 것.
  3. `{"min_count": 3}` — 비율은 0으로 두고(그 자체로는 아무 건수도
     만들지 않음) 최소 건수만 강제.
  4. `{"ratio": 0.02, "min_count": 3}` — 비율로 계산한 건수가 3보다
     작으면 3으로 끌어올림.

  (2)/(3)/(4)는 모두 `{"ratio": ..., "min_count": ...}` 객체의
  부분집합이며, 최소 하나의 키는 있어야 한다(빈 객체 `{}`는 에러).

## 최상위 구조

```json
{
  "seed": 42,
  "scale": { "...": "아래 참고" },
  "case_ratios": { "...": "아래 참고" }
}
```

최상위 객체에는 `seed`/`scale`/`case_ratios` 세 키만 허용한다(그 외
키가 있으면 에러). 완료 기준 "규모, seed, 각 케이스 비율을 config로
조절 가능"의 세 부분이 각각 `scale`, `seed`, `case_ratios`에
대응한다.

## `seed`

| 필드 | 타입 | 필수 여부 | 설명 |
| --- | --- | --- | --- |
| `seed` | int | 필수 | 난수 생성 seed. 같은 config + 같은 seed는 같은 데이터를 만들어야 한다(재현성). |

생성기가 seed 하나로 모든 난수 소비를 결정적으로 재현하는 방법은
T012 구현이 정했다: **단일 `random.Random(seed)` 인스턴스를 생성기
전체가 공유한다.** `generator/pipeline.py`의 `generate(config)`가 이
인스턴스를 한 번만 만들어 `generator/master.py`/`generator/eqp_step.py`/
`generator/lot_data.py` 등 각 단계 함수에 명시적으로 넘긴다(각 단계
함수 자신의 `rng=None` 기본 동작은 단독 호출/테스트 편의일 뿐, 실제
파이프라인은 쓰지 않는다). 이 선택의 결과로, 생성 순서 중간에 난수
소비 지점을 추가/제거하면(예: 새 케이스 주입 로직 추가) 그 뒤에
나오는 모든 데이터가 같은 seed에서도 달라진다 — 이는 받아들인
트레이드오프이며, 단계별 파생 seed로 바꾸려면 이 문서와
`generator/pipeline.py`를 함께 갱신해야 한다. problem.md 10절 "표본
변경과 재현을 위한 seed 설정·기록 방식"은 **표본 선택** 쪽 미결
사항이며, 이 문서가 다루는 생성기 seed와는 별개다.

## `scale`

| 필드 | 타입 | 필수 여부 | 설명 |
| --- | --- | --- | --- |
| `scale.lot_count` | int | 필수 | 생성할 lot 수(factor 적용 전 값). 기본값 없음(설계 제안치 10,000, problem.md 8절). |
| `scale.eqp_count` | int | 필수 | 생성할 설비 수(설비 마스터 전체 대수). 제안치 80. |
| `scale.resource_count` | int | 필수 | 생성할 resource 수. 제안치 24. |
| `scale.floor_count` | int | 필수 | 건물 층수(가상, `location_floor.md`의 `location_floor_lookup.floor` 범위와 `eqp_floor.floor` 범위를 결정). T018(단일/다층 후보)이 다층 사례를 만들려면 2 이상이어야 한다. |
| `scale.location_count` | int | 필수 | 가상 위치 코드(`location_id`) 개수. `location_floor_lookup`은 이 중 일부(또는 전부)를 담고, `lot_location.location_id`는 이 개수 범위 밖의 코드를 가리킬 수도 있다 — `lot_location_lookup_miss`(형태 3)를 만들려면 후자가 필요하다. 구체적으로 몇 개를 lookup에 넣고 몇 개를 밖에 둘지는 T012/T021 구현이 정한다; 이 필드는 "위치 코드 공간의 크기" 하나만 정한다. |
| `scale.process_count` | int | 필수 | 가상 공정 수(`eqp_step.process_id` 범위). |
| `scale.step_count` | int | 필수 | 가상 step 수(`eqp_step.step_id`, `lot_data.current_step` 범위). |
| `scale.factor` | float | 선택 | `scale.lot_count`에만 곱하는 배율(위 "유효 lot 수" 정의 참고). 예: `0.01`이면 lot 10,000 → 100인 소규모 데이터(T023)를 만든다. |

각 `scale.*_count` 필드의 정확한 기본값(제안치 외의 나머지)은 이
표가 아니라 `generator/default_config.json`(T012 구현이 만든 명시적
기본 config 파일)에 있다 — 이 표는 "기본값 없음(필수)"으로 두어,
config를 안 주면 생성기가 임의로 추측하지 않고 에러를 내도록 한다
(아래 "잘못된 config" 절 참고). `default_config.json`의 값은
`floor_count: 5`/`location_count: 30`/`process_count: 6`/
`step_count: 20`로, 이 문서의 "예시" 절 전체 규모 예시와 같다.

**`scale.factor`는 `lot_count`에만 적용되고, `eqp_count`/`resource_count`/
`floor_count`/`location_count`/`process_count`/`step_count`에는 적용되지
않는다** — 이 필드들은 항상 명시한 정수 값을 그대로 쓴다. 이렇게 정한
이유: 이런 절대값이 작은 필드에 소수 배율을 곱하면 반올림 방식과
무관하게 구조적으로 실현 불가능한 조합이 생긴다(예: 설비 80대 ×
factor 0.01 = 0.8대 → "설비 5대 할당 가능한 lot"을 요구하는
`eligible_eqp_count_distribution`을 애초에 만족시킬 수 없다). 따라서
소규모 스모크 데이터(T023)를 만들 때는 `factor`로 `lot_count`만
줄이고, 나머지 구조 knob과 `case_ratios`는 유효 lot 수 기준으로
실현 가능한 값으로 **별도로 명시**한다(아래 "예시" 절 참고).
`scale.factor`를 생략하면 유효 lot 수 = `lot_count`다.

## `case_ratios`

P2의 각 케이스 주입 작업(T015~T022)이 참조할 비율/분포/최소 건수를
담는다. 이 문서는 **필드가 있어야 한다는 것과 그 의미**만 정하고,
세부 파라미터의 기본값(원본 분포에 가깝게 맞출지, 임의의 기본 비율을
둘지)은 각 작업 구현 시 정한다.

### on/off 규칙 (T022 완료 기준 "속성 config로 on/off 가능"에 대응)

`case_ratios` 아래에 나타나는 키는 네 종류로 나뉘고, on/off 규칙은
그중 **자유 이름 슬롯**과 **독립 on/off 항목**에만 적용된다:

- **자유 이름 슬롯**(config 작성자가 임의로 이름을 붙임, on/off 대상):
  `case_ratios`의 최상위 키(필드 목록에 나열된 이름들),
  `selected_attribute_distribution` 안의 속성 이름(`priority` 등),
  `selected_attribute_combination_distribution` 안의 조합 이름. 있으면
  활성화, 없으면 비활성화(생성기가 해당 항목을 만들지 않음) — "값이
  0이어도 활성화"와 "키 자체가 없어 비활성화"는 다르다.
- **독립 on/off 항목**(이 문서가 이름을 고정했지만, 각 항목이 서로
  독립적인 anomaly라 개별로 켜고 끌 수 있음): `missing_location_info`
  안의 정해진 6개 형태 이름. 위 자유 이름 슬롯과 동일하게 on/off
  규칙을 따르되, 이름 자체는 이 6개로 고정돼 있어 그 외의 키가
  있으면(오탈자 등) 에러다.
- **완결된 카테고리 집합**(on/off 대상이 **아님** — 필드가
  활성화되면 전부 있어야 함): `floor_candidate_spread` 안의
  `single_floor`/`multi_floor`, `current_floor_relation` 안의
  `current_only`/`other_only`/`both`. 이 키들은 하나의 범주형 분포를
  이루는 서로 배타적인 항목이라 T018/T019 완료 기준("둘 다 존재"/
  "세 유형 각각 최소 1건")이 전부를 요구한다 — 개별적으로 껐다 켰다
  하는 대상이 아니라, 필드 전체(`floor_candidate_spread`/
  `current_floor_relation` 자체)가 자유 이름 슬롯으로서 on/off될
  뿐이다. 필드가 활성화됐는데 정해진 카테고리 중 하나라도 빠지면
  에러(아래 "잘못된 config" 참고), 정해지지 않은 이름이 있어도 에러.
- **자유 숫자 키**(정수를 문자열로 표기, on/off 개념과 무관 — 키
  집합 자체를 작성자가 고른다): `eligible_eqp_count_distribution`/
  `rare_eligible_eqp_count_types`의 키(`"0"`, `"5"` 등), 그리고
  `selected_attribute_combination_distribution`의 `distribution`
  객체 키(`"1|P1"` 등, `dimensions` 값 조합을 표현하는 자유 문자열).
  전자는 0 이상의 정수를 10진수로 표기한 문자열이어야 하며, 그 외
  형식(`"abc"`, `"2.5"` 등)이면 에러(아래 "잘못된 config" 참고).

on/off 규칙 자체("기본값은 각 작업에서 정한다"는 **활성화된 뒤**
세부 파라미터에 적용할 fallback을 각 작업(T015~T022)이 정한다는
뜻이며, on/off 여부는 키 존재 여부로만 판정한다)는 위 첫 두 종류에만
적용된다. T022 완료 기준의 "속성"은 `case_ratios` 최상위 키가 아니라
`selected_attribute_distribution` 안의 개별 속성 이름을 가리키는
것으로 이 문서는 해석한다.

**`ratio`/`min_count`/`max_count`/`dimensions`/`distribution` 같은
구조 키는 이 네 종류 어디에도 속하지 않는다 — on/off 대상이
아니다.** 이들은 이름 슬롯/카테고리 키가 활성화된 뒤 그 값을
표현하는 고정된 필드 스키마다 — 예를 들어 `max_count` 생략은
"비활성화"가 아니라 "상한 없음"을 뜻하고(위 "값 선택 지침" 및 필드
목록 참고), `dimensions`/`distribution`은 조합 이름이 있는 한 항상
있어야 하는 필수 키다(없으면 아래 "잘못된 config"의 스키마 오류).

이는 problem.md 5절 "속성 간 조합도 config에서 각각 지정한다"와
"선택한 모든 속성을 자동으로 하나의 거대한 조합으로 묶지는 않는다"에
따라, 아래 항목들은 서로 독립적으로 켜고 끌 수 있어야 한다.

### 필드 목록

| 필드 | min_count 지원 | 대응 작업 | 의미 |
| --- | --- | --- | --- |
| `case_ratios.eligible_eqp_count_distribution` | 아니오(분포 자체, 합=1) | T015 (설비 수 분포 다양화) | lot별 할당 가능 설비 수(`lot_data.md`의 파생값 `eligible_eqp_count`, problem.md 3절 "할당 가능 설비 수")가 몇 가지 값으로, 어떤 비중으로 나타날지. 표 형태(예: `{"1": 0.2, "2": 0.6, "3": 0.2}`)를 가정하되 정확한 구조는 T015에서 정한다. 키 `"0"`도 유효하다 — `candidate_pairs`가 빈 배열인 lot(problem.md 7절 "빈 가능 쌍" 테스트 대상, `lot_data.md`의 `eligible_eqp_count = 0` 정의)을 뜻한다. **`scale.eqp_count`(설비 마스터 전체 대수)와는 다른 값이다** — 혼동 방지를 위해 필드명을 `eqp_count_distribution`이 아니라 `eligible_eqp_count_distribution`으로 두어 `lot_data.md`의 파생값 이름과 맞춘다. 여기 쓰는 각 키는 `scale.eqp_count` 이하여야 하고, `rare_eligible_eqp_count_types`에 이미 지정된 키와 **겹칠 수 없다**(아래 검증 규칙). |
| `case_ratios.shared_eqp_multi_resource` | 예 | T016 (동일 설비·여러 resource 쌍) | 같은 설비가 서로 다른 resource와 두 번 이상 짝지어지는 lot의 비율/최소 건수. 분모는 유효 lot 수(추후 T071 "관계 조합 정의와 분모"[결정 필요]/T043 "관계별 비교표" 논의 시 재정의될 수 있음 — 이 문서가 **분석 시점** 분모를 확정하는 것은 아니다). |
| `case_ratios.rare_eligible_eqp_count_types` | 예(형태는 아래 참고) | T017 (드문 설비 수 유형) | `eligible_eqp_count_distribution`과 같은 분포를 다시 정의하는 필드가 **아니다.** 특정 `eligible_eqp_count` 값의 건수를 절대 범위로 직접 지정해 "드문 유형"을 만든다: `{"5": {"min_count": 1, "max_count": 5}}`. 여기 지정한 값(`5`)은 **`eligible_eqp_count_distribution`에 동시에 지정할 수 없다**(검증 규칙) — 그 값의 건수는 이 필드가 절대 건수로 전담하고, 나머지("드물지 않은") 값들만 `eligible_eqp_count_distribution`이 비율로 분배한다(그 비율은 나머지 값들끼리 합이 1). 유효 lot 수 = 이 필드가 만든 건수 총합 + `eligible_eqp_count_distribution`이 분배하는 나머지. `max_count`가 없으면 상한 없음 — T017의 "1~수 개" 요구를 만족하려면 실무에서는 항상 작은 `max_count`를 지정해야 한다(이 문서는 생략을 금지하지는 않지만 권장하지 않는다). |
| `case_ratios.floor_candidate_spread` | 예(카테고리별 개별 지정, 두 카테고리 합=1) | T018 (단일 층/다층 후보) | 후보 설비가 한 층에만 있는 lot(`single_floor`)과 여러 층에 있는 lot(`multi_floor`)의 비율. T018 완료 기준이 "둘 다 존재"이므로 두 카테고리 모두에 `min_count`를 쓸 수 있다. **분모는 후보 설비 전원의 층 정보가 해석된 lot**이다(`eqp_floor_row_missing`/`eqp_floor_null`에 해당하는 설비를 후보로 가진 lot은 제외) — lot 자신의 현재 위치 해석 여부와는 무관하다(아래 `current_floor_relation`과 분모가 다를 수 있음, "값 선택 지침" 참고). `eligible_eqp_count == 0`인 lot(후보가 아예 없음, 위 `eligible_eqp_count_distribution`의 `"0"` 키 참고)은 단일/다층 어느 쪽으로도 분류할 수 없으므로 이 분모에서도 제외한다. |
| `case_ratios.current_floor_relation` | 예(카테고리별 개별 지정, 세 카테고리 합=1) | T019 (현재층/다른층 3유형) | lot의 현재 층 기준으로 "현재 층에서만(`current_only`)/다른 층에서만(`other_only`)/양쪽 모두(`both`)" 세 유형의 비율. T019 완료 기준이 "세 유형 각각 최소 1건"이므로 세 카테고리 모두에 `min_count`를 쓸 수 있다. **분모는 `floor_candidate_spread`의 분모(후보 설비 층 해석됨)에 더해, lot 자신의 현재 위치·층까지 해석된 lot**이다 — `missing_location_info`의 `lot_location_*` 항목에 해당하는 lot은 제외한다. 이 두 필드의 분모가 정확히 같지 않을 수 있다는 점(`current_floor_relation` 쪽이 부분집합)을 "값 선택 지침"에서 다시 설명한다. 이 config가 생성 시점에 쓰는 분모이며, `location_floor.md`가 "T029에서 명확히 표시해야 한다"고 남긴 **분석 시점** 분모 미결 사항과는 별개다. |
| `case_ratios.lot_eqp_step_mismatch` | 예 | T020 (lot-eqp_step 사양 불일치) | lot의 가능 쌍 중 `eqp_step`에 없는 조합을 의도적으로 포함하는 lot의 비율/최소 건수(분모 = 유효 lot 수, problem.md 7절 "lot 정보 우선 유지" 케이스를 만들기 위함). **차단 사항 주의:** `eqp_step_run_spec.md`가 "빈 배열 vs 행 자체의 부재" 구분과 "`step_id` 단독 조회의 비결정성"을 조인 키 확정 전까지 결정적으로 풀 수 없는 문제로 못박아 두었다 — 이 필드로 만든 "불일치" 사례가 실제로 어떤 형태(행 부재/빈 배열/조인 모호성)의 불일치인지는 그 두 미결 사항이 먼저 정해져야 명확해진다. 이 config는 "불일치 사례를 몇 건 만든다"까지만 정하고, 그 형태의 구분은 T020 구현 및 상위 미결 사항(problem.md 10절)에 맡긴다. |
| `case_ratios.missing_location_info` | 예(항목별 개별 지정) | T021 (위치·층 연결 누락) | `location_floor.md` "이미 정해진 정책"의 네 항목과 "위치를 못 찾음의 세 가지 형태"를 하나로 뭉치지 않고 항목별로 각각 지정한다. lot 단위 현상(분모 = 유효 lot 수): `lot_location_row_missing`(형태1, lot_location 행 자체 없음), `lot_location_id_null`(형태2, `location_id`가 null), `lot_location_lookup_miss`(형태3, `location_id`는 있지만 `location_floor_lookup`에 없음), `lot_location_duplicate`(같은 lot에 서로 다른 위치 중복 기재). 설비 단위 현상(분모 = `scale.eqp_count`): `eqp_floor_row_missing`(eqp_floor 행 자체 없음), `eqp_floor_null`(`floor`가 null). 각각 위 "비율 또는 최소 건수" 공통 형식을 따른다. 이렇게 나누는 이유: T053(중단·확인 요청)과 T062(테스트)가 구분해서 보여줘야 하는 사례가 서로 다르기 때문에, 하나의 "누락 비율"로 뭉치면 특정 형태가 생성되지 않을 수 있다. |
| `case_ratios.selected_attribute_distribution` | 아니오(속성별 분포 자체, 각 속성 값 분포는 합=1) | T022 (선택 속성 가상 필드) | `lot_data.attributes`(`docs/virtual_schema/lot_data.md` 참고)에 넣을 개발용 예시 속성(예: priority)의 값 분포. 실제 속성 존재 여부·값 체계가 미확인이므로, 이 필드도 "가상 예시를 만들 때의 분포"일 뿐 회사 실제 속성 분포를 추정한 것이 아니다. |
| `case_ratios.selected_attribute_combination_distribution` | 아니오(부분 지정 허용, 합<=1 — 아래 참고) | T022 확장 / T028·T060이 소비 | problem.md 5절 #5 "속성 간 조합도 config에서 각각 지정한다"(예: `할당 가능 설비 수 × 우선순위`)를 위한 필드. `{"이름": {"dimensions": [...], "distribution": {"값1|값2": 비율}}}` 형태로, 조합마다 이름을 붙여 **개별적으로** 켜고 끈다(위 on/off 규칙 참고) — #6 "자동으로 하나의 거대한 조합으로 묶지 않는다"는 자동 병합을 하지 않는다는 뜻이며, 조합 분포 지정 자체가 없다는 뜻이 아니다. **이 필드의 `distribution`은 나열한 조합들의 비율 합이 1일 필요가 없다**(전체 조합 공간을 다 나열하지 않고 일부만 강조 지정할 수 있어야 하므로) — 다만 합이 1을 넘으면 에러다(아래 검증 규칙). `dimensions`에는 `floor_candidate_spread`/`current_floor_relation`의 카테고리는 쓸 수 없다(이 문서는 이 필드를 속성·`eligible_eqp_count`와의 조합으로만 제한한다) — 층 관련 축과의 결합 분포는 이번 설계 범위 밖이다(아래 "확정하지 않는 것" 참고). `dimensions`에 쓸 수 있는 이름은 `selected_attribute_distribution`에 정의된 속성 이름 또는 `eligible_eqp_count`뿐이다. `distribution`의 키는 `dimensions` 순서대로 값을 `\|`로 이어붙인 문자열이다. 이 필드와 각 차원의 주변 분포 사이에 값이 어긋날 때 무엇이 우선하는지는 이 문서가 정하지 않는다(아래 "확정하지 않는 것" 참고). |

## 값 선택 지침 (참고용 — 정적 config 검증 대상이 아님)

아래 항목들은 config 파일 하나만 보고 생성 실행 전에 기계적으로
판정할 수 없거나, 판정할 수 있어도 다른 필드의 실제 실현 결과에
의존한다. 그래서 "잘못된 config" 절의 에러 목록에는 넣지 않고,
config를 직접 작성하는 사람이 스스로 확인해야 하는 지침으로 둔다.
생성 결과가 이 지침에서 크게 벗어나면 생성기가 경고를 내는 것은
가능하지만(T012 이후 구현이 정할 사항), config 로딩 시점의 에러로
다루지는 않는다.

- **`floor_candidate_spread`/`current_floor_relation`과 `scale.floor_count`의
  관계.** (`scale.floor_count == 1`일 때 `multi_floor`/`both`를
  금지하는 규칙은 정적으로 판정 가능하므로 위 "잘못된 config"의
  에러 목록으로 옮겼다 — 여기서는 그 나머지를 다룬다.) 두 필드가
  정확히 같은 모집단을 쓴다면(단순화 가정) `scale.floor_count == 2`일
  때는 "여러 층에 있음"이 항상
  "두 층 모두"와 같아 `multi_floor ≈ both`, `single_floor ≈
  current_only + other_only`가 되며, `scale.floor_count >= 3`에서는
  `multi_floor >= both`, `single_floor >= current_only`인 부등식
  경향만 있으면 된다. **다만 두 필드의 실제 분모는 정확히 같지
  않을 수 있다** — `current_floor_relation`은 `floor_candidate_spread`의
  분모(후보 설비 층 해석됨)에 lot 자신의 위치·층 해석 여부까지
  추가로 요구하는 부분집합이다(위 필드 목록 참고). 두 분모가 얼마나
  차이 나는지는 `missing_location_info`의 `lot_location_*` 비율에
  따라 달라지므로, 이 관계는 "대략 맞춰야 하는 목표"이지 소수점까지
  맞는 등식이 아니다.
- **비율 반올림의 합.** 위 "전역" 절 참고 — 같은 필드 안 여러
  카테고리의 반올림 결과 합이 모집단과 정확히 일치하지 않을 수
  있다. 특히 어떤 카테고리에 `min_count`가 있고 다른 카테고리들의
  비율 합이 이미 1에 가까우면, `min_count`를 채우기 위해 다른
  카테고리에서 lot을 재배정해야 할 수 있다 — 그 재배정 방식은 이
  문서가 정하지 않는다.
- **`eligible_eqp_count_distribution`/`floor_candidate_spread`/
  `current_floor_relation` 사이의 상관관계.** 이 문서는 이 세
  필드가 서로 독립적으로 배정된다고 가정한다(즉 `multi_floor`
  비율이 높다고 해서 `eligible_eqp_count`가 2 이상인 lot이 저절로
  늘어나지 않는다). `multi_floor`/`both`가 의미 있게 나타나려면
  후보 설비가 2개 이상인 lot이 충분히 있어야 하므로, 이 세 필드의
  값을 서로 맞춰 쓰는 것은 config 작성자의 책임이다 — 정적 검증도,
  `selected_attribute_combination_distribution`으로 상관관계를
  지정하는 것도 이번 설계 범위 밖이다.

## 잘못된 config에 대한 최소 규칙

problem.md 7절(144행)은 "중복 ID, 존재하지 않는 resource·설비 참조,
빈 가능 쌍, 잘못된 config 등은 테스트 대상으로 다루되, 실제 처리
정책은 별도로 확정해야 한다"고 한다. 여기서 "잘못된 config"는 표본
선택 등 다른 단계의 config까지 포함할 수 있어 범위가 이 문서보다
넓고, 그 실제 **처리 정책**(무시/중단/보정 등 중 무엇을 할지)은
T054(`needs_decision`, 아직 확정 안 됨)가 결정할 사안이다. 이 절은
T054를 대신 확정하는 것이 아니다 — **이 생성기 config 하나로 범위를
좁혀서, "config 파일 자체가 구조적으로 무엇이 형식 오류인가"만**
도구 설계자 권한으로 지금 정한다(전제 절 참고: 이건 회사 데이터
정책이 아니라 우리 도구 자신의 입력 검증 규칙이다). 아래 규칙을
위반하면 생성기는 **중단하고 에러를 낸다** — 이 "중단" 자체가
T054가 고를 수 있는 여러 처리 정책 후보 중 하나를 이 config
하나에 한해 미리 고른 것일 뿐, T054가 다룰 회사 데이터/다른 config
전반의 처리 정책을 대신 정한 것은 아니다. 이 규칙들의 실제 구현과
테스트를 담당할 작업은 아직 배정되지 않았다 — T012(생성 로직) 구현
시 필요하면 별도 작업으로 분리한다.

- 최상위 객체에 `seed`/`scale`/`case_ratios` 외의 키가 있으면 에러.
- `scale` 아래 이 문서에 정의되지 않은 키가 있으면 에러.
- `case_ratios` 최상위에 필드 목록에 없는 이름이 있으면 에러.
- `missing_location_info` 안에 정해진 6개 형태 이름 외의 키가
  있으면 에러(위 on/off 규칙 "독립 on/off 항목" 참고). 다른 자유
  이름 슬롯(`selected_attribute_distribution`/
  `selected_attribute_combination_distribution` 안의 이름)은
  작성자가 임의로 붙이는 이름이라 이 오탈자 검사 대상이 아니다.
- `floor_candidate_spread`가 있는데 `single_floor`/`multi_floor`
  중 하나라도 없으면 에러. 이 두 키 외의 키가 있어도 에러.
  `current_floor_relation`이 있는데 `current_only`/`other_only`/
  `both` 중 하나라도 없으면 에러. 이 세 키 외의 키가 있어도 에러
  (위 on/off 규칙 "완결된 카테고리 집합" 참고).
- `eligible_eqp_count_distribution`/`rare_eligible_eqp_count_types`의
  키가 0 이상의 정수를 10진수로 표기한 문자열이 아니면 에러.
- `selected_attribute_combination_distribution`의 각 조합에는
  `dimensions`와 `distribution`이 둘 다 있어야 하며, 하나라도
  없으면 에러. `distribution`의 각 키는 `\|`로 구분했을 때 조각
  수가 `dimensions` 길이와 같아야 하며, 각 조각은 해당 차원의
  선언된 카테고리 값(예: `eligible_eqp_count_distribution`/
  `rare_eligible_eqp_count_types`에 나온 숫자 키, 또는
  `selected_attribute_distribution`에 나온 해당 속성의 값) 중
  하나여야 한다 — 그렇지 않으면 에러.
- 각 필드의 구조 키(`ratio`/`min_count`/`max_count`/`dimensions`/
  `distribution`) 자리에 이 목록에 없는 키가 있으면 에러. 값이
  `{"ratio": ..., "min_count": ...}` 객체 형태인데 키가 하나도
  없으면(빈 객체 `{}`) 에러.
- `scale`의 필수 필드(`lot_count`/`eqp_count`/`resource_count`/
  `floor_count`/`location_count`/`process_count`/`step_count`) 중
  하나라도 없으면 에러. `seed`가 없거나 정수가 아니어도 에러.
- `scale.*_count` 값이 정수가 아니거나 0 이하이면 에러.
- `scale.factor`가 있는데 0 이하이면 에러.
- **`scale.floor_count == 1`이면 `multi_floor`/`both`의 `ratio`가
  0보다 크거나 `min_count`가 1 이상이면 에러** — 층이 하나뿐이면
  다층 후보 자체가 존재할 수 없으므로, 이 판정은 다른 `case_ratios`의
  실현 결과와 무관하게 config만으로 확정할 수 있다(위 "값 선택
  지침"의 나머지 층 관련 항목과 달리 이건 정적 규칙이다).
- **`shared_eqp_multi_resource`가 활성화됐는데(`ratio > 0` 또는
  `min_count >= 1`) `scale.resource_count < 2`이면 에러** — 같은
  설비가 서로 다른 resource와 두 번 이상 짝지어지려면 resource가
  최소 2개 있어야 한다.
- 비율 필드(0~1 범위를 가정하는 필드)의 값이 0~1 범위를 벗어나면 에러.
- "분포 자체"로 표시된 필드(`eligible_eqp_count_distribution`,
  `floor_candidate_spread`, `current_floor_relation`,
  `selected_attribute_distribution`의 각 속성별 값 분포)는 그 필드
  **자신이 나열한** 카테고리 값(`ratio` 성분만)의 합이 1이 아니면
  에러. `min_count`는 이 합계 검사에 포함하지 않는다.
- `selected_attribute_combination_distribution`의 각 조합에서
  `distribution` 값의 합이 1을 넘으면 에러(1보다 작은 것은 허용 —
  부분 지정).
- `case_ratios.rare_eligible_eqp_count_types`에 나열된 키는
  `case_ratios.eligible_eqp_count_distribution`에 동시에 나타나면
  에러. 두 필드에 나타나는 모든 키는 `scale.eqp_count` 이하여야
  하며, 그렇지 않으면 에러.
- `min_count`/`max_count`는 정수여야 하고 음수면 에러.
  `max_count < min_count`이면 에러.
- **`min_count` 합의 상한 검사(모집단을 config만으로 정적으로 알
  수 있는 필드에 한정):**
  - `shared_eqp_multi_resource`의 `min_count`, `lot_eqp_step_mismatch`의
    `min_count`는 각각 유효 lot 수를 넘으면 에러.
    `rare_eligible_eqp_count_types`는 그 안에 나열된 **모든 키의
    `min_count`를 합산한 값**이 유효 lot 수를 넘으면 에러(이 필드의
    각 키는 서로 다른 `eligible_eqp_count` 값을 가진 lot 수를
    뜻하므로 서로 배타적이며, 합산해서 비교하는 것이 맞다).
  - `missing_location_info` 안에서 **lot 단위 4개 항목**
    (`lot_location_row_missing`/`lot_location_id_null`/
    `lot_location_lookup_miss`/`lot_location_duplicate`)의
    `min_count`를 모두 더한 값이 유효 lot 수를 넘으면 에러.
  - `missing_location_info` 안에서 **eqp 단위 2개 항목**
    (`eqp_floor_row_missing`/`eqp_floor_null`)의 `min_count`를
    더한 값이 `scale.eqp_count`를 넘으면 에러.
  - `floor_candidate_spread`/`current_floor_relation`은 정확한
    모집단이 다른 `case_ratios`의 생성 결과에 따라 달라지지만,
    각 필드 안의 `min_count` 합이 **유효 lot 수**(참 모집단의
    상한)를 넘으면 그 자체로 이미 불가능하므로 이 상한 검사만은
    적용한다(넘으면 에러). 그보다 작다고 해서 실현 가능하다는
    보장은 아니다(위 "값 선택 지침" 참고).

## 예시

```json
{
  "seed": 42,
  "scale": {
    "lot_count": 10000,
    "eqp_count": 80,
    "resource_count": 24,
    "floor_count": 5,
    "location_count": 30,
    "process_count": 6,
    "step_count": 20
  },
  "case_ratios": {
    "eligible_eqp_count_distribution": { "1": 0.2, "2": 0.6, "3": 0.2 },
    "shared_eqp_multi_resource": { "ratio": 0.05, "min_count": 20 },
    "rare_eligible_eqp_count_types": { "5": { "min_count": 5, "max_count": 8 } },
    "floor_candidate_spread": { "single_floor": 0.5, "multi_floor": { "ratio": 0.5, "min_count": 50 } },
    "current_floor_relation": { "current_only": 0.34, "other_only": { "ratio": 0.33, "min_count": 50 }, "both": { "ratio": 0.33, "min_count": 50 } },
    "lot_eqp_step_mismatch": { "ratio": 0.01, "min_count": 5 },
    "missing_location_info": {
      "lot_location_row_missing": { "ratio": 0.005, "min_count": 2 },
      "lot_location_id_null": { "ratio": 0.005, "min_count": 2 },
      "lot_location_lookup_miss": { "ratio": 0.005, "min_count": 2 },
      "lot_location_duplicate": { "ratio": 0.002, "min_count": 1 },
      "eqp_floor_row_missing": { "min_count": 1 },
      "eqp_floor_null": { "min_count": 1 }
    },
    "selected_attribute_distribution": { "priority": { "P1": 0.2, "P2": 0.5, "P3": 0.3 } },
    "selected_attribute_combination_distribution": {
      "eligible_eqp_count_x_priority": {
        "dimensions": ["eligible_eqp_count", "priority"],
        "distribution": { "1|P1": 0.15, "1|P3": 0.02, "3|P1": 0.01, "3|P3": 0.12 }
      }
    }
  }
}
```

(위 조합 분포 예시 값은 일부러 각 차원의 주변 분포(`eligible_eqp_count_distribution`의
`1`:0.2·`3`:0.2, `priority`의 `P1`:0.2·`P3`:0.3)를 단순히 곱한 값이
아니게 잡았다 — `1`은 `P1`과, `3`은 `P3`과 더 자주 같이 나타나도록
해서, T028/T060이 검증할 "비자명한 결합분포"를 실제로 만든다. 이
비율은 위 "값 선택 지침"이 말하는 목표치이며, 정수 단위로 정확히
일치함을 보장하지 않는다.)

`eligible_eqp_count_distribution`에 `5`가 없는 이유: `5`는
`rare_eligible_eqp_count_types`가 절대 건수(5~8건, T017의 "1~수 개"에
맞춘 작은 상한)로 전담하므로 두 필드에 동시에 넣지 않는다(위 검증
규칙).

스모크 데이터(T023)용 축소 예시 — `scale.factor`로 `lot_count`만
줄이고, 구조 관련 knob과 `case_ratios`는 유효 lot 수(100개)에서도
실현 가능한 값으로 **별도로 명시**한다(위 전체 예시를 그대로
스케일만 줄이면 실현 불가능한 조합이 생기므로 그대로 재사용하지
않는다):

```json
{
  "seed": 42,
  "scale": {
    "lot_count": 10000,
    "factor": 0.01,
    "eqp_count": 8,
    "resource_count": 5,
    "floor_count": 3,
    "location_count": 5,
    "process_count": 2,
    "step_count": 4
  },
  "case_ratios": {
    "eligible_eqp_count_distribution": { "1": 0.5, "2": 0.5 },
    "shared_eqp_multi_resource": { "ratio": 0.05, "min_count": 2 },
    "rare_eligible_eqp_count_types": { "3": { "min_count": 1, "max_count": 2 } },
    "floor_candidate_spread": { "single_floor": 0.5, "multi_floor": { "ratio": 0.5, "min_count": 3 } },
    "current_floor_relation": { "current_only": 0.34, "other_only": { "ratio": 0.33, "min_count": 2 }, "both": { "ratio": 0.33, "min_count": 2 } },
    "lot_eqp_step_mismatch": { "ratio": 0.02, "min_count": 1 },
    "missing_location_info": {
      "lot_location_row_missing": { "min_count": 1 },
      "lot_location_id_null": { "min_count": 1 },
      "lot_location_lookup_miss": { "min_count": 1 },
      "lot_location_duplicate": { "min_count": 1 },
      "eqp_floor_row_missing": { "min_count": 1 },
      "eqp_floor_null": { "min_count": 1 }
    },
    "selected_attribute_distribution": { "priority": { "P1": 0.3, "P2": 0.4, "P3": 0.3 } },
    "selected_attribute_combination_distribution": {
      "eligible_eqp_count_x_priority": {
        "dimensions": ["eligible_eqp_count", "priority"],
        "distribution": { "1|P1": 0.1, "2|P3": 0.1 }
      }
    }
  }
}
```

이 스모크 예시는 위 "잘못된 config" 정적 규칙은 전부 통과한다:
`eligible_eqp_count_distribution`이 `3`을 빼고 `{1,2}`만 다뤄
`rare_eligible_eqp_count_types`의 `3`과 겹치지 않고, 두 값 모두
`scale.eqp_count = 8` 이하이며, `floor_candidate_spread`/
`current_floor_relation`의 `min_count` 합도 유효 lot 수(100) 이내다.

다만 "값 선택 지침"이 말하는 **실현 가능성은 이 예시에서 빠듯하다**
— `eqp_floor_row_missing`/`eqp_floor_null`로 설비 8대 중 2대(25%)의
층 정보를 없앴는데, `floor_candidate_spread`/`current_floor_relation`의
분모는 바로 그 "설비 층이 전부 해석된 lot"이다. 설비 대수가 작을수록
이 두 min_count(설비 단위 누락, lot 단위 층 분포)가 서로의 실현
여지를 깎아먹는 정도가 커진다 — 이 상호작용을 정량적으로 얼마나
줄이는지는 후보 설비를 뽑는 정책(무작위 균등 추출인지, 다른
방식인지)에 따라 달라지며 이 문서가 정하지 않는다(T012/T014
구현이 정한다). 이 스모크 예시는 "정적 규칙을 통과하는 예시"이지
"두 케이스가 넉넉하게 동시에 실현됨을 보장하는 예시"는 아니다 —
실제 생성 후 T024/T023 검증에서 `multi_floor`/`both` 목표 건수가
못 채워지면, 이 예시의 `eqp_floor_*` `min_count`를 줄이거나
`eqp_count`를 늘려 재조정해야 한다. `selected_attribute_combination_distribution`도
100 lot 규모에서 최소 몇 건이 나오도록 비율을 남겨, problem.md 8절
"여러 속성·조합" 사례가 스모크에서도 0건이 되지 않게 했다.

## 이 문서가 확정하지 않는 것

- `case_ratios` 각 필드의 정확한 내부 구조(예: 분포를 히스토그램으로
  둘지, 구간으로 둘지)와 세부 기본값 — 해당 케이스 작업(T015~T022)에서
  구현하며 필요하면 이 문서를 갱신한다.
- 여러 `case_ratios`를 동시에 켰을 때 서로 충돌하는 경우(예: 위치 누락
  비율과 다층 후보 비율이 같은 lot에 겹칠 때)의 우선순위, 그리고 값
  선택 지침에서 언급한 "필드 간 상관관계"를 실제로 어떻게 실현할지
  — problem.md 10절 "여러 분포가 충돌할 때 후보를 만드는 구체적인
  방법과 개선 정도의 지표"와 같은 종류의 미결 사항(T072, [결정
  필요])이며, 이 문서는 생성기 config 구조만 정하고 그 알고리즘은
  정하지 않는다.
- `selected_attribute_combination_distribution`이 지정한 조합 분포와
  각 차원의 주변 분포(`eligible_eqp_count_distribution`,
  `selected_attribute_distribution`)가 수치상 어긋날 때 무엇을
  우선할지, 그리고 층 관련 축(`floor_candidate_spread`/
  `current_floor_relation`)과의 결합 분포 자체 — 위와 같은 종류의
  미결 사항으로 남긴다.
- `case_ratios.lot_eqp_step_mismatch`가 만드는 불일치의 정확한 형태
  구분 — `eqp_step_run_spec.md`의 "빈 배열 vs 행 부재", "`step_id`
  단독 조회의 비결정성" 미결 사항이 먼저 정해져야 한다(위 표 참고).
- `resource_data.md`가 정의한 resource 속성(예: `resource_type`)의
  분포를 통제하는 `case_ratios` 필드, 그리고 (공유 설비 케이스가
  아닌) 일반적인 `candidate_pairs`당 쌍 수 분포를 통제하는 필드 —
  둘 다 이번 설계에는 없는 공백이다. 필요해지면 별도 필드를 추가하고
  이 문서를 갱신한다.
- 같은 필드 안에서 여러 카테고리에 동시에 `min_count`가 걸릴 때의
  실제 재배분 알고리즘(위 "값 선택 지침" 참고) — 정적 검증으로
  걸러지지 않는 조합의 실제 실현 방법은 T012 이후 구현이 정한다.
- 표본 선택(P4) 단계의 config, 실행 CLI 인터페이스, 결과 파일
  구성 — 이 문서 범위 밖(위 "전제" 및 문서 상단 T077 관련 안내 참고).
