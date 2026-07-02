# GrowDaily Custom KJV Revision Plan

## Base

This plan is for a GrowDaily custom revision based on the King James Version text already used in the app.

This is not an official King James Version, Cambridge edition, Oxford edition, NKJV, or publisher-owned Bible edition.

## Status

Planned / in verification.

Do not treat the modified Bible JSON as final until the script output is verified.

## Active File

Input file:

`assets/bible/en_kjv.json`

Planned output file:

`assets/bible/kjv_modified.json`

The original `en_kjv.json` must not be overwritten.

## Confirmed Modification Rules

### Holy Spirit wording

Replace:

`Holy Ghost`

with:

`Holy Spirit`

### Jesus Christ death verses

Use reverential capitalization for Jesus Christ's Spirit.

Specific verse rules:

- Matthew 27:50: `yielded up the ghost` → `yielded up His Spirit`
- Mark 15:37: `gave up the ghost` → `gave up His Spirit`
- Mark 15:39: `gave up the ghost` → `gave up His Spirit`
- Luke 23:46: `he gave up the ghost` → `He gave up His Spirit`
- John 19:30: `gave up the ghost` → `gave up His Spirit`

### Human death idioms

For all other people, use lowercase `his spirit`.

Replace:

- `gave up the ghost` → `gave up his spirit`
- `yielded up the ghost` → `yielded up his spirit`
- `give up the ghost` → `give up his spirit`
- `given up the ghost` → `given up his spirit`
- `giveth up the ghost` → `giveth up his spirit`
- `giving up of the ghost` → `giving up of the spirit`

Proper names must remain capitalized.

### Satan formatting

Replace exact word:

`Satan`

with:

`ꜱatan`

Do not alter Samson, Samuel, or any other name.

### Sonship wording

Replace:

`adoption` → `sonship`

Replace:

`Adoption` → `Sonship`

### Azazel wording

In Leviticus 16 only:

`scapegoat` → `Azazel`

### Passover wording

In Acts 12:4 only:

`Easter` → `Passover`

### Conduct wording

Replace:

`conversation` → `conduct`

Replace:

`Conversation` → `Conduct`

## Future Bible Work

These are not part of the first script unless separately verified:

- Deity pronoun capitalization for God and Jesus Christ
- Expanded red-letter mapping for Jesus Christ's words
- Strong's Concordance impact review
- Separate metadata/disclaimer handling
- Optional custom translation selector in GrowDaily

## Verification Requirements

Before using `kjv_modified.json` in the app, verify:

- Output still has exactly 66 books
- `Holy Ghost` count is 0
- lowercase `ghost` count is 0
- `Satan` count is 0
- `adoption` count is 0
- `scapegoat` count is 0
- `Easter` count is 0
- `conversation` count is 0
- all 19 ghost verses show correct before/after
- all 5 adoption verses show correct before/after
- all Leviticus 16 scapegoat verses show correct before/after
- Acts 12:4 shows correct before/after
- all 21 conversation verses show correct before/after

## Disclaimer Draft

GrowDaily Custom KJV Revision is a custom Bible text revision prepared for GrowDaily. It is based on the King James Version text where permitted and includes custom theological and wording corrections. It is not an official King James Version edition and is not affiliated with Cambridge University Press, Oxford University Press, Thomas Nelson, HarperCollins, or any Bible publisher.
