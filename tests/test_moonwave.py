"""Tests for Moonwave JSON loading and identifier resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from mkdocstrings import CollectionError

from mkdocstrings_handlers.luau._internal._models import Function, Property, TypeAlias
from mkdocstrings_handlers.luau._internal._moonwave import (
    format_lua_type,
    linkify_markdown,
    load_library,
    read_json,
    run_extractor,
)

ROOT = Path(__file__).parent.parent
EXAMPLE_JSON = ROOT / "docs" / "examples" / "api.json"


def test_example_json_matches_the_sample_library() -> None:
    """The committed fixture is the extractor output for the sample library."""
    library = load_library(read_json(EXAMPLE_JSON), base_dir=ROOT)
    vector = library.resolve("Vector3")
    assert vector.kind == "class"
    assert vector.tags == ("math",)
    assert vector.since == "v1.0.0"
    assert vector.source is not None
    assert vector.source.path == "docs/examples/src/Vector3.luau"
    assert vector.source.text is not None
    assert "local Vector3" in vector.source.text

    constructor = library.resolve("Vector3.new")
    assert isinstance(constructor, Function)
    assert constructor.kind == "function"
    assert constructor.function_type == "static"
    assert [parameter.name for parameter in constructor.parameters] == ["x", "y", "z?"]
    assert constructor.parameters[2].optional is True
    assert "z: number?" in constructor.signature
    assert constructor.errors[0].description == "A component was not a number"
    assert constructor.source is not None
    assert constructor.source.text is not None
    assert "function Vector3.new" in constructor.source.text

    dot = library.resolve("Vector3:dot")
    assert isinstance(dot, Function)
    assert dot is library.resolve("Vector3.dot")
    assert dot.kind == "method"
    assert dot.yields is True
    assert dot.realm == ("client", "server")
    assert dot.signature == "function Vector3:dot(other: Vector3): number"

    magnitude = library.resolve("Vector3.magnitude")
    assert isinstance(magnitude, Function)
    assert magnitude.deprecated is not None
    assert magnitude.deprecated.version == "v2.0.0"

    hidden = library.resolve("Vector3.Y")
    assert isinstance(hidden, Property)
    assert hidden.private is True
    assert library.resolve("Vector3.W").unreleased is True
    assert library.resolve("Vector3._secret").ignore is True
    component = library.resolve("Vector3.X")
    assert isinstance(component, Property)
    assert component.readonly is True

    unit = library.resolve("UnitVector")
    assert isinstance(unit, TypeAlias)
    assert unit.path == "Vector3.UnitVector"
    assert unit.lua_type == "{ number }"
    options = library.resolve("Vector3.Options")
    assert isinstance(options, TypeAlias)
    assert [field.name for field in options.fields] == ["Scale", "Unit"]

    greet = library.resolve("Greeter.greet")
    assert greet.external_types[0].name == "Promise"
    assert "Promise" in library.external_types
    assert 'identifier="Vector3.new"' in linkify_markdown(vector.description, library)
    assert 'href="https://eryn.io/roblox-lua-promise/api/Promise"' in linkify_markdown(
        library.resolve("Greeter").description,
        library,
    )
    rendered = format_lua_type("Vector3 | Promise", library, greet.external_types)
    assert 'identifier="Vector3"' in rendered
    assert "roblox-lua-promise" in rendered


def test_duplicate_member_is_rejected() -> None:
    """Two members cannot share one identifier."""
    payload = [
        {
            "name": "Box",
            "desc": "",
            "functions": [{"name": "open", "desc": "", "function_type": "static"}],
            "properties": [{"name": "open", "desc": "", "lua_type": "boolean"}],
            "types": [],
        },
    ]
    with pytest.raises(CollectionError, match="Duplicate"):
        load_library(payload)


def test_read_json_rejects_invalid_files(tmp_path: Path) -> None:
    """JSON that is not a class array fails collection."""
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(CollectionError, match="Invalid Moonwave JSON"):
        read_json(path)
    path.write_text("1", encoding="utf-8")
    with pytest.raises(CollectionError, match="array of class objects"):
        read_json(path)


def test_extractor_merges_paths_and_reports_failures(tmp_path: Path) -> None:
    """The extractor helper runs the binary once per path and surfaces errors."""
    first = [{"name": "A", "desc": "a", "functions": [], "properties": [], "types": []}]
    second = [{"name": "A", "desc": "a", "functions": [{"name": "go", "desc": ""}], "properties": [], "types": []}]
    script = tmp_path / "moonwave-extractor"
    script.write_text(
        "#!/bin/sh\n"
        'case "$2" in\n'
        "  *one*) printf '%s' '" + json.dumps(first) + "' ;;\n"
        "  *two*) printf '%s' '" + json.dumps(second) + "' ;;\n"
        "  *) echo boom >&2; exit 1 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    one = tmp_path / "one"
    two = tmp_path / "two"
    one.mkdir()
    two.mkdir()
    payload = run_extractor(str(script), [one, two], base=tmp_path)
    library = load_library(payload)
    assert library.resolve("A.go").kind == "function"

    with pytest.raises(CollectionError, match="failed"):
        run_extractor(str(script), [tmp_path / "missing"], base=tmp_path)
