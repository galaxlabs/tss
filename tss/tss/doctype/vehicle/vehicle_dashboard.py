from __future__ import annotations


def get_data(data=None):
    return {
        "fieldname": "vehicle",
        "transactions": [
            {
                "label": "Operations",
                "items": ["Trip", "Vehicle Inspection Log"],
            }
        ],
        "internal_links": {
            "Staff": ["assigned_driver"],
            "Route": ["default_route"],
        },
        "non_standard_fieldnames": {
            "Trip": "vehicle",
            "Vehicle Inspection Log": "vehicle",
        },
    }
