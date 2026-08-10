import click
from flask import current_app
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from .extensions import db
from .models import User
from .collection_import import import_collection
from .routes import current_registration_invite


def register_commands(app):
    @app.cli.command("show-registration-invite")
    def show_registration_invite():
        """Affiche le code quotidien seulement si les inscriptions sont activées."""
        if not current_app.config.get("REGISTRATION_INVITE_ENABLED", False):
            raise click.ClickException(
                "L'inscription est désactivée; configurer REGISTRATION_INVITE_ENABLED=true."
            )
        code, invite_day = current_registration_invite()
        click.echo(f"Code d'invitation du {invite_day} : {code}")

    @app.cli.command("import-official-collection")
    @click.option("--source", type=click.Path(exists=True, dir_okay=False), required=True)
    @click.option("--user-map", "user_maps", multiple=True, metavar="LABEL=USERNAME")
    @click.option("--default-holder", required=True, metavar="USERNAME")
    @click.option("--apply", is_flag=True, help="Écrit les créations après un aperçu validé.")
    def import_official_collection(source, user_maps, default_holder, apply):
        """Prévisualise ou importe la collection officielle sans écraser de données."""
        mapping = {}
        for value in user_maps:
            if "=" not in value:
                raise click.ClickException(
                    f"Correspondance invalide : {value!r}; utiliser LABEL=USERNAME."
                )
            label, username = value.split("=", 1)
            if not label.strip() or not username.strip():
                raise click.ClickException(
                    f"Correspondance invalide : {value!r}; utiliser LABEL=USERNAME."
                )
            mapping[label.strip()] = username.strip()

        try:
            report = import_collection(
                source,
                mapping,
                default_holder.strip(),
                apply=apply,
            )
        except ValueError as error:
            raise click.ClickException(str(error)) from error

        click.echo(f"Lignes source : {report['rows']}")
        click.echo(
            f"Jeux : {report['new_games']} à créer, "
            f"{report['existing_games']} existants"
        )
        click.echo(
            f"Boîtes : {report['new_boxes']} à créer, "
            f"{report['existing_boxes']} existantes"
        )
        if report["missing_mappings"]:
            click.echo("Correspondances manquantes : " + ", ".join(report["missing_mappings"]))
        if report["missing_users"]:
            click.echo("Comptes manquants : " + ", ".join(report["missing_users"]))
        if report["missing_mappings"] or report["missing_users"]:
            raise click.ClickException("Aucune écriture : prérequis incomplets.")
        click.echo("Import appliqué." if apply else "Aperçu seulement : aucune écriture.")

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
