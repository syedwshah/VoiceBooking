from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.utils.config import get_settings


def load_venues() -> List[Dict[str, Any]]:
    settings = get_settings()
    venue_path = Path(settings.venue_data_path)
    if not venue_path.exists():
        return []

    with venue_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_venue_by_id(venue_id: str) -> Dict[str, Any] | None:
    for venue in load_venues():
        if str(venue.get("id")) == str(venue_id):
            return venue
    return None
