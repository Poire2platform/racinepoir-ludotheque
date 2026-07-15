from datetime import datetime, timezone

from flask_login import UserMixin

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    display_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="member")
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    owned_boxes = db.relationship(
        "Box",
        foreign_keys="Box.owner_user_id",
        back_populates="owner",
    )

    held_boxes = db.relationship(
        "Box",
        foreign_keys="Box.current_holder_user_id",
        back_populates="current_holder",
    )

    wanted_boxes = db.relationship(
        "Box",
        foreign_keys="Box.wanted_by_user_id",
        back_populates="wanted_by",
    )

    def __repr__(self):
        return f"<User {self.username}>"


class Game(db.Model):
    """
    Fiche de référence optionnelle.

    Le noyau du système est Box. Game sert à enrichir une boîte avec des infos
    générales sur le jeu : titre officiel, éditeur, durée, BGG ID, etc.
    """
    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(255), nullable=False, index=True)
    normalized_title = db.Column(db.String(255), nullable=True, index=True)

    edition_name = db.Column(db.String(255), nullable=True)
    language = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)

    publisher = db.Column(db.String(255), nullable=True)
    year_published = db.Column(db.Integer, nullable=True)

    min_players = db.Column(db.Integer, nullable=True)
    max_players = db.Column(db.Integer, nullable=True)
    min_playtime = db.Column(db.Integer, nullable=True)
    max_playtime = db.Column(db.Integer, nullable=True)
    age_min = db.Column(db.Integer, nullable=True)

    complexity = db.Column(db.Float, nullable=True)
    bgg_id = db.Column(db.Integer, nullable=True, index=True)
    cover_image_url = db.Column(db.String(500), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    boxes = db.relationship("Box", back_populates="game")

    def __repr__(self):
        return f"<Game {self.title}>"


class Box(db.Model):
    """
    Boîte physique réelle.

    C'est la table centrale du projet. Une boîte peut référencer une fiche Game,
    mais elle peut aussi exister sans Game si on veut l'inventorier rapidement.
    """
    __tablename__ = "boxes"

    id = db.Column(db.Integer, primary_key=True)

    display_name = db.Column(db.String(255), nullable=False, index=True)

    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=True)

    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    current_holder_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    wanted_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    qr_code_token = db.Column(db.String(255), unique=True, nullable=False, index=True)

    condition = db.Column(db.String(50), nullable=False, default="unknown")
    availability_status = db.Column(db.String(50), nullable=False, default="available")
    lifecycle_status = db.Column(db.String(50), nullable=False, default="active")

    missing_pieces_note = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    acquired_at = db.Column(db.DateTime(timezone=True), nullable=True)
    archived_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    game = db.relationship("Game", back_populates="boxes")

    owner = db.relationship(
        "User",
        foreign_keys=[owner_user_id],
        back_populates="owned_boxes",
    )

    current_holder = db.relationship(
        "User",
        foreign_keys=[current_holder_user_id],
        back_populates="held_boxes",
    )

    wanted_by = db.relationship(
        "User",
        foreign_keys=[wanted_by_user_id],
        back_populates="wanted_boxes",
    )

    events = db.relationship(
        "BoxEvent",
        back_populates="box",
        cascade="all, delete-orphan",
        order_by="BoxEvent.created_at.desc()",
    )

    def __repr__(self):
        return f"<Box {self.display_name}>"


class BoxEvent(db.Model):
    __tablename__ = "box_events"

    id = db.Column(db.Integer, primary_key=True)

    box_id = db.Column(db.Integer, db.ForeignKey("boxes.id"), nullable=False)

    event_type = db.Column(db.String(80), nullable=False, index=True)

    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    from_holder_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    to_holder_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    notes = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    box = db.relationship("Box", back_populates="events")

    actor = db.relationship("User", foreign_keys=[actor_user_id])
    from_holder = db.relationship("User", foreign_keys=[from_holder_user_id])
    to_holder = db.relationship("User", foreign_keys=[to_holder_user_id])

    def __repr__(self):
        return f"<BoxEvent {self.event_type} box={self.box_id}>"
