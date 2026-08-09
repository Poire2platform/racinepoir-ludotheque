import os
import subprocess
from pathlib import Path


ACCESS_DIR = Path(__file__).parents[1] / "deploy" / "web01-access"


def test_web01_access_scripts_are_executable_and_valid_bash():
    scripts = (
        ACCESS_DIR / "install-web01-access",
        ACCESS_DIR / "racinepoir-ops",
    )

    for script in scripts:
        assert os.access(script, os.X_OK)
        result = subprocess.run(
            ["bash", "-n", script],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr


def test_sudoers_only_allows_the_root_owned_operations_wrapper():
    sudoers = (ACCESS_DIR / "racinepoir-ops.sudoers").read_text()

    rules = [line for line in sudoers.splitlines() if line and not line.startswith("#")]
    assert rules == [
        "deploy-racinepoir ALL=(root) NOPASSWD: /usr/local/sbin/racinepoir-ops"
    ]


def test_installation_preserves_private_environment_and_python_environment():
    installer = (ACCESS_DIR / "install-web01-access").read_text()

    assert 'EXPECTED_SOURCE=192.168.18.18' in installer
    assert 'no-agent-forwarding,no-port-forwarding,no-X11-forwarding,no-user-rc' in installer
    assert '-path "$APP_DIR/.env" -o -path "$APP_DIR/.venv"' in installer
    assert '/usr/bin/chmod 0600 "$APP_DIR/.env"' in installer
