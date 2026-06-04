from pydantic import BaseModel, Field, field_validator

from app.enums.auction import AuctionEnum
from app.enums.fee_type import FeeTypeEnum
from app.enums.vehicle_type import (
    CalculatorVehicleTypeEnum,
    parse_calculator_vehicle_type,
)


class CalculatorDataIn(BaseModel):
    price: int = Field(..., gt=0, description="Price for vehicle")
    auction: AuctionEnum = Field(..., description="Auction")
    fee_type: FeeTypeEnum | None = Field(description="Fee type", default=FeeTypeEnum.NON_CLEAN_TITLE_FEE)
    vehicle_type: CalculatorVehicleTypeEnum = Field(..., description="Vehicle type")
    destination: str | None = Field(None, description="Destination (Port in Europe)")
    location: str = Field(..., description="Location")

    # New BIDMAX specific fields
    year: int | None = Field(None, description="Year of the vehicle")
    purchase_for_company: bool = Field(False, description="Purchase for a company")

    @field_validator("vehicle_type", mode="before")
    @classmethod
    def normalize_vehicle_type(cls, value):
        if isinstance(value, CalculatorVehicleTypeEnum):
            return value
        if isinstance(value, str):
            return parse_calculator_vehicle_type(value)
        return value


class CalculatorWithoutDetailsIn(BaseModel):
    price: int = Field(..., gt=0, description="Price for vehicle")
    destination: str | None = Field(None, description="Destination (Port in Europe)")
    purchase_for_company: bool = Field(False, description="Purchase for a company")
