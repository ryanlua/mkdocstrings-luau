<!-- --8<-- [start:header] -->

<h1 align="center">mkdocstrings-luau</h1>

<p align="center">A Luau handler for <a href="https://github.com/mkdocstrings/mkdocstrings"><i>mkdocstrings</i></a>.</p>

<!-- --8<-- [end:header] -->

[![ci](https://github.com/ryanlua/mkdocstrings-luau/actions/workflows/ci.yml/badge.svg)](https://github.com/ryanlua/mkdocstrings-luau/actions/workflows/ci.yml)
[![documentation](https://img.shields.io/badge/docs-mkdocs-708FCC.svg?style=flat)](https://ryanlua.github.io/mkdocstrings-luau/)
[![pypi version](https://img.shields.io/pypi/v/mkdocstrings-luau.svg)](https://pypi.org/project/mkdocstrings-luau/)

---

<img src="docs/logo.svg" width="100%">

A Luau handler for mkdocstrings.

<!-- --8<-- [start:install] -->

## Installation

```bash
pip install mkdocstrings-luau
```

<!-- --8<-- [end:install] -->

<!-- --8<-- [start:footer] -->

## Features

- **Data collection from Moonwave comments:** collection of the object-tree and docstrings is done thanks to
  [Moonwave](https://github.com/evaera/moonwave) (`moonwave-extractor`), or from a prebuilt Moonwave JSON file.

- **Support for Luau type annotations:** parameter and return types from Moonwave tags and Luau signatures are
  rendered in the docs. With cross-references enabled, types that name documented objects become links.
  See [how to load inventories](https://mkdocstrings.github.io/usage/#cross-references-to-other-projects-inventories)
  to link across projects.

- **Class-scoped documentation:** inject a class with `::: Class` (or a member with `::: Class.member` /
  `::: Class:method`) and get its full API—properties, events, types, functions, and methods—without documenting
  each member separately.

- **Moonwave docstring support:** `--[=[` blocks or `---` lines with tags such as `@class`, `@param`, `@return`,
  `@error`, `@prop`, `@type` / `@interface`, `@deprecated`, `@since`, and more.
  See [Moonwave's documentation](https://eryn.io/moonwave/docs/intro) on comment syntax.

- **Rich member metadata:** labels for deprecated, private, unreleased, static, yields, readonly, realms, and
  custom tags. `@deprecated` is rendered as a [warning admonition](https://squidfunk.github.io/mkdocs-material/reference/admonitions/).

- **Every object has a TOC entry:** we render a heading for each object, so *MkDocs* picks them into the Table
  of Contents (especially nice with the Material theme). Cross-reference objects with the classic Markdown syntax:
  `[this object][Class.member]` or Moonwave-style `[Class:method]`.

- **Source code display:** *mkdocstrings* can add a collapsible section with the highlighted declaration source
  for the Luau object.

<!-- --8<-- [end:footer] -->