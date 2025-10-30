"""Utility helpers for parsing and formatting command inputs."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

from dateutil import parser


def parse_range(value: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    if not value:
        return None, None
    if "-" not in value:
        try:
            number = int(value)
        except ValueError:
            return None, None
        return number, number
    start, end = value.split("-", 1)
    try:
        start_num = int(start) if start else None
        end_num = int(end) if end else None
    except ValueError:
        return None, None
    return start_num, end_num


def parse_float_range(value: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    if not value:
        return None, None
    if "-" not in value:
        try:
            number = float(value)
        except ValueError:
            return None, None
        return number, number
    start, end = value.split("-", 1)
    try:
        start_num = float(start) if start else None
        end_num = float(end) if end else None
    except ValueError:
        return None, None
    return start_num, end_num


def parse_datetime(value: str) -> Optional[datetime]:
    try:
        return parser.parse(value)
    except (ValueError, parser.ParserError):
        return None
