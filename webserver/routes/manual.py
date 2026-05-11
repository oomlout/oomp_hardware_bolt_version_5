from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from webserver.presentation import build_form_values, select_family
from webserver.services import config_form, source_writer

manual_blueprint = Blueprint("manual", __name__)


@manual_blueprint.route("/add", methods=["GET", "POST"])
def add_item():
    loaded_form_config = config_form.load_form_config(
        Path(current_app.config["CONFIG_FORM_BASE_PATH"]),
        Path(current_app.config["CONFIG_FORM_PATH"]),
    )
    current_app.config["CONFIG_FORM"] = loaded_form_config
    families = loaded_form_config["families"]
    selected_slug, family_config = select_family(
        loaded_form_config,
        request.values.get("family") if request.method == "POST" else request.args.get("family"),
    )
    if request.method == "POST":
        submitted = request.form.to_dict()
        try:
            result = source_writer.write_manual_entry(
                Path(current_app.config["MANUAL_QUEUE_PATH"]),
                submitted,
                family_config,
            )
        except source_writer.ValidationError as exc:
            flash(str(exc), "error")
            form_values = build_form_values(family_config, submitted)
            return render_template(
                "add_item.html",
                family_slug=selected_slug,
                family_config=family_config,
                families=families,
                form_values=form_values,
                image_viewer_enabled=False,
            )

        flash(
            f"Recorded manual entry #{result['entry_count']} in {result['target_file']}.",
            "success",
        )
        return redirect(url_for("manual.add_item", family=selected_slug))

    form_values = build_form_values(family_config)
    return render_template(
        "add_item.html",
        family_slug=selected_slug,
        family_config=family_config,
        families=families,
        form_values=form_values,
        image_viewer_enabled=False,
    )
