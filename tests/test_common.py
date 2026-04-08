"""Tests for seestar_common utilities."""

import os

import pytest

from seestar_common import (
    cleanup_process,
    detect_calibration_frames,
    setup_directories,
    validate_workdir,
)


class TestDetectCalibrationFrames:
    def test_no_extras(self, tmp_workdir):
        result = detect_calibration_frames(str(tmp_workdir))
        assert result == {"darks": False, "flats": False, "biases": False}

    def test_all_present(self, tmp_workdir_full):
        result = detect_calibration_frames(str(tmp_workdir_full))
        assert result == {"darks": True, "flats": True, "biases": True}

    def test_darks_only(self, tmp_workdir_darks_only):
        result = detect_calibration_frames(str(tmp_workdir_darks_only))
        assert result == {"darks": True, "flats": False, "biases": False}

    def test_empty_dir_not_detected(self, tmp_workdir):
        (tmp_workdir / "darks").mkdir()
        result = detect_calibration_frames(str(tmp_workdir))
        assert result["darks"] is False

    def test_dir_with_wrong_extension(self, tmp_workdir):
        darks = tmp_workdir / "darks"
        darks.mkdir()
        (darks / "dark_00001.png").write_bytes(b"\x00")
        result = detect_calibration_frames(str(tmp_workdir))
        assert result["darks"] is False


class TestValidateWorkdir:
    def test_valid(self, tmp_workdir):
        validate_workdir(str(tmp_workdir))  # should not raise

    def test_missing_lights(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="No lights/ directory"):
            validate_workdir(str(tmp_path))

    def test_no_fit_files(self, tmp_path):
        lights = tmp_path / "lights"
        lights.mkdir()
        (lights / "readme.txt").write_text("not a fit file")
        with pytest.raises(FileNotFoundError, match="No .fit files"):
            validate_workdir(str(tmp_path))


class TestSetupDirectories:
    def test_creates_stacked(self, tmp_workdir):
        setup_directories(str(tmp_workdir))
        assert (tmp_workdir / "stacked").is_dir()

    def test_idempotent(self, tmp_workdir):
        setup_directories(str(tmp_workdir))
        setup_directories(str(tmp_workdir))  # should not raise
        assert (tmp_workdir / "stacked").is_dir()


class TestCleanupProcess:
    def test_deletes_process(self, tmp_workdir):
        process = tmp_workdir / "process"
        process.mkdir()
        (process / "temp.fit").write_bytes(b"\x00")
        cleanup_process(str(tmp_workdir))
        assert not process.exists()

    def test_missing_process_no_error(self, tmp_workdir):
        cleanup_process(str(tmp_workdir))  # should not raise
