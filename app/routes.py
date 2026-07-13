from flask import Blueprint, render_template, redirect, url_for
from app.models import Game, GameCopy, CopyEvent

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

    return render_template("copy_detail.html", copy=copy, events=events)

@main.route("/scan/<token>")
def scan_copy(token):
    copy = GameCopy.query.filter_by(qr_code_token=token).first_or_404()
    return redirect(url_for("main.copy_detail", copy_id=copy.id))
