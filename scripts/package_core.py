#!/usr/bin/env python3
"""Shared packaging logic for the openttd-national-anthem volume split.

Used by both:
  - gen_volumes.py  (one-time generator that lays out the 6 local project dirs)
  - build_package.py (per-repo builder, run by CI / locally)

The 162 unique anthems are split into N_VOLUMES volumes of ~27 each. Each
volume is an independent OpenTTD Base Music set (its own .obm, GitHub repo and
Bananas package), so the full collection fits OpenTTD's 31-slot music system.
"""
import os
import sys
import json
import hashlib
import tarfile
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import country_map as cm

N_VOLUMES = 6
PKG_BASE = "openttd-national-anthem"
GITHUB_USER = "Maicarons"
VERSION = 1
VERSION_STR = "1.0"

# Fixed OpenTTD music slots (max 31).
SLOT_ORDER = (["theme"]
              + [f"old_{i}" for i in range(10)]
              + [f"new_{i}" for i in range(10)]
              + [f"ezy_{i}" for i in range(10)])


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sorted_items():
    """All (iso2, name, orig) tuples, sorted by ISO code, excluding dropped dups."""
    items = [(iso2, name, orig)
             for orig, (iso2, name) in cm.COUNTRY_MAP.items()
             if orig not in cm.DROP]
    items.sort(key=lambda x: x[0])
    return items


def volume_groups():
    """Split the sorted items into N_VOLUMES contiguous chunks."""
    items = sorted_items()
    per = (len(items) + N_VOLUMES - 1) // N_VOLUMES
    return [items[i * per:(i + 1) * per] for i in range(N_VOLUMES)]


def slot_assignment(midis):
    """Fill all 31 fixed slots deterministically.

    Bananas requires every base-music .obm to define all 31 [files] slots
    (theme + old_0..9 + new_0..9 + ezy_0..9). A volume with N unique anthems
    (here 27) fills the first N slots, then repeats earlier anthems to reach 31
    so no slot is missing. Every unique anthem still appears at least once.
    """
    return {SLOT_ORDER[i]: midis[i % len(midis)] for i in range(len(SLOT_ORDER))}


def repo_midis(repo_dir, volume):
    """Glob *.mid in a volume repo and resolve (iso2, name, orig) via the map."""
    files = [f[:-4] for f in os.listdir(repo_dir) if f.endswith(".mid")]
    out = []
    for iso2 in files:
        found = [(o, n) for o, (i2, n) in cm.COUNTRY_MAP.items()
                 if i2 == iso2 and o not in cm.DROP]
        if not found:
            continue
        orig, name = found[0]
        out.append((iso2, name, orig))
    out.sort(key=lambda x: x[0])
    return out


def write_obm(repo_dir, volume, slots):
    short = "ANT%d" % volume
    name = "national_anthems_vol%d" % volume
    lines = []
    lines.append("; National anthems of the world — Volume %d of %d (OpenTTD Base Music)"
                 % (volume, N_VOLUMES))
    lines.append("; Auto-generated; slot assignment is deterministic from ISO codes.")
    lines.append("")
    lines.append("[metadata]")
    lines.append("name              = %s" % name)
    lines.append("shortname         = %s" % short)
    lines.append("version           = %d" % VERSION)
    lines.append("description       = National anthems of the world — Volume %d of %d "
                 "(OpenTTD Base Music set)." % (volume, N_VOLUMES))
    lines.append("")
    lines.append("[files]")
    md5s, names = {}, {}
    for slot, (iso2, name_, orig) in slots.items():
        fname = iso2 + ".mid"
        lines.append("%-8s = %s" % (slot, fname))
        md5s[fname] = md5_of(os.path.join(repo_dir, fname))
        names[fname] = name_
    lines.append("")
    lines.append("[md5s]")
    for fname, h in md5s.items():
        lines.append("%-8s = %s" % (fname, h))
    lines.append("")
    lines.append("[names]")
    for fname, name_ in names.items():
        lines.append("%-8s = %s" % (fname, name_))
    lines.append("")
    lines.append("[origin]")
    lines.append("default      = National anthems of the world — OpenTTD Base Music, "
                 "Volume %d of %d." % (volume, N_VOLUMES))
    obm_name = "national_anthems_vol%d.obm" % volume
    with open(os.path.join(repo_dir, obm_name), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return obm_name


def make_tarball(repo_dir, volume, midis):
    dist = os.path.join(repo_dir, "dist")
    os.makedirs(dist, exist_ok=True)
    base = "%s-%d-%s" % (PKG_BASE, volume, VERSION_STR)
    tar_path = os.path.join(dist, base + ".tar")
    tgz_path = os.path.join(dist, base + ".tar.gz")
    for p in (tar_path, tgz_path):
        if os.path.exists(p):
            os.remove(p)
    # Bananas only accepts .obm, .mid and .txt files in a base-music package.
    members = [m[0] + ".mid" for m in midis] + [
        "national_anthems_vol%d.obm" % volume,
        "readme.txt", "license.txt", "changelog.txt",
    ]
    for mode, out in (("w", tar_path), ("w:gz", tgz_path)):
        with tarfile.open(out, mode) as tar:
            for m in members:
                fp = os.path.join(repo_dir, m)
                if os.path.exists(fp):
                    tar.add(fp, arcname=m)
    return tar_path, tgz_path, md5_of(tgz_path)


def write_metadata(repo_dir, volume, tar_md5):
    base = "%s-%d-%s" % (PKG_BASE, volume, VERSION_STR)
    meta = {
        "name": "%s-%d" % (PKG_BASE, volume),
        "version": VERSION_STR,
        "type": "base-music",
        "description": (
            "National anthems of the world — Volume %d of %d (OpenTTD Base Music). "
            "Part of a split collection; install all %d volumes for the complete set."
            % (volume, N_VOLUMES, N_VOLUMES)
        ),
        "authors": ["CountrySongs contributors"],
        "license": "CC BY 4.0",
        "url": "https://github.com/%s/%s-%d" % (GITHUB_USER, PKG_BASE, volume),
        "tags": ["music", "anthems", "midi", "national"],
        "dependency": [],
        "md5sum": tar_md5,
        "files": {"tar": base + ".tar.gz"},
    }
    with open(os.path.join(repo_dir, "dist", "bananas-metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta


def write_manifest(repo_dir, volume, midis):
    manifest = {
        "package": "%s-%d" % (PKG_BASE, volume),
        "version": VERSION,
        "volume": volume,
        "total_volumes": N_VOLUMES,
        "tracks": [{"iso2": m[0], "country": m[1], "file": m[0] + ".mid"} for m in midis],
    }
    with open(os.path.join(repo_dir, "dist", "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def write_docs(repo_dir, volume, midis, all_groups):
    n = N_VOLUMES
    today = datetime.date.today().isoformat()
    vol_list = "\n".join(
        "- Volume %d (%d anthems): https://github.com/%s/%s-%d"
        % (i + 1, len(g), GITHUB_USER, PKG_BASE, i + 1)
        for i, g in enumerate(all_groups)
    )
    countries = ", ".join(m[1] for m in midis)
    readme = f"""# National Anthems of the World — Volume {volume} (of {n})

Part of a split collection of national anthems packaged as **OpenTTD Base
Music** sets. The full collection is published across {n} volumes so every
anthem fits OpenTTD's music system.

This volume ({volume} of {n}) contains {len(midis)} anthems:

{countries}

## All volumes

{vol_list}

Install all {n} volumes in your `baseset/` directory to get the complete set.

## Installation

**Via Bananas:** search for `openttd-national-anthem` in the in-game Content
Download (each volume is a separate base-music package), or upload on
<https://bananas.openttd.org/package/base-music>.

**Manual:** copy `national_anthems_vol{volume}.obm` and all `*.mid` files into your
OpenTTD `baseset/` directory (e.g.
`%USERPROFILE%\\Documents\\OpenTTD\\baseset\\` on Windows or
`~/.openttd/baseset/` on Linux/macOS), then select the set in
*Game Options → Music*.

## How OpenTTD base music works

OpenTTD has exactly **31 fixed track slots** (`theme`, `old_0..9`, `new_0..9`,
`ezy_0..9`). This volume wires its {len(midis)} anthems into the first available
slots (theme + old + new + ezy). To use a different anthem for a slot, edit
`national_anthems_vol{volume}.obm`.

## Rebuilding (CI / local)

A GitHub Actions workflow builds the package on every push. Locally:

```
python scripts/build_package.py
```

This regenerates `national_anthems_vol{volume}.obm` and the
`dist/{PKG_BASE}-{volume}-{VERSION_STR}.tar.gz` Bananas package.

## Deduplication

A transposition/tempo-invariant melody analysis over the source files removed 1
byte-identical duplicate (Guinea-Bissau == Cape Verde). `estonia` and `finland`
share the same Pacius tune but are kept as separate countries. All other
anthems are distinct.

## License

**Creative Commons Attribution 4.0 International (CC BY 4.0).** You may share
and adapt for any purpose, including commercially, provided appropriate credit
is given. License text: <https://creativecommons.org/licenses/by/4.0/>

Generated {today}.
"""

    # README.md is for GitHub; readme.txt goes inside the Bananas package
    # (Bananas only recognises .txt documentation files, not .md).
    with open(os.path.join(repo_dir, "README.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(readme)
    with open(os.path.join(repo_dir, "readme.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(readme)

    license_text = (
        "Creative Commons Attribution 4.0 International (CC BY 4.0)\n"
        "\n"
        "You are free to:\n"
        "  Share  - copy and redistribute the material in any medium or format.\n"
        "  Adapt  - remix, transform, and build upon the material for any purpose,\n"
        "           even commercially.\n"
        "\n"
        "Under the following terms:\n"
        "  Attribution - You must give appropriate credit, provide a link to the\n"
        "  license, and indicate if changes were made.\n"
        "\n"
        "License: https://creativecommons.org/licenses/by/4.0/\n"
    )
    # LICENSE is for GitHub; license.txt goes inside the Bananas package.
    with open(os.path.join(repo_dir, "LICENSE"), "w", encoding="utf-8", newline="\n") as f:
        f.write(license_text)
    with open(os.path.join(repo_dir, "license.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(license_text)

    changelog = (
        "1.0 (initial release)\n"
        "  * Volume %d of %d: %d national-anthem MIDI files.\n"
        "  * Packaged as OpenTTD Base Music (national_anthems_vol%d.obm).\n"
        "  * Deduplicated source set (%d unique anthems across %d volumes).\n"
        "  * License: CC BY 4.0.\n"
    ) % (volume, n, len(midis), volume, len(sorted_items()), n)
    with open(os.path.join(repo_dir, "changelog.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(changelog)

    makefile = (
        "PKG     = %s\n"
        "VERSION = %s\n"
        "VOL     = %d\n"
        "DIR     = $(PKG)-$(VOL)-$(VERSION)\n"
        "TGZ     = $(DIR).tar.gz\n"
        "\n"
        "all:\n"
        "\tpython scripts/build_package.py\n"
        "\n"
        "clean:\n"
        "\trm -rf dist\n"
        "\n"
        ".PHONY: all clean\n"
    ) % (PKG_BASE, VERSION_STR, volume)
    with open(os.path.join(repo_dir, "Makefile"), "w", encoding="utf-8", newline="\n") as f:
        f.write(makefile)
