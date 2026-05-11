from __future__ import annotations

from flask import Flask

from webserver.routes.actions import actions_blueprint
from webserver.routes.explore import explore_blueprint
from webserver.routes.manual import manual_blueprint
from webserver.routes.parts import parts_blueprint


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(explore_blueprint)
    app.register_blueprint(parts_blueprint)
    app.register_blueprint(manual_blueprint)
    app.register_blueprint(actions_blueprint)
