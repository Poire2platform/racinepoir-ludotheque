from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import User, Game, Box, BoxEvent

main = Blueprint("main", __name__)


@main.route("/")
def index():
    return render_template("index.html")


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


@main.route("/games")
def games():
    games = Game.query.order_by(Game.title.asc()).all()
    return render_template("games.html", games=games)


@main.route("/boxes")
def boxes():
    boxes = Box.query.order_by(Box.id.asc()).all()
    return render_template("boxes.html", boxes=boxes)


@main.route("/boxes/<int:box_id>")
def box_detail(box_id):
    box = Box.query.get_or_404(box_id)
    events = BoxEvent.query.filter_by(box_id=box.id).order_by(BoxEvent.created_at.desc()).all()
    users = User.query.order_by(User.display_name.asc()).all()

    return render_template(
        "box_detail.html",
        box=box,
        events=events,
        users=users,
    )


@main.route("/scan/<token>")
@login_required
def scan_box(token):
    box = Box.query.filter_by(qr_code_token=token).first_or_404()

    return render_template(
        "scan_box.html",
        box=box,
    )


@main.route("/scan/<token>/confirm")
@login_required
def confirm_scan_box(token):
    box = Box.query.filter_by(qr_code_token=token).first_or_404()

    old_holder = box.current_holder

    box.current_holder = current_user

    event = BoxEvent(
        box=box,
        event_type="box_claimed",
        actor_user_id=current_user.id,
        from_holder_user_id=old_holder.id if old_holder else None,
        to_holder_user_id=current_user.id,
        notes=f"{current_user.display_name} a déclaré avoir cette boîte.",
    )

    db.session.add(event)

    if box.wanted_by_user_id == current_user.id:
        box.wanted_by_user_id = None

        clear_event = BoxEvent(
            box=box,
            event_type="wanted_by_cleared",
            actor_user_id=current_user.id,
            from_holder_user_id=current_user.id,
            notes="Demande effacée automatiquement : la boîte est maintenant chez la personne qui la demandait.",
        )

        db.session.add(clear_event)

    db.session.commit()

    return redirect(url_for("main.box_detail", box_id=box.id))


@main.route("/boxes/<int:box_id>/wanted/<int:user_id>")
@login_required
def set_wanted_by(box_id, user_id):
    box = Box.query.get_or_404(box_id)
    wanted_user = User.query.get_or_404(user_id)

    box.wanted_by = wanted_user

    if box.current_holder_user_id == wanted_user.id:
        box.wanted_by_user_id = None

        event = BoxEvent(
            box=box,
            event_type="wanted_by_cleared",
            actor_user_id=current_user.id,
            to_holder_user_id=wanted_user.id,
            notes="Demande effacée automatiquement : la boîte est déjà chez cette personne.",
        )
    else:
        event = BoxEvent(
            box=box,
            event_type="wanted_by_set",
            actor_user_id=current_user.id,
            to_holder_user_id=wanted_user.id,
            notes=f"Boîte demandée par {wanted_user.display_name}.",
        )

    db.session.add(event)
    db.session.commit()

    return redirect(url_for("main.box_detail", box_id=box.id))


@main.route("/boxes/<int:box_id>/wanted/clear")
@login_required
def clear_wanted_by(box_id):
    box = Box.query.get_or_404(box_id)
    old_wanted_by = box.wanted_by

    box.wanted_by = None

    event = BoxEvent(
        box=box,
        event_type="wanted_by_cleared",
        actor_user_id=current_user.id,
        from_holder_user_id=old_wanted_by.id if old_wanted_by else None,
        notes="Demande effacée depuis l’interface.",
    )

    db.session.add(event)
    db.session.commit()

    return redirect(url_for("main.box_detail", box_id=box.id))


@main.route("/boxes/<int:box_id>/mark-lost")
@login_required
def mark_box_lost(box_id):
    box = Box.query.get_or_404(box_id)

    box.lifecycle_status = "lost"

    event = BoxEvent(
        box=box,
        event_type="marked_lost",
        actor_user_id=current_user.id,
        notes=f"Boîte marquée comme perdue par {current_user.display_name}.",
    )

    db.session.add(event)
    db.session.commit()

    return redirect(url_for("main.box_detail", box_id=box.id))


# Redirects temporaires pour ne pas casser les vieux liens.
@main.route("/copies")
def copies_redirect():
    return redirect(url_for("main.boxes"))


@main.route("/copies/<int:copy_id>")
def copy_detail_redirect(copy_id):
    return redirect(url_for("main.box_detail", box_id=copy_id))
