#!/usr/bin/env python3
"""Full-resolution uniqueness gate over the complete prior corpus (H59).

Candidates are binary rasters (or packed supports from the H59 build cache).
The corpus is every raster in ``.arena/prior_corpus`` (re-fetched by
``scripts/fetch_prior_corpus.py``: 50 hash-verified pins + every TIFF found in
the 54 sibling ``GEMSDOE`` repositories) plus ``docs/downloads`` and
``downloads`` of this repository.

Per (candidate, prior) pair, on the official 3,730 x 3,292 grid:

* ``exact_shared``      — dots of the candidate that are positive in the prior;
* ``jaccard``           — |C ∩ P| / |C ∪ P| on positive pixels;
* ``novel_2px``         — fraction of candidate dots with **no** prior positive
  pixel within 2 px (Euclidean; 13-offset disc). The metric's own tolerance is
  3 px, so a dot within 2 px of a prior dot competes for the same credit;
* ``block8_iou`` / ``block32_iou`` — IoU of 8 x 8 / 32 x 32 block occupancy,
  which catches shifted or resampled copies.

Priors with positive fraction above 5 % of the grid are continuous data fields,
not submission artifacts; they are listed but not gated. Byte-identical files
and identical positive masks are deduplicated (all names kept).

Gate (preregistration section 5): ``max jaccard < 0.5`` and ``min novel_2px > 0.5``
over all submission-like priors, with exemptions passed via ``--exempt`` (used
only for a superseding candidate's own never-submitted parent).

Post-hoc refinement (added after the first run, labelled as such in the
output): against *dense* priors (hundreds of thousands of positive pixels) the
raw 2-px proximity is mostly chance coverage — a 326-dot seismic file unrelated
to them was only 29 % "novel". So each pair also reports

* ``containment``  = exact_shared / candidate dots (a subset copy gives 1);
* ``chance_2px``   = fraction of off-catalogue footprint cells within 2 px of
  the prior's positives (the near-fraction a uniform dot set would have);
* ``excess_2px``   = ((1 - novel_2px) - chance_2px) / (1 - chance_2px), the
  chance-corrected proximity (a shifted copy gives ~1, independent placement ~0).

The refined gate is ``max jaccard < 0.5``, ``max containment < 0.5`` and
``max excess_2px < 0.5``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

REPO = Path(__file__).resolve().parents[1]
SHAPE = (3730, 3292)
MAX_POSITIVE_FRACTION = 0.05
DISC2 = [(dy, dx) for dy in range(-2, 3) for dx in range(-2, 3) if dy * dy + dx * dx <= 4]


def _occ(mask: np.ndarray, f: int) -> np.ndarray:
    h, w = mask.shape
    h2, w2 = h // f * f, w // f * f
    return mask[:h2, :w2].reshape(h2 // f, f, w2 // f, f).any(axis=(1, 3))


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    u = np.count_nonzero(a | b)
    return float(np.count_nonzero(a & b) / u) if u else 1.0


def _load_positive(path: Path) -> np.ndarray | None:
    try:
        with rasterio.open(path) as ds:
            if ds.shape != SHAPE:
                return None
            a = ds.read(1)
    except Exception:  # noqa: BLE001 — unreadable files are reported, not fatal
        return None
    return np.isfinite(a) & (a > 0)


def _candidate(spec: str) -> tuple[str, np.ndarray]:
    if "::" in spec:
        npz, key = spec.split("::", 1)
        with np.load(REPO / npz) as z:
            m = np.unpackbits(z[key])[: SHAPE[0] * SHAPE[1]].astype(bool).reshape(SHAPE)
        return f"{key} (from {npz})", m
    m = _load_positive(REPO / spec)
    if m is None:
        raise ValueError(f"cannot read candidate {spec}")
    return spec, m


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate", action="append", required=True,
                    help="raster path, or cache.npz::key for a packed support")
    ap.add_argument("--exempt", action="append", default=[],
                    help="candidate_label_substring=prior_filename_substring")
    ap.add_argument("--corpus", action="append", default=[".arena/prior_corpus", "docs/downloads", "downloads"])
    ap.add_argument("--out", default="evidence/h59_uniqueness.json")
    args = ap.parse_args()

    cands = [_candidate(c) for c in args.candidate]
    cand_info = []
    for label, m in cands:
        r, c = np.nonzero(m)
        cand_info.append({"label": label, "mask": m, "rows": r, "cols": c, "n": int(r.size),
                          "o8": _occ(m, 8), "o32": _occ(m, 32),
                          "mask_sha": hashlib.sha256(np.packbits(m.ravel()).tobytes()).hexdigest()})

    with rasterio.open(REPO / "data/grid/sample_submission.tif") as ds:
        valid = np.isfinite(ds.read(1))
    with rasterio.open(REPO / "data/grid/labels.tif") as ds:
        cat = ds.read(1) == 1
    domain = valid & (ndimage.distance_transform_edt(~cat) > 3.0)
    n_domain = int(domain.sum())
    disc = np.zeros((5, 5), dtype=bool)
    for dy, dx in DISC2:
        disc[dy + 2, dx + 2] = True

    files = []
    for d in dict.fromkeys(args.corpus):
        base = REPO / d
        if base.exists():
            files.extend(sorted(p for p in base.iterdir() if p.suffix.lower() in (".tif", ".tiff")))
    t0 = time.time()
    seen_bytes: dict[str, str] = {}
    seen_masks: dict[str, str] = {}
    rows: list[dict] = []
    skipped: list[dict] = []
    for p in files:
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if digest in seen_bytes:
            skipped.append({"file": str(p.relative_to(REPO)), "reason": f"byte-identical to {seen_bytes[digest]}"})
            continue
        seen_bytes[digest] = str(p.relative_to(REPO))
        pos = _load_positive(p)
        if pos is None:
            skipped.append({"file": str(p.relative_to(REPO)), "reason": "unreadable or not on the competition grid"})
            continue
        frac = float(pos.mean())
        if frac > MAX_POSITIVE_FRACTION or not pos.any():
            skipped.append({"file": str(p.relative_to(REPO)),
                            "reason": f"positive fraction {frac:.4f} (data field or empty), not gated"})
            continue
        msha = hashlib.sha256(np.packbits(pos.ravel()).tobytes()).hexdigest()
        if msha in seen_masks:
            skipped.append({"file": str(p.relative_to(REPO)), "reason": f"identical positive mask to {seen_masks[msha]}"})
            continue
        seen_masks[msha] = str(p.relative_to(REPO))
        o8, o32 = _occ(pos, 8), _occ(pos, 32)
        padded = np.pad(pos, 2)
        chance = float(np.count_nonzero(ndimage.binary_dilation(pos, structure=disc) & domain) / n_domain)
        entry = {"file": str(p.relative_to(REPO)), "prior_positive": int(pos.sum()),
                 "chance_2px": chance, "per_candidate": {}}
        for ci in cand_info:
            if msha == ci["mask_sha"]:
                entry["per_candidate"][ci["label"]] = {"self": True}
                continue
            near = np.zeros(ci["n"], dtype=bool)
            for dy, dx in DISC2:
                near |= padded[ci["rows"] + 2 + dy, ci["cols"] + 2 + dx]
            shared = int(pos[ci["rows"], ci["cols"]].sum())
            near_frac = float(near.mean()) if ci["n"] else 0.0
            entry["per_candidate"][ci["label"]] = {
                "exact_shared": shared,
                "jaccard": shared / max(ci["n"] + int(pos.sum()) - shared, 1),
                "containment": shared / max(ci["n"], 1),
                "novel_2px": 1.0 - near_frac,
                "excess_2px": (near_frac - chance) / (1.0 - chance) if chance < 1.0 else 0.0,
                "block8_iou": _iou(ci["o8"], o8),
                "block32_iou": _iou(ci["o32"], o32),
            }
        rows.append(entry)
    print(f"compared {len(rows)} distinct submission-like priors in {time.time()-t0:.0f}s; skipped {len(skipped)}")

    summary = {}
    for ci in cand_info:
        lab = ci["label"]
        exempt = [e.split("=", 1)[1] for e in args.exempt if e.split("=", 1)[0] in lab]
        vals = [(r["file"], r["per_candidate"][lab]) for r in rows
                if lab in r["per_candidate"] and not r["per_candidate"][lab].get("self")]
        gated = [(f, v) for f, v in vals if not any(x in f for x in exempt)]
        worst_j = max(gated, key=lambda fv: fv[1]["jaccard"]) if gated else None
        worst_n = min(gated, key=lambda fv: fv[1]["novel_2px"]) if gated else None
        worst_b = max(gated, key=lambda fv: fv[1]["block8_iou"]) if gated else None
        passed = bool(gated) and worst_j[1]["jaccard"] < 0.5 and worst_n[1]["novel_2px"] > 0.5
        worst_c = max(gated, key=lambda fv: fv[1]["containment"]) if gated else None
        worst_e = max(gated, key=lambda fv: fv[1]["excess_2px"]) if gated else None
        refined = (bool(gated) and worst_j[1]["jaccard"] < 0.5 and worst_c[1]["containment"] < 0.5
                   and worst_e[1]["excess_2px"] < 0.5)
        summary[lab] = {
            "dots": ci["n"],
            "priors_compared": len(vals),
            "exemptions": exempt,
            "max_jaccard": {"value": worst_j[1]["jaccard"], "prior": worst_j[0]} if worst_j else None,
            "min_novel_2px": {"value": worst_n[1]["novel_2px"], "prior": worst_n[0]} if worst_n else None,
            "max_block8_iou": {"value": worst_b[1]["block8_iou"], "prior": worst_b[0]} if worst_b else None,
            "priors_sharing_any_exact_pixel": sum(1 for _f, v in gated if v["exact_shared"] > 0),
            "gate": "max jaccard < 0.5 and min novel_2px > 0.5",
            "pass": passed,
            "max_containment": {"value": worst_c[1]["containment"], "prior": worst_c[0]} if worst_c else None,
            "max_excess_2px": {"value": worst_e[1]["excess_2px"], "prior": worst_e[0]} if worst_e else None,
            "refined_gate_post_hoc": "max jaccard < 0.5, max containment < 0.5, max excess_2px < 0.5",
            "refined_pass_post_hoc": refined,
        }
        print(json.dumps({lab: summary[lab]}, indent=1))

    out = {
        "schema": "gemsdoe50.h59-uniqueness.v1",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "corpus_dirs": list(dict.fromkeys(args.corpus)),
        "corpus_receipt": "evidence/h59_prior_corpus_receipt.json",
        "files_seen": len(files),
        "distinct_submission_like_priors": len(rows),
        "skipped": skipped,
        "summary": summary,
        "pairs": rows,
    }
    dest = REPO / args.out
    dest.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
