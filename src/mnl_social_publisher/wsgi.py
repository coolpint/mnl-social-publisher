from __future__ import annotations

from .settings import Settings
from .web_app import create_web_app


app = create_web_app(Settings.from_env())
application = app
