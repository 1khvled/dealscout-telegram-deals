"""Caption titles must keep the model the source posted, never silently upgrade variants."""
from app.aliexpress.product import product_extractor


def test_source_model_name_is_not_upgraded_to_pro():
    """Anis posted 'AJAZZ AJ179'; the catalog title says 'AJAZZ AJ179 PRO'."""
    chosen = product_extractor._choose_title(
        "AJAZZ AJ179",
        "AJAZZ AJ179 PRO PAW3395 Wireless Gaming Mouse with RGB Charging Base",
    )
    assert chosen == "AJAZZ AJ179"


def test_generic_source_title_still_uses_catalog_title():
    chosen = product_extractor._choose_title(
        "ماوس لاسلكي",
        "AJAZZ AJ179 PRO PAW3395 Wireless Gaming Mouse",
    )
    assert chosen == "AJAZZ AJ179 PRO PAW3395 Wireless Gaming Mouse"


def test_short_brand_without_model_still_uses_catalog_title():
    chosen = product_extractor._choose_title(
        "AJAZZ",
        "AJAZZ AJ179 PRO PAW3395 Wireless Gaming Mouse",
    )
    assert chosen == "AJAZZ AJ179 PRO PAW3395 Wireless Gaming Mouse"


def test_full_source_title_with_model_is_kept():
    chosen = product_extractor._choose_title(
        "Delux M400 PAW3311 24000DPI 1Khz",
        "DELUX M400 Wireless Gaming Mouse PAW3311 24000DPI",
    )
    assert chosen == "Delux M400 PAW3311 24000DPI 1Khz"
