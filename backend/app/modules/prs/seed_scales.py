"""
PRS Scale Seeder — reads JSON files from prs-frontend-app/data/ and seeds
the prs_scales and prs_condition_batteries tables.

Usage:
    python -m app.modules.prs.seed_scales
"""

import json
import uuid
from pathlib import Path
from app.core.database import get_supabase_client

SCALES_DIR = Path(__file__).resolve().parents[4] / "prs-frontend-app" / "data" / "scales"
CONDITION_MAP_PATH = Path(__file__).resolve().parents[4] / "prs-frontend-app" / "data" / "conditionMap.json"


def seed_scales():
    """Seed all scale JSON files into prs_scales table."""
    client = get_supabase_client()
    scale_files = sorted(SCALES_DIR.glob("*.json"))
    print(f"Found {len(scale_files)} scale files in {SCALES_DIR}")

    for filepath in scale_files:
        data = json.loads(filepath.read_text(encoding="utf-8"))
        scale_id = data.get("id", filepath.stem)

        # Check if already exists
        existing = (
            client.table("prs_scales")
            .select("id")
            .eq("scale_id", scale_id)
            .execute()
        )
        if existing.data:
            print(f"  SKIP  {scale_id} (already exists)")
            continue

        row = {
            "id": str(uuid.uuid4()),
            "scale_id": scale_id,
            "short_name": data.get("shortName", data.get("name", scale_id)),
            "full_name": data.get("name", scale_id),
            "category": data.get("category", "general"),
            "version": data.get("version", "1.0"),
            "scoring_type": data.get("scoringType", data.get("scoringMethod", "sum")),
            "max_score": data.get("maxScore"),
            "estimated_minutes": _parse_time(data.get("timeToComplete", "5")),
            "definition": data,
            "is_active": True,
            "is_clinician_rated": data.get("isClinicianRated", False),
            "languages": data.get("languages", ["en"]),
        }

        client.table("prs_scales").insert(row).execute()
        print(f"  SEED  {scale_id}")

    print(f"Scale seeding complete.")


def seed_conditions():
    """Seed conditionMap.json into prs_condition_batteries table."""
    client = get_supabase_client()

    if not CONDITION_MAP_PATH.exists():
        print(f"conditionMap.json not found at {CONDITION_MAP_PATH}")
        return

    condition_map = json.loads(CONDITION_MAP_PATH.read_text(encoding="utf-8"))
    conditions = condition_map if isinstance(condition_map, list) else condition_map.get("conditions", [])

    print(f"Found {len(conditions)} conditions")

    for i, cond in enumerate(conditions):
        condition_id = cond.get("id", cond.get("condition", f"condition-{i}"))

        existing = (
            client.table("prs_condition_batteries")
            .select("id")
            .eq("condition_id", condition_id)
            .execute()
        )
        if existing.data:
            print(f"  SKIP  {condition_id} (already exists)")
            continue

        row = {
            "id": str(uuid.uuid4()),
            "condition_id": condition_id,
            "label": cond.get("label", cond.get("name", condition_id)),
            "description": cond.get("description", ""),
            "scale_ids": cond.get("scales", cond.get("scaleIds", [])),
            "is_active": True,
            "display_order": i,
        }

        client.table("prs_condition_batteries").insert(row).execute()
        print(f"  SEED  {condition_id}")

    print(f"Condition seeding complete.")


def _parse_time(time_str) -> int:
    """Parse time strings like '5-10 minutes' to integer minutes."""
    if isinstance(time_str, int):
        return time_str
    import re
    numbers = re.findall(r"\d+", str(time_str))
    if numbers:
        return int(numbers[0])
    return 5


if __name__ == "__main__":
    print("=== PRS Scale Seeder ===")
    seed_scales()
    print()
    seed_conditions()
    print("\n=== Done ===")
