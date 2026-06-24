"""Lightweight GUI translation helpers.

This module intentionally avoids Qt translation files so the GUI can switch
between a small Chinese/English dictionary without affecting CLI or core APIs.
"""

from __future__ import annotations

from typing import Final

DEFAULT_LANGUAGE: Final = "zh_CN"
SUPPORTED_LANGUAGES: Final = ("zh_CN", "en_US")

_CURRENT_LANGUAGE = DEFAULT_LANGUAGE

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "app.title": {
        "zh_CN": "HCZ DAS View",
        "en_US": "HCZ DAS View",
    },
    "language": {
        "zh_CN": "语言",
        "en_US": "Language",
    },
    "language.zh_CN": {
        "zh_CN": "中文",
        "en_US": "Chinese",
    },
    "language.en_US": {
        "zh_CN": "English",
        "en_US": "English",
    },
    "open_file": {
        "zh_CN": "打开文件",
        "en_US": "Open File",
    },
    "file_menu": {
        "zh_CN": "文件",
        "en_US": "File",
    },
    "exit": {
        "zh_CN": "退出",
        "en_US": "Exit",
    },
    "file_information": {
        "zh_CN": "文件信息",
        "en_US": "File information",
    },
    "metadata": {
        "zh_CN": "元数据",
        "en_US": "Metadata",
    },
    "ready": {
        "zh_CN": "就绪",
        "en_US": "Ready",
    },
    "no_file_loaded": {
        "zh_CN": "未加载文件。",
        "en_US": "No file loaded.",
    },
    "metadata_prompt": {
        "zh_CN": "打开支持的 DAS 文件以查看元数据。",
        "en_US": "Open a supported DAS file to view metadata.",
    },
    "safe_preview": {
        "zh_CN": "安全预览",
        "en_US": "Safe preview",
    },
    "analysis_safe_default": {
        "zh_CN": "分析安全默认值",
        "en_US": "Analysis safe default",
    },
    "max_samples": {
        "zh_CN": "最大采样点",
        "en_US": "Max samples",
    },
    "max_channels": {
        "zh_CN": "最大通道数",
        "en_US": "Max channels",
    },
    "waterfall": {
        "zh_CN": "瀑布图",
        "en_US": "Waterfall",
    },
    "waveform": {
        "zh_CN": "波形",
        "en_US": "Waveform",
    },
    "spectrum": {
        "zh_CN": "频谱",
        "en_US": "Spectrum",
    },
    "fk": {
        "zh_CN": "FK",
        "en_US": "FK",
    },
    "analysis": {
        "zh_CN": "分析",
        "en_US": "Analysis",
    },
    "display_backend": {
        "zh_CN": "显示后端",
        "en_US": "Display backend",
    },
    "matplotlib": {
        "zh_CN": "Matplotlib",
        "en_US": "Matplotlib",
    },
    "pyqtgraph_experimental": {
        "zh_CN": "PyQtGraph 实验模式",
        "en_US": "PyQtGraph experimental",
    },
    "pyqtgraph_unavailable": {
        "zh_CN": "PyQtGraph 实验模式（需安装 display extra）",
        "en_US": "PyQtGraph experimental (install display extra)",
    },
    "axis_mode": {
        "zh_CN": "横轴模式",
        "en_US": "Axis mode",
    },
    "axis_channel": {
        "zh_CN": "通道",
        "en_US": "Channel",
    },
    "axis_distance": {
        "zh_CN": "距离",
        "en_US": "Distance",
    },
    "axis_channel_label": {
        "zh_CN": "通道",
        "en_US": "Channel",
    },
    "axis_distance_label": {
        "zh_CN": "距离 (m)",
        "en_US": "Distance (m)",
    },
    "time_start": {
        "zh_CN": "时间起点",
        "en_US": "Time start",
    },
    "time_stop": {
        "zh_CN": "时间终点",
        "en_US": "Time stop",
    },
    "time_step": {
        "zh_CN": "时间步长",
        "en_US": "Time step",
    },
    "channel_index": {
        "zh_CN": "通道号",
        "en_US": "Channel index",
    },
    "channel_start": {
        "zh_CN": "通道起点",
        "en_US": "Channel start",
    },
    "channel_stop": {
        "zh_CN": "通道终点",
        "en_US": "Channel stop",
    },
    "channel_step": {
        "zh_CN": "通道步长",
        "en_US": "Channel step",
    },
    "analysis_type": {
        "zh_CN": "分析类型",
        "en_US": "Analysis type",
    },
    "spectrum_method": {
        "zh_CN": "频谱方法",
        "en_US": "Analysis type",
    },
    "nfft": {
        "zh_CN": "nfft",
        "en_US": "nfft",
    },
    "nperseg": {
        "zh_CN": "分段长度",
        "en_US": "nperseg",
    },
    "noverlap": {
        "zh_CN": "重叠长度",
        "en_US": "noverlap",
    },
    "fk_mode": {
        "zh_CN": "FK 模式",
        "en_US": "FK mode",
    },
    "output_mode": {
        "zh_CN": "输出模式",
        "en_US": "Output mode",
    },
    "velocity_min": {
        "zh_CN": "最小速度",
        "en_US": "vmin",
    },
    "velocity_max": {
        "zh_CN": "最大速度",
        "en_US": "vmax",
    },
    "percentiles": {
        "zh_CN": "百分位",
        "en_US": "Percentiles",
    },
    "nan_policy": {
        "zh_CN": "NaN 策略",
        "en_US": "NaN policy",
    },
    "bands_hz": {
        "zh_CN": "频带 Hz",
        "en_US": "Bands Hz",
    },
    "frequency_range_hz": {
        "zh_CN": "频率范围 Hz",
        "en_US": "Frequency range Hz",
    },
    "rolloff": {
        "zh_CN": "滚降",
        "en_US": "Rolloff",
    },
    "sta_samples": {
        "zh_CN": "STA 采样点",
        "en_US": "STA samples",
    },
    "lta_samples": {
        "zh_CN": "LTA 采样点",
        "en_US": "LTA samples",
    },
    "trigger_on": {
        "zh_CN": "触发阈值",
        "en_US": "Trigger on",
    },
    "trigger_off": {
        "zh_CN": "结束阈值",
        "en_US": "Trigger off",
    },
    "envelope_threshold": {
        "zh_CN": "包络阈值",
        "en_US": "Envelope threshold",
    },
    "smooth_samples": {
        "zh_CN": "平滑采样点",
        "en_US": "Smooth samples",
    },
    "min_duration": {
        "zh_CN": "最短持续",
        "en_US": "Min duration",
    },
    "merge_gap": {
        "zh_CN": "合并间隔",
        "en_US": "Merge gap",
    },
    "max_events": {
        "zh_CN": "最大事件数",
        "en_US": "Max events",
    },
    "manual_roi": {
        "zh_CN": "手动 ROI",
        "en_US": "Manual ROI",
    },
    "roi_pad_samples": {
        "zh_CN": "ROI 采样点扩展",
        "en_US": "ROI pad samples",
    },
    "roi_pad_channels": {
        "zh_CN": "ROI 通道扩展",
        "en_US": "ROI pad channels",
    },
    "max_rois": {
        "zh_CN": "最大 ROI 数",
        "en_US": "Max ROIs",
    },
    "window_samples": {
        "zh_CN": "窗口采样点",
        "en_US": "Window samples",
    },
    "step_samples": {
        "zh_CN": "步进采样点",
        "en_US": "Step samples",
    },
    "channel_lag": {
        "zh_CN": "通道滞后",
        "en_US": "Channel lag",
    },
    "denoise_workflow": {
        "zh_CN": "去噪流程",
        "en_US": "Denoise workflow",
    },
    "statistics_axis": {
        "zh_CN": "统计轴",
        "en_US": "Statistics axis",
    },
    "run": {
        "zh_CN": "运行",
        "en_US": "Run",
    },
    "cancel": {
        "zh_CN": "取消",
        "en_US": "Cancel",
    },
    "clear": {
        "zh_CN": "清空",
        "en_US": "Clear",
    },
    "run_spectrum": {
        "zh_CN": "运行频谱",
        "en_US": "Run spectrum",
    },
    "run_fk": {
        "zh_CN": "运行 FK",
        "en_US": "Run FK",
    },
    "run_analysis": {
        "zh_CN": "运行分析",
        "en_US": "Run analysis",
    },
    "plot_waveform": {
        "zh_CN": "绘制波形",
        "en_US": "Plot waveform",
    },
    "export_json": {
        "zh_CN": "导出 JSON",
        "en_US": "Export JSON",
    },
    "export_csv": {
        "zh_CN": "导出 CSV",
        "en_US": "Export CSV",
    },
    "clear_results": {
        "zh_CN": "清空结果",
        "en_US": "Clear results",
    },
    "no_preview_loaded": {
        "zh_CN": "未加载预览",
        "en_US": "No preview loaded",
    },
    "no_waveform_loaded": {
        "zh_CN": "未加载波形",
        "en_US": "No waveform loaded",
    },
    "no_spectrum_loaded": {
        "zh_CN": "未加载频谱",
        "en_US": "No spectrum loaded",
    },
    "no_fk_loaded": {
        "zh_CN": "未加载 FK 结果",
        "en_US": "No FK result loaded",
    },
    "statistics": {
        "zh_CN": "统计",
        "en_US": "Statistics",
    },
    "band_energy": {
        "zh_CN": "频带能量",
        "en_US": "Band energy",
    },
    "spectral_attributes": {
        "zh_CN": "频谱属性",
        "en_US": "Spectral attributes",
    },
    "events_stalta": {
        "zh_CN": "事件候选 - STA/LTA",
        "en_US": "Event candidates - STA/LTA",
    },
    "events_envelope": {
        "zh_CN": "事件候选 - 包络阈值",
        "en_US": "Event candidates - Envelope threshold",
    },
    "roi_statistics": {
        "zh_CN": "ROI 统计",
        "en_US": "ROI statistics",
    },
    "qc_report": {
        "zh_CN": "质量控制报告",
        "en_US": "QC report",
    },
    "bad_channels": {
        "zh_CN": "异常通道",
        "en_US": "Bad channels",
    },
    "multiband_summary": {
        "zh_CN": "多频带摘要",
        "en_US": "Multiband map summary",
    },
    "denoise_report": {
        "zh_CN": "去噪报告",
        "en_US": "Denoise report",
    },
    "moveout_summary": {
        "zh_CN": "时距辅助分析",
        "en_US": "Moveout summary",
    },
    "directional_energy": {
        "zh_CN": "方向能量",
        "en_US": "Directional energy",
    },
}

_TOOLTIPS: dict[str, dict[str, str]] = {
    "language": {
        "zh_CN": "切换 GUI 显示语言。默认中文，英文仍可用于对照。",
        "en_US": "Switch the GUI language. Chinese is the default; English remains available.",
    },
    "open_file": {
        "zh_CN": "打开 DAS 数据文件，支持当前 reader 已识别的 HDF5 / DAT 格式。",
        "en_US": "Open a DAS data file supported by the current HDF5 / DAT readers.",
    },
    "max_samples": {
        "zh_CN": "限制预览读取的最大时间采样点，避免误读超大文件。",
        "en_US": "Limit the maximum time samples read for preview to avoid accidental large reads.",
    },
    "max_channels": {
        "zh_CN": "限制预览读取的最大通道数，适合先做安全浏览。",
        "en_US": "Limit the maximum channels read for preview for a safe first look.",
    },
    "display_backend": {
        "zh_CN": "选择瀑布图显示后端。Matplotlib 最稳定；PyQtGraph 是实验功能，若显示异常可切回 Matplotlib。",
        "en_US": "Choose the waterfall display backend. Matplotlib is stable; PyQtGraph is experimental and can be switched back if display looks wrong.",
    },
    "axis_mode": {
        "zh_CN": "选择瀑布图横轴显示方式：通道号，或在 dx 可用时按距离显示。",
        "en_US": "Choose the waterfall x-axis: channel number, or distance when dx is available.",
    },
    "waveform_channel": {
        "zh_CN": "输入零基通道号，可用逗号输入多个通道，例如 10,20,30。",
        "en_US": "Enter zero-based channel indices; comma-separated values such as 10,20,30 are allowed.",
    },
    "waveform_time_step": {
        "zh_CN": "波形读取的时间降采样步长，大文件建议增大。",
        "en_US": "Time downsampling step for waveform reads; increase it for large files.",
    },
    "run_waveform": {
        "zh_CN": "读取所选通道并绘制波形，运行前会进行选择范围检查。",
        "en_US": "Read selected channels and plot waveforms after a selection-size check.",
    },
    "spectrum_channel": {
        "zh_CN": "频谱分析使用的单个零基通道号。",
        "en_US": "Single zero-based channel index used for spectrum analysis.",
    },
    "spectrum_method": {
        "zh_CN": "选择频谱、PSD 或时频图方法。",
        "en_US": "Choose spectrum, PSD, or spectrogram method.",
    },
    "run_spectrum": {
        "zh_CN": "对单通道运行有界频谱分析。",
        "en_US": "Run bounded single-channel spectrum analysis.",
    },
    "fk_run": {
        "zh_CN": "运行有界 FK 任务；FK 结果是波场查看辅助，不是定位或反演。",
        "en_US": "Run a bounded FK task; FK output is a wavefield review aid, not localization or inversion.",
    },
    "analysis_type": {
        "zh_CN": "选择分析任务。QC、去噪、moveout 等都是数据复核辅助功能。",
        "en_US": "Choose the analysis task. QC, denoise, and moveout are data-review aids.",
    },
    "run_analysis": {
        "zh_CN": "运行当前分析任务。运行前会估算本次选择的数据大小，避免误读超大文件。",
        "en_US": "Run the selected analysis task after estimating the selection size.",
    },
    "cancel": {
        "zh_CN": "请求取消当前后台任务。已进入 reader 或计算内部的步骤可能需要结束后才会停止应用结果。",
        "en_US": "Request cancellation for the current background task. Reader or calculation calls may finish before results are discarded.",
    },
    "clear_results": {
        "zh_CN": "清空当前分析摘要、表格和导出状态。",
        "en_US": "Clear the current analysis summary, table, and export state.",
    },
    "export_json": {
        "zh_CN": "导出当前分析结果为 JSON，不包含原始大数据。",
        "en_US": "Export the current analysis result as JSON without raw large data.",
    },
    "export_csv": {
        "zh_CN": "导出当前表格行到 CSV，不包含原始大数据。",
        "en_US": "Export the current table rows to CSV without raw large data.",
    },
    "time_range": {
        "zh_CN": "可选时间采样范围。留空时使用安全默认范围。",
        "en_US": "Optional time-sample range. Blank values use safe defaults.",
    },
    "channel_range": {
        "zh_CN": "可选通道范围。留空时使用安全默认范围。",
        "en_US": "Optional channel range. Blank values use safe defaults.",
    },
    "selection_step": {
        "zh_CN": "读取步长/降采样设置，可减少内存压力。",
        "en_US": "Read step/downsampling setting to reduce memory pressure.",
    },
    "memory_guard": {
        "zh_CN": "运行前会估算本次选择的数据大小，超过阈值会提示或阻止。",
        "en_US": "The GUI estimates selected data size before running and warns or blocks oversized selections.",
    },
    "moveout_boundary": {
        "zh_CN": "Moveout 是波场辅助属性，不代表真实地下速度或震源位置。",
        "en_US": "Moveout is a wavefield auxiliary attribute, not measured physical velocity or source location.",
    },
}


def get_supported_languages() -> tuple[str, ...]:
    """Return supported GUI language codes."""

    return SUPPORTED_LANGUAGES


def get_default_language() -> str:
    """Return the default GUI language code."""

    return DEFAULT_LANGUAGE


def get_language() -> str:
    """Return the current process-local GUI language code."""

    return _CURRENT_LANGUAGE


def set_language(language_code: str) -> str:
    """Set and return the active GUI language code."""

    global _CURRENT_LANGUAGE
    normalized = _normalize_language(language_code)
    _CURRENT_LANGUAGE = normalized
    return normalized


def translate(key: str, language_code: str | None = None) -> str:
    """Translate a GUI text key with stable fallback to English or the key."""

    language = _normalize_language(language_code or _CURRENT_LANGUAGE, fallback=DEFAULT_LANGUAGE)
    values = _TRANSLATIONS.get(str(key), {})
    return values.get(language) or values.get("en_US") or str(key)


def tooltip(key: str, language_code: str | None = None) -> str:
    """Translate a GUI tooltip key with stable fallback."""

    language = _normalize_language(language_code or _CURRENT_LANGUAGE, fallback=DEFAULT_LANGUAGE)
    values = _TOOLTIPS.get(str(key), {})
    return values.get(language) or values.get("en_US") or str(key)


def translation_keys() -> tuple[str, ...]:
    """Return translation keys for tests."""

    return tuple(sorted(_TRANSLATIONS))


def tooltip_keys() -> tuple[str, ...]:
    """Return tooltip keys for tests."""

    return tuple(sorted(_TOOLTIPS))


def _normalize_language(language_code: str, *, fallback: str | None = None) -> str:
    code = str(language_code).strip()
    if code in SUPPORTED_LANGUAGES:
        return code
    if fallback is not None:
        return fallback
    raise ValueError(f"unsupported GUI language: {language_code!r}")
