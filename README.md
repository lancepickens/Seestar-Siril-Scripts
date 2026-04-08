# Seestar Siril Scripts

A collection of [Siril](https://siril.org/) scripts for processing astrophotography data captured with the [ZWO Seestar S50](https://www.zwoastro.com/seestar/) smart telescope.

These scripts automate the stacking and processing pipeline so you can get better results from your Seestar sub-exposures than the built-in live stacking provides.

## Requirements

- Seestar S50 sub-exposure FITS files (`.fit`)
- Internet connection or local star catalogs (for plate solving and SPCC)
- **SSF scripts:** Siril 1.2.0 or later
- **Python scripts:** Siril 1.4.0 or later (with Python scripting enabled)

## Scripts

### SSF Scripts (Siril 1.2+)

Located in `scripts/`. These are traditional Siril script files.

| Script | Description |
|--------|-------------|
| `Seestar_BasicStack.ssf` | Simple stacking with no calibration frames. Best starting point for beginners. |
| `Seestar_WithDarks.ssf` | Stacking with dark frame subtraction for reduced thermal noise. |
| `Seestar_FullCalibration.ssf` | Full calibration pipeline using darks, flats, and bias frames. |
| `Seestar_Comet.ssf` | Comet-specific processing that registers on the comet nucleus. |
| `Seestar_FrameSelect.ssf` | Selective stacking that filters out poor quality frames by FWHM and roundness. |
| `Seestar_Drizzle2x.ssf` | 2x drizzle stacking for enhanced resolution (requires 50+ subs). |

### Python Scripts (Siril 1.4+)

Located in `python/`. These use Siril's built-in `sirilpy` module and offer additional features:
auto-detection of calibration frames, automatic cleanup of temporary files, configurable
parameters via YAML, and error handling with meaningful messages.

| Script | Description |
|--------|-------------|
| `seestar_stack.py` | Smart stacking -- auto-detects darks/flats/biases and applies available calibration. Replaces BasicStack, WithDarks, and FullCalibration. |
| `seestar_comet.py` | Comet processing with nucleus registration and trailed stars. |
| `seestar_drizzle.py` | 2x drizzle stacking with auto-detect calibration (50+ subs recommended). |
| `seestar_frameselect.py` | Quality-filtered stacking by FWHM and roundness with auto-detect calibration. |

Supporting files:
- `seestar_common.py` -- Shared utilities (must be copied alongside the scripts)
- `seestar_config.yaml` -- Default Seestar S50 parameters (optional, copy to your working directory to customize)

## Directory Setup

Before running a script, organize your files into this directory structure:

```
my_target/
  lights/          # Your Seestar sub-exposures
    light_00001.fit
    light_00002.fit
    ...
  darks/           # (Optional) Dark frames
    dark_00001.fit
    ...
  flats/           # (Optional) Flat frames
    flat_00001.fit
    ...
  biases/          # (Optional) Bias/offset frames
    bias_00001.fit
    ...
```

After running a script, output directories are created:

```
my_target/
  stacked/         # Final results (FITS, TIFF, JPEG)
  process/         # Intermediate working files (auto-deleted by Python scripts)
```

**Important:** The Seestar saves individual sub-exposures in its internal storage under a path like `Seestar S50/<target>/sub/`. Copy the `.fit` files from there into the `lights/` directory.

## How to Use

1. **Copy** script files into Siril's scripts directory:
   - **Linux:** `~/.local/share/siril/scripts/`
   - **macOS:** `~/Library/Application Support/siril/scripts/`
   - **Windows:** `%LOCALAPPDATA%\siril\scripts\`
   - For SSF scripts, copy from `scripts/`
   - For Python scripts, copy all `.py` files from `python/`
2. **Organize** your Seestar sub-exposures into the directory structure shown above.
3. **(Optional)** Copy `seestar_config.yaml` to your target folder to customize processing parameters.
4. **Open Siril** and set the working directory to your target folder (e.g., `my_target/`).
5. **Run** the script from the Scripts menu (SSF) or Scripts > Python Scripts menu (Python).
6. **Results** will be saved in the `stacked/` subdirectory as FITS, TIFF, and JPEG files.
7. **Clean up:** Python scripts auto-delete `process/`. For SSF scripts, delete it manually.

## Choosing a Script

If you have **Siril 1.4+**, use the Python scripts -- they auto-detect your calibration frames and clean up after themselves. Just run `seestar_stack.py` and it will figure out the best pipeline.

For **Siril 1.2-1.3**, use the SSF scripts:
- **First time?** Start with `Seestar_BasicStack.ssf` -- it requires only your light frames.
- **Noisy images?** Use `Seestar_WithDarks.ssf` if you have matching dark frames.
- **Best quality?** Use `Seestar_FullCalibration.ssf` with a full set of calibration frames.
- **Windy night?** Use `Seestar_FrameSelect.ssf` to automatically discard bad frames.
- **Small targets?** Use `Seestar_Drizzle2x.ssf` to boost resolution on planetary nebulae or small galaxies.
- **Comets?** Use `Seestar_Comet.ssf` for sharp comet stacking with trailed stars.

## Tips for Seestar Users

- **Collect many subs:** More sub-exposures = better signal-to-noise ratio. Aim for 100+ subs when possible.
- **Take darks:** Cover the Seestar lens cap and capture 20-30 dark frames at the same temperature as your lights.
- **Let it dither:** The Seestar's natural tracking drift provides dithering, which helps with noise reduction during stacking.
- **Export individual subs:** Make sure your Seestar is set to save individual sub-exposures, not just the live-stacked result.

## License

These scripts are provided as-is for the astrophotography community. Feel free to modify and share.
