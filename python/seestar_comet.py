"""
Seestar S50 - Comet Processing Script

Registers and stacks on the comet nucleus to produce a sharp comet
with trailed stars. Uses standard star registration first, then
comet-mode stacking.

NOTE: Siril will open a dialog for you to mark the comet position
on the first and last frames. Follow the on-screen prompts.

Requires Siril 1.4+ with Python scripting support.
Requires internet connection or local star catalogs for plate solving and SPCC.

Directory structure expected:
  workdir/
    lights/    - Seestar sub-exposures (.fit) [required]
    seestar_config.yaml  [optional]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sirilpy as s

from seestar_common import (
    convert_and_calibrate_lights,
    load_config,
    register_sequence,
    run_pipeline,
    setup_directories,
    stack_sequence,
    validate_workdir,
)

OUTPUT_NAME = "Seestar_comet_result"


def main():
    siril = s.SirilInterface()
    siril.connect()

    try:
        workdir = os.getcwd()
        config = load_config(workdir)
        fwhm = config["frame_selection"]["fwhm_percent"]

        siril.log("Seestar S50 Comet Processing Script")
        validate_workdir(workdir)
        setup_directories(workdir)

        # No calibration for comet mode -- lights only
        masters = {"dark": None, "flat": None, "bias": None}
        seq_name = convert_and_calibrate_lights(siril, workdir, config, masters)

        # Standard registration (required before comet stacking)
        register_sequence(siril, seq_name)

        # Stack with comet mode and frame selection
        stack_sequence(siril, seq_name, config, comet=True, filter_fwhm=fwhm)

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
