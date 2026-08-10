import json
from unittest.mock import patch

from app.bgg_bulk import apply_preview, build_preview, classify_matches
from app.extensions import db
from app.models import Game


def test_classify_matches_does_not_choose_first_partial_result():
    matches = [
        {"bgg_id": "271512", "title": "5211: Azul", "year_published": "2019"},
        {"bgg_id": "230802", "title": "Azul", "year_published": "2017"},
    ]

    assert classify_matches("Azul", matches) == ("exact_unique", "230802")


def test_classify_matches_leaves_duplicate_exact_titles_ambiguous():
    matches = [
        {"bgg_id": "1", "title": "Café", "year_published": "2001"},
        {"bgg_id": "2", "title": "Cafe", "year_published": "2010"},
    ]

    assert classify_matches("Café", matches) == ("exact_ambiguous", None)


def test_preview_writes_manifest_without_database_changes(app, tmp_path):
    db.session.add_all([
        Game(title="Azul", normalized_title="azul"),
        Game(title="Bananagrame", normalized_title="bananagrame"),
    ])
    db.session.commit()
    output = tmp_path / "preview.json"

    with patch("app.bgg_bulk.search_games") as search:
        search.side_effect = [
            [{"bgg_id": "230802", "title": "Azul", "year_published": "2017"}],
            [{"bgg_id": "1", "title": "Bananagrams", "year_published": "2006"}],
        ]
        manifest = build_preview(output, delay_seconds=0)

    assert [item["status"] for item in manifest["items"]] == ["exact_unique", "no_exact"]
    assert json.loads(output.read_text())["version"] == 1
    assert all(game.bgg_id is None for game in Game.query.all())


def test_apply_preview_enriches_only_exact_unique_items(app, tmp_path):
    azul = Game(title="Azul", normalized_title="azul")
    ambiguous = Game(title="Café", normalized_title="café")
    db.session.add_all([azul, ambiguous])
    db.session.commit()
    manifest = {
        "version": 1,
        "items": [
            {"game_id": azul.id, "title": "Azul", "status": "exact_unique", "selected_bgg_id": "230802"},
            {"game_id": ambiguous.id, "title": "Café", "status": "exact_ambiguous", "selected_bgg_id": None},
        ],
    }
    path = tmp_path / "preview.json"
    path.write_text(json.dumps(manifest))
    details = {
        "bgg_id": 230802,
        "title": "Azul",
        "description": "Mosaïque.",
        "publisher": "Plan B Games",
        "year_published": 2017,
        "min_players": 2,
        "max_players": 4,
        "min_playtime": 30,
        "max_playtime": 45,
        "age_min": 8,
        "complexity": 1.75,
        "cover_image_url": "https://example.test/azul.jpg",
    }

    with patch("app.bgg_bulk.game_details", return_value=details):
        report = apply_preview(path, delay_seconds=0)

    assert report == {"enriched": 1, "skipped": 0, "errors": []}
    assert db.session.get(Game, azul.id).bgg_id == 230802
    assert db.session.get(Game, ambiguous.id).bgg_id is None
