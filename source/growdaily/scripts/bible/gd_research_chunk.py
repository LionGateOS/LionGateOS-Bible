"""Reproducible, offset-preserving chunking for the GD Bible Research pipeline.

Milestone 0.

Determinism is the whole point: the same document with the same
``CHUNKER_VERSION`` must always yield byte-identical chunks with
byte-identical offsets.  A finding's provenance depends on the offsets
being reproducible, so that a reviewer can jump straight back to the
exact passage in the original extraction.

Invariant enforced by :func:`chunk_text` and asserted in the tests::

    text[chunk["char_start"]:chunk["char_end"]] == chunk["text"]
"""

from __future__ import annotations

CHUNKER_VERSION = "1.0.0"

#: default window size, in characters.  A 2,400-char window costs roughly
#: 600 tokens, which leaves ample room inside the model's 8,192-token
#: context for the instruction block and the JSON reply.
DEFAULT_CHUNK_CHARS = 2400


def chunk_text(text, chunk_chars=DEFAULT_CHUNK_CHARS, overlap=0):
    """Split *text* into consecutive windows with absolute offsets.

    Parameters
    ----------
    text:
        The extracted document text.  Not modified.
    chunk_chars:
        Window size in characters.
    overlap:
        Characters shared between consecutive windows.  Milestone 0 uses
        0; the parameter exists so a later milestone can add context
        bleed without changing the offset contract.

    Returns
    -------
    list of dict
        ``{"chunk_id", "index", "char_start", "char_end", "char_count", "text"}``
    """
    if chunk_chars <= 0:
        raise ValueError("chunk_chars must be positive")
    if overlap < 0 or overlap >= chunk_chars:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_chars")

    chunks = []
    step = chunk_chars - overlap
    start = 0
    index = 0
    total = len(text)

    while start < total:
        end = min(start + chunk_chars, total)
        chunks.append({
            "chunk_id": "c%04d" % index,
            "index": index,
            "char_start": start,
            "char_end": end,
            "char_count": end - start,
            "text": text[start:end],
        })
        if end >= total:
            break
        start += step
        index += 1

    return chunks
