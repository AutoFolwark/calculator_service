import grpc
from fastapi import APIRouter, Body, Depends, Path
from fastapi.params import Param
from fastapi_cache import default_key_builder
from fastapi_cache.decorator import cache
from fastapi_pagination import Params
from fastapi_pagination.ext.sqlalchemy import paginate
from rfc9457 import NotFoundProblem
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.database.crud.location import LocationService
from app.database.db.session import get_async_db
from app.enums.auction import AuctionEnum
from app.enums.vehicle_type import parse_calculator_vehicle_type
from app.rpc_client_server.auction_api import ApiRpcClient
from app.schemas.calculator import CalculatorDataIn, CalculatorWithoutDetailsIn, GetLocationsIn, LocationPage
from app.services.calculator.calculator_service import CalculatorService
from app.services.calculator.exceptions import NotFoundError
from app.services.calculator.types import Calculator

calculator_api_router = APIRouter(prefix="/calculator")


@calculator_api_router.post(
    "",
    response_model=Calculator,
    tags=["calculator"],
    name="get_calculator",
    description="Get calculator by data from lot",
    summary="Get calculator by data (PREFERRED)",
)
@cache(expire=60 * 15, key_builder=default_key_builder)
async def get_calculator(data: CalculatorDataIn = Body(...), db: AsyncSession = Depends(get_async_db)):
    try:
        calculator_service = CalculatorService(
            db=db,
            price=data.price,
            auction=data.auction,
            fee_type=data.fee_type,
            location=data.location,
            vehicle_type=data.vehicle_type,
            destination=data.destination,
            year=data.year,
            purchase_for_company=data.purchase_for_company,
        )

        return await calculator_service.calculate()
    except NotFoundError as e:
        raise NotFoundProblem(detail=e.message)


@calculator_api_router.get(
    "/{auction}/{lot_id}",
    response_model=Calculator,
    tags=["calculator"],
    name="get_calculator",
    description="Get calculator by auction and lot id",
)
@cache(expire=60 * 15, key_builder=default_key_builder)
async def get_calculator_by_lot(
    auction: AuctionEnum = Path(..., description="Auction"),
    lot_id: str = Path(..., description="Lot id"),
    price: CalculatorWithoutDetailsIn = Param(...),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        async with ApiRpcClient() as rpc_client:
            lot = await rpc_client.get_lot_by_vin_or_lot_id(lot_id, auction)

        calculator_service = CalculatorService(
            db=db,
            price=price.price,
            auction=auction,
            fee_type=None,
            location=lot.lot[0].location,
            vehicle_type=parse_calculator_vehicle_type(
                lot.lot[0].body_type if hasattr(lot.lot[0], "body_type") else lot.lot[0].vehicle_type
            ),
            year=lot.lot[0].year if hasattr(lot.lot[0], "year") else None,
            purchase_for_company=price.purchase_for_company,
        )
        return await calculator_service.calculate()
    except grpc.aio.AioRpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            logger.warning(f"Could not find lot {lot_id}", extra={"lot_id": lot_id, "auction": auction})
            raise NotFoundProblem("Lot not found")
        elif e.code() == grpc.StatusCode.UNAVAILABLE:
            logger.error("Auction API service is unavailable", exc_info=e)
            raise NotFoundProblem("Auction API service is unavailable")
        elif e.code() == grpc.StatusCode.INTERNAL:
            logger.error("Internal error in Auction API service", exc_info=e)
            raise NotFoundProblem("Internal error in Auction API service")
        else:
            logger.error(f"Unknown error on auction {auction}", exc_info=e)
            raise NotFoundProblem("Unknown error in Auction API service")
    except NotFoundError as e:
        raise NotFoundProblem(detail=e.message)


@cache(expire=60 * 5, key_builder=default_key_builder)
@calculator_api_router.get("/locations", response_model=LocationPage, description="Get All Locations")
async def get_locations(
    db: AsyncSession = Depends(get_async_db), params: Params = Depends(), data: GetLocationsIn = Depends()
):
    location_service = LocationService(db)
    locations_stmt = await location_service.get_with_search_auction(
        search=data.search, auction=data.auction, get_stmt=True
    )
    return await paginate(db, locations_stmt, params)
