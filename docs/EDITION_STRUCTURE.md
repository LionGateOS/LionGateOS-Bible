# Edition Structure

## Canonical GD Bible source

Standard KJV reference text:

`source/growdaily/assets/bible/en_kjv.json`

GD custom Scripture text:

`source/growdaily/assets/bible/kjv_modified.json`

GD words-of-Jesus map:

`source/growdaily/assets/red_letters/jesus_speech_map_custom.json`

Strong's source and alignment data:

`source/growdaily/assets/strong/`

Revision and provenance documentation:

`source/growdaily/docs/bible/`

## GD

**Grow Daily - Custom King James Version**

GD is generated from the canonical GD custom Scripture text.

Features:

- 66 books
- 31,102 canonical verses
- documented GD wording revisions
- Jesus speech in Royal Purple `#9B00FF`
- no inline Strong's numbers

Generated outputs:

- `editions/esword/GD.bblx`
- `editions/esword/GD.bbli`

## GD+

**Grow Daily - Custom King James Version with Strong's Numbers**

GD+ uses the same underlying GD Scripture text.

Features:

- 66 books
- 31,102 canonical verses
- Jesus speech in Aqua `#00E5FF`
- integrated Strong's numbers
- native/plain e-Sword `<num>` markup for clickable Strong's lookup

Generated outputs:

- `editions/esword/GD+.bblx`
- `editions/esword/GD+.bbli`
- `editions/esword/GD+.metadata.json`

## Source-of-truth rule

Generated e-Sword files are distribution outputs.

They must never become the canonical editing source.

Canonical Bible changes must flow from the documented source assets through the generation and validation pipeline.
