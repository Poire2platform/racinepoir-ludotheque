"""Passenger/cPanel entrypoint for RacinePoir Ludothèque.

cPanel's Python App / Passenger integration looks for a module-level
``application`` object. Keep this file at the project root, beside
``requirements.txt`` and ``run.py``.
"""

import os
import sys


PROJECT_ROOT = os.path.dirname(__file__)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app  # noqa: E402


application = create_app()
