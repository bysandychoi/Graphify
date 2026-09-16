"""T012: 설비 층 배정(eqp_floor)과 resource id 마스터(resources) 생성.

docs/generator/config.md의 scale.eqp_count/resource_count/floor_count를
받아 docs/virtual_schema/location_floor.md의 eqp_floor,
docs/virtual_schema/resource_data.md의 resources를 생성한다. eqp_id
자체의 마스터 스키마(속성 등)는 정의 대상이 아니다(eqp_step_run_spec.md
"표현하지 않는 것" 참고) — 여기서 만드는 것은 eqp_id-층 매핑뿐이다.

id 자릿수는 eqp_count/resource_count에 따라 바뀌지 않는 고정폭이다 —
자릿수가 실제 개수에 따라 달라지면 소규모(스모크)와 대규모 데이터셋
사이에서 같은 순번의 설비/리소스가 서로 다른 id를 갖게 되어, 두
데이터셋을 비교하거나 fixture를 재사용할 때 조인이 조용히 깨진다.

seed 소비 방식(config.md "seed" 절이 T012 구현에 위임한 결정): 생성기
전체가 하나의 random.Random(seed) 인스턴스를 공유한다 — 이 모듈이 그
인스턴스를 만들거나 넘겨받아 소비하고, 이후 단계도 같은 인스턴스를
이어받아 쓴다고 가정한다.
"""
import random

from generator._util import positive_int

_EQP_ID_WIDTH = 4
_RESOURCE_ID_WIDTH = 4


def generate_equipment_floors(eqp_count: int, floor_count: int, rng: random.Random) -> list:
    eqp_count = positive_int(eqp_count, "eqp_count")
    floor_count = positive_int(floor_count, "floor_count")
    if floor_count > eqp_count:
        raise ValueError(
            f"floor_count ({floor_count}) must not exceed eqp_count ({eqp_count}): "
            "every floor needs at least one equipment on it"
        )
    # 층 1..floor_count를 먼저 한 번씩 배정해 모든 층이 채워짐을 보장하고,
    # 나머지 설비는 무작위로 채운 뒤 전체를 섞는다.
    floors = list(range(1, floor_count + 1))
    rng.shuffle(floors)
    floors += [rng.randint(1, floor_count) for _ in range(eqp_count - floor_count)]
    rng.shuffle(floors)
    return [
        {"eqp_id": f"M{i:0{_EQP_ID_WIDTH}d}", "floor": floor}
        for i, floor in zip(range(1, eqp_count + 1), floors)
    ]


def generate_resources(resource_count: int) -> list:
    resource_count = positive_int(resource_count, "resource_count")
    return [
        {"resource_id": f"R{i:0{_RESOURCE_ID_WIDTH}d}"}
        for i in range(1, resource_count + 1)
    ]


def generate_master_data(config: dict, rng: random.Random = None) -> dict:
    scale = config["scale"]
    if rng is None:
        rng = random.Random(config["seed"])
    return {
        "eqp_floor": generate_equipment_floors(scale["eqp_count"], scale["floor_count"], rng),
        "resources": generate_resources(scale["resource_count"]),
    }
