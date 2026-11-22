"""Configuration for the pytest test suite."""

from __future__ import annotations

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
    example_json = project / "docs" / "examples" / "api.json"
    conf = MkDocsConfig(config_file_path=str(project / "mkdocs.yml"))
    conf_dict: dict[str, Any] = {
        "site_name": "foo",
        "site_url": "https://example.org/",
        "site_dir": str(tmp_path),
        "docs_dir": str(project / "docs"),
        "theme": "material",
        "plugins": [
            "autorefs",
            {
                "mkdocstrings": {
                    "default_handler": "luau",
                    "handlers": {"luau": {"json": str(example_json)}},
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
