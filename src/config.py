"""Configuration helpers for VicBot."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class BotConfig:
    token: str
    default_report_channel_id: Optional[int]
    announcement_channel_id: Optional[int] = None
    announce_timeout_hours: int = 1
    timezone: str = "Asia/Taipei"
    # 新成員加入設定
    auto_assign_role_name: str = "客戶"  # 自動指派的角色名稱
    welcome_channel_id: Optional[int] = None  # 新成員歡迎頻道 ID
    system_log_channel_id: Optional[int] = None  # 系統日誌頻道 ID
    error_log_channel_id: Optional[int] = None  # 異常警告頻道 ID
    # 房價查詢設定
    price_query_enabled: bool = True  # 是否啟用房價查詢
    price_cache_ttl_hours: int = 24  # 快取有效期限（小時）
    welcome_message: str = (
        "🎉 歡迎加入 HomescoutTaiChung！\n\n"
        "您已被自動指派「客戶」角色，可以存取以下頻道：\n\n"
        "📢 **資訊頻道**\n"
        "• #公告 - 重要訊息公告\n"
        "• #資源 - 房源資源分享\n"
        "• #常見問題 - 常見問題解答\n\n"
        "💬 **互動頻道**\n"
        "• #一般 - 一般討論\n"
        "• #新房推播 - 最新房源推播\n"
        "• #找房需求 - 發布找房需求\n\n"
        "🤖 **Bot 指令說明**\n"
        "• `!監控新增 <區域> <價格範圍> <坪數範圍>` - 新增房源監控\n"
        "• `!監控列表` - 查看您的監控條件\n"
        "• `!物件查詢 <區域> <價格範圍> <坪數範圍>` - 搜尋房源\n"
        "• `!客戶新增 <姓名> <預算範圍> <偏好區域>` - 新增客戶資料\n\n"
        "如有任何問題，請聯繫管理員。祝您找到理想的房子！ 🏠"
    )


def load_config() -> BotConfig:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable must be set")

    channel_raw = os.getenv("REPORT_CHANNEL_ID")
    channel_id = int(channel_raw) if channel_raw else None

    announcement_raw = os.getenv("ANNOUNCEMENT_CHANNEL_ID")
    announcement_id = int(announcement_raw) if announcement_raw else None

    timeout_raw = os.getenv("ANNOUNCE_TIMEOUT_HOURS")
    timeout_hours = int(timeout_raw) if timeout_raw else 1

    tz = os.getenv("TIMEZONE", "Asia/Taipei")

    # 新成員加入設定
    auto_role = os.getenv("AUTO_ASSIGN_ROLE_NAME", "客戶")

    # 日誌與歡迎頻道
    welcome_channel_raw = os.getenv("WELCOME_CHANNEL_ID")
    welcome_channel_id = int(welcome_channel_raw) if welcome_channel_raw else None

    system_log_raw = os.getenv("SYSTEM_LOG_CHANNEL_ID")
    system_log_id = int(system_log_raw) if system_log_raw else None

    error_log_raw = os.getenv("ERROR_LOG_CHANNEL_ID")
    error_log_id = int(error_log_raw) if error_log_raw else None

    # 房價查詢設定
    price_query_enabled_raw = os.getenv("PRICE_QUERY_ENABLED", "true")
    price_query_enabled = price_query_enabled_raw.lower() in ("true", "1", "yes")

    price_cache_ttl_raw = os.getenv("PRICE_CACHE_TTL_HOURS")
    price_cache_ttl = int(price_cache_ttl_raw) if price_cache_ttl_raw else 24

    welcome_msg = os.getenv("WELCOME_MESSAGE")
    if not welcome_msg:
        welcome_msg = (
            "🎉 歡迎加入 HomescoutTaiChung！\n\n"
            "您已被自動指派「客戶」角色，可以存取以下頻道：\n\n"
            "📢 **資訊頻道**\n"
            "• #公告 - 重要訊息公告\n"
            "• #資源 - 房源資源分享\n"
            "• #常見問題 - 常見問題解答\n\n"
            "💬 **互動頻道**\n"
            "• #一般 - 一般討論\n"
            "• #新房推播 - 最新房源推播\n"
            "• #找房需求 - 發布找房需求\n\n"
            "🤖 **Bot 指令說明**\n"
            "• `!監控新增 <區域> <價格範圍> <坪數範圍>` - 新增房源監控\n"
            "• `!監控列表` - 查看您的監控條件\n"
            "• `!物件查詢 <區域> <價格範圍> <坪數範圍>` - 搜尋房源\n"
            "• `!客戶新增 <姓名> <預算範圍> <偏好區域>` - 新增客戶資料\n\n"
            "如有任何問題，請聯繫管理員。祝您找到理想的房子！ 🏠"
        )

    return BotConfig(
        token=token,
        default_report_channel_id=channel_id,
        announcement_channel_id=announcement_id,
        announce_timeout_hours=timeout_hours,
        timezone=tz,
        auto_assign_role_name=auto_role,
        welcome_channel_id=welcome_channel_id,
        system_log_channel_id=system_log_id,
        error_log_channel_id=error_log_id,
        price_query_enabled=price_query_enabled,
        price_cache_ttl_hours=price_cache_ttl,
        welcome_message=welcome_msg,
    )
