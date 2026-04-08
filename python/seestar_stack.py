"""
Seestar S50 - Smart Stacking Script

Automatically detects available calibration frames (darks, flats, biases)
and applies the appropriate calibration pipeline before stacking.

Requires Siril 1.4+ with Python scripting support.
Requires internet connection or local star catalogs for plate solving and SPCC.

Directory structure expected:
  workdir/
    lights/    - Seestar sub-exposures (.fit) [required]
    darks/     - Dark frames (.fit) [optional]
    flats/     - Flat frames (.fit) [optional]
    biases/    - Bias/offset frames (.fit) [optional]
    seestar_config.yaml  [optional]

Set your working directory in Siril to the parent folder containing lights/.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sirilpy as s

from seestar_common import (
    cleanup_process,
    convert_and_calibrate_lights,
    detect_calibration_frames,
    load_config,
    post_process,
    register_sequence,
    run_pipeline,
    save_results,
    setup_directories,
    stack_calibration_masters,
    stack_sequence,
    validate_workdir,
)

OUTPUT_NAME = "Seestar_result"


def main():
    siril = s.SirilInterface()
    siril.connect()

    try:
        workdir = os.getcwd()
        config = load_config(workdir)

        siril.log("Seestar S50 Smart Stacking Script")
        siril.log("Validating working directory...")
        validate_workdir(workdir)
        setup_directories(workdir)

        # Detect available calibration frames
        calibration = detect_calibration_frames(workdir)
        detected = [k for k, v in calibration.items() if v]
        if detected:
            siril.log(f"Detected calibration frames: {', '.join(detected)}")
        else:
            siril.log("No calibration frames detected, stacking lights only.")

        # Stack calibration masters
        masters = stack_calibration_masters(siril, workdir, calibration)

        # Convert and calibrate lights
        seq_name = convert_and_calibrate_lights(siril, workdir, config, masters)

        # Register and stack
        register_sequence(siril, seq_name)
        stack_sequence(siril, seq_name, config)

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
