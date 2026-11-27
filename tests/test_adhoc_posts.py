"""Tests for the ad-hoc / surprise post classifier, formatter, and dedup."""

from app.ai.adhoc_posts import classify_adhoc_post, format_adhoc_post
from app.publisher import state_tracker


def test_classify_and_format_adhoc_tips_and_news():
    coins_tip = (
        "💡 حيلة مهمة لزيادة خصم العملات في AliExpress!\n"
        "بدّل بلد الحساب إلى كندا أو أستراليا قبل الدخول إلى رابط العملات.\n"
        "ستلاحظ ارتفاع نسبة الخصم مباشرة على أغلب المنتجات.\n"
        "🔸 قناتنا: https://t.me/aniscoupons\n"
        "🔸 البوت: https://t.me/CoinsDiscountBot"
    )
    assert classify_adhoc_post(coins_tip) == "coins_tip"
    out = format_adhoc_post(coins_tip, "coins_tip", fallback_url="https://s.click.aliexpress.com/e/_cOUR")
    assert "💡 <b>" in out
    assert "aniscoupons" not in out.lower()
    assert "coinsdiscountbot" not in out.lower()
    assert "https://s.click.aliexpress.com/e/_cOUR" in out
    assert "@DzAliexpress0" in out
    assert "Alilo07BOT" in out

    # Priced product deals must NEVER be classified as adhoc
    product = (
        "تخفيض ممتاز لـ Baseus 20W Charger\n"
        "السعر : 4.89$ 🔥\n"
        "رابط https://s.click.aliexpress.com/e/_c123"
    )
    assert classify_adhoc_post(product) is None

    # Channel chatter / giveaways must be ignored
    chatter = "مسابقة كبرى للمتابعين بمناسبة وصولنا 50 ألف مشترك مبروك للفائزين!"
    assert classify_adhoc_post(chatter) is None


def test_adhoc_dedup_prevents_cross_channel_reposts(tmp_path, monkeypatch):
    monkeypatch.setattr(state_tracker, "STATE_FILE_PATH", str(tmp_path / "state.json"))
    title = "حيلة مهمة لزيادة خصم العملات في AliExpress"
    assert state_tracker.is_recent_adhoc_duplicate(title)[0] is False
    state_tracker.record_adhoc_published(title)
    is_dup, reason = state_tracker.is_recent_adhoc_duplicate(title)
    assert is_dup is True
    assert "Duplicate adhoc" in reason


def test_zedstoreonline_40754_short_link_tease_is_rejected_by_classify_adhoc_post():
    from app.ai.adhoc_posts import classify_adhoc_post

    text = "الححححححححق قم بالحجز من هنا\nhttps://s.click.aliexpress.com/e/_c37eVVtf"
    assert classify_adhoc_post(text) is None
