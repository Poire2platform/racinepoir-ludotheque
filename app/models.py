from datetime import datetime, timezone
from .extensions import db
from flask_login import UserMixin


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(80), nullable=False, unique=True, index=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    display_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="member")
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    owned_copies = db.relationship(
        "GameCopy",
        foreign_keys="GameCopy.owner_user_id",
        back_populates="owner",
    )

    held_copies = db.relationship(
        "GameCopy",
        foreign_keys="GameCopy.current_holder_user_id",
        back_populates="current_holder",
    )

    locations = db.relationship("Location", back_populates="owner")


class Game(db.Model):
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
    cover_image_url = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    copies = db.relationship("GameCopy", back_populates="game")


class Location(db.Model):
    __tablename__ = "locations"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255), nullable=False)
    parent_location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=True)

    description = db.Column(db.Text, nullable=True)
    location_type = db.Column(db.String(50), nullable=False, default="unknown")

    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    is_private = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    owner = db.relationship("User", back_populates="locations")

    parent = db.relationship(
        "Location",
        remote_side=[id],
        back_populates="children",
    )

    children = db.relationship("Location", back_populates="parent")


class GameCopy(db.Model):
    __tablename__ = "game_copies"

    id = db.Column(db.Integer, primary_key=True)

    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    current_holder_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    current_location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=True)
    wanted_location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=True)

    qr_code_token = db.Column(db.String(255), nullable=False, unique=True, index=True)

    nickname = db.Column(db.String(255), nullable=True)
    condition = db.Column(db.String(50), nullable=False, default="unknown")
    availability_status = db.Column(db.String(50), nullable=False, default="available")
    lifecycle_status = db.Column(db.String(50), nullable=False, default="active")

    missing_pieces_note = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    acquired_at = db.Column(db.Date, nullable=True)
    archived_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    game = db.relationship("Game", back_populates="copies")

    owner = db.relationship(
        "User",
        foreign_keys=[owner_user_id],
        back_populates="owned_copies",
    )

    current_holder = db.relationship(
        "User",
        foreign_keys=[current_holder_user_id],
        back_populates="held_copies",
    )

    current_location = db.relationship(
        "Location",
        foreign_keys=[current_location_id],
    )

    wanted_location = db.relationship(
        "Location",
        foreign_keys=[wanted_location_id],
    )

    events = db.relationship("CopyEvent", back_populates="game_copy")


class CopyEvent(db.Model):
    __tablename__ = "copy_events"

    id = db.Column(db.Integer, primary_key=True)

    game_copy_id = db.Column(db.Integer, db.ForeignKey("game_copies.id"), nullable=False)

    event_type = db.Column(db.String(80), nullable=False, index=True)

    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    to_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    from_location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=True)
    to_location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=True)

    notes = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    game_copy = db.relationship("GameCopy", back_populates="events")

    actor = db.relationship("User", foreign_keys=[actor_user_id])
    from_user = db.relationship("User", foreign_keys=[from_user_id])
    to_user = db.relationship("User", foreign_keys=[to_user_id])

    from_location = db.relationship("Location", foreign_keys=[from_location_id])
    to_location = db.relationship("Location", foreign_keys=[to_location_id])
