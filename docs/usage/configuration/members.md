# Members options

These options control which members of a class are rendered. Asking for a member directly, as in `::: Vector3.Y`, still collects that member even when it would be hidden on the class page.

[](){ #option-show_category_heading }
## `show_category_heading`

- **:octicons-package-24: Type [`bool`][] :material-equal: `True`{ title="default value" }**

Show a heading for each non-empty group: Properties, Events, Types, Functions, and Methods.

[](){ #option-event_types }
## `event_types`

- **:octicons-package-24: Type [`list`][][`str`][] :material-equal: `["BindableEvent", "RBXScriptSignal", "Signal"]`{ title="default value" }**

Moonwave does not have an `@event` tag. Properties are rendered under **Events** when their type contains one of these names, or when the property has a custom `@tag event`. An empty list turns off the type match; `@tag event` still opens an Events section.

```yaml title="mkdocs.yml"
plugins:
- mkdocstrings:
    handlers:
      luau:
        options:
          event_types:
          - BindableEvent
          - RBXScriptSignal
```

[](){ #option-summary }
## `summary`

- **:octicons-package-24: Type [`bool`][] :material-equal: `True`{ title="default value" }**

Show a summary table of the visible members before their full documentation.

[](){ #option-show_private }
## `show_private`

- **:octicons-package-24: Type [`bool`][] :material-equal: `False`{ title="default value" }**

Include members marked with Moonwave's `@private` tag.

[](){ #option-show_unreleased }
## `show_unreleased`

- **:octicons-package-24: Type [`bool`][] :material-equal: `False`{ title="default value" }**

Include members marked with `@unreleased`.

[](){ #option-show_ignored }
## `show_ignored`

- **:octicons-package-24: Type [`bool`][] :material-equal: `False`{ title="default value" }**

Include members marked with `@ignore`.

[](){ #option-members }
## `members`

- **:octicons-package-24: Type [`list`][][`str`][] | `None` :material-equal: `None`{ title="default value" }**

Names of members to render. `None` or `true` means every member that passes the visibility flags and [`filters`][option-filters]. `false` or `[]` renders none. A string is treated as a one-item list.

```md
::: Vector3
    options:
      members:
      - new
      - dot
```

[](){ #option-filters }
## `filters`

- **:octicons-package-24: Type [`list`][][`str`][] :material-equal: `[]`{ title="default value" }**

Regular expressions matched against member names. A pattern prefixed with `!` excludes matches. Later patterns win, which is the same rule the Python handler uses.

```yaml title="mkdocs.yml"
plugins:
- mkdocstrings:
    handlers:
      luau:
        options:
          filters:
          - "!^_"
```

[](){ #option-members_order }
## `members_order`

- **:octicons-package-24: Type [`str`][] :material-equal: `"source"`{ title="default value" }**

`source` keeps Moonwave's source order (line number, then name). `alphabetical` sorts by name.
