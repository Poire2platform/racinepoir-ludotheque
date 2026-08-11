from pathlib import Path

from app.extensions import db
from app.collection_import import replace_collection
from app.models import Box, BoxEvent, Game


SOURCE = """
<table>
<tr><td></td><td>De Kessé</td><td>sta ki</td><td>Youcéquecé</td><td>Min de Jeu</td></tr>
<tr><td></td><td>Azul</td><td>Anouk</td><td>Anouk</td><td>20-40</td></tr>
<tr><td></td><td>Long jeu</td><td>Anouk et Maxika</td><td>Chez Maxika</td><td>120 et +</td></tr>
<tr><td></td><td>Jeu Anika</td><td>Anika</td><td></td><td>10-20</td></tr>
<tr><td></td><td>Jeu Maxime</td><td>Maxime</td><td>chez Maxika</td><td></td></tr>
</table>
"""


def command(source, *, apply=False):
    args = [
        "import-official-collection",
        "--source", str(source),
        "--user-map", "Anouk=anouk",
        "--user-map", "Maxika=maxika",
        "--user-map", "Anika=anika",
        "--user-map", "Maxime=admin",
        "--default-holder", "admin",
    ]
    if apply:
        args.append("--apply")
    return args


def create_source(tmp_path):
    source = tmp_path / "collection.html"
    source.write_text(SOURCE, encoding="utf-8")
    return source


def test_collection_preview_has_no_writes(app, make_user, tmp_path):
    for username in ("admin", "anouk", "maxika", "anika"):
        make_user(username, role="admin" if username == "admin" else "member")
    runner = app.test_cli_runner()

    result = runner.invoke(args=command(create_source(tmp_path)))

    assert result.exit_code == 0
    assert "Lignes source : 4" in result.output
    assert "Jeux : 4 à créer, 0 existants" in result.output
    assert "Boîtes : 4 à créer, 0 existantes" in result.output
    assert "Aperçu seulement : aucune écriture." in result.output
    assert Game.query.count() == 0
    assert Box.query.count() == 0


def test_collection_import_requires_existing_users(app, make_user, tmp_path):
    make_user("admin", role="admin")
    runner = app.test_cli_runner()

    result = runner.invoke(args=command(create_source(tmp_path), apply=True))

    assert result.exit_code == 1
    assert "Comptes manquants : anika, anouk, maxika" in result.output
    assert "Aucune écriture" in result.output
    assert Game.query.count() == 0


def test_collection_import_is_non_destructive_and_idempotent(app, make_user, tmp_path):
    users = {
        username: make_user(username, role="admin" if username == "admin" else "member")
        for username in ("admin", "anouk", "maxika", "anika")
    }
    source = create_source(tmp_path)
    runner = app.test_cli_runner()

    first = runner.invoke(args=command(source, apply=True))
    first_counts = (Game.query.count(), Box.query.count(), BoxEvent.query.count())
    second = runner.invoke(args=command(source, apply=True))
    second_counts = (Game.query.count(), Box.query.count(), BoxEvent.query.count())

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert first_counts == (4, 4, 4)
    assert second_counts == first_counts
    assert "Boîtes : 0 à créer, 4 existantes" in second.output
    assert Box.query.filter_by(display_name="Long jeu").one().owner_user_id == users["anouk"].id
    assert Box.query.filter_by(display_name="Jeu Anika").one().current_holder_user_id == users["admin"].id
    long_game = Game.query.filter_by(title="Long jeu").one()
    assert (long_game.min_playtime, long_game.max_playtime) == (120, None)
    assert db.session.get(Game, long_game.id) is long_game


def test_replace_collection_preserves_users_and_replaces_games(app, make_user, tmp_path):
    users = {
        username: make_user(username, role="admin" if username == "admin" else "member")
        for username in ("admin", "anouk", "maxika")
    }
    old_game = Game(title="Ancien jeu", normalized_title="ancien jeu")
    db.session.add(old_game)
    db.session.flush()
    db.session.add(
        Box(
            display_name="Ancienne boîte",
            game_id=old_game.id,
            owner_user_id=users["admin"].id,
            current_holder_user_id=users["admin"].id,
            qr_code_token="old-box",
        )
    )
    db.session.commit()

    report = replace_collection(
        create_source(tmp_path),
        {
            "Anouk": "anouk",
            "Maxika": "maxika",
            "Anika": "anouk",
            "Maxime": "admin",
        },
        "admin",
    )

    assert report["rows"] == 4
    assert Game.query.filter_by(title="Ancien jeu").first() is None
    assert Box.query.filter_by(qr_code_token="old-box").first() is None
    assert Game.query.count() == 4
    assert Box.query.count() == 4
    from app.models import User

    assert set(users) <= {user.username for user in User.query.all()}
