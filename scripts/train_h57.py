"""Train the H57 blocked detector and save OOF + ensemble probability maps."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems57 import frames as FR  # noqa: E402
from gems57 import model as M  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=".arena/h57")
    args = ap.parse_args()
    work = Path(args.work)

    labels, footprint = FR.load_labels()
    positives = labels == 1
    fold, fold_names = FR.macrofolds(footprint)

    t0 = time.time()
    oof, ensemble, results, names = M.train_blocked(
        work / "features.npy", positives, footprint, fold, fold_names
    )
    np.save(work / "prob_oof.npy", oof.astype(np.float32))
    np.save(work / "prob_ensemble.npy", ensemble.astype(np.float32))

    # OOF skill on held-out label blocks, and on the off-catalogue proxy.
    from gems57.metric import evaluate

    truth_S = FR.load_sgmc_offcatalogue()

    def block_auc(mask: np.ndarray, truth: np.ndarray) -> float:
        v = ensemble[mask]
        y = truth[mask].astype(np.int8)
        return M._auc(y, v)

    audit = {
        "seed": M.RNG_SEED,
        "max_iter": M.MAX_ITER,
        "n_features": len(names),
        "folds": [
            {"name": r.name, "auc_L_sample": r.auc_L, "train_pos": r.n_train_pos}
            for r in results
        ],
        "oof_auc_L_blocks": [block_auc(fold == k, positives) for k in range(len(fold_names))],
        "oof_auc_S_blocks": [block_auc(fold == k, truth_S) for k in range(len(fold_names))],
        "oof_auc_L_all": block_auc(footprint, positives),
        "oof_auc_S_all": block_auc(footprint, truth_S),
        "seconds": round(time.time() - t0, 1),
    }

    # DTI of the raw probability field (no threshold/skeleton) is not meaningful
    # for the official metric; instead report top-N selection on both frames.
    def topn_dti(field: np.ndarray, truth: np.ndarray, n: int, elig: np.ndarray) -> float:
        a = np.where(elig, np.nan_to_num(field, nan=-1.0), -np.inf)
        idx = np.argpartition(a.ravel(), -n)[-n:]
        pos = np.zeros(a.size, bool)
        pos[idx] = True
        return evaluate(pos.reshape(field.shape).astype(np.float32), truth).dti

    from scipy import ndimage

    catbuf = ndimage.distance_transform_edt(~positives) <= 3
    elig = footprint & ~catbuf
    audit["topn_dti_ensemble"] = {
        "S": {str(n): topn_dti(ensemble, truth_S, n, elig) for n in (10_000, 20_000, 35_000, 60_000)},
        "L": {str(n): topn_dti(ensemble, positives, n, elig) for n in (10_000, 20_000, 35_000, 60_000)},
    }

    (work / "train_audit.json").write_text(json.dumps(audit, indent=1))
    print(json.dumps(audit, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
