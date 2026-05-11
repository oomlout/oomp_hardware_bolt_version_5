"""
test_generate_structure.py
Checks that every option dict returned by each generate() has the right keys and value formats.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from working_oomp_populate_countersunk import generate as gen_countersunk
from working_oomp_populate_countersunk_pozi import generate as gen_countersunk_pozi
from working_oomp_populate_countersunk_philips import generate as gen_countersunk_philips
from working_oomp_populate_socket_cap import generate as gen_socket_cap
from working_oomp_populate_socket_cap_low_head import generate as gen_socket_cap_low_head
from working_oomp_populate_socket_cap_low_head_ultra import generate as gen_socket_cap_low_head_ultra
from working_oomp_populate_flat_head import generate as gen_flat_head
from working_oomp_populate_button_head import generate as gen_button_head
from working_oomp_populate_grub import generate as gen_grub
from working_oomp_populate_machine_screw import generate as gen_machine_screw
from working_oomp_populate_self_tapping import generate as gen_self_tapping
from working_oomp_populate_thread_forming import generate as gen_thread_forming
from working_oomp_populate_wood import generate as gen_wood

ALL_GENERATORS = {
    "countersunk": gen_countersunk,
    "countersunk_pozi": gen_countersunk_pozi,
    "countersunk_philips": gen_countersunk_philips,
    "socket_cap": gen_socket_cap,
    "socket_cap_low_head": gen_socket_cap_low_head,
    "socket_cap_low_head_ultra": gen_socket_cap_low_head_ultra,
    "flat_head": gen_flat_head,
    "button_head": gen_button_head,
    "grub": gen_grub,
    "machine_screw": gen_machine_screw,
    "self_tapping": gen_self_tapping,
    "thread_forming": gen_thread_forming,
    "wood": gen_wood,
}

REQUIRED_KEYS = ["taxonomy_3", "taxonomy_4", "taxonomy_6", "taxonomy_7"]


@pytest.mark.parametrize("name,gen", ALL_GENERATORS.items())
def test_non_empty(name, gen):
    options = gen()
    assert len(options) > 0, f"{name}: generate() returned empty list"


@pytest.mark.parametrize("name,gen", ALL_GENERATORS.items())
def test_required_keys(name, gen):
    options = gen()
    for i, opt in enumerate(options):
        for key in REQUIRED_KEYS:
            assert key in opt, f"{name}[{i}]: missing key '{key}'"


@pytest.mark.parametrize("name,gen", ALL_GENERATORS.items())
def test_taxonomy_6_ends_with_diameter(name, gen):
    options = gen()
    for i, opt in enumerate(options):
        assert opt["taxonomy_6"].endswith("_diameter"), (
            f"{name}[{i}]: taxonomy_6='{opt['taxonomy_6']}' does not end with '_diameter'"
        )


@pytest.mark.parametrize("name,gen", ALL_GENERATORS.items())
def test_taxonomy_7_ends_with_mm_length(name, gen):
    options = gen()
    for i, opt in enumerate(options):
        assert opt["taxonomy_7"].endswith("_mm_length"), (
            f"{name}[{i}]: taxonomy_7='{opt['taxonomy_7']}' does not end with '_mm_length'"
        )


@pytest.mark.parametrize("name,gen", ALL_GENERATORS.items())
def test_no_duplicates_within_type(name, gen):
    options = gen()
    # Build a minimal folder-name key from the taxonomy fields present
    seen = set()
    for i, opt in enumerate(options):
        key = "_".join([
            opt.get("taxonomy_3", ""),
            opt.get("taxonomy_4", ""),
            opt.get("taxonomy_5", ""),
            opt.get("taxonomy_6", ""),
            opt.get("taxonomy_7", ""),
        ])
        assert key not in seen, f"{name}[{i}]: duplicate entry '{key}'"
        seen.add(key)
