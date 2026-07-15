from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash
from app.extensions import db
from app.models import User, Game, Box, BoxEvent, BoxRequest, utcnow

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
    return render_template("games.html", games=Game.query.order_by(Game.title.asc()).all())

@main.route("/boxes")
def boxes():
    return render_template("boxes.html", boxes=Box.query.order_by(Box.id.asc()).all())

@main.route("/boxes/<int:box_id>")
def box_detail(box_id):
    box = Box.query.get_or_404(box_id)
    events = BoxEvent.query.filter_by(box_id=box.id).order_by(BoxEvent.created_at.desc()).all()
    return render_template("box_detail.html", box=box, events=events)

@main.route("/scan/<token>")
@login_required
def scan_box(token):
    box = Box.query.filter_by(qr_code_token=token).first_or_404()
    return render_template("scan_box.html", box=box)

@main.route("/scan/<token>/confirm")
@login_required
def confirm_scan_box(token):
    box = Box.query.filter_by(qr_code_token=token).first_or_404()
    old_holder = box.current_holder
    box.current_holder = current_user

    db.session.add(BoxEvent(
        box=box,
        event_type="box_claimed",
        actor_user_id=current_user.id,
        from_holder_user_id=old_holder.id if old_holder else None,
        to_holder_user_id=current_user.id,
        notes=f"{current_user.display_name} a déclaré avoir cette boîte.",
    ))

    active_request = box.active_request_for_user(current_user)
    if active_request:
        active_request.status = "fulfilled"
        active_request.fulfilled_at = utcnow()
        db.session.add(BoxEvent(
            box=box,
            event_type="box_request_fulfilled",
            actor_user_id=current_user.id,
            related_request=active_request,
            to_holder_user_id=current_user.id,
            notes=f"La demande de {current_user.display_name} a été complétée par le claim.",
        ))

    db.session.commit()
    return redirect(url_for("main.box_detail", box_id=box.id))

@main.route("/boxes/<int:box_id>/request")
@login_required
def request_box(box_id):
    box = Box.query.get_or_404(box_id)

    if box.current_holder_user_id == current_user.id:
        db.session.add(BoxEvent(
            box=box,
            event_type="box_request_ignored",
            actor_user_id=current_user.id,
            notes="Demande ignorée : cette personne a déjà la boîte.",
        ))
        db.session.commit()
        return redirect(url_for("main.box_detail", box_id=box.id))

    if box.active_request_for_user(current_user):
        return redirect(url_for("main.box_detail", box_id=box.id))

    box_request = BoxRequest(box=box, requester=current_user, status="active")
    db.session.add(box_request)
    db.session.flush()

    db.session.add(BoxEvent(
        box=box,
        event_type="box_requested",
        actor_user_id=current_user.id,
        related_request=box_request,
        to_holder_user_id=current_user.id,
        notes=f"{current_user.display_name} a ajouté son nom à la file d’attente.",
    ))

    db.session.commit()
    return redirect(url_for("main.box_detail", box_id=box.id))

@main.route("/boxes/<int:box_id>/request/clear")
@login_required
def clear_box_request(box_id):
    box = Box.query.get_or_404(box_id)
    active_request = box.active_request_for_user(current_user)

    if not active_request and current_user.role != "admin":
        return "Action refusée : tu peux seulement annuler ta propre demande.", 403

    if current_user.role == "admin" and not active_request:
        active_request = BoxRequest.query.filter_by(
            box_id=box.id,
            status="active",
        ).order_by(BoxRequest.created_at.asc()).first()

    if not active_request:
        return redirect(url_for("main.box_detail", box_id=box.id))

    active_request.status = "cancelled"
    active_request.cancelled_at = utcnow()

    db.session.add(BoxEvent(
        box=box,
        event_type="box_request_cancelled",
        actor_user_id=current_user.id,
        related_request=active_request,
        from_holder_user_id=active_request.requester_user_id,
        notes=f"Demande annulée par {current_user.display_name}.",
    ))

    db.session.commit()
    return redirect(url_for("main.box_detail", box_id=box.id))

@main.route("/boxes/<int:box_id>/mark-lost")
@login_required
def mark_box_lost(box_id):
    box = Box.query.get_or_404(box_id)
    box.lifecycle_status = "lost"
    db.session.add(BoxEvent(
        box=box,
        event_type="marked_lost",
        actor_user_id=current_user.id,
        notes=f"Boîte marquée comme perdue par {current_user.display_name}.",
    ))
    db.session.commit()
    return redirect(url_for("main.box_detail", box_id=box.id))

@main.route("/copies")
def copies_redirect():
    return redirect(url_for("main.boxes"))

@main.route("/copies/<int:copy_id>")
def copy_detail_redirect(copy_id):
    return redirect(url_for("main.box_detail", box_id=copy_id))
