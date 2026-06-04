from collections.abc import Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base import BaseService
from app.database.models import DeliveryPrice, Destination, ShippingPrice, Terminal, VehicleType
from app.database.schemas.shipping_price import ShippingPriceCreate, ShippingPriceUpdate
from app.enums.auction import AuctionEnum


class ShippingPriceService(BaseService[ShippingPrice, ShippingPriceCreate, ShippingPriceUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(ShippingPrice, session)

    async def get_by_terminal_and_vehicle_type(
        self, terminal: Terminal, vehicle_type: VehicleType
    ) -> Sequence[ShippingPrice]:
        result = await self.session.execute(
            select(ShippingPrice).where(
                and_(ShippingPrice.terminal_id == terminal.id, ShippingPrice.vehicle_type_id == vehicle_type.id)
            )
        )
        return result.scalars().all()

    async def get_by_destination_and_vehicle_type(
        self, destination: Destination, vehicle_type: VehicleType
    ) -> Sequence[ShippingPrice]:
        result = await self.session.execute(
            select(ShippingPrice).where(
                and_(ShippingPrice.destination_id == destination.id, ShippingPrice.vehicle_type_id == vehicle_type.id)
            )
        )
        return result.scalars().all()

    async def create_by_destination_vehicle_type_terminal(
        self, price: int, destination: Destination, vehicle_type: VehicleType, terminal: Terminal
    ) -> ShippingPrice:
        obj = ShippingPrice(price=price, destination=destination, terminal=terminal, vehicle_type=vehicle_type)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def get_by_destination_vehicle_type_terminal_single(
        self, destination: Destination, vehicle_type: VehicleType, terminal: Terminal
    ) -> ShippingPrice | None:
        result = await self.session.execute(
            select(ShippingPrice).where(
                and_(
                    ShippingPrice.destination_id == destination.id,
                    ShippingPrice.vehicle_type_id == vehicle_type.id,
                    ShippingPrice.terminal_id == terminal.id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_available_destinations(
        self,
        location_id: int,
        terminal_id: int,
        auction: AuctionEnum | None = None,
        get_stmt: bool = False,
    ):
        stmt = (
            select(Destination)
            .join(ShippingPrice, ShippingPrice.destination_id == Destination.id)
            .join(
                DeliveryPrice,
                and_(
                    DeliveryPrice.vehicle_type_id == ShippingPrice.vehicle_type_id,
                    DeliveryPrice.location_id == location_id,
                    DeliveryPrice.terminal_id == terminal_id,
                ),
            )
            .where(ShippingPrice.terminal_id == terminal_id)
            .distinct()
        )

        if auction:
            stmt = stmt.join(VehicleType, ShippingPrice.vehicle_type_id == VehicleType.id).where(
                VehicleType.auction == auction
            )

        if get_stmt:
            return stmt

        result = await self.session.execute(stmt)
        return result.scalars().unique().all()
