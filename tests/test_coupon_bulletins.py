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


def test_single_coupon_drop_post_not_misread_as_30_dollar_product():
    """Regression (@DzAliexpress0/3772 / aniscoupons #35674): 'كوبون جديد 30$ شغال : OTSBF30'
    must NEVER have 30$ read as product price or 'سارع بحجزه من هنا' as title;
    it must be routed as a clean 'single' coupon post with code OTSBF30."""
    from app.ai.coupon_bulletins import single_coupon_from_text
    from app.aliexpress.parser import extract_clean_title, extract_prices

    raw = (
        "الححححححححق كوبون جديد 30$ شغال : OTSBF30\n"
        "سارع بحجزه من هنا \n"
        "https://s.click.aliexpress.com/e/_c3eYYZWZ\n\n"
        "انسخ الكود و دخلو في المنتج هذا و بصحتك"
    )
    assert extract_prices(raw) == (None, None)
    assert extract_clean_title(raw) is None
    assert single_coupon_from_text(raw) == ("30$", "OTSBF30")
    assert detect_bulletin_kind(raw) == "single"

    our = ["https://s.click.aliexpress.com/e/_cOURCOUPON"]
    cap = build_bulletin_caption(raw, our)
    assert cap is not None
    assert "<code>OTSBF30</code>" in cap
    assert "30$" in cap
    assert our[0] in cap
    assert "سارع بحجزه من هنا" not in cap
    assert "_c3eYYZWZ" not in cap


def test_linkless_coupon_news_announcement_is_detected_and_formatted():
    """Regression (aniscoupons #35693): linkless Super Friday OTSBF66 news post
    must be detected as 'announcement' and formatted with code, timing, and our link."""
    from app.ai.coupon_bulletins import single_coupon_from_text

    raw = (
        "📢 مفاجأة جمعة السوبر من علي إكسبريس!\n"
        "وصلتنا أخبار من وكيل علي اكسبريس أنه غدا إن شاء الله، "
        "راح يكون بإمكانكم استعمال كوبون OTSBF66 حتى 5 مرات لكل مستخدم!\n"
        "🎫 الكوبون 66$/405$: OTSBF66\n"
        "الخصم: 66$ على طلبات 405$ فما فوق.\n"
        "🗓 الموعد: الجمعة 27 نوفمبر.\n"
        "⏰ الساعة: 09:00 صباحًا بتوقيت الجزائر."
    )
    assert single_coupon_from_text(raw) == ("66/405$", "OTSBF66")
    assert detect_bulletin_kind(raw) == "announcement"

    our = ["https://s.click.aliexpress.com/e/_c3OOlDBD"]
    cap = build_bulletin_caption(raw, our)
    assert cap is not None
    assert "<code>OTSBF66</code>" in cap
    assert "66$" in cap and "405$" in cap
    assert "5 مرات" in cap
    assert "الجمعة 27 نوفمبر" in cap
    assert our[0] in cap


def test_ecksdeal_6147_https_is_never_extracted_as_coupon_code():
    from app.ai.coupon_bulletins import single_coupon_from_text

    text = "احجزها من هنا : https://s.click.aliexpress.com/e/_c4rA2E3J"
    assert single_coupon_from_text(text) is None


def test_coupon_announcement_omits_scheduled_phrase_without_date_or_time():
    from app.ai.coupon_bulletins import format_coupon_announcement_bulletin

    raw = "يمكن حجز الكوبونات 5 مرات\nhttps://s.click.aliexpress.com/e/_c4rA2E3J"
    apply_url = "https://s.click.aliexpress.com/e/_c3mHO3JF"
    cap = format_coupon_announcement_bulletin("66/405$", "OTSBF66", raw, apply_url)
    assert "في الموعد المحدد" not in cap
    assert "طبّق الكوبون مباشرة في صفحة الدفع عبر هذا الرابط" in cap
    assert apply_url in cap


def test_anis_35749_combined_normal_business_and_auto_reserve_fits_cleanly():
    from app.ai.coupon_bulletins import (
        build_bulletin_caption,
        compact_photo_caption,
        coupons_from_text,
        detect_bulletin_kind,
        event_from_text,
    )

    raw = (
        "🔥\n كوبونــات خاصـــة بمناسبــة \nتخفيضات الجمعـــة البيضـــاء\n"
        "🗓 تعمـــل الان إلى غاية 3 ديسمبـــر 📢\n"
        "✅ قــــــائمة الكـــــــــوبونات ⬇️⬇️\n"
        "🎟️ كوبـــون 3/15$ : OTSBF03\n"
        "🎟️ كوبـــون 4/24$ : OTSBF04\n"
        "🎟️ كوبـــون 8/60$ : OTSBF08\n"
        "🎟️ كوبـــون 19/115$ : OTSBF19\n"
        "🎟️ كوبـــون 30/200$ : OTSBF30\n"
        "🎟️ كوبـــون 34/209$ : OTSBF34\n"
        "🎟️ كوبـــون 50/305$ : OTSBF79\n"
        "🎟️ كوبـــون 66/405$ : OTSBF66\n"
        "✅ قــــــائمة كـــــــــوبونات البــــــــزنيس ⬇️⬇️\n"
        "🎟️ كوبـــون 90/689$ : AEBBF10\n"
        "🎟️ كوبـــون 115/899$ : AEBBF11\n"
        "🎟️ كوبـــون 125/1000$ : AEBBF12\n"
        "🎟️ كوبـــون 185/1500$ : AEBBF31\n"
        "🎟️ كوبـــون 185/1500$ : AEBBF32\n"
        "طريقة حجز الكوبونات هي بالدخول لرابط المنتج ⬇️⬇️\n"
        "https://s.click.aliexpress.com/e/_c3eYYZWZ\n"
        "يعمل تلقائيا بدون اعادة نسخه مرة اخرى\n"
    )
    assert detect_bulletin_kind(raw) == "normal"
    assert event_from_text(raw) == "الجمعة البيضاء"
    assert len(coupons_from_text(raw)) == 13

    our = ["https://s.click.aliexpress.com/e/_cOURRESERVE"]
    cap = build_bulletin_caption(raw, our)
    assert cap is not None
    compact = compact_photo_caption(cap)
    assert len(compact) <= 1024
    for code in ["OTSBF03", "OTSBF66", "AEBBF10", "AEBBF32"]:
        assert f"<code>{code}</code>" in compact
    assert "البزنيس" in compact
    assert "3 ديسمبر" in compact
    assert our[0] in compact
    assert "_c3eYYZWZ" not in compact


def test_full_coupon_wall_not_blocked_by_small_partial_or_single_bulletin(tmp_path, monkeypatch):
    import time
    from app.publisher import state_tracker

    state_file = str(tmp_path / "pub_state.json")
    monkeypatch.setattr(state_tracker, "STATE_FILE_PATH", state_file)
    monkeypatch.setattr(state_tracker, "_CACHED_CHANNEL_TEXTS", [])
    state_tracker.save_persistent_state({
        "published_coupon_bulletins": [{
            "promo": "Black Friday & Cyber Monday",
            "hash": "67c5d85c",
            "codes": ["OTSBF03", "OTSBF04"],
            "channel_msg_id": 3849,
            "channel": "@DzAliexpress0",
            "timestamp": time.time(),
        }],
        "published_product_timestamps": {"COUPONS_67c5d85c": time.time()},
    })

    full_wall = [{"tier": f"{i}/10$", "code": c} for i, c in enumerate(
        ["OTSBF03", "OTSBF04", "OTSBF08", "OTSBF19", "OTSBF66", "AEBBF10", "AEBBF11"], 1
    )]
    is_dup, _ = state_tracker.is_coupon_bulletin_already_published(
        coupon_list=full_wall,
        promo_name="الجمعة البيضاء",
        channel_id="@DzAliexpress0",
    )
    assert is_dup is False
