"""여러 generator 모듈이 함께 쓰는 자잘한 검증/계산 헬퍼."""
import math


def positive_int(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive int, got {value!r}")
    return value


def round_half_up(value: float) -> int:
    """config.md "반올림 규칙(전역)": 0.5 이상을 올리는 사사오입.

    표준 라이브러리 round()는 은행가 반올림(0.5를 짝수로)이라 이 규칙과
    다르게 동작할 수 있어(예: round(2.5) == 2) 직접 구현한다.
    """
    return math.floor(value + 0.5)


def effective_lot_count(config: dict) -> int:
    """config.md "유효 lot 수": factor가 있으면 round_half_up(lot_count*factor),
    없으면 lot_count 그대로."""
    scale = config["scale"]
    lot_count = positive_int(scale["lot_count"], "lot_count")
    factor = scale.get("factor")
    if factor is None:
        return lot_count
    if isinstance(factor, bool) or not isinstance(factor, (int, float)) or factor <= 0:
        raise ValueError(f"factor must be a positive number, got {factor!r}")
    count = round_half_up(lot_count * factor)
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
