"""Spatially blocked supervised fault detector for H57.

The model is a gradient-boosted tree classifier over the H57 feature cube.  Folds
are the frozen spatial macrofolds from :mod:`gems59.frames`; the out-of-fold (OOF)
probability map is built by predicting each fold with a model that never saw that
fold.  The production map is the mean of the four fold models, so no pixel of the
final map is predicted by a model that was fitted on it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

RNG_SEED = 20261007
NEG_PER_FOLD = 150_000
MAX_ITER = 300


@dataclass
class FoldResult:
    fold: int
    name: str
    auc_L: float
    n_train_pos: int
    n_train_neg: int
    feature_importance: dict[str, float] = field(default_factory=dict)


def _load_cube(path: Path | str) -> np.memmap:
    return np.load(path, mmap_mode="r")


def _sample_training(
    cube: np.memmap,
    train_mask: np.ndarray,
    positives: np.ndarray,
    rng: np.random.Generator,
    n_neg: int,
) -> tuple[np.ndarray, np.ndarray]:
    pos_idx = np.flatnonzero((positives & train_mask).ravel())
    neg_pool = np.flatnonzero(train_mask.ravel())
    neg_idx = rng.choice(neg_pool, size=min(n_neg, len(neg_pool)), replace=False)
    idx = np.concatenate([pos_idx, neg_idx])
    rows, cols = np.unravel_index(idx, positives.shape)
    x = np.asarray(cube[rows, cols, :], dtype=np.float32)
    y = np.zeros(len(idx), dtype=np.int8)
    y[: len(pos_idx)] = 1
    return x, y


def _auc(y: np.ndarray, score: np.ndarray) -> float:
    order = np.argsort(score, kind="stable")
    ranks = np.empty(len(score), dtype=np.float64)
    ranks[order] = np.arange(len(score), dtype=np.float64)
    npos = int(y.sum())
    nneg = len(y) - npos
    if npos == 0 or nneg == 0:
        return float("nan")
    return float((ranks[y == 1].sum() - npos * (npos - 1) / 2.0) / (npos * nneg))


def train_blocked(
    cube_path: Path | str,
    positives: np.ndarray,
    footprint: np.ndarray,
    fold: np.ndarray,
    fold_names: list[str],
    *,
    seed: int = RNG_SEED,
    n_neg: int = NEG_PER_FOLD,
    max_iter: int = MAX_ITER,
    progress=print,
) -> tuple[np.ndarray, np.ndarray, list[FoldResult], list[str]]:
    """Train one model per fold and return ``(oof, ensemble, results, names)``.

    ``oof`` is the out-of-fold probability map (value at a pixel of fold *k* comes
    from the model trained without fold *k*).  ``ensemble`` is the mean of the four
    fold models over the whole grid.
    """
    from sklearn.ensemble import HistGradientBoostingClassifier

    cube = _load_cube(cube_path)
    meta = json.loads((Path(cube_path).parent / "feature_names.json").read_text())
    names = meta["names"]
    h, w = positives.shape
    rng = np.random.default_rng(seed)

    oof = np.zeros((h, w), dtype=np.float32)
    ensemble = np.zeros((h, w), dtype=np.float32)
    results: list[FoldResult] = []

    eval_rng = np.random.default_rng(seed + 1)
    eval_pool = np.flatnonzero(footprint.ravel())
    eval_idx = eval_rng.choice(eval_pool, size=min(400_000, len(eval_pool)), replace=False)
    eval_rows, eval_cols = np.unravel_index(eval_idx, positives.shape)
    x_eval = np.asarray(cube[eval_rows, eval_cols, :], dtype=np.float32)
    y_eval = positives[eval_rows, eval_cols].astype(np.int8)

    for k, name in enumerate(fold_names):
        train_mask = (fold >= 0) & (fold != k)
        x, y = _sample_training(cube, train_mask, positives, rng, n_neg)
        clf = HistGradientBoostingClassifier(
            max_iter=max_iter,
            learning_rate=0.06,
            max_leaf_nodes=31,
            min_samples_leaf=40,
            l2_regularization=1.0,
            early_stopping=False,
            random_state=seed + k,
        )
        clf.fit(x, y.astype(np.int32))
        results.append(
            FoldResult(
                fold=k,
                name=name,
                auc_L=_auc(y_eval, clf.predict_proba(x_eval)[:, 1]),
                n_train_pos=int(y.sum()),
                n_train_neg=int((y == 0).sum()),
            )
        )
        progress(
            f"  fold {name}: train pos={results[-1].n_train_pos} neg={results[-1].n_train_neg} "
            f"sample-AUC(L)={results[-1].auc_L:.4f}"
        )

        # full-grid prediction, in row chunks, written where this fold is unseen
        chunk = 128
        for r0 in range(0, h, chunk):
            r1 = min(r0 + chunk, h)
            block = np.asarray(cube[r0:r1]).reshape(-1, cube.shape[-1])
            pr = clf.predict_proba(block)[:, 1].astype(np.float32).reshape(r1 - r0, w)
            ensemble[r0:r1] += pr / len(fold_names)
            sel = (fold[r0:r1] == k) & footprint[r0:r1]
            oof[r0:r1][sel] = pr[sel]
        del clf

    return oof, ensemble, results, names


def permutation_importance(
    cube_path: Path | str,
    positives: np.ndarray,
    footprint: np.ndarray,
    fold: np.ndarray,
    fold_names: list[str],
    fold_index: int,
    *,
    seed: int = RNG_SEED,
    n_neg: int = NEG_PER_FOLD,
    max_iter: int = 120,
) -> dict[str, float]:
    """Block-permutation importance on one held-out fold (audit instrument only)."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    cube = _load_cube(cube_path)
    meta = json.loads((Path(cube_path).parent / "feature_names.json").read_text())
    names = meta["names"]
    rng = np.random.default_rng(seed)
    train_mask = (fold >= 0) & (fold != fold_index)
    x, y = _sample_training(cube, train_mask, positives, rng, n_neg)
    clf = HistGradientBoostingClassifier(max_iter=max_iter, random_state=seed)
    clf.fit(x, y.astype(np.int32))

    hold = fold == fold_index
    hrows, hcols = np.unravel_index(np.flatnonzero((positives & hold).ravel()), positives.shape)
    if len(hrows) > 20_000:
        pick = rng.choice(len(hrows), 20_000, replace=False)
        hrows, hcols = hrows[pick], hcols[pick]
    negrows, negcols = np.unravel_index(
        rng.choice(np.flatnonzero((footprint & hold).ravel()), 20_000, replace=False),
        positives.shape,
    )
    rows = np.concatenate([hrows, negrows])
    cols = np.concatenate([hcols, negcols])
    yy = np.concatenate([np.ones(len(hrows), np.int8), np.zeros(len(negrows), np.int8)])
    base = np.asarray(cube[rows, cols, :], dtype=np.float32)
    ref = _auc(yy, clf.predict_proba(base)[:, 1])

    out: dict[str, float] = {}
    for j, nm in enumerate(names):
        perm = base.copy()
        perm[:, j] = perm[rng.permutation(len(perm)), j]
        out[nm] = float(ref - _auc(yy, clf.predict_proba(perm)[:, 1]))
    return out
