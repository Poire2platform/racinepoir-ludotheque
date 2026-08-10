from datetime import datetime, timezone
from statistics import median
from flask_login import UserMixin
from app.extensions import db

def utcnow():
    return datetime.now(timezone.utc)

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="member")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    owned_boxes = db.relationship("Box", foreign_keys="Box.owner_user_id", back_populates="owner")
    held_boxes = db.relationship("Box", foreign_keys="Box.current_holder_user_id", back_populates="current_holder")
    box_requests = db.relationship("BoxRequest", foreign_keys="BoxRequest.requester_user_id", back_populates="requester")
    game_ratings = db.relationship("GameRating", back_populates="user", cascade="all, delete-orphan")
    player_profile = db.relationship("PlayerProfile", back_populates="linked_user", uselist=False)

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
    cover_image_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    boxes = db.relationship("Box", back_populates="game")
    ratings = db.relationship("GameRating", back_populates="game", cascade="all, delete-orphan")

    @property
    def median_rating(self):
        values = [rating.score_percent for rating in self.ratings]
        if not values:
            return None
        result = median(values)
        return int(result) if isinstance(result, float) and result.is_integer() else result

    def rating_for_user(self, user):
        if not user or not getattr(user, "is_authenticated", False):
            return None
        for rating in self.ratings:
            if rating.user_id == user.id:
                return rating
        return None

    @property
    def is_bgg_recognized(self):
        return self.bgg_id is not None

    @property
    def bgg_url(self):
        if not self.bgg_id:
            return None
        return f"https://boardgamegeek.com/boardgame/{self.bgg_id}"


class GameRating(db.Model):
    __tablename__ = "game_ratings"
    __table_args__ = (
        db.UniqueConstraint("game_id", "user_id", name="uq_game_ratings_game_user"),
        db.CheckConstraint("score_percent >= 0 AND score_percent <= 100", name="ck_game_ratings_score_percent"),
    )
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    score_percent = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    game = db.relationship("Game", back_populates="ratings")
    user = db.relationship("User", back_populates="game_ratings")

class Box(db.Model):
    __tablename__ = "boxes"
    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(255), nullable=False, index=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=True)
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    current_holder_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
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
    owner = db.relationship("User", foreign_keys=[owner_user_id], back_populates="owned_boxes")
    current_holder = db.relationship("User", foreign_keys=[current_holder_user_id], back_populates="held_boxes")
    events = db.relationship("BoxEvent", back_populates="box", cascade="all, delete-orphan", order_by="BoxEvent.created_at.desc()")
    requests = db.relationship("BoxRequest", back_populates="box", cascade="all, delete-orphan", order_by="BoxRequest.created_at.asc()")
    sessions = db.relationship("GameSession", back_populates="box")

    @property
    def interest_flags(self):
        return [r for r in self.requests if r.status == "active"]

    def interest_flag_for_user(self, user):
        if not user or not getattr(user, "is_authenticated", False):
            return None
        for r in self.interest_flags:
            if r.requester_user_id == user.id:
                return r
        return None

    @property
    def display_label(self):
        if self.game:
            return self.game.title
        return self.display_name

class BoxRequest(db.Model):
    __tablename__ = "box_requests"
    id = db.Column(db.Integer, primary_key=True)
    box_id = db.Column(db.Integer, db.ForeignKey("boxes.id"), nullable=False, index=True)
    requester_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(db.String(50), nullable=False, default="active", index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    fulfilled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    cancelled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    box = db.relationship("Box", back_populates="requests")
    requester = db.relationship("User", foreign_keys=[requester_user_id], back_populates="box_requests")

class BoxEvent(db.Model):
    __tablename__ = "box_events"
    id = db.Column(db.Integer, primary_key=True)
    box_id = db.Column(db.Integer, db.ForeignKey("boxes.id"), nullable=False)
    event_type = db.Column(db.String(80), nullable=False, index=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    from_holder_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    to_holder_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    related_request_id = db.Column(db.Integer, db.ForeignKey("box_requests.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    box = db.relationship("Box", back_populates="events")
    actor = db.relationship("User", foreign_keys=[actor_user_id])
    from_holder = db.relationship("User", foreign_keys=[from_holder_user_id])
    to_holder = db.relationship("User", foreign_keys=[to_holder_user_id])
    related_request = db.relationship("BoxRequest", foreign_keys=[related_request_id])

class PlayerProfile(db.Model):
    __tablename__ = "player_profiles"
    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(120), nullable=False, index=True)
    normalized_name = db.Column(db.String(120), nullable=False, index=True)
    linked_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    linked_user = db.relationship("User", back_populates="player_profile")
    session_entries = db.relationship("GameSessionParticipant", back_populates="player_profile")

class GameSession(db.Model):
    __tablename__ = "game_sessions"
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False, index=True)
    box_id = db.Column(db.Integer, db.ForeignKey("boxes.id"), nullable=True, index=True)
    played_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    duration_minutes = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    game = db.relationship("Game")
    box = db.relationship("Box", back_populates="sessions")
    created_by = db.relationship("User")
    participants = db.relationship("GameSessionParticipant", back_populates="session", cascade="all, delete-orphan", order_by="GameSessionParticipant.id.asc()")

class GameSessionParticipant(db.Model):
    __tablename__ = "game_session_participants"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id"), nullable=False, index=True)
    player_profile_id = db.Column(db.Integer, db.ForeignKey("player_profiles.id"), nullable=False, index=True)
    team_label = db.Column(db.String(80), nullable=True)
    score = db.Column(db.Integer, nullable=True)
    rank = db.Column(db.Integer, nullable=True)
    is_winner = db.Column(db.Boolean, nullable=False, default=False)
    notes = db.Column(db.Text, nullable=True)
    session = db.relationship("GameSession", back_populates="participants")
    player_profile = db.relationship("PlayerProfile", back_populates="session_entries")
