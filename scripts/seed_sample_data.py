import secrets

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import User, Game, Box, BoxEvent, BoxRequest


def get_or_create_user(username, email, display_name):
    user = User.query.filter_by(username=username).first()
    if user:
        return user, None

    temporary_password = secrets.token_urlsafe(12)

    user = User(
        username=username,
        email=email,
        display_name=display_name,
        password_hash=generate_password_hash(temporary_password),
        role="member",
        is_active=True,
    )

    db.session.add(user)
    db.session.flush()

    return user, temporary_password


def get_or_create_game(title, **values):
    game = Game.query.filter_by(title=title).first()
    if game:
        return game

    game = Game(
        title=title,
        normalized_title=title.lower(),
        **values,
    )

    db.session.add(game)
    db.session.flush()
    return game


def get_or_create_box(token, game, owner, holder, **values):
    box = Box.query.filter_by(qr_code_token=token).first()
    if box:
        return box

    box = Box(
        display_name=game.title,
        game_id=game.id,
        owner_user_id=owner.id,
        current_holder_user_id=holder.id,
        qr_code_token=token,
        condition=values.get("condition", "good"),
        availability_status="available",
        lifecycle_status="active",
        notes=values.get("notes"),
    )

    db.session.add(box)
    db.session.flush()

    db.session.add(
        BoxEvent(
            box_id=box.id,
            event_type="created",
            actor_user_id=owner.id,
            to_holder_user_id=holder.id,
            notes=f"Boîte de démonstration créée. Détenteur initial : {holder.display_name}.",
        )
    )

    return box


def seed():
    max_user = User.query.filter_by(username="max").first()

    if not max_user:
        raise RuntimeError("Le compte max doit exister avant le seed.")

    anouk, anouk_password = get_or_create_user(
        "anouk",
        "anouk@example.local",
        "Anouk",
    )

    frere, frere_password = get_or_create_user(
        "frere",
        "frere@example.local",
        "Frère",
    )

    catan = get_or_create_game(
        "Catan",
        language="FR",
        publisher="Kosmos",
        year_published=1995,
        min_players=3,
        max_players=4,
        min_playtime=60,
        max_playtime=120,
        complexity=2.3,
    )

    azul = get_or_create_game(
        "Azul",
        language="FR",
        publisher="Plan B Games",
        year_published=2017,
        min_players=2,
        max_players=4,
        min_playtime=30,
        max_playtime=45,
        complexity=1.8,
    )

    catan_box = get_or_create_box(
        "dev-catan-box-001",
        catan,
        max_user,
        anouk,
        notes="Appartient à Max, actuellement chez Anouk.",
    )

    get_or_create_box(
        "dev-azul-box-001",
        azul,
        anouk,
        max_user,
        notes="Appartient à Anouk, actuellement chez Max.",
    )

    existing_request = BoxRequest.query.filter_by(
        box_id=catan_box.id,
        requester_user_id=frere.id,
        status="active",
    ).first()

    if not existing_request:
        db.session.add(
            BoxRequest(
                box_id=catan_box.id,
                requester_user_id=frere.id,
                status="active",
            )
        )

    db.session.commit()

    print("Seed non destructif terminé.")

    if anouk_password:
        print(f"Mot de passe temporaire Anouk : {anouk_password}")

    if frere_password:
        print(f"Mot de passe temporaire Frère : {frere_password}")


if __name__ == "__main__":
    app = create_app()

    with app.app_context():
        seed()
