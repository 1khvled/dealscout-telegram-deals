"""Deterministic handler for unexpected / ad-hoc competitor posts ("out of nowhere").

Handles linkless or non-product AliExpress news, coins/country tips, payment/card
updates, and shipping/customs notices without leaking competitor branding or
misreading numbers as fake product prices.
"""

import re
from typing import Dict, Optional, Sequence

from app.aliexpress.parser import (
    extract_prices,
    is_competitor_branded_code,
    is_spam_or_non_deal,
)

FOOTER = (
    "🤖 بوت تخفيض النقاط: https://t.me/Alilo07BOT\n\n"
    "📢 قناة الصفقات الرسمية: @DzAliexpress0\n"
    "https://t.me/DzAliexpress0"
)

# Personal, giveaway, or channel-housekeeping chatter that we must never repost
IGNORE_CH_NOISE = (
    "مسابقة", "قرعة", "سحب", "مبروك للفائز", "مبروك للفائزين",
    "تواصل معي", "ابلوكيه", "نصاب", "شكون يبيع", "ادعمونا",
    "تفاعلوا", "وصلونا", "شكراً على", "شكرا على", "متابعينا",
    "عيدكم", "رمضان", "جمعة مباركة",
)

ALI_RELEVANCE_KWS = (
    "aliexpress", "علي إكسبريس", "علي اكسبريس", "علي اكسبرس",
    "عملات", "نقاط", "coins", "كوبون", "كوبونات", "كود", "قسيمة",
    "تخفيض", "تخفيضات", "السلة", "شحن", "جمارك", "توصيل",
    "choice", "bundle", "باندل", "superdeals",
)

COINS_TIP_KWS = ("عملات", "نقاط", "coins", "تخفيض العملات", "كندا", "أستراليا", "استراليا", "بلد الحساب")
SHIPPING_KWS = ("شحن", "جمارك", "توصيل", "طرد", "طرود", "بريد", "الجزائرية", "ecotrack", "yalidine")


def classify_adhoc_post(raw_text: str) -> Optional[str]:
    """Return 'coins_tip', 'shipping_notice', 'promo_news', or None."""
    if not raw_text:
        return None
    is_spam, _ = is_spam_or_non_deal(raw_text)
    if is_spam:
        return None

    # Strip URLs BEFORE length/relevance checks so 'https://s.click.aliexpress.com/...'
    # inside a short 4-word booking stub ('الحق قم بالحجز من هنا') never matches 'aliexpress'.
    norm = re.sub(r'\u0640', '', raw_text).strip()
    non_url = re.sub(r'https?://\S+|s\.click\.\S+|t\.me/\S+', '', norm, flags=re.IGNORECASE).strip()
    if len(non_url) < 40:
        return None
    lower = non_url.lower()

    if any(k in lower for k in IGNORE_CH_NOISE):
        return None
    # Never hijack priced product deals
    if re.search(r'(?:تخفيض|عرض)\s+لـ', non_url) or any(w in lower for w in ("السعر", "prix", "price")):
        return None
    usd_price, _ = extract_prices(norm)
    if usd_price is not None:
        return None

    if not any(k in lower for k in ALI_RELEVANCE_KWS):
        return None

    words = [w for w in re.split(r'\s+', non_url) if len(w) >= 2]
    if len(words) < 8:
        return None

    if any(k in lower for k in SHIPPING_KWS):
        return "shipping_notice"
    if any(k in lower for k in COINS_TIP_KWS):
        return "coins_tip"
    return "promo_news"


def format_adhoc_post(
    raw_text: str,
    kind: str,
    link_mapping: Optional[Dict[str, str]] = None,
    fallback_url: Optional[str] = None,
) -> str:
    """Clean competitor mentions/links, wrap promo codes, and format cleanly."""
    mapping = link_mapping or {}
    lines = []
    for raw_line in (raw_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue
        low = line.lower()
        # Strip competitor channel/bot promo lines
        if any(b in low for b in (
            "قناتنا", "قناة التليغرام", "قناة التيليغرام", "للمزيد من العروض",
            "بوت تخفيض", "بوت العملات", "البوت", "coinsdiscountbot",
            "lodycouponsbot", "ecksdealsbot", "zedstoresve_bot", "bnd_hot_deals",
            "t.me/lodydeals", "t.me/aniscoupons", "t.me/zedstoreonline",
            "t.me/ecksdeal", "t.me/bnddeals", "t.me/couponsglobal",
        )):
            continue
        line = re.sub(
            r'@(?:lodydeals|aniscoupons|zedstoreonline|ecksdeal|bnddeals|couponsglobal)\b',
            '@DzAliexpress0',
            line,
            flags=re.IGNORECASE,
        )
        for orig_u, new_u in mapping.items():
            if orig_u in line:
                line = line.replace(orig_u, new_u)
        # Drop any leftover unmapped t.me links
        if re.search(r'(?:https?://)?t\.me/(?!DzAliexpress0|Alilo07BOT)[A-Za-z0-9_]+', line, re.I):
            continue
        # Remove tatweel elongation inside Arabic words while keeping 'لـ'
        line = re.sub(r'(?<!ل)\u0640+', '', line)
        lines.append(line)

    body = "\n".join(lines).strip()
    body = re.sub(r'\n{3,}', '\n\n', body)

    # Wrap non-competitor promo codes in <code> tags
    for code in set(re.findall(r'\b([A-Z]{2,6}[0-9]{2,6}[A-Z0-9]*)\b', body)):
        if not is_competitor_branded_code(code):
            body = re.sub(rf'(?<!<code>)\b{code}\b(?!</code>)', f'<code>{code}</code>', body)

    # Bold the first line as a clean header
    split_lines = body.splitlines()
    if split_lines:
        first = re.sub(r'^[📢💡📦🔥🚨⚡\s]+', '', split_lines[0]).strip()
        icon = {"coins_tip": "💡", "shipping_notice": "📦"}.get(kind, "📢")
        split_lines[0] = f"{icon} <b>{first}</b>"
        body = "\n".join(split_lines)

    if fallback_url and fallback_url not in body and not any(v in body for v in mapping.values()):
        body += f"\n\n🔗 <b>رابط مباشر ⤵️</b>\n{fallback_url}"

    return f"{body}\n\n{FOOTER}".strip()


__all__ = ["classify_adhoc_post", "format_adhoc_post"]
