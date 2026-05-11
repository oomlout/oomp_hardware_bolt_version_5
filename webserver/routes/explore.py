from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from webserver.presentation import SORT_OPTIONS, selected_search_fields, selected_sort
from webserver.services import parts_repository

explore_blueprint = Blueprint("explore", __name__)


@explore_blueprint.get("/")
def index():
    return redirect(url_for("explore.explore"))


@explore_blueprint.get("/explore")
def explore():
    cache = current_app.config["PARTS_CACHE"]
    current_ui_config = current_app.config["CONFIG_UI"]
    all_parts = cache.get_parts()
    taxonomy_filters = {
        key: request.args.get(key, "").strip()
        for key in [field for field in request.args.keys() if field.startswith("taxonomy_")]
    }
    query = request.args.get("q", "").strip()
    selected_fields = selected_search_fields(
        current_ui_config,
        request.args.getlist("search_fields"),
    )
    sort_name = selected_sort(request.args.get("sort"))
    filtered_parts = parts_repository.filter_parts(
        all_parts,
        taxonomy_filters,
        query,
        selected_fields,
        sort_name=sort_name,
    )
    navigation = parts_repository.build_taxonomy_navigation(all_parts, taxonomy_filters)
    breadcrumb_params: dict[str, Any] = {}
    for pair in navigation["selected"]:
        breadcrumb_params[pair["key"]] = pair["value"]
        pair["params"] = dict(breadcrumb_params)
        if query:
            pair["params"]["q"] = query
        if sort_name:
            pair["params"]["sort"] = sort_name
        for field_name in selected_fields:
            pair["params"].setdefault("search_fields", [])
            pair["params"]["search_fields"].append(field_name)
        pair["url"] = url_for("explore.explore", **pair["params"])
    for option in navigation["options"]:
        params = {key: value for key, value in taxonomy_filters.items() if value}
        params[option["key"]] = option["value"]
        if query:
            params["q"] = query
        if selected_fields:
            params["search_fields"] = list(selected_fields)
        if sort_name:
            params["sort"] = sort_name
        option["params"] = params
        option["url"] = url_for("explore.explore", **params)
    return render_template(
        "explore.html",
        all_parts=all_parts,
        parts=filtered_parts,
        taxonomy_filters=taxonomy_filters,
        query=query,
        sort_name=sort_name,
        sort_options=SORT_OPTIONS,
        search_field_options=current_ui_config["search_fields"]["available"],
        selected_search_fields=selected_fields,
        navigation=navigation,
        cache_errors=cache.get_errors(),
        image_viewer_enabled=True,
    )
