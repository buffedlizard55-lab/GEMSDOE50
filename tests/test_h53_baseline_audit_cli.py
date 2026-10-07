from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASELINE = REPO / "evidence/h53-baseline-20261007.json"
SCRIPT = REPO / "scripts/h53_baseline_audit.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_baseline_reaudit_requires_separate_output_and_preserves_frozen_report() -> None:
    frozen_hash = _sha256(BASELINE)
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "--output" in result.stderr
    assert _sha256(BASELINE) == frozen_hash
