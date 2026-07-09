#!/usr/bin/env python3

import json
from pathlib import Path

REGISTRY = Path("editions/registry.json")


def load_registry():
    if not REGISTRY.exists():
        raise FileNotFoundError("Missing editions/registry.json")

    return json.loads(REGISTRY.read_text())


def get_edition(edition_id):
    data = load_registry()

    for edition in data.get("editions", []):
        if edition["id"] == edition_id:
            return edition

    return None


def list_editions():
    data = load_registry()
    return data.get("editions", [])


if __name__ == "__main__":
    print("Available Bible Editions")
    print("------------------------")

    for edition in list_editions():
        print(f"{edition['name']} ({edition['language']})")
