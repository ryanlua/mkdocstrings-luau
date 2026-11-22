# General options

[](){ #option-extra }
## `extra`

- **:octicons-package-24: Type [`dict`][] :material-equal: `{}`{ title="default value" }**

The `extra` option lets you inject additional variables into the Jinja context used when rendering templates. You can then use this extra context in your overridden templates.

Local `extra` options will be merged into the global `extra` option:

```yaml title="in mkdocs.yml (global configuration)"
plugins:
- mkdocstrings:
    handlers:
      luau:
        options:
          extra:
            hello: world
```

```md title="in docs/some_page.md (local configuration)"
::: your_package.your_module.your_func
    options:
      extra:
        foo: bar
```

...will inject both `hello` and `foo` into the Jinja context when rendering `your_package.your_module.your_func`.

[](){ #option-show_source }
## `show_source`

- **:octicons-package-24: Type [`bool`][] :material-equal: `True`{ title="default value" }**

Show the `path:line` Moonwave recorded. When that file exists under [`base`][setting-base], the declaration is included: one line for properties and types, and the following block for functions.

[](){ #option-show_signature }
## `show_signature`

- **:octicons-package-24: Type [`bool`][] :material-equal: `True`{ title="default value" }**

Show a Luau signature. Methods use `:`, static functions use `.`, and a parameter documented as `name?` is rendered as an optional type.

[](){ #option-separate_signature }
## `separate_signature`

- **:octicons-package-24: Type [`bool`][] :material-equal: `False`{ title="default value" }**

Put the signature under the heading instead of inside it. The heading then shows the object name.

[](){ #option-signature_crossrefs }
## `signature_crossrefs`

- **:octicons-package-24: Type [`bool`][] :material-equal: `True`{ title="default value" }**

Link types in parameter, return, error, and field tables, and on the type line under each property. A type that names a documented object points at that object. A type declared with `@external` points at that URL, including builtins such as `boolean` and `string` when you declare them. Builtins without an `@external` entry stay as plain type text.

[](){ #option-show_labels }
## `show_labels`

- **:octicons-package-24: Type [`bool`][] :material-equal: `True`{ title="default value" }**

Show labels next to the heading: `deprecated`, `private`, `unreleased`, `ignored`, realms (`client`, `server`, `plugin`), custom `@tag` values, `static`, `yields`, and `readonly`.

[](){ #option-docstring_section_style }
## `docstring_section_style`

- **:octicons-package-24: Type [`str`][] :material-equal: `"table"`{ title="default value" }**

Render parameters, returns, errors, and fields as a `table` or a `list`.

Descriptions are Markdown, rendered with the same Markdown extensions as the rest of the site. `[Class.member]` and `[Class:method]` are Moonwave shortcut links and become cross-references. `Class.member` is also the anchor registered for autorefs.
