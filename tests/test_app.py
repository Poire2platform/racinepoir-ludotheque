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
