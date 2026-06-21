"""Worker helpers for the optional PyQt5 GUI layer."""

from __future__ import annotations

from pathlib import Path

from das_view.analysis.service import (
    FKFilterServiceResult,
    FKServiceResult,
    SpectrumServiceResult,
    compute_fk_filter_for_file,
    compute_fk_for_file,
    compute_psd_for_file,
    compute_spectrogram_for_file,
    compute_spectrum_for_file,
)
from das_view.gui.models import FKAnalysisRequest, SpectrumAnalysisRequest
from das_view.io.data_service import SelectionResult, read_trace
from das_view.io.preview import PreviewResult, create_preview

try:  # Optional GUI dependency; non-GUI tests should import this module cleanly.
    from PyQt5 import QtCore
except ImportError:  # pragma: no cover - exercised in environments without PyQt5.
    QtCore = None  # type: ignore[assignment]


class PreviewWorker:
    """Thin callable wrapper around create_preview.

    The class intentionally contains no reader logic. It exists so the GUI can
    later move the same callable into QThread without changing file IO code.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        max_samples: int = 2000,
        max_channels: int = 500,
    ) -> None:
        self.path = Path(path)
        self.max_samples = int(max_samples)
        self.max_channels = int(max_channels)

    def run(self) -> PreviewResult:
        return create_preview(
            self.path,
            max_samples=self.max_samples,
            max_channels=self.max_channels,
        )


class WaveformWorker:
    """Thin callable wrapper around read_trace for waveform loading."""

    def __init__(
        self,
        path: str | Path,
        *,
        channels: int | tuple[int, ...],
        time_step: int = 1,
    ) -> None:
        self.path = Path(path)
        self.channels = channels
        self.time_step = int(time_step)

    def run(self) -> SelectionResult:
        return read_trace(
            self.path,
            channel=self.channels,
            downsample=(self.time_step, 1),
        )


class SpectrumWorker:
    """Thin callable wrapper around file-level spectrum analysis services."""

    def __init__(
        self,
        path: str | Path,
        *,
        request: SpectrumAnalysisRequest,
    ) -> None:
        self.path = Path(path)
        self.request = request

    def run(self) -> SpectrumServiceResult:
        request = self.request
        if request.analysis_type == "amplitude":
            return compute_spectrum_for_file(
                self.path,
                channel=request.channel,
                max_samples=request.max_samples,
                kind="amplitude",
                nfft=request.nfft,
            )
        if request.analysis_type == "power":
            return compute_spectrum_for_file(
                self.path,
                channel=request.channel,
                max_samples=request.max_samples,
                kind="power",
                nfft=request.nfft,
            )
        if request.analysis_type == "psd_periodogram":
            return compute_psd_for_file(
                self.path,
                channel=request.channel,
                max_samples=request.max_samples,
                method="periodogram",
                nfft=request.nfft,
                nperseg=request.nperseg,
                noverlap=request.noverlap,
            )
        if request.analysis_type == "psd_welch":
            return compute_psd_for_file(
                self.path,
                channel=request.channel,
                max_samples=request.max_samples,
                method="welch",
                nfft=request.nfft,
                nperseg=request.nperseg,
                noverlap=request.noverlap,
            )
        if request.analysis_type == "spectrogram":
            return compute_spectrogram_for_file(
                self.path,
                channel=request.channel,
                max_samples=request.max_samples,
                nperseg=request.nperseg,
                noverlap=request.noverlap,
            )
        raise ValueError(f"unsupported spectrum analysis type: {request.analysis_type!r}")


class FKWorker:
    """Thin callable wrapper around file-level FK analysis services."""

    def __init__(
        self,
        path: str | Path,
        *,
        request: FKAnalysisRequest,
    ) -> None:
        self.path = Path(path)
        self.request = request

    def run(self) -> FKServiceResult | FKFilterServiceResult:
        request = self.request
        if request.mode == "transform":
            return compute_fk_for_file(
                self.path,
                time_slice=request.bounded_time_slice(),
                channel_slice=request.bounded_channel_slice(),
                downsample=request.downsample,
                output=request.output,
            )
        if request.mode == "velocity_filter":
            return compute_fk_filter_for_file(
                self.path,
                time_slice=request.bounded_time_slice(),
                channel_slice=request.bounded_channel_slice(),
                downsample=request.downsample,
                vmin_mps=request.vmin_mps,
                vmax_mps=request.vmax_mps,
                pass_inside=request.pass_inside,
                return_fk=False,
            )
        raise ValueError(f"unsupported FK mode: {request.mode!r}")


if QtCore is not None:

    class _BaseQtWorker(QtCore.QObject):
        """Common soft-cancellable QObject worker behavior.

        Cancellation is cooperative. It cannot interrupt a synchronous reader
        call already in progress, but it prevents completed results from being
        emitted as successful GUI results after cancellation was requested.
        """

        started = QtCore.pyqtSignal()
        progress = QtCore.pyqtSignal(str, int)
        failed = QtCore.pyqtSignal(str)
        cancelled = QtCore.pyqtSignal()

        def __init__(self) -> None:
            super().__init__()
            self._cancel_requested = False

        def cancel(self) -> None:
            self._cancel_requested = True

        def is_cancelled(self) -> bool:
            return self._cancel_requested

        def _emit_cancelled_if_requested(self) -> bool:
            if self._cancel_requested:
                self.cancelled.emit()
                return True
            return False


    class QtPreviewWorker(_BaseQtWorker):
        """QObject worker that runs create_preview in a QThread."""

        finished = QtCore.pyqtSignal(object)

        def __init__(
            self,
            path: str | Path,
            *,
            max_samples: int = 2000,
            max_channels: int = 500,
        ) -> None:
            super().__init__()
            self.worker = PreviewWorker(
                path,
                max_samples=max_samples,
                max_channels=max_channels,
            )

        @QtCore.pyqtSlot()
        def run(self) -> None:
            self.started.emit()
            self.progress.emit("Loading preview metadata", 25)
            if self._emit_cancelled_if_requested():
                return
            try:
                result = self.worker.run()
            except Exception as exc:  # noqa: BLE001 - worker boundary reports all errors.
                if self._emit_cancelled_if_requested():
                    return
                self.failed.emit(_format_worker_error(exc))
                return
            self.progress.emit("Preview loaded", 100)
            if self._emit_cancelled_if_requested():
                return
            self.finished.emit(result)


    class QtWaveformWorker(_BaseQtWorker):
        """QObject worker that runs read_trace in a QThread."""

        finished = QtCore.pyqtSignal(object)

        def __init__(
            self,
            path: str | Path,
            *,
            channels: int | tuple[int, ...],
            time_step: int = 1,
        ) -> None:
            super().__init__()
            self.worker = WaveformWorker(path, channels=channels, time_step=time_step)

        @QtCore.pyqtSlot()
        def run(self) -> None:
            self.started.emit()
            self.progress.emit("Loading waveform data", 25)
            if self._emit_cancelled_if_requested():
                return
            try:
                result = self.worker.run()
            except Exception as exc:  # noqa: BLE001 - worker boundary reports all errors.
                if self._emit_cancelled_if_requested():
                    return
                self.failed.emit(_format_worker_error(exc))
                return
            self.progress.emit("Waveform loaded", 100)
            if self._emit_cancelled_if_requested():
                return
            self.finished.emit(result)


    class QtSpectrumWorker(_BaseQtWorker):
        """QObject worker that runs spectrum analysis services in a QThread."""

        finished = QtCore.pyqtSignal(object)

        def __init__(
            self,
            path: str | Path,
            *,
            request: SpectrumAnalysisRequest,
        ) -> None:
            super().__init__()
            self.worker = SpectrumWorker(path, request=request)

        @QtCore.pyqtSlot()
        def run(self) -> None:
            self.started.emit()
            self.progress.emit("Computing spectrum", 25)
            if self._emit_cancelled_if_requested():
                return
            try:
                result = self.worker.run()
            except Exception as exc:  # noqa: BLE001 - worker boundary reports all errors.
                if self._emit_cancelled_if_requested():
                    return
                self.failed.emit(_format_worker_error(exc))
                return
            self.progress.emit("Spectrum computed", 100)
            if self._emit_cancelled_if_requested():
                return
            self.finished.emit(result)


    class QtFKWorker(_BaseQtWorker):
        """QObject worker that runs FK analysis services in a QThread."""

        finished = QtCore.pyqtSignal(object)

        def __init__(
            self,
            path: str | Path,
            *,
            request: FKAnalysisRequest,
        ) -> None:
            super().__init__()
            self.worker = FKWorker(path, request=request)

        @QtCore.pyqtSlot()
        def run(self) -> None:
            self.started.emit()
            self.progress.emit("Computing FK", 25)
            if self._emit_cancelled_if_requested():
                return
            try:
                result = self.worker.run()
            except Exception as exc:  # noqa: BLE001 - worker boundary reports all errors.
                if self._emit_cancelled_if_requested():
                    return
                self.failed.emit(_format_worker_error(exc))
                return
            self.progress.emit("FK task computed", 100)
            if self._emit_cancelled_if_requested():
                return
            self.finished.emit(result)

else:

    class QtPreviewWorker:  # type: ignore[no-redef]
        """Placeholder that fails only when Qt worker construction is requested."""

        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            raise ImportError("PyQt5 is required to use QtPreviewWorker")


    class QtWaveformWorker:  # type: ignore[no-redef]
        """Placeholder that fails only when Qt worker construction is requested."""

        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            raise ImportError("PyQt5 is required to use QtWaveformWorker")


    class QtSpectrumWorker:  # type: ignore[no-redef]
        """Placeholder that fails only when Qt worker construction is requested."""

        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            raise ImportError("PyQt5 is required to use QtSpectrumWorker")


    class QtFKWorker:  # type: ignore[no-redef]
        """Placeholder that fails only when Qt worker construction is requested."""

        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            raise ImportError("PyQt5 is required to use QtFKWorker")


def _format_worker_error(error: BaseException) -> str:
    message = str(error).strip()
    if not message:
        message = error.__class__.__name__
    return f"{error.__class__.__name__}: {message}"
