"""VicBot Discord bot implementation."""
from __future__ import annotations

# --- .env 載入（緊接在 future import 之後）---
from dotenv import load_dotenv
import os
load_dotenv()
print("DISCORD_TOKEN loaded?", bool(os.getenv("DISCORD_TOKEN")))
# ---------------------------------------------

import asyncio
import logging
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo
from typing import List, Optional, Dict, Tuple

import discord
from discord.ext import commands, tasks
from discord.utils import utcnow

from src import database
from src.config import BotConfig, load_config
from src.services import cases, clients, market, monitoring, viewings, price_query
from src.utils.formatting import parse_datetime, parse_float_range, parse_range

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True


class VicBot(commands.Bot):
    def __init__(self, *, config: BotConfig):
        super().__init__(command_prefix="!", intents=INTENTS)
        self.config = config
        self.local_tz = ZoneInfo(config.timezone)
        self._last_moi_sync_week: Optional[int] = None
        self._last_report_week: Optional[int] = None

        # 公告頻道違規計數與可配置項目
        self._channel_warnings: Dict[Tuple[int, int], int] = {}  # (guild_id, user_id) -> warnings
        self.announcement_channel_id: Optional[int] = config.announcement_channel_id
        self.announce_timeout_hours: int = config.announce_timeout_hours

        # 任務錯誤處理
        self.moi_sync_task.add_exception_type(Exception)
        self.weekly_report_task.add_exception_type(Exception)
        self.viewing_reminder_task.add_exception_type(Exception)

        # 房價查詢設定
        if config.price_query_enabled:
            price_query.set_cache_ttl(config.price_cache_ttl_hours)
            logger.info(f"房價查詢功能已啟用 | cache_ttl={config.price_cache_ttl_hours}小時")

    async def setup_hook(self) -> None:
        await database.init_db()
        self.moi_sync_task.start()
        self.weekly_report_task.start()
        self.viewing_reminder_task.start()

    async def on_ready(self) -> None:
        logger.info("VicBot 已上線，登入為 %s", self.user)

        # 自動檢查並下載房價資料（如果啟用）
        if self.config.price_query_enabled:
            await self._ensure_price_data()

    async def _log_to_discord(self, message: str, level: str = "info") -> None:
        """
        將日誌訊息發送到 Discord 頻道。

        Args:
            message: 日誌訊息內容
            level: 日誌等級 ("info", "warning", "error")
        """
        try:
            # 根據等級決定發送到哪個頻道
            if level in ("error", "critical"):
                channel_id = self.config.error_log_channel_id
                emoji = "🚨"
            else:
                channel_id = self.config.system_log_channel_id
                emoji = "ℹ️" if level == "info" else "⚠️"

            if not channel_id:
                return  # 未設定頻道 ID，不發送

            channel = self.get_channel(channel_id)
            if not channel:
                try:
                    channel = await self.fetch_channel(channel_id)
                except discord.NotFound:
                    logger.warning("日誌頻道不存在 | channel_id=%s", channel_id)
                    return
                except Exception as exc:
                    logger.error("取得日誌頻道失敗 | channel_id=%s | error=%s", channel_id, exc)
                    return

            # 格式化訊息
            timestamp = datetime.now(self.local_tz).strftime("%Y-%m-%d %H:%M:%S")
            formatted_msg = f"{emoji} `[{timestamp}]` {message}"

            # 如果訊息太長，分段發送
            if len(formatted_msg) > 2000:
                formatted_msg = formatted_msg[:1997] + "..."

            await channel.send(formatted_msg)

        except discord.Forbidden:
            logger.warning("無權限發送日誌到 Discord 頻道 | channel_id=%s", channel_id)
        except Exception as exc:
            logger.error("發送 Discord 日誌失敗 | error=%s", exc)

    async def _ensure_price_data(self) -> None:
        """
        確保房價資料已下載並最新。

        - 啟動時自動檢查
        - 若資料過期（7天），自動下載
        - 下載失敗時使用舊快取
        """
        try:
            logger.info("🔄 檢查房價資料更新...")

            from src.services import data_downloader

            # 檢查快取資訊
            cache_info = data_downloader.get_taichung_cache_info()

            if cache_info:
                if cache_info["is_valid"]:
                    logger.info(
                        f"✅ 房價資料快取有效 | "
                        f"last_modified={cache_info['last_modified']} | "
                        f"age={cache_info['age_days']}天 | "
                        f"expires_in={cache_info['expires_in_days']}天"
                    )
                    await self._log_to_discord(
                        f"房價資料快取有效（{cache_info['age_days']}天前更新，{cache_info['expires_in_days']}天後過期）",
                        level="info"
                    )
                else:
                    logger.info(
                        f"⚠️ 房價資料快取已過期 | "
                        f"age={cache_info['age_days']}天 | "
                        f"開始下載最新資料..."
                    )
                    await self._log_to_discord(
                        f"房價資料快取已過期（{cache_info['age_days']}天），正在下載最新資料...",
                        level="warning"
                    )

            # 確保資料可用（自動下載或使用快取）
            result_path = await data_downloader.ensure_taichung_data()

            if result_path:
                logger.info(f"✅ 房價資料已就緒 | path={result_path}")
                await self._log_to_discord(
                    f"✅ 房價資料已就緒",
                    level="info"
                )
            else:
                logger.error("❌ 房價資料下載失敗且無本地快取")
                await self._log_to_discord(
                    "❌ 房價資料下載失敗且無本地快取，房價查詢功能可能無法使用",
                    level="error"
                )

        except ImportError:
            logger.warning("⚠️ data_downloader 模組不可用，跳過自動下載")
        except Exception as exc:
            logger.error(f"❌ 房價資料檢查失敗 | error={exc}", exc_info=True)
            await self._log_to_discord(
                f"❌ 房價資料檢查失敗：{exc}",
                level="error"
            )

    async def on_message(self, message: discord.Message) -> None:
        # 先讓 Bot/自己略過；避免回圈與不必要處理
        if message.author.bot:
            return

        # 是否在公告頻道（ID 優先，名稱備援）
        in_announce = False
        announcement_channel = None
        if message.guild and isinstance(message.channel, discord.TextChannel):
            if self.announcement_channel_id:
                in_announce = (message.channel.id == self.announcement_channel_id)
                if in_announce:
                    announcement_channel = message.channel
            else:
                in_announce = (message.channel.name == "公告")
                if in_announce:
                    announcement_channel = message.channel

        # 非管理員在公告頻道發言 → 刪文 + 計次 + DM 警告 + 三犯禁言
        if in_announce and not message.author.guild_permissions.administrator:
            key = (message.guild.id, message.author.id)
            warnings = self._channel_warnings.get(key, 0) + 1
            self._channel_warnings[key] = warnings

            # 記錄違規事件
            logger.info(
                "公告頻道違規發言 | user_id=%s | guild_id=%s | channel_id=%s | warnings=%s",
                message.author.id,
                message.guild.id,
                message.channel.id,
                warnings,
            )

            # 刪除訊息
            try:
                await message.delete()
                logger.info("訊息已刪除 | user_id=%s | message_id=%s", message.author.id, message.id)
            except discord.DiscordException as exc:
                logger.error(
                    "刪除訊息失敗 | user_id=%s | message_id=%s | error=%s",
                    message.author.id,
                    message.id,
                    exc,
                )

            # 準備警告訊息
            if warnings == 1:
                warn_message = f"⚠️ 您於 #{message.channel.name} 頻道沒有發言權限。\n\n這是您的第 1 次警告。"
            elif warnings == 2:
                warn_message = f"⚠️ 您於 #{message.channel.name} 頻道沒有發言權限。\n\n這是您的第 2 次警告，再違規將被禁言 {self.announce_timeout_hours} 小時。"
            else:
                warn_message = f"⚠️ 您於 #{message.channel.name} 頻道沒有發言權限。\n\n這是您的第 {warnings} 次警告。"

            # 第 3 次違規執行禁言
            mute_applied = False
            if warnings == 3 and isinstance(message.author, discord.Member):
                until = utcnow() + timedelta(hours=self.announce_timeout_hours)  # tz-aware
                try:
                    await message.author.edit(timed_out_until=until)
                    mute_applied = True
                    # 禁言成功後重置警告計數
                    self._channel_warnings[key] = 0
                    logger.info(
                        "使用者已被禁言 | user_id=%s | guild_id=%s | duration_hours=%s | warnings_reset=True",
                        message.author.id,
                        message.guild.id,
                        self.announce_timeout_hours,
                    )
                except discord.DiscordException as exc:
                    logger.error(
                        "設定禁言失敗 | user_id=%s | guild_id=%s | error=%s",
                        message.author.id,
                        message.guild.id,
                        exc,
                    )

            # 更新私訊內容（如果禁言成功）
            if mute_applied:
                warn_message = f"⚠️ 您已在 #{message.channel.name} 頻道違規發言 3 次。\n\n您已被禁言 {self.announce_timeout_hours} 小時，警告次數已重置。"

            # 發送私訊警告
            try:
                await message.author.send(warn_message)
                logger.info("警告私訊已發送 | user_id=%s | warnings=%s", message.author.id, warnings)
            except discord.Forbidden:
                logger.warning(
                    "無法發送私訊（用戶關閉私訊） | user_id=%s | warnings=%s",
                    message.author.id,
                    warnings,
                )
            except discord.DiscordException as exc:
                logger.error(
                    "傳送警告訊息失敗 | user_id=%s | error=%s",
                    message.author.id,
                    exc,
                )

            # 禁言成功後在公告頻道發布公告
            if mute_applied and announcement_channel:
                try:
                    announcement_message = (
                        f"📢 使用者 <@{message.author.id}> 因違規發言 3 次，"
                        f"已被禁言 {self.announce_timeout_hours} 小時。"
                    )
                    await announcement_channel.send(announcement_message)
                    logger.info(
                        "禁言公告已發布 | user_id=%s | channel_id=%s",
                        message.author.id,
                        announcement_channel.id,
                    )
                except discord.DiscordException as exc:
                    logger.error(
                        "發布禁言公告失敗 | user_id=%s | channel_id=%s | error=%s",
                        message.author.id,
                        announcement_channel.id,
                        exc,
                    )

            return  # 不再往下傳遞，避免觸發指令等

        # 其他訊息交給內建處理（指令等）
        await super().on_message(message)

    async def on_member_join(self, member: discord.Member) -> None:
        """
        當新成員加入伺服器時自動執行。

        功能：
        1. 自動指派「客戶」角色
        2. 發送詳細的歡迎私訊
        3. 在 #新成員歡迎 頻道發布公告
        4. 多層級日誌記錄（終端機 + Discord 頻道）
        5. 完整的錯誤處理和備援機制
        """
        # 基本資訊記錄
        log_msg = f"新成員加入 | user_id={member.id} | user_name={member.name} | guild={member.guild.name}"
        logger.info(log_msg)
        await self._log_to_discord(log_msg, level="info")

        # 追蹤執行狀態
        role_assigned = False
        dm_sent = False
        announcement_sent = False

        # ==================== 1. 自動指派角色 ====================
        role_name = self.config.auto_assign_role_name

        try:
            target_role = discord.utils.get(member.guild.roles, name=role_name)

            if target_role:
                await member.add_roles(target_role, reason="新成員自動指派")
                role_assigned = True
                log_msg = f"✅ 角色已指派 | user={member.name} | role={role_name}"
                logger.info(log_msg)
                await self._log_to_discord(log_msg, level="info")
            else:
                log_msg = f"❌ 找不到角色 | guild={member.guild.name} | role={role_name} | 請檢查角色是否存在"
                logger.error(log_msg)
                await self._log_to_discord(log_msg, level="error")

        except discord.Forbidden:
            log_msg = f"❌ 指派角色失敗：權限不足 | user={member.name} | role={role_name} | 請確認 Bot 權限"
            logger.error(log_msg)
            await self._log_to_discord(log_msg, level="error")
        except discord.HTTPException as exc:
            log_msg = f"❌ 指派角色失敗：HTTP 錯誤 | user={member.name} | error={exc}"
            logger.error(log_msg)
            await self._log_to_discord(log_msg, level="error")
        except Exception as exc:
            log_msg = f"❌ 指派角色失敗：未知錯誤 | user={member.name} | error={exc}"
            logger.error(log_msg)
            await self._log_to_discord(log_msg, level="error")

        # ==================== 2. 發送歡迎私訊 ====================
        try:
            welcome_msg = self.config.welcome_message
            await member.send(welcome_msg)
            dm_sent = True
            log_msg = f"✅ 歡迎私訊已發送 | user={member.name}"
            logger.info(log_msg)
            await self._log_to_discord(log_msg, level="info")

        except discord.Forbidden:
            log_msg = f"⚠️ 無法發送私訊（用戶關閉私訊） | user={member.name}"
            logger.warning(log_msg)
            await self._log_to_discord(log_msg, level="warning")
        except discord.HTTPException as exc:
            log_msg = f"❌ 發送私訊失敗：HTTP 錯誤 | user={member.name} | error={exc}"
            logger.error(log_msg)
            await self._log_to_discord(log_msg, level="error")
        except Exception as exc:
            log_msg = f"❌ 發送私訊失敗：未知錯誤 | user={member.name} | error={exc}"
            logger.error(log_msg)
            await self._log_to_discord(log_msg, level="error")

        # ==================== 3. 在歡迎頻道發布公告 ====================
        welcome_channel = None
        fallback_used = False

        try:
            # 嘗試使用配置的歡迎頻道
            if self.config.welcome_channel_id:
                welcome_channel = self.get_channel(self.config.welcome_channel_id)
                if not welcome_channel:
                    try:
                        welcome_channel = await self.fetch_channel(self.config.welcome_channel_id)
                    except discord.NotFound:
                        log_msg = f"⚠️ 歡迎頻道不存在 | channel_id={self.config.welcome_channel_id} | 嘗試備援方案"
                        logger.warning(log_msg)
                        await self._log_to_discord(log_msg, level="warning")

            # 備援方案：搜尋名為「新成員歡迎」或「一般」的頻道
            if not welcome_channel:
                for channel_name in ["新成員歡迎", "一般"]:
                    welcome_channel = discord.utils.get(
                        member.guild.text_channels,
                        name=channel_name
                    )
                    if welcome_channel:
                        fallback_used = True
                        log_msg = f"⚠️ 使用備援頻道 | channel=#{channel_name}"
                        logger.warning(log_msg)
                        await self._log_to_discord(log_msg, level="warning")
                        break

            # 發送歡迎公告
            if welcome_channel:
                announcement = f"🎉 歡迎 <@{member.id}> 加入 **{member.guild.name}**！\n\n請查看私訊了解更多資訊。"
                await welcome_channel.send(announcement)
                announcement_sent = True

                log_msg = f"✅ 歡迎公告已發布 | channel=#{welcome_channel.name} | fallback={fallback_used}"
                logger.info(log_msg)
                await self._log_to_discord(log_msg, level="info")
            else:
                log_msg = f"⚠️ 找不到歡迎頻道 | 請設定 WELCOME_CHANNEL_ID 或創建 #新成員歡迎 頻道"
                logger.warning(log_msg)
                await self._log_to_discord(log_msg, level="warning")

        except discord.Forbidden:
            log_msg = f"❌ 發送歡迎公告失敗：權限不足 | channel=#{welcome_channel.name if welcome_channel else 'Unknown'}"
            logger.error(log_msg)
            await self._log_to_discord(log_msg, level="error")
        except discord.HTTPException as exc:
            log_msg = f"❌ 發送歡迎公告失敗：HTTP 錯誤 | error={exc}"
            logger.error(log_msg)
            await self._log_to_discord(log_msg, level="error")
        except Exception as exc:
            log_msg = f"❌ 發送歡迎公告失敗：未知錯誤 | error={exc}"
            logger.error(log_msg)
            await self._log_to_discord(log_msg, level="error")

        # ==================== 4. 最終摘要日誌 ====================
        summary = (
            f"📊 新成員處理完成 | user={member.name} | "
            f"role_assigned={role_assigned} | dm_sent={dm_sent} | announcement_sent={announcement_sent}"
        )
        logger.info(summary)
        await self._log_to_discord(summary, level="info")

    async def _send_private(self, ctx: commands.Context, message: str) -> None:
        try:
            await ctx.author.send(message)
            if ctx.guild:
                await ctx.reply("已透過私訊提供資料，以保障資訊安全。", delete_after=30)
        except discord.Forbidden:
            await ctx.reply("無法傳送私訊，請確認私訊設定。")

    @tasks.loop(minutes=10)
    async def moi_sync_task(self) -> None:
        now_local = datetime.now(self.local_tz)
        week = now_local.isocalendar().week
        if now_local.weekday() != 0 or now_local.hour != 9:
            return
        if self._last_moi_sync_week == week:
            return

        logger.info("Running weekly MOI sync task")
        self._last_moi_sync_week = week
        async with database.connect() as db:
            rules = await monitoring.iter_rules(db)
        for rule in rules:
            listings = await market.fetch_latest_listings(
                area=rule.area,
                price_min=rule.price_min,
                price_max=rule.price_max,
                size_min=rule.size_min,
                size_max=rule.size_max,
                limit=10,
            )
            if not listings:
                continue
            user = self.get_user(rule.user_id) or await self.fetch_user(rule.user_id)
            lines = ["符合監控條件的最新房源："]
            for listing in listings:
                lines.append(
                    f"{listing.area} | {listing.price} 萬 | {listing.size} 坪 | {listing.address}"
                )
                if getattr(listing, "url", None):
                    lines.append(listing.url)
            await user.send("\n".join(lines))

    @moi_sync_task.before_loop
    async def before_moi_sync(self) -> None:
        await self.wait_until_ready()

    @tasks.loop(minutes=10)
    async def weekly_report_task(self) -> None:
        now_local = datetime.now(self.local_tz)
        week = now_local.isocalendar().week
        if now_local.weekday() != 0 or now_local.hour != 10:
            return
        if self._last_report_week == week:
            return
        if not self.config.default_report_channel_id:
            return
        channel = self.get_channel(self.config.default_report_channel_id)
        if not channel:
            try:
                channel = await self.fetch_channel(self.config.default_report_channel_id)
            except discord.NotFound:
                logger.warning("Report channel not found: %s", self.config.default_report_channel_id)
                return
        summary = await market.generate_report(["全區"], days=7)
        await channel.send(summary)
        self._last_report_week = week

    @weekly_report_task.before_loop
    async def before_weekly_report(self) -> None:
        await self.wait_until_ready()

    @tasks.loop(minutes=1)
    async def viewing_reminder_task(self) -> None:
        now = datetime.utcnow()
        remind_before = now + timedelta(minutes=90)
        viewings_to_remind = await viewings.pending_reminders(before=remind_before)
        for viewing in viewings_to_remind:
            scheduled_at = datetime.fromisoformat(viewing.scheduled_at)
            user = self.get_user(viewing.creator_id) or await self.fetch_user(viewing.creator_id)
            message = (
                "看屋提醒：\n"
                f"時間：{scheduled_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"客戶：{viewing.client}\n物件：{viewing.property}"
            )
            if viewing.agent:
                message += f"\n指派業務：{viewing.agent}"
            if viewing.contact:
                message += f"\n聯絡方式：{viewing.contact}"
            if viewing.note:
                message += f"\n備註：{viewing.note}"
            if viewing.link:
                message += f"\n連結：{viewing.link}"
            await user.send(message)
            await viewings.mark_reminded(viewing.id)

    @viewing_reminder_task.before_loop
    async def before_viewing_reminder(self) -> None:
        await self.wait_until_ready()


bot_instance: Optional[VicBot] = None


def _ensure_guild(ctx: commands.Context) -> bool:
    if ctx.guild is None:
        raise commands.NoPrivateMessage("此指令僅能在伺服器中使用。")
    return True


def _parse_key_values(parts: List[str]) -> dict:
    result = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        result[key] = value
    return result


@commands.command(name="監控新增")
async def monitor_add(ctx: commands.Context, area: str, price_range: Optional[str] = None, size_range: Optional[str] = None):
    _ensure_guild(ctx)
    price_min, price_max = parse_range(price_range)
    size_min, size_max = parse_float_range(size_range)
    rule_id = await monitoring.add_rule(
        user_id=ctx.author.id,
        guild_id=ctx.guild.id,
        area=area,
        price_min=price_min,
        price_max=price_max,
        size_min=size_min,
        size_max=size_max,
    )
    await ctx.reply(f"已新增監控條件（編號 {rule_id}）。")


@commands.command(name="監控列表")
async def monitor_list(ctx: commands.Context):
    _ensure_guild(ctx)
    rules = await monitoring.list_rules(user_id=ctx.author.id, guild_id=ctx.guild.id)
    if not rules:
        await ctx.reply("目前沒有監控條件。")
        return
    lines = ["您的監控條件："]
    for rule in rules:
        price = f"{rule.price_min}-{rule.price_max}" if rule.price_min or rule.price_max else "不限"
        size = f"{rule.size_min}-{rule.size_max}" if rule.size_min or rule.size_max else "不限"
        lines.append(f"{rule.id}. {rule.area} | 價格 {price} 萬 | 坪數 {size}")
    await ctx.reply("\n".join(lines))


@commands.command(name="監控刪除")
async def monitor_delete(ctx: commands.Context, rule_id: int):
    _ensure_guild(ctx)
    if await monitoring.delete_rule(rule_id=rule_id, user_id=ctx.author.id, guild_id=ctx.guild.id):
        await ctx.reply("已刪除監控條件。")
    else:
        await ctx.reply("找不到對應的監控條件。")


@commands.command(name="物件查詢")
async def object_search(
    ctx: commands.Context,
    area: str,
    price_range: Optional[str] = None,
    size_range: Optional[str] = None,
    *,
    keyword: Optional[str] = None,
):
    _ensure_guild(ctx)
    price_min, price_max = parse_range(price_range)
    size_min, size_max = parse_float_range(size_range)
    listings = await market.fetch_latest_listings(
        area=area,
        price_min=price_min,
        price_max=price_max,
        size_min=size_min,
        size_max=size_max,
        limit=5,
    )
    if keyword:
        keyword_lower = keyword.lower()
        listings = [
            listing for listing in listings
            if getattr(listing, "address", None) and keyword_lower in listing.address.lower()
        ]

    if not listings:
        await ctx.reply("目前查無符合條件的物件。")
        return

    lines = ["最新物件："]
    for listing in listings:
        lines.append(
            f"{listing.area} | {listing.price} 萬 | {listing.size} 坪 | {listing.address}"
        )
        if getattr(listing, "url", None):
            lines.append(listing.url)
    await bot_instance._send_private(ctx, "\n".join(lines))


@commands.command(name="案件新增")
async def case_add(ctx: commands.Context, *args: str):
    _ensure_guild(ctx)
    params = _parse_key_values(list(args))
    title = params.get("標題")
    if not title:
        await ctx.reply("請提供標題，例如 標題=xxx")
        return
    status = params.get("狀態", "跟進中")
    area = params.get("區域")
    price = params.get("價格")
    assignee = params.get("指派")
    assignee_id = None
    if assignee and ctx.message.mentions:
        assignee_id = ctx.message.mentions[0].id
    price_value = int(price.rstrip("萬")) if price else None
    notes = params.get("備註")

    case_id = await cases.create_case(
        guild_id=ctx.guild.id,
        creator_id=ctx.author.id,
        title=title,
        area=area,
        price=price_value,
        status=status,
        assignee_id=assignee_id,
        notes=notes,
    )
    await ctx.reply(f"已新增案件（編號 {case_id}）。")


@commands.command(name="案件列表")
async def case_list(ctx: commands.Context, *args: str):
    _ensure_guild(ctx)
    params = _parse_key_values(list(args))
    status = params.get("狀態")
    area = params.get("區域")
    case_list = await cases.list_cases(
        guild_id=ctx.guild.id,
        user_id=ctx.author.id,
        status=status,
        area=area,
    )
    if not case_list:
        await ctx.reply("沒有符合條件的案件。")
        return
    lines = ["案件列表："]
    for case_item in case_list:
        assignee = f"<@{case_item.assignee_id}>" if case_item.assignee_id else "未指派"
        lines.append(
            f"{case_item.id}. {case_item.title} | 狀態 {case_item.status} | 區域 {case_item.area or '未填寫'} | 指派 {assignee}"
        )
    await ctx.reply("\n".join(lines))


@commands.command(name="案件更新")
async def case_update(ctx: commands.Context, case_id: int, *args: str):
    _ensure_guild(ctx)
    params = _parse_key_values(list(args))
    status = params.get("狀態")
    note = params.get("備註")
    success = await cases.update_case(
        case_id=case_id,
        guild_id=ctx.guild.id,
        user_id=ctx.author.id,
        status=status,
        note=note,
    )
    if success:
        await ctx.reply("案件已更新。")
    else:
        await ctx.reply("無權限或找不到案件。")


@commands.command(name="案件查看")
async def case_view(ctx: commands.Context, case_id: int):
    _ensure_guild(ctx)
    case_item = await cases.get_case(case_id=case_id, guild_id=ctx.guild.id)
    if not case_item:
        await ctx.reply("找不到案件。")
        return
    if ctx.author.id not in (case_item.creator_id, case_item.assignee_id):
        await ctx.reply("僅限負責人查看案件內容。")
        return
    updates = await cases.list_case_updates(case_id=case_id)
    lines = [
        f"案件：{case_item.title}",
        f"區域：{case_item.area or '未填寫'}",
        f"價格：{case_item.price or '未填寫'} 萬",
        f"狀態：{case_item.status}",
        f"指派：{'<@' + str(case_item.assignee_id) + '>' if case_item.assignee_id else '未指派'}",
    ]
    if case_item.notes:
        lines.append(f"備註：{case_item.notes}")
    if updates:
        lines.append("更新紀錄：")
        for update in updates:
            summary = update.status or ""
            if update.note:
                summary += f" - {update.note}"
            lines.append(f"{update.created_at}: {summary}")
    await bot_instance._send_private(ctx, "\n".join(lines))


@commands.command(name="客戶新增")
async def client_add(ctx: commands.Context, name: str, budget_range: Optional[str] = None, preferred_area: Optional[str] = None, *, description: Optional[str] = None):
    _ensure_guild(ctx)
    budget_min, budget_max = parse_range(budget_range)
    client_id = await clients.create_client(
        guild_id=ctx.guild.id,
        owner_id=ctx.author.id,
        name=name,
        budget_min=budget_min,
        budget_max=budget_max,
        preferred_areas=preferred_area,
        description=description,
    )
    await ctx.reply(f"已新增客戶（編號 {client_id}）。")


@commands.command(name="客戶列表")
async def client_list(ctx: commands.Context):
    _ensure_guild(ctx)
    client_records = await clients.list_clients(guild_id=ctx.guild.id, owner_id=ctx.author.id)
    if not client_records:
        await ctx.reply("尚無客戶資料。")
        return
    lines = ["您的客戶："]
    for item in client_records:
        budget = "-".join(str(b) for b in (item.budget_min or "", item.budget_max or "") if b)
        lines.append(f"{item.id}. {item.name} | 預算 {budget or '未填寫'} | 偏好 {item.preferred_areas or '未填寫'}")
    await bot_instance._send_private(ctx, "\n".join(lines))


@commands.command(name="客戶更新")
async def client_update(ctx: commands.Context, client_id: int, *args: str):
    _ensure_guild(ctx)
    params = _parse_key_values(list(args))
    updates = {}
    if "姓名" in params:
        updates["name"] = params["姓名"]
    if "預算" in params:
        budget_min, budget_max = parse_range(params["預算"])
        updates["budget_min"] = budget_min
        updates["budget_max"] = budget_max
    if "偏好區域" in params:
        updates["preferred_areas"] = params["偏好區域"]
    if "需求描述" in params:
        updates["description"] = params["需求描述"]
    success = await clients.update_client(
        client_id=client_id,
        guild_id=ctx.guild.id,
        owner_id=ctx.author.id,
        updates=updates,
    )
    if success:
        await ctx.reply("客戶資料已更新。")
    else:
        await ctx.reply("無權限或找不到客戶。")


@commands.command(name="客戶跟進")
async def client_followup(ctx: commands.Context, client_id: int, *, note: str):
    _ensure_guild(ctx)
    success = await clients.add_followup(
        client_id=client_id,
        guild_id=ctx.guild.id,
        user_id=ctx.author.id,
        note=note,
    )
    if success:
        await ctx.reply("已記錄跟進。")
    else:
        await ctx.reply("無權限或找不到客戶。")


@commands.command(name="客戶紀錄")
async def client_records(ctx: commands.Context, client_id: int):
    _ensure_guild(ctx)
    followups = await clients.list_followups(
        client_id=client_id,
        guild_id=ctx.guild.id,
        owner_id=ctx.author.id,
    )
    if followups is None:
        await ctx.reply("無權限或找不到客戶。")
        return
    if not followups:
        await ctx.reply("目前沒有跟進紀錄。")
        return
    lines = [f"客戶 {client_id} 的跟進紀錄："]
    for item in followups:
        lines.append(f"{item.created_at} - {item.note}")
    await bot_instance._send_private(ctx, "\n".join(lines))


@commands.command(name="看屋排程")
async def viewing_add(ctx: commands.Context, datetime_part: str, time_part: str, *, details: str):
    _ensure_guild(ctx)
    dt = parse_datetime(f"{datetime_part} {time_part}")
    if not dt:
        await ctx.reply("時間格式錯誤，請使用 YYYY-MM-DD HH:MM。")
        return
    parts = [p.strip() for p in details.split("|")]
    if len(parts) < 4:
        await ctx.reply("請依格式提供 客戶|物件|指派業務|聯絡方式|備註|連結。")
        return
    client_name = parts[0]
    property_name = parts[1]
    agent = parts[2] if len(parts) > 2 else None
    contact = parts[3] if len(parts) > 3 else None
    note = parts[4] if len(parts) > 4 else None
    link = parts[5] if len(parts) > 5 else None
    viewing_id = await viewings.add_viewing(
        guild_id=ctx.guild.id,
        creator_id=ctx.author.id,
        scheduled_at=dt,
        client=client_name,
        property=property_name,
        agent=agent,
        contact=contact,
        note=note,
        link=link,
    )
    await ctx.reply(f"已建立看屋行程（編號 {viewing_id}）。")


@commands.command(name="看屋列表")
async def viewing_list(ctx: commands.Context, days: Optional[int] = 7):
    _ensure_guild(ctx)
    until = datetime.utcnow() + timedelta(days=days or 7)
    viewing_records = await viewings.list_viewings(
        guild_id=ctx.guild.id,
        creator_id=ctx.author.id,
        until=until,
    )
    if not viewing_records:
        await ctx.reply("沒有即將到來的行程。")
        return
    lines = ["看屋行程："]
    for item in viewing_records:
        scheduled_at = datetime.fromisoformat(item.scheduled_at)
        lines.append(
            f"{item.id}. {scheduled_at.strftime('%Y-%m-%d %H:%M')} | 客戶 {item.client} | 物件 {item.property} | 指派 {item.agent or '未填寫'}"
        )
    await bot_instance._send_private(ctx, "\n".join(lines))


@commands.command(name="行情")
async def market_command(ctx: commands.Context, area: str, days: Optional[int] = 30):
    _ensure_guild(ctx)
    summary = await market.fetch_market_summary(area, days)
    message = (
        f"{area} 近 {days} 天行情：\n"
        f"平均單價：{summary.average_price or 'N/A'}\n"
        f"中位數單價：{summary.median_price or 'N/A'}\n"
        f"成交量：{summary.transactions} 件"
    )
    await ctx.reply(message)


@commands.command(name="報表")
async def report_command(ctx: commands.Context, days: Optional[int] = 7):
    _ensure_guild(ctx)
    summary = await market.generate_report(["全區"], days)
    await ctx.reply(summary)


@commands.command(name="房價查詢")
async def price_query_command(ctx: commands.Context, *, area: str):
    """
    查詢台中市房價統計資料。

    使用方式：
        !房價查詢 北屯區
        !房價查詢 西屯區文心路
        !房價查詢 台中市南屯區
    """
    _ensure_guild(ctx)

    # 記錄查詢請求
    log_msg = f"房價查詢請求 | user={ctx.author.name} | area={area} | guild={ctx.guild.name}"
    logger.info(log_msg)
    await bot_instance._log_to_discord(log_msg, level="info")

    # 發送「正在查詢」訊息
    processing_msg = await ctx.reply(f"🔍 正在查詢「{area}」的房價資料，請稍候...")

    try:
        # 執行查詢
        stats = await price_query.query_price(area, use_cache=True)

        # 創建 Discord Embed 格式化回覆
        embed = discord.Embed(
            title=f"📊 {stats.area} 房價統計",
            description=f"過去 5 年成交記錄（{stats.query_period}）",
            color=discord.Color.blue(),
            timestamp=datetime.now(bot_instance.local_tz)
        )

        # 基本統計
        embed.add_field(
            name="📈 整體統計",
            value=(
                f"**總交易筆數：** {stats.total_transactions} 筆\n"
                f"**建案分組數：** {len(stats.project_groups)} 個\n"
                f"**平均總價：** {stats.avg_price:.2f} 萬元\n"
                f"**平均單價：** {stats.avg_unit_price:.2f} 萬/坪"
            ),
            inline=False
        )

        # 建案分組展示（核心功能）
        if stats.project_groups:
            # 限制顯示最多 10 個分組（避免 Embed 過長）
            groups_to_show = stats.project_groups[:10]

            for group in groups_to_show:
                # 建案標題
                group_title = f"🏢 {group.road_name} {group.address_range}"
                if group.transaction_count > 1:
                    group_title += " (推測同社區)"

                # 建案詳情
                group_value = (
                    f"**成交筆數：** {group.transaction_count} 筆\n"
                    f"**平均總價：** {group.avg_price:.2f} 萬元\n"
                    f"**平均單價：** {group.avg_unit_price:.2f} 萬/坪\n"
                    f"**成交門牌：** {', '.join(group.addresses[:10])}"  # 最多顯示 10 個門牌
                )

                # 如果門牌太多，顯示「等 N 筆」
                if len(group.addresses) > 10:
                    group_value += f" 等 {group.transaction_count} 筆"

                embed.add_field(
                    name=group_title,
                    value=group_value,
                    inline=False
                )

            # 如果分組太多，提示有更多分組
            if len(stats.project_groups) > 10:
                embed.add_field(
                    name="📋 更多分組",
                    value=f"還有 {len(stats.project_groups) - 10} 個建案分組未顯示",
                    inline=False
                )

        # 價格區間
        embed.add_field(
            name="💰 價格區間",
            value=(
                f"**最高總價：** {stats.max_price:.2f} 萬元\n"
                f"**最低總價：** {stats.min_price:.2f} 萬元\n"
                f"**最高單價：** {stats.max_unit_price:.2f} 萬/坪\n"
                f"**最低單價：** {stats.min_unit_price:.2f} 萬/坪"
            ),
            inline=False
        )

        # 資料來源聲明（合法授權）
        from src.services import data_downloader
        cache_info = data_downloader.get_taichung_cache_info()

        data_source_text = "數據來源：內政部不動產成交案件實價登錄"
        if cache_info and cache_info.get("version"):
            data_source_text += f" ({cache_info['version']})"

        # 授權聲明
        license_text = "\n依政府資料開放授權條款 (OGDL) 第1版公眾釋出"

        embed.add_field(
            name="📄 資料來源與授權",
            value=(
                f"{data_source_text}\n"
                f"{license_text}\n"
                f"授權連結：https://data.gov.tw/license"
            ),
            inline=False
        )

        # 頁尾資訊
        footer_text = f"查詢者：{ctx.author.name}"
        if cache_info and cache_info.get("row_count"):
            footer_text += f" | 資料筆數：{cache_info['row_count']:,}"

        embed.set_footer(
            text=footer_text,
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )

        # 刪除「正在查詢」訊息
        await processing_msg.delete()

        # 發送結果
        await ctx.reply(embed=embed)

        # 記錄成功日誌
        log_msg = f"✅ 房價查詢成功 | user={ctx.author.name} | area={area} | transactions={stats.total_transactions}"
        logger.info(log_msg)
        await bot_instance._log_to_discord(log_msg, level="info")

    except ValueError as exc:
        # 使用者輸入錯誤（例如：地區不存在）
        await processing_msg.delete()
        error_embed = discord.Embed(
            title="❌ 查詢失敗",
            description=str(exc),
            color=discord.Color.red()
        )
        await ctx.reply(embed=error_embed)

        # 記錄警告日誌
        log_msg = f"⚠️ 房價查詢失敗（用戶輸入） | user={ctx.author.name} | area={area} | error={exc}"
        logger.warning(log_msg)
        await bot_instance._log_to_discord(log_msg, level="warning")

    except asyncio.TimeoutError:
        # 查詢超時
        await processing_msg.delete()
        error_embed = discord.Embed(
            title="⏱️ 查詢超時",
            description=f"查詢「{area}」的房價資料超時，請稍後再試。",
            color=discord.Color.orange()
        )
        await ctx.reply(embed=error_embed)

        # 記錄錯誤日誌
        log_msg = f"❌ 房價查詢超時 | user={ctx.author.name} | area={area}"
        logger.error(log_msg)
        await bot_instance._log_to_discord(log_msg, level="error")

    except Exception as exc:
        # 其他未知錯誤
        await processing_msg.delete()
        error_embed = discord.Embed(
            title="🚨 系統錯誤",
            description=f"查詢時發生錯誤，請聯繫管理員。\n\n錯誤訊息：`{exc}`",
            color=discord.Color.red()
        )
        await ctx.reply(embed=error_embed)

        # 記錄錯誤日誌
        log_msg = f"🚨 房價查詢失敗（系統錯誤） | user={ctx.author.name} | area={area} | error={exc}"
        logger.error(log_msg, exc_info=True)
        await bot_instance._log_to_discord(log_msg, level="error")


async def main() -> None:
    config = load_config()
    global bot_instance
    bot_instance = VicBot(config=config)
    for command in [
        monitor_add,
        monitor_list,
        monitor_delete,
        object_search,
        case_add,
        case_list,
        case_update,
        case_view,
        client_add,
        client_list,
        client_update,
        client_followup,
        client_records,
        viewing_add,
        viewing_list,
        market_command,
        report_command,
        price_query_command,
    ]:
        bot_instance.add_command(command)
    await bot_instance.start(config.token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
