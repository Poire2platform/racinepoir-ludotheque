from app import create_app
from app.extensions import db
from app.models import User, Game, Box, BoxEvent
from werkzeug.security import generate_password_hash


def reset_dev_data():
    db.session.query(BoxEvent).delete()
    db.session.query(Box).delete()
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


def create_box(
    display_name,
    owner,
    current_holder,
    qr_code_token,
    game=None,
    wanted_by=None,
    condition="good",
    availability_status="available",
    lifecycle_status="active",
    notes=None,
):
    box = Box(
        display_name=display_name,
        game_id=game.id if game else None,
        owner_user_id=owner.id,
        current_holder_user_id=current_holder.id if current_holder else None,
        wanted_by_user_id=wanted_by.id if wanted_by else None,
        qr_code_token=qr_code_token,
        condition=condition,
        availability_status=availability_status,
        lifecycle_status=lifecycle_status,
        notes=notes,
    )

    db.session.add(box)
    db.session.flush()

    event = BoxEvent(
        box_id=box.id,
        event_type="created",
        actor_user_id=owner.id,
        to_holder_user_id=current_holder.id if current_holder else None,
        notes=f"Boîte créée. Détenteur initial : {current_holder.display_name if current_holder else 'inconnu'}.",
    )

    db.session.add(event)
    return box


def seed():
    reset_dev_data()

    admin = create_user("admin", "admin@example.local", "Admin", "admin123", role="admin")
    max_user = create_user("max", "max@example.local", "Max", "max123")
    anouk_user = create_user("anouk", "anouk@example.local", "Anouk", "anouk123")
    frere_user = create_user("frere", "frere@example.local", "Frère", "frere123")

    catan = create_game("Catan", "FR", "Kosmos", 1995, 3, 4, 60, 120, 2.3)
    azul = create_game("Azul", "FR", "Plan B Games", 2017, 2, 4, 30, 45, 1.8)
    terraform = create_game("Terraforming Mars", "EN", "FryxGames", 2016, 1, 5, 120, 180, 3.3)
    ticket = create_game("Ticket to Ride Europe", "FR", "Days of Wonder", 2005, 2, 5, 45, 90, 1.9)

    create_box(
        display_name="Catan — boîte de Max",
        game=catan,
        owner=max_user,
        current_holder=anouk_user,
        wanted_by=max_user,
        qr_code_token="dev-catan-box-001",
        condition="good",
        notes="Boîte de test : appartient à Max, présentement entre les mains d’Anouk, demandée par Max.",
    )

    create_box(
        display_name="Azul — boîte d’Anouk",
        game=azul,
        owner=anouk_user,
        current_holder=max_user,
        wanted_by=anouk_user,
        qr_code_token="dev-azul-box-001",
        condition="good",
        notes="Boîte de test : appartient à Anouk, présentement entre les mains de Max, demandée par Anouk.",
    )

    create_box(
        display_name="Terraforming Mars — boîte du frère",
        game=terraform,
        owner=frere_user,
        current_holder=frere_user,
        wanted_by=None,
        qr_code_token="dev-terraform-box-001",
        condition="worn",
        notes="Boîte de test : appartient au frère, déjà entre ses mains.",
    )

    create_box(
        display_name="Ticket to Ride Europe — boîte communautaire",
        game=ticket,
        owner=admin,
        current_holder=None,
        wanted_by=None,
        qr_code_token="dev-ticket-box-001",
        condition="unknown",
        notes="Boîte de test : détenteur courant inconnu ou communautaire.",
    )

    create_box(
        display_name="Vieille boîte de Risk non cataloguée",
        game=None,
        owner=max_user,
        current_holder=frere_user,
        wanted_by=max_user,
        qr_code_token="dev-risk-box-uncatalogued-001",
        condition="unknown",
        notes="Exemple de boîte sans fiche Game liée.",
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
    print("  dev-catan-box-001")
    print("  dev-azul-box-001")
    print("  dev-terraform-box-001")
    print("  dev-ticket-box-001")
    print("  dev-risk-box-uncatalogued-001")


if __name__ == "__main__":
    app = create_app()

    with app.app_context():
        seed()
