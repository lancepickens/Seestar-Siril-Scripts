"""Shared test fixtures for Seestar Siril script tests."""

import os
import sys
import types
from unittest.mock import MagicMock

import pytest

# Mock sirilpy before any seestar modules are imported
mock_sirilpy = types.ModuleType("sirilpy")
mock_sirilpy.SirilInterface = MagicMock
mock_sirilpy.LogColor = MagicMock()
mock_sirilpy.LogColor.GREEN = "GREEN"
mock_sirilpy.LogColor.RED = "RED"
mock_sirilpy.CommandError = type("CommandError", (Exception,), {})
mock_sirilpy.SirilError = type("SirilError", (Exception,), {})
mock_sirilpy.DataError = type("DataError", (Exception,), {})
sys.modules["sirilpy"] = mock_sirilpy

# Add python/ to path so we can import seestar modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))


@pytest.fixture
def mock_siril():
    """A mock SirilInterface that tracks cmd() calls."""
    siril = MagicMock()
    siril.cmd_calls = []

    def track_cmd(*args):
        siril.cmd_calls.append(args)

    siril.cmd.side_effect = track_cmd
    return siril


@pytest.fixture
def tmp_workdir(tmp_path):
    """Create a temporary working directory with lights/ containing dummy .fit files."""
    lights = tmp_path / "lights"
    lights.mkdir()
    for i in range(5):
        (lights / f"light_{i:05d}.fit").write_bytes(b"\x00")
    return tmp_path


@pytest.fixture
def tmp_workdir_full(tmp_workdir):
    """Working directory with lights, darks, flats, and biases."""
    for subdir in ("darks", "flats", "biases"):
        d = tmp_workdir / subdir
        d.mkdir()
        for i in range(3):
            (d / f"{subdir[:-1]}_{i:05d}.fit").write_bytes(b"\x00")
    return tmp_workdir


@pytest.fixture
def tmp_workdir_darks_only(tmp_workdir):
    """Working directory with lights and darks only."""
    darks = tmp_workdir / "darks"
    darks.mkdir()
    for i in range(3):
        (darks / f"dark_{i:05d}.fit").write_bytes(b"\x00")
    return tmp_workdir
