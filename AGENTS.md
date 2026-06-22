# DAS View Agent Guide

## Project goal

das_view is the new, maintainable DAS Viewer / DAS Analysis package for this workspace. It should grow from a small, testable baseline into a package that can read DAS data, expose metadata, plot time-channel data, waveform traces, spectra, spectrograms, and FK views, run common preprocessing and DAS analysis, provide an optional GUI, and stay testable, documented, packageable, and maintainable.

本项目定位为 DAS 数据查看与分析软件包，不是面波成像、MASW、F-J 或频散拾取软件。

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
- GUI must not directly implement complex algorithms.
- GUI must not depend on concrete HDF5 internal paths; it should call reader/core APIs.
- Large files must be handled with slicing, downsampling, or lazy-access plans before full visualization.
- Prefer explicit exceptions from das_view.core.exceptions.

## Testing requirements

- Add or update tests for metadata, dimension validation, readers, registry, processing, filters, and analysis.
- Use small synthetic data where real DAS data is unavailable.
- GUI tests may be deferred, but GUI-independent logic must be testable without PyQt5.
- Run python -m pytest after meaningful code changes when pytest is available.

## Documentation requirements

- Keep docs/ to eight files or fewer unless the project owner approves expansion.
- docs/09_tutorial_user_manual.ipynb is the allowed Jupyter tutorial/user manual
  in addition to the markdown docs.
- If a development round adds mature, stable user-facing functionality, update
  docs/09_tutorial_user_manual.ipynb in the same round.
- The tutorial notebook should explain method principles, key formulas, CLI
  examples, GUI workflow, and interpretation boundaries. It must not include
  development process notes, test runs, commit history, real data paths, or
  private local paths.
- Update docs/05_development_log.md every development round.
- Update architecture, format, and testing docs when interfaces or assumptions change.

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
