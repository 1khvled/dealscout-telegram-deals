"""Reusable coupon-bulletin formats for @DzAliexpress0.

Two saved layouts:
  * BUSINESS — the "كوبونات حساب Business" bulletin (guide + AEBBF coupons).
  * NORMAL   — the standard promo/event coupon wall (OTSBF coupons), same
               structure as the well-maintained #3195 White Friday post.

Both use only our own links/branding — no competitor handles or links.
"""

from typing import Iterable, Optional, Tuple

# (tier, code) — e.g. ("90/689$", "AEBBF10")
Coupon = Tuple[str, str]

BUSINESS_COUPONS: Tuple[Coupon, ...] = (
    ("90/689$", "AEBBF10"),
    ("115/899$", "AEBBF11"),
    ("125/1000$", "AEBBF12"),
    ("185/1500$", "AEBBF31"),
)

NORMAL_COUPONS: Tuple[Coupon, ...] = (
    ("3/15$", "OTSBF03"),
    ("4/24$", "OTSBF04"),
    ("8/60$", "OTSBF08"),
    ("19/115$", "OTSBF19"),
    ("34/209$", "OTSBF34"),
    ("50/305$", "OTSBF50"),
    ("66/405$", "OTSBF66"),
)

BUSINESS_GUIDE_URL = "https://s.click.aliexpress.com/e/_c38vQBKV"
BUSINESS_APPLY_URL = "https://s.click.aliexpress.com/e/_c4pJY9Vj"
NORMAL_APPLY_URL = "https://s.click.aliexpress.com/e/_c3d8Osgp"

FOOTER = """لا تنسى استخدام البوت للشراء بأقل الأسعار :
https://t.me/Alilo07BOT

━━━━━━━━━━━━━━━━━
🌐 موقع الصفقات والكوبونات: https://dealscoutgreen.vercel.app/
📢 قناة الصفقات الرسمية: @DzAliexpress0"""


def _coupon_lines(coupons: Iterable[Coupon]) -> str:
    return "\n".join(f"🎟️ كوبون {tier} : {code}" for tier, code in coupons)


def format_business_coupon_bulletin(
    coupons: Iterable[Coupon] = BUSINESS_COUPONS,
    guide_url: str = BUSINESS_GUIDE_URL,
    apply_url: str = BUSINESS_APPLY_URL,
    company_example: str = "DealScout Phone",
    event_title: str = "🚀 إطلاق كوبونات حساب Business ⚡️ تخفيضات ضخمة حتى 1500$ 🛍️",
) -> str:
    """The saved BUSINESS format (published as @DzAliexpress0 #3479)."""
    steps = [
        '1️⃣ اضغط "تحقق من الهوية" واتبع الخطوات',
        '2️⃣ اختر "المبيعات عبر الإنترنت" ثم التالي',
        "3️⃣ المعلومات الأساسية خلّيها في حالها → البلد: الجزائر 🇩🇿",
        f"4️⃣ اسم الشركة: أي اسم تختاره (مثال: {company_example})",
        "5️⃣ اختر ميزانية مناسبة + سيناريوهات الشراء (معالجات، هواتف، سماعات، رامات...)",
        '6️⃣ اختر "لا أملك رخصة تجارية" + ارفع صورة حساب تجاري → تأكيد',
    ]
    return "\n\n".join([
        event_title,
        "✅ الكوبونات تشتغل في الجزائر 🇩🇿\n"
        "انسخ الرابط وحطّه في المتصفح (Via Browser) ⬇️\n"
        f"{guide_url}",
        "📋 الخطوات باختصار:\n" + "\n".join(steps),
        "🎟️ قائمة الكوبونات ⬇️\n" + _coupon_lines(coupons),
        "⭕️ طريقة حجز الكوبونات وتثبيتها في حسابك 🔥👌🏽:\n"
        "⚠️ ابدأ دائماً بالكوبونات الكبيرة ($90 ثم $115...) ثم البقية واحداً تلو الآخر "
        "باه يبقاو في حسابك طيلة التخفيضات وما يهربلكش الستوك ✅\n"
        "🔹 طبّق الآن كامل الكوبونات على هذا المنتج باه تبقالكم في الحساب ⤵️\n"
        f"{apply_url}",
        "🚨 الكوبون يشتغل على جميع المنتجات تقريباً حتى الهواتف 📱",
        FOOTER,
    ]).strip()


def format_normal_coupon_bulletin(
    coupons: Iterable[Coupon] = NORMAL_COUPONS,
    apply_url: str = NORMAL_APPLY_URL,
    event_name: str = "الجمعة البيضاء Black Friday 🖤",
    start_time: str = "08:00 صباحاً بتوقيت الجزائر 🇩🇿",
    hook: Optional[str] = None,
) -> str:
    """The saved NORMAL format (same structure as the well-maintained #3195 post)."""
    headline = hook or (
        f"🚀 انطلاق تخفيضات {event_name} رسمياً الآن! 🛍️🔥\n"
        f"⏰ الكوبونات اشتغلت وبدأت بالعمل في هذه اللحظات ({start_time}):\n"
        "سارعوا بحجزها وتطبيقها فوراً في حساباتكم قبل نفاد الكميات المحدودة! 🏃💨"
    )
    return "\n\n".join([
        headline,
        _coupon_lines(coupons),
        "⭕️ طريقة حجز الكوبونات وتثبيتها في حسابك الآن 🔥👌🏽:\n"
        "⚠️ ابدأ دائماً بالكوبونات الكبيرة ($55 ثم $42...) ثم البقية واحداً تلو الآخر "
        "باه يبقاو في حسابك طيلة التخفيضات وما يهربلكش الستوك ✅\n"
        "🔹 طبّقوا الآن كامل الكوبونات على هذا المنتج باه تبقالكم في الحساب ⤵️\n"
        f"{apply_url}",
        FOOTER,
    ]).strip()


__all__ = [
    "BUSINESS_COUPONS", "NORMAL_COUPONS", "Coupon",
    "format_business_coupon_bulletin", "format_normal_coupon_bulletin",
]
