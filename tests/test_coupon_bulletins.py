"""Coupon bulletin formats must be dynamic — never store campaign coupons."""

from app.ai.coupon_bulletins import (
    build_bulletin_caption,
    compact_photo_caption,
    coupons_from_text,
    detect_bulletin_kind,
    event_from_text,
    format_business_coupon_bulletin,
    format_normal_coupon_bulletin,
)

BIZ_POST = """😍 إطلاق كوبون حساب Business ⚡️ تشتغل في الجزائر 🇩🇿
✅ انسخ الرابط وحطه في المتصفح : https://s.click.aliexpress.com/e/_c4cz2BHf
🎟️ كوبون 90/689$ : AEBBF10
🎟️ كوبون 115/899$ : AEBBF11
🎟️ كوبون 125/1000$ : AEBBF12
🎟️ كوبون 185/1500$ : AEBBF31
🔗 https://s.click.aliexpress.com/e/_c3M3gw2z"""

NORMAL_POST = """🔥 ظهور كوبونات خاصة بمناسبة تخفيضات الجمعة البيضاء
⏰ 08:00 صباحاً بتوقيت الجزائر
🎟️ كوبون 3/15$ : OTSBF03
🎟️ كوبون 4/24$ : OTSBF04
🎟️ كوبون 8/60$ : OTSBF08
🎟️ كوبون 19/115$ : OTSBF19
🎟️ كوبون 34/209$ : OTSBF34
🎟️ كوبون 50/305$ : OTSBF50
🎟️ كوبون 66/405$ : OTSBF66
https://s.click.aliexpress.com/e/_c4lZ2Hy5"""

OTHER_EVENT_POST = """📣 كوبونات خاصة بتخفيضات Party Ready Sale لشهر أكتوبر
🎟️ كوبون 5/25$ : PARTY5
🎟️ كوبون 10/50$ : PARTY10
https://s.click.aliexpress.com/e/_c4lZ2Hy5"""

PLAIN_LIST_POST = """🎟️ كوبون 4/25$ : OTD1104
🎟️ كوبون 19/115$ : OTSBF19
🔗 https://s.click.aliexpress.com/e/_c3yeCRmH"""

PRODUCT_POST = """تخفيض ممتاز لـ Ulanzi MA35
السعر : 9.7$
🎟️ كوبون 3/15$ : OTSBF03
https://s.click.aliexpress.com/e/_c3BAJUn3"""


def test_detection_and_extraction_are_driven_by_the_post():
    assert detect_bulletin_kind(BIZ_POST) == "business"
    assert detect_bulletin_kind(NORMAL_POST) == "normal"
    assert detect_bulletin_kind(PRODUCT_POST) is None  # one coupon = product deal
    # A plain coupon list (no festival keyword, no dates) is handled too —
    # this is the case the old calendar-gated path used to drop.
    assert detect_bulletin_kind(PLAIN_LIST_POST) == "normal"

    assert coupons_from_text(BIZ_POST) == [
        ("90/689$", "AEBBF10"), ("115/899$", "AEBBF11"),
        ("125/1000$", "AEBBF12"), ("185/1500$", "AEBBF31"),
    ]
    assert len(coupons_from_text(NORMAL_POST)) == 7


def test_business_caption_uses_the_coupons_given_not_a_stored_list():
    a = format_business_coupon_bulletin(
        [("90/689$", "AEBBF10"), ("185/1500$", "AEBBF31")],
        guide_url="https://s.click.aliexpress.com/e/_guide",
        apply_url="https://s.click.aliexpress.com/e/_apply",
    )
    b = format_business_coupon_bulletin(
        [("5/25$", "NEWC01"), ("10/50$", "NEWC02")],
        guide_url="https://s.click.aliexpress.com/e/_g2",
        apply_url="https://s.click.aliexpress.com/e/_a2",
    )
    assert "AEBBF10" in a and "AEBBF31" in a and "حتى 1500$" in a
    assert "NEWC01" in b and "NEWC02" in b and "AEBBF10" not in b
    assert "حتى 50$" in b
    assert "https://s.click.aliexpress.com/e/_guide" in a
    assert "https://s.click.aliexpress.com/e/_g2" in b


def test_build_caption_uses_our_links_and_no_competitor_branding():
    our = ["https://s.click.aliexpress.com/e/_OUR1", "https://s.click.aliexpress.com/e/_OUR2"]
    caption = build_bulletin_caption(BIZ_POST, our)

    assert caption is not None
    assert "AEBBF10" in caption and "AEBBF31" in caption
    assert our[0] in caption and our[1] in caption
    for bad in ["aniscoupons", "CoinsDiscountBot", "_c4cz2BHf", "_c3M3gw2z"]:
        assert bad not in caption.lower()
    assert "https://t.me/Alilo07BOT" in caption

    normal = build_bulletin_caption(NORMAL_POST, [our[0]])
    assert normal is not None and "OTSBF03" in normal and "الجمعة البيضاء" in normal
    assert build_bulletin_caption(PRODUCT_POST, our) is None


def test_photo_caption_stays_under_telegram_limit_and_keeps_coupons():
    full = build_bulletin_caption(BIZ_POST, ["https://s.click.aliexpress.com/e/_OUR1"])
    assert len(full) > 1024  # business layout needs a compact photo caption

    compact = compact_photo_caption(full)
    assert len(compact) <= 1024
    for code in ["AEBBF10", "AEBBF11", "AEBBF12", "AEBBF31"]:
        assert code in compact
    assert "https://s.click.aliexpress.com/e/_OUR1" in compact
    assert "Alilo07BOT" in compact

    short = compact_photo_caption("short caption")
    assert short == "short caption"


def test_event_name_is_read_from_post_not_hardcoded():
    assert "الجمعة البيضاء" in event_from_text(NORMAL_POST)
    assert "Party Ready Sale" in event_from_text(OTHER_EVENT_POST)

    other = build_bulletin_caption(OTHER_EVENT_POST, ["https://s.click.aliexpress.com/e/_OUR1"])
    assert other is not None
    assert "Party Ready Sale" in other
    assert "الجمعة البيضاء" not in other and "Black Friday" not in other
    assert "PARTY5" in other and "PARTY10" in other


def test_variant_coupon_product_post_is_not_classified_as_bulletin():
    """Regression (#3649 / ECKSDEAL #6125): a product deal with per-variant
    prices and multiple coupons must NEVER be hijacked into a coupon bulletin."""
    variant_product_post = """❗️ حول دولة التطبيق الى كندا 🇨🇦
تخفيض لـــ  : تخزين Kootion X12 Sata SSD
السعــــر💲 :
✅ 128 GB 7.56 $
🎟 كوبون 03/15$ :  OTSBF03
✅ 240 GB 14.98 $
🎟 كوبون 04/24$ :  OTSBF04
✅ 256 GB 16.73 $
🎟 كوبون 04/24$ :  OTSBF04
الرابـــــط 🔗: https://s.click.aliexpress.com/e/_c3CbKaZ5"""

    assert detect_bulletin_kind(variant_product_post) is None
    assert build_bulletin_caption(variant_product_post, ["https://s.click.aliexpress.com/e/_OUR1"]) is None
