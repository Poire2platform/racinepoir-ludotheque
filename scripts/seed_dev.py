from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import User, Game, Location, GameCopy, CopyEvent


app = create_app()


def get_or_create(model, defaults=None, **kwargs):
    instance = model.query.filter_by(**kwargs).first()
    if instance:
        return instance, False

    params = dict(kwargs)
    if defaults:
        params.update(defaults)

    instance = model(**params)
    db.session.add(instance)
    return instance, True


with app.app_context():
    admin, _ = get_or_create(
        User,
        username="admin",
        defaults={
            "email": "admin@example.local",
            "password_hash": generate_password_hash("admin123"),
            "display_name": "Admin",
            "role": "admin",
        },
    )

    max_user, _ = get_or_create(
        User,
        username="max",
        defaults={
            "email": "max@example.local",
            "password_hash": generate_password_hash("max123"),
            "display_name": "Max",
            "role": "member",
        },
    )

    anouk, _ = get_or_create(
        User,
        username="anouk",
        defaults={
            "email": "anouk@example.local",
            "password_hash": generate_password_hash("anouk123"),
            "display_name": "Anouk",
            "role": "member",
        },
    )

    frere, _ = get_or_create(
        User,
        username="frere",
        defaults={
            "email": "frere@example.local",
            "password_hash": generate_password_hash("frere123"),
            "display_name": "Frère",
            "role": "member",
        },
    )

    chez_max, _ = get_or_create(
        Location,
        name="Chez Max",
        defaults={"location_type": "home", "owner": max_user, "is_private": True},
    )

    chez_anouk, _ = get_or_create(
        Location,
        name="Chez Anouk",
        defaults={"location_type": "home", "owner": anouk, "is_private": True},
    )

    chez_frere, _ = get_or_create(
        Location,
        name="Chez Frère",
        defaults={"location_type": "home", "owner": frere, "is_private": True},
    )

    local, _ = get_or_create(
        Location,
        name="Local communautaire",
        defaults={"location_type": "community", "is_private": False},
    )

    catan, _ = get_or_create(
        Game,
        title="Catan",
        defaults={
            "normalized_title": "catan",
            "language": "FR",
            "min_players": 3,
            "max_players": 4,
            "min_playtime": 60,
            "max_playtime": 120,
        },
    )

    azul, _ = get_or_create(
        Game,
        title="Azul",
        defaults={
            "normalized_title": "azul",
            "language": "FR",
            "min_players": 2,
            "max_players": 4,
            "min_playtime": 30,
            "max_playtime": 45,
        },
    )

    terraforming, _ = get_or_create(
        Game,
        title="Terraforming Mars",
        defaults={
            "normalized_title": "terraforming mars",
            "language": "EN",
            "min_players": 1,
            "max_players": 5,
            "min_playtime": 120,
            "max_playtime": 180,
        },
    )

    ticket, _ = get_or_create(
        Game,
        title="Ticket to Ride Europe",
        defaults={
            "normalized_title": "ticket to ride europe",
            "language": "FR",
            "min_players": 2,
            "max_players": 5,
            "min_playtime": 45,
            "max_playtime": 90,
        },
    )

    copies = [
        {
            "qr_code_token": "dev-catan-copy-001",
            "game": catan,
            "owner": max_user,
            "holder": anouk,
            "location": chez_anouk,
            "wanted": chez_max,
            "condition": "good",
        },
        {
            "qr_code_token": "dev-azul-copy-001",
            "game": azul,
            "owner": anouk,
            "holder": max_user,
            "location": chez_max,
            "wanted": chez_anouk,
            "condition": "good",
        },
        {
            "qr_code_token": "dev-tfm-copy-001",
            "game": terraforming,
            "owner": frere,
            "holder": frere,
            "location": chez_frere,
            "wanted": None,
            "condition": "worn",
        },
        {
            "qr_code_token": "dev-ticket-copy-001",
            "game": ticket,
            "owner": admin,
            "holder": None,
            "location": local,
            "wanted": None,
            "condition": "unknown",
        },
    ]

    for item in copies:
        copy, created = get_or_create(
            GameCopy,
            qr_code_token=item["qr_code_token"],
            defaults={
                "game": item["game"],
                "owner": item["owner"],
                "current_holder": item["holder"],
                "current_location": item["location"],
                "wanted_location": item["wanted"],
                "condition": item["condition"],
                "availability_status": "available",
                "lifecycle_status": "active",
            },
        )

        if created:
            event = CopyEvent(
                game_copy=copy,
                event_type="created",
                actor=admin,
                to_user=item["holder"],
                to_location=item["location"],
                notes="Seed dev initial.",
            )
            db.session.add(event)

    db.session.commit()

    print("Seed dev enrichi terminé.")
