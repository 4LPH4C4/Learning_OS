from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class NextReview:
    due_on: date
    interval_days: int
    streak: int


def schedule_review(
    *,
    correct: bool,
    confidence: int,
    previous_streak: int = 0,
    today: date | None = None,
) -> NextReview:
    if not 1 <= confidence <= 5:
        raise ValueError("confidence는 1~5여야 한다")
    current = today or date.today()
    if not correct:
        interval = 1
        streak = 0
    else:
        streak = max(0, previous_streak) + 1
        if confidence <= 2:
            interval = 2
        else:
            interval = (4, 7, 14, 30)[min(streak, 4) - 1]
    return NextReview(
        due_on=current + timedelta(days=interval),
        interval_days=interval,
        streak=streak,
    )
