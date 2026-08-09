from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import User


def test_create_admin_prompts_twice_and_creates_active_admin(app):
    runner = app.test_cli_runner()

    result = runner.invoke(
        args=[
            "create-admin",
            "--username", "maxime",
            "--email", "maxime@example.test",
            "--display-name", "Maxime",
        ],
        input="mot-de-passe-test\nmot-de-passe-test\n",
    )

    assert result.exit_code == 0
    assert "Administrateur créé : maxime (Maxime)." in result.output
    assert "mot-de-passe-test" not in result.output

    user = db.session.execute(
        db.select(User).filter_by(username="maxime")
    ).scalar_one()
    assert user.role == "admin"
    assert user.is_active is True
    assert check_password_hash(user.password_hash, "mot-de-passe-test")


def test_create_admin_refuses_existing_username_without_mutation(app, make_user):
    existing = make_user("maxime")
    runner = app.test_cli_runner()

    result = runner.invoke(
        args=[
            "create-admin",
            "--username", existing.username,
            "--email", "different@example.test",
            "--display-name", "Autre Maxime",
        ],
    )

    assert result.exit_code == 1
    assert "Ce nom d’utilisateur existe déjà." in result.output
    assert User.query.count() == 1


def test_create_admin_refuses_mismatched_passwords(app):
    runner = app.test_cli_runner()

    result = runner.invoke(
        args=[
            "create-admin",
            "--username", "maxime",
            "--email", "maxime@example.test",
            "--display-name", "Maxime",
        ],
        input="premier-mot-de-passe\nautre-mot-de-passe\n",
    )

    assert result.exit_code != 0
    assert "Error: The two entered values do not match." in result.output
    assert User.query.count() == 0


def test_create_admin_does_not_accept_password_on_command_line(app):
    runner = app.test_cli_runner()

    result = runner.invoke(
        args=[
            "create-admin",
            "--username", "maxime",
            "--email", "maxime@example.test",
            "--display-name", "Maxime",
            "--password", "secret-dans-la-commande",
        ],
    )

    assert result.exit_code == 2
    assert "No such option '--password'" in result.output
    assert User.query.count() == 0
