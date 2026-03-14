from __future__ import annotations

from frappe.utils import getdate, now_datetime, nowdate, time_diff_in_hours


def is_trip_active(trip) -> bool:
    if getattr(trip, "trip_status", None) == "Cancelled":
        return False

    if getattr(trip, "actual_arrival_datetime", None) or getattr(trip, "trip_status", None) in ("Completed", "Closed"):
        return False

    trip_date = getattr(trip, "trip_date", None)
    if trip_date and getdate(trip_date) < getdate(nowdate()):
        return False

    creation = getattr(trip, "creation", None)
    if creation and time_diff_in_hours(now_datetime(), creation) > 12:
        return False

    return True
