"""Invariants of the emitter, checked against brute force."""

import numpy as np

from gems50 import emitter, metric


def brute_force_marginal(belief, dots):
    """Independent computation of expected marginal credit for the first free pixel."""
    H, W = belief.shape
    off, w = emitter.kernel_offsets()
    C = np.zeros_like(belief, dtype=np.float32)
    for r, c in np.argwhere(dots):
        for (dy, dx), k in zip(off, w):
            rr, cc = r + dy, c + dx
            if 0 <= rr < H and 0 <= cc < W:
                C[rr, cc] = max(C[rr, cc], k)
    out = np.zeros_like(belief)
    for r in range(H):
        for c in range(W):
            tot = 0.0
            for (dy, dx), k in zip(off, w):
                rr, cc = r + dy, c + dx
                if 0 <= rr < H and 0 <= cc < W:
                    tot += max(k - C[rr, cc], 0.0) * belief[rr, cc]
            out[r, c] = tot
    return out


def test_kernel_offsets_match_the_metric_kernel():
    off, w = emitter.kernel_offsets()
    # offsets with k > 0: |d| < 3 px  ->  1 + 4 + 4 + 4 + 8 + 4 = 25
    assert len(off) == len(w) == 25
    d = np.hypot(off[:, 0], off[:, 1])
    assert np.allclose(w, metric.kernel(d))
    assert np.all(d < 3.0)
    assert np.all(w > 0.0)


def test_delta_t_matches_brute_force():
    rng = np.random.default_rng(3)
    belief = (rng.random((30, 30)) < 0.2).astype(np.float32) * rng.random((30, 30)).astype(np.float32)
    dots = np.zeros((30, 30), dtype=bool)
    dots[10, 10] = True
    off, w = emitter.kernel_offsets()
    C = np.zeros_like(belief, dtype=np.float32)
    for (dy, dx), k in zip(off, w):
        C[10 + dy, 10 + dx] = k
    rows = np.arange(5, 25)
    cols = np.arange(5, 25)
    got = emitter.delta_t(belief, C, off, w, rows, cols)
    want = brute_force_marginal(belief, dots)[5:25, 5:25].diagonal()
    assert np.allclose(got, want, atol=1e-5)


def test_emitter_places_dots_on_the_belief_maximum_and_respects_the_bar():
    belief = np.zeros((60, 60), dtype=np.float32)
    belief[30, 30] = 1.0
    belief[10, 10] = 0.5
    dots = emitter.emit(belief, target_score=0.32, max_dots=50)
    assert dots[30, 30]
    # marginal bar at s=0.32 is 0.064: the isolated 0.5 pixel yields ~ 0.5*sum(k)
    assert dots[10, 10]


def test_emitter_stops_when_no_pixel_beats_the_bar():
    belief = np.full((40, 40), 1e-4, dtype=np.float32)
    dots = emitter.emit(belief, target_score=0.32, max_dots=1000)
    assert dots.sum() == 0


def test_expected_credit_is_monotone_in_belief_scale():
    rng = np.random.default_rng(5)
    belief = np.zeros((80, 80), dtype=np.float32)
    belief[rng.integers(0, 80, 30), rng.integers(0, 80, 30)] = 1.0
    dots = emitter.emit(belief, target_score=0.10, max_dots=40)
    c1 = emitter.expected_credit(belief, dots)
    c2 = emitter.expected_credit(belief * 0.5, dots)
    assert c2 < c1
    assert dots.sum() > 0
