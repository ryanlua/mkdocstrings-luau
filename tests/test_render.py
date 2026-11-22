"""Tests for rendering Luau objects and inventory aliases."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

import pytest
from mkdocstrings import CollectionError, Inventory

from mkdocstrings_handlers.luau._internal.config import LuauConfig
from mkdocstrings_handlers.luau._internal.handler import LuauHandler

if TYPE_CHECKING:
    from pathlib import Path


def test_class_page_renders_members_signatures_and_links(handler: LuauHandler) -> None:
    """A class page includes public members and skips hidden ones."""
    options = handler.get_options({"show_symbol_type_heading": True})
    page = handler.render(handler.collect("Vector3", options), options)

    assert 'id="Vector3"' in page
    assert "doc-symbol-class" in page
    assert 'id="Vector3.new"' in page
    assert "Vector3.new" in page
    assert "z?" in page
    assert 'id="Vector3.dot"' in page
    assert "X component" in page
    assert "invalid component" in page
    assert "Deprecated in v2.0.0" in page
    assert 'id="Vector3.UnitVector"' in page
    assert 'id="Vector3.Options"' in page
    assert "Uniform scale" in page
    assert 'identifier="Vector3.new"' in page
    assert 'identifier="Vector3.UnitVector"' in page
    assert "docs/examples/src/Vector3.luau:10" in page
    assert 'id="Vector3.Y"' not in page
    assert 'id="Vector3.W"' not in page
    assert 'id="Vector3._secret"' not in page
    assert handler.get_aliases("Vector3.dot") == ("Vector3.dot", "Vector3:dot")


def test_hidden_members_can_be_selected(handler: LuauHandler) -> None:
    """Visibility flags and member filters change what a class page includes."""
    shown = handler.get_options({"show_private": True, "show_unreleased": True, "show_ignored": True})
    page = handler.render(handler.collect("Vector3", shown), shown)
    assert 'id="Vector3.Y"' in page
    assert 'id="Vector3.W"' in page
    assert 'id="Vector3._secret"' in page

    only_dot = handler.get_options({"members": ["dot"], "summary": False, "show_category_heading": False})
    page = handler.render(handler.collect("Vector3", only_dot), only_dot)
    assert 'id="Vector3.dot"' in page
    assert 'id="Vector3.new"' not in page

    listed = handler.get_options({"docstring_section_style": "list", "heading_level": 4})
    page = handler.render(handler.collect("Vector3.new", listed), listed)
    assert "<h4" in page
    assert "<ul>" in page
    assert "X component" in page


def test_external_type_and_missing_identifier(handler: LuauHandler) -> None:
    """External types become links, and unknown identifiers fail collection."""
    options = handler.get_options({})
    page = handler.render(handler.collect("Greeter", options), options)
    assert "roblox-lua-promise" in page
    assert "empty name" in page

    with pytest.raises(CollectionError, match="Could not find"):
        handler.collect("NotAClass", options)


def test_inventory_round_trip(tmp_path: Path) -> None:
    """Configured inventories are parsed as Sphinx objects.inv files."""
    inventory = Inventory(project="demo", version="1")
    inventory.register("Vector3", "luau", "class", "api/#Vector3")
    inventory.register("skip", "py", "class", "api/#skip")
    loaded = list(
        LuauHandler.load_inventory(BytesIO(inventory.format_sphinx()), "https://example.com/objects.inv"),
    )
    assert loaded == [("Vector3", "https://example.com/api/#Vector3")]

    handler = LuauHandler(
        config=LuauConfig.from_data(inventories=[{"url": "https://example.com/objects.inv", "domains": ["luau"]}]),
        base_dir=tmp_path,
        theme="material",
        custom_templates=None,
        mdx=[],
        mdx_config={},
    )
    urls = handler.get_inventory_urls()
    assert urls == [("https://example.com/objects.inv", {"base_url": None, "domains": ["luau"]})]


def test_handler_runs_the_extractor(tmp_path: Path) -> None:
    """A configured extractor binary is used when no JSON file is set."""
    source = tmp_path / "src"
    source.mkdir()
    script = tmp_path / "moonwave-extractor"
    payload = json_payload()
    script.write_text(f"#!/bin/sh\nprintf '%s' '{payload}'\n", encoding="utf-8")
    script.chmod(0o755)
    handler = LuauHandler(
        config=LuauConfig.from_data(extractor=str(script), paths=[str(source)]),
        base_dir=tmp_path,
        theme="material",
        custom_templates=None,
        mdx=[],
        mdx_config={},
    )
    item = handler.collect("Only", handler.get_options({}))
    assert item.kind == "class"
    assert item.name == "Only"


def json_payload() -> str:
    """Return a one-class Moonwave document."""
    return (
        '[{"name":"Only","desc":"Just one class.","functions":[],'
        '"properties":[],"types":[],"source":{"line":1,"path":"src/only.luau"}}]'
    )
