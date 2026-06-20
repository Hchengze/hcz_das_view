"""Logging helpers."""

from __future__ import annotations

import logging


def get_logger(name: str = "das_view") -> logging.Logger:
    """Return a package logger without configuring global logging."""

    return logging.getLogger(name)
