# National Anthems of the World — Volume 6 (of 6)

Part of a split collection of national anthems packaged as **OpenTTD Base
Music** sets. The full collection is published across 6 volumes so every
anthem fits OpenTTD's music system.

This volume (6 of 6) contains 27 anthems:

Senegal, Somalia, Suriname, Sao Tome and Principe, El Salvador, Syria, Eswatini, Chad, Togo, Thailand, Tunisia, Tonga, Turkey, Trinidad and Tobago, Tuvalu, Tanzania, Ukraine, Uganda, United States, Uruguay, Vatican City, Saint Vincent and the Grenadines, Venezuela, Vietnam, Vanuatu, Unknown (manislef), Yemen

## All volumes

- Volume 1 (27 anthems): https://github.com/Maicarons/openttd-national-anthem-1
- Volume 2 (27 anthems): https://github.com/Maicarons/openttd-national-anthem-2
- Volume 3 (27 anthems): https://github.com/Maicarons/openttd-national-anthem-3
- Volume 4 (27 anthems): https://github.com/Maicarons/openttd-national-anthem-4
- Volume 5 (27 anthems): https://github.com/Maicarons/openttd-national-anthem-5
- Volume 6 (27 anthems): https://github.com/Maicarons/openttd-national-anthem-6

Install all 6 volumes in your `baseset/` directory to get the complete set.

## Installation

**Via Bananas:** search for `openttd-national-anthem` in the in-game Content
Download (each volume is a separate base-music package), or upload on
<https://bananas.openttd.org/package/base-music>.

**Manual:** copy `national_anthems_vol6.obm` and all `*.mid` files into your
OpenTTD `baseset/` directory (e.g.
`%USERPROFILE%\Documents\OpenTTD\baseset\` on Windows or
`~/.openttd/baseset/` on Linux/macOS), then select the set in
*Game Options → Music*.

## How OpenTTD base music works

OpenTTD has exactly **31 fixed track slots** (`theme`, `old_0..9`, `new_0..9`,
`ezy_0..9`). This volume wires its 27 anthems into the first available
slots (theme + old + new + ezy). To use a different anthem for a slot, edit
`national_anthems_vol6.obm`.

## Rebuilding (CI / local)

A GitHub Actions workflow builds the package on every push. Locally:

```
python scripts/build_package.py
```

This regenerates `national_anthems_vol6.obm` and the
`dist/openttd-national-anthem-6-1.0.tar.gz` Bananas package.

## Deduplication

A transposition/tempo-invariant melody analysis over the source files removed 1
byte-identical duplicate (Guinea-Bissau == Cape Verde). `estonia` and `finland`
share the same Pacius tune but are kept as separate countries. All other
anthems are distinct.

## License

**Creative Commons Attribution 4.0 International (CC BY 4.0).** You may share
and adapt for any purpose, including commercially, provided appropriate credit
is given. License text: <https://creativecommons.org/licenses/by/4.0/>

Generated 2026-10-31.
