"""
Test Suite: Smoke Testing & App Entrypoint Validation
"""

import sys
import importlib
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


def test_module_imports():
    modules = [
        "pipeline.transform",
        "pipeline.ingest",
        "pipeline.validate",
        "analysis.freq_testing",
        "analysis.bayesian_analysis",
        "analysis.power_analysis",
        "analysis.segment_analysis"
    ]
    for m in modules:
        mod = importlib.import_module(m)
        assert mod is not None, f"Failed to import {m}"


def test_dashboard_files_exist():
    pages = [
        BASE_DIR / "dashboard" / "app.py",
        BASE_DIR / "dashboard" / "pages" / "01_experiment_overview.py",
        BASE_DIR / "dashboard" / "pages" / "02_statistical_testing.py",
        BASE_DIR / "dashboard" / "pages" / "03_bayesian_analysis.py",
        BASE_DIR / "dashboard" / "pages" / "04_power_calculator.py"
    ]
    for p in pages:
        assert p.exists(), f"Dashboard page missing: {p}"
