"""T014: lot_data의 candidate_pairs(가능 쌍) 생성.

eqp_step_run_spec.md가 "step_id 단독 조회의 비결정성"(조인 키 미확정,
problem.md 10절)을 미결로 남겨뒀고, "임의로 합집합/우선순위 등을 정해
넘기지 않는다"고 못박아 두었다. 이 모듈은 **lot마다 process_id 하나와
step_id 하나를 함께 골라, 그 (process_id, step_id) 조합의 eqp_step
행만으로 candidate_pairs를 만든다** — 여러 process의 행을 합치지
않는다. 이렇게 고른 이유: 이 방식은 두 가지 가능한 조인 해석(step_id
단독 조인 / (process_id, step_id) 조합 조인) 중 어느 쪽과도 모순되지
않는다 — (process,step) 조인 기준으로는 정확히 일치하고, step_id
단독 조인 기준으로는 그 step의 전체 행 중 한 process분의 부분집합일
뿐이라 결과가 틀리지 않는다. (반대로 여러 process의 행을 합쳤다면
step_id 단독 조인 해석에서만 맞고 (process,step) 조인 해석에서는
전체 lot이 사양 불일치가 되어, 사실상 한쪽 해석을 골라 확정하는
것과 같아진다.) `lot_data.current_step`에는 이렇게 내부적으로 고른
process_id를 노출하지 않는다 — lot_data.md가 "공정 식별자는 이
필드에 포함하지 않는다"고 정했기 때문이며, 이는 실제 조인 키가
무엇인지에 대한 이 모듈의 내부 선택과는 별개다.

lot_data.md는 "완전히 동일한 {eqp, resource} 쌍이 두 번 나타나는
경우의 처리(중복 제거 여부)는 이 문서에서 정하지 않는다 — 생성기가
중복을 만들지 않도록 하거나, 만든다면 그 정책을 생성 로직 문서에
별도로 적는다"고 위임했다 — 이 모듈은 **중복 쌍을 만들지 않는다**
(집합으로 dedupe). 하나의 (process, step) 조합 안에서는
eqp_step_run_spec.md의 유일성 가정(같은 (process,step,resource)는
한 번만 나타남)이 이미 중복을 막아주지만, 방어적으로 한 번 더
dedupe한다.
"""
import random

from generator._util import LOT_ID_WIDTH, check_no_duplicates, effective_lot_count


def build_candidate_pairs(process_id: str, step_id: str, eqp_step_rows: list) -> list:
    seen = set()
    pairs = []
    for row in eqp_step_rows:
        if row["process_id"] != process_id or row["step_id"] != step_id:
            continue
        for eqp_id in row["eligible_eqp_ids"]:
            key = (eqp_id, row["resource_id"])
            if key not in seen:
                seen.add(key)
                pairs.append({"eqp": eqp_id, "resource": row["resource_id"]})
    return pairs


def generate_lot_data(
    config: dict, *, process_ids: list, step_ids: list, eqp_step_rows: list,
    rng: random.Random = None,
) -> dict:
    """rng를 안 넘기면 이 함수가 새 random.Random(config["seed"])을 만든다 —
    단독/테스트 호출용 편의이며, 실제 파이프라인(generator/pipeline.py)은
    앞 단계가 쓰던 rng를 그대로 이어받아 넘긴다."""
    if not process_ids:
        raise ValueError("process_ids must not be empty")
    if not step_ids:
        raise ValueError("step_ids must not be empty")
    check_no_duplicates(process_ids, "process_ids")
    check_no_duplicates(step_ids, "step_ids")
    if rng is None:
        rng = random.Random(config["seed"])
    lot_count = effective_lot_count(config)
    lots = []
    for i in range(1, lot_count + 1):
        process_id = rng.choice(process_ids)
        step_id = rng.choice(step_ids)
        lots.append({
            "lot_id": f"LOT_V{i:0{LOT_ID_WIDTH}d}",
            "current_step": step_id,
            "candidate_pairs": build_candidate_pairs(process_id, step_id, eqp_step_rows),
            "attributes": {},
        })
    return {"lot_data": lots}
