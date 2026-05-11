from __future__ import annotations

from pathlib import Path

import yaml
from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, send_file, url_for

from webserver.presentation import build_manual_form_values, part_image_url, positive_int_arg
from webserver.runtime import reload_part_source_config, reload_ui_config
from webserver.services import file_actions, file_previews, generation_runner, image_derivatives, parts_repository, source_writer

parts_blueprint = Blueprint("parts", __name__)


def _resolve_part_file_path(part: dict[str, object], relative_path: str) -> Path | None:
    part_dir = Path(str(part["part_dir"])).resolve()
    requested = (part_dir / relative_path).resolve()
    if part_dir not in requested.parents and requested != part_dir:
        return None
    if not requested.exists() or not requested.is_file():
        return None
    return requested


def _load_part_or_404(part_id: str) -> dict[str, object]:
    part = current_app.config["PARTS_CACHE"].get_part(part_id)
    if part is None:
        abort(404)
    return part


def _load_part_with_assets_or_404(part_id: str) -> dict[str, object]:
    part = _load_part_or_404(part_id)
    return parts_repository.populate_part_assets(
        part,
        current_app.config["CONFIG_UI"]["preview_priority"],
    )


def _build_part_viewer_payload(part: dict[str, object]) -> dict[str, object]:
    items: list[dict[str, object]] = []
    part_dir = Path(str(part["part_dir"])).resolve(strict=False)
    for index, item in enumerate(part.get("preview_items", [])):
        relative_path = str(item["relative_path"])
        payload_item = {
            "index": index,
            "kind": item["kind"],
            "name": item["name"],
            "relativePath": relative_path,
            "originalUrl": url_for("parts.part_file", part_id=part["id"], relative_path=relative_path),
        }
        if item["kind"] == "image":
            payload_item["modalUrl"] = part_image_url(str(part["id"]), relative_path, preset="modal")
            payload_item["width"] = item.get("width")
            payload_item["height"] = item.get("height")
        else:
            source_path = part_dir / relative_path
            preview = file_previews.build_modal_preview(source_path, relative_path)
            payload_item["language"] = preview["language"]
            payload_item["languageLabel"] = preview["language_label"]
            payload_item["content"] = preview["content"]
            payload_item["truncated"] = preview["truncated"]
        items.append(payload_item)
    return {
        "partId": part["id"],
        "partName": part["name"],
        "items": items,
    }


@parts_blueprint.get("/parts/<part_id>")
def part_detail(part_id: str):
    part = _load_part_with_assets_or_404(part_id)
    manual_fields = current_app.config["CONFIG_UI"]["manual_fields"]
    previewable = part.get("preview_file")
    working_yaml_text = yaml.safe_dump(
        part["working_yaml"],
        allow_unicode=False,
        sort_keys=False,
    )
    working_manual_text = ""
    if part["working_manual"]:
        working_manual_text = yaml.safe_dump(
            part["working_manual"],
            allow_unicode=False,
            sort_keys=False,
        )
    return render_template(
        "part_detail.html",
        part=part,
        manual_fields=manual_fields,
        manual_form_values=build_manual_form_values(part["working_manual"], manual_fields),
        previewable=previewable,
        working_manual_text=working_manual_text,
        working_yaml_text=working_yaml_text,
        image_viewer_enabled=True,
    )


@parts_blueprint.post("/parts/<part_id>/manual")
def update_part_manual(part_id: str):
    part = _load_part_or_404(part_id)
    manual_fields = current_app.config["CONFIG_UI"]["manual_fields"]
    manual_path = Path(str(part["part_dir"])) / "working_manual.yaml"
    try:
        result = source_writer.write_part_manual_fields(
            manual_path,
            request.form.to_dict(),
            [field["name"] for field in manual_fields],
        )
    except source_writer.ValidationError as exc:
        flash(str(exc), "error")
        return redirect(url_for("parts.part_detail", part_id=part_id))

    summary = current_app.config["PARTS_CACHE"].reload_changed()
    for error in summary.errors:
        flash(error, "error")

    if result["file_exists"]:
        flash(f"Saved working_manual.yaml for {part['name']}.", "success")
    else:
        flash(f"Cleared working_manual.yaml for {part['name']}.", "success")
    return redirect(url_for("parts.part_detail", part_id=part_id))


@parts_blueprint.post("/parts/<part_id>/reload")
def reload_part_detail(part_id: str):
    part = _load_part_or_404(part_id)
    _, ui_changed = reload_ui_config(current_app)
    _, part_source_changed = reload_part_source_config(current_app)
    if ui_changed or part_source_changed:
        summary = current_app.config["PARTS_CACHE"].load_all()
        flash("Reloaded part details after applying config changes.", "success")
    else:
        summary = current_app.config["PARTS_CACHE"].reload_changed()
        flash(f"Reloaded part details for {part['name']} from disk.", "success")

    for error in summary.errors:
        flash(error, "error")
    if current_app.config["PARTS_CACHE"].get_part(part_id) is None:
        flash("That part is no longer available in the configured sources.", "error")
        return redirect(url_for("explore.explore"))
    return redirect(url_for("parts.part_detail", part_id=part_id))


@parts_blueprint.post("/parts/<part_id>/files/<path:relative_path>/actions/<action_id>")
def run_part_file_action(part_id: str, relative_path: str, action_id: str):
    part = _load_part_or_404(part_id)
    source_path = _resolve_part_file_path(part, relative_path)
    if source_path is None:
        abort(404)

    action = file_actions.get_file_action(action_id)
    if action is None or not action.applies_to(source_path):
        abort(404)

    invocation = action.build_invocation(source_path)
    if invocation.mode == "launch":
        generation_runner.launch_detached_command(invocation.command or [], cwd=invocation.cwd)
        target_name = invocation.target_path.name if invocation.target_path else source_path.name
        flash(
            f"Launched {action.label} for {relative_path}. Reload later to see {target_name}.",
            "success",
        )
        return redirect(url_for("parts.part_detail", part_id=part_id))

    if invocation.mode == "delete":
        source_path.unlink()
        summary = current_app.config["PARTS_CACHE"].reload_changed()
        for error in summary.errors:
            flash(error, "error")

        if current_app.config["PARTS_CACHE"].get_part(part_id) is None:
            flash(f"Deleted {relative_path}. That part is no longer available.", "success")
            return redirect(url_for("explore.explore"))

        flash(f"Deleted {relative_path}.", "success")
        return redirect(url_for("parts.part_detail", part_id=part_id))

    abort(400)


@parts_blueprint.get("/parts/<part_id>/files/<path:relative_path>")
def part_file(part_id: str, relative_path: str):
    part = _load_part_or_404(part_id)
    requested = _resolve_part_file_path(part, relative_path)
    if requested is None:
        abort(404)
    return send_file(requested)


@parts_blueprint.get("/parts/<part_id>/image/<path:relative_path>")
def part_image(part_id: str, relative_path: str):
    part = _load_part_or_404(part_id)
    source_path = _resolve_part_file_path(part, relative_path)
    if source_path is None:
        abort(404)

    preset = request.args.get("preset", "").strip() or None
    width = positive_int_arg(request.args.get("w"))
    height = positive_int_arg(request.args.get("h"))
    fit = request.args.get("fit", "").strip() or None
    quality = positive_int_arg(request.args.get("q"))

    target_path = image_derivatives.get_served_image_path(
        source_path,
        current_app.config["CONFIG_UI"]["image_serving"],
        preset_name=preset,
        width=width,
        height=height,
        fit=fit,
        quality=quality,
    )
    return send_file(target_path, conditional=True)


@parts_blueprint.get("/parts/<part_id>/viewer-data")
def part_image_viewer_data(part_id: str):
    part = _load_part_with_assets_or_404(part_id)
    return jsonify(_build_part_viewer_payload(part))
