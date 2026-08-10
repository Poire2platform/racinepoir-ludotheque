import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from .bgg import BggApiError, game_details, search_games
from .extensions import db
from .models import Game


BGG_DETAIL_FIELDS = (
    "title",
    "description",
    "publisher",
    "year_published",
    "min_players",
    "max_players",
    "min_playtime",
    "max_playtime",
    "age_min",
    "complexity",
    "cover_image_url",
)


def normalize_bgg_title(value):
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(character for character in text if not unicodedata.combining(character))
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def classify_matches(title, matches):
    normalized = normalize_bgg_title(title)
    exact = [
        match for match in matches
        if normalize_bgg_title(match.get("title")) == normalized
    ]
    if len(exact) == 1:
        return "exact_unique", exact[0]["bgg_id"]
    if len(exact) > 1:
        return "exact_ambiguous", None
    return "no_exact", None


def build_preview(output_path, delay_seconds=2.0, limit=None):
    query = db.select(Game).where(Game.bgg_id.is_(None)).order_by(Game.id.asc())
    games = list(db.session.execute(query).scalars())
    if limit is not None:
        games = games[:limit]

    items = []
    for index, game in enumerate(games):
        try:
            matches = search_games(game.title, limit=8)
            status, selected_bgg_id = classify_matches(game.title, matches)
            item = {
                "game_id": game.id,
                "title": game.title,
                "status": status,
                "selected_bgg_id": selected_bgg_id,
                "candidates": matches,
            }
        except BggApiError as error:
            item = {
                "game_id": game.id,
                "title": game.title,
                "status": "error",
                "selected_bgg_id": None,
                "candidates": [],
                "error": str(error),
            }
        items.append(item)
        if delay_seconds and index + 1 < len(games):
            time.sleep(delay_seconds)

    manifest = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
    Path(output_path).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def apply_preview(manifest_path, delay_seconds=2.0):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("version") != 1 or not isinstance(manifest.get("items"), list):
        raise ValueError("Format de manifeste BGG non reconnu.")

    report = {"enriched": 0, "skipped": 0, "errors": []}
    selected_items = [
        item for item in manifest["items"]
        if item.get("status") == "exact_unique" and item.get("selected_bgg_id")
    ]

    for index, item in enumerate(selected_items):
        game = db.session.get(Game, item.get("game_id"))
        if not game or game.title != item.get("title") or game.bgg_id is not None:
            report["skipped"] += 1
            continue
        bgg_id = int(item["selected_bgg_id"])
        conflict = db.session.execute(
            db.select(Game).where(Game.bgg_id == bgg_id)
        ).scalar_one_or_none()
        if conflict:
            report["errors"].append(f"BGG #{bgg_id} déjà lié à {conflict.title}.")
            continue
        try:
            details = game_details(bgg_id)
        except BggApiError as error:
            report["errors"].append(f"{game.title}: {error}")
            continue
        if not details:
            report["errors"].append(f"{game.title}: aucun détail pour BGG #{bgg_id}.")
            continue

        for field in BGG_DETAIL_FIELDS:
            setattr(game, field, details.get(field))
        game.bgg_id = bgg_id
        db.session.commit()
        report["enriched"] += 1
        if delay_seconds and index + 1 < len(selected_items):
            time.sleep(delay_seconds)

    return report
