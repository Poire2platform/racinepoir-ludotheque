import os

import pytest
from werkzeug.security import generate_password_hash


os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["LOGIN_RATE_LIMIT_ATTEMPTS"] = "1000"
os.environ["SCAN_CONFIRM_RATE_LIMIT_ATTEMPTS"] = "1000"

from app import create_app
from app.extensions import db
from app.models import Box, Game, User
from app.security import _rate_limit_buckets


@pytest.fixture
def app():
    application = create_app()
    application.config.update(TESTING=True)
    context = application.app_context()
    context.push()

    db.create_all()

    yield application

    db.session.remove()
    db.drop_all()
    context.pop()
    _rate_limit_buckets.clear()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user(app):
    def factory(
        username,
        *,
        password="secret123",
        role="member",
        is_active=True,
    ):
        user = User(
            username=username,
            email=f"{username}@example.test",
            display_name=username.title(),
            password_hash=generate_password_hash(password),
            role=role,
            is_active=is_active,
        )
        db.session.add(user)
        db.session.commit()
        return user

    return factory


@pytest.fixture
def make_box(app):
    def factory(owner, *, holder=None, title="Azul", token="test-box-token"):
        game = Game(title=title, normalized_title=title.lower())
        box = Box(
            display_name=title,
            game=game,
            owner=owner,
            current_holder=holder or owner,
            qr_code_token=token,
            condition="good",
            availability_status="available",
            lifecycle_status="active",
        )
        db.session.add_all([game, box])
        db.session.commit()
        return box

    return factory


@pytest.fixture
def csrf_token(client):
    client.get("/login")
    with client.session_transaction() as session:
        return session["_csrf_token"]


@pytest.fixture
def login_as(client):
    def login(user, password="secret123"):
        with client.session_transaction() as session:
            token = session.get("_csrf_token")

        if not token:
            client.get("/login")
            with client.session_transaction() as session:
                token = session["_csrf_token"]

        response = client.post(
            "/login",
            data={
                "_csrf_token": token,
                "username": user.username,
                "password": password,
            },
        )
        assert response.status_code == 302

    return login
