"""Configuration for the pytest test suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from markdown.core import Markdown
from mkdocs.config.defaults import MkDocsConfig

if TYPE_CHECKING:
    from collections.abc import Iterator

    from mkdocstrings.plugin import MkdocstringsPlugin

    from mkdocstrings_handlers.luau._internal.handler import LuauHandler


@pytest.fixture(name="mkdocs_conf")
def fixture_mkdocs_conf(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[MkDocsConfig]:
    """Yield a MkDocs configuration object.

    Parameters:
        request: Pytest fixture.
        tmp_path: Pytest fixture.

    Yields:
        MkDocs config.
    """
    while hasattr(request, "_parent_request") and hasattr(request._parent_request, "_parent_request"):
        request = request._parent_request

    project = Path(__file__).parent.parent
    _write_fixture(tmp_path)
    conf = MkDocsConfig(config_file_path=str(project / "mkdocs.yml"))
    conf_dict: dict[str, Any] = {
        "site_name": "foo",
        "site_url": "https://example.org/",
        "site_dir": str(tmp_path / "site"),
        "docs_dir": str(project / "docs"),
        "theme": "material",
        "plugins": [
            "autorefs",
            {
                "mkdocstrings": {
                    "default_handler": "luau",
                    "handlers": {"luau": {"json": str(tmp_path / "api.json"), "base": str(tmp_path)}},
                },
            },
        ],
        **getattr(request, "param", {}),
    }

    conf.load_dict(conf_dict)
    assert conf.validate() == ([], [])

    conf.markdown_extensions.insert(0, "toc")  # Guaranteed to be added by MkDocs.

    configured = conf.plugins["mkdocstrings"].on_config(conf)
    assert configured is not None
    conf = configured
    configured = conf.plugins["autorefs"].on_config(conf)
    assert configured is not None
    conf = configured
    yield conf
    conf.plugins["mkdocstrings"].on_post_build(config=conf)


@pytest.fixture(name="plugin")
def fixture_plugin(mkdocs_conf: MkDocsConfig) -> MkdocstringsPlugin:
    """Return a plugin instance.

    Parameters:
        mkdocs_conf: Pytest fixture (see conftest.py).

    Returns:
        mkdocstrings plugin instance.
    """
    return mkdocs_conf.plugins["mkdocstrings"]


@pytest.fixture(name="ext_markdown")
def fixture_ext_markdown(mkdocs_conf: MkDocsConfig) -> Markdown:
    """Return a Markdown instance with MkdocstringsExtension.

    Parameters:
        mkdocs_conf: Pytest fixture (see conftest.py).

    Returns:
        A Markdown instance.
    """
    return Markdown(extensions=list(mkdocs_conf.markdown_extensions), extension_configs=dict(mkdocs_conf.mdx_configs))


@pytest.fixture(name="handler")
def fixture_handler(plugin: MkdocstringsPlugin, ext_markdown: Markdown) -> LuauHandler:
    """Return a handler instance.

    Parameters:
        plugin: Pytest fixture (see conftest.py).

    Returns:
        A handler instance.
    """
    handler = plugin.handlers.get_handler("luau")
    handler._update_env(ext_markdown, config=plugin.handlers._tool_config)
    return handler


def _write_fixture(tmp_path: Path) -> None:
    """Write the Moonwave JSON and source file the handler tests load."""
    source = tmp_path / "src"
    source.mkdir()
    lines = [
        "-- box",
        "local function open()",
        "\treturn",
        "end",
        'Box.Changed = Create("BindableEvent")({',
        '\tName = "Changed",',
        "})",
        "Box.open = open",
        "Box.Flag = false",
    ]
    (source / "init.luau").write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload = [
        {
            "name": "Box",
            "desc": "A box. Open it with [Box.open].",
            "external_types": [
                {"name": "BindableEvent", "url": "https://example.com/BindableEvent"},
                {"name": "boolean", "url": "https://example.com/boolean"},
            ],
            "source": {"line": 1, "path": "src/init.luau"},
            "functions": [
                {
                    "name": "open",
                    "desc": "Opens the box.",
                    "function_type": "static",
                    "params": [{"name": "x", "desc": "Width", "lua_type": "number"}],
                    "returns": [{"lua_type": "()", "desc": ""}],
                    "source": {"line": lines.index("Box.open = open") + 1, "path": "src/init.luau"},
                },
                {
                    "name": "measure",
                    "desc": "Measures the box.",
                    "function_type": "method",
                    "params": [],
                    "returns": [{"lua_type": "number", "desc": "The size"}],
                    "source": {"line": 1, "path": "src/init.luau"},
                },
            ],
            "properties": [
                {
                    "name": "Flag",
                    "desc": "Whether it is open.",
                    "lua_type": "boolean",
                    "source": {"line": lines.index("Box.Flag = false") + 1, "path": "src/init.luau"},
                },
                {
                    "name": "Changed",
                    "desc": "Fires when it opens.",
                    "lua_type": "BindableEvent",
                    "source": {
                        "line": lines.index('Box.Changed = Create("BindableEvent")({') + 1,
                        "path": "src/init.luau",
                    },
                },
            ],
            "types": [
                {
                    "name": "Kind",
                    "desc": "A kind of box.",
                    "lua_type": "string",
                    "source": {"line": 1, "path": "src/init.luau"},
                },
            ],
        },
    ]
    (tmp_path / "api.json").write_text(json.dumps(payload), encoding="utf-8")
