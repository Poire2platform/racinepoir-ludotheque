import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

import click
from flask import current_app
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from .extensions import db
from .models import User
from .collection_import import import_collection, replace_collection
from .routes import current_registration_invite
from .bgg_bulk import apply_preview, build_preview


def register_commands(app):
    @app.cli.command("replace-official-collection")
    @click.option("--source", type=click.Path(exists=True, dir_okay=False), required=True)
    @click.option("--backup-dir", type=click.Path(file_okay=False), required=True)
    @click.option("--existing-backup-reference", default=None, metavar="REFERENCE")
    @click.option("--confirm", required=True, metavar="PHRASE")
    def replace_official_collection(source, backup_dir, existing_backup_reference, confirm):
        """Sauvegarde puis remplace la collection officielle en conservant les comptes."""
        if confirm != "REMPLACER-LA-COLLECTION-OFFICIELLE":
            raise click.ClickException("Phrase de confirmation invalide.")

        database_url = current_app.config["SQLALCHEMY_DATABASE_URI"]
        parsed = urlsplit(database_url)
        if parsed.scheme not in {"postgresql", "postgresql+psycopg2"}:
            raise click.ClickException("Cette commande exige PostgreSQL.")

        if existing_backup_reference:
            dump_description = f"sauvegarde existante confirmée : {existing_backup_reference}"
        else:
            backup_path = Path(backup_dir)
            backup_path.mkdir(mode=0o700, parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            dump_path = backup_path / f"racinepoir_ludotheque_prod-before-replace-{timestamp}.dump"
            dump_env = os.environ.copy()
            dump_env.update({
                "PGHOST": parsed.hostname or "",
                "PGPORT": str(parsed.port or 5432),
                "PGUSER": unquote(parsed.username or ""),
                "PGPASSWORD": unquote(parsed.password or ""),
                "PGDATABASE": parsed.path.lstrip("/"),
                "PGSSLMODE": "require",
            })
            try:
                subprocess.run(
                    ["pg_dump", "--format=custom", "--file", str(dump_path)],
                    env=dump_env,
                    check=True,
                )
            except (OSError, subprocess.CalledProcessError) as error:
                dump_path.unlink(missing_ok=True)
                raise click.ClickException("La sauvegarde a échoué; aucune donnée supprimée.") from error
            if not dump_path.is_file() or dump_path.stat().st_size == 0:
                dump_path.unlink(missing_ok=True)
                raise click.ClickException("La sauvegarde est vide; aucune donnée supprimée.")
            dump_path.chmod(0o600)
            dump_description = str(dump_path)

        mapping = {
            "Admin": "admin",
            "Anouk": "Anouk",
            "Anika": "Anouk",
            "Maxika": "Maxika",
            "Maxime": "admin",
        }
        report = replace_collection(source, mapping, "admin")
        if report["missing_mappings"] or report["missing_users"]:
            db.session.rollback()
            details = []
            if report["missing_mappings"]:
                details.append("correspondances : " + ", ".join(report["missing_mappings"]))
            if report["missing_users"]:
                details.append("comptes : " + ", ".join(report["missing_users"]))
            raise click.ClickException(
                "Prérequis incomplets (" + "; ".join(details) + "); aucune donnée supprimée."
            )
        click.echo(f"Sauvegarde : {dump_description}")
        click.echo(f"Lignes importées : {report['rows']}")
        click.echo(f"Jeux créés : {report['new_games']}")
        click.echo(f"Boîtes créées : {report['new_boxes']}")

    @app.cli.command("preview-bgg-enrichment")
    @click.option("--output", type=click.Path(dir_okay=False), required=True)
    @click.option("--delay", type=click.FloatRange(min=0.0), default=2.0, show_default=True)
    @click.option("--limit", type=click.IntRange(min=1), default=None)
    def preview_bgg_enrichment(output, delay, limit):
        """Recherche les correspondances BGG sans modifier la base."""
        manifest = build_preview(output, delay_seconds=delay, limit=limit)
        counts = {}
        for item in manifest["items"]:
            counts[item["status"]] = counts.get(item["status"], 0) + 1
        click.echo(f"Jeux inspectés : {len(manifest['items'])}")
        click.echo(f"Correspondances exactes uniques : {counts.get('exact_unique', 0)}")
        click.echo(f"Titres exacts ambigus : {counts.get('exact_ambiguous', 0)}")
        click.echo(f"Sans correspondance exacte : {counts.get('no_exact', 0)}")
        click.echo(f"Erreurs BGG : {counts.get('error', 0)}")
        click.echo(f"Manifeste écrit : {output}")
        click.echo("Aucune écriture en base.")

    @app.cli.command("apply-bgg-enrichment")
    @click.option("--manifest", type=click.Path(exists=True, dir_okay=False), required=True)
    @click.option("--delay", type=click.FloatRange(min=0.0), default=2.0, show_default=True)
    @click.option("--apply", is_flag=True, help="Confirme l'enrichissement des exacts uniques.")
    def apply_bgg_enrichment(manifest, delay, apply):
        """Applique uniquement les correspondances exactes uniques du manifeste."""
        if not apply:
            raise click.ClickException("Ajouter --apply après sauvegarde et validation du manifeste.")
        try:
            report = apply_preview(manifest, delay_seconds=delay)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise click.ClickException(str(error)) from error
        click.echo(f"Jeux enrichis : {report['enriched']}")
        click.echo(f"Jeux ignorés : {report['skipped']}")
        click.echo(f"Erreurs : {len(report['errors'])}")
        for error in report["errors"]:
            click.echo(f"- {error}")

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
    @click.option("--email", prompt="Adresse courriel (facultative)", default="")
    @click.option("--display-name", prompt="Nom affiché")
    def create_admin(username, email, display_name):
        """Crée un administrateur actif sans modifier les comptes existants."""
        username = username.strip()
        email = email.strip() or None
        display_name = display_name.strip()

        if not username or not display_name:
            raise click.ClickException("Le nom d’utilisateur et le nom affiché sont obligatoires.")

        if User.query.filter_by(username=username).first():
            raise click.ClickException("Ce nom d’utilisateur existe déjà.")

        if email and User.query.filter_by(email=email).first():
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
