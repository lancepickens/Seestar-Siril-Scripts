"""Tests for stacking command sequences and calibration logic."""

import os

import pytest

from seestar_common import (
    DEFAULT_CONFIG,
    convert_and_calibrate_lights,
    format_integration_time,
    post_process,
    read_fits_keyword,
    register_sequence,
    run_pipeline,
    save_results,
    stack_calibration_masters,
    stack_sequence,
)


class TestStackCalibrationMasters:
    def test_no_calibration(self, mock_siril, tmp_workdir):
        calibration = {"darks": False, "flats": False, "biases": False}
        masters = stack_calibration_masters(mock_siril, str(tmp_workdir), calibration)
        assert masters == {"dark": None, "flat": None, "bias": None}
        assert mock_siril.cmd.call_count == 0

    def test_darks_only(self, mock_siril, tmp_workdir_darks_only):
        workdir = str(tmp_workdir_darks_only)
        calibration = {"darks": True, "flats": False, "biases": False}
        masters = stack_calibration_masters(mock_siril, workdir, calibration)

        assert masters["dark"] == "dark_stacked"
        assert masters["flat"] is None
        assert masters["bias"] is None

        # Verify dark stacking commands were called
        cmds = [args[0] for args in mock_siril.cmd_calls]
        assert "convert" in cmds
        assert "stack" in cmds

    def test_full_calibration(self, mock_siril, tmp_workdir_full):
        workdir = str(tmp_workdir_full)
        calibration = {"darks": True, "flats": True, "biases": True}
        masters = stack_calibration_masters(mock_siril, workdir, calibration)

        assert masters["dark"] == "dark_stacked"
        assert masters["flat"] == "pp_flat_stacked"
        assert masters["bias"] == "bias_stacked"

        # Should have convert+stack for each type, plus calibrate for flats
        cmds = [args[0] for args in mock_siril.cmd_calls]
        assert cmds.count("convert") == 3  # bias, dark, flat
        assert cmds.count("stack") == 3
        assert cmds.count("calibrate") == 1  # flat calibrated with bias

    def test_flats_without_bias(self, mock_siril, tmp_workdir):
        """Flats should still be processed even without bias frames."""
        workdir = str(tmp_workdir)
        # Create flats dir
        flats = tmp_workdir / "flats"
        flats.mkdir()
        (flats / "flat_00001.fit").write_bytes(b"\x00")

        calibration = {"darks": False, "flats": True, "biases": False}
        masters = stack_calibration_masters(mock_siril, workdir, calibration)

        assert masters["flat"] == "pp_flat_stacked"
        assert masters["bias"] is None

        # Calibrate should be called without -bias argument
        calibrate_calls = [
            args for args in mock_siril.cmd_calls if args[0] == "calibrate"
        ]
        assert len(calibrate_calls) == 1
        cal_args = calibrate_calls[0]
        assert not any("-bias=" in str(a) for a in cal_args)

    def test_bias_calibrates_flats(self, mock_siril, tmp_workdir_full):
        """When bias is available, it should be used to calibrate flats."""
        workdir = str(tmp_workdir_full)
        calibration = {"darks": True, "flats": True, "biases": True}
        stack_calibration_masters(mock_siril, workdir, calibration)

        calibrate_calls = [
            args for args in mock_siril.cmd_calls if args[0] == "calibrate"
        ]
        assert len(calibrate_calls) == 1
        cal_args = calibrate_calls[0]
        assert any("-bias=bias_stacked" in str(a) for a in cal_args)


class TestConvertAndCalibrateLights:
    def test_no_masters_debayers_during_convert(self, mock_siril, tmp_workdir):
        masters = {"dark": None, "flat": None, "bias": None}
        seq = convert_and_calibrate_lights(
            mock_siril, str(tmp_workdir), DEFAULT_CONFIG, masters
        )
        assert seq == "light"
        # Should not call calibrate
        cmds = [args[0] for args in mock_siril.cmd_calls]
        assert "calibrate" not in cmds
        # Should debayer during convert
        convert_call = [args for args in mock_siril.cmd_calls if args[0] == "convert"][0]
        assert "-debayer" in convert_call

    def test_dark_only_debayers_during_calibrate(self, mock_siril, tmp_workdir):
        masters = {"dark": "dark_stacked", "flat": None, "bias": None}
        seq = convert_and_calibrate_lights(
            mock_siril, str(tmp_workdir), DEFAULT_CONFIG, masters
        )
        assert seq == "pp_light"
        calibrate_calls = [
            args for args in mock_siril.cmd_calls if args[0] == "calibrate"
        ]
        assert len(calibrate_calls) == 1
        cal_args = " ".join(str(a) for a in calibrate_calls[0])
        assert "-dark=dark_stacked" in cal_args
        assert "-cfa" in cal_args
        assert "-debayer" in cal_args
        # Convert should NOT debayer (CFA preserved for calibration)
        convert_call = [args for args in mock_siril.cmd_calls if args[0] == "convert"][0]
        assert "-debayer" not in convert_call

    def test_full_masters(self, mock_siril, tmp_workdir):
        masters = {
            "dark": "dark_stacked",
            "flat": "pp_flat_stacked",
            "bias": "bias_stacked",
        }
        seq = convert_and_calibrate_lights(
            mock_siril, str(tmp_workdir), DEFAULT_CONFIG, masters
        )
        assert seq == "pp_light"
        calibrate_calls = [
            args for args in mock_siril.cmd_calls if args[0] == "calibrate"
        ]
        cal_args = " ".join(str(a) for a in calibrate_calls[0])
        assert "-dark=dark_stacked" in cal_args
        assert "-flat=pp_flat_stacked" in cal_args
        assert "-bias=bias_stacked" in cal_args
        assert "-cfa" in cal_args
        assert "-debayer" in cal_args


class TestRegisterSequence:
    def test_normal(self, mock_siril):
        register_sequence(mock_siril, "light")
        assert mock_siril.cmd_calls == [("register", "light")]

    def test_drizzle(self, mock_siril):
        register_sequence(mock_siril, "light", drizzle=True)
        assert mock_siril.cmd_calls == [("register", "light", "-drizzle")]


class TestStackSequence:
    def test_basic(self, mock_siril):
        stack_sequence(mock_siril, "light", DEFAULT_CONFIG)
        call = mock_siril.cmd_calls[0]
        assert call[0] == "stack"
        assert "r_light" in call
        assert "-norm=addscale" in call

    def test_comet(self, mock_siril):
        stack_sequence(mock_siril, "light", DEFAULT_CONFIG, comet=True)
        call = mock_siril.cmd_calls[0]
        assert "-comet" in call

    def test_frame_selection(self, mock_siril):
        stack_sequence(mock_siril, "light", DEFAULT_CONFIG,
                       filter_fwhm=80, filter_round=90)
        call = mock_siril.cmd_calls[0]
        assert "-filter-wfwhm=80%" in call
        assert "-filter-round=90%" in call

    def test_custom_sigma(self, mock_siril):
        config = {
            **DEFAULT_CONFIG,
            "stacking": {
                "sigma_high": 5,
                "sigma_low": 2,
                "normalization": "mul",
            },
        }
        stack_sequence(mock_siril, "light", config)
        call = mock_siril.cmd_calls[0]
        assert "5" in call
        assert "2" in call
        assert "-norm=mul" in call


class TestPostProcess:
    def test_pipeline_order(self, mock_siril, tmp_workdir):
        post_process(mock_siril, str(tmp_workdir), DEFAULT_CONFIG)
        cmds = [args[0] for args in mock_siril.cmd_calls]
        assert cmds.index("platesolve") < cmds.index("spcc")
        assert cmds.index("spcc") < cmds.index("subsky")
        assert "autostretch" not in cmds

    def test_uses_config_values(self, mock_siril, tmp_workdir):
        post_process(mock_siril, str(tmp_workdir), DEFAULT_CONFIG)
        platesolve_call = [
            args for args in mock_siril.cmd_calls if args[0] == "platesolve"
        ][0]
        assert "-focal=250" in platesolve_call
        assert "-pixelsize=2.9" in platesolve_call
        assert "-limitmag=18" in platesolve_call


class TestSaveResults:
    def test_saves_three_formats(self, mock_siril, tmp_workdir):
        save_results(mock_siril, str(tmp_workdir), "Seestar_result")
        cmds = [args[0] for args in mock_siril.cmd_calls]
        assert "save" in cmds
        assert "savejpg" in cmds
        assert "savetif" in cmds

    def test_output_paths(self, mock_siril, tmp_workdir):
        save_results(mock_siril, str(tmp_workdir), "Seestar_result")
        save_call = [args for args in mock_siril.cmd_calls if args[0] == "save"][0]
        assert save_call[1] == "stacked/Seestar_result"


def _make_fits_header(keywords):
    """Build a minimal FITS primary header block from keyword dict."""
    cards = ["SIMPLE  =                    T".ljust(80)]
    cards.append("BITPIX  =                   16".ljust(80))
    cards.append("NAXIS   =                    0".ljust(80))
    for key, val in keywords.items():
        if isinstance(val, float):
            card = f"{key.ljust(8)}= {val:20.6f}"
        elif isinstance(val, int):
            card = f"{key.ljust(8)}= {val:20d}"
        else:
            card = f"{key.ljust(8)}= '{val}'"
        cards.append(card.ljust(80))
    cards.append("END".ljust(80))
    header = "".join(cards).encode("ascii")
    # Pad to multiple of 2880 bytes
    remainder = len(header) % 2880
    if remainder:
        header += b" " * (2880 - remainder)
    return header


class TestReadFitsKeyword:
    def test_reads_float(self, tmp_path):
        fits = tmp_path / "test.fit"
        fits.write_bytes(_make_fits_header({"LIVETIME": 5400.0}))
        assert read_fits_keyword(str(fits), "LIVETIME") == 5400.0

    def test_reads_string(self, tmp_path):
        fits = tmp_path / "test.fit"
        fits.write_bytes(_make_fits_header({"INSTRUME": "Seestar"}))
        assert read_fits_keyword(str(fits), "INSTRUME") == "Seestar"

    def test_missing_keyword(self, tmp_path):
        fits = tmp_path / "test.fit"
        fits.write_bytes(_make_fits_header({"EXPTIME": 10.0}))
        assert read_fits_keyword(str(fits), "LIVETIME") is None

    def test_missing_file(self, tmp_path):
        assert read_fits_keyword(str(tmp_path / "nope.fit"), "LIVETIME") is None


class TestFormatIntegrationTime:
    def test_hours(self):
        assert format_integration_time(5400.0) == "1h30m00s"

    def test_minutes(self):
        assert format_integration_time(750.0) == "12m30s"

    def test_seconds_only(self):
        assert format_integration_time(30.0) == "30s"

    def test_none(self):
        assert format_integration_time(None) is None

    def test_zero(self):
        assert format_integration_time(0) is None

    def test_negative(self):
        assert format_integration_time(-10) is None
