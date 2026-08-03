from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import Box, Game, User


def test_application_restart_preserves_data_and_core_routes(tmp_path, monkeypatch):
    database_path = tmp_path / "restart.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    first_app = create_app()
    first_app.config.update(TESTING=True)
    with first_app.app_context():
        db.create_all()
        owner = User(
            username="restart-user",
            email="restart@example.test",
            display_name="Restart User",
            password_hash=generate_password_hash("restart-password"),
            role="member",
            is_active=True,
        )
        game = Game(title="Restart Game", normalized_title="restart game")
        box = Box(
            display_name="Restart Game",
            game=game,
            owner=owner,
            current_holder=owner,
            qr_code_token="restart-box",
            condition="good",
            availability_status="available",
            lifecycle_status="active",
        )
        db.session.add_all([owner, game, box])
        db.session.commit()
        db.session.remove()

    restarted_app = create_app()
    restarted_app.config.update(TESTING=True)
    client = restarted_app.test_client()
    client.get("/login")
    with client.session_transaction() as session:
        csrf_token = session["_csrf_token"]

    login_response = client.post(
        "/login",
        data={
            "_csrf_token": csrf_token,
            "username": "restart-user",
            "password": "restart-password",
        },
    )

    assert login_response.status_code == 302
    assert client.get("/healthz").status_code == 200
    assert b"Restart Game" in client.get("/games").data
    assert b"Restart Game" in client.get("/boxes").data
    assert client.get("/scan/restart-box").status_code == 200

    with restarted_app.app_context():
        assert User.query.filter_by(username="restart-user").count() == 1
        assert Game.query.filter_by(title="Restart Game").count() == 1
        assert Box.query.filter_by(qr_code_token="restart-box").count() == 1
        db.session.remove()
