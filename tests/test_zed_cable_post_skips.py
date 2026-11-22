"""Regressions for zedstoreonline deals that were silently skipped.

40551 / 40552: bundle captions printed the 3-piece total (16.5$) while the
               validator expected the per-piece price (4.1$) -> rejected.
40550:         caption printed "4$" while the validator wanted the literal "4.0".
40546:         "احجز قسيمة البائع" (seller voucher) was misread as a coupon claim.
"""

from app.ai.generator import format_competitor_to_lody_1to1
from app.ai.validator import caption_validator
from app.aliexpress.parser import is_coupon_claim_post, is_coupon_bulletin_post

AFF = "https://s.click.aliexpress.com/e/_aff123"

ZED_BUNDLE_RAW = """🔥   الحححححححق    🔥
🔥.   عروض bundle deals   ضع البلد الجزائر  😏

✨   ESSAGER 45W Car Charger

💵  سعر ثلاث قطع 16.5$      🔥
💵  سعر القطعة 4.1$      🔥

🙏   كوبون 3/15$ :OTSBF03
1️⃣  رابط المنتج  ⤵️

 https://s.click.aliexpress.com/e/_c3Ic4stn
"""

ZED_SELLER_VOUCHER_RAW = """🚨    ألحححححححححححق    🔥
غير البلد من الاعدادات أستراليا 🇦🇺
⭐️  Ulanzi MA35 MagSafe Smartphone Camera

💵  السعر 9.7$      🔥

🙏   احجز قسيمة البائع 1 دولار

🙏   كوبون 3/15$ :OTSBF03

🔗  رابـــــط المنتـج   https://s.click.aliexpress.com/e/_c3BAJUn3
"""

REAL_COUPON_CLAIM_RAW = """🔥 كوبونات متاحة الان
حجز الكوبونات متاحة الآن
🎟️ كوبون 4/25$ : OTD1104
🔗 https://s.click.aliexpress.com/e/_c3yeCRmH
"""


def _validate(caption, title, price, coupon):
    return caption_validator.validate(
        caption=caption,
        expected_title=title,
        expected_usd_price=price,
        expected_eur_price=None,
        expected_affiliate_url=AFF,
        expected_coupon=coupon,
        expected_points=False,
        is_coupon_list=False,
    )


def test_bundle_caption_uses_verified_per_piece_price_and_validates():
    caption = format_competitor_to_lody_1to1(
        raw_text=ZED_BUNDLE_RAW,
        affiliate_url=AFF,
        coupon_code="OTSBF03",
        extracted_title="ESSAGER 45W Car Charger",
        deal_type="bundle",
        usd_price=4.1,
    )
    assert "السعر : 4.1" in caption, caption
    assert "16.5" in caption, caption  # keep the 3-piece total visible
    result = _validate(caption, "ESSAGER 45W Car Charger", 4.1, "OTSBF03")
    assert result.approved, result.errors


def test_integer_price_in_caption_matches_float_expectation():
    caption = (
        "تخفيض ممتاز لـ Portable Thermal Printer\n"
        "السعر : 4$\n"
        f"رابط {AFF}\n"
        "@DzAliexpress0"
    )
    result = _validate(caption, "Portable Thermal Printer", 4.0, None)
    assert result.approved, result.errors

    # A genuinely wrong price must still be rejected.
    bad = caption.replace("السعر : 4$", "السعر : 9.5$")
    assert not _validate(bad, "Portable Thermal Printer", 4.0, None).approved


def test_seller_voucher_deal_is_not_a_coupon_claim():
    assert is_coupon_claim_post(ZED_SELLER_VOUCHER_RAW) is False


def test_genuine_coupon_claim_is_still_detected():
    assert is_coupon_claim_post(REAL_COUPON_CLAIM_RAW) is True


def test_coupon_wall_post_is_not_treated_as_a_product():
    # The exact title that produced @DzAliexpress0 post #3410 (fake "15$" deal).
    assert is_coupon_bulletin_post("أحدث كوبونات وتخفيضات AliExpress", "") is True
    assert is_coupon_bulletin_post("كوبونات AliExpress", "كوبون 4/25$ : OTD1104") is True

    # Real single products must never be caught, even when they mention a coupon.
    assert is_coupon_bulletin_post("ESSAGER 45W Car Charger", "كوبون 3/15$ : OTSBF03") is False
    assert is_coupon_bulletin_post("Ulanzi MA35 MagSafe Smartphone Camera", "") is False
