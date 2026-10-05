# Strong's Data Explained

## Plain-language answer

The repository includes Strong's-number dictionary and Bible-alignment data
for the complete 66-book Bible.

It is not a digital reproduction of every page, index, and feature in the
printed *Strong's Exhaustive Concordance*.

## Included dictionary data

| Dictionary | Entries |
|---|---:|
| Hebrew | 8,674 |
| Greek | 5,523 |
| **Combined** | **14,197** |

The dictionary records provide information such as:

- Strong's number
- original Hebrew or Greek form
- transliteration
- short meaning or gloss
- KJV-related definition fields where available

## Production alignment

The active production alignment covers the complete canonical Bible.

| Standard KJV production item | Verified total |
|---|---:|
| Books | 66 |
| Canonical verses | 31,102 |
| Aligned verses | 31,102 |
| Strong's markers | 348,950 |
| Alignment fallback verses | 0 |
| Missing canonical verses | 0 |

The primary production source is the eBible.org King James Version USFM data
with embedded Hebrew and Greek Strong's identifiers.

Three verses absent from the primary eBible source use a documented CrossWire
source fallback. That is a **source-provenance fallback**, not an unresolved
alignment fallback. The combined production alignment still covers all 31,102
canonical verses.

## GD+ projection

GD+ projects the verified Standard KJV alignment onto the documented GD custom
wording without changing the GD Scripture text.

| GD+ projection item | Verified total |
|---|---:|
| Projected verses | 31,102 |
| Strong's markers retained | 348,902 |
| Plain fallback verses | 0 |
| Reconstruction failures | 0 |
| GD changed verses | 335 |
| Changed verses projected | 335 |

The 48-marker difference between the Standard KJV alignment and GD+ is
intentional.

Those markers are not transferred where changed GD wording makes the original
word association uncertain. The project does not invent or guess Strong's
associations merely to preserve a numerical total.

## Alignment rules

The production process follows these rules:

1. Canonical GD/KJV Scripture text remains authoritative for displayed text.
2. Strong's identifiers are transferred only where the word association is
   supported.
3. Translator-added or unmatched words are not assigned invented identifiers.
4. Generated verses must reconstruct the canonical displayed Scripture text.
5. Ambiguous associations remain unassigned rather than being presented as
   certain.

## e-Sword GD+ behavior

GD+ keeps Strong's identifiers in ordinary e-Sword markup such as:

`<num>G190</num>`

The Strong's tags are intentionally left unstyled so e-Sword can keep them
clickable.

Words spoken by Jesus in GD+ are rendered separately in Aqua `#00E5FF`.

## Data files

Primary project areas include:

- `source/growdaily/assets/strong/strong_dict_hebrew.json`
- `source/growdaily/assets/strong/strong_dict_greek.json`
- `source/growdaily/assets/strong/alignment/`
- `source/growdaily/docs/bible/EBIBLE_KJV_STRONGS_PROVENANCE.md`

Legacy Strong's assets may remain for historical compatibility and audit
purposes, but they are not the authoritative active GD+ production alignment
when newer Schema 2.0 production data supersedes them.

## Attribution and licensing

The bundled dictionary material includes data derived from Open Scriptures
Strong's sources.

Production Bible-alignment provenance is documented separately for the eBible
primary source and the limited CrossWire source fallback.

See the repository provenance and rights documentation before changing data
sources or publishing a packaged release.
