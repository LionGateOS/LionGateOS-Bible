# Complete Custom KJV Change Summary

## Plain-language overview

The LionGateOS Custom KJV preserves the complete 66-book, 31,100-verse
structure of the Standard KJV.

The custom edition applies 159 documented text operations across 137 unique
verses.

| Testament | Text operations | Unique verses |
|---|---:|---:|
| Old Testament | 28 | 16 |
| New Testament | 131 | 121 |
| **Total** | **159** | **137** |

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
| **Total** |  |  | **28** | **131** | **159** |

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

## Important counting note

The 159 total is not 159 different theological rewrites.

It consists of:

- primary wording replacements
- necessary pronoun changes
- one article adjustment
- one capitalization adjustment

There are 137 unique affected verses because some verses contain more than one
operation.

## Authoritative records

The machine-readable rule list and verse references are stored in:

`source/growdaily/docs/bible/TRANSFORMATION_MANIFEST.json`

Additional audit and verification records are stored in:

- `source/growdaily/docs/bible/KJV_CUSTOM_REVISION_AUDIT.md`
- `source/growdaily/docs/bible/KJV_CUSTOM_REVISION_VERIFICATION.txt`
- `source/growdaily/docs/bible/KJV_CUSTOM_REVISION_PLAN.md`
