# Windows Packaging Guide

This guide prepares a local Windows build of the HCZ DAS View GUI. It is a
packaging smoke workflow, not a release guarantee. Build results depend on the
local Python, Conda, PyQt5, matplotlib, scipy, numpy, and PyInstaller versions.

## 1. Create or activate an environment

```powershell
conda activate mywork
python -m pip install -e .[gui,packaging]
```

For development validation, install the development extras:

```powershell
python -m pip install -e .[dev,gui,packaging]
```

## 2. Start the GUI before packaging

```powershell
hcz-das-view --help
hcz-das-view
```

Open a small supported DAS file manually and verify Waterfall, Waveform,
Spectrum, FK, and Analysis tabs as needed. Do not copy real DAS data into the
repository.

## 3. Build with PyInstaller

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

The script calls:

```powershell
python -m PyInstaller packaging\hcz_das_view.spec --clean --noconfirm
```

Generated `build/` and `dist/` folders are local artifacts and are ignored by
git.

## 4. PyQt5 and matplotlib notes

- The spec includes PyQt5 hidden imports used by the optional GUI layer.
- Matplotlib is configured through the normal package imports. If a backend
  issue appears on a target machine, rebuild in the same environment used for
  manual GUI validation.
- The GUI entry point is `das_view.gui.app:main`; core, IO, processing,
  analysis, and plotting modules remain PyQt5-independent.
- For a visible help smoke in shells where Windows `gui-scripts` executables do
  not attach to the console, run `python -m das_view.gui.app --help`.

## 5. Validate the exe

After building:

```powershell
dist\hcz-das-view\hcz-das-view.exe --help
dist\hcz-das-view\hcz-das-view.exe
```

Manual validation should include opening a small local sample and checking that
metadata, preview, waveform, spectrum, FK, and Analysis panels still work.

## 6. Do not package repository artifacts

Do not commit or bundle:

- real DAS files;
- `local_validation_paths.txt`;
- `validation_outputs/`;
- `outputs/`;
- generated JSON/CSV/image files;
- `build/`, `dist/`, wheels, archives, or exe files.
- `.tmp_release_venv/` or other local clean-install validation environments.

## 7. Current limitations

- CI does not yet build Windows executables automatically.
- The executable is not code-signed.
- Large-file performance still requires local validation.
- PyInstaller output may depend on the local Conda/Python environment.
- Clean-environment install checks with `--no-deps` validate package metadata
  and entry point generation, but runtime imports still require dependencies
  such as numpy and scipy.
