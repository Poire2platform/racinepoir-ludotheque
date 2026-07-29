from app.models import Box, BoxEvent, BoxRequest, Game, User
from scripts.seed_sample_data import seed


def test_sample_seed_is_non_destructive_and_idempotent(app, make_user):
    admin = make_user("admin", role="admin")

    seed()
    first_counts = {
        "users": User.query.count(),
        "games": Game.query.count(),
        "boxes": Box.query.count(),
        "events": BoxEvent.query.count(),
        "requests": BoxRequest.query.count(),
    }

    seed()
    second_counts = {
        "users": User.query.count(),
        "games": Game.query.count(),
        "boxes": Box.query.count(),
        "events": BoxEvent.query.count(),
        "requests": BoxRequest.query.count(),
    }

    assert second_counts == first_counts
    assert db_user_state(admin.id) == ("admin", True)
    assert Box.query.filter_by(qr_code_token="dev-catan-box-001").count() == 1
    assert Box.query.filter_by(qr_code_token="dev-azul-box-001").count() == 1


def db_user_state(user_id):
    user = User.query.filter_by(id=user_id).one()
    return user.role, user.is_active
