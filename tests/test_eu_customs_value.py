import pytest
from pydantic import ValidationError

from app.enums.auction import AuctionEnum
from app.enums.vehicle_type import CalculatorVehicleTypeEnum
from app.schemas.calculator import CalculatorDataIn, CalculatorWithoutDetailsIn
from app.services.calculator.calculator_service import CalculatorService

DELIVERY = 375.0
SHIPPING = 995.0
ADDITIONAL = 800.0
AGENCY = 100.0
BASE_INPUTS = {
    "price": 5000,
    "auction": AuctionEnum.COPART,
    "location": "TX - Houston",
    "vehicle_type": CalculatorVehicleTypeEnum.AUTOMOBILE,
}


def _service(**overrides) -> CalculatorService:
    params = {"year": 2018, **BASE_INPUTS, **overrides}
    return CalculatorService(db=None, **params)


def _base_sum(service: CalculatorService) -> float:
    return service._calculate_base_import_value(
        delivery_price=DELIVERY,
        shipping_price=SHIPPING,
        additional_sum=ADDITIONAL,
    )


def test_default_customs_value_matches_real_base() -> None:
    service = _service()
    base_sum = _base_sum(service)

    assert service.data.customs_value is None
    assert service._get_customs_value(base_sum) == base_sum

    duty = service._calculate_duty(base_sum)
    vat = service._calculate_vat(base_sum, duty)
    total = service._calculate_eu_total(base_sum=base_sum, duty=duty, vat=vat, custom_agency=AGENCY)

    assert duty == round(base_sum * 0.10, 2)
    assert vat == round((base_sum + duty) * 0.21, 2)
    assert total == round(base_sum + duty + vat + AGENCY, 2)


def test_customs_value_override_uses_real_base_for_total() -> None:
    customs_value = 4000.0
    service = _service(customs_value=customs_value)
    base_sum = _base_sum(service)

    assert service._get_customs_value(base_sum) == customs_value
    assert base_sum != customs_value

    duty = service._calculate_duty(customs_value)
    vat = service._calculate_vat(customs_value, duty)
    total = service._calculate_eu_total(base_sum=base_sum, duty=duty, vat=vat, custom_agency=AGENCY)

    assert duty == 400.0
    assert vat == round((customs_value + duty) * 0.21, 2)
    assert total == round(base_sum + duty + vat + AGENCY, 2)
    assert total != round(customs_value + duty + vat + AGENCY, 2)


def test_monument_and_company_paths_with_customs_value() -> None:
    customs_value = 4000.0

    monument = _service(year=1990, customs_value=customs_value)
    assert monument.is_monument
    monument_duty = monument._calculate_duty(customs_value)
    monument_vat = monument._calculate_vat(customs_value, monument_duty)
    assert monument_duty == 0.0
    assert monument_vat == round(customs_value * 0.08, 2)

    company = _service(purchase_for_company=True, customs_value=customs_value)
    company_duty = company._calculate_duty(customs_value)
    company_vat = company._calculate_vat(customs_value, company_duty)
    assert company_duty == 400.0
    assert company_vat == 0.0


@pytest.mark.parametrize("customs_value", [0, -1])
def test_customs_value_must_be_positive(customs_value: int) -> None:
    with pytest.raises(ValidationError):
        CalculatorDataIn(**BASE_INPUTS, customs_value=customs_value)
    with pytest.raises(ValidationError):
        CalculatorWithoutDetailsIn(price=5000, customs_value=customs_value)


def test_customs_value_defaults_to_none() -> None:
    data = CalculatorDataIn(**BASE_INPUTS)
    without_details = CalculatorWithoutDetailsIn(price=5000)
    assert data.customs_value is None
    assert without_details.customs_value is None
