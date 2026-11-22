"""Saved coupon bulletin formats (BUSINESS = #3479, NORMAL = #3195 style)."""

from app.ai.coupon_bulletins import (
    BUSINESS_APPLY_URL,
    BUSINESS_COUPONS,
    BUSINESS_GUIDE_URL,
    NORMAL_APPLY_URL,
    NORMAL_COUPONS,
    format_business_coupon_bulletin,
    format_normal_coupon_bulletin,
)


def _assert_clean(caption: str) -> None:
    for bad in ["aniscoupons", "CoinsDiscountBot", "zedstoreonline", "@DzAliexpress0_bot"]:
        assert bad.lower() not in caption.lower()
    assert "https://t.me/Alilo07BOT" in caption
    assert "https://dealscoutgreen.vercel.app/" in caption
    assert "@DzAliexpress0" in caption


def test_business_format_matches_published_3479():
    caption = format_business_coupon_bulletin()

    assert "كوبونات حساب Business" in caption
    assert "تشتغل في الجزائر" in caption
    assert BUSINESS_GUIDE_URL in caption
    assert BUSINESS_APPLY_URL in caption
    assert "المبيعات عبر الإنترنت" in caption
    assert "لا أملك رخصة تجارية" in caption
    assert "DealScout Phone" in caption
    for _tier, code in BUSINESS_COUPONS:
        assert code in caption
    _assert_clean(caption)


def test_normal_format_matches_3195_style():
    caption = format_normal_coupon_bulletin()

    assert "انطلاق تخفيضات" in caption
    assert "تخفيضات تخفيضات" not in caption  # no duplicated word
    assert NORMAL_APPLY_URL in caption
    assert "طريقة حجز الكوبونات" in caption
    for _tier, code in NORMAL_COUPONS:
        assert code in caption
    assert "4/24$" in caption
    _assert_clean(caption)


def test_formats_accept_custom_coupons_and_links():
    biz = format_business_coupon_bulletin(
        coupons=[("10/50$", "TEST10")],
        guide_url="https://s.click.aliexpress.com/e/_guide",
        apply_url="https://s.click.aliexpress.com/e/_apply",
    )
    assert "TEST10" in biz and "AEBBF10" not in biz
    assert "https://s.click.aliexpress.com/e/_guide" in biz
    assert "https://s.click.aliexpress.com/e/_apply" in biz

    normal = format_normal_coupon_bulletin(
        coupons=[("2/10$", "ABC02")], event_name="Test Event"
    )
    assert "ABC02" in normal and "OTSBF03" not in normal
    assert "Test Event" in normal
