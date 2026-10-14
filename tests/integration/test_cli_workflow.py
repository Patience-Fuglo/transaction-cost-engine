"""Stage 10 -- runs this repo's real CLI script as a subprocess,
exactly as a researcher would from the command line.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.slow
def test_run_cost_analysis_cli_produces_a_real_report(tmp_path):
    output_dir = tmp_path / "reports"
    result = subprocess.run(
        [sys.executable, "scripts/run_cost_analysis.py", "--output-dir", str(output_dir)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    assert (output_dir / "cost_report_portfolio.json").exists()
    assert (output_dir / "cost_report_portfolio.md").exists()
    assert "net expected return" in result.stdout.lower() or "net:" in result.stdout.lower()
