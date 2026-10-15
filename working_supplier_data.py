"""Copy supplier harvests into this repo and expose them by OOMP ID.

The supplier scraper is maintained separately. Its CSV files are treated as
read-only inputs; this module copies snapshots into ``source_file`` so part
generation is reproducible from the repository.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path


DEFAULT_SOURCE = Path(r"C:\od\OneDrive\docs\project_bolt_web_scraper\data")
DEFAULT_DESTINATION = Path(__file__).resolve().parent / "source_file" / "supplier_data"
DEFAULT_SEARCH_DESTINATION = Path(__file__).resolve().parent / "source_file" / "search"


def copy_supplier_csvs(source: Path = DEFAULT_SOURCE, destination: Path = DEFAULT_DESTINATION) -> int:
    """Copy current ``base.csv`` and ``harvested.csv`` files for each supplier."""
    if not source.is_dir():
        raise FileNotFoundError(f"Supplier data folder does not exist: {source}")

    copied = 0
    for supplier_folder in sorted(path for path in source.iterdir() if path.is_dir()):
        for filename in ("base.csv", "harvested.csv"):
            source_file = supplier_folder / filename
            if not source_file.is_file():
                continue
            destination_file = destination / supplier_folder.name / filename
            destination_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, destination_file)
            copied += 1
    return copied


def copy_search_data(source: Path = DEFAULT_SOURCE, destination: Path = DEFAULT_SEARCH_DESTINATION) -> int:
    """Copy the scraper's complete search snapshot, including evidence files."""
    search_source = source / "search"
    if not search_source.is_dir():
        raise FileNotFoundError(f"Search data folder does not exist: {search_source}")

    copied = 0
    for path in search_source.rglob("*"):
        if not path.is_file():
            continue
        destination_file = destination / path.relative_to(search_source)
        destination_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination_file)
        copied += 1
    return copied


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _parse_value(key: str, value: str) -> object:
    if key in {"tiers", "warnings"} and value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    if key == "selected_by_current_filter" and value:
        return value.casefold() == "true"
    return value


def load_supplier_data(
    directory: Path = DEFAULT_DESTINATION,
) -> dict[str, dict[str, dict[str, object]]]:
    """Return ``{oomp_id: {supplier: supplier_record}}`` from local snapshots.

    Harvested values take precedence over the mapping CSV. Empty harvested
    fields do not erase a verified supplier part number or product URL.
    Monetary values remain strings to preserve their exact decimal precision.
    """
    by_part: dict[str, dict[str, dict[str, object]]] = {}
    if not directory.is_dir():
        return by_part

    for supplier_folder in sorted(path for path in directory.iterdir() if path.is_dir()):
        supplier_name = supplier_folder.name
        records: dict[str, dict[str, object]] = {}

        for row in _read_csv(supplier_folder / "base.csv"):
            oomp_id = (row.get("oomp_id") or "").strip()
            if not oomp_id:
                continue
            record: dict[str, object] = {"supplier": supplier_name}
            for key in ("supplier_id", "supplier_website"):
                value = (row.get(key) or "").strip()
                if value:
                    record[key] = value
            records[oomp_id] = record

        for row in _read_csv(supplier_folder / "harvested.csv"):
            oomp_id = (row.get("oomp_id") or "").strip()
            if not oomp_id:
                continue
            record = records.setdefault(oomp_id, {"supplier": supplier_name})
            for key, raw_value in row.items():
                if key == "oomp_id" or raw_value is None:
                    continue
                value = raw_value.strip()
                if value or key not in record:
                    record[key] = _parse_value(key, value)
            record.setdefault("supplier", supplier_name)

        for oomp_id, record in records.items():
            if "supplier_id" in record:
                record.setdefault("supplier_part_number", record["supplier_id"])
            by_part.setdefault(oomp_id, {})[supplier_name] = record

    return by_part


def load_search_data(
    directory: Path = DEFAULT_SEARCH_DESTINATION,
) -> dict[str, dict[str, dict[str, str]]]:
    """Return ``{oomp_id: {platform: search_record}}`` from the search snapshot."""
    by_part: dict[str, dict[str, dict[str, str]]] = {}
    for row in _read_csv(directory / "results.csv"):
        oomp_id = (row.get("oomp_id") or "").strip()
        platform = (row.get("platform") or "").strip()
        if not oomp_id or not platform:
            continue
        record = {key: (value or "").strip() for key, value in row.items() if key not in {"oomp_id", "platform"}}
        by_part.setdefault(oomp_id, {})[platform] = record
    return by_part


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Supplier scraper data folder")
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION, help="Local snapshot folder")
    parser.add_argument("--search-destination", type=Path, default=DEFAULT_SEARCH_DESTINATION, help="Local search snapshot folder")
    args = parser.parse_args()
    copied = copy_supplier_csvs(args.source, args.destination)
    search_copied = copy_search_data(args.source, args.search_destination)
    part_data = load_supplier_data(args.destination)
    supplier_count = sum(len(suppliers) for suppliers in part_data.values())
    search_data = load_search_data(args.search_destination)
    search_count = sum(len(platforms) for platforms in search_data.values())
    print(
        f"Copied {copied} supplier CSV files and {search_copied} search files; "
        f"loaded {supplier_count} supplier records for {len(part_data)} OOMP parts "
        f"and {search_count} search records for {len(search_data)} OOMP parts."
    )


if __name__ == "__main__":
    main()
