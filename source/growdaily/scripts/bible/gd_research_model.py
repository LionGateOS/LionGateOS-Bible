"""Local-only Ollama client for the GD Bible Research pipeline.

Milestone 0.

Safety properties enforced here, not by convention:

* **Cloud models are rejected before any request is made.**
  The Ollama server on this host runs with ``OLLAMA_NO_CLOUD=false`` and
  ``OLLAMA_REMOTES=[ollama.com]``, and cloud-tagged models
  (``kimi-k3:cloud``, ``glm-5.3:cloud``, ``qwen3.5:cloud``,
  ``glm-5.1:cloud``) are installed.  A typo in a model name would
  silently spend Ollama Cloud tokens, so the client refuses anything
  that is not on an explicit local allow-list.
* **Competing workloads are detected before loading a model**, so we do
  not evict somebody else's resident model by accident.
* **Bounded retries and hard timeouts** -- no unbounded loops.
* No global Ollama state is touched: this module only issues per-request
  HTTP calls and never runs the ``ollama`` CLI or edits its config.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

#: Models this pipeline is permitted to load.  Every entry must be a
#: genuinely local model (no ``:cloud`` suffix) that has been verified to
#: load on this host.
#:
#: ``qwen38-27b-q8:latest`` is deliberately absent: it is installed but
#: cannot be initialised by Ollama 0.22.1 --
#: "qwen3next: layer 64 missing attn_qkv/attn_gate projections".
LOCAL_MODEL_ALLOWLIST = ("qwen3.6:27b",)

DEFAULT_BASE_URL = os.environ.get(
    "GD_RESEARCH_OLLAMA_BASE_URL", "http://127.0.0.1:11434"
).rstrip("/")
DEFAULT_TIMEOUT = 600
DEFAULT_ATTEMPTS = 2
DEFAULT_BACKOFF = 3.0


class ModelError(Exception):
    """Base class for model-client failures."""


class CloudModelRejected(ModelError):
    """Raised when a model name is cloud-tagged or not allow-listed."""


class ModelUnavailable(ModelError):
    """Raised when the local server cannot be reached or refuses to serve."""


def assert_local_model(name):
    """Reject cloud-tagged and non-allow-listed model names.

    Called before any HTTP request is constructed.  Raises
    :class:`CloudModelRejected` rather than warning, so that a bad name
    can never reach the network.
    """
    if not isinstance(name, str) or not name.strip():
        raise CloudModelRejected("model name must be a non-empty string")

    candidate = name.strip()
    lowered = candidate.lower()

    if ":cloud" in lowered or lowered.endswith("-cloud"):
        raise CloudModelRejected(
            "refusing cloud-tagged model %r: this pipeline must never "
            "consume Ollama Cloud tokens" % candidate
        )
    if candidate not in LOCAL_MODEL_ALLOWLIST:
        raise CloudModelRejected(
            "model %r is not on the local allow-list %r"
            % (candidate, list(LOCAL_MODEL_ALLOWLIST))
        )
    return candidate


def _get_json(base_url, path, timeout=30):
    request = urllib.request.Request(base_url + path, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def list_loaded_models(base_url=DEFAULT_BASE_URL, timeout=30):
    """Return the models currently resident in memory (``/api/ps``)."""
    try:
        payload = _get_json(base_url, "/api/ps", timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller
        raise ModelUnavailable("cannot reach Ollama at %s: %s" % (base_url, exc))
    return [
        {
            "name": item.get("name"),
            "size_vram": item.get("size_vram", 0),
            "context": item.get("context"),
        }
        for item in payload.get("models", [])
    ]


def check_competing_workloads(model, base_url=DEFAULT_BASE_URL, allow_evict=False):
    """Inspect resident models before we load anything.

    Returns a dict describing what was found.  Raises
    :class:`ModelUnavailable` when another model is resident and
    *allow_evict* is false, so that evicting a pinned model is an
    explicit, recorded decision rather than a silent side effect.
    """
    target = assert_local_model(model)
    loaded = list_loaded_models(base_url=base_url)
    competing = [item for item in loaded if item["name"] != target]

    report = {
        "loaded_before": loaded,
        "competing": competing,
        "target_already_loaded": any(item["name"] == target for item in loaded),
        "allow_evict": allow_evict,
    }

    if competing and not allow_evict:
        names = ", ".join(str(item["name"]) for item in competing)
        raise ModelUnavailable(
            "competing local-model workload(s) resident: %s. "
            "Loading %r would evict them. Re-run with --allow-evict to "
            "accept that explicitly." % (names, target)
        )
    return report


def generate_json(
    prompt,
    model,
    base_url=DEFAULT_BASE_URL,
    options=None,
    timeout=DEFAULT_TIMEOUT,
    attempts=DEFAULT_ATTEMPTS,
    backoff=DEFAULT_BACKOFF,
    keep_alive="2m",
):
    """Send one prompt and return the raw JSON-mode response.

    The model is forced into ``format="json"`` and ``think=False``.
    ``think=False`` is mandatory for ``qwen3.6:27b``: left in its default
    thinking mode the visible ``response`` comes back empty because the
    token budget is consumed by reasoning tokens.

    Returns a dict with the text plus the timing and identity metadata
    that must be preserved as provenance.  Retries are bounded by
    *attempts*.
    """
    target = assert_local_model(model)

    payload = {
        "model": target,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "think": False,
        "keep_alive": keep_alive,
        "options": dict(options or {}),
    }
    body = json.dumps(payload).encode("utf-8")

    last_error = None
    for attempt in range(1, attempts + 1):
        started = time.time()
        request = urllib.request.Request(
            base_url + "/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
            elapsed = time.time() - started
            return {
                "response": result.get("response", ""),
                "model": target,
                "model_reported": result.get("model", target),
                "attempts": attempt,
                "wall_seconds": elapsed,
                "load_seconds": result.get("load_duration", 0) / 1e9,
                "prompt_eval_count": result.get("prompt_eval_count"),
                "prompt_eval_seconds": result.get("prompt_eval_duration", 0) / 1e9,
                "eval_count": result.get("eval_count"),
                "eval_seconds": result.get("eval_duration", 0) / 1e9,
                "total_seconds": result.get("total_duration", 0) / 1e9,
            }
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", "replace")[:300]
            except Exception:  # noqa: BLE001
                pass
            last_error = "HTTP %s: %s" % (exc.code, detail)
        except Exception as exc:  # noqa: BLE001 - network/timeout/JSON
            last_error = "%s: %s" % (type(exc).__name__, exc)

        if attempt < attempts:
            time.sleep(backoff * attempt)

    raise ModelUnavailable(
        "model %r failed after %d attempt(s): %s" % (target, attempts, last_error)
    )
