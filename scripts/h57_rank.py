"""Rank the H57 channel screens and print an auditable table.

Reads one or more `evidence/h57_screen*.json` files (the output of
`scripts/h57_screen.py`), de-duplicates by channel name with later files
winning, pools the four catalogue-holdout macrofolds (F2) into exact metric
counts, and optionally joins the F1 independent-population lift.

    python scripts/h57_rank.py evidence/h57_screen.json evidence/h57_screen_tf.json
"""

from __future__ import annotations

import json
import sys

MASSPREF = 30000


def fold_keys(row, prefix):
    return sorted(k for k in row if k.startswith(prefix))


def pooled_metric(row, prefix, mass):
    """Exact pooled metric counts over the folds selected by ``prefix``."""
    keys = fold_keys(row, prefix)
    if not keys:
        return None
    credit = dots = truth = 0.0
    for k in keys:
        s = row[k].get(f"m{mass}")
        if not s:
            continue
        credit += s["credit"]
        dots += s["n_dots"]
        truth += row[k]["truth_px"]
    if dots == 0:
        return None
    t = min(credit, truth)
    d = 0.2 * t + 0.2 * (dots - credit) + 0.8 * truth
    base = sum(row[k]["base_c_per_dot"] for k in keys) / len(keys)
    return {
        "folds": len(keys),
        "n_dots": dots,
        "credit": credit,
        "truth_px": truth,
        "c_per_dot": credit / dots,
        "base_c_per_dot": base,
        "lift": (credit / dots) / base if base else float("nan"),
        "coverage": t / truth if truth else 0.0,
        "dti": t / d if d > 0 else 0.0,
    }


def load(paths):
    seen = {}
    for p in paths:
        with open(p) as fh:
            d = json.load(fh)
        for r in d["rows"]:
            seen[r["channel"]] = r
    return seen


def main(paths, mass=MASSPREF, top=35, f1=True):
    rows = load(paths)
    table = []
    for ch, r in rows.items():
        p = pooled_metric(r, "F2_cat_", mass)
        if not p:
            continue
        f1r = pooled_metric(r, "F1_", mass) if f1 else None
        table.append((p["lift"], ch, p, f1r))
    table.sort(key=lambda z: z[0], reverse=True)

    print(f"channels with a complete F2 measurement: {len(table)}   (mass {mass})")
    head = (f"{'channel':44s} {'liftF2':>7s} {'c/dot':>7s} {'DTI_F2':>7s} {'covF2':>6s} "
            f"{'liftF1':>7s} {'DTI_F1':>7s}")
    print("\n" + head)
    print("-" * len(head))
    for lift, ch, p, f1r in table[:top]:
        f1l = f"{f1r['lift']:7.3f}" if f1r else "    n/a"
        f1d = f"{f1r['dti']:7.4f}" if f1r else "    n/a"
        print(f"{ch[:44]:44s} {lift:7.3f} {p['c_per_dot']:7.4f} {p['dti']:7.4f} "
              f"{p['coverage']:6.3f} {f1l} {f1d}")
    inc = [(i, ch, p) for i, (lift, ch, p, _) in enumerate(table, 1) if "INCUMBENT" in ch]
    for i, ch, p in inc:
        print(f"\n{ch}: rank {i}/{len(table)}, lift {p['lift']:.3f}, DTI {p['dti']:.4f}")


if __name__ == "__main__":
    args = sys.argv[1:] or ["evidence/h57_screen.json", "evidence/h57_screen_tf.json"]
    main(args)
