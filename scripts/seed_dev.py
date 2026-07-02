from werkzeug.security import generate_password_hash

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.extensions import db
from app.models import User, Game, Location, GameCopy, CopyEvent


app = create_app()

with app.app_context():
    admin = User(
        username="admin",
        email="admin@example.local",
        password_hash=generate_password_hash("admin123"),
        display_name="Admin",
        role="admin",
    )

    max_home = Location(
        name="Chez Max",
        location_type="home",
        owner=admin,
        is_private=True,
    )

    catan = Game(
        title="Catan",
        normalized_title="catan",
        language="FR",
        min_players=3,
        max_players=4,
        min_playtime=60,
        max_playtime=120,
    )

    catan_copy = GameCopy(
        game=catan,
        owner=admin,
        current_holder=admin,
        current_location=max_home,
        qr_code_token="dev-catan-copy-001",
        condition="good",
        availability_status="available",
        lifecycle_status="active",
    )

    event = CopyEvent(
        game_copy=catan_copy,
        event_type="created",
        actor=admin,
        to_user=admin,
        to_location=max_home,
        notes="Seed dev initial.",
    )

    db.session.add_all([admin, max_home, catan, catan_copy, event])
    db.session.commit()

    print("Seed dev terminé.")
