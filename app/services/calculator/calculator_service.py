import asyncio

from currency_converter import CurrencyConverter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import log_async_execution_time, logger
from app.database.crud.additional_fee import AdditionalFeeService
from app.database.crud.additional_special_fee import AdditionalSpecialFeeService
from app.database.crud.delivery_price import DeliveryPriceService
from app.database.crud.destination import DestinationService
from app.database.crud.fee import FeeService
from app.database.crud.fee_type import FeeTypeService
from app.database.crud.location import LocationService
from app.database.crud.shipping_price import ShippingPriceService
from app.database.crud.vehicle_type import VehicleTypeService
from app.database.db.session import AsyncSessionLocal
from app.enums.auction import AuctionEnum
from app.enums.fee_type import FeeTypeEnum
from app.enums.vehicle_type import (
    CalculatorVehicleTypeEnum,
    VehicleTypeEnum,
    to_pricing_vehicle_type,
)
from app.schemas.calculator import CalculatorDataIn
from app.services.calculator.exceptions import (
    DeliveryPriceNotFoundError,
    DestinationNotFoundError,
    LocationNotFoundError,
    ShippingPriceNotFoundError,
    VehicleTypeNotFoundError,
)
from app.services.calculator.tax_rules import (
    compute_is_monument,
    get_duty_rate,
    get_vat_rate,
    infer_duty_category,
)
from app.services.calculator.types import (
    AdditionalFeesOut,
    Calculator,
    CalculatorOut,
    City,
    DefaultCalculator,
    EUCalculator,
    SpecialFee,
    Taxes,
    TaxFlags,
)


class CalculatorService:
    BROKER_FEE = 600

    def __init__(
        self,
        db: AsyncSession,
        price: int,
        auction: AuctionEnum,
        location: str,
        vehicle_type: CalculatorVehicleTypeEnum,
        fee_type: FeeTypeEnum | None = None,
        destination: str | None = None,
        # New BIDMAX specific fields
        year: int | None = None,
        purchase_for_company: bool = False,
    ):
        """Initialize calculator input data and tax-related flags."""

        self.db = db
        self.data = CalculatorDataIn(
            price=price,
            auction=auction,
            fee_type=fee_type,
            location=location,
            vehicle_type=vehicle_type,
            destination=destination,
            year=year,
            purchase_for_company=purchase_for_company,
        )
        self.currency_converter = CurrencyConverter()
        self.is_monument = self._compute_is_monument(self.data.year)
        self.duty_category = infer_duty_category(vehicle_type=self.data.vehicle_type)

    @log_async_execution_time("Additional Fees Calculation")
    async def additional_fees_calculator(self) -> AdditionalFeesOut:
        """Calculate auction-related additional fees."""

        def normalize_fee(value: float | int | None) -> float:
            if value is None:
                return 0.0
            return round(float(value), 2)

        additional_special_fee_service = AdditionalSpecialFeeService(self.db)
        fee_type_service = FeeTypeService(self.db)
        fee_service = FeeService(self.db)
        additional_fee_service = AdditionalFeeService(self.db)

        fees = await additional_special_fee_service.get_additional_special_fee(self.data.auction)

        all_fees_summ = sum(normalize_fee(fee.amount) for fee in fees)
        special_fees_obj = [SpecialFee(name=fee.name, price=normalize_fee(fee.amount)) for fee in fees]

        if self.data.fee_type:
            fee_type = await fee_type_service.get_by_fee_auction(self.data.auction, self.data.fee_type)
        else:
            fee_type = await fee_type_service.get_by_fee_auction(self.data.auction, FeeTypeEnum.NON_CLEAN_TITLE_FEE)

        internet_fee = 0.0
        live_fee = 0.0

        auction_fee_obj = await fee_service.get_fee_in_car_price(fee_type, self.data.price)

        if auction_fee_obj.car_price_fee < 1:
            auction_fee = self.data.price * auction_fee_obj.car_price_fee
        else:
            auction_fee = auction_fee_obj.car_price_fee

        if self.data.auction == AuctionEnum.IAAI:
            internet_fee = await additional_fee_service.get_price_in_int_proxy(self.data.price)
            internet_fee = internet_fee.int_fee
        elif self.data.auction == AuctionEnum.COPART:
            live_fee = await additional_fee_service.get_price_in_live(self.data.price)
            live_fee = live_fee.live_bid_fee

        auction_fee = normalize_fee(auction_fee)
        internet_fee = normalize_fee(internet_fee)
        live_fee = normalize_fee(live_fee)
        addit_fees = all_fees_summ + auction_fee + internet_fee + live_fee
        special_fees_obj += [
            SpecialFee(name="Auction Fee", price=auction_fee),
            SpecialFee(name="Internet Fee", price=internet_fee),
            SpecialFee(name="Live Fee", price=live_fee),
        ]

        return AdditionalFeesOut(
            summ=addit_fees,
            fees=special_fees_obj,
            auction_fee=auction_fee,
            internet_fee=internet_fee,
            live_fee=live_fee,
        )

    @staticmethod
    def sync_terminals(delivery_cities: list[City], shipping_terminals: list[City]):
        """Keep only terminals that exist in both delivery and shipping lists."""

        delivery_names = {city.name for city in delivery_cities}
        shipping_names = {terminal.name for terminal in shipping_terminals}

        common_names = delivery_names & shipping_names

        filtered_delivery = [city for city in delivery_cities if city.name in common_names]
        filtered_shipping = [terminal for terminal in shipping_terminals if terminal.name in common_names]

        return filtered_delivery, filtered_shipping

    @staticmethod
    def _compute_is_monument(year: int | None) -> bool:
        """Return True when the vehicle qualifies as a monument (30+ years)."""

        return compute_is_monument(year)

    def _calculate_base_import_value(
        self,
        delivery_price: float,
        shipping_price: float,
        additional_sum: float,
    ) -> float:
        """Calculate base import value before duty and VAT."""

        return round(
            self.BROKER_FEE + shipping_price + delivery_price + additional_sum + self.data.price,
            2,
        )

    def _calculate_duty(self, base_sum: float) -> float:
        """Calculate duty for the base amount, with monument exemption."""

        if self.is_monument:
            return 0.0
        duty_rate = get_duty_rate(self.duty_category)
        return round(base_sum * duty_rate, 2)

    def _get_applied_duty_rate(self) -> float:
        """Return effective duty rate after monument override."""

        if self.is_monument:
            return 0.0
        return get_duty_rate(self.duty_category)

    def _calculate_vat(self, base_sum: float, duty: float) -> float:
        """Calculate VAT from base plus duty using configured VAT rules."""

        vat_rate = get_vat_rate(
            is_monument=self.is_monument,
            purchase_for_company=self.data.purchase_for_company,
        )
        return round((base_sum + duty) * vat_rate, 2)

    @staticmethod
    def _calculate_eu_total(base_sum: float, duty: float, vat: float, custom_agency: float) -> float:
        """Calculate final EU total amount."""

        return round(base_sum + duty + vat + custom_agency, 2)

    def _get_pricing_vehicle_type(self) -> VehicleTypeEnum:
        """Map business vehicle type to pricing type used by shipping/delivery tables."""

        return to_pricing_vehicle_type(self.data.vehicle_type)

    @staticmethod
    def _build_default_calculator(
        delivery_cities: list[City],
        shipping_terminals: list[City],
        additional_fees: AdditionalFeesOut,
        totals: list[City],
    ) -> DefaultCalculator:
        """Build default calculator output section."""

        return DefaultCalculator(
            broker_fee=CalculatorService.BROKER_FEE,
            transportation_price=delivery_cities,
            ocean_ship=shipping_terminals,
            additional=additional_fees,
            auction_fee=additional_fees.auction_fee,
            live_fee=additional_fees.live_fee,
            internet_fee=additional_fees.internet_fee,
            totals=totals,
        )

    def _build_eu_calculator(
        self,
        delivery_cities: list[City],
        shipping_terminals: list[City],
        additional_fees: AdditionalFeesOut,
        taxes_obj: Taxes,
        custom_agency: float,
        total_eu: list[City],
        total_without_default: list[City],
    ) -> EUCalculator:
        """Build EU calculator output section with applied tax flags."""

        return EUCalculator(
            broker_fee=self.BROKER_FEE,
            transportation_price=delivery_cities,
            ocean_ship=shipping_terminals,
            additional=additional_fees,
            taxes=taxes_obj,
            custom_agency=custom_agency,
            totals=total_eu,
            totals_without_default=total_without_default,
            tax_flags=TaxFlags(
                is_monument=self.is_monument,
                purchase_for_company=self.data.purchase_for_company,
                duty_category=self.duty_category.value,
                duty_rate=self._get_applied_duty_rate(),
                vat_rate=get_vat_rate(
                    is_monument=self.is_monument,
                    purchase_for_company=self.data.purchase_for_company,
                ),
            ),
        )

    @log_async_execution_time("Calculator into currency ")
    async def calculate_in_currency(self, calculator: CalculatorOut, currency: str) -> CalculatorOut:
        """Convert calculator values from USD to EUR."""

        usd_currency_rate = self.currency_converter.convert(1, "USD", currency)
        rate_to_usd = 1.0 if currency == "USD" else self.currency_converter.convert(1, currency, "USD")

        def usd_to_currency(usd: float) -> float:
            return round(usd * usd_currency_rate, 2)

        def city_to_currency(cities: list[City]) -> list[City]:
            return [City(name=city.name, price=usd_to_currency(city.price)) for city in cities]

        def additional_fee_to_currency(additional_fees: AdditionalFeesOut) -> AdditionalFeesOut:
            special_fees = [
                SpecialFee(name=special_fee.name, price=usd_to_currency(special_fee.price))
                for special_fee in additional_fees.fees
            ]
            return AdditionalFeesOut(
                summ=usd_to_currency(additional_fees.summ),
                fees=special_fees,
                auction_fee=usd_to_currency(additional_fees.auction_fee),
                internet_fee=usd_to_currency(additional_fees.internet_fee),
                live_fee=usd_to_currency(additional_fees.live_fee),
            )

        default_calculator = DefaultCalculator(
            broker_fee=usd_to_currency(calculator.calculator.broker_fee),
            transportation_price=city_to_currency(calculator.calculator.transportation_price),
            ocean_ship=city_to_currency(calculator.calculator.ocean_ship),
            additional=additional_fee_to_currency(calculator.calculator.additional),
            totals=city_to_currency(calculator.calculator.totals),
            auction_fee=usd_to_currency(calculator.calculator.auction_fee),
            live_fee=usd_to_currency(calculator.calculator.live_fee),
            internet_fee=usd_to_currency(calculator.calculator.internet_fee),
        )
        eu_calculator = EUCalculator(
            broker_fee=usd_to_currency(calculator.eu_calculator.broker_fee),
            transportation_price=city_to_currency(calculator.eu_calculator.transportation_price),
            ocean_ship=city_to_currency(calculator.eu_calculator.ocean_ship),
            additional=additional_fee_to_currency(calculator.eu_calculator.additional),
            totals=city_to_currency(calculator.eu_calculator.totals),
            taxes=Taxes(
                vats=city_to_currency(calculator.eu_calculator.taxes.vats),
                duties=city_to_currency(calculator.eu_calculator.taxes.duties),
            ),
            totals_without_default=city_to_currency(calculator.eu_calculator.totals_without_default),
            custom_agency=usd_to_currency(calculator.eu_calculator.custom_agency),
            tax_flags=calculator.eu_calculator.tax_flags,
        )
        return CalculatorOut(
            currency=currency,
            rate_to_usd=round(rate_to_usd, 6),
            calculator=default_calculator,
            eu_calculator=eu_calculator,
        )

    @log_async_execution_time("Calculations")
    async def calculate(self) -> Calculator:
        """Run full calculator flow and return USD/EUR outputs."""

        vehicle_type_service = VehicleTypeService(self.db)
        location_service = LocationService(self.db)
        destination_service = DestinationService(self.db)
        shipping_price_service = ShippingPriceService(self.db)
        delivery_price_service = DeliveryPriceService(self.db)
        pricing_vehicle_type = self._get_pricing_vehicle_type()

        vehicle_type_obj = await vehicle_type_service.get_by_auction_and_type(
            auction=self.data.auction,
            vehicle_type=pricing_vehicle_type,
        )
        if not vehicle_type_obj:
            logger.warning(
                f"Vehicle type {pricing_vehicle_type} not found",
                extra={"vehicle_type": pricing_vehicle_type},
            )
            raise VehicleTypeNotFoundError()
        logger.debug(
            "Vehicle type found",
            extra={
                "vehicle_type": vehicle_type_obj.vehicle_type,
                "id": vehicle_type_obj.id,
                "vehicle_type_auction": vehicle_type_obj.auction,
            },
        )

        if self.data.destination is None:
            destination = await destination_service.get_default()
        else:
            destination = await destination_service.get_by_name(name=self.data.destination)
            if not destination:
                logger.warning(
                    f"Destination {self.data.destination} not found",
                    extra={"destination": self.data.destination},
                )
                raise DestinationNotFoundError(f"Destination {self.data.destination} not found")

        additional_fees = await self.additional_fees_calculator()
        logger.debug(
            f"Additional fees calculated, summ: {additional_fees.summ}",
            extra={"additional_fees": additional_fees.model_dump()},
        )

        delivery_location_obj = await location_service.find_location(self.data.location, vehicle_type_obj)
        if not delivery_location_obj:
            logger.warning(f"Location {self.data.location} not found", extra={"location": self.data.location})
            raise LocationNotFoundError(f"Location {self.data.location} not found")

        delivery_prices = await delivery_price_service.get_by_terminal_location_vehicle_type(
            location=delivery_location_obj,
            vehicle_type=vehicle_type_obj,
        )

        if not delivery_prices:
            logger.warning(
                f"Delivery prices not found for location {delivery_location_obj.name} and vehicle type {vehicle_type_obj.vehicle_type}",
                extra={"location": delivery_location_obj.name, "vehicle_type": vehicle_type_obj.vehicle_type},
            )
            raise DeliveryPriceNotFoundError(
                f"Delivery prices not found for location {delivery_location_obj.name} and vehicle type {vehicle_type_obj.vehicle_type}"
            )

        logger.debug("Delivery prices found", extra={"delivery_prices_ids": [price.id for price in delivery_prices]})

        # Collect terminals from delivery prices
        terminals = [dp.terminal for dp in delivery_prices]

        # Collect all available destinations for these terminals
        available_destinations = set()
        for terminal in terminals:
            terminal_shipping_prices = await shipping_price_service.get_by_terminal_and_vehicle_type(
                terminal=terminal,
                vehicle_type=vehicle_type_obj,
            )
            for sp in terminal_shipping_prices:
                available_destinations.add(sp.destination.name)  # Assuming destination has a 'name' attribute

        # Convert to sorted list for consistency
        destinations_list = sorted(list(available_destinations))
        logger.debug(f"Available destinations found: {destinations_list}", extra={"count": len(destinations_list)})

        shipping_prices = await shipping_price_service.get_by_destination_and_vehicle_type(
            destination,
            vehicle_type_obj,
        )

        if not shipping_prices:
            logger.warning(
                f"Shipping prices not found for destination {destination.name} and vehicle type {vehicle_type_obj.vehicle_type}",
                extra={"destination": destination.name, "vehicle_type": vehicle_type_obj.vehicle_type},
            )
            raise ShippingPriceNotFoundError(
                f"Shipping prices not found for destination {destination.name} and vehicle type {vehicle_type_obj.vehicle_type}"
            )

        logger.debug("Shipping prices found", extra={"shipping_prices_ids": [price.id for price in shipping_prices]})

        delivery_cities = []
        for delivery_price in delivery_prices:
            if delivery_price.price > 0:
                delivery_cities.append(City(name=delivery_price.terminal.name, price=delivery_price.price))

        shipping_terminals = [
            City(name=shipping_price.terminal.name, price=shipping_price.price) for shipping_price in shipping_prices
        ]

        delivery_cities, shipping_terminals = self.sync_terminals(delivery_cities, shipping_terminals)

        rate = CurrencyConverter().convert(1, "USD", "EUR")
        logger.debug("Exchange rate found", extra={"rate": rate})

        custom_agency = round(540 / rate, 2)

        logger.debug(f"Custom agency = {custom_agency}")

        total_default: list[City] = []
        for delivery, shipping in zip(delivery_cities, shipping_terminals, strict=False):
            base_sum = self._calculate_base_import_value(
                delivery_price=delivery.price,
                shipping_price=shipping.price,
                additional_sum=additional_fees.summ,
            )
            total_default.append(City(name=delivery.name, price=base_sum))

        calculator = self._build_default_calculator(
            delivery_cities=delivery_cities,
            shipping_terminals=shipping_terminals,
            additional_fees=additional_fees,
            totals=total_default,
        )

        # ЕС калькулятор (в долларах)
        duties_list: list[City] = []
        vats_list: list[City] = []
        total_eu: list[City] = []
        total_without_default: list[City] = []

        for delivery, shipping in zip(delivery_cities, shipping_terminals, strict=False):
            base_sum = self._calculate_base_import_value(
                delivery_price=delivery.price,
                shipping_price=shipping.price,
                additional_sum=additional_fees.summ,
            )
            duty = self._calculate_duty(base_sum)
            duties_list.append(City(name=delivery.name, price=duty))

            vat = self._calculate_vat(base_sum, duty)
            vats_list.append(City(name=delivery.name, price=vat))

            total_price_eu = self._calculate_eu_total(
                base_sum=base_sum,
                duty=duty,
                vat=vat,
                custom_agency=custom_agency,
            )
            total_eu.append(City(name=delivery.name, price=total_price_eu))
            total_without_default.append(City(name=delivery.name, price=round(total_price_eu - base_sum, 2)))

        taxes_obj = Taxes(
            duties=duties_list,
            vats=vats_list,
        )

        eu_calculator = self._build_eu_calculator(
            delivery_cities=delivery_cities,
            shipping_terminals=shipping_terminals,
            additional_fees=additional_fees,
            taxes_obj=taxes_obj,
            custom_agency=round(custom_agency, 2),
            total_eu=total_eu,
            total_without_default=total_without_default,
        )

        calculator_out = CalculatorOut(
            currency="USD",
            rate_to_usd=1.0,
            calculator=calculator,
            eu_calculator=eu_calculator,
        )

        return Calculator(
            calculator_in_dollars=calculator_out,
            calculators_in_currencies=[
                await self.calculate_in_currency(calculator_out, "EUR"),
                await self.calculate_in_currency(calculator_out, "PLN"),
            ],
            destinations=destinations_list,
            rate=rate,
        )


if __name__ == "__main__":

    async def main():
        db = AsyncSessionLocal()

        location = "Abilene"
        user_price = 1000
        auction = AuctionEnum.IAAI
        vehicle_type = CalculatorVehicleTypeEnum.AUTOMOBILE

        calculator = CalculatorService(db, user_price, auction, location, vehicle_type)
        data = await calculator.calculate()

        def print_data(calculator):
            print(
                f"INPUTS:\n"
                f"vehicle price: {user_price}\n"
                f"auction: {auction.value}\n"
                f"vehicle type: {vehicle_type.value}\n"
                f"location: {location}\n"
                f"\n\n"
                f"CALCULATOR:\n"
                f"VEHICLE_PRICE: {user_price}\n"
                f"+\n"
                f"BROKER_FEE: ${calculator.broker_fee}\n"
                f"+\n"
                f"TRANSPORTATION PRICE (from auction to terminal: {calculator.transportation_price[0].name}): ${calculator.transportation_price[0].price}\n"
                f"+\n"
                f"OCEAN SHIP (from terminal in usa to Klaipeda): ${calculator.ocean_ship[0].price}\n"
                f"+\n"
                f"ADDITIONAL FEES (include {', '.join([f'{special_fee.name}: {special_fee.price}' for special_fee in calculator.additional.fees])}): ${calculator.additional.summ}\n"
                f"=\n"
                f"TOTAL: ${calculator.totals[0].price}\n"
            )

        print_data(data.calculator_in_currency.eu_calculator)

        await db.close()

    asyncio.run(main())
