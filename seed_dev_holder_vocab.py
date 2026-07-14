from app import create_app
from app.extensions import db
from app.models import User, Game, Location, GameCopy, CopyEvent
from werkzeug.security import generate_password_hash


def reset_dev_data():
    """Efface les données de développement, sans toucher aux migrations."""
    db.session.query(CopyEvent).delete()
    db.session.query(GameCopy).delete()
    db.session.query(Location).delete()
    db.session.query(Game).delete()
    db.session.query(User).delete()
    db.session.commit()


def create_user(username, email, display_name, password, role="member"):
    user = User(
        username=username,
        email=email,
        display_name=display_name,
        password_hash=generate_password_hash(password),
        role=role,
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()
    return user


def create_holder(name, owner_user=None, is_private=False):
    """
    Techniquement, on utilise encore la table Location.
    Conceptuellement, pour le projet actuel, ces lignes représentent des détenteurs.
    """
    holder = Location(
        name=name,
        owner_user_id=owner_user.id if owner_user else None,
        location_type="holder",
        is_private=is_private,
    )
    db.session.add(holder)
    db.session.flush()
    return holder


def create_game(
    title,
    language="FR",
    publisher=None,
    year_published=None,
    min_players=None,
    max_players=None,
    min_playtime=None,
    max_playtime=None,
    complexity=None,
):
    game = Game(
        title=title,
        normalized_title=title.lower(),
        language=language,
        publisher=publisher,
        year_published=year_published,
        min_players=min_players,
        max_players=max_players,
        min_playtime=min_playtime,
        max_playtime=max_playtime,
        complexity=complexity,
    )
    db.session.add(game)
    db.session.flush()
    return game


def create_copy(
    game,
    owner,
    current_holder,
    qr_code_token,
    wanted_holder=None,
    condition="good",
    availability_status="available",
    lifecycle_status="active",
    notes=None,
):
    copy = GameCopy(
        game_id=game.id,
        owner_user_id=owner.id,
        current_location_id=current_holder.id if current_holder else None,
        wanted_location_id=wanted_holder.id if wanted_holder else None,
        qr_code_token=qr_code_token,
        condition=condition,
        availability_status=availability_status,
        lifecycle_status=lifecycle_status,
        notes=notes,
    )
    db.session.add(copy)
    db.session.flush()

    event = CopyEvent(
        game_copy_id=copy.id,
        event_type="created",
        actor_user_id=owner.id,
        to_location_id=current_holder.id if current_holder else None,
        notes=f"Copie créée. Détenteur initial : {current_holder.name if current_holder else 'inconnu'}.",
    )
    db.session.add(event)

    return copy


def seed():
    reset_dev_data()

    admin = create_user("admin", "admin@example.local", "Admin", "admin123", role="admin")
    max_user = create_user("max", "max@example.local", "Max", "max123")
    anouk_user = create_user("anouk", "anouk@example.local", "Anouk", "anouk123")
    frere_user = create_user("frere", "frere@example.local", "Frère", "frere123")

    admin_holder = create_holder("Admin", owner_user=admin)
    max_holder = create_holder("Max", owner_user=max_user)
    anouk_holder = create_holder("Anouk", owner_user=anouk_user)
    frere_holder = create_holder("Frère", owner_user=frere_user)
    community_holder = create_holder("Local communautaire")

    catan = create_game("Catan", "FR", "Kosmos", 1995, 3, 4, 60, 120, 2.3)
    azul = create_game("Azul", "FR", "Plan B Games", 2017, 2, 4, 30, 45, 1.8)
    terraform = create_game("Terraforming Mars", "EN", "FryxGames", 2016, 1, 5, 120, 180, 3.3)
    ticket = create_game("Ticket to Ride Europe", "FR", "Days of Wonder", 2005, 2, 5, 45, 90, 1.9)

    create_copy(
        game=catan,
        owner=max_user,
        current_holder=anouk_holder,
        wanted_holder=max_holder,
        qr_code_token="dev-catan-copy-001",
        condition="good",
        notes="Copie de test : appartient à Max, présentement chez Anouk, demandée par Max.",
    )

    create_copy(
        game=azul,
        owner=anouk_user,
        current_holder=max_holder,
        wanted_holder=anouk_holder,
        qr_code_token="dev-azul-copy-001",
        condition="good",
        notes="Copie de test : appartient à Anouk, présentement chez Max, demandée par Anouk.",
    )

    create_copy(
        game=terraform,
        owner=frere_user,
        current_holder=frere_holder,
        wanted_holder=None,
        qr_code_token="dev-terraform-copy-001",
        condition="worn",
        notes="Copie de test : appartient au frère, déjà chez lui.",
    )

    create_copy(
        game=ticket,
        owner=admin,
        current_holder=community_holder,
        wanted_holder=None,
        qr_code_token="dev-ticket-copy-001",
        condition="unknown",
        notes="Copie de test : placée au local communautaire.",
    )

    create_copy(
        game=azul,
        owner=max_user,
        current_holder=community_holder,
        wanted_holder=anouk_holder,
        qr_code_token="dev-azul-copy-002",
        condition="good",
        notes="Deuxième copie de test : utile pour tester le claim depuis le local communautaire.",
    )

    db.session.commit()

    print("Seed dev terminé.")
    print("Comptes créés :")
    print("  admin / admin123")
    print("  max / max123")
    print("  anouk / anouk123")
    print("  frere / frere123")
    print("")
    print("QR tokens utiles :")
    print("  dev-catan-copy-001")
    print("  dev-azul-copy-001")
    print("  dev-terraform-copy-001")
    print("  dev-ticket-copy-001")
    print("  dev-azul-copy-002")


if __name__ == "__main__":
    app = create_app()

    with app.app_context():
        seed()
