"""Tests for the different themes we claim to support."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from markdown import Markdown
    from mkdocstrings.plugin import MkdocstringsPlugin

    from mkdocstrings_handlers.luau._internal.handler import LuauHandler


@pytest.mark.parametrize(
    "plugin",
    [
        {"theme": "mkdocs"},
        {"theme": "readthedocs"},
        {"theme": {"name": "material"}},
    ],
    indirect=["plugin"],
)
@pytest.mark.parametrize(
    "identifier",
    [
        "Box",
        "Box.open",
        "Box.measure",
        "Box:measure",
        "Box.Flag",
        "Box.Changed",
        "Box.Kind",
    ],
)
def test_render_themes_templates_python(identifier: str, plugin: MkdocstringsPlugin, ext_markdown: Markdown) -> None:
    """Test rendering of a given theme's templates.

    Parameters:
        identifier: Parametrized identifier.
        plugin: Pytest fixture (see conftest.py).
        ext_markdown: Pytest fixture (see conftest.py).
    """
    handler = plugin.handlers.get_handler("luau")
    handler._update_env(ext_markdown, config=plugin.handlers._tool_config)
    options = handler.get_options({})
    data = handler.collect(identifier, options)
    handler.render(data, options)


def test_moonwave_page_covers_events_types_returns_and_source(handler: LuauHandler) -> None:
    """A class page loads JSON and renders the handler's main sections.

    Parameters:
        handler: Pytest fixture (see conftest.py).
    """
    options = handler.get_options({})
    box = handler.collect("Box", options)
    page = handler.render(box, options)
    properties = page.split('id="Box-properties"', maxsplit=1)[1].split('id="Box-events"', maxsplit=1)[0]
    events = page.split('id="Box-events"', maxsplit=1)[1].split('id="Box-types"', maxsplit=1)[0]
    opened = page.split('id="Box.open"', maxsplit=1)[1].split('id="Box.measure"', maxsplit=1)[0]
    open_fn = next(item for item in box.functions if item.name == "open")
    changed = next(item for item in box.properties if item.name == "Changed")

    assert 'id="Box.Flag"' in properties
    assert "Changed" not in properties
    assert 'id="Box.Changed"' in events
    assert 'id="Box.Kind"' in page
    assert "Type:" in page
    assert 'href="https://example.com/boolean"' in page
    assert 'href="https://example.com/BindableEvent"' in page
    assert "Returns:" not in opened
    assert open_fn.visible_returns == ()
    assert open_fn.source is not None
    assert open_fn.source.text is not None
    assert open_fn.source.text.startswith("local function open()")
    assert changed.source is not None
    assert changed.source.text is not None
    assert 'Name = "Changed"' in changed.source.text
    assert handler.get_aliases("Box.measure") == ("Box.measure", "Box:measure")
