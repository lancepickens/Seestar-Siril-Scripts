"""
Seestar S50 - 2x Drizzle Stacking Script

Uses drizzle integration to increase resolution of the final stacked
image. Works best with 50+ sub-exposures. The Seestar's natural
tracking drift provides the dithering needed for drizzle.

NOTE: Output file size will be ~4x larger due to doubled resolution.

Requires Siril 1.4+ with Python scripting support.
Requires internet connection or local star catalogs for plate solving and SPCC.

Directory structure expected:
  workdir/
    lights/    - Seestar sub-exposures (.fit) [required]
    darks/     - Dark frames (.fit) [optional]
    flats/     - Flat frames (.fit) [optional]
    biases/    - Bias/offset frames (.fit) [optional]
    seestar_config.yaml  [optional]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sirilpy as s

from seestar_common import (
    convert_and_calibrate_lights,
    detect_calibration_frames,
    load_config,
    register_sequence,
    run_pipeline,
    setup_directories,
    stack_calibration_masters,
    stack_sequence,
    validate_workdir,
)

OUTPUT_NAME = "Seestar_drizzle_result"


def main():
    siril = s.SirilInterface()
    siril.connect()

    try:
        workdir = os.getcwd()
        config = load_config(workdir)
        fwhm = config["frame_selection"]["fwhm_percent"]

        siril.log("Seestar S50 2x Drizzle Stacking Script")
        siril.log("Note: Output will be ~4x larger than normal stacking.")
        validate_workdir(workdir)
        setup_directories(workdir)

        # Auto-detect and stack calibration frames
        calibration = detect_calibration_frames(workdir)
        masters = stack_calibration_masters(siril, workdir, calibration)

        # Convert and calibrate lights
        seq_name = convert_and_calibrate_lights(siril, workdir, config, masters)

        # Register with drizzle enabled
        register_sequence(siril, seq_name, drizzle=True)

        # Stack with frame selection
        stack_sequence(siril, seq_name, config, filter_fwhm=fwhm)

        # Post-process, save, and cleanup
        run_pipeline(siril, workdir, config, OUTPUT_NAME, seq_name)

    except s.CommandError as e:
        siril.log(f"Siril command failed: {e}", s.LogColor.RED)
    except FileNotFoundError as e:
        siril.log(str(e), s.LogColor.RED)
    except Exception as e:
        siril.log(f"Unexpected error: {e}", s.LogColor.RED)
    finally:
        siril.disconnect()


main()
