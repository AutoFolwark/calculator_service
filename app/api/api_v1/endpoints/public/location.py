from fastapi import APIRouter, Depends, Query
from fastapi_cache import default_key_builder
from fastapi_cache.decorator import cache
from fastapi_pagination import Params
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.delivery_price import DeliveryPriceService
from app.database.crud.location import LocationService
from app.database.crud.shipping_price import ShippingPriceService
from app.database.db.session import get_async_db
from app.database.schemas.destination import DestinationRead
from app.database.schemas.terminal import TerminalRead
from app.enums.auction import AuctionEnum
from app.schemas.location import GetLocationsIn, LocationPage

location_api_router = APIRouter(prefix="/locations")


@location_api_router.get("", response_model=LocationPage, tags=["locations"], description="Get locations list")
async def get_locations_list(
    params: Params = Depends(),
    filters: GetLocationsIn = Depends(),
    db: AsyncSession = Depends(get_async_db),
):
    location_service = LocationService(db)
    locations_stmt = await location_service.get_with_search_auction(
        search=filters.search, auction=filters.auction, get_stmt=True
    )
    return await paginate(db, locations_stmt, params)


@location_api_router.get(
    "/{location_id}/terminals",
    response_model=list[TerminalRead],
    tags=["locations"],
    description="Get available terminals for a location",
)
@cache(expire=60 * 5, key_builder=default_key_builder)
async def get_location_terminals(
    location_id: int,
    auction: AuctionEnum | None = Query(None, description="Filter by auction"),
    db: AsyncSession = Depends(get_async_db),
):
    delivery_service = DeliveryPriceService(db)
    terminals = await delivery_service.get_available_terminals(
        location_id=location_id,
        auction=auction,
    )
    return [TerminalRead.model_validate(term, from_attributes=True) for term in terminals]


@location_api_router.get(
    "/{location_id}/terminals/{terminal_id}/destinations",
    response_model=list[DestinationRead],
    tags=["locations"],
    description="Get available destinations for a location and terminal",
)
@cache(expire=60 * 5, key_builder=default_key_builder)
async def get_location_terminal_destinations(
    location_id: int,
    terminal_id: int,
    auction: AuctionEnum | None = Query(None, description="Filter by auction"),
    db: AsyncSession = Depends(get_async_db),
):
    shipping_service = ShippingPriceService(db)
    destinations = await shipping_service.get_available_destinations(
        location_id=location_id,
        terminal_id=terminal_id,
        auction=auction,
    )
    return [DestinationRead.model_validate(dest, from_attributes=True) for dest in destinations]
