import secrets
from io import BytesIO

from flask import Blueprint, render_template, redirect, url_for, request, send_file
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.bgg import BggApiError, game_details, search_games
from app.models import User, Game, Box, BoxEvent, BoxRequest, utcnow

main = Blueprint("main", __name__)
BOX_CONDITIONS = ("unknown", "good", "worn", "incomplete")
NEW_GAME_VALUE = "__new__"
MANUAL_GAME_VALUE = "__manual__"
USER_ROLES = ("member", "admin")


def generate_box_token():
    while True:
        token = secrets.token_urlsafe(16)
        if not Box.query.filter_by(qr_code_token=token).first():
            return token


def can_manage_box(box):
    return (
        current_user.is_authenticated
        and (current_user.role == "admin" or box.owner_user_id == current_user.id)
    )


def admin_required():
    if not current_user.is_authenticated or current_user.role != "admin":
        return "Action refusée : admin requis.", 403
    return None


def user_form_data(user):
    return {
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "is_active": "yes" if user.is_active else "",
    }


def box_form_data(box):
    return {
        "game_id": str(box.game_id) if box.game_id else "",
        "new_game_title": "",
        "owner_user_id": str(box.owner_user_id),
        "condition": box.condition,
        "notes": box.notes or "",
    }


def render_box_form(**context):
    context.setdefault("games", Game.query.order_by(Game.title.asc()).all())
    context.setdefault("users", User.query.order_by(User.display_name.asc()).all())
    context.setdefault("new_game_value", NEW_GAME_VALUE)
    context.setdefault("manual_game_value", MANUAL_GAME_VALUE)
    return render_template("box_form.html", **context)


def resolve_box_game(form):
    game_choice = form.get("game_id") or ""

    if game_choice == NEW_GAME_VALUE:
        title = (form.get("new_game_title") or "").strip()
        if not title:
            return None, "Le nom du nouveau jeu est obligatoire."

        bgg_choice = form.get("bgg_choice") or ""

        if not bgg_choice:
            try:
                matches = search_games(title)
            except BggApiError as exc:
                return None, str(exc), None

            if matches:
                return None, None, matches

        if bgg_choice and bgg_choice != MANUAL_GAME_VALUE:
            existing_game = Game.query.filter_by(bgg_id=bgg_choice).first()
            if existing_game:
                return existing_game, None, None

            try:
                details = game_details(bgg_choice)
            except BggApiError as exc:
                return None, str(exc), None

            if details:
                game = Game(
                    title=details["title"],
                    normalized_title=details["title"].lower(),
                )
                apply_bgg_details(game, details)
                db.session.add(game)
                return game, None, None

        game = Game(title=title, normalized_title=title.lower())
        db.session.add(game)
        return game, None, None

    if not game_choice:
        return None, "Choisis un jeu existant ou crée un nouveau jeu.", None

    game = Game.query.get(game_choice)
    if not game:
        return None, "Le jeu référencé sélectionné est introuvable.", None

    return game, None, None


def resolve_box_owner(form):
    owner_id = form.get("owner_user_id") or None
    if not owner_id:
        return None, "Le propriétaire est obligatoire."

    owner = User.query.get(owner_id)
    if not owner:
        return None, "Le propriétaire sélectionné est introuvable."

    return owner, None


def apply_bgg_details(game, details):
    game.title = details["title"]
    game.normalized_title = details["title"].lower()
    game.description = details["description"]
    game.publisher = details["publisher"]
    game.year_published = details["year_published"]
    game.min_players = details["min_players"]
    game.max_players = details["max_players"]
    game.min_playtime = details["min_playtime"]
    game.max_playtime = details["max_playtime"]
    game.age_min = details["age_min"]
    game.complexity = details["complexity"]
    game.bgg_id = details["bgg_id"]
    game.cover_image_url = details["cover_image_url"]

    for box in game.boxes:
        box.display_name = game.title


@main.route("/")
@login_required
def index():
    held_count = Box.query.filter_by(
        current_holder_user_id=current_user.id
    ).count()

    owned_count = Box.query.filter_by(
        owner_user_id=current_user.id
    ).count()

    requested_count = BoxRequest.query.filter_by(
        requester_user_id=current_user.id,
        status="active"
    ).count()

    return render_template(
        "index.html",
        held_count=held_count,
        owned_count=owned_count,
        requested_count=requested_count,
    )


@main.route("/login", methods=["GET", "POST"])
def login():
    next_page = request.args.get("next")

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        next_page = request.form.get("next") or request.args.get("next")

        user = User.query.filter_by(username=username).first()

        if user and not user.is_active:
            return render_template("login.html", error="Compte désactivé.", next_page=next_page)

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


@main.route("/me/profile", methods=["GET", "POST"])
@login_required
def my_profile():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        display_name = (request.form.get("display_name") or "").strip()
        current_password = request.form.get("current_password") or ""
        new_password = request.form.get("new_password") or ""

        if not email or not display_name:
            return render_template("my_profile.html", error="Nom affiché et email sont obligatoires.", form=request.form)

        existing_email = User.query.filter_by(email=email).first()
        if existing_email and existing_email.id != current_user.id:
            return render_template("my_profile.html", error="Cet email est déjà utilisé.", form=request.form)

        if new_password:
            if not check_password_hash(current_user.password_hash, current_password):
                return render_template("my_profile.html", error="Mot de passe actuel invalide.", form=request.form)

            current_user.password_hash = generate_password_hash(new_password)

        current_user.email = email
        current_user.display_name = display_name

        db.session.commit()
        return redirect(url_for("main.my_profile"))

    form = {
        "email": current_user.email,
        "display_name": current_user.display_name,
    }
    return render_template("my_profile.html", form=form)


@main.route("/users")
@login_required
def users():
    denied = admin_required()
    if denied:
        return denied

    users = User.query.order_by(User.display_name.asc()).all()
    return render_template("users.html", users=users)


@main.route("/users/new", methods=["GET", "POST"])
@login_required
def new_user():
    denied = admin_required()
    if denied:
        return denied

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        display_name = (request.form.get("display_name") or "").strip()
        password = request.form.get("password") or ""
        role = request.form.get("role") or "member"
        is_active = request.form.get("is_active") == "yes"

        if not username or not email or not display_name or not password:
            return render_template("user_form.html", error="Tous les champs principaux sont obligatoires.", form=request.form, roles=USER_ROLES)

        if role not in USER_ROLES:
            role = "member"

        if User.query.filter_by(username=username).first():
            return render_template("user_form.html", error="Ce username existe déjà.", form=request.form, roles=USER_ROLES)

        if User.query.filter_by(email=email).first():
            return render_template("user_form.html", error="Cet email existe déjà.", form=request.form, roles=USER_ROLES)

        user = User(
            username=username,
            email=email,
            display_name=display_name,
            password_hash=generate_password_hash(password),
            role=role,
            is_active=is_active,
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("main.users"))

    return render_template("user_form.html", form={"role": "member", "is_active": "yes"}, roles=USER_ROLES)


@main.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    denied = admin_required()
    if denied:
        return denied

    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        display_name = (request.form.get("display_name") or "").strip()
        password = request.form.get("password") or ""
        role = request.form.get("role") or "member"
        is_active = request.form.get("is_active") == "yes"

        if not username or not email or not display_name:
            return render_template("user_form.html", user=user, error="Username, email et nom affiché sont obligatoires.", form=request.form, roles=USER_ROLES, mode="edit")

        if role not in USER_ROLES:
            role = "member"

        existing_username = User.query.filter_by(username=username).first()
        if existing_username and existing_username.id != user.id:
            return render_template("user_form.html", user=user, error="Ce username existe déjà.", form=request.form, roles=USER_ROLES, mode="edit")

        existing_email = User.query.filter_by(email=email).first()
        if existing_email and existing_email.id != user.id:
            return render_template("user_form.html", user=user, error="Cet email existe déjà.", form=request.form, roles=USER_ROLES, mode="edit")

        if user.id == current_user.id and (role != "admin" or not is_active):
            return render_template(
                "user_form.html",
                user=user,
                error="Tu ne peux pas retirer ton propre accès admin ou désactiver ton propre compte.",
                form=request.form,
                roles=USER_ROLES,
                mode="edit",
            )

        user.username = username
        user.email = email
        user.display_name = display_name
        user.role = role
        user.is_active = is_active

        if password:
            user.password_hash = generate_password_hash(password)

        db.session.commit()
        return redirect(url_for("main.users"))

    return render_template("user_form.html", user=user, form=user_form_data(user), roles=USER_ROLES, mode="edit")


@main.route("/games")
def games():
    return render_template("games.html", games=Game.query.order_by(Game.title.asc()).all())


@main.route("/games/<int:game_id>")
def game_detail(game_id):
    game = Game.query.get_or_404(game_id)
    boxes = Box.query.filter_by(game_id=game.id).order_by(Box.id.asc()).all()
    return render_template("game_detail.html", game=game, boxes=boxes)


@main.route("/games/<int:game_id>/bgg", methods=["GET", "POST"])
@login_required
def populate_game_from_bgg(game_id):
    game = Game.query.get_or_404(game_id)

    if request.method == "POST":
        bgg_choice = request.form.get("bgg_choice") or ""
        if not bgg_choice:
            return redirect(url_for("main.populate_game_from_bgg", game_id=game.id))

        try:
            details = game_details(bgg_choice)
        except BggApiError as exc:
            return render_template("game_bgg_matches.html", game=game, error=str(exc), matches=[])

        if not details:
            return render_template("game_bgg_matches.html", game=game, error="Aucun détail BGG trouvé pour ce jeu.", matches=[])

        apply_bgg_details(game, details)
        db.session.commit()
        return redirect(url_for("main.game_detail", game_id=game.id))

    try:
        matches = search_games(game.title)
    except BggApiError as exc:
        return render_template("game_bgg_matches.html", game=game, error=str(exc), matches=[])

    return render_template("game_bgg_matches.html", game=game, matches=matches)


@main.route("/boxes")
def boxes():
    return render_template("boxes.html", boxes=Box.query.order_by(Box.id.asc()).all())


@main.route("/boxes/new", methods=["GET", "POST"])
@login_required
def new_box():
    if request.method == "POST":
        condition = request.form.get("condition") or "unknown"
        notes = (request.form.get("notes") or "").strip() or None

        game, game_error, bgg_matches = resolve_box_game(request.form)
        if bgg_matches:
            return render_box_form(form=request.form, bgg_matches=bgg_matches)
        if game_error:
            return render_box_form(error=game_error, form=request.form)

        owner, owner_error = resolve_box_owner(request.form)
        if owner_error:
            return render_box_form(error=owner_error, form=request.form)

        if condition not in BOX_CONDITIONS:
            condition = "unknown"

        box = Box(
            display_name=game.title,
            game=game,
            owner=owner,
            current_holder=owner,
            qr_code_token=generate_box_token(),
            condition=condition,
            availability_status="available",
            lifecycle_status="active",
            notes=notes,
        )
        db.session.add(box)
        db.session.flush()

        db.session.add(BoxEvent(
            box=box,
            event_type="box_created",
            actor_user_id=current_user.id,
            to_holder_user_id=owner.id,
            notes=f"Boîte créée par {current_user.display_name} pour {owner.display_name}.",
        ))

        db.session.commit()
        return redirect(url_for("main.box_detail", box_id=box.id))

    return render_box_form(
        form={
            "game_id": NEW_GAME_VALUE,
            "owner_user_id": str(current_user.id),
        }
    )


@main.route("/boxes/<int:box_id>/edit", methods=["GET", "POST"])
@login_required
def edit_box(box_id):
    box = Box.query.get_or_404(box_id)

    if not can_manage_box(box):
        return "Action refusée : seul le propriétaire ou un admin peut modifier cette boîte.", 403

    if request.method == "POST":
        condition = request.form.get("condition") or "unknown"
        notes = (request.form.get("notes") or "").strip() or None

        game, game_error, bgg_matches = resolve_box_game(request.form)
        if bgg_matches:
            return render_box_form(box=box, form=request.form, mode="edit", bgg_matches=bgg_matches)
        if game_error:
            return render_box_form(box=box, error=game_error, form=request.form, mode="edit")

        owner, owner_error = resolve_box_owner(request.form)
        if owner_error:
            return render_box_form(box=box, error=owner_error, form=request.form, mode="edit")

        if condition not in BOX_CONDITIONS:
            condition = "unknown"

        box.game = game
        box.display_name = game.title
        box.owner = owner
        box.condition = condition
        box.notes = notes

        db.session.add(BoxEvent(
            box=box,
            event_type="box_updated",
            actor_user_id=current_user.id,
            notes=f"Boîte modifiée par {current_user.display_name}.",
        ))

        db.session.commit()
        return redirect(url_for("main.box_detail", box_id=box.id))

    return render_template(
        "box_form.html",
        box=box,
        games=Game.query.order_by(Game.title.asc()).all(),
        users=User.query.order_by(User.display_name.asc()).all(),
        form=box_form_data(box),
        mode="edit",
        new_game_value=NEW_GAME_VALUE,
        manual_game_value=MANUAL_GAME_VALUE,
    )


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
    users = User.query.order_by(User.display_name.asc()).all() if current_user.is_authenticated and can_manage_box(box) else []
    return render_template("box_detail.html", box=box, events=events, users=users)


@main.route("/boxes/<int:box_id>/transfer", methods=["POST"])
@login_required
def transfer_box(box_id):
    box = Box.query.get_or_404(box_id)

    if not can_manage_box(box):
        return "Action refusée : seul le propriétaire ou un admin peut changer le détenteur.", 403

    new_holder_id = request.form.get("current_holder_user_id") or None
    new_holder = User.query.get(new_holder_id) if new_holder_id else None

    if not new_holder:
        return "Détenteur introuvable.", 400

    old_holder = box.current_holder

    if old_holder and old_holder.id == new_holder.id:
        return redirect(url_for("main.box_detail", box_id=box.id))

    box.current_holder = new_holder

    db.session.add(BoxEvent(
        box=box,
        event_type="holder_changed_manually",
        actor_user_id=current_user.id,
        from_holder_user_id=old_holder.id if old_holder else None,
        to_holder_user_id=new_holder.id,
        notes=f"Détenteur changé manuellement par {current_user.display_name}.",
    ))

    db.session.commit()
    return redirect(url_for("main.box_detail", box_id=box.id))


@main.route("/boxes/<int:box_id>/label")
@login_required
def box_label(box_id):
    box = Box.query.get_or_404(box_id)

    if not can_manage_box(box):
        return "Action refusée : seul le propriétaire ou un admin peut imprimer cette étiquette.", 403

    scan_url = url_for("main.scan_box", token=box.qr_code_token, _external=True)
    return render_template("box_label.html", box=box, scan_url=scan_url)


@main.route("/boxes/<int:box_id>/qr.png")
@login_required
def box_qr(box_id):
    box = Box.query.get_or_404(box_id)

    if not can_manage_box(box):
        return "Action refusée : seul le propriétaire ou un admin peut générer ce QR.", 403

    import qrcode

    scan_url = url_for("main.scan_box", token=box.qr_code_token, _external=True)
    image = qrcode.make(scan_url)
    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)

    return send_file(output, mimetype="image/png")


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

    if not can_manage_box(box):
        return "Action refusée : seul le propriétaire ou un admin peut changer l’état de cette boîte.", 403

    box.lifecycle_status = "lost"

    db.session.add(BoxEvent(
        box=box,
        event_type="marked_lost",
        actor_user_id=current_user.id,
        notes=f"Boîte marquée comme perdue par {current_user.display_name}.",
    ))

    db.session.commit()
    return redirect(url_for("main.box_detail", box_id=box.id))


@main.route("/boxes/<int:box_id>/mark-active")
@login_required
def mark_box_active(box_id):
    box = Box.query.get_or_404(box_id)

    if not can_manage_box(box):
        return "Action refusée : seul le propriétaire ou un admin peut changer l’état de cette boîte.", 403

    box.lifecycle_status = "active"

    db.session.add(BoxEvent(
        box=box,
        event_type="marked_active",
        actor_user_id=current_user.id,
        notes=f"Boîte remise active par {current_user.display_name}.",
    ))

    db.session.commit()
    return redirect(url_for("main.box_detail", box_id=box.id))


@main.route("/copies")
def copies_redirect():
    return redirect(url_for("main.boxes"))


@main.route("/copies/<int:copy_id>")
def copy_detail_redirect(copy_id):
    return redirect(url_for("main.box_detail", box_id=copy_id))
