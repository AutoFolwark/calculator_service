import time
from typing import TYPE_CHECKING

import grpc
from pydantic import BaseModel

from app.core.logger import logger
from app.database.crud.delivery_price import DeliveryPriceService
from app.database.crud.destination import DestinationService
from app.database.crud.fee_type import FeeTypeService
from app.database.crud.location import LocationService
from app.database.crud.shipping_price import ShippingPriceService
from app.database.crud.vehicle_type import VehicleTypeService
from app.database.db.session import get_db_context
from app.database.models import Destination, FeeType, Location
from app.enums.auction import AuctionEnum
from app.enums.fee_type import FeeTypeEnum
from app.enums.vehicle_type import (
    CalculatorVehicleTypeEnum,
    parse_calculator_vehicle_type,
    to_pricing_vehicle_type,
)
from app.rpc_client_server.auction_api import ApiRpcClient
from app.rpc_client_server.gen.python.calculator.v1 import calculator_pb2, calculator_pb2_grpc
from app.rpc_client_server.gen.python.calculator.v1.calculator_pb2 import (
    AdditionalFeesOut,
    CalculatorBatchItem,
    City,
    DefaultCalculator,
    DetailedCalculatorData,
    EUCalculator,
    GetCalculatorWithDataBatchResponse,
    GetCalculatorWithDataResponse,
    GetCalculatorWithoutDataResponse,
    SpecialFee,
    Taxes,
    TaxFlags,
)
from app.rpc_client_server.gen.python.calculator.v1.calculator_pb2 import (
    Calculator as CalculatorProto,
)
from app.rpc_client_server.gen.python.calculator.v1.calculator_pb2 import (
    CalculatorOut as CalculatorOutProto,
)
from app.services.calculator.calculator_service import CalculatorService
from app.services.calculator.exceptions import NotFoundError
from app.services.calculator.types import Calculator as CalculatorModel
from app.services.calculator.types import CalculatorOut as CalculatorOutModel

if TYPE_CHECKING:
    pass


class CalculatorRequest(BaseModel):
    price: int
    auction: AuctionEnum | None
    fee_type: FeeTypeEnum | None
    location: str
    vehicle_type: CalculatorVehicleTypeEnum
    destination: str | None
    year: int | None = None
    purchase_for_company: bool = False


class CalculatorRpc(calculator_pb2_grpc.CalculatorServiceServicer):
    @staticmethod
    def _safe_enum_conversion(value, enum_cls, field_name: str):
        if value in (None, ""):
            return None
        candidates = [value]
        if isinstance(value, str):
            candidates.extend([value.upper(), value.lower()])
        for candidate in candidates:
            try:
                return enum_cls(candidate)
            except ValueError:
                continue
        raise ValueError(f"Invalid {field_name}: {value}")

    @staticmethod
    def _to_city(city) -> City:
        return City(name=city.name, price=float(city.price))

    def _to_cities(self, cities) -> list[City]:
        return [self._to_city(city) for city in (cities or [])]

    @staticmethod
    def _to_special_fee(fee) -> SpecialFee:
        return SpecialFee(name=fee.name, price=float(fee.price))

    def _to_additional_fees(self, additional) -> AdditionalFeesOut:
        if not additional:
            return AdditionalFeesOut(summ=0.0, fees=[], auction_fee=0.0, internet_fee=0.0, live_fee=0.0)
        return AdditionalFeesOut(
            summ=float(additional.summ),
            fees=[self._to_special_fee(fee) for fee in additional.fees],
            auction_fee=float(additional.auction_fee),
            internet_fee=float(additional.internet_fee),
            live_fee=float(additional.live_fee),
        )

    def _to_default_calculator(self, default_calculator) -> DefaultCalculator:
        return DefaultCalculator(
            broker_fee=float(default_calculator.broker_fee),
            transportation_price=self._to_cities(default_calculator.transportation_price),
            ocean_ship=self._to_cities(default_calculator.ocean_ship),
            additional=self._to_additional_fees(default_calculator.additional),
            totals=self._to_cities(default_calculator.totals),
            auction_fee=float(default_calculator.auction_fee),
            live_fee=float(default_calculator.live_fee),
            internet_fee=float(default_calculator.internet_fee),
        )

    def _to_tax_flags(self, tax_flags) -> TaxFlags | None:
        if not tax_flags:
            return None
        return TaxFlags(
            is_monument=tax_flags.is_monument,
            purchase_for_company=tax_flags.purchase_for_company,
            duty_category=tax_flags.duty_category,
            duty_rate=float(tax_flags.duty_rate),
            vat_rate=float(tax_flags.vat_rate),
        )

    def _to_eu_calculator(self, eu_calculator) -> EUCalculator:
        taxes = Taxes(
            vats=self._to_cities(eu_calculator.taxes.vats if eu_calculator.taxes else []),
            duties=self._to_cities(eu_calculator.taxes.duties if eu_calculator.taxes else []),
        )
        eu_kwargs = dict(
            broker_fee=float(eu_calculator.broker_fee),
            transportation_price=self._to_cities(eu_calculator.transportation_price),
            ocean_ship=self._to_cities(eu_calculator.ocean_ship),
            additional=self._to_additional_fees(eu_calculator.additional),
            totals=self._to_cities(eu_calculator.totals),
            taxes=taxes,
            custom_agency=float(eu_calculator.custom_agency),
            totals_without_default=self._to_cities(eu_calculator.totals_without_default),
        )
        tax_flags = self._to_tax_flags(eu_calculator.tax_flags)
        if tax_flags is not None:
            eu_kwargs["tax_flags"] = tax_flags
        return EUCalculator(**eu_kwargs)

    def _to_calculator_out(self, calculator_out: CalculatorOutModel) -> CalculatorOutProto:
        return CalculatorOutProto(
            calculator=self._to_default_calculator(calculator_out.calculator),
            eu_calculator=self._to_eu_calculator(calculator_out.eu_calculator),
            currency=calculator_out.currency,
        )

    def _to_calculator(self, calculator: CalculatorModel) -> CalculatorProto:
        return CalculatorProto(
            calculator_in_dollars=self._to_calculator_out(calculator.calculator_in_dollars),
            calculators_in_currencies=[
                self._to_calculator_out(calculator_out) for calculator_out in calculator.calculators_in_currencies
            ],
            destinations=list(calculator.destinations),
            rate=float(calculator.rate),
        )

    @staticmethod
    def _get_optional_int32(request, field_name: str) -> int | None:
        return getattr(request, field_name) if request.HasField(field_name) else None

    async def _build_detailed_data(self, db, params: CalculatorRequest) -> DetailedCalculatorData | None:
        logger.debug(f"Building detailed calculator data for params: {params}")
        try:
            vehicle_type_service = VehicleTypeService(db)
            location_service = LocationService(db)
            delivery_price_service = DeliveryPriceService(db)
            fee_type_service = FeeTypeService(db)
            shipping_price_service = ShippingPriceService(db)
            pricing_vehicle_type = to_pricing_vehicle_type(params.vehicle_type)

            vehicle_type_obj = await vehicle_type_service.get_by_auction_and_type(
                params.auction,
                pricing_vehicle_type,
            )
            if not vehicle_type_obj:
                logger.warning("Vehicle type not found while building detailed data")
                return None

            location_obj = await location_service.find_location(params.location, vehicle_type_obj)
            if not location_obj:
                logger.warning(f"Location not found while building detailed data: {params.location}")
                return None

            fee_type_obj = await fee_type_service.get_by_fee_auction(
                params.auction, params.fee_type if params.fee_type else FeeTypeEnum.NON_CLEAN_TITLE_FEE
            )

            delivery_prices = await delivery_price_service.get_by_terminal_location_vehicle_type(
                location=location_obj,
                vehicle_type=vehicle_type_obj,
            )

            terminals = [
                calculator_pb2.Terminal(
                    terminal_id=dp.terminal.id if dp.terminal else 0,
                    terminal_name=dp.terminal.name if dp.terminal and dp.terminal.name else "",
                )
                for dp in delivery_prices
                if dp.terminal
            ]

            destination_map = {}
            for dp in delivery_prices:
                if not dp.terminal:
                    continue
                shipping_prices = await shipping_price_service.get_by_terminal_and_vehicle_type(
                    dp.terminal,
                    vehicle_type_obj,
                )
                for sp in shipping_prices:
                    dest_id = sp.destination_id or 0
                    if dest_id in destination_map:
                        continue
                    destination_map[dest_id] = calculator_pb2.Destination(
                        destination_id=dest_id,
                        destination_name=sp.destination.name if sp.destination else "",
                    )

            detailed_kwargs = dict(
                location_id=location_obj.id,
                location_data=calculator_pb2.Location(
                    name=location_obj.name or "",
                    city=location_obj.city or "",
                    state=location_obj.state or "",
                    postal_code=location_obj.postal_code or "",
                    email=location_obj.email or "",
                ),
                terminals=terminals,
                available_destinations=list(destination_map.values()),
            )

            if fee_type_obj:
                detailed_kwargs["fee_type_id"] = fee_type_obj.id
                detailed_kwargs["fee_type_data"] = calculator_pb2.FeeType(
                    auction=fee_type_obj.auction.value if fee_type_obj.auction else "",
                    fee_type=fee_type_obj.fee_type.value if fee_type_obj.fee_type else "",
                )

            return calculator_pb2.DetailedCalculatorData(**detailed_kwargs)

        except Exception as e:
            logger.error(f"Failed to build detailed calculator data: {e}", exc_info=True)
            return None

    async def _calculate(self, request: CalculatorRequest) -> tuple[CalculatorProto, DetailedCalculatorData | None]:
        async with get_db_context() as db:
            logger.debug("Database connection established")
            calculator_service = CalculatorService(db=db, **request.model_dump())
            logger.debug("CalculatorService instance created")
            result = await calculator_service.calculate()
            logger.info("Calculation completed successfully")

            calculator_out = self._to_calculator(result)
            logger.debug("Calculator proto created successfully")
            detailed_data = await self._build_detailed_data(db, request)
            logger.debug("Detailed calculator data prepared")
            return calculator_out, detailed_data

    async def _calculate_and_respond(self, request: CalculatorRequest, context, response_cls):
        try:
            calculator_out, detailed_data = await self._calculate(request)
            return response_cls(
                data=calculator_out,
                detailed_data=detailed_data,
                success=True,
            )
        except NotFoundError as e:
            logger.warning(f"Not found error in calculation: {e}")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            return response_cls(
                message=str(e),
                success=False,
            )
        except ValueError as e:
            logger.warning(f"Validation error in calculation: {e}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return response_cls(
                message=str(e),
                success=False,
            )
        except Exception as e:
            logger.error(f"Unexpected error during calculation: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return response_cls(
                message="Internal server error",
                success=False,
            )

    @staticmethod
    async def _get_entity_or_set_not_found(db, model, obj_id: int, entity_name: str, context):
        entity = await db.get(model, obj_id)
        if entity:
            return entity

        message = f"{entity_name} {obj_id} not found"
        logger.warning(f"{message}")
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details(message)
        return None

    def get_params_from_request(self, request: calculator_pb2.GetCalculatorWithDataRequest) -> CalculatorRequest:
        return CalculatorRequest(
            price=request.price,
            auction=self._safe_enum_conversion(request.auction, AuctionEnum, "auction"),
            fee_type=self._safe_enum_conversion(request.fee_type, FeeTypeEnum, "fee_type"),
            location=request.location,
            vehicle_type=parse_calculator_vehicle_type(request.vehicle_type),
            destination=request.destination if request.HasField("destination") else None,
            year=self._get_optional_int32(request, "year"),
            purchase_for_company=request.purchase_for_company,
        )

    async def GetCalculatorWithData(
        self, request: calculator_pb2.GetCalculatorWithDataRequest, context
    ) -> calculator_pb2.GetCalculatorWithDataResponse:
        logger.info(
            f"GetCalculatorWithData called with price: {request.price}, auction: {request.auction}, location: {request.location}"
        )
        try:
            if request.price < -1:
                logger.warning(f"Invalid price provided: {request.price}")
                raise ValueError("Price must be greater than -1")

            if not request.location:
                logger.warning("Location not provided in request")
                raise ValueError("Location is required")

            logger.debug(
                f"Validating request parameters: auction={request.auction}, fee_type={request.fee_type}, vehicle_type={request.vehicle_type}"
            )

            params = self.get_params_from_request(request)
            logger.info(f"Parameters validated successfully for GetCalculatorWithData: {params}")
            calculator, detailed_data = await self._calculate(params)
            return GetCalculatorWithDataResponse(data=calculator, detailed_data=detailed_data, success=True)

        except NotFoundError as e:
            logger.warning(f"Not found error in GetCalculatorWithData: {e}")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            return GetCalculatorWithDataResponse(
                message=str(e),
                success=False,
            )
        except ValueError as e:
            logger.warning(f"Validation error in GetCalculatorWithData: {e}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return GetCalculatorWithDataResponse(
                message=str(e),
                success=False,
            )
        except Exception as e:
            logger.error(f"Unexpected error in GetCalculatorWithData: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return GetCalculatorWithDataResponse(
                message="Internal server error",
                success=False,
            )

    async def GetCalculatorWithIds(
        self, request: calculator_pb2.GetCalculatorWithIdsRequest, context
    ) -> calculator_pb2.GetCalculatorWithIdsResponse:
        logger.info(
            f"GetCalculatorWithIds called with price: {request.price}, auction: {request.auction}, location_id: {request.location_id}"
        )
        try:
            if request.price < -1:
                logger.warning(f"Invalid price provided: {request.price}")
                raise ValueError("Price must be greater than -1")

            if not request.HasField("location_id") or request.location_id <= 0:
                logger.warning("Location ID not provided in request")
                raise ValueError("location_id is required")

            if not request.vehicle_type:
                logger.warning("Vehicle type not provided in request")
                raise ValueError("vehicle_type is required")

            auction_enum = self._safe_enum_conversion(request.auction, AuctionEnum, "auction")
            calculator_vehicle_type = parse_calculator_vehicle_type(request.vehicle_type)
            pricing_vehicle_type = to_pricing_vehicle_type(calculator_vehicle_type)

            location_message = None
            destination_name = ""
            destination_value = None
            fee_type_enum_value = None
            fee_type_message = None
            terminal_name = ""
            location_name = ""

            try:
                async with get_db_context() as db:
                    destination_service = DestinationService(db)

                    location = await self._get_entity_or_set_not_found(
                        db,
                        Location,
                        request.location_id,
                        "Location",
                        context,
                    )
                    if not location:
                        return calculator_pb2.GetCalculatorWithIdsResponse()

                    location_name = location.name or ""
                    location_message = calculator_pb2.Location(
                        name=location.name or "",
                        city=location.city or "",
                        state=location.state or "",
                        postal_code=location.postal_code or "",
                        email=location.email or "",
                    )

                    if request.HasField("destination_id") and request.destination_id > 0:
                        destination = await self._get_entity_or_set_not_found(
                            db,
                            Destination,
                            request.destination_id,
                            "Destination",
                            context,
                        )
                        if not destination:
                            return calculator_pb2.GetCalculatorWithIdsResponse()
                    else:
                        destination = await destination_service.get_default()
                        if not destination:
                            logger.error("Default destination not found")
                            context.set_code(grpc.StatusCode.NOT_FOUND)
                            context.set_details("Default destination not found")
                            return calculator_pb2.GetCalculatorWithIdsResponse()

                    destination_name = destination.name or ""
                    destination_value = destination.name or ""

                    if request.HasField("fee_type_id") and request.fee_type_id > 0:
                        fee_type = await self._get_entity_or_set_not_found(
                            db,
                            FeeType,
                            request.fee_type_id,
                            "Fee type",
                            context,
                        )
                        if not fee_type:
                            return calculator_pb2.GetCalculatorWithIdsResponse()
                        fee_type_enum_value = fee_type.fee_type
                        fee_type_message = calculator_pb2.FeeType(
                            auction=fee_type.auction.value if fee_type.auction else "",
                            fee_type=fee_type.fee_type.value if fee_type.fee_type else "",
                        )

                    vehicle_type_service = VehicleTypeService(db)
                    vehicle_type_model = await vehicle_type_service.get_by_auction_and_type(
                        auction_enum, pricing_vehicle_type
                    )
                    if not vehicle_type_model:
                        message = "Vehicle type not found"
                        logger.warning(f"{message}")
                        context.set_code(grpc.StatusCode.NOT_FOUND)
                        context.set_details(message)
                        return calculator_pb2.GetCalculatorWithIdsResponse()

                    delivery_price_service = DeliveryPriceService(db)
                    delivery_prices = await delivery_price_service.get_by_terminal_location_vehicle_type(
                        location=location,
                        vehicle_type=vehicle_type_model,
                    )
                    if delivery_prices:
                        terminal_name = delivery_prices[0].terminal.name or ""
            except Exception as e:
                logger.error(f"Error preparing data for GetCalculatorWithIds: {e}", exc_info=True)
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to prepare calculator data")
                return calculator_pb2.GetCalculatorWithIdsResponse()

            calc_request = CalculatorRequest(
                price=request.price,
                auction=auction_enum,
                fee_type=fee_type_enum_value,
                location=location_name,
                vehicle_type=calculator_vehicle_type,
                destination=destination_value,
                year=self._get_optional_int32(request, "year"),
                purchase_for_company=request.purchase_for_company,
            )

            calculator_out, _detailed_data = await self._calculate(calc_request)
            if calculator_out is None:
                return calculator_pb2.GetCalculatorWithIdsResponse()

            response_kwargs = dict(
                calculator=calculator_out,
                location=location_message,
                terminal_name=terminal_name,
                destination_name=destination_name,
            )

            if fee_type_message:
                response_kwargs["fee_type"] = fee_type_message

            return calculator_pb2.GetCalculatorWithIdsResponse(**response_kwargs)

        except ValueError as e:
            logger.warning(f"Validation error in GetCalculatorWithIds: {e}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return calculator_pb2.GetCalculatorWithIdsResponse()
        except Exception as e:
            logger.error(f"Unexpected error in GetCalculatorWithIds: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return calculator_pb2.GetCalculatorWithIdsResponse()

    async def GetCalculatorWithDataBatch(self, request, context):
        logger.info(f"GetCalculatorWithDataBatch called with {len(request.data)} requests")

        start = time.time()
        try:
            responses = []

            for i, req_item in enumerate(request.data):
                item_start = time.time()

                params = self.get_params_from_request(req_item.data)
                response = await self._calculate_and_respond(
                    params,
                    context,
                    GetCalculatorWithDataResponse,
                )

                item_time = time.time() - item_start
                logger.info(f"Item {i} (lot_id={req_item.lot_id}) took {item_time:.3f}s")

                if context.code() != grpc.StatusCode.OK:
                    logger.error(f"Error in batch item with lot_id {req_item.lot_id}: {context.details()}")
                    context.set_code(grpc.StatusCode.OK)
                    context.set_details("")
                    continue

                responses.append(CalculatorBatchItem(calculator=response.data, lot_id=req_item.lot_id))

            total_time = time.time() - start
            logger.info(f"Total batch time: {total_time:.3f}s")

            return GetCalculatorWithDataBatchResponse(data=responses)

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return GetCalculatorWithDataBatchResponse()

    async def GetCalculatorWithoutData(self, request, context) -> calculator_pb2.GetCalculatorWithoutDataResponse:
        logger.info(
            f"GetCalculatorWithoutData called with price: {request.price}, lot_id: {request.lot_id}, auction: {request.auction}"
        )
        try:
            if request.price <= 0:
                logger.warning(f"Invalid price provided: {request.price}")
                raise ValueError("Price must be greater than 0")

            if not request.lot_id:
                logger.warning("Lot ID not provided in request")
                raise ValueError("Lot ID is required")

            auction_enum = self._safe_enum_conversion(request.auction, AuctionEnum, "auction")
            logger.debug(f"Auction enum converted: {auction_enum}")

            lot = None
            try:
                logger.info(f"Fetching lot data for lot_id: {request.lot_id}, auction: {request.auction}")
                async with ApiRpcClient() as client:
                    lot = await client.get_lot_by_vin_or_lot_id(request.lot_id, request.auction)
                logger.info(f"Successfully fetched lot data for lot_id: {request.lot_id}")
            except grpc.aio.AioRpcError as e:
                logger.error(f"RPC error when fetching lot data: {e.code()}: {e.details()}")
                if e.code() == grpc.StatusCode.NOT_FOUND:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Lot {request.lot_id} not found")
                    return GetCalculatorWithoutDataResponse(
                        message=f"Lot {request.lot_id} not found",
                        success=False,
                    )
                elif e.code() == grpc.StatusCode.UNAVAILABLE:
                    context.set_code(grpc.StatusCode.UNAVAILABLE)
                    context.set_details("External service unavailable")
                    return GetCalculatorWithoutDataResponse(
                        message="Cannot fetch lot data: service unavailable",
                        success=False,
                    )
                else:
                    context.set_code(grpc.StatusCode.INTERNAL)
                    context.set_details("Failed to fetch lot data")
                    return GetCalculatorWithoutDataResponse(
                        message="Failed to fetch lot data",
                        success=False,
                    )
            except Exception as e:
                logger.error(f"Unexpected error when fetching lot data: {e}", exc_info=True)
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to fetch lot data")
                return GetCalculatorWithoutDataResponse(
                    message="Failed to fetch lot data",
                    success=False,
                )

            if not lot or not lot.lot or len(lot.lot) == 0:
                logger.warning(f"No lot data found for lot_id: {request.lot_id}")
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"No data found for lot {request.lot_id}")
                return GetCalculatorWithoutDataResponse(
                    message=f"No data found for lot {request.lot_id}",
                    success=False,
                )

            try:
                lot_item = lot.lot[0]
                logger.debug(f"Processing lot item with location: {lot_item.location}")
                request_year = self._get_optional_int32(request, "year")

                if not lot_item.location:
                    logger.error("Lot location is empty")
                    raise ValueError("Lot location is empty")

                vehicle_type = parse_calculator_vehicle_type(
                    lot_item.body_type if hasattr(lot_item, "body_type") else lot_item.vehicle_type
                )
                logger.debug(f"Determined vehicle type: {vehicle_type}")

                params = CalculatorRequest(
                    price=request.price,
                    auction=auction_enum,
                    fee_type=None,
                    location=lot_item.location,
                    vehicle_type=vehicle_type,
                    destination=request.destination if request.HasField("destination") else None,
                    year=request_year
                    if request_year is not None
                    else (lot_item.year if hasattr(lot_item, "year") else None),
                    purchase_for_company=request.purchase_for_company,
                )
                logger.info(f"Parameters prepared for calculation: {params}")

            except (IndexError, AttributeError) as e:
                logger.error(f"Error parsing lot data: {e}")
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Invalid lot data format")
                return GetCalculatorWithoutDataResponse(
                    message="Invalid lot data format",
                    success=False,
                )

            return await self._calculate_and_respond(
                params,
                context,
                GetCalculatorWithoutDataResponse,
            )

        except ValueError as e:
            logger.warning(f"Validation error in GetCalculatorWithoutData: {e}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return GetCalculatorWithoutDataResponse(
                message=str(e),
                success=False,
            )
        except Exception as e:
            logger.error(f"Unexpected error in GetCalculatorWithoutData: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return GetCalculatorWithoutDataResponse(
                message="Internal server error",
                success=False,
            )
