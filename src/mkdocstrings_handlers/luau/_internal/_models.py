# Data collected from Moonwave JSON.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(eq=False)
class Source:
    """File location of a documented declaration."""

    line: int
    """1-based line number reported by Moonwave."""

    path: str
    """Path relative to the extractor base directory."""

    text: str | None = None
    """Source excerpt, when the file is available on disk."""

    text_line: int | None = None
    """1-based line where `text` starts. Differs from `line` when an assignment resolves to a function."""

    @property
    def display_line(self) -> int:
        """Return the line number the excerpt should be numbered from."""
        return self.line if self.text_line is None else self.text_line

    @property
    def label(self) -> str:
        """Return `path:line` for the excerpt."""
        return f"{self.path}:{self.display_line}"


@dataclass(eq=False)
class Deprecated:
    """A Moonwave `@deprecated` tag."""

    version: str | None = None
    """Version in which the object was deprecated."""

    description: str | None = None
    """Why the object was deprecated."""


@dataclass(eq=False)
class ExternalType:
    """A Moonwave `@external` tag."""

    name: str
    """Type name used in signatures."""

    url: str
    """Documentation URL for that type."""


@dataclass(eq=False)
class Parameter:
    """A function parameter from `@param` or a Luau annotation."""

    name: str
    """Parameter name. A trailing `?` marks it optional."""

    description: str
    """Parameter description. May be empty."""

    lua_type: str
    """Luau type. May be empty when Moonwave could not infer one."""

    @property
    def optional(self) -> bool:
        """Whether Moonwave recorded the parameter name with a trailing `?`."""
        return self.name.endswith("?")

    @property
    def display_name(self) -> str:
        """Parameter name without the optional marker."""
        return self.name[:-1] if self.optional else self.name


@dataclass(eq=False)
class ReturnValue:
    """A `@return` entry."""

    description: str
    """Return description. May be empty."""

    lua_type: str
    """Luau type of the returned value."""


@dataclass(eq=False)
class ErrorValue:
    """An `@error` entry."""

    lua_type: str
    """Error identifier or string literal."""

    description: str
    """When this error is raised."""


@dataclass(eq=False)
class FieldInfo:
    """A field on a Moonwave `@interface`."""

    name: str
    """Field name, without the leading dot."""

    lua_type: str
    """Luau type of the field."""

    description: str
    """Field description. May be empty."""


def _common_labels(
    *,
    deprecated: Deprecated | None,
    private: bool,
    unreleased: bool,
    ignore: bool,
    realm: tuple[str, ...],
    tags: tuple[str, ...],
) -> list[str]:
    labels: list[str] = []
    if deprecated is not None:
        labels.append("deprecated")
    if private:
        labels.append("private")
    if unreleased:
        labels.append("unreleased")
    if ignore:
        labels.append("ignored")
    labels.extend(realm)
    labels.extend(tags)
    return labels


@dataclass(eq=False)
class DocItem:
    """Shared fields of every documented Luau object."""

    name: str
    """Short name."""

    path: str
    """Canonical identifier, such as `Vector3` or `Vector3.dot`."""

    kind: str
    """One of `class`, `function`, `method`, `property`, or `type`."""

    description: str
    """Markdown description."""

    source: Source | None
    """Where the declaration lives."""

    tags: tuple[str, ...]
    """Custom `@tag` values."""

    external_types: tuple[ExternalType, ...]
    """`@external` types declared on this object."""

    realm: tuple[str, ...]
    """Lowercased realm names: client, server, plugin."""

    deprecated: Deprecated | None
    """Deprecation metadata, when `@deprecated` is present."""

    since: str | None
    """`@since` version."""

    private: bool
    """Whether `@private` was set."""

    unreleased: bool
    """Whether `@unreleased` was set."""

    ignore: bool
    """Whether `@ignore` was set."""

    parent: Class | None = field(default=None, repr=False)
    """Owning class, for members."""

    @property
    def labels(self) -> list[str]:
        """Labels rendered next to the heading."""
        return _common_labels(
            deprecated=self.deprecated,
            private=self.private,
            unreleased=self.unreleased,
            ignore=self.ignore,
            realm=self.realm,
            tags=self.tags,
        )


def _format_parameter(parameter: Parameter) -> str:
    name = parameter.display_name
    if parameter.name == "...":
        name = "..."
    if not parameter.lua_type:
        return parameter.name
    lua_type = parameter.lua_type
    if parameter.optional and not lua_type.endswith("?"):
        lua_type = f"{lua_type}?"
    return f"{name}: {lua_type}"


def is_absent_return(lua_type: str) -> bool:
    """Whether a Moonwave return type means "no value".

    `@return ()` is how callers record an empty return list. It should not become a row.

    Parameters:
        lua_type: Return type text from Moonwave.

    Returns:
        True for `()` and whitespace-only variants of it.
    """
    compact = "".join(lua_type.split())
    return compact == "()"


def _format_returns(returns: tuple[ReturnValue, ...]) -> str:
    types = [item.lua_type for item in returns if item.lua_type and not is_absent_return(item.lua_type)]
    if not types:
        return ""
    if len(types) == 1:
        return f": {types[0]}"
    joined = ", ".join(types)
    return f": ({joined})"


@dataclass(eq=False)
class Function(DocItem):
    """A Moonwave function or method."""

    parameters: tuple[Parameter, ...] = ()
    """Parameters, in source order."""

    returns: tuple[ReturnValue, ...] = ()
    """Return values, in `@return` order."""

    errors: tuple[ErrorValue, ...] = ()
    """Documented errors."""

    function_type: str = "static"
    """Moonwave `function_type`: `method` or `static`."""

    yields: bool = False
    """Whether `@yields` was set."""

    @property
    def visible_returns(self) -> tuple[ReturnValue, ...]:
        """Return values worth rendering.

        Empty `()` returns are omitted.
        """
        return tuple(item for item in self.returns if not is_absent_return(item.lua_type))

    @property
    def labels(self) -> list[str]:
        """Labels rendered next to the heading."""
        labels = super().labels
        if self.function_type == "static" and self.name != "__call":
            labels.append("static")
        if self.yields:
            labels.append("yields")
        return labels

    @property
    def signature(self) -> str:
        """Luau signature, using `:` for methods and `.` for functions."""
        owner = self.parent.name if self.parent is not None else ""
        if self.name == "__call":
            head = f"function {owner}" if owner else "function __call"
        elif self.kind == "method":
            head = f"function {owner}:{self.name}" if owner else f"function {self.name}"
        elif owner:
            head = f"function {owner}.{self.name}"
        else:
            head = f"function {self.name}"
        parameters = ", ".join(_format_parameter(parameter) for parameter in self.parameters)
        return f"{head}({parameters}){_format_returns(self.returns)}"


@dataclass(eq=False)
class Property(DocItem):
    """A Moonwave `@prop` entry."""

    lua_type: str = ""
    """Declared Luau type."""

    readonly: bool = False
    """Whether `@readonly` was set."""

    @property
    def labels(self) -> list[str]:
        """Labels rendered next to the heading."""
        labels = super().labels
        if self.readonly:
            labels.append("readonly")
        return labels

    @property
    def signature(self) -> str:
        """`name: type` when a type is known."""
        if self.lua_type:
            return f"{self.name}: {self.lua_type}"
        return self.name


@dataclass(eq=False)
class TypeAlias(DocItem):
    """A Moonwave `@type` or `@interface` entry."""

    lua_type: str | None = None
    """Alias target. Empty for interfaces that only declare fields."""

    fields: tuple[FieldInfo, ...] = ()
    """Interface fields."""

    @property
    def signature(self) -> str:
        """`Name = Type` for aliases, or the interface name."""
        if self.lua_type:
            return f"{self.name} = {self.lua_type}"
        return self.name


@dataclass(eq=False)
class Class(DocItem):
    """A Moonwave class and the members grouped under it."""

    functions: tuple[Function, ...] = ()
    """Static functions and methods."""

    properties: tuple[Property, ...] = ()
    """Properties."""

    types: tuple[TypeAlias, ...] = ()
    """Type aliases and interfaces."""

    def iter_members(self) -> Iterator[Function | Property | TypeAlias]:
        """Yield every member in Moonwave's group order."""
        yield from self.functions
        yield from self.properties
        yield from self.types
