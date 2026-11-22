"""Tests for event sections, external types, empty returns, and source excerpts."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from mkdocstrings_handlers.luau._internal._models import ExternalType, Function, ReturnValue, is_absent_return
from mkdocstrings_handlers.luau._internal._moonwave import Library, Source, _read_snippet, format_lua_type, load_library
from mkdocstrings_handlers.luau._internal.config import LuauConfig
from mkdocstrings_handlers.luau._internal.handler import LuauHandler

if TYPE_CHECKING:
    from pathlib import Path

    from markdown import Markdown
    from mkdocstrings.plugin import MkdocstringsPlugin


def test_empty_parentheses_are_not_a_return() -> None:
    """`@return ()` means the function returns nothing."""
    assert is_absent_return("()")
    assert is_absent_return("( )")
    function = Function(
        name="OpenClose",
        path="BackpackScript.OpenClose",
        kind="function",
        description="Toggles whether the inventory is visible.",
        source=None,
        tags=(),
        external_types=(),
        realm=(),
        deprecated=None,
        since=None,
        private=False,
        unreleased=False,
        ignore=False,
        returns=(ReturnValue(description="", lua_type="()"),),
    )
    assert function.visible_returns == ()
    assert function.signature == "function OpenClose()"


def test_external_types_link_and_builtins_stay_visible() -> None:
    """`@external` links a type, and an unlinked builtin is still shown."""
    library = _library_with_externals()
    linked = format_lua_type("BindableEvent", library)
    assert 'href="https://example.com/BindableEvent"' in linked
    assert "BindableEvent" in linked
    builtin = format_lua_type("boolean", library)
    assert "boolean" in builtin
    assert "href=" not in builtin
    explicit = format_lua_type("boolean", library, external=[_external("boolean", "https://example.com/boolean")])
    assert 'href="https://example.com/boolean"' in explicit


def test_source_excerpt_covers_statement_and_assigned_function(tmp_path: Path) -> None:
    """Assignments resolve a same-file function, and calls keep every line."""
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    file_path = source_dir / "init.luau"
    file_path.write_text(
        "\n".join(
            [
                "local function openClose()",
                "\tif ready then -- Only continue if nothing is being dragged",
                "\t\tfor i = 1, 2 do",
                "\t\t\treturn -- end of the early exit",
                "\t\tend",
                "\tend",
                "end",
                "--[=[",
                "@function NotThis",
                "]=]",
                "",
                "BackpackScript.OpenClose = openClose -- Exposed",
                "",
                'BackpackScript.BackpackEmpty = Create("BindableEvent")({',
                '\tName = "BackpackEmpty",',
                "\tParent = script,",
                "})",
                "",
                "BackpackScript.IsHotbarVisible = false",
                "",
            ],
        ),
        encoding="utf-8",
    )
    lines = file_path.read_text(encoding="utf-8").splitlines()
    alias_line = lines.index("BackpackScript.OpenClose = openClose -- Exposed") + 1
    event_line = lines.index('BackpackScript.BackpackEmpty = Create("BindableEvent")({') + 1
    flag_line = lines.index("BackpackScript.IsHotbarVisible = false") + 1

    alias = _read_snippet(tmp_path, Source(line=alias_line, path="src/init.luau"), "function")
    assert alias is not None
    alias_text, alias_line_shown = alias
    assert alias_line_shown == lines.index("local function openClose()") + 1
    assert alias_text.startswith("local function openClose()")
    assert "return" in alias_text
    assert alias_text.rstrip().endswith("end")
    assert "BackpackScript.OpenClose" not in alias_text
    assert "NotThis" not in alias_text

    event = _read_snippet(tmp_path, Source(line=event_line, path="src/init.luau"), "property")
    assert event is not None
    event_text, event_line_shown = event
    assert event_line_shown == event_line
    assert 'Name = "BackpackEmpty"' in event_text
    assert event_text.rstrip().endswith("})")

    flag = _read_snippet(tmp_path, Source(line=flag_line, path="src/init.luau"), "property")
    assert flag == ("BackpackScript.IsHotbarVisible = false", flag_line)


def test_events_section_property_types_and_empty_return(
    plugin: MkdocstringsPlugin,
    ext_markdown: Markdown,
    tmp_path: Path,
) -> None:
    """Events leave Properties, types are linked, and `()` adds no return row."""
    payload: dict[str, Any] = {
        "name": "BackpackScript",
        "desc": "The backpack.",
        "external_types": [
            {"name": "BindableEvent", "url": "https://example.com/BindableEvent"},
            {"name": "boolean", "url": "https://example.com/boolean"},
        ],
        "functions": [
            {
                "name": "OpenClose",
                "desc": "Toggles whether the inventory is visible.",
                "function_type": "static",
                "params": [],
                "returns": [{"lua_type": "()", "desc": ""}],
            },
        ],
        "properties": [
            {"name": "IsOpen", "desc": "Returns true if the inventory is open.", "lua_type": "boolean"},
            {"name": "StateChanged", "desc": "Fires after the inventory is opened or closed.", "lua_type": "BindableEvent"},
            {"name": "Custom", "desc": "A tagged event.", "lua_type": "number", "tags": ["event"]},
        ],
        "types": [],
    }
    page = _render(plugin, ext_markdown, tmp_path, payload, options={"show_symbol_type_heading": True})
    properties = page.split('id="BackpackScript-properties"', maxsplit=1)[1].split(
        'id="BackpackScript-events"',
        maxsplit=1,
    )[0]
    events = page.split('id="BackpackScript-events"', maxsplit=1)[1].split(
        'id="BackpackScript-functions"',
        maxsplit=1,
    )[0]
    assert "IsOpen" in properties
    assert "StateChanged" not in properties
    assert "StateChanged" in events
    assert "Custom" in events
    assert 'href="https://example.com/BindableEvent"' in page
    assert 'href="https://example.com/boolean"' in page
    assert "Returns:" not in page
    assert "doc-symbol-event" in page

    flat = _render(plugin, ext_markdown, tmp_path, payload, options={"event_types": []})
    kept = flat.split('id="BackpackScript-properties"', maxsplit=1)[1].split(
        'id="BackpackScript-events"',
        maxsplit=1,
    )[0]
    assert "StateChanged" in kept
    assert "IsOpen" in kept


def _render(
    plugin: MkdocstringsPlugin,
    ext_markdown: Markdown,
    tmp_path: Path,
    payload: dict[str, Any],
    options: dict[str, object] | None = None,
) -> str:
    path = tmp_path / "api.json"
    path.write_text(json.dumps([payload]), encoding="utf-8")
    sample = plugin.handlers.get_handler("luau")
    handler = LuauHandler(
        config=LuauConfig.from_data(json=str(path), base=str(tmp_path)),
        base_dir=tmp_path,
        theme="material",
        custom_templates=None,
        mdx=sample.mdx,
        mdx_config=sample.mdx_config,
    )
    handler._update_env(ext_markdown, config=plugin.handlers._tool_config)
    final = handler.get_options(options or {})
    return handler.render(handler.collect("BackpackScript", final), final)


def _library_with_externals() -> Library:
    return load_library(
        [
            {
                "name": "BackpackScript",
                "desc": "",
                "external_types": [{"name": "BindableEvent", "url": "https://example.com/BindableEvent"}],
                "functions": [],
                "properties": [],
                "types": [],
            },
        ],
    )


def _external(name: str, url: str) -> ExternalType:
    return ExternalType(name=name, url=url)
