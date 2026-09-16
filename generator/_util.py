"""여러 generator 모듈이 함께 쓰는 자잘한 검증/계산 헬퍼."""
from decimal import Decimal, ROUND_HALF_UP


def positive_int(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive int, got {value!r}")
    return value


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
