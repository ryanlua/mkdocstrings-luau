# This module implements a handler for Luau.

from __future__ import annotations

import posixpath
import re
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, ClassVar

from mkdocs.exceptions import PluginError
from mkdocstrings import BaseHandler, CollectionError, CollectorItem, Inventory, get_logger

from mkdocstrings_handlers.luau._internal._models import Class, DocItem, Function, Property
from mkdocstrings_handlers.luau._internal._moonwave import (
    format_lua_type,
    linkify_markdown,
    load_library,
    read_json,
    run_extractor,
)
from mkdocstrings_handlers.luau._internal.config import LuauConfig, LuauOptions

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, MutableMapping

    from markupsafe import Markup
    from mkdocs.config.defaults import MkDocsConfig
    from mkdocstrings import HandlerOptions


_logger = get_logger(__name__)

_TEMPLATES: dict[str, tuple[str, str]] = {
    "class": ("class.html.jinja", "class"),
    "function": ("function.html.jinja", "function"),
    "method": ("function.html.jinja", "function"),
    "property": ("property.html.jinja", "property"),
    "type": ("type.html.jinja", "typedef"),
}


class LuauHandler(BaseHandler):
    """The Luau handler class."""

    name: ClassVar[str] = "luau"
    """The handler's name."""

    domain: ClassVar[str] = "luau"
    """The cross-documentation domain/language for this handler."""

    enable_inventory: ClassVar[bool] = True
    """Whether this handler is interested in enabling the creation of the `objects.inv` Sphinx inventory file."""

    fallback_theme: ClassVar[str] = "material"
    """The theme to fallback to."""

    def __init__(self, config: LuauConfig, base_dir: Path, **kwargs: Any) -> None:
        """Initialize the handler.

        Parameters:
            config: The handler configuration.
            base_dir: The base directory of the project.
            **kwargs: Arguments passed to the parent constructor.
        """
        super().__init__(**kwargs)

        self.config = config
        """The handler configuration."""
        self.base_dir = base_dir
        """The base directory of the project."""
        self.global_options = config.options
        """The global configuration options."""

        self._collected: dict[str, CollectorItem] = {}
        self._library: Any = None
        self._library_key: tuple[Any, ...] | None = None

    def get_inventory_urls(self) -> list[tuple[str, dict[str, Any]]]:
        """Return inventory URLs configured for this handler.

        Returns:
            `(url, options)` pairs passed to `load_inventory`.
        """
        return [
            (item.url, {"base_url": item.base_url, "domains": list(item.domains)}) for item in self.config.inventories
        ]

    @staticmethod
    def load_inventory(
        in_file: BinaryIO,
        url: str,
        base_url: str | None = None,
        domains: list[str] | None = None,
        **kwargs: Any,  # noqa: ARG004
    ) -> Iterator[tuple[str, str]]:
        """Yield items and their URLs from an inventory file streamed from `in_file`.

        Parameters:
            in_file: The binary file-like object to read the inventory from.
            url: The URL that this file is being streamed from (used to guess `base_url`).
            base_url: The URL that this inventory's sub-paths are relative to.
            domains: Domains to keep. Defaults to `luau`.
            **kwargs: Ignore additional arguments passed from the config.

        Yields:
            Tuples of (item identifier, item URL).
        """
        domains = domains or ["luau"]
        if base_url is None:
            base_url = posixpath.dirname(url)
        for item in Inventory.parse_sphinx(in_file, domain_filter=domains).values():
            yield item.name, posixpath.join(base_url, item.uri)

    def get_options(self, local_options: Mapping[str, Any]) -> HandlerOptions:
        """Get combined default, global and local options.

        Arguments:
            local_options: The local options.

        Returns:
            The combined options.
        """
        extra = {**self.global_options.get("extra", {}), **local_options.get("extra", {})}
        options = {**self.global_options, **local_options, "extra": extra}
        try:
            return LuauOptions.from_data(**options)
        except Exception as error:
            raise PluginError(f"Invalid options: {error}") from error

    def collect(self, identifier: str, options: LuauOptions) -> CollectorItem:  # noqa: ARG002
        """Collect data given an identifier and selection configuration.

        Parameters:
            identifier: `Class`, `Class.member`, or `Class:method`.
            options: Combined rendering options. Collection sources come from the handler configuration.

        Returns:
            The documented class or member.
        """
        library = self._load_library()
        try:
            return library.resolve(identifier)
        except KeyError as error:
            known = ", ".join(sorted(library.objects))
            raise CollectionError(
                f"Could not find Luau object {identifier!r}. Known objects: {known}",
            ) from error

    def render(self, data: CollectorItem, options: LuauOptions, *, locale: str | None = None) -> str:  # noqa: ARG002
        """Render a template using provided data and configuration options.

        Parameters:
            data: Collected Luau object.
            options: Combined rendering options.
            locale: Unused. Templates are English.

        Returns:
            Rendered HTML.
        """
        try:
            template_name, variable = _TEMPLATES[data.kind]
        except KeyError as error:
            raise CollectionError(f"Don't know how to render {data.kind!r}") from error
        context: dict[str, Any] = {
            "config": options,
            variable: data,
            "heading_level": options.heading_level,
            "root": True,
        }
        if isinstance(data, Class):
            context["members"] = _select_members(data, options)
        if isinstance(data, Property) and _is_event(data, options.event_types):
            context["member_symbol"] = "event"
        return self.env.get_template(template_name).render(**context)

    def get_aliases(self, identifier: str) -> tuple[str, ...]:
        """Get aliases for a given identifier.

        Parameters:
            identifier: Heading id, which is the object's canonical path.

        Returns:
            The canonical path and, for methods, the colon spelling `Class:method`.
        """
        item = self._collected.get(identifier)
        if item is None and self._library is not None:
            try:
                item = self._library.resolve(identifier)
            except KeyError:
                return ()
        if item is None:
            return ()
        aliases = [item.path]
        if isinstance(item, Function) and item.kind == "method" and item.parent is not None:
            aliases.append(f"{item.parent.name}:{item.name}")
        return tuple(dict.fromkeys(aliases))

    def update_env(self, config: dict) -> None:  # noqa: ARG002
        """Update the Jinja environment with any custom settings/filters/options for this handler.

        Parameters:
            config: MkDocs configuration, read from `mkdocs.yml`.
        """
        self.env.trim_blocks = True
        self.env.lstrip_blocks = True
        self.env.keep_trailing_newline = False
        self.env.filters["lua_type"] = self._format_lua_type
        self.env.filters["moonwave_markdown"] = self._moonwave_markdown

    def _format_lua_type(self, lua_type: str, external: tuple[Any, ...] = ()) -> Markup:
        return format_lua_type(lua_type, self._library, external)

    def _moonwave_markdown(self, text: str, heading_level: int, html_id: str = "") -> Markup:
        linked = linkify_markdown(text or "", self._library)
        return self.do_convert_markdown(linked, heading_level, html_id)

    def _load_library(self) -> Any:
        base = self._resolve(self.config.base) if self.config.base else self.base_dir
        paths = tuple(self._resolve(path) for path in self.config.paths)
        key = (self.config.json, paths, self.config.extractor, str(base))
        if self._library is not None and self._library_key == key:
            return self._library

        if self.config.json:
            payload = read_json(self._resolve(self.config.json))
        elif paths:
            payload = run_extractor(self.config.extractor, paths, base=base)
        else:
            raise CollectionError(
                "Configure the luau handler with `json` (Moonwave JSON) or `paths` (sources for moonwave-extractor).",
            )

        library = load_library(payload, base_dir=base)
        self._library = library
        self._library_key = key
        self._collected = dict(library.objects)
        _logger.debug("Loaded %s Luau objects", len(library.objects))
        return library

    def _resolve(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return (self.base_dir / path).resolve()


def _select_members(item: Class, options: LuauOptions) -> dict[str, list[DocItem]]:
    functions = [member for member in item.functions if _visible(member, options)]
    properties: list[DocItem] = []
    events: list[DocItem] = []
    for member in item.properties:
        if not _visible(member, options):
            continue
        if isinstance(member, Property) and _is_event(member, options.event_types):
            events.append(replace(member, kind="event"))
        else:
            properties.append(member)
    return {
        "methods": _order([member for member in functions if member.kind == "method"], options),
        "functions": _order([member for member in functions if member.kind == "function"], options),
        "properties": _order(properties, options),
        "events": _order(events, options),
        "types": _order([member for member in item.types if _visible(member, options)], options),
    }


def _is_event(item: Property, event_types: list[str]) -> bool:
    """Whether a property should be rendered as an event.

    Moonwave has no `@event` tag. A custom `@tag event` counts, as does a type whose
    name is configured in `event_types` (BindableEvent, RBXScriptSignal, and Signal by default).
    """
    if "event" in item.tags:
        return True
    if not event_types:
        return False
    names = set(event_types)
    return any(token in names for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", item.lua_type))


def _visible(item: DocItem, options: LuauOptions) -> bool:
    if item.private and not options.show_private:
        return False
    if item.unreleased and not options.show_unreleased:
        return False
    if item.ignore and not options.show_ignored:
        return False
    if options.members is not None and item.name not in options.members:
        return False
    return _filters_allow(item.name, options.filters)


def _filters_allow(name: str, filters: list[str]) -> bool:
    keep = True
    for pattern in filters:
        exclude = pattern.startswith("!")
        expression = pattern[1:] if exclude else pattern
        try:
            matched = re.search(expression, name) is not None
        except re.error as error:
            raise PluginError(f"Invalid member filter {pattern!r}: {error}") from error
        if matched:
            keep = not exclude
    return keep


def _order(items: list[DocItem], options: LuauOptions) -> list[DocItem]:
    if options.members_order == "alphabetical":
        return sorted(items, key=lambda item: item.name)
    return sorted(
        items,
        key=lambda item: (
            item.source.line if item.source is not None else 0,
            item.source.path if item.source is not None else "",
            item.name,
        ),
    )


def get_handler(
    handler_config: MutableMapping[str, Any],
    tool_config: MkDocsConfig,
    **kwargs: Any,
) -> LuauHandler:
    """Simply return an instance of `LuauHandler`.

    Arguments:
        handler_config: The handler configuration.
        tool_config: The tool (SSG) configuration.

    Returns:
        An instance of `LuauHandler`.
    """
    base_dir = Path(tool_config.config_file_path or "./mkdocs.yml").parent
    return LuauHandler(
        config=LuauConfig.from_data(**handler_config),
        base_dir=base_dir,
        **kwargs,
    )
