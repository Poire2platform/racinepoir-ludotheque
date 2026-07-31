from unittest.mock import patch

from app.extensions import db
from app.models import Box, BoxEvent, BoxRequest, Game


def test_healthz_reports_application_and_database_ready(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    assert response.get_json()["database"] == "ok"


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


def test_request_can_be_created_and_cancelled(
    app,
    client,
    make_user,
    make_box,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    requester = make_user("requester")
    box = make_box(owner)
    login_as(requester)

    response = client.post(
        f"/boxes/{box.id}/request",
        data={"_csrf_token": csrf_token},
    )
    assert response.status_code == 302

    response = client.post(
        f"/boxes/{box.id}/request/clear",
        data={"_csrf_token": csrf_token},
    )
    assert response.status_code == 302

    with app.app_context():
        box_request = BoxRequest.query.one()
        assert box_request.status == "cancelled"
        assert box_request.cancelled_at is not None


def test_scan_changes_holder_and_fulfills_request(
    app,
    client,
    make_user,
    make_box,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    requester = make_user("requester")
    box = make_box(owner, token="scan-me")
    box_request = BoxRequest(
        box_id=box.id,
        requester_user_id=requester.id,
        status="active",
    )
    db.session.add(box_request)
    db.session.commit()
    login_as(requester)

    response = client.post(
        "/scan/scan-me/confirm",
        data={"_csrf_token": csrf_token},
    )

    assert response.status_code == 200
    with app.app_context():
        refreshed_box = db.session.get(Box, box.id)
        refreshed_request = db.session.get(BoxRequest, box_request.id)
        assert refreshed_box.current_holder_user_id == requester.id
        assert refreshed_request.status == "fulfilled"
        assert refreshed_request.fulfilled_at is not None


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
        "/sessions",
        "/players",
        "/users",
        "/scan/smoke-box",
        "/healthz",
    )

    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, path


def test_boxes_can_be_searched_by_title(client, make_user, make_box):
    owner = make_user("owner")
    make_box(owner, title="Azul", token="azul")
    make_box(owner, title="Catan", token="catan")

    response = client.get("/boxes?title=azu")

    assert response.status_code == 200
    assert b"Azul" in response.data
    assert b"Catan" not in response.data


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
