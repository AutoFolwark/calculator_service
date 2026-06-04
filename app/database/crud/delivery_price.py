from collections.abc import Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base import BaseService
from app.database.models import DeliveryPrice, Location, Terminal, VehicleType
from app.database.schemas.delivery_price import DeliveryPriceCreate, DeliveryPriceUpdate
from app.enums.auction import AuctionEnum


class DeliveryPriceService(BaseService[DeliveryPrice, DeliveryPriceCreate, DeliveryPriceUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(DeliveryPrice, session)

    async def create_with_terminal_location_vehicle_type(
        self, price: int, terminal: Terminal, location: Location, vehicle_type: VehicleType
    ):
        delivery_price = DeliveryPrice(price=price, terminal=terminal, location=location, vehicle_type=vehicle_type)
        self.session.add(delivery_price)
        await self.session.commit()
        await self.session.refresh(delivery_price)
        return delivery_price

    async def get_by_terminal_location_vehicle_type(
        self,
        location: Location,
        vehicle_type: VehicleType,
        terminal: Terminal = None,
    ) -> Sequence[DeliveryPrice]:
        conditions = [DeliveryPrice.location_id == location.id, DeliveryPrice.vehicle_type_id == vehicle_type.id]
        if terminal:
            conditions.append(DeliveryPrice.terminal_id == terminal.id)

        result = await self.session.execute(select(DeliveryPrice).where(and_(*conditions)))
        return result.scalars().all()

    async def get_available_terminals(
        self,
        location_id: int,
        auction: AuctionEnum | None = None,
        get_stmt: bool = False,
    ):
        stmt = (
            select(Terminal)
            .join(DeliveryPrice, DeliveryPrice.terminal_id == Terminal.id)
            .where(DeliveryPrice.location_id == location_id)
            .distinct()
        )

        if auction:
            stmt = stmt.join(VehicleType, DeliveryPrice.vehicle_type_id == VehicleType.id).where(
                VehicleType.auction == auction
            )

        if get_stmt:
            return stmt

        result = await self.session.execute(stmt)
        return result.scalars().unique().all()
