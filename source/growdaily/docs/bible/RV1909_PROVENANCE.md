# Reina-Valera 1909 Provenance

## Translation

- Name: Santa Biblia — Reina-Valera 1909
- Runtime ID: `rv1909`
- Language: Spanish
- Status: Public Domain / Dominio Público
- Runtime asset: `assets/bible/es_rv1909.json`

## Authoritative source

The runtime asset was generated from the audited eBible USFX source:

- `spaRV1909_usfx.xml`
- SHA-256: `233b4d6a87f833ac809d0e68dcf9ba83c709d612e914a357a4f5473782b703a3`

Spanish book names were taken from:

- `BookNames.xml`
- SHA-256: `d5c5fd5e287728859156f6df80ba14a833a4fddb851484c658966e8f0761a916`

## Verified structure

- Books: 66
- Chapters: 1,189
- USFX verse markers: 31,102
- Real non-empty Spanish verse texts: 31,084
- Audited empty trailing placeholders: 18
- Duplicate coordinates: 0
- Unparsed verse markers: 0

The 18 empty markers exactly match the audited USFX-only coordinate
set. They contain no Scripture text and are not emitted as blank
runtime verses. No non-empty Spanish verse text is discarded.

## Generation

The deterministic generator is:

`scripts/bible/build_rv1909.py`

The generated asset uses the same runtime structure as the existing
GrowDaily Bible assets: an array of 66 books, each containing `name`,
`abbrev`, and chapter arrays.
