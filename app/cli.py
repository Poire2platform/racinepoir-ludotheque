import click
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from .extensions import db
from .models import User


def register_commands(app):
    @app.cli.command("create-admin")
    @click.option("--username", prompt="Nom d’utilisateur")
    @click.option("--email", prompt="Adresse courriel")
    @click.option("--display-name", prompt="Nom affiché")
    def create_admin(username, email, display_name):
        """Crée un administrateur actif sans modifier les comptes existants."""
        username = username.strip()
        email = email.strip()
        display_name = display_name.strip()

        if not username or not email or not display_name:
            raise click.ClickException("Tous les champs sont obligatoires.")

        if User.query.filter_by(username=username).first():
            raise click.ClickException("Ce nom d’utilisateur existe déjà.")

        if User.query.filter_by(email=email).first():
            raise click.ClickException("Cette adresse courriel existe déjà.")

        password = click.prompt(
            "Mot de passe",
            hide_input=True,
            confirmation_prompt="Répéter le mot de passe",
        )

        user = User(
            username=username,
            email=email,
            display_name=display_name,
            password_hash=generate_password_hash(password),
            role="admin",
            is_active=True,
        )
        db.session.add(user)

        try:
            db.session.commit()
        except IntegrityError as error:
            db.session.rollback()
            raise click.ClickException(
                "Le compte n’a pas été créé, car son nom ou son adresse existe déjà."
            ) from error

        click.echo(f"Administrateur créé : {user.username} ({user.display_name}).")
