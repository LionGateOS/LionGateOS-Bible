"""Content-sniffing text extraction for the GD Bible Research pipeline.

Milestone 0.  Strictly read-only with respect to source documents: every
file is opened ``"rb"`` and never written, renamed or deleted.

The dispatcher keys on the first bytes of the file, **never** on the
filename.  A survey of the 5,303-file archive found ~210 files whose
declared extension disagrees with their real container (103 ``.doc``
files are actually RTF, 37 ``.rtf`` files are OLE2, 28 ``.docx`` files
are OLE2, 28 ``.doc`` files are ZIP, ...).  Extension-based dispatch
would silently mis-extract all of them.

Extraction preserves capitalization, punctuation and original wording.
No case folding, no whitespace collapsing, no Unicode normalisation is
applied to the returned text -- the research goals depend on the exact
surface form (``God`` vs ``god``, ``LORD`` vs ``Lord``).
"""

from __future__ import annotations

import codecs
import struct
import zipfile

EXTRACTOR_VERSION = "1.1.0"

#: bytes of a file inspected to decide its container
SNIFF_BYTES = 8


class ExtractionError(Exception):
    """Base class for extraction failures."""


class UnsupportedFormat(ExtractionError):
    """The container is recognised but no extractor handles it."""


class MalformedDocument(ExtractionError):
    """The container is supported but its internal structure is invalid."""


# --------------------------------------------------------------------------
# container sniffing
# --------------------------------------------------------------------------

def sniff(path):
    """Return the real container of *path*: OLE2, ZIP, RTF, PDF or OTHER."""
    with open(path, "rb") as handle:
        head = handle.read(SNIFF_BYTES)
    if head[:4] == b"\xd0\xcf\x11\xe0":
        return "OLE2"
    if head[:2] == b"PK":
        return "ZIP"
    if head[:5] in (b"{\\rtf", b"{\rtf"):
        return "RTF"
    if head[:4] == b"%PDF":
        return "PDF"
    return "OTHER"


# --------------------------------------------------------------------------
# OLE2 / MS-DOC (Word 97-2003 binary, and Word 6/95)
# --------------------------------------------------------------------------

def _u16(buf, offset):
    return struct.unpack_from("<H", buf, offset)[0]


def _u32(buf, offset):
    return struct.unpack_from("<I", buf, offset)[0]


def _ole2_text(path):
    """Extract text from a Word binary (OLE2) document.

    Walks the FIB -> Clx -> Pcdt -> PlcPcd piece table described by
    MS-DOC, honouring the 8-bit/UTF-16 flag in each piece descriptor.
    Returns ``(text, extractor_name)``.
    """
    import olefile  # imported lazily so sniffing never needs it

    ole = olefile.OleFileIO(path)
    try:
        if not ole.exists("WordDocument"):
            raise MalformedDocument("OLE2 stream 'WordDocument' is absent")
        word = ole.openstream("WordDocument").read()
        if len(word) < 0x20:
            raise MalformedDocument("WordDocument stream truncated")

        fib_flags = _u16(word, 0x000A)
        n_fib = _u16(word, 0x0002)

        # Word 6/95 keeps a plain character range, no piece table.
        if n_fib < 193:
            start = _u32(word, 0x0018)
            end = _u32(word, 0x001C)
            if not 0 <= start <= end <= len(word):
                raise MalformedDocument("legacy text range is out of bounds")
            return word[start:end].decode("cp1252", "replace"), "legacy"

        table_name = "1Table" if (fib_flags & 0x0200) else "0Table"
        if not ole.exists(table_name):
            raise MalformedDocument("table stream %r is absent" % table_name)
        table = ole.openstream(table_name).read()

        fc_clx = _u32(word, 0x01A2)
        lcb_clx = _u32(word, 0x01A6)
        if not 0 <= fc_clx <= fc_clx + lcb_clx <= len(table):
            raise MalformedDocument("Clx range is out of bounds in table stream")
        clx = table[fc_clx:fc_clx + lcb_clx]

        # Skip any Prc entries (0x01) preceding the Pcdt (0x02).
        index = 0
        while index < len(clx) and clx[index] == 1:
            index += 3 + struct.unpack_from("<h", clx, index + 1)[0]
        if index >= len(clx) or clx[index] != 2:
            raise MalformedDocument("piece table (Pcdt) not found in Clx")

        lcb_plc = _u32(clx, index + 1)
        plc = clx[index + 5:index + 5 + lcb_plc]
        pieces = (len(plc) - 4) // 12
        if pieces <= 0:
            raise MalformedDocument("piece table is empty")

        cps = [_u32(plc, 4 * i) for i in range(pieces + 1)]
        parts = []
        for i in range(pieces):
            descriptor = 4 * (pieces + 1) + 8 * i
            fc = _u32(plc, descriptor + 2)
            compressed = bool(fc & 0x40000000)
            offset = (fc & 0x3FFFFFFF) // 2 if compressed else fc
            length = cps[i + 1] - cps[i]
            if length < 0:
                raise MalformedDocument("piece %d has negative length" % i)
            if compressed:
                parts.append(word[offset:offset + length].decode("cp1252", "replace"))
            else:
                parts.append(word[offset:offset + length * 2].decode("utf-16-le", "replace"))
        return "".join(parts), "word97"
    finally:
        ole.close()


# --------------------------------------------------------------------------
# ZIP / OOXML (WordprocessingML) and other ZIP containers
# --------------------------------------------------------------------------

_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _zip_text(path):
    """Extract text from an OOXML (docx) package."""
    import xml.etree.ElementTree as ElementTree

    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if "word/document.xml" not in names:
            if any(name.startswith("Index/") for name in names):
                raise UnsupportedFormat("Apple Pages document (Index/*.iwa)")
            raise MalformedDocument("ZIP container has no word/document.xml")
        root = ElementTree.fromstring(archive.read("word/document.xml"))

    paragraphs = []
    for paragraph in root.iter(_W_NS + "p"):
        paragraphs.append("".join(node.text or "" for node in paragraph.iter(_W_NS + "t")))
    return "\n".join(paragraphs), "docx"


# --------------------------------------------------------------------------
# RTF
# --------------------------------------------------------------------------

_RTF_SKIP_DESTINATIONS = frozenset((
    "fonttbl", "colortbl", "stylesheet", "info", "header", "footer",
    "headerl", "headerr", "headerf", "footerl", "footerr", "footerf",
    "pict", "object", "annotation", "field", "fldinst",
    "listtable", "listoverridetable", "revtbl", "generator",
    "xmlnstbl", "themedata", "datastore", "filetbl",
))
_RTF_MAX_DEPTH = 256


def _rtf_text(path):
    """Extract visible body text with group-aware RTF destination handling."""
    with open(path, "rb") as handle:
        raw = handle.read().decode("cp1252", "replace")

    if not raw.startswith(r"{\rtf"):
        raise MalformedDocument("missing RTF header")

    output = []
    stack = []
    skip = False
    uc = 1
    active_font = 0
    ansi_codec = "cp1252"
    font_charsets = {}
    font_table_depth = None
    font_definition = None
    fallback = 0
    i = 0

    while i < len(raw):
        ch = raw[i]

        if ch == "{":
            if len(stack) >= _RTF_MAX_DEPTH:
                raise MalformedDocument("RTF nesting limit exceeded")
            stack.append((skip, uc, active_font, font_table_depth, font_definition))
            i += 1
            continue

        if ch == "}":
            if not stack:
                raise MalformedDocument("unexpected RTF closing brace")
            skip, uc, active_font, font_table_depth, font_definition = stack.pop()
            i += 1
            continue

        if ch != "\\":
            if not skip and fallback == 0 and ch not in "\r\n":
                output.append(ch)
            elif not skip and fallback > 0:
                fallback -= 1
            i += 1
            continue

        i += 1
        if i >= len(raw):
            raise MalformedDocument("trailing RTF backslash")

        control = raw[i]

        if control in "{}\\":
            if not skip:
                if fallback:
                    fallback -= 1
                else:
                    output.append(control)
            i += 1
            continue

        if control == "'":
            if i + 2 >= len(raw):
                raise MalformedDocument("truncated RTF hex escape")
            value = raw[i + 1:i + 3]
            try:
                byte_value = int(value, 16)
            except ValueError:
                raise MalformedDocument("invalid RTF hex escape")
            if not skip:
                if fallback:
                    fallback -= 1
                else:
                    charset = font_charsets.get(active_font, 0)
                    codec = "mac_roman" if charset == 77 else ansi_codec
                    output.append(bytes([byte_value]).decode(codec, "replace"))
            i += 3
            continue

        if control == "*":
            skip = True
            i += 1
            continue

        if not control.isalpha():
            if control == "~" and not skip and not fallback:
                output.append("\u00a0")
            elif control == "-" and not skip and not fallback:
                output.append("\u00ad")
            elif control == "_" and not skip and not fallback:
                output.append("\u2011")
            i += 1
            continue

        begin = i
        while i < len(raw) and raw[i].isalpha():
            i += 1
        word = raw[begin:i]

        number = None
        number_start = i
        if i < len(raw) and raw[i] == "-":
            i += 1
        while i < len(raw) and raw[i].isdigit():
            i += 1
        if i > number_start and raw[number_start:i] != "-":
            number = int(raw[number_start:i])
        elif i > number_start:
            raise MalformedDocument("invalid RTF numeric argument")

        if i < len(raw) and raw[i] == " ":
            i += 1

        if word == "fonttbl":
            font_table_depth = len(stack)
            skip = True
            continue

        if font_table_depth is not None:
            if word == "f" and number is not None:
                font_definition = number
            elif word == "fcharset" and number is not None and font_definition is not None:
                font_charsets[font_definition] = number

        if word in _RTF_SKIP_DESTINATIONS:
            skip = True
            continue

        if word == "ansicpg" and number is not None and not skip:
            candidate_codec = "mac_roman" if number == 10000 else f"cp{number}"
            try:
                codecs.lookup(candidate_codec)
            except LookupError:
                raise MalformedDocument("unsupported RTF ANSI code page")
            ansi_codec = candidate_codec
            continue

        if word == "f" and number is not None and not skip:
            active_font = number
            continue

        if word == "uc" and number is not None:
            uc = max(0, min(number, 32))
            continue

        if skip:
            continue

        if word == "u" and number is not None:
            code_unit = number % 65536
            if 0xDC00 <= code_unit <= 0xDFFF:
                if output and len(output[-1]) == 1 and 0xD800 <= ord(output[-1]) <= 0xDBFF:
                    high = ord(output.pop()) - 0xD800
                    low = code_unit - 0xDC00
                    output.append(chr(0x10000 + (high << 10) + low))
                else:
                    output.append("\ufffd")
            else:
                if output and len(output[-1]) == 1 and 0xD800 <= ord(output[-1]) <= 0xDBFF:
                    output[-1] = "\ufffd"
                output.append(chr(code_unit))
            fallback = uc
        elif word in ("par", "line"):
            output.append("\n")
        elif word == "tab":
            output.append("\t")
        elif word == "emdash":
            output.append("\u2014")
        elif word == "endash":
            output.append("\u2013")
        elif word == "bullet":
            output.append("\u2022")
        elif word == "lquote":
            output.append("\u2018")
        elif word == "rquote":
            output.append("\u2019")
        elif word == "ldblquote":
            output.append("\u201c")
        elif word == "rdblquote":
            output.append("\u201d")

    if stack:
        raise MalformedDocument("unclosed RTF group")

    text = "".join(output)
    text = "".join(
        "\ufffd" if 0xD800 <= ord(char) <= 0xDFFF else char
        for char in text
    )
    return text, "rtf"


# --------------------------------------------------------------------------
# dispatcher
# --------------------------------------------------------------------------

_EXTRACTORS = {
    "OLE2": _ole2_text,
    "ZIP": _zip_text,
    "RTF": _rtf_text,
}


def extract(path):
    """Extract text from *path* using its real container.

    Returns a dict::

        {"text": str, "container": str, "extractor": str,
         "extractor_version": str, "char_count": int}

    Raises :class:`UnsupportedFormat` for containers with no extractor
    (PDF, QuarkXPress, plain text) and :class:`MalformedDocument` when the
    container is supported but internally broken.  Callers must record
    both cases in the failure ledger rather than skipping silently.
    """
    container = sniff(path)
    extractor = _EXTRACTORS.get(container)
    if extractor is None:
        raise UnsupportedFormat("no extractor for container %s" % container)

    text, name = extractor(path)
    return {
        "text": text,
        "container": container,
        "extractor": name,
        "extractor_version": EXTRACTOR_VERSION,
        "char_count": len(text),
    }
