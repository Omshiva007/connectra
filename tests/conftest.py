"""
Shared pytest fixtures for the Connectra test suite.
"""
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Redirect all runtime data to a temporary directory for every test."""
    monkeypatch.setenv("CONNECTRA_DATA_DIR", str(tmp_path))

    # Force re-evaluation of module-level singletons that depend on the
    # env var so that each test gets a clean state.
    import importlib
    import connectra_core.config as cfg
    importlib.reload(cfg)

    import connectra_core.database as db
    importlib.reload(db)

    import connectra_core.admin_database as adb
    importlib.reload(adb)

    import connectra_core.holiday_checker as hc
    importlib.reload(hc)

    import connectra_core.security as sec
    importlib.reload(sec)

    yield tmp_path
