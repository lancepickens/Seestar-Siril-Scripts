"""
Shared utilities for Seestar S50 Siril Python scripts.

Provides configuration loading, directory management, calibration
frame detection, and the common post-processing pipeline used by
all processing scripts.
"""

import os
import sys
import glob
import shutil

# sirilpy is only available when running inside Siril 1.4+
# It will be mocked in unit tests
try:
    import sirilpy as s
except ImportError:
    s = None

# Default configuration matching Seestar S50 specs
DEFAULT_CONFIG = {
    "optics": {
        "focal_length": 250,
        "pixel_size": 2.9,
    },
    "platesolve": {
        "limit_mag": 18,
    },
    "spcc": {
        "sensor": "ZWO Seestar S50",
        "filter": "UV/IR Block",
    },
    "stacking": {
        "sigma_high": 3,
        "sigma_low": 3,
        "normalization": "addscale",
    },
    "frame_selection": {
        "fwhm_percent": 80,
        "roundness_percent": 90,
    },
    "background_extraction": {
        "smooth": 0.5,
        "samples": 15,
    },
}


def load_config(workdir):
    """Load seestar_config.yaml from workdir, falling back to defaults.

    If the YAML file exists in the working directory, its values override
    the defaults. Missing keys use default values. If PyYAML is not
    available or the file doesn't exist, returns defaults.
    """
    import copy
    config = copy.deepcopy(DEFAULT_CONFIG)

    config_path = os.path.join(workdir, "seestar_config.yaml")
    if not os.path.isfile(config_path):
        return config

    try:
        import yaml
    except ImportError:
        # PyYAML not available -- use defaults
        return config

    with open(config_path, "r") as f:
        user_config = yaml.safe_load(f)

    if not isinstance(user_config, dict):
        return config

    # Merge user config over defaults (one level deep)
    for section, values in user_config.items():
        if section in config and isinstance(values, dict):
            config[section].update(values)

    return config


def detect_calibration_frames(workdir):
    """Detect which calibration frame directories contain .fit files.

    Returns a dict with keys 'darks', 'flats', 'biases' mapped to
    True/False based on whether the directory exists and contains
    at least one .fit file.
    """
    result = {}
    for frame_type in ("darks", "flats", "biases"):
        frame_dir = os.path.join(workdir, frame_type)
        if os.path.isdir(frame_dir):
            fits = glob.glob(os.path.join(frame_dir, "*.fit"))
            result[frame_type] = len(fits) > 0
        else:
            result[frame_type] = False
    return result


def validate_workdir(workdir):
    """Validate that the working directory has a lights/ folder with .fit files.

    Raises FileNotFoundError if lights/ is missing or contains no .fit files.
    """
    lights_dir = os.path.join(workdir, "lights")
    if not os.path.isdir(lights_dir):
        raise FileNotFoundError(
            f"No lights/ directory found in {workdir}. "
            "Place your Seestar sub-exposures in a lights/ subdirectory."
        )
    fits = glob.glob(os.path.join(lights_dir, "*.fit"))
    if not fits:
        raise FileNotFoundError(
            f"No .fit files found in {lights_dir}. "
            "Ensure your Seestar sub-exposures are .fit format."
        )


def setup_directories(workdir):
    """Create the stacked/ output directory."""
    os.makedirs(os.path.join(workdir, "stacked"), exist_ok=True)


def cleanup_process(workdir):
    """Delete the process/ intermediate directory."""
    process_dir = os.path.join(workdir, "process")
    if os.path.isdir(process_dir):
        shutil.rmtree(process_dir)


def get_siril():
    """Create and connect a SirilInterface instance."""
    siril = s.SirilInterface()
    siril.connect()
    return siril


def stack_calibration_masters(siril, workdir, calibration):
    """Stack available calibration frames into master files.

    Args:
        siril: Connected SirilInterface
        workdir: Working directory path
        calibration: Dict from detect_calibration_frames()

    Returns:
        Dict with keys 'dark', 'flat', 'bias' mapped to master filenames
        or None if not available.
    """
    masters = {"dark": None, "flat": None, "bias": None}

    if calibration.get("biases"):
        siril.log("Stacking bias frames...")
        siril.cmd("cd", os.path.join(workdir, "biases"))
        siril.cmd("convert", "bias", "-out=../process")
        siril.cmd("cd", os.path.join(workdir, "process"))
        siril.cmd("stack", "bias", "rej", "3", "3", "-nonorm")
        siril.cmd("cd", workdir)
        masters["bias"] = "bias_stacked"

    if calibration.get("darks"):
        siril.log("Stacking dark frames...")
        siril.cmd("cd", os.path.join(workdir, "darks"))
        siril.cmd("convert", "dark", "-out=../process")
        siril.cmd("cd", os.path.join(workdir, "process"))
        siril.cmd("stack", "dark", "rej", "3", "3", "-nonorm")
        siril.cmd("cd", workdir)
        masters["dark"] = "dark_stacked"

    if calibration.get("flats"):
        siril.log("Stacking flat frames...")
        siril.cmd("cd", os.path.join(workdir, "flats"))
        siril.cmd("convert", "flat", "-out=../process")
        siril.cmd("cd", os.path.join(workdir, "process"))
        if masters["bias"]:
            siril.cmd("calibrate", "flat", f"-bias={masters['bias']}")
        else:
            siril.cmd("calibrate", "flat")
        siril.cmd("stack", "pp_flat", "rej", "3", "3", "-norm=mul")
        siril.cmd("cd", workdir)
        masters["flat"] = "pp_flat_stacked"

    return masters


def convert_and_calibrate_lights(siril, workdir, config, masters):
    """Convert light frames and calibrate with available masters.

    Args:
        siril: Connected SirilInterface
        workdir: Working directory path
        config: Configuration dict
        masters: Dict from stack_calibration_masters()

    Returns:
        The sequence name prefix to use for registration (e.g. 'light' or 'pp_light').
    """
    siril.cmd("cd", os.path.join(workdir, "lights"))

    # Build calibrate arguments from available masters
    cal_args = []
    if masters["dark"]:
        cal_args.extend([f"-dark={masters['dark']}", "-cc=dark", "-sighi=3", "-siglo=3"])
    if masters["flat"]:
        cal_args.extend([f"-flat={masters['flat']}"])
    if masters["bias"]:
        cal_args.extend([f"-bias={masters['bias']}"])

    if cal_args:
        # Keep CFA data during convert, debayer after calibration
        siril.cmd("convert", "light", "-out=../process")
        siril.cmd("cd", os.path.join(workdir, "process"))
        siril.cmd("calibrate", "light", *cal_args, "-cfa", "-debayer")
        return "pp_light"
    else:
        # No calibration -- debayer during convert
        siril.cmd("convert", "light", "-debayer", "-out=../process")
        siril.cmd("cd", os.path.join(workdir, "process"))
        return "light"


def register_sequence(siril, seq_name, drizzle=False):
    """Register (align) a sequence.

    Args:
        siril: Connected SirilInterface
        seq_name: Sequence name prefix
        drizzle: Enable drizzle mode
    """
    args = [seq_name]
    if drizzle:
        args.append("-drizzle")
    siril.cmd("register", *args)


def stack_sequence(siril, seq_name, config, comet=False,
                   filter_fwhm=None, filter_round=None):
    """Stack a registered sequence.

    Args:
        siril: Connected SirilInterface
        seq_name: Registered sequence name (with r_ prefix)
        config: Configuration dict
        comet: Enable comet stacking mode
        filter_fwhm: FWHM filter percentage (e.g. 90 for best 90%)
        filter_round: Roundness filter percentage
    """
    sig_h = config["stacking"]["sigma_high"]
    sig_l = config["stacking"]["sigma_low"]
    norm = config["stacking"]["normalization"]

    args = [f"r_{seq_name}", "rej", str(sig_l), str(sig_h),
            f"-norm={norm}", "-output_norm", "-weight=wfwhm"]

    if filter_fwhm is not None:
        args.append(f"-filter-wfwhm={filter_fwhm}%")
    if filter_round is not None:
        args.append(f"-filter-round={filter_round}%")
    if comet:
        args.append("-comet")

    siril.cmd("stack", *args)


def post_process(siril, workdir, config):
    """Run the common post-processing pipeline on the loaded image.

    Pipeline: platesolve -> SPCC -> background extraction
    """
    optics = config["optics"]
    ps = config["platesolve"]
    spcc_cfg = config["spcc"]
    bg = config["background_extraction"]

    siril.cmd("cd", workdir)

    siril.cmd("platesolve",
              f"-focal={optics['focal_length']}",
              f"-pixelsize={optics['pixel_size']}",
              f"-limitmag={ps['limit_mag']}")

    siril.cmd("spcc",
              f'-oscsensor="{spcc_cfg["sensor"]}"',
              f'-oscfilter="{spcc_cfg["filter"]}"')

    siril.cmd("subsky", "-rbf",
              f"-smooth={bg['smooth']}",
              f"-samples={bg['samples']}")


def read_fits_keyword(filepath, keyword):
    """Read a keyword value from a FITS file header."""
    target = keyword.ljust(8)[:8]
    try:
        with open(filepath, "rb") as f:
            while True:
                block = f.read(2880)
                if len(block) < 2880:
                    return None
                for i in range(0, 2880, 80):
                    card = block[i:i + 80].decode("ascii", errors="replace")
                    if card[:8].strip() == "END":
                        return None
                    if card[:8] == target and card[8] == "=":
                        value_str = card[10:].split("/")[0].strip()
                        if value_str.startswith("'"):
                            return value_str.strip("' ")
                        try:
                            return float(value_str)
                        except ValueError:
                            return value_str
    except (OSError, IOError):
        return None


def format_integration_time(seconds):
    """Format integration time in seconds as a filename-safe string."""
    if seconds is None or seconds <= 0:
        return None
    total = int(seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours > 0:
        return f"{hours}h{minutes:02d}m{secs:02d}s"
    if minutes > 0:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


def save_results(siril, workdir, output_name):
    """Save the processed image as FITS, JPEG, and TIFF to stacked/."""
    siril.cmd("save", f"stacked/{output_name}")
    siril.cmd("savejpg", f"stacked/{output_name}_preview")
    siril.cmd("savetif", f"stacked/{output_name}_16bit")


def run_pipeline(siril, workdir, config, output_name, seq_name):
    """Run the final steps: load stacked, post-process, save, cleanup."""
    stacked_path = os.path.join(workdir, "process", f"r_{seq_name}_stacked.fit")
    livetime = read_fits_keyword(stacked_path, "LIVETIME")
    time_suffix = format_integration_time(livetime)

    siril.cmd("cd", workdir)
    siril.cmd("load", f"process/r_{seq_name}_stacked")

    post_process(siril, workdir, config)

    full_name = f"{output_name}_{time_suffix}" if time_suffix else output_name
    save_results(siril, workdir, full_name)

    siril.cmd("close")
    cleanup_process(workdir)

    siril.log(f"Done! Results saved to stacked/{full_name}", s.LogColor.GREEN)
