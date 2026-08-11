import hashlib
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from sqlalchemy import func

from .extensions import db
from .models import (
    Box,
    BoxEvent,
    BoxRequest,
    Game,
    GameRating,
    GameSession,
    GameSessionParticipant,
    User,
)


@dataclass(frozen=True)
class CollectionRow:
    title: str
    owner_label: str
    holder_label: str
    duration_label: str


class _SheetTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self._cell is not None:
            value = " ".join("".join(self._cell).replace("\u200b", "").split())
            self._row.append(value)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


def read_collection_html(source):
    parser = _SheetTableParser()
    parser.feed(Path(source).read_text(encoding="utf-8"))

    header_index = None
    for index, row in enumerate(parser.rows):
        if "De Kessé" in row and "sta ki" in row and "Youcéquecé" in row:
            header_index = index
            header = row
            break

    if header_index is None:
        raise ValueError("Colonnes officielles introuvables dans la source HTML.")

    columns = {
        "title": header.index("De Kessé"),
        "owner": header.index("sta ki"),
        "holder": header.index("Youcéquecé"),
        "duration": header.index("Min de Jeu"),
    }
    required_width = max(columns.values()) + 1
    records = []

    for source_row in parser.rows[header_index + 1 :]:
        row = source_row + [""] * max(0, required_width - len(source_row))
        title = row[columns["title"]].strip()
        if not title:
            continue
        records.append(
            CollectionRow(
                title=title,
                owner_label=row[columns["owner"]].strip(),
                holder_label=row[columns["holder"]].strip(),
                duration_label=row[columns["duration"]].strip(),
            )
        )

    if not records:
        raise ValueError("La source ne contient aucune ligne de collection.")
    return records


def normalize_person_label(label):
    cleaned = " ".join(label.split()).strip()
    if cleaned.casefold().startswith("chez "):
        cleaned = cleaned[5:].strip()
    if "anouk" in cleaned.casefold() and (" et " in cleaned.casefold() or "," in cleaned):
        return "Anouk"
    return cleaned


def parse_duration(label):
    numbers = [int(value) for value in re.findall(r"\d+", label)]
    if not numbers:
        return None, None
    if len(numbers) == 1:
        return numbers[0], None if "+" in label else numbers[0]
    return numbers[0], numbers[1]


def official_box_token(title):
    digest = hashlib.sha256(title.casefold().strip().encode("utf-8")).hexdigest()[:24]
    return f"official-collection-{digest}"


def import_collection(source, user_mapping, default_holder_username, apply=False):
    rows = read_collection_html(source)
    normalized_mapping = {
        normalize_person_label(label).casefold(): username.strip()
        for label, username in user_mapping.items()
    }
    labels = {
        normalize_person_label(row.owner_label)
        for row in rows
        if normalize_person_label(row.owner_label)
    }
    labels.update(
        normalize_person_label(row.holder_label)
        for row in rows
        if normalize_person_label(row.holder_label)
    )

    missing_mappings = sorted(
        label for label in labels if label.casefold() not in normalized_mapping
    )
    usernames = set(normalized_mapping.values()) | {default_holder_username}
    users = {
        user.username: user
        for user in db.session.execute(
            db.select(User).where(User.username.in_(usernames))
        ).scalars()
    }
    missing_users = sorted(username for username in usernames if username not in users)

    report = {
        "rows": len(rows),
        "new_games": 0,
        "existing_games": 0,
        "new_boxes": 0,
        "existing_boxes": 0,
        "missing_mappings": missing_mappings,
        "missing_users": missing_users,
    }
    if missing_mappings or missing_users:
        return report

    for row in rows:
        normalized_title = row.title.casefold().strip()
        game = db.session.execute(
            db.select(Game).where(func.lower(Game.title) == normalized_title)
        ).scalar_one_or_none()
        if game:
            report["existing_games"] += 1
        else:
            report["new_games"] += 1

        token = official_box_token(row.title)
        box = db.session.execute(
            db.select(Box).where(Box.qr_code_token == token)
        ).scalar_one_or_none()
        if box:
            report["existing_boxes"] += 1
            continue
        report["new_boxes"] += 1

        if not apply:
            continue

        if game is None:
            min_playtime, max_playtime = parse_duration(row.duration_label)
            game = Game(
                title=row.title,
                normalized_title=normalized_title,
                min_playtime=min_playtime,
                max_playtime=max_playtime,
            )
            db.session.add(game)
            db.session.flush()

        owner_label = normalize_person_label(row.owner_label).casefold()
        holder_label = normalize_person_label(row.holder_label).casefold()
        owner = users[normalized_mapping[owner_label]]
        holder_username = (
            normalized_mapping[holder_label]
            if holder_label
            else default_holder_username
        )
        holder = users[holder_username]
        box = Box(
            display_name=row.title,
            game_id=game.id,
            owner_user_id=owner.id,
            current_holder_user_id=holder.id,
            qr_code_token=token,
            condition="unknown",
            availability_status="available",
            lifecycle_status="active",
            notes="Import de la collection officielle.",
        )
        db.session.add(box)
        db.session.flush()
        db.session.add(
            BoxEvent(
                box_id=box.id,
                event_type="created",
                actor_user_id=owner.id,
                to_holder_user_id=holder.id,
                notes="Boîte créée par l’import de la collection officielle.",
            )
        )

    if apply:
        db.session.commit()
    else:
        db.session.rollback()
    return report


def replace_collection(source, user_mapping, default_holder_username):
    """Replace collection data atomically while preserving users and profiles."""
    # Validate the source and every required account before scheduling deletes.
    preview = import_collection(
        source,
        user_mapping,
        default_holder_username,
        apply=False,
    )
    if preview["missing_mappings"] or preview["missing_users"]:
        return preview

    try:
        db.session.query(GameSessionParticipant).delete()
        db.session.query(GameSession).delete()
        db.session.query(BoxEvent).delete()
        db.session.query(BoxRequest).delete()
        db.session.query(GameRating).delete()
        db.session.query(Box).delete()
        db.session.query(Game).delete()
        db.session.flush()
        db.session.expunge_all()
        return import_collection(
            source,
            user_mapping,
            default_holder_username,
            apply=True,
        )
    except Exception:
        db.session.rollback()
        raise
