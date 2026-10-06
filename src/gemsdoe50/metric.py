from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree


@dataclass(frozen=True)
class DTIComponents:
    score: float
    tp_weight: float
    fp_weight: float
    fn_weight: float
    truth_cells: int
    prediction_cells: int
    alpha: float
    beta: float
    radius_m: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def weighted_tversky_from_components(
    tp_weight: float,
    fp_weight: float,
    fn_weight: float,
    *,
    alpha: float = 0.2,
    beta: float = 0.8,
    epsilon: float = 1e-9,
) -> float:
    """Apply the official Tversky ratio to already distance-weighted counts."""
    values = np.asarray([tp_weight, fp_weight, fn_weight, alpha, beta, epsilon], dtype=np.float64)
    if np.any(~np.isfinite(values)):
        raise ValueError("Tversky components and parameters must be finite")
    if min(tp_weight, fp_weight, fn_weight) < 0:
        raise ValueError("Tversky components must be non-negative")
    if alpha < 0 or beta < 0 or epsilon <= 0:
        raise ValueError("alpha and beta must be non-negative and epsilon must be positive")
    denominator = tp_weight + alpha * fp_weight + beta * fn_weight + epsilon
    return float(tp_weight / denominator) if denominator > 0 else 0.0


def distance_weighted_tversky(
    truth: np.ndarray,
    prediction: np.ndarray,
    *,
    pixel_size_m: float = 100.0,
    radius_m: float = 300.0,
    alpha: float = 0.2,
    beta: float = 0.8,
    truth_eval_mask: np.ndarray | None = None,
    prediction_eval_mask: np.ndarray | None = None,
) -> DTIComponents:
    """Compute the registered triangular-kernel, distance-weighted Tversky score.

    ``truth`` is binary. ``prediction`` is finite in [0, 1], with zero meaning
    no predicted trace. A truth cell receives the maximum nearby prediction
    confidence times a linear 0--300 m kernel; prediction confidence is
    discounted by proximity to the nearest truth cell. Optional evaluation
    masks let a spatial block use a small distance halo without double-counting
    neighboring blocks: all halo points provide context, while only selected
    truth/prediction cells contribute counts. Pixels are not treated as
    independent samples.
    """
    truth = np.asarray(truth, dtype=bool)
    prediction = np.asarray(prediction, dtype=np.float64)
    if truth.shape != prediction.shape:
        raise ValueError(f"shape mismatch: truth {truth.shape}, prediction {prediction.shape}")
    if pixel_size_m <= 0 or radius_m <= 0:
        raise ValueError("pixel_size_m and radius_m must be positive")
    if alpha < 0 or beta < 0:
        raise ValueError("alpha and beta must be non-negative")
    if np.any(~np.isfinite(prediction)):
        raise ValueError("prediction contains NaN or infinity; mask/fill nodata before scoring")
    if np.any((prediction < 0) | (prediction > 1)):
        raise ValueError("prediction values must be in [0, 1]")

    prediction = np.clip(prediction, 0.0, 1.0)
    if truth_eval_mask is None:
        truth_eval = truth
    else:
        truth_eval_mask = np.asarray(truth_eval_mask, dtype=bool)
        if truth_eval_mask.shape != truth.shape:
            raise ValueError("truth evaluation mask shape mismatch")
        truth_eval = truth & truth_eval_mask
    if prediction_eval_mask is None:
        prediction_eval = prediction > 0
    else:
        prediction_eval_mask = np.asarray(prediction_eval_mask, dtype=bool)
        if prediction_eval_mask.shape != prediction.shape:
            raise ValueError("prediction evaluation mask shape mismatch")
        prediction_eval = (prediction > 0) & prediction_eval_mask
    truth_coords = np.argwhere(truth_eval)
    pred_mask = prediction > 0
    pred_coords = np.argwhere(pred_mask)
    pred_values = prediction[pred_mask]

    best_match = np.zeros(truth_coords.shape[0], dtype=np.float64)
    if truth_coords.size and pred_coords.size:
        tree = cKDTree(pred_coords.astype(np.float64) * pixel_size_m)
        neighbors = tree.query_ball_point(
            truth_coords.astype(np.float64) * pixel_size_m,
            r=radius_m + 1e-9,
        )
        for idx, candidate_ids in enumerate(neighbors):
            if not candidate_ids:
                continue
            ids = np.asarray(candidate_ids, dtype=np.int64)
            delta = (pred_coords[ids] - truth_coords[idx]) * pixel_size_m
            distance = np.sqrt(np.sum(delta * delta, axis=1))
            kernel = np.maximum(0.0, 1.0 - distance / radius_m)
            best_match[idx] = float(np.max(pred_values[ids] * kernel))

    tp_weight = float(np.sum(best_match))
    fn_weight = float(np.sum(1.0 - best_match))
    if np.any(truth):
        # ``truth`` may include halo context outside truth_eval_mask. It must still reduce
        # nearby FP cost even when this subtile contains no truth cells of its own.
        nearest_truth_distance = distance_transform_edt(
            ~truth, sampling=(pixel_size_m, pixel_size_m)
        )
        truth_support = np.maximum(0.0, 1.0 - nearest_truth_distance / radius_m)
    else:
        truth_support = np.zeros(truth.shape, dtype=np.float64)
    fp_weight = float(np.sum(prediction[prediction_eval] * (1.0 - truth_support[prediction_eval])))
    epsilon = 1e-9
    score = weighted_tversky_from_components(
        tp_weight,
        fp_weight,
        fn_weight,
        alpha=alpha,
        beta=beta,
        epsilon=epsilon,
    )
    return DTIComponents(
        score=score,
        tp_weight=tp_weight,
        fp_weight=fp_weight,
        fn_weight=fn_weight,
        truth_cells=int(truth_coords.shape[0]),
        prediction_cells=int(np.count_nonzero(prediction_eval)),
        alpha=float(alpha),
        beta=float(beta),
        radius_m=float(radius_m),
    )
