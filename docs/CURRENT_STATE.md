# Current State

## Repository purpose

This public repository is the canonical development and distribution source for **GD Bible — Grow Daily**.

It is separate from the private GrowDaily application repository.

The public Bible repository owns the GD Scripture source, editorial history, words-of-Jesus data, Strong's data, validation tools, and generated GD/GD+ Bible editions.

## Public editions

There are two public GD Bible editions:

### GD

**Grow Daily - Custom King James Version**

- complete 66-book GD custom Bible text
- 31,102 canonical verses
- documented GD wording revisions
- words spoken by Jesus displayed in Royal Purple `#9B00FF`
- no inline Strong's numbers

### GD+

**Grow Daily - Custom King James Version with Strong's Numbers**

- the same GD Scripture text as GD
- words spoken by Jesus displayed in Aqua `#00E5FF`
- integrated Hebrew and Greek Strong's numbers
- native e-Sword Strong's `<num>` markup remains clickable

## Canonical source

Authoritative Standard KJV text:

`source/growdaily/assets/bible/en_kjv.json`

Authoritative GD custom text:

`source/growdaily/assets/bible/kjv_modified.json`

Authoritative GD words-of-Jesus map:

`source/growdaily/assets/red_letters/jesus_speech_map_custom.json`

Strong's production alignment:

`source/growdaily/assets/strong/alignment/`

Generated e-Sword files are outputs and must never become the canonical editing source.

## Verified Bible structure

- Books: 66
- Chapters: 1,189
- Canonical verses: 31,102
- GD changed verses: 335
- Missing canonical verses: 0

## Words-of-Jesus status

- Custom speech-map entries: 2,055
- Unexpected zero-red entries: 0
- Known speech-boundary checks: PASS
- Projection failures: 0

GD uses Royal Purple.

GD+ uses Aqua so Jesus speech remains visually distinct from e-Sword's native Strong's-link rendering.

## Strong's status

Standard KJV production alignment:

- 31,102 verses
- 348,950 Strong's markers
- 0 fallback verses

GD+ custom projection:

- 31,102 projected verses
- 348,902 Strong's markers
- 0 plain fallback verses
- 0 projection failures

The 48-marker difference from the Standard KJV alignment is intentional: uncertain associations are not guessed across changed GD wording.

## e-Sword status

Current generated editions:

- `editions/esword/GD.bblx`
- `editions/esword/GD.bbli`
- `editions/esword/GD+.bblx`
- `editions/esword/GD+.bbli`

Actual iPad e-Sword HD testing has verified:

- GD imports successfully
- GD displays Jesus speech in Royal Purple
- GD contains no Strong's numbers
- GD+ imports successfully
- GD+ displays Jesus speech in Aqua
- GD+ Strong's numbers remain clickable

## GrowDaily application relationship

The private GrowDaily application lives in a separate repository:

`LionGateOS/GrowDaily`

The GrowDaily app may contain additional translations and application-specific Bible features.

Those app-specific translations and application architecture do not belong in this public GD Bible repository.

The synchronization direction is:

`GD Bible canonical source -> verified/generated Bible assets -> private GrowDaily application`

The GD Bible should not be independently edited in both repositories.

## Current work

The current repository-maintenance work is:

1. remove obsolete application/multi-language infrastructure from this public Bible repository
2. update surviving documentation to describe GD and GD+ accurately
3. validate the cleaned public repository
4. commit and push the boundary cleanup
5. later synchronize the verified GD Bible data into the private GrowDaily application
