# mkdocstrings-luau

[![ci](https://github.com/ryanlua/mkdocstrings-luau/workflows/ci/badge.svg)](https://github.com/ryanlua/mkdocstrings-luau/actions?query=workflow%3Aci)
[![documentation](https://img.shields.io/badge/docs-mkdocs-708FCC.svg?style=flat)](https://ryanlua.github.io/mkdocstrings-luau/)
[![pypi version](https://img.shields.io/pypi/v/mkdocstrings-luau.svg)](https://pypi.org/project/mkdocstrings-luau/)
[![gitter](https://img.shields.io/badge/matrix-chat-4DB798.svg?style=flat)](https://app.gitter.im/#/room/#mkdocstrings-luau:gitter.im)

A Luau handler for mkdocstrings. It reads the JSON emitted by [Moonwave](https://github.com/evaera/moonwave)'s extractor and renders classes, functions, methods, properties, and types.

## Installation

```bash
pip install mkdocstrings-luau
```

Install the `moonwave-extractor` binary when you want MkDocs to extract sources during the build. You can also commit the JSON and point the handler at that file.

## Configuration

```yaml title="mkdocs.yml"
plugins:
- autorefs
- mkdocstrings:
    handlers:
      luau:
        extractor: moonwave-extractor
        paths:
        - src
        options:
          show_source: true
          signature_crossrefs: true
```

Or, with JSON you generated yourself (`moonwave-extractor extract src --base . > docs/api.json`):

```yaml title="mkdocs.yml"
plugins:
- mkdocstrings:
    handlers:
      luau:
        json: docs/api.json
```

In a page, with the handler selected globally or on the directive:

````md
::: Vector3
    handler: luau

::: Vector3.dot
::: Vector3:dot
````

`Vector3` renders the class and its visible members. `Vector3.dot` and `Vector3:dot` render that method. Moonwave links such as `[Vector3.new]` become autorefs, and every rendered object is registered in the site inventory (domain `luau`) so other pages can link to it.

Members marked `@private`, `@unreleased`, or `@ignore` are hidden on the class page until you opt in with `show_private`, `show_unreleased`, or `show_ignored`.

See the [usage guide](https://ryanlua.github.io/mkdocstrings-luau/usage/) for comment syntax and the full list of options. The repository's `docs/examples` directory is a small library rendered by this handler.

## Building this site

This repository's own documentation is built with MkDocs:

```bash
uv run mkdocs build
uv run mkdocs serve
```

The preview is served at <http://127.0.0.1:8000/mkdocstrings-luau/>. The rendered Luau sample is under `examples/`.


