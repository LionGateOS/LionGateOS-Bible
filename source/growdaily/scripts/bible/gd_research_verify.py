"""Schema validation and quotation verification.

Milestone 0.

The model's output is **never trusted**.  Everything it returns is
checked deterministically in Python before it is allowed into a findings
file:

* the JSON must match the expected shape, and
* every quotation must be a literal substring of the source -- exactly,
  or after a conservative Unicode/whitespace normalisation.

Measured on real archive text with ``qwen3.6:27b`` (10 chunks): 10/10
responses were valid JSON and 24/26 quotations matched exactly, with the
remaining 2 matching after normalisation and **0 fabricated**.  The
verifier is what makes that guarantee hold rather than hope.

A quotation that fails both checks is **quarantined**, not discarded and
not emitted as a finding, so a reviewer can always see what the model
tried to claim.
"""

from __future__ import annotations

import re
import unicodedata

SCHEMA_VERSION = "gd-findings/1"

#: Topics the analyser may report.  Anything else is rejected.
TOPICS = ("translation", "wording", "capitalization", "terminology", "scripture")

#: Topics that are close enough to a canonical topic to be folded in.
_TOPIC_ALIASES = {
    "translations": "translation",
    "translation_wording": "translation",
    "capitalisation": "capitalization",
    "capitalization_wording": "capitalization",
    "capitalisation_wording": "capitalization",
    "terms": "terminology",
    "terminology_change": "terminology",
    "scripture_reference": "scripture",
    "scripture_refs": "scripture",
    "bible": "scripture",
}

REQUIRED_FINDING_KEYS = ("topic", "quote", "note")
ALLOWED_CONFIDENCE = ("high", "medium", "low")

_WHITESPACE = re.compile(r"\s+")
_SMART_QUOTES = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
    "\u2013": "-", "\u2014": "-", "\u2015": "-", "\u2212": "-",
    "\u00a0": " ", "\u2009": " ", "\u202f": " ", "\u200b": "",
}


def normalize_for_match(text):
    """Conservative normalisation used only for the fallback match.

    Folds compatibility forms, unifies curly quotes and dashes, and
    collapses runs of whitespace.  It deliberately does **not** fold
    case or strip punctuation, because capitalization is itself a
    research topic.
    """
    if not text:
        return ""
    folded = unicodedata.normalize("NFKC", text)
    folded = "".join(_SMART_QUOTES.get(ch, ch) for ch in folded)
    return _WHITESPACE.sub(" ", folded).strip()


def canonical_topic(topic):
    """Map a reported topic onto the canonical set, or return None."""
    if not isinstance(topic, str):
        return None
    key = topic.strip().lower().replace(" ", "_")
    if key in TOPICS:
        return key
    return _TOPIC_ALIASES.get(key)


def validate_response(payload):
    """Validate the raw model payload against the findings schema.

    Returns ``(findings, errors)`` where *findings* is the list of
    structurally acceptable finding dicts (topic canonicalised, strings
    coerced) and *errors* is a list of human-readable problems.  A
    non-empty *errors* list does not by itself abort the run: the caller
    decides, but it is always recorded.
    """
    errors = []

    if not isinstance(payload, dict):
        return [], ["top level is %s, expected object" % type(payload).__name__]

    findings = payload.get("findings")
    if findings is None:
        return [], ["missing 'findings' key"]
    if not isinstance(findings, list):
        return [], ["'findings' is %s, expected array" % type(findings).__name__]

    accepted = []
    for position, item in enumerate(findings):
        if not isinstance(item, dict):
            errors.append("findings[%d] is not an object" % position)
            continue

        missing = [key for key in REQUIRED_FINDING_KEYS if not item.get(key)]
        if missing:
            errors.append("findings[%d] missing/empty %s" % (position, ", ".join(missing)))
            continue

        topic = canonical_topic(item.get("topic"))
        if topic is None:
            errors.append(
                "findings[%d] topic %r is not one of %s"
                % (position, item.get("topic"), list(TOPICS))
            )
            continue

        raw_refs = item.get("scripture_refs") or []
        if isinstance(raw_refs, str):
            raw_refs = [raw_refs]
        if not isinstance(raw_refs, list):
            errors.append("findings[%d] scripture_refs is not an array" % position)
            raw_refs = []
        refs = [str(ref).strip() for ref in raw_refs if str(ref).strip()]

        confidence = str(item.get("confidence", "") or "").strip().lower()
        if confidence not in ALLOWED_CONFIDENCE:
            confidence = "low"

        speaker = str(item.get("speaker", "") or "").strip() or "unknown"

        accepted.append({
            "topic": topic,
            "quote": str(item.get("quote")).strip(),
            "scripture_refs": refs,
            "speaker": speaker,
            "note": str(item.get("note")).strip(),
            "confidence": confidence,
        })

    return accepted, errors


def verify_quote(quote, chunk, document_text):
    """Locate *quote* in the source.

    Checks the quote twice: against the chunk the model actually saw, and
    against the whole extracted document.  Returns a dict describing both
    matches and the absolute offset in the document when one exists.
    """
    result = {
        "match": "none",
        "verified": False,
        "offset_in_chunk": None,
        "char_start": None,
        "char_end": None,
    }
    if not quote:
        return result

    # 1. exact, inside the chunk the model was shown
    position = chunk["text"].find(quote)
    if position >= 0:
        result["match"] = "exact"
        result["offset_in_chunk"] = position
        absolute = chunk["char_start"] + position
        result["char_start"] = absolute
        result["char_end"] = absolute + len(quote)
        result["verified"] = True
        return result

    # 2. exact, anywhere in the document
    position = document_text.find(quote)
    if position >= 0:
        result["match"] = "exact"
        result["char_start"] = position
        result["char_end"] = position + len(quote)
        result["verified"] = True
        return result

    # 3. normalised fallback (curly quotes, dashes, whitespace runs)
    needle = normalize_for_match(quote)
    haystack = normalize_for_match(chunk["text"])
    if needle and needle in haystack:
        result["match"] = "normalized"
        result["offset_in_chunk"] = haystack.find(needle)
        result["verified"] = True
        result["char_start"] = chunk["char_start"]
        return result

    haystack = normalize_for_match(document_text)
    if needle and needle in haystack:
        result["match"] = "normalized"
        result["verified"] = True
        result["char_start"] = haystack.find(needle)
        return result

    return result


def verify_findings(findings, chunk, document_text):
    """Attach verification metadata, splitting verified from quarantined.

    Returns ``(verified, quarantined)``.  A quarantined entry keeps the
    model's original claim plus the reason it was rejected.
    """
    verified = []
    quarantined = []

    for finding in findings:
        check = verify_quote(finding["quote"], chunk, document_text)
        enriched = dict(finding)
        enriched["quote_match"] = check["match"]
        enriched["quote_verified"] = check["verified"]
        enriched["quote_char_start"] = check["char_start"]
        enriched["quote_char_end"] = check["char_end"]

        if check["verified"]:
            verified.append(enriched)
        else:
            quarantined.append({
                "reason": "quote not found in source text",
                "finding": enriched,
            })

    return verified, quarantined
