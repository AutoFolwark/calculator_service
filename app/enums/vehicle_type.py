from enum import Enum


class VehicleTypeEnum(str, Enum):
    CAR = "CAR"
    MOTO = "MOTO"


class CalculatorVehicleTypeEnum(str, Enum):
    AUTOMOBILE = "Automobile"
    BOAT = "Boat"
    MOBILE_HOME = "Mobile Home"
    TRUCK = "Truck"
    BUS = "Bus"
    TRAILERS = "Trailers"
    MOTORCYCLE = "Motorcycle"
    OTHER = "Other"


def to_pricing_vehicle_type(vehicle_type: CalculatorVehicleTypeEnum) -> VehicleTypeEnum:
    if vehicle_type == CalculatorVehicleTypeEnum.MOTORCYCLE:
        return VehicleTypeEnum.MOTO
    return VehicleTypeEnum.CAR


def parse_calculator_vehicle_type(raw_value: str | None) -> CalculatorVehicleTypeEnum:
    if not raw_value:
        return CalculatorVehicleTypeEnum.OTHER

    normalized = raw_value.strip().lower()

    direct_map = {
        "automobile": CalculatorVehicleTypeEnum.AUTOMOBILE,
        "boat": CalculatorVehicleTypeEnum.BOAT,
        "mobile home": CalculatorVehicleTypeEnum.MOBILE_HOME,
        "truck": CalculatorVehicleTypeEnum.TRUCK,
        "bus": CalculatorVehicleTypeEnum.BUS,
        "trailers": CalculatorVehicleTypeEnum.TRAILERS,
        "motorcycle": CalculatorVehicleTypeEnum.MOTORCYCLE,
        "other": CalculatorVehicleTypeEnum.OTHER,
        # legacy values still accepted by RPC callers
        "car": CalculatorVehicleTypeEnum.AUTOMOBILE,
        "moto": CalculatorVehicleTypeEnum.MOTORCYCLE,
    }
    if normalized in direct_map:
        return direct_map[normalized]

    if any(token in normalized for token in ("motorcycle", "moto", "bike")):
        return CalculatorVehicleTypeEnum.MOTORCYCLE
    if "boat" in normalized:
        return CalculatorVehicleTypeEnum.BOAT
    if "mobile home" in normalized:
        return CalculatorVehicleTypeEnum.MOBILE_HOME
    if "trailer" in normalized:
        return CalculatorVehicleTypeEnum.TRAILERS
    if "bus" in normalized:
        return CalculatorVehicleTypeEnum.BUS
    if "truck" in normalized:
        return CalculatorVehicleTypeEnum.TRUCK
    if "auto" in normalized or "car" in normalized:
        return CalculatorVehicleTypeEnum.AUTOMOBILE

    return CalculatorVehicleTypeEnum.OTHER
