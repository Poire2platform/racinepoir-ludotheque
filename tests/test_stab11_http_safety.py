from unittest.mock import patch

import pytest

from app.extensions import db
from app.models import (
    Box,
    BoxEvent,
    BoxRequest,
    Game,
    GameSession,
    GameSessionParticipant,
    PlayerProfile,
    User,
)


@pytest.mark.parametrize(
    "path",
    (
        "/logout",
        "/boxes/1/transfer",
        "/scan/test-box-token/confirm",
        "/boxes/1/request",
        "/boxes/1/mark-lost",
        "/boxes/1/mark-active",
    ),
)
def test_mutation_only_routes_reject_get(
    path,
    client,
    make_user,
    make_box,
    login_as,
):
    owner = make_user("owner")
    make_box(owner)
    login_as(owner)

    response = client.get(path)

    assert response.status_code == 405


@pytest.mark.parametrize(
    "path",
    (
        "/register",
        "/logout",
        "/me/profile",
        "/users/new",
        "/users/1/edit",
        "/security",
        "/games/1/bgg",
        "/games/1/rating",
        "/boxes/new",
        "/boxes/1/edit",
        "/boxes/1/transfer",
        "/scan/test-box-token/confirm",
        "/boxes/1/request",
        "/boxes/1/mark-lost",
        "/boxes/1/mark-active",
        "/sessions/new",
    ),
)
def test_every_post_route_rejects_missing_csrf(path, client):
    response = client.post(path, data={})

    assert response.status_code == 400


def test_form_get_routes_do_not_change_database(
    client,
    make_user,
    make_box,
    login_as,
):
    admin = make_user("admin", role="admin")
    box = make_box(admin)
    login_as(admin)
    initial_state = database_state()

    paths = (
        "/me/profile",
        "/users/new",
        f"/users/{admin.id}/edit",
        "/security",
        f"/games/{box.game_id}/bgg",
        "/boxes/new",
        f"/boxes/{box.id}/edit",
        "/sessions/new",
    )

    with patch("app.routes.search_games", return_value=[]):
        for path in paths:
            response = client.get(path)
            assert response.status_code == 200, path

    assert database_state() == initial_state


def test_scan_get_does_not_change_holder_request_or_history(
    client,
    make_user,
    make_box,
    login_as,
):
    owner = make_user("owner")
    requester = make_user("requester")
    box = make_box(owner, token="read-only-scan")
    box_request = BoxRequest(
        box=box,
        requester=requester,
        status="active",
    )
    db.session.add(box_request)
    db.session.commit()
    login_as(requester)
    initial_state = database_state()

    response = client.get("/scan/read-only-scan")

    assert response.status_code == 200
    assert database_state() == initial_state


def test_member_cannot_manage_users(
    client,
    make_user,
    login_as,
    csrf_token,
):
    member = make_user("member")
    login_as(member)

    create_response = client.post(
        "/users/new",
        data={
            "_csrf_token": csrf_token,
            "username": "intruder",
            "email": "intruder@example.test",
            "display_name": "Intruder",
            "password": "secret123",
            "role": "admin",
            "is_active": "yes",
        },
    )
    edit_response = client.post(
        f"/users/{member.id}/edit",
        data={
            "_csrf_token": csrf_token,
            "username": member.username,
            "email": member.email,
            "display_name": member.display_name,
            "role": "admin",
            "is_active": "yes",
        },
    )

    assert create_response.status_code == 403
    assert edit_response.status_code == 403
    assert User.query.filter_by(username="intruder").count() == 0
    assert member.role == "member"


def test_member_cannot_manage_registration_invites(
    app,
    client,
    make_user,
    login_as,
    csrf_token,
):
    member = make_user("member")
    login_as(member)
    initial_invite_state = (
        app.config["REGISTRATION_INVITE_ENABLED"],
        app.config["REGISTRATION_INVITE_CODE"],
        app.config["REGISTRATION_INVITE_DAY"],
    )

    response = client.post(
        "/security",
        data={"_csrf_token": csrf_token, "action": "generate_invite"},
    )

    assert response.status_code == 403
    assert (
        app.config["REGISTRATION_INVITE_ENABLED"],
        app.config["REGISTRATION_INVITE_CODE"],
        app.config["REGISTRATION_INVITE_DAY"],
    ) == initial_invite_state


@pytest.mark.parametrize(
    "path,data",
    (
        ("/boxes/1/edit", {}),
        ("/boxes/1/transfer", {"current_holder_user_id": "2"}),
        ("/boxes/1/mark-lost", {}),
        ("/boxes/1/mark-active", {}),
    ),
)
def test_non_owner_cannot_manage_box(
    path,
    data,
    client,
    make_user,
    make_box,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    non_owner = make_user("nonowner")
    box = make_box(owner)
    login_as(non_owner)
    initial_state = database_state()

    response = client.post(
        path,
        data={"_csrf_token": csrf_token, **data},
    )

    assert response.status_code == 403
    assert database_state() == initial_state
    assert box.owner_user_id == owner.id


@pytest.mark.parametrize(
    "path_template",
    (
        "/boxes/{box_id}/edit",
        "/boxes/{box_id}/label",
        "/boxes/{box_id}/qr.png",
    ),
)
def test_non_owner_cannot_access_box_management_pages(
    path_template,
    client,
    make_user,
    make_box,
    login_as,
):
    owner = make_user("owner")
    non_owner = make_user("nonowner")
    box = make_box(owner)
    login_as(non_owner)
    initial_state = database_state()

    response = client.get(path_template.format(box_id=box.id))

    assert response.status_code == 403
    assert database_state() == initial_state


def test_admin_can_manage_another_members_box(
    client,
    make_user,
    make_box,
    login_as,
    csrf_token,
):
    owner = make_user("owner")
    new_holder = make_user("holder")
    admin = make_user("admin", role="admin")
    box = make_box(owner)
    login_as(admin)

    assert client.get(f"/boxes/{box.id}/edit").status_code == 200
    assert client.get(f"/boxes/{box.id}/label").status_code == 200

    transfer_response = client.post(
        f"/boxes/{box.id}/transfer",
        data={
            "_csrf_token": csrf_token,
            "current_holder_user_id": new_holder.id,
        },
    )
    lost_response = client.post(
        f"/boxes/{box.id}/mark-lost",
        data={"_csrf_token": csrf_token},
    )

    assert transfer_response.status_code == 302
    assert lost_response.status_code == 302
    db.session.refresh(box)
    assert box.current_holder_user_id == new_holder.id
    assert box.lifecycle_status == "lost"


def test_admin_cannot_remove_own_access(
    client,
    make_user,
    login_as,
    csrf_token,
):
    admin = make_user("admin", role="admin")
    login_as(admin)

    response = client.post(
        f"/users/{admin.id}/edit",
        data={
            "_csrf_token": csrf_token,
            "username": admin.username,
            "email": admin.email,
            "display_name": admin.display_name,
            "role": "member",
        },
    )

    assert response.status_code == 200
    db.session.refresh(admin)
    assert admin.role == "admin"
    assert admin.is_active is True


def database_state():
    return {
        "users": User.query.count(),
        "games": Game.query.count(),
        "boxes": Box.query.count(),
        "events": BoxEvent.query.count(),
        "requests": BoxRequest.query.count(),
        "sessions": GameSession.query.count(),
        "participants": GameSessionParticipant.query.count(),
        "profiles": PlayerProfile.query.count(),
        "holders": tuple(
            (box.id, box.current_holder_user_id, box.lifecycle_status)
            for box in Box.query.order_by(Box.id).all()
        ),
        "request_statuses": tuple(
            (request.id, request.status)
            for request in BoxRequest.query.order_by(BoxRequest.id).all()
        ),
    }
