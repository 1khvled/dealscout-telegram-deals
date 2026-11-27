"""Coupon bulletin layouts — dynamic, never hardcoded coupon codes.

When a monitored channel (currently @aniscoupons) posts a coupon bulletin,
we detect the situation, read the *actual* coupons from that post, and render
our own version with our own monetized links. Coupons and links are always
supplied by the caller; nothing about a specific campaign is stored here.
"""

import re
from typing import Iterable, List, Optional, Sequence, Tuple

from app.aliexpress.parser import (
    extract_clean_title,
    extract_coupon_list,
    extract_prices,
    is_competitor_branded_code,
)

# (tier, code) — read from the source post, e.g. ("90/689$", "AEBBF10")
Coupon = Tuple[str, str]

BUSINESS_MARKERS = (
    "كوبون حساب", "حساب business", "business coupon", "inbusiness",
    "تحقق من الهوية", "المبيعات عبر الإنترنت",
)
NORMAL_MARKERS = (
    "كوبونات خاصة", "كوبونات", "كوبون", "كود", "تخفيضات", "عروض", "مهرجان",
)
SINGLE_COUPON_MARKERS = (
    "كوبون جديد", "كود جديد", "شغال", "سارع بحجز", "انسخ الكود",
    "دخلو في المنتج", "دخله في المنتج", "لتثبيته", "طبق الكوبون", "طبّق الكوبون",
    "احجز الكوبون",
)
ANNOUNCEMENT_MARKERS = (
    "مفاجأة", "غدا", "غدوة", "الموعد", "الساعة", "عدد الاستخدامات",
    "مرات", "سلاتكم", "في السلة", "جمعة السوبر", "أخبار", "وكيل",
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


def single_coupon_from_text(raw_text: str) -> Optional[Coupon]:
    """Read a standalone single-coupon announcement like 'كوبون جديد 30$ شغال : OTSBF30'."""
    if not raw_text:
        return None
    norm = re.sub(r'\u0640', '', raw_text)
    COUPON_CODE_BLACKLIST = {
        "HTTP", "HTTPS", "S.CLICK", "ALIEXPRESS", "HTML", "HTML5",
        "LINK", "URL", "TELEGRAM", "NONE", "NULL", "TRUE", "FALSE",
    }

    def _valid_code(cand: str, end_pos: int) -> bool:
        c = cand.strip().upper()
        if not c or c in COUPON_CODE_BLACKLIST or is_competitor_branded_code(c):
            return False
        # Never treat a URL scheme ('https://...') as a coupon code
        if norm[end_pos:end_pos + 3] == "://":
            return False
        return bool(re.search(r'\d', c))

    m_val = re.search(
        r'(?:كوبون|كود|coupon|code|قسيمة)[^\r\n:\d$€]{0,30}'
        r'([$€]?\s*\d+(?:\.\d+)?\s*[$€]?(?:\s*/\s*[$€]?\s*\d+(?:\.\d+)?)?\s*[$€]?)'
        r'[^\r\n:]{0,30}[:：]\s*([A-Z][A-Z0-9_-]{3,19})\b',
        norm,
        re.IGNORECASE,
    )
    if m_val and _valid_code(m_val.group(2), m_val.end(2)):
        raw_val = re.sub(r'\s+', '', m_val.group(1) or "")
        raw_val = re.sub(r'[$€](?=/)', '', raw_val)
        code = m_val.group(2).strip().upper()
        if raw_val and not re.search(r'[$€]', raw_val):
            raw_val = f"{raw_val}$"
        return (raw_val, code)

    pairs = coupons_from_text(norm)
    if len(pairs) == 1 and pairs[0][1] and pairs[0][1].upper() not in COUPON_CODE_BLACKLIST and not is_competitor_branded_code(pairs[0][1]):
        return pairs[0]

    m_plain = re.search(
        r'(?:كوبون|كود|coupon|code|قسيمة)[^\r\n:]{0,40}[:：]\s*([A-Z][A-Z0-9_-]{3,19})\b',
        norm,
        re.IGNORECASE,
    )
    if m_plain and _valid_code(m_plain.group(1), m_plain.end(1)):
        return ("", m_plain.group(1).strip().upper())
    return None


def detect_bulletin_kind(raw_text: str) -> Optional[str]:
    """Return 'business', 'normal', 'single', or None for a coupon bulletin situation."""
    if not raw_text:
        return None
    coupons = coupons_from_text(raw_text)
    lower = raw_text.lower()
    if len(coupons) < 2:
        # Check for standalone single-coupon drop announcements (e.g. aniscoupons #35674):
        # NO product price, NO product deal header, explicit single coupon + claim wording.
        if re.search(r'(?:تخفيض|عرض)\s+لـ', raw_text) or any(w in lower for w in ("السعر", "prix", "price")):
            return None
        usd_price, _ = extract_prices(raw_text)
        if usd_price is not None:
            return None
        single = single_coupon_from_text(raw_text)
        if not single:
            return None
        if any(m in lower for m in ANNOUNCEMENT_MARKERS):
            return "announcement"
        if any(m in lower for m in SINGLE_COUPON_MARKERS) or extract_clean_title(raw_text) is None:
            return "single"
        return None
    if any(m in lower for m in BUSINESS_MARKERS):
        return "business"
    # A product deal with variant coupons (e.g. "128 GB 7.56$ -> OTSBF03,
    # 240 GB 14.98$ -> OTSBF04") quotes a product price and/or product deal header;
    # never hijack it into a fake coupon bulletin.
    distinct_codes = {code.upper() for _, code in coupons if code}
    if len(distinct_codes) < 2:
        return None
    usd_price, _ = extract_prices(raw_text)
    if usd_price is not None or "السعر" in lower or re.search(r'(?:تخفيض|عرض)\s+لـ', raw_text):
        return None
    if any(m in lower for m in NORMAL_MARKERS):
        return "normal"
    return None


def event_from_text(raw_text: str) -> Optional[str]:
    """Read whichever event the source announces — no event name is stored here."""
    if not raw_text:
        return None
    norm = re.sub(r'\u0640', '', raw_text)  # Arabic tatweel
    # Skip floating emoji/symbol-only lines (e.g. '🔥\n كوبونات خاصة بمناسبة \nتخفيضات الجمعة البيضاء')
    text_lines = [
        l.strip() for l in norm.splitlines()
        if l.strip() and re.search(r'[\u0600-\u06FFA-Za-z0-9]', l)
    ]
    if not text_lines:
        return None
    first = text_lines[0]
    if len(text_lines) >= 2 and re.search(r'(?:بمناسبة|لـ|تخفيضات|خاصة)$', first):
        first = f"{first} {text_lines[1]}"
    first = re.sub(r'^[^\u0600-\u06FFA-Za-z0-9]+', '', first).strip()
    # Cut at the first emoji or explicit date — the event phrase sits before those.
    first = re.split(
        r'[🗓📢⏰🎟️🔥⚡️😍🚀🛍️💥]|(?:\d{1,2}\s*(?:نوفمبر|ديسمبر|أكتوبر|سبتمبر|'
        r'يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|غشت|اغسطس))',
        first,
    )[0]
    # Strip announcement scaffolding, keep only the actual event name.
    first = re.sub(
        r'^(?:ظهور|إطلاق|انطلاق)?\s*(?:كوبونات|الكوبونات)\s+خاصة\s+'
        r'(?:بمناسبة\s+|بـ\s+|بتخفيضات\s+)?(?:تخفيضات\s+)?',
        '', first, flags=re.IGNORECASE,
    )
    first = re.sub(r'^(?:انطلاق|إطلاق)\s+(?:تخفيضات\s+)?', '', first)
    first = first.strip(' !!.؟:،-')
    return first or None


def _coupon_lines(coupons: Iterable[Coupon]) -> str:
    return "\n".join(f"🎟️ كوبون {tier} : <code>{code}</code>" for tier, code in coupons)


def _split_normal_and_business_coupons(coupons: Sequence[Coupon], raw_text: str = "") -> Tuple[List[Coupon], List[Coupon]]:
    """Splits combined coupon walls (like aniscoupons #35749) into normal vs Business tiers."""
    norm = re.sub(r'\u0640', '', raw_text or "")
    biz_codes_in_section: set = set()
    m_biz = re.search(r'(?:قائمة\s+كوبونات\s+البزنيس|كوبونات\s+البزنيس|business)(.*)', norm, re.IGNORECASE | re.S)
    if m_biz:
        biz_section = re.split(r'(?:طريقة\s+حجز|🔗|https?://)', m_biz.group(1), maxsplit=1)[0]
        for _, c in coupons_from_text(biz_section):
            biz_codes_in_section.add(c.upper())

    normal_list: List[Coupon] = []
    biz_list: List[Coupon] = []
    for tier, code in coupons:
        cu = code.upper()
        if cu in biz_codes_in_section or cu.startswith("AEBBF"):
            biz_list.append((tier, code))
        else:
            normal_list.append((tier, code))
    return normal_list, biz_list


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
    valid_until: Optional[str] = None,
    raw_text: str = "",
) -> str:
    """Our NORMAL (and combined Normal + Business) coupon-wall layout, filled from the source post."""
    if not coupons:
        raise ValueError("normal bulletin needs coupons")
    event = event_name or "كوبونات AliExpress"
    when = f" ({start_time})" if start_time else ""
    until_line = f"\n🗓 <b>تعمل الآن إلى غاية {valid_until}</b>" if valid_until else ""

    normal_list, biz_list = _split_normal_and_business_coupons(coupons, raw_text=raw_text)
    if normal_list and biz_list:
        coupons_block = (
            "✅ <b>قائمة الكوبونات العامة:</b>\n" + _coupon_lines(normal_list)
            + "\n\n💼 <b>قائمة كوبونات البزنيس:</b>\n" + _coupon_lines(biz_list)
        )
    else:
        coupons_block = _coupon_lines(coupons)

    norm_raw = re.sub(r'\u0640', '', raw_text or "")
    has_launch_cue = bool(
        re.search(r'(?:انطلاق|انطلقت|إطلاق|بدأت|ظهور|تشتغل\s+على\s+الساعة|0[789]:00)', norm_raw)
    )
    has_auto_reserve_tip = bool(re.search(r'(?:تلقائياً|تلقائيا|طريقة\s+حجز|صفحة\s+الدفع)', norm_raw))
    if has_auto_reserve_tip:
        reserve_block = (
            "⭕️ <b>طريقة تثبيت الكوبونات تلقائياً:</b>\n"
            f"ادخل للرابط ← اضغط «دفع» ← طبّق كل كود (ابدأ بـ ${_max_spend(coupons)}) لتثبيته في حسابك ✅\n"
            f"🔗 {apply_url}"
        )
    else:
        reserve_block = (
            "⭕️ طريقة حجز الكوبونات وتثبيتها في حسابك الآن 🔥👌🏽:\n"
            f"⚠️ ابدأ دائماً بالكوبونات الكبيرة (${_max_spend(coupons)} ...) ثم البقية واحداً تلو الآخر "
            "باه يبقاو في حسابك طيلة التخفيضات وما يهربلكش الستوك ✅\n"
            "🔹 طبّقوا الآن كامل الكوبونات على هذا المنتج باه تبقالكم في الحساب ⤵️\n"
            f"{apply_url}"
        )

    if has_launch_cue:
        header = (
            f"🚀 انطلاق تخفيضات {event} رسمياً الآن! 🛍️🔥{until_line}\n"
            f"⏰ سارعوا بحجزها قبل نفاد الكمية{when} 🏃💨"
        )
    else:
        ev_label = f"قائمة كوبونات {event} الشغالة الآن" if event_name else "قائمة الكوبونات الشغالة الآن"
        header = (
            f"🔥 <b>{ev_label}!</b> 🛍️{until_line}\n"
            "⏰ الكوبونات متوفرة وشغالة الآن، احجزها في حسابك قبل نفاد الكمية 🏃💨"
        )
    return "\n\n".join([
        header,
        coupons_block,
        reserve_block,
        FOOTER,
    ]).strip()


def format_single_coupon_bulletin(
    tier: str,
    code: str,
    apply_url: str,
) -> str:
    """Standalone single-coupon announcement (e.g. 'كوبون جديد 30$ شغال : OTSBF30')."""
    if not code:
        raise ValueError("single coupon bulletin needs code")
    val_label = f"بقيمة {tier} " if tier else ""
    return "\n\n".join([
        f"🎟️ كوبون جديد {val_label}شغال الآن : <code>{code}</code> 🔥\n"
        "⏰ سارع بنسخ الكود وتطبيقه الآن على هذا المنتج لتثبيته في حسابك قبل انتهاء الكمية! 🏃💨",
        f"🔹 طبّق الكوبون مباشرة من هنا ⤵️\n{apply_url}",
        FOOTER,
    ]).strip()


def format_coupon_announcement_bulletin(
    tier: str,
    code: str,
    raw_text: str,
    apply_url: str,
) -> str:
    """Linkless coupon/promo news announcement (e.g. Super Friday 5x usage alert)."""
    if not code:
        raise ValueError("announcement bulletin needs code")
    norm = re.sub(r'\u0640', '', raw_text or "")
    lines = []
    first = next((l.strip() for l in norm.splitlines() if l.strip()), "")
    headline = re.sub(r'^[📢🔥🚨⚡\s]+', '', first).strip() or "تحديث مهم حول كوبونات AliExpress!"
    lines.append(f"📢 <b>{headline}</b> 🔥")

    tier_clean = tier.replace("$", "").strip()
    if "/" in tier_clean:
        disc, min_sp = [p.strip() for p in tier_clean.split("/", 1)]
        lines.append(f"🎟️ <b>الكوبون ({disc}$/{min_sp}$) :</b> <code>{code}</code>\n💰 الخصم: <b>{disc}$</b> على طلبات <b>{min_sp}$</b> فما فوق.")
    elif tier_clean:
        lines.append(f"🎟️ <b>الكوبون ({tier_clean}$) :</b> <code>{code}</code>")
    else:
        lines.append(f"🎟️ <b>الكوبون :</b> <code>{code}</code>")

    details = []
    m_uses = re.search(r'(?:حتى\s*)?(\d+)\s*مرات', norm)
    if m_uses:
        details.append(f"↗️ <b>عدد الاستخدامات:</b> حتى {m_uses.group(1)} مرات لكل حساب")
    m_date = re.search(r'الموعد\s*[:：]\s*([^\r\n]+)', norm)
    if m_date:
        details.append(f"🗓 <b>الموعد:</b> {m_date.group(1).strip()}")
    m_time = re.search(r'الساعة\s*[:：]\s*([^\r\n]+)', norm)
    if m_time:
        details.append(f"⏰ <b>الساعة:</b> {m_time.group(1).strip()}")
    if details:
        lines.append("\n".join(details))

    if m_date or m_time:
        lines.append(
            f"🛒 <b>جهّزوا سلاتكم مسبقاً وادخلوا عبر الرابط في الموعد المحدد ⤵️</b>\n{apply_url}"
        )
    else:
        lines.append(
            f"🔹 <b>طبّق الكوبون مباشرة في صفحة الدفع عبر هذا الرابط ⤵️</b>\n{apply_url}"
        )
    lines.append(FOOTER)
    return "\n\n".join(lines).strip()


def build_bulletin_caption(raw_text: str, our_links: Sequence[str]) -> Optional[str]:
    """Detect + render in one call. ``our_links`` must be our own monetized URLs."""
    kind = detect_bulletin_kind(raw_text)
    if not kind or not our_links:
        return None
    if kind == "single":
        single = single_coupon_from_text(raw_text)
        if not single:
            return None
        tier, code = single
        return format_single_coupon_bulletin(tier=tier, code=code, apply_url=our_links[0])
    if kind == "announcement":
        single = single_coupon_from_text(raw_text)
        if not single:
            return None
        tier, code = single
        return format_coupon_announcement_bulletin(tier=tier, code=code, raw_text=raw_text, apply_url=our_links[0])
    coupons = coupons_from_text(raw_text)
    if not coupons:
        return None
    if kind == "business":
        return format_business_coupon_bulletin(
            coupons, guide_url=our_links[0],
            apply_url=our_links[1] if len(our_links) > 1 else our_links[0],
        )
    event = event_from_text(raw_text)
    norm_raw = re.sub(r'\u0640', '', raw_text)
    m_time = re.search(r'([0-9]{1,2}:[0-9]{2}\s*(?:صباحاً|مساءً)?)', norm_raw)
    m_until = re.search(r'إلى\s+غاية\s+([^\r\n📢🗓]+)', norm_raw)
    return format_normal_coupon_bulletin(
        coupons, apply_url=our_links[0],
        event_name=event,
        start_time=m_time.group(1) if m_time else None,
        valid_until=m_until.group(1).strip() if m_until else None,
        raw_text=raw_text,
    )


def compact_photo_caption(caption: str, limit: int = 1000) -> str:
    """Photo captions cap at 1024 chars — keep coupons & booking essentials cleanly when longer."""
    if len(caption) <= limit:
        return caption
    kept = []
    for line in caption.splitlines():
        s = line.strip()
        if not s:
            continue
        if (s.startswith("🎟️ كوبون") or s.startswith("🚀") or s.startswith("🔥 <b>قائمة") or s.startswith("🗓")
                or s.startswith("✅") or s.startswith("💼") or s.startswith("⭕️")
                or s.startswith("ادخل للرابط") or s.startswith("🔗")
                or s.startswith("https://s.click.aliexpress.com")
                or s.startswith("https://t.me/Alilo07BOT")
                or "@DzAliexpress0" in s
                or "dealscoutgreen.vercel.app" in s):
            kept.append(s)
    # Single newlines keep 13+ coupons + reservation guide well under Telegram's 1024-char limit
    out_lines = []
    for idx, s in enumerate(kept):
        prev = kept[idx - 1] if idx > 0 else ""
        if idx > 0 and not (
            (s.startswith("🎟️") and prev.startswith(("🎟️", "✅", "💼")))
            or (s.startswith(("ادخل للرابط", "🔗", "https://s.click.")) and prev.startswith(("⭕️", "ادخل للرابط")))
            or (s.startswith("🗓") and prev.startswith(("🚀", "🔥 <b>قائمة")))
            or ("@DzAliexpress0" in s and "dealscoutgreen" in prev)
        ):
            out_lines.append("")
        out_lines.append(s)
    out = "\n".join(out_lines)
    if len(out) <= limit:
        return out
    return out[:limit].rsplit("\n", 1)[0] if "\n" in out[:limit] else out[:limit]


__all__ = [
    "Coupon", "coupons_from_text", "single_coupon_from_text", "detect_bulletin_kind", "event_from_text",
    "format_business_coupon_bulletin", "format_normal_coupon_bulletin",
    "format_single_coupon_bulletin", "format_coupon_announcement_bulletin",
    "build_bulletin_caption", "compact_photo_caption",
]
