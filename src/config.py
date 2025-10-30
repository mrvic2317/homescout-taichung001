"""Configuration helpers for VicBot."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class BotConfig:
    token: str
    default_report_channel_id: Optional[int]
    timezone: str = "Asia/Taipei"


def load_config() -> BotConfig:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable must be set")

    channel_raw = os.getenv("REPORT_CHANNEL_ID")
    channel_id = int(channel_raw) if channel_raw else None

    tz = os.getenv("TIMEZONE", "Asia/Taipei")

    return BotConfig(token=token, default_report_channel_id=channel_id, timezone=tz)
