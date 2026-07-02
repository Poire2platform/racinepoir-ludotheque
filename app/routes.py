from flask import Blueprint, render_template

from app.models import Game, GameCopy

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
