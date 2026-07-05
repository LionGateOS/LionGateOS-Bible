# Complete Custom KJV Change Summary

## Plain-language overview

The LionGateOS Custom KJV preserves the complete 66-book, 31,100-verse
structure of the Standard KJV.

The custom edition applies 368 documented text operations across 320 unique
verses.

| Testament | Text operations | Unique verses |
|---|---:|---:|
| Old Testament | 140 | 120 |
| New Testament | 228 | 200 |
| **Total** | **368** | **320** |

A text operation means one recorded replacement or adjustment. Several
operations can occur in the same verse.

For example, changing “gave up the ghost” to “gave up his spirit” requires both
a noun change and a nearby pronoun change.

## All documented rules

| Rule | Standard wording | Custom wording | Old Testament | New Testament | Total |
|---|---|---|---:|---:|---:|
| R001 | Holy Ghost | Holy Spirit | 0 | 90 | 90 |
| R002 | ghost | spirit | 11 | 3 | 14 |
| R003 | ghost | Spirit | 0 | 5 | 5 |
| R004 | the | his | 5 | 2 | 7 |
| R005 | the | His | 0 | 5 | 5 |
| R006 | the | my | 3 | 0 | 3 |
| R007 | the | her | 1 | 1 | 2 |
| R008 | the | their | 1 | 0 | 1 |
| R009 | he | He | 0 | 1 | 1 |
| R010 | adoption | sonship | 0 | 5 | 5 |
| R011 | scapegoat | Azazel | 4 | 0 | 4 |
| R014 | a | an | 1 | 0 | 1 |
| R012 | Easter | Passover | 0 | 1 | 1 |
| R013 | conversation | conduct | 2 | 18 | 20 |
| R015 | was | became | 1 | 0 | 1 |
| R016 | in his spirit | by his spirit | 1 | 0 | 1 |
| R017 | hate not | love less than | 0 | 1 | 1 |
| R018 | gentleness | kindness | 0 | 1 | 1 |
| R019 | longsuffering | patience and mercy | 0 | 1 | 1 |
| R020 | goodness | goodness and generosity | 0 | 1 | 1 |
| R021 | Meekness | Meekness and humility | 0 | 1 | 1 |
| R022 | temperance | self-control | 0 | 1 | 1 |
| R023 | prevent | precede | 6 | 1 | 7 |
| R024 | charity | love | 0 | 28 | 28 |
| R025 | devils | demons | 4 | 51 | 55 |
| R026 | corn | grain | 91 | 11 | 102 |
| R027 | unicorn | wild ox | 6 | 0 | 6 |
| R028 | an | a | 3 | 0 | 3 |
| **Total** |  |  | **140** | **228** | **368** |

## Explanation of the rules

### Holy Ghost to Holy Spirit

“Holy Ghost” is changed to “Holy Spirit” in 90 New Testament applications.

The title and meaning remain a reference to the Holy Spirit. The wording is
made consistent with commonly understood modern English usage.

### Ghost to spirit

In phrases describing death, “ghost” is changed to “spirit.”

Examples include forms of:

- gave up the ghost
- gave up his spirit
- gave up His Spirit
- give up my spirit
- gave up her spirit
- gave up their spirit

Companion pronoun and capitalization adjustments are recorded as separate
operations so every changed token remains auditable.

### Adoption to sonship

“Adoption” is changed to “sonship” in five New Testament locations.

### Scapegoat to Azazel

“Scapegoat” is changed to “Azazel” in four applications across three verses in
Leviticus.

One nearby article changes from “a” to “an” in Leviticus 16:10. That article
change is limited to this specific context and is not a global rule.

### Easter to Passover

“Easter” is changed to “Passover” in Acts 12:4.

### Conversation to conduct

“Conversation” is changed to “conduct” in 20 locations:

- 2 Old Testament applications
- 18 New Testament applications

This uses the present-day meaning of behavior or manner of life rather than
the modern meaning of spoken discussion.

### Verse-specific clarifying revisions

Eight additional controlled verse-specific revisions are documented in this
pass:

- Genesis 1:2: “was” becomes “became”
- Zechariah 7:12: “in his spirit” becomes “by his spirit”
- Luke 14:26: “hate not” becomes “love less than”
- Galatians 5:22: “longsuffering” becomes “patience and mercy”
- Galatians 5:22: “gentleness” becomes “kindness”
- Galatians 5:22: “goodness” becomes “goodness and generosity”
- Galatians 5:23: “Meekness” becomes “Meekness and humility”
- Galatians 5:23: “temperance” becomes “self-control”

### Additional global modernization rules

Five further controlled global rules are now documented:

- `prevent` becomes `precede` in 7 applications
- `charity` becomes `love` in 28 applications
- `devils` becomes `demons` in 55 applications
- `corn` becomes `grain` in 102 applications
- `unicorn` becomes `wild ox` in 6 applications

## Important counting note

The 368 total is not 368 different theological rewrites.

It consists of:

- primary wording replacements
- necessary pronoun changes
- controlled article adjustments
- one capitalization adjustment
- controlled phrase expansions where the modern wording needs more than one token

There are 320 unique affected verses because some verses contain more than one
operation.

## Authoritative records

The machine-readable rule list and verse references are stored in:

`source/growdaily/docs/bible/TRANSFORMATION_MANIFEST.json`

Additional audit and verification records are stored in:

- `source/growdaily/docs/bible/KJV_CUSTOM_REVISION_AUDIT.md`
- `source/growdaily/docs/bible/KJV_CUSTOM_REVISION_VERIFICATION.txt`
- `source/growdaily/docs/bible/KJV_CUSTOM_REVISION_PLAN.md`
