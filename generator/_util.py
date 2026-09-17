"""여러 generator 모듈이 함께 쓰는 자잘한 검증/계산 헬퍼."""
from decimal import Decimal, ROUND_HALF_UP

# lot_id의 고정 자릿수. master.py의 eqp_id/resource_id와 같은 이유로
# lot_count 값과 무관하게 고정한다(lot_data.py, eqp_count_distribution.py
# 둘 다 lot_id를 만들므로 여기서 한 번만 정의해 공유한다).
LOT_ID_WIDTH = 4


def positive_int(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive int, got {value!r}")
    return value


def check_no_duplicates(ids: list, name: str) -> None:
    if len(set(ids)) != len(ids):
        raise ValueError(f"{name} must not contain duplicates")


def round_half_up(value) -> int:
    """config.md "반올림 규칙(전역)": 0.5 이상을 올리는 사사오입.

    표준 라이브러리 round()는 은행가 반올림(0.5를 짝수로)이라 이 규칙과
    다르게 동작한다(예: round(2.5) == 2). `math.floor(value + 0.5)`도
    안 되는데, 부동소수 덧셈 자체가 오차를 만들어 0.5 미만인 값이
    0.5로 반올림돼 버리는 경우가 있다. `Decimal(str(value))`로 value의
    "보이는 그대로의" 십진 표현을 취해 반올림하면 이 문제를 피한다 —
    다만 `value` 자체가 이미 부동소수 곱셈 등으로 오차를 포함하고
    있다면 그 오차까지 그대로 반영된다(예: `1500 * 0.009`는 부동소수로
    계산하면 정확히 13.5가 아닐 수 있다). 두 값을 곱한 결과를
    반올림해야 한다면 이 함수에 곱셈 결과를 직접 넘기지 말고
    `scaled_count()`를 대신 쓴다.
    """
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def scaled_count(multiplier, population: int) -> int:
    """population × multiplier를 Decimal로 정확히 곱한 뒤 위 사사오입
    규칙을 적용한다. `population * multiplier`를 먼저 float로 계산한
    뒤 반올림하면(예: `round_half_up(1500 * 0.009)`) 곱셈 자체의
    부동소수 오차가 반올림 결과를 바꿀 수 있어, 곱셈도 Decimal로
    한다."""
    exact = Decimal(str(population)) * Decimal(str(multiplier))
    return round_half_up(exact)


def effective_lot_count(config: dict) -> int:
    """config.md "유효 lot 수": factor가 있으면 scaled_count(factor, lot_count),
    없으면 lot_count 그대로."""
    scale = config["scale"]
    lot_count = positive_int(scale["lot_count"], "lot_count")
    factor = scale.get("factor")
    if factor is None:
        return lot_count
    if isinstance(factor, bool) or not isinstance(factor, (int, float)) or factor <= 0:
        raise ValueError(f"factor must be a positive number, got {factor!r}")
    count = scaled_count(factor, lot_count)
    if count < 1:
        raise ValueError(
            f"effective lot count rounds to {count} (lot_count={lot_count}, factor={factor}); "
            "must be at least 1"
        )
    return count


def eligible_eqp_count(candidate_pairs: list) -> int:
    """lot_data.md의 파생값 eligible_eqp_count: candidate_pairs의 중복
    없는 eqp 개수. 저장하지 않고 항상 candidate_pairs에서 계산한다."""
    return len({pair["eqp"] for pair in candidate_pairs})


def _check_ratio(ratio) -> None:
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)):
        raise ValueError(f"ratio must be a number, got {ratio!r}")
    if not 0 <= ratio <= 1:
        raise ValueError(f"ratio must be within 0..1, got {ratio}")


def _check_min_count(min_count) -> None:
    if isinstance(min_count, bool) or not isinstance(min_count, int):
        raise ValueError(f"min_count must be an int, got {min_count!r}")
    if min_count < 0:
        raise ValueError(f"min_count must be >= 0, got {min_count}")


def resolve_ratio_or_count(spec, population: int) -> int:
    """config.md "비율 또는 최소 건수" 공통 형식(전제 절)을 실제 목표
    건수로 바꾼다. `spec`은 숫자(비율, 0~1)이거나
    `{"ratio": ..., "min_count": ...}` 객체(둘 중 하나 이상)다. 반환값은
    `max(round(ratio*population), min_count)` — ratio로 계산한 건수가
    min_count보다 작을 때만 min_count로 끌어올린다는 규칙 그대로다."""
    if isinstance(spec, (int, float)) and not isinstance(spec, bool):
        _check_ratio(spec)
        return scaled_count(spec, population) if spec else 0
    if isinstance(spec, dict):
        unknown = set(spec) - {"ratio", "min_count"}
        if unknown:
            raise ValueError(f"unknown keys in ratio-or-count spec: {sorted(unknown)}")
        if "ratio" not in spec and "min_count" not in spec:
            raise ValueError(f"ratio-or-count spec must have ratio and/or min_count: {spec!r}")
        ratio = spec.get("ratio", 0)
        min_count = spec.get("min_count", 0)
        _check_ratio(ratio)
        _check_min_count(min_count)
        return max(scaled_count(ratio, population) if ratio else 0, min_count)
    raise ValueError(f"invalid ratio-or-count spec: {spec!r}")
