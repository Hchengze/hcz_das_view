# DAS View Agent Guide

## Project goal

das_view is the new, maintainable DAS Viewer / DAS Analysis package for this workspace. It should grow from a small, testable baseline into a package that can read DAS data, expose metadata, plot time-channel data, waveform traces, spectra, spectrograms, and FK views, run common preprocessing and DAS analysis, provide an optional GUI, and stay testable, documented, packageable, and maintainable.

本项目定位为 DAS 数据查看与分析软件包，不是面波成像、MASW、F-J
或频散拾取软件。
FK visualization and FK-domain smoke filtering may remain as DAS 2D wavefield inspection capabilities. They should not be treated as a mainline path toward specialized topic workflows. If those topic-specific methods are ever needed, they should be independent plugins or extensions outside the current core roadmap.

## Old code usage rules

- New work must not modify old_code/ in place.
- New runtime code must not import old_code.
- Old code is audit, rewrite, refactor, and verification reference only.
- If old code contains logic judged correct and valuable, it may be reimplemented in das_view, but the new implementation must follow the new interfaces, naming, tests, and documentation rules.
- Every migration from old code must be recorded in docs/05_development_log.md, including source path, reuse decision, new location, test status, and interface/dimension changes.

Required wording:

    New code must not import old_code.
    Old code is only a reference for audit, rewriting, refactoring, and validation.
    If a piece of old-code logic is judged correct and excellent, it may be reimplemented in das_view, but it must conform to the new interface, naming, testing, and documentation standards.

## Directory structure

    das_view/
    - core/
    - io/
    - processing/
    - analysis/
    - plotting/
    - gui/
    - utils/

Supporting directories:

    docs/
    tests/
    examples/

## Data dimension convention

All internal core arrays must use:

    data.shape == (n_samples, n_channels)

- Axis 0: time samples.
- Axis 1: spatial channel / fiber channel.
- Readers are responsible for converting external formats to this convention.
- If a source format uses another orientation, record the original shape/orientation in metadata extra_attrs.

## Coding rules

- Prefer small modules with single responsibilities.
- Keep IO, core data structures, processing, analysis, plotting, and GUI separated.
- Keep algorithm functions pure where practical.
- Core modules must not import PyQt5.
- Core, IO, processing, analysis, plotting, and plugins modules must not import
  PyQt5.
- GUI must not directly implement complex algorithms.
- GUI must not depend on concrete HDF5 internal paths; it should call reader/core APIs.
- Large files must be handled with slicing, downsampling, or lazy-access plans before full visualization.
- Do not default to full-array reads for large files. Prefer bounded
  selections, preview downsampling, metadata-only estimates, and explicit
  user limits.
- CLI and GUI workflows should expose or preserve bounded defaults such as
  max_samples, max_channels, and optional estimated-memory guards.
- Local performance smoke outputs, validation outputs, preview images, JSON,
  CSV, and path-list files are user artifacts and must not be committed.
- Real/private data paths may be used only for local validation and must not be
  written into docs, notebooks, handoff files, examples, or tests.
- Prefer explicit exceptions from das_view.core.exceptions.
- When adding more advanced DAS functionality, prefer general, testable,
  low-risk data-quality and feature-analysis helpers first.
- Deep-learning models, location, inversion, or specialized interpretation
  algorithms must remain deferred experimental/plugin work unless the project
  owner explicitly changes the roadmap.
- Do not present specialized algorithms as the mainline package direction.
- Level 4 denoising/enhancement work must use traditional, explainable,
  low-dependency methods only.
- Do not introduce training models, PyTorch, TensorFlow, or deep-learning
  denoising into the core package.
- Denoising/enhancement outputs must be described as signal enhancement or
  data-review aids, not geologic interpretation results.
- Level 5 moveout / apparent-velocity work must remain auxiliary attribute
  analysis only.
- Apparent velocity is not a ground-truth propagation velocity.
- Directional energy and FK-domain direction labels are review aids, not
  definitive physical propagation or geologic direction statements.
- Do not turn moveout attributes into source location, inversion, imaging, or
  interpretation workflows.
- Optional GPU acceleration must remain CPU-first and lazy. Do not import CuPy
  during `import das_view`; only import it inside explicit GPU backend helper
  calls. `backend="auto"` must not silently enable GPU in core/service/CLI
  workflows.
- GPU support must not introduce PyTorch, TensorFlow, training models, or
  deep-learning denoising into the core package. Phase 9A-style GPU work is
  compute acceleration only; GPU/OpenGL display acceleration belongs to a
  separate GUI/display phase.
- GPU diagnostics, numeric validation, and benchmark workflows must use
  synthetic data or bounded user-selected real-data windows only. Benchmark
  JSON/CSV/images and local timing outputs are user artifacts and must not be
  committed.

## Testing requirements

- Add or update tests for metadata, dimension validation, readers, registry, processing, filters, and analysis.
- Use small synthetic data where real DAS data is unavailable.
- GUI tests may be deferred, but GUI-independent logic must be testable without PyQt5.
- Run python -m pytest after meaningful code changes when pytest is available.
- GPU optional tests must pass without CuPy or GPU hardware. Tests for real
  GPU numerical equivalence should skip cleanly when CuPy is unavailable.
- CLI and CI smoke may run GPU diagnostics such as `hcz-das-gpu --info`, but
  they must not require CUDA devices or CuPy installation.

## Documentation requirements

- Keep docs/ to eight files or fewer unless the project owner approves expansion.
- docs/09_tutorial_user_manual.ipynb is the allowed Jupyter tutorial/user manual
  in addition to the markdown docs.
- If a development round adds mature, stable user-facing functionality, update
  docs/09_tutorial_user_manual.ipynb in the same round.
- The tutorial notebook should explain method principles, key formulas, CLI
  examples, GUI workflow including mature GUI panels, and interpretation
  boundaries. It must not include
  development process notes, test runs, commit history, real data paths, or
  private local paths.
- Update docs/05_development_log.md every development round.
- Update architecture, format, and testing docs when interfaces or assumptions change.
- Documentation and notebooks must not include real/private data paths.

## Packaging and release rules

- Packaging metadata lives in pyproject.toml and should remain compatible with
  standard pip installation.
- Installed CLI entry points should live under das_view/cli/ and call stable
  service-layer APIs instead of depending on examples/ as package API.
- GUI entry points may import PyQt5 only inside das_view/gui/ or GUI startup
  paths. Importing das_view or das_view.cli modules must not require PyQt5.
- Do not commit build/, dist/, wheel files, source archives, exe files, or
  *.egg-info directories.
- Do not commit clean-environment validation directories such as
  .tmp_release_venv/ or temporary pytest directories.
- Do not commit PyInstaller output. packaging/ may contain documentation,
  scripts, and specs only when they avoid local absolute paths and real data.
- Do not add CUDA-specific CuPy wheels to main dependencies. If optional GPU
  installation is documented, tell users to install the CuPy package matching
  their CUDA runtime, such as `cupy-cuda12x`.
- Release and artifact checks should keep benchmark outputs out of Git.
- Release rounds should check version metadata, full pytest, CLI help smoke,
  GUI help/launch smoke, example help smoke, clean venv install smoke,
  wheel/sdist build smoke, Windows packaging smoke where practical,
  README/notebook freshness, and staged artifact safety.
- CI workflows must not depend on real/private local data paths.
- CI workflows must not upload, commit, or publish real data or local
  validation outputs.
- Windows CI should use a repository-local `.tmp_pytest` directory to avoid
  default TEMP permission issues.
- Notebook safety, artifact safety, CLI help smoke, import-boundary tests, and
  packaging metadata checks should remain part of release quality gates.
- Release smoke workflows may build local wheel/sdist artifacts, but must not
  publish to PyPI or create an official release unless the project owner
  explicitly requests that release step.
- Release-candidate polish rounds may draft checklists, release notes, and
  validation workflows, but must not create tags, publish GitHub Releases,
  upload to PyPI, or stage release-validation outputs unless explicitly
  requested.
- Real-world validation package summaries, timing outputs, JSON/CSV files, and
  private path lists are local artifacts. They must not be committed, and real
  paths must not be written into docs, notebooks, handoff files, or examples.
- Release notes should be user-facing summaries, not development chronology or
  commit-by-commit logs.

## GUI large-file rules

- GUI workflows must not default to full-array reads for large DAS files.
- GUI file summaries should use metadata-only memory estimates and safe
  preview/analysis hints before users run heavier operations.
- GUI selection checks should be shared through PyQt-free model helpers where
  practical, then dispatched to service/data-service workers.
- GUI code may show user-readable warnings or block oversized selections, but
  it must not implement DAS analysis algorithms or reader internals.
- GUI exports must use shared export helpers, avoid default names derived from
  real absolute paths, and generated output files must not be committed.
- Real/private paths must not be written into docs or the tutorial notebook.

## Plugin and extension rules

- Plugin core code must not depend on PyQt5.
- Importing das_view must not scan external plugins.
- Entry point discovery must be explicit and on-demand.
- Plugin metadata and discovery must not read real DAS data or generate output
  artifacts.
- Built-in extension metadata may describe existing stable capabilities, but it
  must not execute analysis, plotting, reader IO, or GUI startup work.
- The plugin layer must not replace or break the existing reader registry,
  data service, analysis service, plotting helpers, or GUI APIs.
- Third-party extension interfaces should remain lightweight until validated
  with real external packages.

## Before and after each development round

Before:

1. Check current directory and whether Git is available.
2. Inspect existing files relevant to the task.
3. Avoid overwriting user changes.

After:

1. Run focused tests.
2. Report created/modified files.
3. Report Git status, or state clearly if the directory is not a Git repository.
4. Record old-code reuse decisions in the development log.

## Prohibited actions

- Do not import old_code from new runtime code.
- Do not copy large old GUI files into das_view.
- Do not add heavy optional dependencies to the core package without a clear reason.
- Do not put SEGY, SAC, or TDMS into the first core workflow before ZD HDF5 and Puniu DAT are stable.
- Do not silently change the internal data dimension convention.
