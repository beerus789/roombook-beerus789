from datetime import datetime


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Return whether two half-open time ranges overlap."""
    return a_start < b_end and b_start < a_end
