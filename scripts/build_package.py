#!/usr/bin/env python3
"""Per-repo OpenTTD Base Music builder.

Run inside a volume repo (e.g. openttd-national-anthem-3). Reads `volume.txt`,
regenerates `national_anthems_volN.obm`, and produces the Bananas package
`dist/openttd-national-anthem-N-1.0.tar.gz` plus metadata. Invoked by CI and
locally.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import package_core as pc


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(here)
    with open(os.path.join(repo, "volume.txt")) as f:
        volume = int(f.read().strip())
    midis = pc.repo_midis(repo, volume)
    slots = pc.slot_assignment(midis)
    pc.write_obm(repo, volume, slots)
    _, _, tgz_md5 = pc.make_tarball(repo, volume, midis)
    pc.write_metadata(repo, volume, tgz_md5)
    pc.write_manifest(repo, volume, midis)
    print("Built volume %d with %d tracks (md5 %s)" % (volume, len(midis), tgz_md5))


if __name__ == "__main__":
    main()
