#!/usr/bin/env python3
"""Analyze MIDI national-anthem files: extract melody fingerprints and embedded
text, then detect exact and near-duplicate melodies (transposition / tempo
invariant). Pure-python, no third-party dependencies.

Outputs:
  analysis.json   - per-file parsed info (notes, fingerprint, text)
  dedup_report.json - duplicate groups + canonical keep decision
"""
import os
import sys
import json
import glob
import struct
import hashlib
from collections import defaultdict

MIDI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "midi")


# --------------------------------------------------------------------------
# Minimal MIDI parser
# --------------------------------------------------------------------------
def read_vlq(data, pos):
    """Read a variable-length quantity. Returns (value, new_pos)."""
    value = 0
    while True:
        b = data[pos]
        pos += 1
        value = (value << 7) | (b & 0x7F)
        if not (b & 0x80):
            break
    return value, pos


def parse_midi(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"MThd":
        raise ValueError("not a MIDI file")
    header_len = struct.unpack(">I", data[4:8])[0]
    fmt, ntracks, division = struct.unpack(">HHH", data[8:14])
    pos = 8 + header_len
    tracks = []
    for _ in range(ntracks):
        if data[pos:pos + 4] != b"MTrk":
            # skip to next MTrk
            pos = data.find(b"MTrk", pos)
            if pos < 0:
                break
            pos += 4
        else:
            pos += 4
        tlen = struct.unpack(">I", data[pos:pos + 4])[0]
        pos += 4
        tracks.append(data[pos:pos + tlen])
        pos += tlen
    return fmt, division, tracks


def parse_track(track, division):
    """Return list of notes [(start_tick, pitch, duration_ticks)] and text events."""
    notes = []
    text_events = []
    open_notes = defaultdict(list)  # (channel, pitch) -> start tick
    tick = 0
    i = 0
    n = len(track)
    running_status = None
    while i < n:
        delta, i = read_vlq(track, i)
        tick += delta
        status = track[i]
        if status & 0x80:
            running_status = status
            i += 1
        else:
            status = running_status
        if status == 0xFF:
            meta_type = track[i]
            i += 1
            length, i = read_vlq(track, i)
            body = track[i:i + length]
            i += length
            if meta_type in (0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07):
                try:
                    text_events.append(body.decode("latin-1"))
                except Exception:
                    pass
            continue
        if status in (0xF0, 0xF7):
            length, i = read_vlq(track, i)
            i += length
            continue
        channel = status & 0x0F
        event_type = status & 0xF0
        if event_type == 0x90:
            pitch = track[i]; vel = track[i + 1]; i += 2
            if vel > 0:
                open_notes[(channel, pitch)].append(tick)
            else:
                # note off
                if open_notes[(channel, pitch)]:
                    start = open_notes[(channel, pitch)].pop()
                    notes.append((start, pitch, tick - start))
        elif event_type == 0x80:
            pitch = track[i]; i += 2
            if open_notes[(channel, pitch)]:
                start = open_notes[(channel, pitch)].pop()
                notes.append((start, pitch, tick - start))
        elif event_type in (0xA0, 0xB0, 0xE0):
            i += 2
        elif event_type in (0xC0, 0xD0):
            i += 1
        else:
            i += 1
    return notes, text_events


# --------------------------------------------------------------------------
# Fingerprint
# --------------------------------------------------------------------------
def quantize_dur(d, division):
    """Convert tick duration to beats then quantize to a coarse grid."""
    beats = d / division
    # snap to nearest multiple of 0.25, capped
    q = round(beats / 0.25) * 0.25
    if q <= 0:
        q = 0.25
    return q


def fingerprint(notes, division):
    """Build a transposition- and tempo-invariant token sequence.

    Each token = (pitch_diff_from_previous, quantized_duration). The first
    token uses pitch_diff=0. Pitch is relative to the FIRST note so the whole
    sequence is key-invariant.
    """
    if not notes:
        return []
    notes = sorted(notes, key=lambda x: (x[0], x[1]))
    seq = []
    prev_pitch = notes[0][1]
    for start, pitch, dur in notes:
        pdiff = pitch - prev_pitch
        q = quantize_dur(dur, division)
        seq.append((pdiff, q))
        prev_pitch = pitch
    return seq


def token_signature(seq):
    """Hash of the full token sequence (exact key/tempo-invariant match)."""
    return hashlib.md5(json.dumps(seq).encode()).hexdigest()


def near_key(seq):
    """Coarse bucket for near-duplicate search (first 14 tokens)."""
    return tuple(seq[:14])


def seq_similarity(a, b):
    """Normalized similarity of two integer/pair sequences via Levenshtein
    distance on the pitch-diff component."""
    if not a or not b:
        return 0.0
    # operate on pitch-diff tuples (ignore duration for similarity core,
    # but require duration close when comparing aligned tokens)
    la, lb = [t[0] for t in a], [t[0] for t in b]
    m, n = len(la), len(lb)
    if abs(m - n) > max(6, 0.25 * max(m, n)):
        return 0.0
    # Levenshtein
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        ai = la[i - 1]
        for j in range(1, n + 1):
            cost = 0 if ai == lb[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    dist = prev[n]
    sim = 1.0 - dist / max(m, n)
    return sim


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    files = sorted(glob.glob(os.path.join(MIDI_DIR, "*.mid")))
    print(f"Found {len(files)} MIDI files", file=sys.stderr)
    info = {}
    for path in files:
        name = os.path.basename(path)
        try:
            fmt, division, tracks = parse_midi(path)
            all_notes = []
            all_text = []
            for tr in tracks:
                ns, tx = parse_track(tr, division)
                all_notes.extend(ns)
                all_text.extend(tx)
            seq = fingerprint(all_notes, division)
            info[name] = {
                "size": os.path.getsize(path),
                "format": fmt,
                "division": division,
                "n_notes": len(all_notes),
                "n_tracks": len(tracks),
                "fingerprint_len": len(seq),
                "signature": token_signature(seq),
                "near_key": near_key(seq),
                "text": [t for t in all_text if t.strip()][:8],
                "seq": seq,
            }
        except Exception as e:
            info[name] = {"error": str(e)}

    # Exact duplicates by signature
    by_sig = defaultdict(list)
    for name, d in info.items():
        if "signature" in d:
            by_sig[d["signature"]].append(name)

    # Near duplicates: group by near_key then compare
    by_near = defaultdict(list)
    for name, d in info.items():
        if "near_key" in d:
            by_near[d["near_key"]].append(name)

    parent = {n: n for n in info}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # first, all exact matches are duplicates
    for sig, group in by_sig.items():
        if len(group) > 1:
            for x in group[1:]:
                union(group[0], x)

    # near matches within same near_key bucket
    near_pairs = []
    for key, group in by_near.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                sa, sb = info[a], info[b]
                if sa.get("fingerprint_len", 0) < 8 or sb.get("fingerprint_len", 0) < 8:
                    continue
                sim = seq_similarity(sa["seq"], sb["seq"])
                if sim >= 0.88:
                    union(a, b)
                    near_pairs.append((a, b, round(sim, 3)))

    # Build clusters
    clusters = defaultdict(list)
    for n in info:
        clusters[find(n)].append(n)
    clusters = {k: sorted(v) for k, v in clusters.items() if len(v) > 1}

    # Decide canonical keep per cluster: prefer the name that looks most
    # "clean" (shorter, no digits, ascii), else first alphabetically.
    def score_name(nm):
        base = nm[:-4]
        s = 0
        if any(c.isdigit() for c in base):
            s += 10
        s += len(base)
        return s
    report = {
        "total_files": len(files),
        "exact_duplicate_groups": {sig: g for sig, g in by_sig.items() if len(g) > 1},
        "near_pairs": near_pairs,
        "duplicate_clusters": clusters,
        "canonical_keep": {},
        "removed": [],
    }
    for root, members in clusters.items():
        keep = min(members, key=score_name)
        report["canonical_keep"][keep] = members
        for m in members:
            if m != keep:
                report["removed"].append(m)

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "analysis.json"), "w") as f:
        json.dump({k: {kk: vv for kk, vv in v.items() if kk != "seq"} for k, v in info.items()}, f, indent=2)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dedup_report.json"), "w") as f:
        json.dump(report, f, indent=2)

    print(f"Exact dup groups: {len(report['exact_duplicate_groups'])}", file=sys.stderr)
    print(f"Near pairs (sim>=0.88): {len(near_pairs)}", file=sys.stderr)
    print(f"Duplicate clusters: {len(clusters)}", file=sys.stderr)
    print(f"Unique files after dedup: {len(files) - len(report['removed'])}", file=sys.stderr)
    print(f"Removed (duplicates): {len(report['removed'])}", file=sys.stderr)


if __name__ == "__main__":
    main()
