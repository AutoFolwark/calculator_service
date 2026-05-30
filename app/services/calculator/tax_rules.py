from datetime import datetime
from enum import Enum

from app.enums.vehicle_type import CalculatorVehicleTypeEnum


class DutyCategory(str, Enum):
    DEFAULT_CAR = "default_car"
    CLASSIC_CAR = "classic_car"
    MOTORCYCLE = "motorcycle"
    TRUCK = "truck"
    SCOOTER_BOAT = "scooter_boat"


def compute_is_monument(year: int | None) -> bool:
    if year is None:
        return False
    current_year = datetime.now().year
    return current_year - year >= 30


def infer_duty_category(
    vehicle_type: CalculatorVehicleTypeEnum,
) -> DutyCategory:
    if vehicle_type == CalculatorVehicleTypeEnum.BOAT:
        return DutyCategory.SCOOTER_BOAT

    if vehicle_type in {
        CalculatorVehicleTypeEnum.TRUCK,
        CalculatorVehicleTypeEnum.BUS,
        CalculatorVehicleTypeEnum.TRAILERS,
    }:
        return DutyCategory.TRUCK

    if vehicle_type == CalculatorVehicleTypeEnum.MOTORCYCLE:
        return DutyCategory.MOTORCYCLE

    return DutyCategory.DEFAULT_CAR


def get_duty_rate(category: DutyCategory) -> float:
    return {
        DutyCategory.DEFAULT_CAR: 0.10,
        DutyCategory.CLASSIC_CAR: 0.00,
        DutyCategory.MOTORCYCLE: 0.06,
        DutyCategory.TRUCK: 0.22,
        DutyCategory.SCOOTER_BOAT: 0.017,
    }[category]


def get_vat_rate(is_monument: bool, purchase_for_company: bool) -> float:
    if is_monument:
        return 0.08
    if purchase_for_company:
        return 0.0
    return 0.21
