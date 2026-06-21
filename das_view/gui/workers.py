"""Worker helpers for the optional PyQt5 GUI layer."""

from __future__ import annotations

from pathlib import Path

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

else:

    class QtPreviewWorker:  # type: ignore[no-redef]
        """Placeholder that fails only when Qt worker construction is requested."""

        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            raise ImportError("PyQt5 is required to use QtPreviewWorker")


    class QtWaveformWorker:  # type: ignore[no-redef]
        """Placeholder that fails only when Qt worker construction is requested."""

        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            raise ImportError("PyQt5 is required to use QtWaveformWorker")


def _format_worker_error(error: BaseException) -> str:
    message = str(error).strip()
    if not message:
        message = error.__class__.__name__
    return f"{error.__class__.__name__}: {message}"
