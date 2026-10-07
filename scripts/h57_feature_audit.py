"""Single-channel audit of every H57 feature on the matched off-catalogue frame.

For each channel: the official DTI of the top-20,000 eligible pixels, the rank AUC
of the channel against the off-catalogue truth, and the same numbers for the whole
channel inside the study footprint.  The uniform control is a random draw of the
same size from the same eligible pool.  Purpose: state which evidence families
carry information about faults the catalogue does not contain, and which do not,
in numbers rather than adjectives.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems57 import frames as FR
from gems57.metric import evaluate

TOP_N = 20_000
UNIFORM_SEEDS = (11, 22, 33)


def auc(score: np.ndarray, truth: np.ndarray, domain: np.ndarray) -> float:
    """Rank AUC of ``score`` for ``truth`` restricted to ``domain`` (finite scores only)."""
    keep = domain & np.isfinite(score)
    score, truth = score[keep], truth[keep]
    s = score[truth]
    b = score[~truth]
    if s.size == 0 or b.size == 0:
        return float("nan")
    r = np.argsort(np.argsort(np.concatenate([s, b]), kind="stable"), kind="stable")
    return float((r[: s.size].sum() - s.size * (s.size - 1) / 2) / (s.size * b.size))


def main() -> int:
    from scipy import ndimage

    work = Path(".arena/h57")
    meta = json.loads((work / "feature_names.json").read_text())
    names = meta["names"]
    labels, footprint = FR.load_labels()
    positives = labels == 1
    catbuf = ndimage.distance_transform_edt(~positives) <= 3
    elig = footprint & ~catbuf
    truth = np.load(".arena/h57/truth_Smat.npy") & footprint
    cube = np.load(work / "features.npy", mmap_mode="r")

    pool_idx = np.flatnonzero(elig.ravel())
    uv = []
    for s in UNIFORM_SEEDS:
        i = np.random.default_rng(s).choice(pool_idx, TOP_N, replace=False)
        u = np.zeros(elig.size, bool)
        u[i] = True
        uv.append(evaluate(u.reshape(elig.shape).astype(np.float32), truth).dti)
    uni = float(np.mean(uv))

    rows = {}
    for j, nm in enumerate(names):
        a = np.asarray(cube[:, :, j], dtype=np.float32)
        finite = np.isfinite(a) & elig
        if int(finite.sum()) < TOP_N:
            rows[nm] = {"usable": False, "finite_in_pool": int(finite.sum())}
            continue
        v = np.where(finite, a, -np.inf).ravel()
        idx = np.argpartition(v, -TOP_N)[-TOP_N:]
        pred = np.zeros(v.size, bool)
        pred[idx] = True
        pred = pred.reshape(a.shape)
        pred &= elig
        parts = evaluate(pred.astype(np.float32), truth)
        rows[nm] = {
            "usable": True,
            "finite_in_pool": int(finite.sum()),
            "topn_dti": parts.dti,
            "topn_lift": parts.dti / uni,
            "auc_matched_frame": auc(a, truth & footprint, elig),
        }
        print(f"{nm:24s} topN DTI={parts.dti:.5f} lift={parts.dti/uni:.3f} auc={rows[nm]['auc_matched_frame']:.3f}")

    out = {"frame": "S_matched", "truth_px": int(truth.sum()), "top_n": TOP_N,
           "uniform_mean": uni, "uniform_values": uv, "channels": rows}
    Path("evidence/h57_feature_audit.json").write_text(json.dumps(out, indent=1))
    print("uniform mean", round(uni, 5), "-> wrote evidence/h57_feature_audit.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
