#!/usr/bin/env python3

import json
from pathlib import Path

REGISTRY = Path("editions/registry.json")

REQUIRED_FIELDS = [
    "id",
    "name",
    "language",
    "type",
    "required",
    "features",
]

FEATURE_FIELDS = [
    "redLetter",
    "strongs",
    "notes",
    "highlights",
]


def main():
    if not REGISTRY.exists():
        raise SystemExit("Missing editions/registry.json")

    data = json.loads(REGISTRY.read_text())

    editions = data.get("editions", [])

    if not editions:
        raise SystemExit("No Bible editions found")

    print("Bible Edition Registry Validation")
    print("--------------------------------")

    for edition in editions:
        missing = [field for field in REQUIRED_FIELDS if field not in edition]

        if missing:
            raise SystemExit(
                f"{edition.get('id', 'unknown')} missing: {missing}"
            )

        missing_features = [
            feature
            for feature in FEATURE_FIELDS
            if feature not in edition["features"]
        ]

        if missing_features:
            raise SystemExit(
                f"{edition['id']} missing features: {missing_features}"
            )

        print(f"✓ {edition['name']}")
        print(f"  Language: {edition['language']}")
        print(f"  Strong's: {'Enabled' if edition['features']['strongs'] else 'Disabled'}")
        print(f"  Red Letter: {'Enabled' if edition['features']['redLetter'] else 'Disabled'}")

    print("--------------------------------")
    print(f"Validated editions: {len(editions)}")


if __name__ == "__main__":
    main()
