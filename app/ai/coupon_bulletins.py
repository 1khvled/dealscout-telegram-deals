"""Coupon bulletin layouts — dynamic, never hardcoded coupon codes.

When a monitored channel (currently @aniscoupons) posts a coupon bulletin,
we detect the situation, read the *actual* coupons from that post, and render
our own version with our own monetized links. Coupons and links are always
supplied by the caller; nothing about a specific campaign is stored here.
"""

import re
from typing import Iterable, List, Optional, Sequence, Tuple

from app.aliexpress.parser import extract_coupon_list

# (tier, code) — read from the source post, e.g. ("90/689$", "AEBBF10")
Coupon = Tuple[str, str]

BUSINESS_MARKERS = (
    "كوبون حساب", "حساب business", "business coupon", "inbusiness",
    "تحقق من الهوية", "المبيعات عبر الإنترنت",
)
NORMAL_MARKERS = (
    "كوبونات خاصة", "الجمعة البيضاء", "black friday", "بلاك فرايداي",
    "11.11", "تخفيضات", "كوبونات",
)

FOOTER = """لا تنسى استخدام البوت للشراء بأقل الأسعار :
https://t.me/Alilo07BOT

━━━━━━━━━━━━━━━━━
🌐 موقع الصفقات والكوبونات: https://dealscoutgreen.vercel.app/
📢 قناة الصفقات الرسمية: @DzAliexpress0"""


def coupons_from_text(raw_text: str) -> List[Coupon]:
    """Read every (tier, code) pair from a source post — always fresh."""
    items = extract_coupon_list(raw_text or "")
    return [(str(i.get("tier") or "").strip(), str(i.get("code") or "").strip())
            for i in items if i.get("code")]


def detect_bulletin_kind(raw_text: str) -> Optional[str]:
    """Return 'business', 'normal', or None for a coupon bulletin situation."""
    if not raw_text:
        return None
    coupons = coupons_from_text(raw_text)
    if len(coupons) < 2:  # a single coupon belongs to a normal product deal
        return None
    lower = raw_text.lower()
    if any(m in lower for m in BUSINESS_MARKERS):
        return "business"
    if any(m in lower for m in NORMAL_MARKERS):
        return "normal"
    return None


def _coupon_lines(coupons: Iterable[Coupon]) -> str:
    return "\n".join(f"🎟️ كوبون {tier} : {code}" for tier, code in coupons)


def _max_spend(coupons: Sequence[Coupon]) -> str:
    values = []
    for tier, _code in coupons:
        m = re.search(r'/\s*([0-9]+(?:\.[0-9]+)?)', tier)
        if m:
            values.append(float(m.group(1)))
    top = max(values) if values else 0
    return f"{int(top)}" if top.is_integer() else f"{top:g}"


def format_business_coupon_bulletin(
    coupons: Sequence[Coupon],
    guide_url: str,
    apply_url: str,
    company_example: str = "DealScout Phone",
) -> str:
    """Our BUSINESS layout, filled with the coupons/links from the source post."""
    if not coupons:
        raise ValueError("business bulletin needs coupons")
    steps = [
        '1️⃣ اضغط "تحقق من الهوية" واتبع الخطوات',
        '2️⃣ اختر "المبيعات عبر الإنترنت" ثم التالي',
        "3️⃣ المعلومات الأساسية خلّيها في حالها → البلد: الجزائر 🇩🇿",
        f"4️⃣ اسم الشركة: أي اسم تختاره (مثال: {company_example})",
        "5️⃣ اختر ميزانية مناسبة + سيناريوهات الشراء (معالجات، هواتف، سماعات، رامات...)",
        '6️⃣ اختر "لا أملك رخصة تجارية" + ارفع صورة حساب تجاري → تأكيد',
    ]
    return "\n\n".join([
        f"🚀 إطلاق كوبونات حساب Business ⚡️ تخفيضات ضخمة حتى {_max_spend(coupons)}$ 🛍️",
        "✅ الكوبونات تشتغل في الجزائر 🇩🇿\n"
        "انسخ الرابط وحطّه في المتصفح (Via Browser) ⬇️\n"
        f"{guide_url}",
        "📋 الخطوات باختصار:\n" + "\n".join(steps),
        "🎟️ قائمة الكوبونات ⬇️\n" + _coupon_lines(coupons),
        "⭕️ طريقة حجز الكوبونات وتثبيتها في حسابك 🔥👌🏽:\n"
        f"⚠️ ابدأ دائماً بالكوبونات الكبيرة (${_max_spend(coupons)} ...) ثم البقية واحداً تلو الآخر "
        "باه يبقاو في حسابك طيلة التخفيضات وما يهربلكش الستوك ✅\n"
        "🔹 طبّق الآن كامل الكوبونات على هذا المنتج باه تبقالكم في الحساب ⤵️\n"
        f"{apply_url}",
        "🚨 الكوبون يشتغل على جميع المنتجات تقريباً حتى الهواتف 📱",
        FOOTER,
    ]).strip()


def format_normal_coupon_bulletin(
    coupons: Sequence[Coupon],
    apply_url: str,
    event_name: Optional[str] = None,
    start_time: Optional[str] = None,
) -> str:
    """Our NORMAL coupon-wall layout, filled from the source post."""
    if not coupons:
        raise ValueError("normal bulletin needs coupons")
    event = event_name or "كوبونات AliExpress"
    when = f" ({start_time})" if start_time else ""
    return "\n\n".join([
        f"🚀 انطلاق تخفيضات {event} رسمياً الآن! 🛍️🔥\n"
        f"⏰ الكوبونات اشتغلت وبدأت بالعمل في هذه اللحظات{when}:\n"
        "سارعوا بحجزها وتطبيقها فوراً في حساباتكم قبل نفاد الكميات المحدودة! 🏃💨",
        _coupon_lines(coupons),
        "⭕️ طريقة حجز الكوبونات وتثبيتها في حسابك الآن 🔥👌🏽:\n"
        f"⚠️ ابدأ دائماً بالكوبونات الكبيرة (${_max_spend(coupons)} ...) ثم البقية واحداً تلو الآخر "
        "باه يبقاو في حسابك طيلة التخفيضات وما يهربلكش الستوك ✅\n"
        "🔹 طبّقوا الآن كامل الكوبونات على هذا المنتج باه تبقالكم في الحساب ⤵️\n"
        f"{apply_url}",
        FOOTER,
    ]).strip()


def build_bulletin_caption(raw_text: str, our_links: Sequence[str]) -> Optional[str]:
    """Detect + render in one call. ``our_links`` must be our own monetized URLs."""
    kind = detect_bulletin_kind(raw_text)
    coupons = coupons_from_text(raw_text)
    if not kind or not coupons or not our_links:
        return None
    if kind == "business":
        return format_business_coupon_bulletin(
            coupons, guide_url=our_links[0],
            apply_url=our_links[1] if len(our_links) > 1 else our_links[0],
        )
    event = None
    for marker in ("الجمعة البيضاء", "11.11", "بلاك فرايداي", "Black Friday"):
        if marker.lower() in raw_text.lower():
            event = marker
            break
    m_time = re.search(r'([0-9]{1,2}:[0-9]{2}\s*(?:صباحاً|مساءً)?)', raw_text)
    return format_normal_coupon_bulletin(
        coupons, apply_url=our_links[0],
        event_name=event, start_time=m_time.group(1) if m_time else None,
    )


__all__ = [
    "Coupon", "coupons_from_text", "detect_bulletin_kind",
    "format_business_coupon_bulletin", "format_normal_coupon_bulletin",
    "build_bulletin_caption",
]
