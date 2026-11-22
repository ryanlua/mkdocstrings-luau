# Usage

Document Luau with Moonwave comments, then let mkdocstrings render them.

## Install

```bash
pip install mkdocstrings-luau
```

You also need the [Moonwave extractor](https://github.com/evaera/moonwave) when the handler runs it during the build. `moonwave-extractor` is a Rust binary. If you would rather not ship it in CI, run it yourself and point the handler at the JSON file.

## Configure MkDocs

```yaml title="mkdocs.yml"
site_name: My Luau library
theme:
  name: material

plugins:
- search
- autorefs
- mkdocstrings:
    handlers:
      luau:
        extractor: moonwave-extractor
        paths:
        - src
        options:
          show_source: true
          show_symbol_type_heading: true
          signature_crossrefs: true
```

`paths` are files or directories of `.lua` / `.luau` sources. They are passed to `moonwave-extractor extract`. Set `json` instead when the JSON already exists:

```yaml title="mkdocs.yml"
plugins:
- mkdocstrings:
    handlers:
      luau:
        json: docs/api.json
```

`json` wins when both are set. Paths inside the JSON are relative to `base` (the extractor's `--base`), which defaults to the directory that contains `mkdocs.yml`.

## Document a class

Moonwave comments use `--[=[` blocks (or `---` lines). The extractor groups functions, properties, and types under a class.

```luau title="src/Vector3.luau"
--[=[
    @class Vector3

    A three-component vector. Create one with [Vector3.new].
]=]
local Vector3 = {}

--[=[
    @param x number -- X component
    @param y number -- Y component
    @param z? number -- Optional Z
    @return Vector3
]=]
function Vector3.new(x: number, y: number, z: number?): Vector3
    return setmetatable({ X = x, Y = y, Z = z or 0 }, Vector3)
end

--[=[
    @param other Vector3 -- The other vector
    @return number
]=]
function Vector3:dot(other: Vector3): number
    return self.X * other.X + self.Y * other.Y + (self.Z or 0) * (other.Z or 0)
end
```

In a Markdown page, with `handler: luau` selected globally or on the directive:

```md
::: Vector3

::: Vector3.dot

::: Vector3:dot
```

`Class.member` is the canonical identifier. Methods can also be written `Class:method`. `[Vector3.new]` inside a Moonwave description becomes a cross-reference when that object is rendered. `@external Promise https://...` links that type name to the URL.

See the [example](../examples/index.md) rendered from a small library, and the [configuration reference](configuration/index.md) for every option.

## Not handled yet

Moonwave's extractor does the parsing. This handler does not read Luau itself, and it does not invent features Moonwave's JSON does not carry:

- `@link` and `@enum` are unimplemented in Moonwave, so they never appear in the JSON.
- There is no class inheritance. `@class` does not record a base class.
- Roblox engine types (such as `Instance` or `Player`) are not linked unless you document them or declare them with `@external`.
- Parameters have no default values. Returns have a type and a description, not a name.
- Source excerpts are the declaration line for properties and types, and the following block for functions, when the file from `source.path` can be read. The JSON itself only includes the path and line.
- Templates are written for the Material theme. MkDocs and Read the Docs themes fall back to those templates.
- If the same class is extracted from more than one path, members are concatenated. Two members with the same name are an error.
