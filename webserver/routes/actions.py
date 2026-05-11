from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, request, url_for

from webserver.runtime import reload_part_source_config, reload_ui_config
from webserver.services import generation_runner

actions_blueprint = Blueprint("actions", __name__)


@actions_blueprint.post("/reload/fast")
def reload_fast():
    _, ui_changed = reload_ui_config(current_app)
    _, part_source_changed = reload_part_source_config(current_app)
    if ui_changed or part_source_changed:
        summary = current_app.config["PARTS_CACHE"].load_all()
        flash("Config changed, so fast reload promoted itself to a full cache rebuild.", "success")
    else:
        summary = current_app.config["PARTS_CACHE"].reload_changed()
    flash(
        f"Fast reload scanned {summary.scanned} parts and refreshed {summary.changed} changed entries.",
        "success",
    )
    if summary.removed:
        flash(f"Removed {summary.removed} missing entries from cache.", "success")
    for error in summary.errors:
        flash(error, "error")
    return redirect(request.referrer or url_for("explore.explore"))


@actions_blueprint.post("/reload/all")
def reload_all():
    reload_ui_config(current_app)
    reload_part_source_config(current_app)
    summary = current_app.config["PARTS_CACHE"].load_all()
    flash(
        f"Full reload loaded {summary.loaded} parts from disk.",
        "success",
    )
    for error in summary.errors:
        flash(error, "error")
    return redirect(request.referrer or url_for("explore.explore"))


@actions_blueprint.post("/generation/run")
def run_generation():
    generation_runner.launch_generation(Path(current_app.config["REPO_ROOT"]))
    flash("Launched action_make_all.py in a separate cmd window.", "success")
    return redirect(request.referrer or url_for("explore.explore"))
