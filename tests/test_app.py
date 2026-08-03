from unittest.mock import Mock, patch

import pytest
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import Box, BoxEvent, BoxRequest, Game, GameRating, User


def test_healthz_reports_application_and_database_ready(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    assert response.get_json()["database"] == "ok"


def test_healthz_reports_database_unavailable_and_logs_failure(client):
    with (
        patch("app.routes.db.session.execute", side_effect=RuntimeError("database offline")),
        patch("app.routes.security_event") as security_log,
    ):
        response = client.get("/healthz")

    assert response.status_code == 503
    assert response.get_json()["status"] == "error"
    assert response.get_json()["database"] == "unavailable"
    assert response.get_json()["checked_at"]
    security_log.assert_called_once_with("health_check_failed", ip="127.0.0.1")


def test_error_responses_do_not_expose_tracebacks(app, client):
    bad_request_response = client.post("/logout")
    assert bad_request_response.status_code == 400
    assert "Demande invalide".encode() in bad_request_response.data
    assert "Jeton de formulaire invalide.".encode() in bad_request_response.data

    not_found_response = client.get("/route-that-does-not-exist")

    assert not_found_response.status_code == 404
    assert "Page introuvable".encode() in not_found_response.data
    assert b"Retour" in not_found_response.data
    assert b'role="alert"' in not_found_response.data
    assert b"Traceback" not in not_found_response.data

    def raise_unexpected_error():
        raise RuntimeError("internal diagnostic detail")

    app.view_functions["main.games"] = raise_unexpected_error
    app.config["PROPAGATE_EXCEPTIONS"] = False
    with patch.object(app.logger, "exception"):
        server_error_response = client.get("/games")

    assert server_error_response.status_code == 500
    assert "Erreur inattendue".encode() in server_error_response.data
    assert b'role="alert"' in server_error_response.data
    assert b"Traceback" not in server_error_response.data
    assert b"internal diagnostic detail" not in server_error_response.data


def test_empty_catalogs_explain_the_next_action(client):
    games_response = client.get("/games")
    boxes_response = client.get("/boxes?title=introuvable")

    assert games_response.status_code == 200
    assert b'class="empty-state"' in games_response.data
    assert b"Aucun jeu de r" in games_response.data
    assert boxes_response.status_code == 200
    assert b'class="empty-state"' in boxes_response.data
    assert "Aucune boîte ne correspond à ces filtres.".encode() in boxes_response.data
    assert b"R\xc3\xa9initialiser les filtres" in boxes_response.data


def test_login_accepts_valid_credentials(client, make_user, csrf_token):
    make_user("max", password="correct-password")

    response = client.post(
        "/login",
        data={
            "_csrf_token": csrf_token,
            "username": "max",
            "password": "correct-password",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_login_returns_anonymous_scanner_to_scan_confirmation(
    client,
    make_user,
    make_box,
    csrf_token,
):
    owner = make_user("owner")
    scanner = make_user("scanner")
    make_box(owner, token="return-to-scan")

    anonymous_response = client.get("/scan/return-to-scan")

    assert anonymous_response.status_code == 302
    assert anonymous_response.headers["Location"].endswith(
        "/login?next=%2Fscan%2Freturn-to-scan"
    )

    login_response = client.post(
        "/login",
        data={
            "_csrf_token": csrf_token,
            "username": scanner.username,
            "password": "secret123",
            "next": "/scan/return-to-scan",
        },
    )

    assert login_response.status_code == 302
    assert login_response.headers["Location"] == "/scan/return-to-scan"
    confirmation_response = client.get(login_response.headers["Location"])
    assert confirmation_response.status_code == 200
    assert b"Confirmer le scan" in confirmation_response.data
    assert b"Owner" in confirmation_response.data


def test_login_rejects_external_next_redirect(client, make_user, csrf_token):
    make_user("member")

    response = client.post(
        "/login",
        data={
            "_csrf_token": csrf_token,
            "username": "member",
            "password": "secret123",
            "next": "//malicious.example.test/phishing",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_login_rate_limit_blocks_repeated_attempts_but_not_other_username(
    client,
    make_user,
    csrf_token,
    monkeypatch,
):
    make_user("target", password="correct-password")
    make_user("other", password="correct-password")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_ATTEMPTS", "2")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300")

    with patch("app.routes.security_event") as security_log:
        for _ in range(2):
            response = client.post(
                "/login",
                data={
                    "_csrf_token": csrf_token,
                    "username": "target",
                    "password": "wrong-password",
                },
            )
            assert response.status_code == 200

        blocked_response = client.post(
            "/login",
            data={
                "_csrf_token": csrf_token,
                "username": "target",
                "password": "correct-password",
            },
        )
        other_response = client.post(
            "/login",
            data={
                "_csrf_token": csrf_token,
                "username": "other",
                "password": "correct-password",
            },
        )

    assert blocked_response.status_code == 429
    assert "Trop d’essais.".encode() in blocked_response.data
    assert other_response.status_code == 302
    assert "login_rate_limited" in [call.args[0] for call in security_log.call_args_list]


def test_login_rejects_invalid_credentials(client, make_user, csrf_token):
    make_user("max", password="correct-password")

    response = client.post(
        "/login",
        data={
            "_csrf_token": csrf_token,
            "username": "max",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 200
    assert "Login invalide.".encode() in response.data


def test_inactive_account_cannot_log_in(client, make_user, csrf_token):
    make_user("inactive", is_active=False)

    response = client.post(
        "/login",
        data={
            "_csrf_token": csrf_token,
            "username": "inactive",
            "password": "secret123",
        },
    )

    assert response.status_code == 200
    assert "Compte désactivé.".encode() in response.data
    assert client.get("/").status_code == 302


def test_authenticated_session_remains_active_across_requests(
    client,
    make_user,
    login_as,
):
    member = make_user("member")
    login_as(member)

    first_response = client.get("/")
    second_response = client.get("/me/profile")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert b"username: <code>member</code>" in first_response.data


def test_logout_ends_authenticated_session(
    client,
    make_user,
    login_as,
    csrf_token,
):
    member = make_user("member")
    login_as(member)

    response = client.post(
        "/logout",
        data={"_csrf_token": csrf_token},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    protected_response = client.get("/")
    assert protected_response.status_code == 302
    assert "/login" in protected_response.headers["Location"]


def test_member_is_denied_admin_user_management(
    client,
    make_user,
    login_as,
):
    member = make_user("member")
    login_as(member)

    response = client.get("/users")

    assert response.status_code == 403


def test_admin_can_access_user_management(client, make_user, login_as):
    admin = make_user("admin", role="admin")
    login_as(admin)

    response = client.get("/users")

    assert response.status_code == 200
    assert "Utilisateurs".encode() in response.data


def test_admin_can_create_user_with_role_and_activation_state(
    app,
    client,
    make_user,
    login_as,
    csrf_token,
):
    admin = make_user("admin", role="admin")
    login_as(admin)

    response = client.post(
        "/users/new",
        data={
            "_csrf_token": csrf_token,
            "username": "gestionnaire",
            "email": "gestionnaire@example.test",
            "display_name": "Gestionnaire",
            "password": "temporary-password",
            "confirm_password": "temporary-password",
            "role": "admin",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/users"
    with app.app_context():
        user = User.query.filter_by(username="gestionnaire").one()
        assert user.email == "gestionnaire@example.test"
        assert user.display_name == "Gestionnaire"
        assert user.role == "admin"
        assert user.is_active is False
        assert check_password_hash(user.password_hash, "temporary-password")


def test_admin_user_creation_rejects_password_mismatch(
    app,
    client,
    make_user,
    login_as,
    csrf_token,
):
    admin = make_user("admin", role="admin")
    login_as(admin)

    response = client.post(
        "/users/new",
        data={
            "_csrf_token": csrf_token,
            "username": "gestionnaire",
            "email": "gestionnaire@example.test",
            "display_name": "Gestionnaire",
            "password": "temporary-password",
            "confirm_password": "different-password",
            "role": "member",
        },
    )

    assert response.status_code == 200
    assert "Les mots de passe ne correspondent pas.".encode() in response.data
    with app.app_context():
        assert User.query.filter_by(username="gestionnaire").first() is None


def test_admin_can_edit_role_activation_and_password(
    app,
    client,
    make_user,
    login_as,
    csrf_token,
):
    admin = make_user("admin", role="admin")
    member = make_user("member", is_active=False)
    login_as(admin)

    response = client.post(
        f"/users/{member.id}/edit",
        data={
            "_csrf_token": csrf_token,
            "username": "member-renamed",
            "email": "renamed@example.test",
            "display_name": "Membre renommé",
            "password": "new-password",
            "confirm_password": "new-password",
            "role": "admin",
            "is_active": "yes",
        },
    )

    assert response.status_code == 302
    with app.app_context():
        refreshed_user = db.session.get(User, member.id)
        assert refreshed_user.username == "member-renamed"
        assert refreshed_user.email == "renamed@example.test"
        assert refreshed_user.display_name == "Membre renommé"
        assert refreshed_user.role == "admin"
        assert refreshed_user.is_active is True
        assert check_password_hash(refreshed_user.password_hash, "new-password")


def test_edit_user_rejects_password_mismatch_without_changing_user(
    app,
    client,
    make_user,
    login_as,
    csrf_token,
):
    admin = make_user("admin", role="admin")
    member = make_user("member")
    login_as(admin)

    response = client.post(
        f"/users/{member.id}/edit",
        data={
            "_csrf_token": csrf_token,
            "username": "member-renamed",
            "email": "renamed@example.test",
            "display_name": "Membre renommé",
            "password": "new-password",
            "confirm_password": "different-password",
            "role": "admin",
            "is_active": "yes",
        },
    )

    assert response.status_code == 200
    assert "Les mots de passe ne correspondent pas.".encode() in response.data
    with app.app_context():
        refreshed_user = db.session.get(User, member.id)
        assert refreshed_user.username == "member"
        assert refreshed_user.email == "member@example.test"
        assert refreshed_user.display_name == "Member"
        assert refreshed_user.role == "member"
        assert check_password_hash(refreshed_user.password_hash, "secret123")


def test_edit_user_rejects_invalid_role_without_changing_user(
    app,
    client,
    make_user,
    login_as,
    csrf_token,
):
    admin = make_user("admin", role="admin")
    member = make_user("member")
    login_as(admin)

    response = client.post(
        f"/users/{member.id}/edit",
        data={
            "_csrf_token": csrf_token,
            "username": "changed",
            "email": "changed@example.test",
            "display_name": "Changed",
            "role": "superadmin",
        },
    )

    assert response.status_code == 200
    assert "Le rôle sélectionné est invalide.".encode() in response.data
    with app.app_context():
        refreshed_user = db.session.get(User, member.id)
        assert refreshed_user.username == "member"
        assert refreshed_user.email == "member@example.test"
        assert refreshed_user.display_name == "Member"
        assert refreshed_user.role == "member"
        assert refreshed_user.is_active is True


def test_game_catalog_lists_games_with_reference_information(app, client):
    with app.app_context():
        db.session.add_all([
            Game(title="Catan", language="fr", min_players=3, max_players=4),
            Game(
                title="Azul",
                language="fr",
                min_players=2,
                max_players=4,
                min_playtime=30,
                max_playtime=45,
                year_published=2017,
                bgg_id=230802,
                cover_image_url="https://images.example.test/azul.jpg",
            ),
        ])
        db.session.commit()

    response = client.get("/games")

    assert response.status_code == 200
    assert response.data.index(b"Azul") < response.data.index(b"Catan")
    assert b"2\xe2\x80\x934" in response.data
    assert b"30\xe2\x80\x9345 min" in response.data
    assert b"2017" in response.data
    assert b"Reconnu" in response.data
    assert "Liste détaillée".encode() in response.data
    assert b"Miniatures" in response.data
    assert b'id="games-list-view"' in response.data
    assert b'id="games-grid-view"' in response.data
    assert b"https://images.example.test/azul.jpg" in response.data
    assert "Aucune couverture disponible pour Catan".encode() in response.data
    assert b"racinepoir-games-view" in response.data
    assert b'<th scope="col">ID</th>' not in response.data
    assert b'class="collection-list-view table-scroll"' in response.data
    assert "glisse horizontalement".encode() in response.data


def test_game_detail_displays_reference_data_and_linked_boxes(
    app,
    client,
    make_user,
    make_box,
):
    owner = make_user("owner")
    box = make_box(owner, title="Azul")
    with app.app_context():
        game = db.session.get(Game, box.game_id)
        game.language = "fr"
        game.edition_name = "Édition française"
        game.publisher = "Plan B Games"
        game.description = "Jeu de placement de tuiles."
        game.year_published = 2017
        game.min_players = 2
        game.max_players = 4
        game.min_playtime = 30
        game.max_playtime = 45
        game.age_min = 8
        game.bgg_id = 230802
        db.session.commit()
        game_id = game.id

    response = client.get(f"/games/{game_id}")

    assert response.status_code == 200
    assert b"Azul" in response.data
    assert "Édition française".encode() in response.data
    assert b"Plan B Games" in response.data
    assert b"Jeu de placement de tuiles." in response.data
    assert b"Consulter la page BGG #230802" in response.data
    assert b"https://boardgamegeek.com/boardgame/230802" in response.data
    assert b"Owner" in response.data
    assert f'/boxes/{box.id}'.encode() in response.data


def test_game_detail_returns_not_found_for_unknown_game(client):
    assert client.get("/games/999999").status_code == 404


def test_players_can_rate_game_and_median_is_displayed(
    app,
    client,
    make_user,
    make_box,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    second_player = make_user("second")
    box = make_box(owner, title="Azul")

    login_as(owner)
    first_response = client.post(
        f"/games/{box.game_id}/rating",
        data={"_csrf_token": csrf_token, "score_percent": "80"},
    )
    assert first_response.status_code == 302

    client.post("/logout", data={"_csrf_token": csrf_token})
    login_as(second_player)
    second_response = client.post(
        f"/games/{box.game_id}/rating",
        data={"_csrf_token": csrf_token, "score_percent": "40"},
    )
    assert second_response.status_code == 302

    catalog_response = client.get("/games")
    detail_response = client.get(f"/games/{box.game_id}")
    assert b"60 % (2)" in catalog_response.data
    assert b"60 % sur 2 note(s)" in detail_response.data

    with app.app_context():
        assert GameRating.query.filter_by(game_id=box.game_id).count() == 2


def test_player_can_update_rating_without_creating_duplicate(
    app,
    client,
    make_user,
    make_box,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    player = make_user("player")
    box = make_box(owner)
    with app.app_context():
        db.session.add(GameRating(game_id=box.game_id, user_id=owner.id, score_percent=40))
        db.session.commit()

    login_as(player)
    client.post(
        f"/games/{box.game_id}/rating",
        data={"_csrf_token": csrf_token, "score_percent": "80"},
    )
    update_response = client.post(
        f"/games/{box.game_id}/rating",
        data={"_csrf_token": csrf_token, "score_percent": "90"},
    )

    assert update_response.status_code == 302
    detail_response = client.get(f"/games/{box.game_id}")
    assert b"65 % sur 2 note(s)" in detail_response.data
    assert b'value="90"' in detail_response.data
    assert b"Modifier ma note" in detail_response.data
    with app.app_context():
        ratings = GameRating.query.filter_by(game_id=box.game_id).all()
        assert sorted(rating.score_percent for rating in ratings) == [40, 90]


@pytest.mark.parametrize("score", ("abc", "-1", "101"))
def test_game_rating_rejects_invalid_percentages_without_mutation(
    score,
    app,
    client,
    make_user,
    make_box,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    box = make_box(owner)
    login_as(owner)

    response = client.post(
        f"/games/{box.game_id}/rating",
        data={"_csrf_token": csrf_token, "score_percent": score},
    )

    assert response.status_code == 400
    with app.app_context():
        assert GameRating.query.count() == 0


def test_bgg_enrichment_search_displays_matches_without_changing_game(
    app,
    client,
    make_user,
    login_as,
):
    user = make_user("member")
    login_as(user)
    with app.app_context():
        game = Game(title="Azul inconnu", normalized_title="azul inconnu")
        db.session.add(game)
        db.session.commit()
        game_id = game.id

    matches = [{"bgg_id": "230802", "title": "Azul", "year_published": "2017"}]
    with patch("app.routes.search_games", return_value=matches) as search:
        response = client.get(f"/games/{game_id}/bgg")

    assert response.status_code == 200
    assert b"Azul (2017)" in response.data
    search.assert_called_once_with("Azul inconnu")
    with app.app_context():
        unchanged_game = db.session.get(Game, game_id)
        assert unchanged_game.title == "Azul inconnu"
        assert unchanged_game.bgg_id is None


def test_bgg_enrichment_imports_selected_details_and_updates_linked_boxes(
    app,
    client,
    make_user,
    make_box,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    box = make_box(owner, title="Azul inconnu")
    login_as(owner)
    details = {
        "bgg_id": 230802,
        "title": "Azul",
        "description": "Jeu de placement de tuiles.",
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

    with patch("app.routes.game_details", return_value=details) as fetch_details:
        response = client.post(
            f"/games/{box.game_id}/bgg",
            data={"_csrf_token": csrf_token, "bgg_choice": "230802"},
        )

    assert response.status_code == 302
    fetch_details.assert_called_once_with("230802")
    with app.app_context():
        enriched_game = db.session.get(Game, box.game_id)
        linked_box = db.session.get(Box, box.id)
        assert enriched_game.title == "Azul"
        assert enriched_game.bgg_id == 230802
        assert enriched_game.publisher == "Plan B Games"
        assert enriched_game.min_players == 2
        assert enriched_game.max_players == 4
        assert linked_box.display_name == "Azul"


def test_manual_box_creation_does_not_require_bgg(
    app,
    client,
    make_user,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    login_as(owner)

    with patch("app.routes.search_games", return_value=[]):
        response = client.post(
            "/boxes/new",
            data={
                "_csrf_token": csrf_token,
                "game_id": "__new__",
                "new_game_title": "Mon jeu test",
                "owner_user_id": str(owner.id),
                "condition": "good",
                "notes": "Création manuelle",
            },
        )

    assert response.status_code == 302
    with app.app_context():
        assert Game.query.filter_by(title="Mon jeu test").count() == 1
        box = Box.query.one()
        assert box.owner_user_id == owner.id
        assert box.current_holder_user_id == owner.id
        assert BoxEvent.query.filter_by(event_type="box_created").count() == 1


def test_uncatalogued_box_can_be_created_without_game(
    app,
    client,
    make_user,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    login_as(owner)

    response = client.post(
        "/boxes/new",
        data={
            "_csrf_token": csrf_token,
            "game_id": "__uncatalogued__",
            "uncatalogued_box_name": "  Prototype maison  ",
            "owner_user_id": str(owner.id),
            "condition": "unknown",
        },
    )

    assert response.status_code == 302
    with app.app_context():
        box = Box.query.one()
        assert box.display_name == "Prototype maison"
        assert box.game_id is None
        assert box.owner_user_id == owner.id
        assert box.current_holder_user_id == owner.id
        assert Game.query.count() == 0


def test_uncatalogued_box_requires_a_display_name(
    app,
    client,
    make_user,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    login_as(owner)

    response = client.post(
        "/boxes/new",
        data={
            "_csrf_token": csrf_token,
            "game_id": "__uncatalogued__",
            "uncatalogued_box_name": " ",
            "owner_user_id": str(owner.id),
        },
    )

    assert response.status_code == 200
    assert "Le nom de la boîte non cataloguée est obligatoire.".encode() in response.data
    with app.app_context():
        assert Box.query.count() == 0
        assert Game.query.count() == 0


def test_box_can_be_changed_to_uncatalogued(
    app,
    client,
    make_user,
    make_box,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    box = make_box(owner, title="Ancien jeu")
    login_as(owner)

    edit_page = client.get(f"/boxes/{box.id}/edit")
    assert edit_page.status_code == 200

    response = client.post(
        f"/boxes/{box.id}/edit",
        data={
            "_csrf_token": csrf_token,
            "game_id": "__uncatalogued__",
            "uncatalogued_box_name": "Boîte mystère",
            "owner_user_id": str(owner.id),
            "condition": "worn",
        },
    )

    assert response.status_code == 302
    with app.app_context():
        refreshed_box = db.session.get(Box, box.id)
        assert refreshed_box.display_name == "Boîte mystère"
        assert refreshed_box.game_id is None
        assert refreshed_box.condition == "worn"

    uncatalogued_edit_page = client.get(f"/boxes/{box.id}/edit")
    assert uncatalogued_edit_page.status_code == 200
    assert b'value="__uncatalogued__" selected' in uncatalogued_edit_page.data
    assert b'value="Bo\xc3\xaete myst\xc3\xa8re"' in uncatalogued_edit_page.data


def test_owner_can_edit_box_details_and_records_event(
    app,
    client,
    make_user,
    make_box,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    new_owner = make_user("newowner")
    box = make_box(owner, title="Ancien jeu")
    replacement_game = Game(title="Nouveau jeu", normalized_title="nouveau jeu")
    db.session.add(replacement_game)
    db.session.commit()
    login_as(owner)

    response = client.post(
        f"/boxes/{box.id}/edit",
        data={
            "_csrf_token": csrf_token,
            "game_id": str(replacement_game.id),
            "owner_user_id": str(new_owner.id),
            "condition": "incomplete",
            "notes": "  Il manque un pion.  ",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == f"/boxes/{box.id}"
    with app.app_context():
        refreshed_box = db.session.get(Box, box.id)
        assert refreshed_box.game_id == replacement_game.id
        assert refreshed_box.display_name == "Nouveau jeu"
        assert refreshed_box.owner_user_id == new_owner.id
        assert refreshed_box.condition == "incomplete"
        assert refreshed_box.notes == "Il manque un pion."

        event = BoxEvent.query.filter_by(
            box_id=box.id,
            event_type="box_updated",
        ).one()
        assert event.actor_user_id == owner.id


def test_edit_box_rejects_unknown_game_without_changing_box(
    app,
    client,
    make_user,
    make_box,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    box = make_box(owner, title="Jeu intact")
    original_game_id = box.game_id
    login_as(owner)

    response = client.post(
        f"/boxes/{box.id}/edit",
        data={
            "_csrf_token": csrf_token,
            "game_id": "999999",
            "owner_user_id": str(owner.id),
            "condition": "worn",
            "notes": "Ne doit pas être enregistré",
        },
    )

    assert response.status_code == 200
    assert "Le jeu référencé sélectionné est introuvable.".encode() in response.data
    with app.app_context():
        refreshed_box = db.session.get(Box, box.id)
        assert refreshed_box.game_id == original_game_id
        assert refreshed_box.display_name == "Jeu intact"
        assert refreshed_box.condition == "good"
        assert refreshed_box.notes is None
        assert BoxEvent.query.filter_by(
            box_id=box.id,
            event_type="box_updated",
        ).count() == 0


def test_interest_flag_is_available_without_priority_or_duplicates(
    app,
    client,
    make_user,
    make_box,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    interested = make_user("interested")
    box = make_box(owner, token="interest")

    login_as(interested)
    list_response = client.get("/boxes")
    game_response = client.get(f"/games/{box.game_id}")
    detail_response = client.get(f"/boxes/{box.id}")
    for response in (list_response, game_response, detail_response):
        assert response.status_code == 200
        assert b">I would like</button>" in response.data

    creation_response = client.post(
        f"/boxes/{box.id}/request",
        data={"_csrf_token": csrf_token},
    )
    assert creation_response.status_code == 302

    detail_response = client.get(f"/boxes/{box.id}")
    assert detail_response.status_code == 200
    assert b"<h3>Int" in detail_response.data
    assert "Interested — toi".encode() in detail_response.data
    assert b'<span class="badge badge--warning">I would like</span>' in detail_response.data
    assert "file d’attente".encode() not in detail_response.data
    assert b"Tu es #" not in detail_response.data
    assert b"Annuler" not in detail_response.data
    home_response = client.get("/")
    assert home_response.status_code == 200
    assert "Mes marqueurs « I would like »".encode() in home_response.data
    assert "1 marqueur(s) actif(s).".encode() in home_response.data
    assert f'/boxes/{box.id}'.encode() in home_response.data
    assert b'href="/me/interested-boxes"' in home_response.data

    interested_response = client.get("/me/interested-boxes")
    assert interested_response.status_code == 200
    assert box.display_label.encode() in interested_response.data
    assert b'id="interested-boxes-grid-view"' in interested_response.data

    duplicate_response = client.post(
        f"/boxes/{box.id}/request",
        data={"_csrf_token": csrf_token},
    )
    assert duplicate_response.status_code == 302

    with app.app_context():
        flags = BoxRequest.query.filter_by(box_id=box.id, status="active").all()
        assert [flag.requester_user_id for flag in flags] == [interested.id]
        assert BoxEvent.query.filter_by(
            box_id=box.id,
            event_type="box_interest_flagged",
        ).count() == 1


def test_direct_scan_changes_holder_and_records_history(
    app,
    client,
    make_user,
    make_box,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    scanner = make_user("scanner")
    box = make_box(owner, token="direct-scan")
    login_as(scanner)

    confirmation_page = client.get("/scan/direct-scan")
    assert confirmation_page.status_code == 200
    assert b"Owner" in confirmation_page.data

    response = client.post(
        "/scan/direct-scan/confirm",
        data={"_csrf_token": csrf_token},
    )

    assert response.status_code == 200
    assert b"Scanner" in response.data
    assert "Ancien détenteur : Owner".encode() in response.data
    with app.app_context():
        refreshed_box = db.session.get(Box, box.id)
        event = BoxEvent.query.filter_by(
            box_id=box.id,
            event_type="box_claimed",
        ).one()
        assert refreshed_box.current_holder_user_id == scanner.id
        assert event.actor_user_id == scanner.id
        assert event.from_holder_user_id == owner.id
        assert event.to_holder_user_id == scanner.id


def test_scan_changes_holder_and_completes_interest_flag(
    app,
    client,
    make_user,
    make_box,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    requester = make_user("requester")
    observer = make_user("observer")
    box = make_box(owner, token="scan-me")
    box_request = BoxRequest(
        box_id=box.id,
        requester_user_id=requester.id,
        status="active",
    )
    observer_flag = BoxRequest(
        box_id=box.id,
        requester_user_id=observer.id,
        status="active",
    )
    db.session.add_all([box_request, observer_flag])
    db.session.commit()
    login_as(requester)

    response = client.post(
        "/scan/scan-me/confirm",
        data={"_csrf_token": csrf_token},
    )

    assert response.status_code == 200
    assert "Ton signal « I would like » a été marqué comme complété.".encode() in response.data
    with app.app_context():
        refreshed_box = db.session.get(Box, box.id)
        refreshed_request = db.session.get(BoxRequest, box_request.id)
        refreshed_observer_flag = db.session.get(BoxRequest, observer_flag.id)
        assert refreshed_box.current_holder_user_id == requester.id
        assert refreshed_request.status == "fulfilled"
        assert refreshed_request.fulfilled_at is not None
        assert refreshed_observer_flag.status == "active"
        assert refreshed_observer_flag.fulfilled_at is None
        assert BoxEvent.query.filter_by(
            box_id=box.id,
            event_type="box_interest_fulfilled",
        ).count() == 1


def test_scan_rate_limit_blocks_repeat_without_second_mutation(
    app,
    client,
    make_user,
    make_box,
    login_as,
    csrf_token,
    monkeypatch,
):
    owner = make_user("owner")
    scanner = make_user("scanner")
    box = make_box(owner, token="limited-scan")
    login_as(scanner)
    monkeypatch.setenv("SCAN_CONFIRM_RATE_LIMIT_ATTEMPTS", "1")
    monkeypatch.setenv("SCAN_CONFIRM_RATE_LIMIT_WINDOW_SECONDS", "300")

    with patch("app.routes.security_event") as security_log:
        first_response = client.post(
            "/scan/limited-scan/confirm",
            data={"_csrf_token": csrf_token},
        )
        with app.app_context():
            event_count_after_first_scan = BoxEvent.query.filter_by(box_id=box.id).count()

        blocked_response = client.post(
            "/scan/limited-scan/confirm",
            data={"_csrf_token": csrf_token},
        )

    assert first_response.status_code == 200
    assert blocked_response.status_code == 429
    assert "Trop de confirmations de scan.".encode() in blocked_response.data
    assert "scan_confirm_rate_limited" in [call.args[0] for call in security_log.call_args_list]
    with app.app_context():
        refreshed_box = db.session.get(Box, box.id)
        assert refreshed_box.current_holder_user_id == scanner.id
        assert BoxEvent.query.filter_by(box_id=box.id).count() == event_count_after_first_scan


def test_authenticated_navigation_smoke(
    client,
    make_user,
    make_box,
    login_as,
):
    admin = make_user("admin", role="admin")
    box = make_box(admin, token="smoke-box")
    login_as(admin)

    paths = (
        "/",
        "/games",
        f"/games/{box.game_id}",
        "/boxes",
        f"/boxes/{box.id}",
        "/me/held-boxes",
        "/me/owned-boxes",
        "/me/interested-boxes",
        "/sessions",
        "/players",
        "/users",
        "/scan/smoke-box",
        "/healthz",
    )

    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, path


def test_mobile_navigation_structure_and_scan_primary_action(
    client,
    make_user,
    make_box,
    login_as,
):
    owner = make_user("owner")
    box = make_box(owner, token="mobile-scan")
    login_as(owner)

    home_response = client.get("/")
    scan_response = client.get("/scan/mobile-scan")

    assert home_response.status_code == 200
    assert b'name="viewport"' in home_response.data
    assert b'class="primary-nav"' in home_response.data
    assert b'class="member-nav"' in home_response.data
    assert b'class="scorebook-nav"' in home_response.data
    assert b'aria-label="Navigation principale"' in home_response.data
    assert b'aria-label="Carnet de pointage"' in home_response.data
    primary_navigation = home_response.data.split(b'<nav class="primary-nav"', 1)[1].split(b"</nav>", 1)[0]
    scorebook_navigation = home_response.data.split(b'<nav class="scorebook-nav"', 1)[1].split(b"</nav>", 1)[0]
    assert b'href="/sessions"' not in primary_navigation
    assert b'href="/players"' not in primary_navigation
    assert b'href="/sessions"' in scorebook_navigation
    assert b'href="/players"' in scorebook_navigation
    assert b'href="/me/held-boxes"' in home_response.data
    assert b'href="/me/interested-boxes"' in home_response.data
    assert scan_response.status_code == 200
    assert b'class="scan-action"' in scan_response.data
    assert b'class="primary-action"' in scan_response.data


def test_accessibility_foundations_are_present(
    client,
    make_user,
    make_box,
    login_as,
):
    login_response = client.get("/login")
    assert b'href="#main-content"' in login_response.data
    assert b'id="main-content" tabindex="-1"' in login_response.data
    assert b'label for="login-username"' in login_response.data
    assert b'id="login-username"' in login_response.data
    assert b'autocomplete="username"' in login_response.data
    assert b'label for="login-password"' in login_response.data
    assert b'autocomplete="current-password"' in login_response.data
    assert b":focus-visible" in login_response.data

    owner = make_user("owner")
    make_box(owner)
    login_as(owner)
    games_response = client.get("/games")
    session_form_response = client.get("/sessions/new")

    assert b'<caption class="visually-hidden">Liste d' in games_response.data
    assert b'<th scope="col">Titre</th>' in games_response.data
    assert b"Joueurs participant" in session_form_response.data
    assert 'aria-label="Utilisateur, joueur 1"'.encode() in session_form_response.data
    assert 'aria-label="Notes, joueur 1"'.encode() in session_form_response.data


def test_my_held_boxes_filters_by_current_holder_not_owner(
    client,
    make_user,
    make_box,
    login_as,
):
    member = make_user("member")
    other = make_user("other")
    borrowed_box = make_box(
        other,
        holder=member,
        title="Borrowed game",
        token="borrowed",
    )
    owned_and_held_box = make_box(
        member,
        title="Owned here",
        token="owned-here",
    )
    owned_elsewhere_box = make_box(
        member,
        holder=other,
        title="Owned elsewhere",
        token="owned-elsewhere",
    )
    login_as(member)

    response = client.get("/me/held-boxes")

    assert response.status_code == 200
    borrowed_label = borrowed_box.display_label.encode()
    owned_here_label = owned_and_held_box.display_label.encode()
    assert borrowed_label in response.data
    assert owned_here_label in response.data
    assert owned_elsewhere_box.display_label.encode() not in response.data
    assert response.data.index(borrowed_label) < response.data.index(owned_here_label)
    assert response.data.count(b">Chez moi</span>") == 2
    assert response.data.count(">À moi</span>".encode()) == 1
    assert b'id="held-boxes-list-view"' in response.data
    assert b'id="held-boxes-grid-view"' in response.data
    assert b"racinepoir-held-boxes-view" in response.data


def test_my_owned_boxes_filters_by_owner_and_displays_current_holder(
    client,
    make_user,
    make_box,
    login_as,
):
    member = make_user("member")
    other = make_user("other")
    interested = make_user("interested")
    owned_elsewhere_box = make_box(
        member,
        holder=other,
        title="Away game",
        token="away",
    )
    owned_here_box = make_box(
        member,
        title="Home game",
        token="home",
    )
    borrowed_box = make_box(
        other,
        holder=member,
        title="Borrowed game",
        token="borrowed-owned-view",
    )
    db.session.add(
        BoxRequest(
            box=owned_elsewhere_box,
            requester=interested,
            status="active",
        )
    )
    db.session.commit()
    login_as(member)

    response = client.get("/me/owned-boxes")

    assert response.status_code == 200
    away_label = owned_elsewhere_box.display_label.encode()
    home_label = owned_here_box.display_label.encode()
    assert away_label in response.data
    assert home_label in response.data
    assert borrowed_box.display_label.encode() not in response.data
    assert response.data.index(away_label) < response.data.index(home_label)
    assert "détenteur :\n                \n                    Other".encode() in response.data
    assert "1 intéressé(s)".encode() in response.data
    assert b"/edit" in response.data
    assert b"/label" in response.data
    assert b'id="owned-boxes-list-view"' in response.data
    assert b'id="owned-boxes-grid-view"' in response.data
    assert b"racinepoir-owned-boxes-view" in response.data


def test_boxes_can_be_searched_by_title(client, make_user, make_box):
    owner = make_user("owner")
    make_box(owner, title="Azul", token="azul")
    make_box(owner, title="Catan", token="catan")

    response = client.get("/boxes?title=azu")

    assert response.status_code == 200
    assert b"Azul" in response.data
    assert b"Catan" not in response.data
    assert b'<details class="inventory-tools" open data-filter-panel>' in response.data


def test_box_list_displays_catalogued_and_uncatalogued_box_details(
    client,
    make_user,
    make_box,
    login_as,
):
    owner = make_user("owner")
    holder = make_user("holder")
    catalogued_box = make_box(owner, holder=holder, title="Azul", token="azul")
    uncatalogued_box = Box(
        display_name="Prototype maison",
        owner=owner,
        current_holder=None,
        qr_code_token="prototype",
        condition="worn",
        availability_status="available",
        lifecycle_status="active",
    )
    db.session.add(uncatalogued_box)
    db.session.commit()
    login_as(owner)

    response = client.get("/boxes")

    assert response.status_code == 200
    assert b"Azul" in response.data
    assert f'/boxes/{catalogued_box.id}'.encode() in response.data
    assert b"Prototype maison" in response.data
    assert f'/boxes/{uncatalogued_box.id}'.encode() in response.data
    assert b"Owner" in response.data
    assert b"Holder" in response.data
    assert b"Inventaire des bo" in response.data
    assert b'href="/boxes/new"' in response.data
    assert b'<details class="inventory-tools" data-filter-panel>' in response.data
    assert b"Rechercher et filtrer" in response.data
    assert b'id="status"' not in response.data
    assert b'<th scope="col">ID</th>' not in response.data
    assert '<th scope="col">État</th>'.encode() not in response.data
    assert b">I would like</button>" in response.data
    assert "glisse horizontalement".encode() in response.data
    assert b'class="collection-list-view table-scroll"' in response.data
    assert b'id="boxes-list-view"' in response.data
    assert b'id="boxes-grid-view"' in response.data
    assert b"racinepoir-boxes-view" in response.data


def test_home_summaries_show_only_three_most_recent_boxes(
    client,
    make_user,
    make_box,
    login_as,
):
    owner = make_user("owner")
    oldest = make_box(owner, title="Oldest", token="summary-oldest")
    recent_boxes = [
        make_box(owner, title=title, token=f"summary-{index}")
        for index, title in enumerate(("Recent one", "Recent two", "Recent three"), start=1)
    ]
    login_as(owner)

    response = client.get("/")

    assert response.status_code == 200
    assert oldest.display_label.encode() not in response.data
    for box in recent_boxes:
        assert box.display_label.encode() in response.data
    assert response.data.count(b'class="summary-card"') == 6


def test_box_detail_displays_ownership_status_and_history(
    client,
    make_user,
    make_box,
):
    owner = make_user("owner")
    previous_holder = make_user("previous")
    current_holder = make_user("current")
    box = make_box(owner, holder=current_holder, title="Azul", token="detail")
    box.condition = "worn"
    box.availability_status = "unavailable"
    box.lifecycle_status = "lost"
    box.notes = "Il manque un sac."
    db.session.add(
        BoxEvent(
            box=box,
            event_type="holder_changed",
            actor=owner,
            from_holder=previous_holder,
            to_holder=current_holder,
            notes="Transfert vérifié.",
        )
    )
    db.session.commit()

    response = client.get(f"/boxes/{box.id}")

    assert response.status_code == 200
    assert b"Azul" in response.data
    assert b"Owner" in response.data
    assert b"Current" in response.data
    assert "Usée".encode() not in response.data
    assert b"Indisponible" not in response.data
    assert b"Perdue" not in response.data
    assert b"Il manque un sac." in response.data
    assert b"holder_changed" in response.data
    assert b"acteur : Owner" in response.data
    assert b"de : Previous" in response.data
    assert b"vers : Current" in response.data
    assert "Transfert vérifié.".encode() in response.data


def test_box_detail_returns_not_found_for_unknown_box(client):
    assert client.get("/boxes/999999").status_code == 404


def test_new_box_gets_stable_qr_token_and_correct_scan_url(
    app,
    client,
    make_user,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    login_as(owner)
    with patch("app.routes.search_games", return_value=[]):
        creation_response = client.post(
            "/boxes/new",
            data={
                "_csrf_token": csrf_token,
                "game_id": "__new__",
                "new_game_title": "Jeu QR",
                "owner_user_id": str(owner.id),
            },
        )

    assert creation_response.status_code == 302
    with app.app_context():
        box = Box.query.one()
        box_id = box.id
        original_token = box.qr_code_token
    assert original_token
    expected_scan_url = f"https://ludo.example.test/scan/{original_token}"

    label_response = client.get(
        f"/boxes/{box_id}/label",
        base_url="https://ludo.example.test",
    )

    assert label_response.status_code == 200
    assert expected_scan_url.encode() in label_response.data
    assert f'/boxes/{box_id}/qr.png'.encode() in label_response.data

    image = Mock()
    image.save.side_effect = lambda output, format: output.write(b"PNG")
    with patch("qrcode.make", return_value=image) as make_qr:
        qr_response = client.get(
            f"/boxes/{box_id}/qr.png",
            base_url="https://ludo.example.test",
        )

    assert qr_response.status_code == 200
    assert qr_response.mimetype == "image/png"
    assert qr_response.data == b"PNG"
    make_qr.assert_called_once_with(expected_scan_url)
    image.save.assert_called_once()
    with app.app_context():
        assert db.session.get(Box, box_id).qr_code_token == original_token


def test_boxes_can_be_filtered_by_owner_holder_and_status(
    client,
    make_user,
    make_box,
):
    alice = make_user("alice")
    bob = make_user("bob")
    matching_box = make_box(
        alice,
        holder=bob,
        title="Boîte correspondante",
        token="matching",
    )
    other_owner_box = make_box(
        bob,
        holder=bob,
        title="Autre propriétaire",
        token="other-owner",
    )
    other_status_box = make_box(
        alice,
        holder=bob,
        title="Boîte perdue",
        token="lost",
    )
    other_status_box.lifecycle_status = "lost"
    db.session.commit()

    response = client.get(
        "/boxes",
        query_string={
            "owner_id": alice.id,
            "holder_id": bob.id,
            "status": "active",
        },
    )

    assert response.status_code == 200
    assert matching_box.display_name.encode() in response.data
    assert other_owner_box.display_name.encode() not in response.data
    assert other_status_box.display_name.encode() not in response.data


def test_boxes_can_be_filtered_by_unknown_holder(client, make_user, make_box):
    owner = make_user("owner")
    unknown_holder_box = make_box(owner, title="Sans détenteur", token="none")
    known_holder_box = make_box(owner, title="Avec détenteur", token="known")
    unknown_holder_box.current_holder = None
    db.session.commit()

    response = client.get("/boxes?holder_id=none")

    assert response.status_code == 200
    assert unknown_holder_box.display_name.encode() in response.data
    assert known_holder_box.display_name.encode() not in response.data
