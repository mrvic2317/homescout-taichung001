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
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Optional

import discord
from discord.ext import commands, tasks

from src import database
from src.config import BotConfig, load_config
from src.services import cases, clients, market, monitoring, viewings
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
        self.moi_sync_task.add_exception_type(Exception)
        self.weekly_report_task.add_exception_type(Exception)
        self.viewing_reminder_task.add_exception_type(Exception)

    async def setup_hook(self) -> None:
        await database.init_db()
        self.moi_sync_task.start()
        self.weekly_report_task.start()
        self.viewing_reminder_task.start()

    async def on_ready(self) -> None:
        logger.info("VicBot 已上線，登入為 %s", self.user)

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
                if listing.url:
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
        listings = [listing for listing in listings if listing.address and keyword_lower in listing.address.lower()]

    if not listings:
        await ctx.reply("目前查無符合條件的物件。")
        return

    lines = ["最新物件："]
    for listing in listings:
        lines.append(
            f"{listing.area} | {listing.price} 萬 | {listing.size} 坪 | {listing.address}"
        )
        if listing.url:
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
    ]:
        bot_instance.add_command(command)
    await bot_instance.start(config.token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
