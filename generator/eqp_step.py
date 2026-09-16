"""T013: eqp_step 참조 사양(가능 쌍) 생성.

docs/generator/config.md의 scale.process_count/step_count와 T012가
만든 설비/리소스 id 목록을 받아 docs/virtual_schema/eqp_step_run_spec.md의
eqp_step 테이블을 생성한다. 같은 (process_id, step_id) 아래 resource별로
eligible_eqp_ids가 달라질 수 있어야 한다는 스키마 요구(T013 완료 기준)를
만족하도록, 각 (process, step, resource) 조합마다 독립적으로 설비
부분집합을 뽑는다. 같은 (process_id, step_id, resource_id) 조합이
두 번 나오지 않는다는 eqp_step_run_spec.md의 유일성 가정은
process_ids/step_ids/resource_ids/eqp_ids 네 목록 모두에 중복이 없다는
전제 위에서 성립한다 — rng.sample()은 값이 아니라 위치를 비복원
추출하므로, 입력 목록 자체에 중복 값이 있으면 결과에도 중복이 남는다.
그래서 네 목록 전부의 중복 여부를 미리 검증한다.

(process,step)당 resource 수, resource당 eligible eqp 수 범위는 각각
1~3으로 고정했다 — config.md는 이 세부 분포를 다루지 않으므로("이
문서가 확정하지 않는 것" 참고) 여기서 직접 정한다. 하한 1을 강제해
빈 eligible_eqp_ids는 만들지 않지만, (process_id, step_id) 조합 자체가
행이 하나도 없는 경우(예: process_count×step_count 대비 실제 조합 수가
적어 발생)는 이 모듈이 만드는 그대로다 — eqp_step_run_spec.md가 "빈
배열 vs 행 자체의 부재"를 미결로 남긴 두 상태 중 후자를 이 생성기가
만들어낸다는 뜻이며, 그 구분 자체를 여기서 없애지는 않는다. (process,step)
조합 하나의 eligible_eqp_count 합집합 상한은 resource 상한(3) × eqp
상한(3) = 9다(resource 1개짜리 상한이 아니다) — T014 이후가 이보다 큰
`eligible_eqp_count`를 원하면 이 상한 자체를 넓혀야 하며, **다른 step의
candidate_pairs를 합쳐서는 안 된다**(lot_data.md "다음 step의 가능
쌍을 추론하지 않는다").
"""
import random

from generator._util import positive_int

_PROCESS_ID_WIDTH = 4
_STEP_ID_WIDTH = 4
_RESOURCES_PER_STEP = (1, 3)
_EQP_PER_RESOURCE = (1, 3)


def generate_process_ids(process_count: int) -> list:
    process_count = positive_int(process_count, "process_count")
    return [f"P{i:0{_PROCESS_ID_WIDTH}d}" for i in range(1, process_count + 1)]


def generate_step_ids(step_count: int) -> list:
    step_count = positive_int(step_count, "step_count")
    return [f"S{i:0{_STEP_ID_WIDTH}d}" for i in range(1, step_count + 1)]


def _check_no_duplicates(ids: list, name: str) -> None:
    if len(set(ids)) != len(ids):
        raise ValueError(f"{name} must not contain duplicates")


def _check_bounds(bounds: tuple, name: str) -> None:
    lo, hi = bounds
    if lo < 1 or hi < lo:
        raise ValueError(f"{name} bounds must satisfy 1 <= lo <= hi, got {bounds}")


def _sample_count(rng: random.Random, bounds: tuple, available: int, name: str) -> int:
    lo, hi = bounds
    if available < lo:
        raise ValueError(f"not enough candidates for {name}: need >= {lo}, have {available}")
    return rng.randint(lo, min(hi, available))


def generate_eqp_step(
    *,
    process_ids: list,
    step_ids: list,
    resource_ids: list,
    eqp_ids: list,
    rng: random.Random,
    resources_per_step: tuple = _RESOURCES_PER_STEP,
    eqp_per_resource: tuple = _EQP_PER_RESOURCE,
) -> list:
    if not resource_ids:
        raise ValueError("resource_ids must not be empty")
    if not eqp_ids:
        raise ValueError("eqp_ids must not be empty")
    _check_no_duplicates(process_ids, "process_ids")
    _check_no_duplicates(step_ids, "step_ids")
    _check_no_duplicates(resource_ids, "resource_ids")
    _check_no_duplicates(eqp_ids, "eqp_ids")
    _check_bounds(resources_per_step, "resources_per_step")
    _check_bounds(eqp_per_resource, "eqp_per_resource")

    rows = []
    for process_id in process_ids:
        for step_id in step_ids:
            k = _sample_count(rng, resources_per_step, len(resource_ids), "resources_per_step")
            for resource_id in rng.sample(resource_ids, k):
                m = _sample_count(rng, eqp_per_resource, len(eqp_ids), "eqp_per_resource")
                rows.append({
                    "process_id": process_id,
                    "step_id": step_id,
                    "resource_id": resource_id,
                    "eligible_eqp_ids": rng.sample(eqp_ids, m),
                })
    return rows


def generate_eqp_step_data(
    config: dict, *, eqp_ids: list, resource_ids: list, rng: random.Random = None
) -> dict:
    """rng를 안 넘기면 이 함수가 새 random.Random(config["seed"])을 만든다 —
    단독/테스트 호출용 편의이며, 실제 파이프라인(generator/pipeline.py)은
    거기서 만든 rng를 이 함수와 다른 모든 단계에 그대로 이어서 넘긴다
    (생성기 전체가 seed 하나를 공유한다는 config.md의 계약).

    반환값에 "eqp_step"뿐 아니라 이 함수가 만든 "process_ids"/"step_ids"도
    함께 담는다 — 뒤 단계(T014 이후)가 같은 값을 다시 만들어 쓰면, 두
    자리에서 각각 만든 목록이 우연히 같은 함수 호출에 의존하는 암묵적
    결합이 생긴다(한쪽만 바뀌면 조용히 어긋난다). 호출자는 이 값을
    데이터 테이블(eqp_step)과 구분해서 다뤄야 한다 — 파이프라인 출력에
    그대로 병합하지 않는다."""
    scale = config["scale"]
    if rng is None:
        rng = random.Random(config["seed"])
    process_ids = generate_process_ids(scale["process_count"])
    step_ids = generate_step_ids(scale["step_count"])
    return {
        "eqp_step": generate_eqp_step(
            process_ids=process_ids, step_ids=step_ids,
            resource_ids=resource_ids, eqp_ids=eqp_ids, rng=rng,
        ),
        "process_ids": process_ids,
        "step_ids": step_ids,
    }
