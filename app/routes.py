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
    next_page = request.args.get("next")

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        next_page = request.form.get("next") or request.args.get("next")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)

            if next_page and next_page.startswith("/"):
                return redirect(next_page)

            return redirect(url_for("main.index"))

        return render_template("login.html", error="Login invalide.", next_page=next_page)

    return render_template("login.html", next_page=next_page)


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

@main.route("/me/held-boxes")
@login_required
def my_held_boxes():
    boxes = Box.query.filter_by(
        current_holder_user_id=current_user.id
    ).order_by(Box.display_name.asc()).all()

    return render_template(
        "my_held_boxes.html",
        boxes=boxes,
    )


@main.route("/me/owned-boxes")
@login_required
def my_owned_boxes():
    boxes = Box.query.filter_by(
        owner_user_id=current_user.id
    ).order_by(Box.display_name.asc()).all()

    return render_template(
        "my_owned_boxes.html",
        boxes=boxes,
    )


@main.route("/boxes/<int:box_id>")
def box_detail(box_id):
    box = Box.query.get_or_404(box_id)
    events = BoxEvent.query.filter_by(box_id=box.id).order_by(BoxEvent.created_at.desc()).all()
    return render_template("box_detail.html", box=box, events=events)


def claim_box_for_current_user(box):
    old_holder = box.current_holder
    already_holder = old_holder and old_holder.id == current_user.id

    box.current_holder = current_user

    if already_holder:
        event_type = "box_claim_confirmed"
        notes = f"{current_user.display_name} a confirmé avoir déjà cette boîte."
    else:
        event_type = "box_claimed"
        notes = f"{current_user.display_name} a déclaré avoir cette boîte."

    db.session.add(BoxEvent(
        box=box,
        event_type=event_type,
        actor_user_id=current_user.id,
        from_holder_user_id=old_holder.id if old_holder else None,
        to_holder_user_id=current_user.id,
        notes=notes,
    ))

    fulfilled_request = None
    active_request = box.active_request_for_user(current_user)

    if active_request:
        active_request.status = "fulfilled"
        active_request.fulfilled_at = utcnow()
        fulfilled_request = active_request

        db.session.add(BoxEvent(
            box=box,
            event_type="box_request_fulfilled",
            actor_user_id=current_user.id,
            related_request=active_request,
            to_holder_user_id=current_user.id,
            notes=f"La demande de {current_user.display_name} a été complétée par le scan.",
        ))

    return old_holder, fulfilled_request, already_holder


@main.route("/scan/<token>")
@login_required
def scan_box(token):
    box = Box.query.filter_by(qr_code_token=token).first_or_404()

    old_holder, fulfilled_request, already_holder = claim_box_for_current_user(box)
    db.session.commit()

    return render_template(
        "scan_result.html",
        box=box,
        old_holder=old_holder,
        fulfilled_request=fulfilled_request,
        already_holder=already_holder,
    )


@main.route("/scan/<token>/confirm")
@login_required
def confirm_scan_box(token):
    return redirect(url_for("main.scan_box", token=token))


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
