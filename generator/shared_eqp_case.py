"""T016: 동일 설비·여러 resource 쌍 케이스 주입.

problem.md 8절 검증 사례 "같은 설비와 여러 resource 쌍"과
config.md의 `case_ratios.shared_eqp_multi_resource`(분모 = 유효 lot 수)에
대응한다. 이미 만들어진 lot_data(T014/T015 산출물) 중 일부를, 같은
eqp가 서로 다른 resource와 두 번 이상 짝지어지는 (process,step)
조합으로 다시 골라 덮어써서 이 케이스를 최소 목표 건수만큼 보장한다.

**목표 건수는 이미 자연적으로 이 성질을 만족하는 lot을 뺀 부족분만
채운다.** config.md "비율 또는 최소 건수" 공통 형식은 "최소 이만큼"을
보장하라는 뜻이지, 이미 그만큼(또는 그 이상) 있는데 무작위로 더
덮어쓰라는 뜻이 아니다 — 무작정 target_count개를 새로 골라 덮어쓰면
비율을 낮게 지정해도(예: 5%) 우연히 이미 그 특성을 가진 lot이 많을
때 결과가 그보다 훨씬 커질 수 있고(관찰됨), 이미 만족하는 lot을 또
덮어써 예산을 낭비한다.

**이 케이스는 각 lot의 (T015가 이미 정했을 수 있는) eligible_eqp_count를
그대로 유지하면서 주입한다** — shared_eqp_multi_resource가 요구하는
건 "eqp 하나가 resource 두 개 이상과 짝지어짐"뿐이고, eligible_eqp_count
(중복 없는 eqp 개수) 자체를 몇으로 할지와는 독립적인 성질이다. 그래서
해당 lot이 이미 갖고 있던 eligible_eqp_count와 같은 값을 유지할 수
있는 (process,step) 조합을 찾아 쓴다 — 못 찾으면(그 정확한 크기에서
"공유 eqp"를 가진 조합이 eqp_step에 없으면) 에러를 낸다. T015의 분포를
조용히 깨뜨리지 않는다.
"""
import random
from collections import defaultdict

from generator._util import eligible_eqp_count
from generator.lot_data import build_candidate_pairs


def _resource_set_by_eqp(candidate_pairs: list) -> dict:
    by_eqp = defaultdict(set)
    for pair in candidate_pairs:
        by_eqp[pair["eqp"]].add(pair["resource"])
    return by_eqp


def has_shared_eqp_multi_resource(candidate_pairs: list) -> bool:
    """candidate_pairs 안에 같은 eqp가 서로 다른 resource와 두 번
    이상 나타나는지 — problem.md 8절 검증 사례의 판정 기준. (eqp,
    resource) 중복 쌍이 남아 있어도 정확하도록 resource를 집합으로
    센다(단순 eqp 등장 횟수가 아니다)."""
    return any(len(resources) >= 2 for resources in _resource_set_by_eqp(candidate_pairs).values())


def find_shared_eqp_combinations(
    process_ids: list, step_ids: list, eqp_step_rows: list
) -> list:
    """실제로 shared_eqp_multi_resource 성질을 갖는 (process_id, step_id)
    조합만 골라 반환한다(존재하지 않는 조합을 지어내지 않는다 — 전부
    build_candidate_pairs로 eqp_step_rows에서 실제로 만들어지는 쌍만
    확인한다)."""
    combos = []
    for process_id in process_ids:
        for step_id in step_ids:
            pairs = build_candidate_pairs(process_id, step_id, eqp_step_rows)
            if has_shared_eqp_multi_resource(pairs):
                combos.append((process_id, step_id))
    return combos


def _build_pairs_at_target_with_shared_eqp(
    process_id: str, step_id: str, eqp_step_rows: list, target: int, rng: random.Random
):
    """이 (process,step)에서 shared_eqp_multi_resource를 만족하면서
    eligible_eqp_count == target인 candidate_pairs를 만든다. 그 조합에
    2개 이상 resource와 짝지어진 eqp가 없거나, 그런 eqp를 포함해도
    유니크 eqp 수가 target보다 적으면 None을 반환한다(호출자가 다른
    조합을 시도한다)."""
    pairs = build_candidate_pairs(process_id, step_id, eqp_step_rows)
    by_eqp = _resource_set_by_eqp(pairs)
    shared_eqp_ids = [eqp for eqp, resources in by_eqp.items() if len(resources) >= 2]
    if not shared_eqp_ids:
        return None
    unique_eqp = sorted(by_eqp)
    if len(unique_eqp) < target:
        return None
    shared_eqp = rng.choice(shared_eqp_ids)
    others = [e for e in unique_eqp if e != shared_eqp]
    chosen = {shared_eqp} | set(rng.sample(others, target - 1))
    return [p for p in pairs if p["eqp"] in chosen]


def _injection_candidates(lots: list, already_shared: set) -> list:
    # target==0(빈 candidate_pairs)인 lot은 건드리지 않는다 — eqp가
    # 하나도 없으면 "공유"가 정의상 불가능하고, 억지로 eqp를 붙이면
    # T015가 그 lot에 정해준 eligible_eqp_count(=0)가 깨진다.
    return [
        i for i in range(len(lots))
        if i not in already_shared and eligible_eqp_count(lots[i]["candidate_pairs"]) >= 1
    ]


def _inject_one(lot: dict, combos: list, rng: random.Random,
                 eqp_step_rows: list) -> dict:
    target = eligible_eqp_count(lot["candidate_pairs"])
    shuffled_combos = combos[:]
    rng.shuffle(shuffled_combos)
    for process_id, step_id in shuffled_combos:
        pairs = _build_pairs_at_target_with_shared_eqp(
            process_id, step_id, eqp_step_rows, target, rng
        )
        if pairs is not None:
            return {**lot, "current_step": step_id, "candidate_pairs": pairs}
    raise ValueError(
        f"no shared-eqp combination in eqp_step supports "
        f"eligible_eqp_count == {target}; cannot inject "
        "case_ratios.shared_eqp_multi_resource without changing that lot's "
        "eligible_eqp_count"
    )


def inject_shared_eqp_cases(
    lots: list, *, process_ids: list, step_ids: list, eqp_step_rows: list,
    target_count: int, rng: random.Random,
) -> list:
    """lots 중 target_count개가 shared_eqp_multi_resource를 만족하도록
    보장한 새 리스트를 반환한다(원본은 바꾸지 않는다). 이미 만족하는
    lot은 세어서 부족분만 채우며, 각 lot의 eligible_eqp_count는 그대로
    유지한다. target_count가 lot 수보다 크거나, 필요한 크기에서
    shared_eqp_multi_resource를 만들 수 있는 (process,step) 조합이
    eqp_step에 없으면 에러를 낸다 — 조용히 목표를 낮추거나 다른
    lot의 eligible_eqp_count를 바꾸지 않는다."""
    if target_count > len(lots):
        raise ValueError(
            f"target_count ({target_count}) exceeds available lots ({len(lots)})"
        )

    already_shared = {
        i for i, lot in enumerate(lots) if has_shared_eqp_multi_resource(lot["candidate_pairs"])
    }
    deficit = target_count - len(already_shared)
    if deficit <= 0:
        return list(lots)

    candidates = _injection_candidates(lots, already_shared)
    if deficit > len(candidates):
        raise ValueError(
            f"not enough lots with eligible_eqp_count >= 1 to inject "
            f"shared_eqp_multi_resource into (need {deficit} more, have {len(candidates)})"
        )

    combos = find_shared_eqp_combinations(process_ids, step_ids, eqp_step_rows)
    if not combos:
        raise ValueError(
            "no (process, step) combination in eqp_step exhibits the "
            "same-equipment/multiple-resource pattern; "
            "case_ratios.shared_eqp_multi_resource cannot be satisfied"
        )

    updated = list(lots)
    for index in rng.sample(candidates, deficit):
        updated[index] = _inject_one(updated[index], combos, rng, eqp_step_rows)
    return updated
