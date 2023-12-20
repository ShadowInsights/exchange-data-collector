from enum import Enum

from _decimal import Decimal


class TrendStatus(Enum):
    INCREASED = "increased"
    DECREASED = "decreased"


def define_trend_status_by_deviation(
    deviation: Decimal | int | None,
) -> TrendStatus:
    if deviation is None:
        deviation = 1

    return TrendStatus.DECREASED if deviation < 1 else TrendStatus.INCREASED
