# e-Sword Export Notes

## Confirmed local desktop export

The current local exporter is:

`scripts/build_esword_bblx.py`

It generates:

- `editions/esword/liongateos-custom-kjv.bblx`
- `editions/esword/liongateos-custom-kjv.metadata.json`

The `.bblx` file keeps the canonical 66-book, 31,100-verse coordinate system
unchanged.

The metadata sidecar adds seven-division presentation/search labels only. It
does not merge books, renumber verses, or alter Strong's-compatible canonical
references.

## Seven presentation divisions

1. Torah
2. History
3. Wisdom
4. Major Prophets
5. Minor Prophets
6. Gospels and Acts
7. Letters and Revelation

## iPad / iOS status

Current repository evidence does not document a native iPad/iOS e-Sword module
writer format.

The official e-Sword Extras page states that custom modules for Apple/Android
device use go through the **e-Sword PC Module Conversion Utility**.

Because of that, the current blocker is:

- desktop `.bblx` output is locally buildable and verifiable
- iPad/iOS output appears to require the official conversion utility path
- no local specification or repo-owned converter exists here for a second
  direct-export writer

Until that conversion path is available in a reproducible way, this repository
should not fake an iPad/iOS exporter.
