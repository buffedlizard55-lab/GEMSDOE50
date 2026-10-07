"""Tests for the H52-A D8 flow-routing / channel-deflection field (src/gems51/drainage.py).

These exercise `route_flow` and `channel_deflection` on small synthetic DEMs with a known
answer (a single straight valley, and a valley with a sharp dog-leg bend), so a regression in
the pysheds wiring or the circular-resultant statistic is caught without touching the real
100 m grid.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems51 import drainage


def _straight_valley(n: int = 50) -> np.ndarray:
    """A V-shaped valley running straight down the middle column, tilted so flow goes south."""
    yy, xx = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    cross_valley = np.abs(xx - n // 2).astype(np.float32) * 2.0   # V-shape, metres
    along_slope = (n - yy).astype(np.float32) * 0.5               # downhill to the south
    return (1000.0 + cross_valley + along_slope).astype(np.float32)


def _bent_valley(n: int = 50) -> np.ndarray:
    """A valley that runs south then takes a sharp right-angle bend to the east."""
    yy, xx = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    bend_row = n // 2
    # distance to the valley centreline: vertical segment above the bend, horizontal after it
    dist = np.where(
        yy <= bend_row,
        np.abs(xx - n // 2).astype(np.float32),
        np.abs(yy - bend_row).astype(np.float32),
    )
    base = 1000.0 + dist * 2.0
    # monotonic downhill gradient along the flow path (south, then east) so water keeps moving
    base += np.where(yy <= bend_row, (bend_row - yy).astype(np.float32), 0.0) * 0.3
    base += np.where(yy > bend_row, (n - xx).astype(np.float32) * -0.3 + 200.0, 0.0)
    return base.astype(np.float32)


def test_in1d_shim_is_installed_and_behaves_like_isin():
    drainage._ensure_in1d_shim()
    import numpy as np  # local, to see the (possibly patched) module state
    a = np.array([1, 2, 3, 4])
    b = np.array([2, 4])
    assert np.array_equal(np.in1d(a, b), np.isin(a, b))


def test_route_flow_runs_on_a_small_synthetic_dem_and_accumulates_downhill():
    dem = _straight_valley()
    valid = np.ones(dem.shape, dtype=bool)
    flow = drainage.route_flow(dem, valid)
    assert flow["fdir"].shape == dem.shape
    assert flow["acc"].shape == dem.shape
    # accumulation must increase somewhere downstream relative to the top of the valley
    top_strip = flow["acc"][2:5, :].max()
    bottom_strip = flow["acc"][-6:-2, :].max()
    assert bottom_strip >= top_strip


def _single_thread_channel(n: int, bend_row: int | None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A synthetic single-thread channel (one flow-contributing path, no lateral tributaries),
    expressed directly as D8 direction codes and accumulation, exactly as `route_flow` would
    hand them to `channel_deflection`. This isolates the deflection statistic itself from the
    pysheds pipeline and from the "every V-valley row is a confluence" confound documented in
    `docs/h52a-protocol.md` (a symmetric valley collects lateral tributary flow at every row,
    which is itself a legitimate confluence confound, but is not what this test is checking).
    `bend_row=None` means the channel runs straight south for its whole length; otherwise it
    runs south to `bend_row` and then turns to run east.
    """
    fdir = np.zeros((n, n), dtype=np.int64)
    acc = np.zeros((n, n), dtype=np.float64)
    col = n // 2
    cells = []
    if bend_row is None:
        cells = [(r, col) for r in range(n)]
    else:
        cells = [(r, col) for r in range(bend_row + 1)]
        cells += [(bend_row, c) for c in range(col + 1, n)]
    for i, (r, c) in enumerate(cells[:-1]):
        nr, nc = cells[i + 1]
        dr, dc = nr - r, nc - c
        # dirmap (N,NE,E,SE,S,SW,W,NW) -> (64,128,1,2,4,8,16,32); only S (4) and E (1) are used
        fdir[r, c] = 1 if (dr, dc) == (0, 1) else 4
        acc[r, c] = i + 1
    return fdir, acc, np.ones((n, n), dtype=bool)


def test_channel_deflection_is_higher_at_a_sharp_bend_than_on_a_straight_reach():
    n = 50
    fdir_straight, acc_straight, valid = _single_thread_channel(n, bend_row=None)
    fdir_bent, acc_bent, _ = _single_thread_channel(n, bend_row=n // 2)

    defl_straight = drainage.channel_deflection(fdir_straight, acc_straight, valid,
                                                channel_area_cells=1, min_neighbours=1)
    defl_bent = drainage.channel_deflection(fdir_bent, acc_bent, valid,
                                            channel_area_cells=1, min_neighbours=1)

    assert defl_straight["channel_cells"] > 0
    assert defl_bent["channel_cells"] > 0
    # a perfectly straight single-direction channel must be exactly zero deflection everywhere
    assert float(defl_straight["deflection"].max()) == 0.0
    # the bent channel must show a clear, non-zero deflection peak exactly at the bend: for a
    # 90 degree turn with an even split of neighbourhood directions either side of the corner,
    # the resultant length is cos(45 deg) so 1-R = 1 - cos(45 deg) ~= 0.293
    assert float(defl_bent["deflection"].max()) > 0.25
    bend_r, bend_c = n // 2, n // 2
    local = defl_bent["deflection"][bend_r - 2:bend_r + 3, bend_c - 2:bend_c + 3]
    assert float(local.max()) == float(defl_bent["deflection"].max())


def test_deflection_field_is_zero_outside_the_channel_mask():
    dem = _straight_valley()
    valid = np.ones(dem.shape, dtype=bool)
    flow = drainage.route_flow(dem, valid)
    defl = drainage.channel_deflection(flow["fdir"], flow["acc"], valid, channel_area_cells=5)
    assert np.all(defl["deflection"][~defl["channel_mask"]] == 0.0)
