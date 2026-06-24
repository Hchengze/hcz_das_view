"""Print a manual GUI validation checklist for release-candidate signoff."""

from __future__ import annotations

import argparse


CHECKLIST_ITEMS = (
    "启动 GUI: hcz-das-view",
    "打开 ZD HDF5 / Puniu DAT",
    "检查 metadata summary",
    "检查 estimated full array size",
    "检查 safe selection preset",
    "检查 Waterfall Matplotlib backend",
    "检查 Waterfall PyQtGraph experimental backend",
    "检查 Waveform tab",
    "检查 Spectrum tab",
    "检查 FK tab",
    "检查 Analysis tab",
    "运行 Statistics",
    "运行 QC report",
    "运行 Bad channels",
    "运行 Multiband summary",
    "运行 Denoise report",
    "运行 Moveout summary",
    "运行 Directional energy",
    "检查 large-file warning",
    "检查 cancel / stale result",
    "检查 JSON export",
    "检查 CSV export",
    "检查 no-result export disabled",
    "关闭 / 重新打开文件后旧结果清空",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Print the GUI manual validation checklist.")
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Render the checklist as Markdown instead of plain text.",
    )
    return parser


def format_checklist(*, markdown: bool = False) -> str:
    if markdown:
        lines = ["# GUI manual validation checklist", ""]
        lines.extend(f"- {item}" for item in CHECKLIST_ITEMS)
        lines.append("")
        lines.append("RC signoff: GUI manual checklist completed, no stale results, no real paths.")
        return "\n".join(lines)
    return "\n".join(CHECKLIST_ITEMS)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(format_checklist(markdown=args.markdown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
