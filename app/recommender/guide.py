"""
Exercise guide loader.

Reads app/data/exercise_guide.json, which maps an exercise name (exactly as it
appears in new_cleaned_exercise_dataset.csv) to:
    muscle, equipment, level, steps[], images[], youtube_link

To add or change a demo, just edit that JSON file:
  - "youtube_link": paste a specific video URL (default is a YouTube search)
  - "steps":        list of short instructions shown as Step 1, Step 2, ...
  - "images":       paths relative to app/static/img/
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

GUIDE_PATH = Path(__file__).resolve().parent.parent / "data" / "exercise_guide.json"


@lru_cache(maxsize=1)
def get_exercise_guide() -> dict:
    try:
        with open(GUIDE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:  # missing/invalid file should never break the app
        logger.warning("Could not load exercise guide (%s): %s", GUIDE_PATH, exc)
        return {}
