"""
AliExpress Official Promo Calendar Publisher & Automation
Handles:
1. Posting the official Sales & Promos Calendar (رزنامة التخفيضات الرسمية).
2. Automatically detecting when an active sale ends and announcing the next upcoming sale.
3. Providing 1-tap manual posting for Admin (/calendar or button).
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any
import httpx

try:
    from sqlalchemy import select
    from app.db.session import db_context
    from app.db.models import Deal
    HAS_DB = True
except (ImportError, Exception):
    HAS_DB = False

from app.config.settings import settings
import os
import json
from app.aliexpress.promos import promo_tracker, PromoEvent
from app.utils.logger import logger
from app.utils.network import enforce_ipv4

from pathlib import Path

DZ_TZ = timezone(timedelta(hours=1))

_ARABIC_MONTHS = {
    1: "جانفي", 2: "فيفري", 3: "مارس", 4: "أفريل", 5: "ماي", 6: "جوان",
    7: "جويلية", 8: "أوت", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر",
}

_ASSETS_DIR = Path(settings.BASE_DIR) / "assets"
LOCAL_CALENDAR_PATH = str(
    next(
        (p for p in [
            _ASSETS_DIR / "dealscout_event_started.png",
            _ASSETS_DIR / "official_calendar_november_2026.jpg",
            _ASSETS_DIR / "official_calendar_october_2026.jpg",
        ] if p.exists()),
        _ASSETS_DIR / "dealscout_event_started.png",
    )
)
CALENDAR_BANNER_IMG = "https://ae-pic-a1.aliexpress-media.com/kf/HTB18eCBQXXXXXXfXXXX760XFXXXa.png"


def _format_ar_range(start_dt: datetime, end_dt: datetime) -> str:
    s = start_dt.astimezone(DZ_TZ)
    e = end_dt.astimezone(DZ_TZ)
    # Cutoffs stored at 06:59 UTC / 07:59 DZ end on the previous calendar evening if < 08:00
    s_m = _ARABIC_MONTHS.get(s.month, "")
    e_m = _ARABIC_MONTHS.get(e.month, "")
    if s.month == e.month:
        return f"من {s.day} إلى {e.day} {e_m}"
    return f"من {s.day} {s_m} إلى {e.day} {e_m}"


def _active_and_upcoming_events(now: datetime, horizon_days: int = 21):
    """Returns deduplicated active + upcoming PromoEvents (never already-ended ones)."""
    from app.publisher.promo_notifiers import _campaign_key, _is_shadowed_placeholder

    now_utc = now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)
    horizon_end = now_utc + timedelta(days=horizon_days)
    calendar = promo_tracker.calendar

    candidates = []
    for p in calendar:
        if _is_shadowed_placeholder(p, calendar):
            continue
        if p.end_date < now_utc:
            continue  # Skip already-ended sales
        in_current_month = (
            (p.start_date.year == now_utc.year and p.start_date.month == now_utc.month)
            or (p.end_date.year == now_utc.year and p.end_date.month == now_utc.month)
        )
        starts_soon = p.start_date <= horizon_end
        if in_current_month or starts_soon:
            candidates.append(p)

    # Sort chronologically and deduplicate identical campaign/date windows
    candidates.sort(key=lambda e: (e.start_date, e.end_date))
    deduped = []
    seen_keys = set()
    for p in candidates:
        sig = (_campaign_key(p), p.start_date.date(), p.end_date.date())
        if sig in seen_keys:
            continue
        seen_keys.add(sig)
        deduped.append(p)
    return deduped


def _format_days_ar(n: int) -> str:
    if n <= 1:
        return "يوم واحد"
    if n == 2:
        return "يومين"
    if 3 <= n <= 10:
        return f"{n} أيام"
    return f"{n} يوماً"


def build_promo_calendar_post(now: Optional[datetime] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Builds a live, time-aware promo calendar post under 600 chars:
    - Never marks ended/past events as active.
    - Shows currently running sales and upcoming sales within the next 21 days
      (including next month when in the final days of the current month).
    """
    if now is None:
        now = datetime.now(timezone.utc)
    now_utc = now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)
    now_dz = now_utc.astimezone(DZ_TZ)

    month_name = _ARABIC_MONTHS.get(now_dz.month, "")
    events = _active_and_upcoming_events(now_utc)
    # Check if events span into next month (e.g. Nov 27 -> shows Dec Choice Day)
    next_month_dt = (now_dz.replace(day=28) + timedelta(days=4))
    spans_next = any(e.start_date.astimezone(DZ_TZ).month == next_month_dt.month for e in events)
    header_title = (
        f"رزنامة تخفيضات علي إكسبريس ({month_name} - {_ARABIC_MONTHS.get(next_month_dt.month, '')} {next_month_dt.year})"
        if spans_next
        else f"رزنامة تخفيضات علي إكسبريس شهر {month_name} {now_dz.year}"
    )

    lines = [
        f"<blockquote>📅 <b>{header_title}</b></blockquote>",
        "",
    ]

    if events:
        lines.append("🔔 <b>العروض الشغالة حالياً والقادمة قريباً:</b>")
        for p in events:
            label = p.name_ar or p.name
            date_range = _format_ar_range(p.start_date, p.end_date)
            if p.start_date <= now_utc <= p.end_date:
                days_left = max(0, (p.end_date.astimezone(DZ_TZ).date() - now_dz.date()).days)
                if days_left == 0:
                    status = "تنتهي غداً صباحاً"
                else:
                    status = f"شغالة الآن • يتبقى {_format_days_ar(days_left)}"
                icon = "🟢"
            else:
                days_to_start = max(1, (p.start_date.astimezone(DZ_TZ).date() - now_dz.date()).days)
                status = "تنطلق غداً" if days_to_start == 1 else f"تنطلق بعد {_format_days_ar(days_to_start)}"
                icon = "⏳"

            lines.append("")
            lines.append(f"{icon} <b>{label}</b>")
            lines.append(f"   🗓 {date_range} ({status})")
    else:
        lines.append("✨ <b>ترقبوا إعلان مواعيد التخفيضات القادمة قريباً</b>")

    lines.extend([
        "",
        "🪙 <b>اجمع العملات التي تحتاجها في العروض من هنا :</b>",
        "https://s.click.aliexpress.com/e/_c4l391NX",
        "",
        "🤖 <b>البوت لتخفيض الأسعار :</b> https://t.me/Alilo07BOT",
        "📢 <b>قناة التيليجرام :</b> https://t.me/DzAliexpress0",
    ])

    caption = "\n".join(lines)
    return caption, {}

def build_next_sale_transition_post(ended_promo: PromoEvent, next_promo: PromoEvent, now: Optional[datetime] = None) -> Tuple[str, Dict[str, Any]]:
    """Builds the transition announcement post when one promo ends and the next approaches."""
    if now is None:
        now = datetime.now(timezone.utc)

    days_left = max(0, (next_promo.start_date - now).days)
    s_str = next_promo.start_date.strftime("%d/%m")
    e_str = next_promo.end_date.strftime("%d/%m/%Y")

    lines = [
        f"🚨 <b>انتهاء {ended_promo.name_ar} والتحضير للحدث القادم! ⏳</b>",
        "━━━━━━━━━━━━━━━━━",
        f"انتهت رسمياً فعالية <b>{ended_promo.name}</b>.",
        "",
        "🎯 <b>الحدث التخفيضي الكبير القادم:</b>",
        f"▫️ <b>{next_promo.name_ar}</b>",
        f"🗓 الموعد: من <b>{s_str}</b> إلى <b>{e_str}</b>",
        f"⏳ المتبقي للانطلاق: <b>{days_left} أيام فقط!</b>",
        "━━━━━━━━━━━━━━━━━",
        "💡 <i>استغل هذه الأيام لجمع أكبر رصيد من العملات المجانية اليومية داخل تطبيق AliExpress لتكون مستعداً لأكبر التخفيضات!</i>",
        "",
        "🪙 استخدم بوت DealScoutDz لحساب خصم العملات: @Alilo07BOT"
    ]

    caption = "\n".join(lines)

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "🪙 فتح بوت تخفيض العملات", "url": "https://t.me/Alilo07BOT"}
            ],
            [
                {"text": "📢 قناة الصفقات المعتمدة", "url": "https://t.me/DzAliexpress0"}
            ]
        ]
    }

    return caption, reply_markup

async def publish_calendar_to_channel(bot_token: Optional[str] = None, channel_id: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[int]]:
    """Directly publishes the official promo calendar post to the Telegram channel."""
    enforce_ipv4()
    token = (
        bot_token
        or getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        or getattr(settings, "ADMIN_BOT_TOKEN", None)
        or os.getenv("TELEGRAM_BOT_TOKEN", "")
    )
    target = (
        channel_id
        or getattr(settings, "TARGET_CHANNEL_ID", None)
        or getattr(settings, "TELEGRAM_CHANNEL", None)
        or os.getenv("TARGET_CHANNEL_ID", "@DzAliexpress0")
    )
    if not token or not target:
        return False, "Bot token or channel ID not configured", None

    caption, markup = build_promo_calendar_post()

    api_url = f"https://api.telegram.org/bot{token}"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            banner_img = str(_ASSETS_DIR / "dealscout_event_started.png")
            if not os.path.exists(banner_img):
                banner_img = LOCAL_CALENDAR_PATH

            if os.path.exists(banner_img):
                with open(banner_img, "rb") as f:
                    mime = "image/png" if banner_img.endswith(".png") else "image/jpeg"
                    files = {"photo": (os.path.basename(banner_img), f, mime)}
                    data = {
                        "chat_id": target,
                        "caption": caption[:1024],
                        "parse_mode": "HTML"
                    }
                    resp = await client.post(f"{api_url}/sendPhoto", data=data, files=files)
            else:
                resp = await client.post(
                    f"{api_url}/sendPhoto",
                    json={
                        "chat_id": target,
                        "photo": CALENDAR_BANNER_IMG,
                        "caption": caption[:1024],
                        "parse_mode": "HTML"
                    }
                )
            data = resp.json()
            if resp.status_code == 200 and data.get("ok"):
                msg_id = data.get("result", {}).get("message_id")
                return True, None, msg_id
            else:
                # Text fallback if photo fails
                resp_text = await client.post(
                    f"{api_url}/sendMessage",
                    json={
                        "chat_id": target,
                        "text": caption,
                        "parse_mode": "HTML"
                    }
                )
                data_text = resp_text.json()
                if resp_text.status_code == 200 and data_text.get("ok"):
                    msg_id = data_text.get("result", {}).get("message_id")
                    return True, None, msg_id
                return False, data.get("description", "Failed to send message"), None
    except Exception as e:
        return False, str(e), None

async def check_and_auto_post_promo_transitions() -> Tuple[bool, Optional[str]]:
    """
    Automated check designed to run in background / cron:
    1. Checks if a promo has ended within the last 24h and the next transition post hasn't been posted yet.
    2. Checks if weekly calendar refresh is due (every 7 days) using central state tracker.
    """
    from app.publisher.state_tracker import is_calendar_eligible, record_calendar_published

    eligible, reason = await is_calendar_eligible()
    if not eligible:
        return False, reason

    now = datetime.now(timezone.utc)
    success, err, msg_id = await publish_calendar_to_channel()
    if success:
        record_calendar_published()
        if HAS_DB:
            try:
                async with db_context() as session:
                    record = Deal(
                        product_id=f"PROMO_CALENDAR_{now.strftime('%Y%m%d')}",
                        original_url="https://aliexpress.com",
                        title="رزنامة تخفيضات ومهرجانات AliExpress",
                        status="PUBLISHED"
                    )
                    session.add(record)
                    await session.commit()
            except Exception:
                pass
        return True, f"Published official promo calendar (Msg ID: {msg_id})"
    return False, err
