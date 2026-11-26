import os
from pathlib import Path
from typing import Optional, List, Dict
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from app.config.settings import settings
from app.utils.logger import logger

def _get_system_font(names: List[str], size: int) -> ImageFont.FreeTypeFont:
    """Bulletproof font loader that searches Windows, Linux, and project font paths with fallback to sized default font."""
    candidate_dirs = [
        "C:/Windows/Fonts",
        "C:/WINNT/Fonts",
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/truetype/liberation",
        "/usr/share/fonts/truetype",
        "/usr/share/fonts",
        str(Path(settings.BASE_DIR) / "assets" / "fonts"),
        str(Path(settings.BASE_DIR) / "storage" / "assets")
    ]
    for name in names:
        for d in candidate_dirs:
            p = os.path.join(d, name)
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()

class MediaRenderer:
    def __init__(self, output_dir: Optional[Path] = None, logo_path: Optional[Path] = None):
        self.output_dir = output_dir or settings.GENERATED_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        circ_path = settings.BASE_DIR / "assets" / "logo_circular.png"
        default_logo = circ_path if circ_path.exists() else (settings.BASE_DIR / "assets" / "logo.png")
        self.logo_path = logo_path or default_logo

    def _render_deal_card(
        self,
        base_img: Image.Image,
        usd_price: Optional[float] = None
    ) -> Image.Image:
        """
        Renders a sleek Option A+B mixed card on the native product image:
        - Full natural product photo (no artificial white bars)
        - DealScout circular logo with subtle shadow and white ring border (top-right)
        - Modern glassmorphic dark-slate price pill with glowing gold text (bottom-left)
        """
        prod = base_img.convert("RGBA")
        max_dim = 1280
        if max(prod.size) > max_dim:
            prod.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        w, h = prod.size
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # 1. TOP-RIGHT: Circular DealScout Logo with soft shadow & white border
        if self.logo_path.exists():
            try:
                with Image.open(self.logo_path) as logo_raw:
                    logo = logo_raw.convert("RGBA")
                    logo_size = max(70, min(130, int(w * 0.11)))
                    logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                    margin = max(18, int(w * 0.03))
                    lx = w - logo_size - margin
                    ly = margin

                    # Soft drop shadow
                    shadow = Image.new("RGBA", (logo_size + 24, logo_size + 24), (0, 0, 0, 0))
                    sdraw = ImageDraw.Draw(shadow)
                    sdraw.ellipse((6, 6, logo_size + 18, logo_size + 18), fill=(0, 0, 0, 80))
                    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
                    overlay.paste(shadow, (lx - 12, ly - 12), shadow)

                    # White circular background / ring
                    draw.ellipse((lx - 3, ly - 3, lx + logo_size + 3, ly + logo_size + 3), fill=(255, 255, 255, 255))

                    # Paste circular logo
                    mask = Image.new("L", (logo_size, logo_size), 0)
                    draw_m = ImageDraw.Draw(mask)
                    draw_m.ellipse((0, 0, logo_size, logo_size), fill=255)
                    overlay.paste(logo, (lx, ly), mask)
            except Exception as e:
                logger.warning(f"Failed rendering logo badge: {e}")

        # 2. BOTTOM-LEFT: Modern Sleek Price Pill Badge
        if usd_price and usd_price > 0:
            try:
                price_text = f"${usd_price:.2f}"
                font_size = max(24, min(42, int(w * 0.035)))
                font_candidates = [
                    "arialbd.ttf", "arial.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                    "DejaVuSans-Bold.ttf"
                ]
                font_price = None
                for fc in font_candidates:
                    try:
                        font_price = ImageFont.truetype(fc, font_size)
                        break
                    except Exception:
                        continue
                if not font_price:
                    font_price = ImageFont.load_default()

                bbox = draw.textbbox((0, 0), price_text, font=font_price)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]

                pill_h = max(52, th + 30)
                pill_w = max(140, tw + 46)
                margin = max(20, int(w * 0.03))
                px = margin
                py = h - pill_h - margin
                radius = pill_h // 2

                # Soft shadow behind pill
                pshadow = Image.new("RGBA", (pill_w + 30, pill_h + 30), (0, 0, 0, 0))
                psdraw = ImageDraw.Draw(pshadow)
                psdraw.rounded_rectangle((10, 10, pill_w + 20, pill_h + 20), radius=radius, fill=(0, 0, 0, 85))
                pshadow = pshadow.filter(ImageFilter.GaussianBlur(7))
                overlay.paste(pshadow, (px - 15, py - 15), pshadow)

                # Pill background (deep dark slate #111827 with subtle transparency)
                draw.rounded_rectangle(
                    (px, py, px + pill_w, py + pill_h),
                    radius=radius,
                    fill=(17, 24, 39, 235),
                    outline=(255, 255, 255, 60),
                    width=2
                )

                # Price Text in glowing gold (#FBBF24)
                tx = px + (pill_w - tw) // 2
                ty = py + (pill_h - th) // 2 - 2
                draw.text((tx, ty), price_text, fill=(251, 191, 36, 255), font=font_price)
            except Exception as e:
                logger.warning(f"Failed rendering price pill: {e}")

        final_composite = Image.alpha_composite(prod, overlay)
        return final_composite.convert("RGB")

    def _render_framed_deal(
        self,
        base_img: Image.Image,
        usd_price: Optional[float] = None,
        title: Optional[str] = None
    ) -> Image.Image:
        """
        Renders product image seamlessly inside DealScout Neon Algerian Deals Frame.
        If product is Attack Shark, adds official Attack Shark logo.
        """
        frame_path = settings.BASE_DIR / "storage" / "assets" / "product_frame_template.png"
        if not frame_path.exists():
            frame_path = settings.BASE_DIR / "assets" / "product_frame_template.png"

        overlay_path = settings.BASE_DIR / "storage" / "assets" / "frame_overlay.png"
        if not overlay_path.exists():
            overlay_path = settings.BASE_DIR / "assets" / "frame_overlay.png"

        if not frame_path.exists():
            return self._render_deal_card(base_img, usd_price=usd_price)

        try:
            with Image.open(frame_path) as frame_raw:
                frame = frame_raw.convert("RGBA")
                fw, fh = frame.size

                # Inner product display box in DealScout Neon frame: left=105, top=215, width=930, height=860
                bx, by, bw, bh = 105, 215, 930, 860
                pad = 14
                avail_w = bw - (pad * 2)
                avail_h = bh - (pad * 2)

                prod = base_img.convert("RGBA")
                iw, ih = prod.size
                scale = min(avail_w / iw, avail_h / ih)
                new_w = max(1, int(iw * scale))
                new_h = max(1, int(ih * scale))
                scaled_img = prod.resize((new_w, new_h), Image.Resampling.LANCZOS)

                px = bx + (bw - new_w) // 2
                py = by + (bh - new_h) // 2

                bg_fill = Image.new("RGBA", (bw, bh), (255, 255, 255, 255))
                canvas = frame.copy()
                canvas.paste(bg_fill, (bx, by))
                canvas.paste(scaled_img, (px, py), scaled_img if scaled_img.mode == "RGBA" else None)

                # Check if Attack Shark brand: place official logo
                is_attack_shark = bool(title and "attack shark" in title.lower())
                if is_attack_shark:
                    as_logo_file = settings.BASE_DIR / "storage" / "assets" / "attack_shark_logo.png"
                    if not as_logo_file.exists():
                        as_logo_file = settings.BASE_DIR / "assets" / "attack_shark_logo.png"
                    if as_logo_file.exists():
                        try:
                            with Image.open(as_logo_file) as as_raw:
                                as_logo = as_raw.convert("RGBA")
                                al_w, al_h = as_logo.size
                                target_al_w = 170
                                target_al_h = int(al_h * (target_al_w / al_w))
                                as_scaled = as_logo.resize((target_al_w, target_al_h), Image.Resampling.LANCZOS)
                                canvas.paste(as_scaled, (bx + 24, by + 18), as_scaled)
                        except Exception as as_err:
                            logger.warning(f"Failed pasting Attack Shark logo: {as_err}")

                # Overlay neon border edges
                if overlay_path.exists():
                    try:
                        with Image.open(overlay_path) as ov_raw:
                            canvas = Image.alpha_composite(canvas, ov_raw.convert("RGBA"))
                    except Exception as ov_err:
                        logger.warning(f"Failed overlaying frame border: {ov_err}")

                return canvas.convert("RGB")
        except Exception as e:
            logger.warning(f"Failed rendering framed deal: {e}, falling back to default card")
            return self._render_deal_card(base_img, usd_price=usd_price)

    def _clean_source_watermark(self, im: Image.Image) -> Image.Image:
        """Deprecated: Avoid destructive pixel scrubbing that cuts out product parts."""
        return im

    def prepare_post_image(
        self,
        image_path: Optional[Path],
        product_id: Optional[str] = None,
        title: Optional[str] = None,
        usd_price: Optional[float] = None
    ) -> Optional[Path]:
        """
        Processes product image seamlessly inside DealScout Neon Frame template.
        """
        pid = product_id or "deal"
        out_file = self.output_dir / f"ready_{pid}.jpg"

        if image_path and image_path.exists():
            try:
                with Image.open(image_path) as img:
                    branded = self._render_framed_deal(img, usd_price=usd_price, title=title)
                    branded.save(out_file, "JPEG", quality=95)
                    return out_file
            except Exception as e:
                logger.warning(f"Failed processing image {image_path}: {e}")
        return None

    def render_coupon_bulletin_card(
        self,
        coupon_list: List[Dict[str, str]],
        promo_title: str = "Choice Day",
        channel_handle: Optional[str] = None,
        is_french: bool = False,
        date_range_str: Optional[str] = None
    ) -> Path:
        """
        Renders a high-definition 1080x1080 promotional coupon card.
        Guarantees coupon bulletin posts always have a professional graphic attached.
        """
        import hashlib
        if not channel_handle:
            channel_handle = "@francedealsdz" if is_french else "@DzAliexpress0"
        elif is_french and channel_handle == "@DzAliexpress0":
            channel_handle = "@francedealsdz"
        if len(coupon_list) == 1:
            try:
                c0 = coupon_list[0]
                tier_raw = str(c0.get("tier", "")).strip()
                code_raw = str(c0.get("code", "")).strip().upper()

                if "/" in tier_raw:
                    parts = tier_raw.replace("$", "").replace("€", "").split("/")
                    amt = parts[0].strip()
                    min_sp = parts[1].strip()
                    headline = f"{amt}€ off" if is_french else f"US ${amt} off"
                    sub_line = f"dès {min_sp}€ d'achat (Articles sélectionnés)" if is_french else f"orders US ${min_sp}+ (Select items only)"
                else:
                    amt = tier_raw.replace("$", "").replace("€", "").strip()
                    if amt:
                        headline = f"{amt}€ off" if is_french else f"US ${amt} off"
                    else:
                        headline = "Code Promo" if is_french else "Promo Coupon"
                    sub_line = "Articles sélectionnés · Quantité limitée" if is_french else "Select items · Limited quantity"

                cw, ch = 1080, 560
                scard = Image.new("RGB", (cw, ch), (255, 255, 255))
                sdraw = ImageDraw.Draw(scard)

                # Soft AliExpress blush-pink coupon ticket container
                sdraw.rounded_rectangle(
                    (36, 36, cw - 36, ch - 86),
                    radius=28,
                    fill=(255, 241, 242),
                    outline=(254, 205, 211),
                    width=2,
                )
                # Perforated divider line inside ticket
                sdraw.line([(48, ch - 196), (cw - 48, ch - 196)], fill=(254, 205, 211), width=2)

                f_hero = _get_system_font(["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], 72)
                f_sub = _get_system_font(["arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"], 28)
                f_label = _get_system_font(["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], 28)
                f_btn = _get_system_font(["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], 30)
                f_code = _get_system_font(["consolab.ttf", "arialbd.ttf", "DejaVuSansMono-Bold.ttf"], 38)
                f_foot = _get_system_font(["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], 22)

                # Left: discount headline + condition
                sdraw.text((88, 130), headline, fill=(225, 29, 72), font=f_hero, anchor="lm")
                sdraw.text((90, 210), sub_line, fill=(190, 18, 60), font=f_sub, anchor="lm")

                # Right: "Shop more" pill + code box
                btn_box = (cw - 330, 82, cw - 80, 152)
                sdraw.rounded_rectangle(btn_box, radius=35, fill=(225, 29, 72))
                sdraw.text(((btn_box[0] + btn_box[2]) // 2, (btn_box[1] + btn_box[3]) // 2),
                           "Profiter" if is_french else "Shop more", fill=(255, 255, 255), font=f_btn, anchor="mm")

                code_box = (cw - 330, 174, cw - 80, 248)
                sdraw.rounded_rectangle(code_box, radius=14, fill=(255, 255, 255), outline=(254, 205, 211), width=2)
                sdraw.text(((code_box[0] + code_box[2]) // 2, (code_box[1] + code_box[3]) // 2),
                           code_raw, fill=(15, 23, 42), font=f_code, anchor="mm")

                # Bottom ticket strip
                sdraw.text((88, ch - 140),
                           "Codes promo AliExpress" if is_french else "AliExpress coupon codes",
                           fill=(225, 29, 72), font=f_label, anchor="lm")
                sdraw.text((cw - 84, ch - 140),
                           "Active now · Limited stock",
                           fill=(100, 116, 139), font=f_sub, anchor="rm")

                # Brand footer
                sdraw.text((cw // 2, ch - 42),
                           f"{channel_handle}   •   @Alilo07BOT   •   dealscoutgreen.vercel.app",
                           fill=(71, 85, 105), font=f_foot, anchor="mm")

                h_sig = hashlib.sha256(f"{tier_raw}:{code_raw}:{is_french}".encode()).hexdigest()[:8]
                out_file = self.output_dir / f"coupon_single_{h_sig}_{'fr' if is_french else 'dz'}.png"
                scard.save(out_file, "PNG")
                return out_file
            except Exception as se:
                logger.warning(f"Single-coupon card render failed, falling back to full card: {se}")

        # 1. Check for 5-coupon poster template (custom high-res neon Choice Day / Brand Day template)
        template_5_path = Path(settings.BASE_DIR) / "storage" / "assets" / "coupon_5_template.png"
        if not template_5_path.exists():
            template_5_path = Path(settings.BASE_DIR) / "assets" / "coupon_5_template.png"

        if len(coupon_list) == 5 and template_5_path.exists():
            try:
                card = Image.open(template_5_path).convert("RGB")
                draw = ImageDraw.Draw(card)

                font_tier = _get_system_font(["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], 31)
                font_code = _get_system_font(["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], 44)
                font_footer = _get_system_font(["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], 23)

                rows_info = [
                    (498, 514),
                    (641, 657),
                    (776, 793),
                    (913, 930),
                    (1045, 1062)
                ]

                for idx, c in enumerate(coupon_list[:5]):
                    box_cy, badge_ty = rows_info[idx]
                    tier_raw = str(c.get("tier", "")).strip()
                    code_raw = str(c.get("code", "")).strip().upper()

                    if is_french:
                        tier_text = tier_raw if "€" in tier_raw else f"{tier_raw}€"
                    else:
                        tier_text = tier_raw if "$" in tier_raw else f"{tier_raw}$"

                    # Red badge: centered above white line
                    draw.text((272, badge_ty - 2), tier_text, fill=(255, 255, 255), font=font_tier, anchor="mm")
                    # Code box: centered in golden box
                    draw.text((946, box_cy), code_raw, fill=(251, 191, 36), font=font_code, anchor="mm")

                # Footer
                draw.text((365, 1162), channel_handle, fill=(255, 255, 255), font=font_footer, anchor="lm")
                draw.text((875, 1162), "@Alilo07BOT", fill=(255, 255, 255), font=font_footer, anchor="lm")

                h_sig = hashlib.sha256(str(coupon_list).encode()).hexdigest()[:8]
                out_file = self.output_dir / f"coupons_card_5_{h_sig}_{'fr' if is_french else 'dz'}.jpg"
                card.save(out_file, "JPEG", quality=95)
                return out_file
            except Exception as e:
                logger.warning(f"Failed rendering 5-coupon template: {e}, falling back to dynamic card")

        # 2. Check for 7-coupon poster template
        template_7_path = Path(settings.BASE_DIR) / "storage" / "assets" / "choice_day_coupon_template.png"
        if not template_7_path.exists():
            template_7_path = Path(settings.BASE_DIR) / "assets" / "choice_day_coupon_template.png"

        if len(coupon_list) == 7 and template_7_path.exists() and "choice" in promo_title.lower():
            try:
                card = Image.open(template_7_path).convert("RGBA")
                draw = ImageDraw.Draw(card)
                font_amount = _get_system_font(["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], 32)
                font_code = _get_system_font(["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], 38)
                font_footer = _get_system_font(["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], 24)

                row_y_centers = [481, 581, 681, 780, 880, 980, 1080]
                for idx, c in enumerate(coupon_list[:7]):
                    cy = row_y_centers[idx]
                    tier_raw = str(c.get("tier", "")).strip()
                    code_raw = str(c.get("code", "")).strip().upper()

                    if is_french:
                        tier_text = tier_raw if "€" in tier_raw else f"{tier_raw}€"
                    else:
                        tier_text = tier_raw if "$" in tier_raw else f"{tier_raw}$"

                    draw.text((285, cy + 12), tier_text, fill=(255, 255, 255), font=font_amount, anchor="mm")
                    draw.text((967, cy), code_raw, fill=(251, 191, 36), font=font_code, anchor="mm")

                draw.text((340, 1180), channel_handle, fill=(255, 255, 255), font=font_footer, anchor="lm")
                draw.text((860, 1180), "@Alilo07BOT", fill=(255, 255, 255), font=font_footer, anchor="lm")

                h_sig = hashlib.sha256(str(coupon_list).encode()).hexdigest()[:8]
                out_file = self.output_dir / f"coupons_card_7_{h_sig}_{'fr' if is_french else 'dz'}.png"
                card.save(out_file, "PNG")
                return out_file
            except Exception as te:
                logger.warning(f"7-coupon template rendering failed: {te}")

        # Clean white + AliExpress blush-pink multi-coupon ticket card (2..7 coupons)
        w, h = 1080, 1080
        card = Image.new("RGB", (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(card)

        # Top header band (soft blush with crimson accent)
        header_h = 200
        draw.rectangle((0, 0, w, header_h), fill=(255, 241, 242))
        draw.line([(0, header_h), (w, header_h)], fill=(254, 205, 211), width=2)

        font_title = _get_system_font(["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], 44)
        font_sub = _get_system_font(["arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"], 22)
        font_badge = _get_system_font(["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], 17)
        font_amount = _get_system_font(["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], 36)
        font_cond = _get_system_font(["arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"], 20)
        font_btn = _get_system_font(["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], 20)
        font_code = _get_system_font(["consolab.ttf", "arialbd.ttf", "DejaVuSansMono-Bold.ttf"], 30)
        font_footer = _get_system_font(["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], 21)

        # Header campaign badge
        if not date_range_str:
            try:
                from app.aliexpress.promos import promo_tracker
                p = getattr(promo_tracker, "get_active_france_promo", promo_tracker.get_active_promo)() if is_french else promo_tracker.get_active_promo()
                if not p:
                    next_p = promo_tracker.get_next_promo()
                    p = next_p[0] if next_p else None
                if p:
                    if getattr(p, "is_sunday_flash", False):
                        date_range_str = "SUPER SUNDAY • FLASH 24H DIMANCHE"
                    else:
                        month = p.end_date.strftime("%b").upper()
                        prefix = "DU" if is_french else "FROM"
                        date_range_str = f"{p.name.upper()} • {prefix} {p.start_date.day:02d} - {p.end_date.day:02d} {month}"
            except Exception:
                pass

        badge_text = date_range_str or ("CODES PROMO OFFICIELS" if is_french else "OFFICIAL PROMO CODES")
        full_badge = f"•  {badge_text.upper()}  •"
        badge_bbox = font_badge.getbbox(full_badge)
        badge_text_w = badge_bbox[2] - badge_bbox[0]
        badge_w = max(380, badge_text_w + 44)
        badge_x1 = (w - badge_w) // 2
        draw.rounded_rectangle((badge_x1, 22, badge_x1 + badge_w, 56), radius=17, fill=(225, 29, 72))
        draw.text((w // 2, 39), full_badge, fill=(255, 255, 255), font=font_badge, anchor="mm")

        # Main Title
        title_text = (
            f"ALIEXPRESS {promo_title.upper()} (FR)" if is_french else f"ALIEXPRESS {promo_title.upper()}"
        )
        t_font = font_title
        bbox = t_font.getbbox(title_text)
        if (bbox[2] - bbox[0]) > w - 100:
            for sz in [38, 34, 30, 26]:
                cand = _get_system_font(["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], sz)
                b = cand.getbbox(title_text)
                if (b[2] - b[0]) <= w - 100 or sz == 26:
                    t_font = cand
                    break
        draw.text((w // 2, 102), title_text, fill=(225, 29, 72), font=t_font, anchor="mm")

        notice_text = (
            "Codes promo AliExpress • Actifs dès 09h00 (Paris)"
            if is_french else "AliExpress coupon codes • Limited quantities"
        )
        draw.text((w // 2, 156), notice_text, fill=(100, 116, 139), font=font_sub, anchor="mm")

        # Ticket rows
        num_coupons = min(len(coupon_list), 7)
        card_w = 1000
        card_x = (w - card_w) // 2
        footer_y = h - 72
        avail_area_y = header_h + 18
        avail_area_h = footer_y - avail_area_y - 14

        if num_coupons <= 4:
            row_h, gap = 136, 22
        elif num_coupons == 5:
            row_h, gap = 126, 18
        elif num_coupons == 6:
            row_h, gap = 108, 14
        else:
            row_h, gap = 94, 12

        total_coupons_h = (num_coupons * row_h) + max(0, (num_coupons - 1) * gap)
        start_y = avail_area_y + max(8, (avail_area_h - total_coupons_h) // 2)

        for i, c in enumerate(coupon_list[:num_coupons]):
            tier_raw = str(c.get("tier", "")).strip()
            code_raw = str(c.get("code", "")).strip().upper()

            if is_french:
                if "dès" in tier_raw.lower():
                    parts = tier_raw.split("dès")
                    amt = parts[0].strip().lstrip("-")
                    headline = f"{amt}€ off" if "€" not in amt else f"{amt} off"
                    cond_str = f"Dès {parts[1].strip()}"
                elif "/" in tier_raw:
                    parts = tier_raw.replace("€", "").split("/")
                    headline = f"{parts[0].strip()}€ off"
                    cond_str = f"dès {parts[1].strip()}€ d'achat"
                else:
                    amt = tier_raw.replace("€", "").strip()
                    headline = f"{amt}€ off" if amt else "Code Promo"
                    cond_str = "Articles sélectionnés"
            else:
                if "/" in tier_raw:
                    parts = tier_raw.replace("$", "").split("/")
                    headline = f"US ${parts[0].strip()} off"
                    cond_str = f"orders US ${parts[1].strip()}+ (Select items only)"
                else:
                    amt = tier_raw.replace("$", "").strip()
                    headline = f"US ${amt} off" if amt else "Promo Coupon"
                    cond_str = "Select items · Limited quantity"

            cy = start_y + i * (row_h + gap)
            draw.rounded_rectangle(
                (card_x, cy, card_x + card_w, cy + row_h),
                radius=20,
                fill=(255, 241, 242),
                outline=(254, 205, 211),
                width=2,
            )

            # Left: bold crimson discount + spend condition
            draw.text((card_x + 36, cy + (row_h // 2) - 16), headline, fill=(225, 29, 72), font=font_amount, anchor="lm")
            draw.text((card_x + 38, cy + (row_h // 2) + 20), cond_str, fill=(190, 18, 60), font=font_cond, anchor="lm")

            # Right: "Shop more" pill + white code box
            right_w = 240
            rx1 = card_x + card_w - right_w - 22
            rx2 = card_x + card_w - 22
            pill_h = max(32, (row_h - 32) // 2)
            pill_y1 = cy + 12
            pill_y2 = pill_y1 + pill_h
            draw.rounded_rectangle((rx1, pill_y1, rx2, pill_y2), radius=pill_h // 2, fill=(225, 29, 72))
            draw.text(((rx1 + rx2) // 2, (pill_y1 + pill_y2) // 2),
                      "Profiter" if is_french else "Shop more", fill=(255, 255, 255), font=font_btn, anchor="mm")

            code_y1 = pill_y2 + 8
            code_y2 = cy + row_h - 12
            draw.rounded_rectangle((rx1, code_y1, rx2, code_y2), radius=12, fill=(255, 255, 255), outline=(254, 205, 211), width=2)
            draw.text(((rx1 + rx2) // 2, (code_y1 + code_y2) // 2), code_raw, fill=(15, 23, 42), font=font_code, anchor="mm")

        # Clean Footer
        draw.line([(40, footer_y), (w - 40, footer_y)], fill=(226, 232, 240), width=2)
        draw.text(
            (w // 2, footer_y + 36),
            f"{channel_handle}   •   @Alilo07BOT   •   dealscoutgreen.vercel.app",
            fill=(71, 85, 105),
            font=font_footer,
            anchor="mm",
        )

        h_sig = hashlib.sha256(str(coupon_list).encode()).hexdigest()[:8]
        out_file = self.output_dir / f"coupons_card_{h_sig}_{'fr' if is_french else 'dz'}.png"
        card.save(out_file, "PNG")
        return out_file

media_renderer = MediaRenderer()
