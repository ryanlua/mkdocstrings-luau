# Load Moonwave extractor JSON and resolve Luau identifiers.

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from markupsafe import Markup
from markupsafe import escape as html_escape
from mkdocstrings import CollectionError

from mkdocstrings_handlers.luau._internal._models import (
    Class,
    Deprecated,
    DocItem,
    ErrorValue,
    ExternalType,
    FieldInfo,
    Function,
    Parameter,
    Property,
    ReturnValue,
    Source,
    TypeAlias,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

_BLOCK_WORD = re.compile(r"\b(function|if|for|while|repeat|do|end|until)\b")
_CODE_SPAN = re.compile(r"(```.*?```|`[^`\n]+`)", re.DOTALL)
_SHORTCUT_LINK = re.compile(r"(?<!!)\[([^\[\]\n]+)\](?![(\[])")
_LUA_TYPE_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")


class Library:
    """Indexed Moonwave classes and members."""

    def __init__(self, classes: Sequence[Class]) -> None:
        """Index classes and members by canonical path."""
        self.classes = tuple(classes)
        """Classes in name order."""

        self.objects: dict[str, DocItem] = {}
        """Canonical path to object."""

        self.aliases: dict[str, str] = {}
        """Alternate spellings, such as `Class:method`, mapped to the canonical path."""

        self.external_types: dict[str, str] = {}
        """External type name to URL, collected from every object."""

        for item in classes:
            self._index(item)
            for member in item.iter_members():
                self._index(member)
                if member.kind == "method":
                    self.aliases[f"{item.name}:{member.name}"] = member.path

    def resolve(self, identifier: str) -> DocItem:
        """Return the object for `identifier`.

        Parameters:
            identifier: `Class`, `Class.member`, or `Class:method`.

        Raises:
            KeyError: When nothing matches.

        Returns:
            The documented object.
        """
        path = self.aliases.get(identifier, identifier)
        try:
            return self.objects[path]
        except KeyError:
            target = self.link_target(identifier)
            if target is None:
                raise
            return self.objects[target]

    def link_target(self, label: str) -> str | None:
        """Return a canonical path for a Moonwave link label.

        Parameters:
            label: Text inside `[...]`, such as `Vector3.new` or `UnitVector`.

        Returns:
            The canonical path, or `None` when the label is ambiguous or unknown.
        """
        colon = label.replace(":", ".", 1)
        if label in self.objects:
            return label
        if colon in self.objects:
            return colon
        if label in self.aliases:
            return self.aliases[label]
        matches = [item.path for item in self.objects.values() if item.name == label]
        if len(matches) == 1:
            return matches[0]
        return None

    def _index(self, item: DocItem) -> None:
        if item.path in self.objects:
            other = self.objects[item.path]
            raise CollectionError(
                f"Duplicate Moonwave member {item.path!r} ({other.kind} and {item.kind})",
            )
        self.objects[item.path] = item
        for external in item.external_types:
            self.external_types.setdefault(external.name, external.url)


def load_library(payload: Sequence[Mapping[str, Any]], *, base_dir: Path | None = None) -> Library:
    """Build a library from Moonwave's JSON array.

    Parameters:
        payload: Parsed extractor output. A single class object is accepted too.
        base_dir: Directory used to read source excerpts. Omit to skip file reads.

    Returns:
        An indexed library.
    """
    classes = [_class_from_json(dict(entry), base_dir) for entry in payload]
    classes.sort(key=lambda item: item.name)
    return Library(classes)


def read_json(path: Path) -> list[dict[str, Any]]:
    """Read a Moonwave JSON file.

    Parameters:
        path: Path to the JSON file.

    Raises:
        CollectionError: When the file is missing or is not a class array.

    Returns:
        A list of class objects.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise CollectionError(f"Could not read Moonwave JSON {path}: {error}") from error
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise CollectionError(f"Invalid Moonwave JSON in {path}: {error}") from error
    return _coerce_payload(data, origin=str(path))


def run_extractor(binary: str, paths: Sequence[Path], *, base: Path | None = None) -> list[dict[str, Any]]:
    """Run `moonwave-extractor extract` on each path and merge the classes.

    Parameters:
        binary: Executable name or path.
        paths: Files or directories to extract.
        base: Value of `--base`. Source paths in the JSON are relative to this directory.

    Raises:
        CollectionError: When the extractor is missing, fails, or prints invalid JSON.

    Returns:
        Merged class objects.
    """
    if not paths:
        raise CollectionError("No source paths were configured for the Moonwave extractor")

    merged: dict[str, dict[str, Any]] = {}
    for path in paths:
        command = [binary, "extract", str(path)]
        if base is not None:
            command.extend(["--base", str(base)])
        try:
            completed = subprocess.run(  # noqa: S603
                command,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as error:
            raise CollectionError(f"Could not run Moonwave extractor {binary!r}: {error}") from error
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise CollectionError(f"moonwave-extractor failed for {path}: {detail}")
        try:
            data = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise CollectionError(f"moonwave-extractor printed invalid JSON for {path}: {error}") from error
        for entry in _coerce_payload(data, origin=str(path)):
            _merge_class(merged, entry)
    return list(merged.values())


def linkify_markdown(text: str, library: Library | None) -> str:
    """Turn Moonwave shortcut links into HTML the autorefs plugin understands.

    Parameters:
        text: A Moonwave description.
        library: Indexed objects used to resolve `[Class.member]` labels.

    Returns:
        Markdown with known labels replaced by `<autoref>` or external anchors.
    """
    if not text or library is None:
        return text

    parts = _CODE_SPAN.split(text)
    rendered: list[str] = []
    for index, part in enumerate(parts):
        if index % 2 == 1:
            rendered.append(part)
            continue
        rendered.append(_SHORTCUT_LINK.sub(lambda match: _replace_link(match.group(1), library), part))
    return "".join(rendered)


def format_lua_type(lua_type: str, library: Library | None, external: Iterable[ExternalType] = ()) -> Markup:
    """Render a Luau type, linking known objects and `@external` types.

    Parameters:
        lua_type: Raw type text from Moonwave.
        library: Indexed objects.
        external: External types declared on the object being rendered.

    Returns:
        HTML safe to embed in a template.
    """
    if not lua_type:
        return Markup("")

    urls = dict(library.external_types) if library is not None else {}
    for item in external:
        urls[item.name] = item.url

    pieces: list[str] = []
    cursor = 0
    for match in _LUA_TYPE_TOKEN.finditer(lua_type):
        pieces.append(str(html_escape(lua_type[cursor : match.start()])))
        pieces.append(_render_type_token(match.group(0), library, urls))
        cursor = match.end()
    pieces.append(str(html_escape(lua_type[cursor:])))
    return Markup("".join(pieces))  # noqa: S704  # pieces are escaped individually


def _render_type_token(token: str, library: Library | None, urls: Mapping[str, str]) -> str:
    if library is not None:
        target = library.link_target(token)
        if target is not None:
            return f'<autoref identifier="{html_escape(target)}" optional>{html_escape(token)}</autoref>'
    if token in urls:
        # An explicit `@external` wins over the builtin skip list, so `boolean` can still be linked.
        url = urls[token]
        return f'<a class="autorefs autorefs-external" href="{html_escape(url)}">{html_escape(token)}</a>'
    return str(html_escape(token))


def _replace_link(label: str, library: Library) -> str:
    target = library.link_target(label)
    if target is not None:
        return f'<autoref identifier="{html_escape(target)}" optional>{html_escape(label)}</autoref>'
    url = library.external_types.get(label)
    if url:
        return f'<a class="autorefs autorefs-external" href="{html_escape(url)}">{html_escape(label)}</a>'
    return f"[{label}]"


def _coerce_payload(data: Any, *, origin: str) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or any(not isinstance(entry, dict) for entry in data):
        raise CollectionError(f"Moonwave JSON from {origin} must be an array of class objects")
    return data


def _merge_class(merged: dict[str, dict[str, Any]], entry: dict[str, Any]) -> None:
    name = entry.get("name")
    if not isinstance(name, str) or not name:
        raise CollectionError("Moonwave class is missing a name")
    current = merged.get(name)
    if current is None:
        merged[name] = entry
        return
    for key in ("functions", "properties", "types"):
        current.setdefault(key, [])
        current[key].extend(entry.get(key) or [])


def _class_from_json(data: dict[str, Any], base_dir: Path | None) -> Class:
    name = str(data.get("name") or "")
    if not name:
        raise CollectionError("Moonwave class is missing a name")
    item = Class(
        name=name,
        path=name,
        kind="class",
        description=_text(data.get("desc")),
        source=_source(data, base_dir, "class"),
        tags=_strings(data.get("tags")),
        external_types=_externals(data),
        realm=_realm(data),
        deprecated=_deprecated(data),
        since=_optional_str(data.get("since")),
        private=bool(data.get("private", False)),
        unreleased=bool(data.get("unreleased", False)),
        ignore=bool(data.get("ignore", False)),
        functions=tuple(_function_from_json(entry, name, base_dir) for entry in data.get("functions") or []),
        properties=tuple(_property_from_json(entry, name, base_dir) for entry in data.get("properties") or []),
        types=tuple(_type_from_json(entry, name, base_dir) for entry in data.get("types") or []),
    )
    for member in item.iter_members():
        member.parent = item
    return item


def _function_from_json(data: Mapping[str, Any], class_name: str, base_dir: Path | None) -> Function:
    name = str(data.get("name") or "")
    function_type = str(data.get("function_type") or "static")
    kind = "method" if function_type == "method" else "function"
    return Function(
        name=name,
        path=f"{class_name}.{name}",
        kind=kind,
        description=_text(data.get("desc")),
        source=_source(data, base_dir, kind),
        tags=_strings(data.get("tags")),
        external_types=_externals(data),
        realm=_realm(data),
        deprecated=_deprecated(data),
        since=_optional_str(data.get("since")),
        private=bool(data.get("private", False)),
        unreleased=bool(data.get("unreleased", False)),
        ignore=bool(data.get("ignore", False)),
        parameters=tuple(_parameter(entry) for entry in data.get("params") or []),
        returns=tuple(_return(entry) for entry in data.get("returns") or []),
        errors=tuple(_error(entry) for entry in data.get("errors") or []),
        function_type=function_type,
        yields=bool(data.get("yields", False)),
    )


def _property_from_json(data: Mapping[str, Any], class_name: str, base_dir: Path | None) -> Property:
    name = str(data.get("name") or "")
    return Property(
        name=name,
        path=f"{class_name}.{name}",
        kind="property",
        description=_text(data.get("desc")),
        source=_source(data, base_dir, "property"),
        tags=_strings(data.get("tags")),
        external_types=_externals(data),
        realm=_realm(data),
        deprecated=_deprecated(data),
        since=_optional_str(data.get("since")),
        private=bool(data.get("private", False)),
        unreleased=bool(data.get("unreleased", False)),
        ignore=bool(data.get("ignore", False)),
        lua_type=_text(data.get("lua_type")),
        readonly=bool(data.get("readonly", False)),
    )


def _type_from_json(data: Mapping[str, Any], class_name: str, base_dir: Path | None) -> TypeAlias:
    name = str(data.get("name") or "")
    lua_type = data.get("lua_type")
    return TypeAlias(
        name=name,
        path=f"{class_name}.{name}",
        kind="type",
        description=_text(data.get("desc")),
        source=_source(data, base_dir, "type"),
        tags=_strings(data.get("tags")),
        external_types=_externals(data),
        realm=_realm(data),
        deprecated=_deprecated(data),
        since=_optional_str(data.get("since")),
        private=bool(data.get("private", False)),
        unreleased=bool(data.get("unreleased", False)),
        ignore=bool(data.get("ignore", False)),
        lua_type=_text(lua_type) if isinstance(lua_type, str) and lua_type else None,
        fields=tuple(_field(entry) for entry in data.get("fields") or []),
    )


def _parameter(data: Mapping[str, Any]) -> Parameter:
    return Parameter(
        name=_text(data.get("name")),
        description=_text(data.get("desc")),
        lua_type=_text(data.get("lua_type")),
    )


def _return(data: Mapping[str, Any]) -> ReturnValue:
    return ReturnValue(description=_text(data.get("desc")), lua_type=_text(data.get("lua_type")))


def _error(data: Mapping[str, Any]) -> ErrorValue:
    return ErrorValue(lua_type=_text(data.get("lua_type")), description=_text(data.get("desc")))


def _field(data: Mapping[str, Any]) -> FieldInfo:
    return FieldInfo(
        name=_text(data.get("name")),
        lua_type=_text(data.get("lua_type")),
        description=_text(data.get("desc")),
    )


def _externals(data: Mapping[str, Any]) -> tuple[ExternalType, ...]:
    values = data.get("external_types") or []
    return tuple(ExternalType(name=_text(item.get("name")), url=_text(item.get("url"))) for item in values)


def _realm(data: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(item).lower() for item in data.get("realm") or [])


def _deprecated(data: Mapping[str, Any]) -> Deprecated | None:
    raw = data.get("deprecated")
    if not isinstance(raw, Mapping):
        return None
    version = raw.get("version")
    description = raw.get("desc")
    return Deprecated(
        version=_text(version) if isinstance(version, str) and version else None,
        description=_text(description) if isinstance(description, str) and description else None,
    )


def _strings(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(str(item) for item in value)


def _optional_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _source(data: Mapping[str, Any], base_dir: Path | None, kind: str) -> Source | None:
    raw = data.get("source")
    if not isinstance(raw, Mapping):
        return None
    try:
        line = int(raw["line"])
        path = str(raw["path"])
    except (KeyError, TypeError, ValueError):
        return None
    source = Source(line=line, path=path)
    if base_dir is not None:
        excerpt = _read_snippet(base_dir, source, kind)
        if excerpt is not None:
            source.text, source.text_line = excerpt
    return source


def _read_snippet(base_dir: Path, source: Source, _kind: str) -> tuple[str, int] | None:
    file_path = Path(source.path)
    if not file_path.is_file():
        file_path = base_dir / source.path
    if not file_path.is_file():
        return None
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    start = source.line - 1
    if start < 0 or start >= len(lines):
        return None
    stripped = lines[start].lstrip()
    if stripped.startswith(("function ", "local function ")):
        return _read_block(lines, start), source.line
    statement = _read_statement(lines, start)
    resolved = _resolve_assigned_function(lines, start, statement)
    if resolved is None:
        return statement, source.line
    return resolved


_ASSIGNED_NAME = re.compile(r"=\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:--.*)?$")


def _read_statement(lines: Sequence[str], start: int) -> str:
    """Read a Luau statement, including a multi-line call or table."""
    collected: list[str] = []
    paren = brace = bracket = 0
    limit = min(len(lines), start + 80)
    for index in range(start, limit):
        line = lines[index]
        collected.append(line)
        delta_paren, delta_brace, delta_bracket = _delimiter_delta(line)
        paren += delta_paren
        brace += delta_brace
        bracket += delta_bracket
        if paren <= 0 and brace <= 0 and bracket <= 0:
            break
    return "\n".join(collected)


def _delimiter_delta(line: str) -> tuple[int, int, int]:
    """Count parentheses, braces, and brackets outside strings and comments."""
    paren = brace = bracket = 0
    index = 0
    length = len(line)
    while index < length:
        character = line[index]
        if character == "-" and index + 1 < length and line[index + 1] == "-":
            break
        if character in {"'", '"', "`"}:
            index = _skip_short_string(line, index)
            continue
        if character == "[" and index + 1 < length and line[index + 1] == "[":
            end = line.find("]]", index + 2)
            index = length if end < 0 else end + 2
            continue
        if character == "(":
            paren += 1
        elif character == ")":
            paren -= 1
        elif character == "{":
            brace += 1
        elif character == "}":
            brace -= 1
        elif character == "[":
            bracket += 1
        elif character == "]":
            bracket -= 1
        index += 1
    return paren, brace, bracket


def _long_closer(line: str, index: int) -> tuple[str, int] | None:
    """Return the closer and the index after a `[` `=`* `[` opener."""
    if index >= len(line) or line[index] != "[":
        return None
    cursor = index + 1
    while cursor < len(line) and line[cursor] == "=":
        cursor += 1
    if cursor >= len(line) or line[cursor] != "[":
        return None
    return "]" + ("=" * (cursor - index - 1)) + "]", cursor + 1


def _code_only(line: str, pending: str | None = None) -> tuple[str, str | None]:
    """Drop strings and comments so keyword counts stay in code.

    `pending` is the closer of a long string or comment that started on an earlier line.
    The returned closer is set when that bracket continues past this line.
    """
    pieces: list[str] = []
    index = 0
    length = len(line)
    if pending is not None:
        end = line.find(pending)
        if end < 0:
            return "", pending
        index = end + len(pending)
    while index < length:
        character = line[index]
        if character == "-" and index + 1 < length and line[index + 1] == "-":
            long = _long_closer(line, index + 2)
            if long is None:
                break
            closer, content = long
            end = line.find(closer, content)
            if end < 0:
                return "".join(pieces), closer
            index = end + len(closer)
            continue
        if character in {"'", '"', "`"}:
            index = _skip_short_string(line, index)
            continue
        long = _long_closer(line, index)
        if long is not None:
            closer, content = long
            end = line.find(closer, content)
            if end < 0:
                return "".join(pieces), closer
            index = end + len(closer)
            continue
        pieces.append(character)
        index += 1
    return "".join(pieces), None


def _skip_short_string(line: str, index: int) -> int:
    quote = line[index]
    index += 1
    length = len(line)
    while index < length:
        if line[index] == "\\":
            index += 2
            continue
        if line[index] == quote:
            return index + 1
        index += 1
    return index


def _resolve_assigned_function(lines: Sequence[str], start: int, statement: str) -> tuple[str, int] | None:
    """Return the body of a function assigned by name in the same file."""
    if "\n" in statement:
        return None
    match = _ASSIGNED_NAME.search(statement.strip())
    if match is None:
        return None
    name = match.group(1)
    pattern = re.compile(rf"^(?:local\s+)?function\s+{re.escape(name)}\b")
    candidates = [index for index, line in enumerate(lines) if pattern.match(line.lstrip())]
    if not candidates:
        return None
    prior = [index for index in candidates if index <= start]
    chosen = prior[-1] if prior else candidates[0] if len(candidates) == 1 else None
    if chosen is None:
        return None
    return _read_block(lines, chosen), chosen + 1


def _block_delta(code: str, *, skip_do: bool) -> tuple[int, bool]:
    """Count block openers and closers. The `do` of `for`/`while` is not a second block."""
    delta = 0
    for word in _BLOCK_WORD.findall(code):
        if word in {"function", "if", "repeat"}:
            delta += 1
            skip_do = False
        elif word in {"for", "while"}:
            delta += 1
            skip_do = True
        elif word == "do":
            if skip_do:
                skip_do = False
            else:
                delta += 1
        else:
            delta -= 1
            skip_do = False
    return delta, skip_do


def _read_block(lines: Sequence[str], start: int) -> str:
    depth = 0
    opened = False
    pending: str | None = None
    skip_do = False
    collected: list[str] = []
    limit = min(len(lines), start + 80)
    for index in range(start, limit):
        line = lines[index]
        collected.append(line)
        code, pending = _code_only(line, pending)
        delta, skip_do = _block_delta(code, skip_do=skip_do)
        depth += delta
        if depth > 0:
            opened = True
        if opened and depth <= 0:
            break
        if not opened and index > start and line and not line[0].isspace():
            collected.pop()
            break
    return "\n".join(collected)
