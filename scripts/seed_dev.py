from app import create_app
from app.extensions import db
from app.models import User, Game, Box, BoxEvent, BoxRequest, GameSession, GameSessionParticipant, PlayerProfile
from werkzeug.security import generate_password_hash

def reset_dev_data():
    db.session.query(GameSessionParticipant).delete()
    db.session.query(GameSession).delete()
    db.session.query(PlayerProfile).delete()
    db.session.query(BoxEvent).delete()
    db.session.query(BoxRequest).delete()
    db.session.query(Box).delete()
    db.session.query(Game).delete()
    db.session.query(User).delete()
    db.session.commit()

def create_user(username, email, display_name, password, role="member"):
    user = User(username=username, email=email, display_name=display_name, password_hash=generate_password_hash(password), role=role, is_active=True)
    db.session.add(user)
    db.session.flush()
    return user

def create_game(title, language="FR", publisher=None, year_published=None, min_players=None, max_players=None, min_playtime=None, max_playtime=None, complexity=None):
    game = Game(title=title, normalized_title=title.lower(), language=language, publisher=publisher, year_published=year_published, min_players=min_players, max_players=max_players, min_playtime=min_playtime, max_playtime=max_playtime, complexity=complexity)
    db.session.add(game)
    db.session.flush()
    return game

def create_box(owner, qr_code_token, game, current_holder=None, condition="good", availability_status="available", lifecycle_status="active", notes=None):
    current_holder = current_holder or owner
    box = Box(display_name=game.title, game_id=game.id, owner_user_id=owner.id, current_holder_user_id=current_holder.id, qr_code_token=qr_code_token, condition=condition, availability_status=availability_status, lifecycle_status=lifecycle_status, notes=notes)
    db.session.add(box)
    db.session.flush()
    db.session.add(BoxEvent(box_id=box.id, event_type="created", actor_user_id=owner.id, to_holder_user_id=current_holder.id, notes=f"Boîte créée. Détenteur initial : {current_holder.display_name}."))
    return box

def create_request(box, requester):
    req = BoxRequest(box_id=box.id, requester_user_id=requester.id, status="active")
    db.session.add(req)
    db.session.flush()
    db.session.add(BoxEvent(box_id=box.id, event_type="box_requested", actor_user_id=requester.id, related_request_id=req.id, to_holder_user_id=requester.id, notes=f"{requester.display_name} a été ajouté à la file d’attente."))
    return req

def normalize_name(name):
    return " ".join(name.lower().strip().split())

def create_player(display_name, linked_user=None):
    profile = PlayerProfile(display_name=display_name, normalized_name=normalize_name(display_name), linked_user_id=linked_user.id if linked_user else None)
    db.session.add(profile)
    db.session.flush()
    return profile

def create_session(game, box, created_by, duration_minutes, notes, participants):
    session = GameSession(game_id=game.id, box_id=box.id if box else None, created_by_user_id=created_by.id, duration_minutes=duration_minutes, notes=notes)
    db.session.add(session)
    db.session.flush()

    for participant in participants:
        db.session.add(GameSessionParticipant(
            session_id=session.id,
            player_profile_id=participant["player"].id,
            team_label=participant.get("team"),
            score=participant.get("score"),
            rank=participant.get("rank"),
            is_winner=participant.get("winner", False),
            notes=participant.get("notes"),
        ))

    return session

def seed():
    reset_dev_data()
    admin = create_user("admin", "admin@example.local", "Admin", "admin123", role="admin")
    max_user = create_user("max", "max@example.local", "Max", "max123")
    anouk_user = create_user("anouk", "anouk@example.local", "Anouk", "anouk123")
    frere_user = create_user("frere", "frere@example.local", "Frère", "frere123")

    max_player = create_player("Max", max_user)
    anouk_player = create_player("Anouk", anouk_user)
    frere_player = create_player("Frère", frere_user)
    anika_player = create_player("Anika")

    catan = create_game("Catan", "FR", "Kosmos", 1995, 3, 4, 60, 120, 2.3)
    azul = create_game("Azul", "FR", "Plan B Games", 2017, 2, 4, 30, 45, 1.8)
    terraform = create_game("Terraforming Mars", "EN", "FryxGames", 2016, 1, 5, 120, 180, 3.3)
    ticket = create_game("Ticket to Ride Europe", "FR", "Days of Wonder", 2005, 2, 5, 45, 90, 1.9)

    catan_box = create_box(max_user, "dev-catan-box-001", catan, current_holder=anouk_user, notes="Appartient à Max, présentement entre les mains d’Anouk.")
    create_request(catan_box, max_user)
    create_request(catan_box, frere_user)

    azul_box = create_box(anouk_user, "dev-azul-box-001", azul, current_holder=max_user, notes="Appartient à Anouk, présentement entre les mains de Max.")
    create_request(azul_box, anouk_user)

    create_box(frere_user, "dev-terraform-box-001", terraform, condition="worn", notes="Appartient au frère, déjà entre ses mains.")
    create_box(admin, "dev-ticket-box-001", ticket, condition="unknown", notes="Boîte communautaire administrée par Admin.")

    risk = create_game("Risk", "FR")
    risk_box = create_box(max_user, "dev-risk-box-uncatalogued-001", risk, current_holder=frere_user, condition="unknown", notes="Vieille boîte de Risk.")
    create_request(risk_box, max_user)

    create_session(
        catan,
        catan_box,
        max_user,
        95,
        "Première partie de test avec invité.",
        [
            {"player": max_player, "score": 10, "rank": 2},
            {"player": anouk_player, "score": 12, "rank": 1, "winner": True},
            {"player": anika_player, "score": 8, "rank": 3},
        ],
    )
    create_session(
        azul,
        azul_box,
        anouk_user,
        40,
        "Partie courte pour valider les stats.",
        [
            {"player": anouk_player, "score": 78, "rank": 1, "winner": True},
            {"player": max_player, "score": 65, "rank": 2},
            {"player": frere_player, "score": 59, "rank": 3},
        ],
    )

    db.session.commit()
    print("Seed dev terminé.")
    print("Comptes: admin/admin123, max/max123, anouk/anouk123, frere/frere123")
    print("QR: dev-catan-box-001, dev-azul-box-001, dev-terraform-box-001, dev-ticket-box-001, dev-risk-box-uncatalogued-001")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed()
