# Sources

These settings live on the handler itself, next to `options`, because they describe where the documentation comes from.

[](){ #setting-extractor }
## `extractor`

- **:octicons-package-24: Type [`str`][] :material-equal: `"moonwave-extractor"`{ title="default value" }**

Path or command name of the Moonwave extractor binary. The handler runs `extractor extract <path> --base <base>` for each entry in [`paths`][setting-paths].

```yaml title="mkdocs.yml"
plugins:
- mkdocstrings:
    handlers:
      luau:
        extractor: moonwave-extractor
```

[](){ #setting-paths }
## `paths`

- **:octicons-package-24: Type [`list`][][`str`][] :material-equal: `[]`{ title="default value" }**

Luau files or directories to extract. Directories are walked for `.lua` and `.luau` files by Moonwave. Relative paths are resolved from the directory that contains `mkdocs.yml`.

Ignored when [`json`][setting-json] is set.

[](){ #setting-json }
## `json`

- **:octicons-package-24: Type [`str`][] :material-equal: `""`{ title="default value" }**

Path to a JSON file already produced by `moonwave-extractor`. When this is non-empty, the extractor is not run. The file must be an array of class objects (a single class object is accepted too).

```yaml title="mkdocs.yml"
plugins:
- mkdocstrings:
    handlers:
      luau:
        json: docs/api.json
```

[](){ #setting-base }
## `base`

- **:octicons-package-24: Type [`str`][] :material-equal: `""`{ title="default value" }**

Directory passed as `--base`. Source paths in the JSON are relative to it, and the handler reads those files from there when [`show_source`][option-show_source] can show the declaration. An empty value means the directory that contains `mkdocs.yml`.

[](){ #setting-inventories }
## `inventories`

- **:octicons-package-24: Type [`list`][] :material-equal: `[]`{ title="default value" }**

Sphinx `objects.inv` files to download so cross-references can point at objects rendered by another site. Each entry is a URL, or a mapping with `url`, optional `base_url`, and optional `domains` (default `["luau"]`).

```yaml title="mkdocs.yml"
plugins:
- mkdocstrings:
    handlers:
      luau:
        inventories:
        - https://example.com/objects.inv
        - url: https://example.com/objects.inv
          base_url: https://example.com/
          domains: [luau]
```

Objects rendered by this handler are written to this site's own inventory with domain `luau` and roles `class`, `function`, `method`, `property`, and `type`. Method headings also register the `Class:method` alias.
