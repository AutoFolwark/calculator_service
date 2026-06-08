import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database.models import DeliveryPrice, Location, Terminal, VehicleType  # noqa: E402
from app.database.models.base import Base  # noqa: E402
from app.enums.auction import AuctionEnum  # noqa: E402
from app.enums.vehicle_type import VehicleTypeEnum  # noqa: E402

# Rows used by find_location integration-style tests (in-memory DB, no external db.sqlite).
LOCATION_ROWS: list[tuple[str, str, str, AuctionEnum]] = [
    ("IL - Chicago North", "Chicago North", "IL", AuctionEnum.COPART),
    ("FL - Miami North", "Miami North", "FL", AuctionEnum.COPART),
    ("TX - Worth", "Fort Worth", "TX", AuctionEnum.COPART),
    ("FL - Pierce", "Fort Pierce", "FL", AuctionEnum.COPART),
    ("MN - Cloud", "St Cloud", "MN", AuctionEnum.COPART),
    ("PA - Pittsburgh North", "Pittsburgh North", "PA", AuctionEnum.COPART),
    ("PA - Philadelphia East", "Philadelphia East", "PA", AuctionEnum.COPART),
    ("FL - Orlando North", "Orlando North", "FL", AuctionEnum.COPART),
    ("MD - Washington Dc", "Washington Dc", "MD", AuctionEnum.COPART),
    ("CA - Ace Carson", "Ace Carson", "CA", AuctionEnum.IAAI),
    ("OH - Acron Canton", "Acron Canton", "OH", AuctionEnum.IAAI),
    ("MA - Boston-Shirley", "Boston Shirley", "MA", AuctionEnum.IAAI),
    ("TX - Houston North", "Houston North", "TX", AuctionEnum.IAAI),
    ("NJ - Avenel", "Avenel", "NJ", AuctionEnum.IAAI),
    ("ME - Portland Gorham", "Portland Gorham", "ME", AuctionEnum.IAAI),
    ("TX - San Antonio South", "San Antonio South", "TX", AuctionEnum.IAAI),
]


class LocationDb:
    def __init__(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    async def setup(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with self.session_factory() as session:
            terminal = Terminal(id=1, name="Test Terminal")
            session.add(terminal)

            vehicle_types = {
                AuctionEnum.COPART: VehicleType(
                    id=1,
                    auction=AuctionEnum.COPART,
                    vehicle_type=VehicleTypeEnum.CAR,
                ),
                AuctionEnum.IAAI: VehicleType(
                    id=2,
                    auction=AuctionEnum.IAAI,
                    vehicle_type=VehicleTypeEnum.CAR,
                ),
            }
            session.add_all(vehicle_types.values())

            for index, (name, city, state, auction) in enumerate(LOCATION_ROWS, start=1):
                location = Location(id=index, name=name, city=city, state=state)
                session.add(location)
                session.add(
                    DeliveryPrice(
                        id=index,
                        location_id=index,
                        terminal_id=1,
                        vehicle_type_id=vehicle_types[auction].id,
                        price=100,
                    )
                )

            await session.commit()

    async def teardown(self) -> None:
        await self.engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as db:
            yield db


@pytest.fixture
def location_db() -> LocationDb:
    db = LocationDb()
    asyncio.run(db.setup())
    yield db
    asyncio.run(db.teardown())
