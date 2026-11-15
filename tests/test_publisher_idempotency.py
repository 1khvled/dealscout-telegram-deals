"""Publisher idempotency: never send the same post twice after a network timeout."""
import pytest
import httpx
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.models import Base, Deal
from app.publisher.publisher import TelegramPublisher


class _FakeTelegramClient:
    def __init__(self):
        self.posts = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, *args, **kwargs):
        self.posts += 1
        raise httpx.ConnectTimeout("simulated timeout")


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _new_deal(session):
    deal = Deal(
        product_id="1005007336232520",
        original_url="https://www.aliexpress.com/item/1005007336232520.html",
        normalized_url="https://www.aliexpress.com/item/1005007336232520.html",
        affiliate_url="https://s.click.aliexpress.com/e/_testdup",
        title="AJAZZ AJ179",
        currency="USD",
        current_price=20.9,
        status="PENDING",
    )
    session.add(deal)
    return deal


CAPTION = (
    "تخفيض ممتاز لـ AJAZZ AJ179\n"
    "السعر : 20.9$ 🔥\n"
    "رابط https://s.click.aliexpress.com/e/_testdup"
)


@pytest.mark.asyncio
async def test_network_timeout_is_not_retried(session):
    """A timed-out sendPhoto may already be live; retrying used to post 3 copies."""
    deal = _new_deal(session)
    await session.commit()
    await session.refresh(deal)

    publisher = TelegramPublisher(bot_token="TEST_TOKEN", target_channel="@DzAliexpress0")
    fake = _FakeTelegramClient()

    with patch.object(publisher, "_find_recent_channel_post", new=AsyncMock(return_value=None)), \
         patch("app.publisher.publisher.httpx.AsyncClient", return_value=fake):
        success, err = await publisher.publish_deal(
            session=session, deal=deal, caption=CAPTION, image_path=None, force=True
        )

    assert success is False
    assert fake.posts == 1, "ambiguous network failures must not be retried"
    assert "unconfirmed" in err


@pytest.mark.asyncio
async def test_existing_channel_post_is_reused_instead_of_duplicated(session):
    """If the channel already shows the deal, record it as published without sending again."""
    deal = _new_deal(session)
    await session.commit()
    await session.refresh(deal)

    publisher = TelegramPublisher(bot_token="TEST_TOKEN", target_channel="@DzAliexpress0")
    fake = _FakeTelegramClient()

    with patch.object(publisher, "_find_recent_channel_post", new=AsyncMock(return_value=2747)), \
         patch("app.publisher.publisher.httpx.AsyncClient", return_value=fake):
        success, err = await publisher.publish_deal(
            session=session, deal=deal, caption=CAPTION, image_path=None, force=True
        )

    assert success is True
    assert err is None
    assert fake.posts == 0, "the already-live post must not be sent again"
    assert deal.telegram_message_id == 2747
    assert deal.status == "PUBLISHED"
