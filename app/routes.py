from flask import Blueprint, render_template, redirect, url_for, request
from app.models import Game, GameCopy, CopyEvent, Location
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash
from app.models import Game, GameCopy, CopyEvent, Location, User

main = Blueprint("main", __name__)


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/games")
def games():
    games = Game.query.order_by(Game.title.asc()).all()
    return render_template("games.html", games=games)


@main.route("/copies")
def copies():
    copies = GameCopy.query.order_by(GameCopy.id.asc()).all()
    return render_template("copies.html", copies=copies)


@main.route("/copies/<int:copy_id>")
def copy_detail(copy_id):
    copy = GameCopy.query.get_or_404(copy_id)

    events = (
        CopyEvent.query
        .filter_by(game_copy_id=copy.id)
        .order_by(CopyEvent.created_at.desc())
        .all()
    )

    locations = Location.query.order_by(Location.name.asc()).all()

    return render_template(
        "copy_detail.html",
        copy=copy,
        events=events,
        locations=locations,
    )



@main.route("/scan/<token>")
def scan_copy(token):
    copy = GameCopy.query.filter_by(qr_code_token=token).first_or_404()
    locations = Location.query.order_by(Location.name.asc()).all()

    return render_template(
        "scan_copy.html",
        copy=copy,
        locations=locations,
    )


@main.route("/copies/<int:copy_id>/mark-lost")
def mark_copy_lost(copy_id):
    copy = GameCopy.query.get_or_404(copy_id)

    copy.lifecycle_status = "lost"

    event = CopyEvent(
        game_copy=copy,
        event_type="marked_lost",
        actor_user_id=copy.owner_user_id,
        notes="Copie marquée comme perdue depuis l'interface dev.",
    )

    from app.extensions import db
    db.session.add(event)
    db.session.commit()

    return redirect(url_for("main.copy_detail", copy_id=copy.id))
@main.route("/copies/<int:copy_id>/move/<int:location_id>")
def move_copy(copy_id, location_id):
    copy = GameCopy.query.get_or_404(copy_id)

    from app.models import Location
    from app.extensions import db

    new_location = Location.query.get_or_404(location_id)
    old_location = copy.current_location

    copy.current_location = new_location

    # Règle métier : si la copie arrive à sa wanted_location, on efface wanted_location.
    if copy.wanted_location_id == new_location.id:
        copy.wanted_location_id = None

    event = CopyEvent(
        game_copy=copy,
        event_type="location_changed",
        actor_user_id=copy.owner_user_id,
        from_location_id=old_location.id if old_location else None,
        to_location_id=new_location.id,
        notes=f"Location changée vers {new_location.name}.",
    )

    db.session.add(event)
    db.session.commit()

    return redirect(url_for("main.copy_detail", copy_id=copy.id))

@main.route("/copies/<int:copy_id>/wanted/<int:location_id>")
def set_wanted_location(copy_id, location_id):
    copy = GameCopy.query.get_or_404(copy_id)
    new_wanted_location = Location.query.get_or_404(location_id)

    from app.extensions import db

    copy.wanted_location = new_wanted_location

    # Règle métier : si la copie est déjà à la location voulue, on efface wanted_location.
    if copy.current_location_id == new_wanted_location.id:
        copy.wanted_location_id = None
        event_type = "wanted_location_cleared"
        notes = "Wanted location effacée automatiquement car la copie est déjà à cet endroit."
    else:
        event_type = "wanted_location_set"
        notes = f"Wanted location définie vers {new_wanted_location.name}."

    event = CopyEvent(
        game_copy=copy,
        event_type=event_type,
        actor_user_id=copy.owner_user_id,
        to_location_id=new_wanted_location.id,
        notes=notes,
    )

    db.session.add(event)
    db.session.commit()

    return redirect(url_for("main.copy_detail", copy_id=copy.id))


@main.route("/copies/<int:copy_id>/wanted/clear")
def clear_wanted_location(copy_id):
    copy = GameCopy.query.get_or_404(copy_id)

    from app.extensions import db

    old_wanted_location = copy.wanted_location
    copy.wanted_location = None

    event = CopyEvent(
        game_copy=copy,
        event_type="wanted_location_cleared",
        actor_user_id=copy.owner_user_id,
        from_location_id=old_wanted_location.id if old_wanted_location else None,
        notes="Wanted location effacée depuis l'interface dev.",
    )

    db.session.add(event)
    db.session.commit()

    return redirect(url_for("main.copy_detail", copy_id=copy.id))
@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("main.index"))

        return render_template("login.html", error="Login invalide.")

    return render_template("login.html")


@main.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("main.index"))
