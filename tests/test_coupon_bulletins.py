"""Coupon bulletin formats must be dynamic — never store campaign coupons."""

from app.ai.coupon_bulletins import (
    build_bulletin_caption,
    coupons_from_text,
    detect_bulletin_kind,
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

PRODUCT_POST = """تخفيض ممتاز لـ Ulanzi MA35
السعر : 9.7$
🎟️ كوبون 3/15$ : OTSBF03
https://s.click.aliexpress.com/e/_c3BAJUn3"""


def test_detection_and_extraction_are_driven_by_the_post():
    assert detect_bulletin_kind(BIZ_POST) == "business"
    assert detect_bulletin_kind(NORMAL_POST) == "normal"
    assert detect_bulletin_kind(PRODUCT_POST) is None  # one coupon = product deal

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
