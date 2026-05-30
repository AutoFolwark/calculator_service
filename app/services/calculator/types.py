from pydantic import BaseModel


class City(BaseModel):
    name: str
    price: float


class Taxes(BaseModel):
    vats: list[City]
    duties: list[City]


class TaxFlags(BaseModel):
    is_monument: bool
    purchase_for_company: bool
    duty_category: str
    duty_rate: float
    vat_rate: float


class SpecialFee(BaseModel):
    price: float
    name: str


class AdditionalFeesOut(BaseModel):
    summ: float
    fees: list[SpecialFee]
    auction_fee: float
    internet_fee: float
    live_fee: float


class BaseCalculator(BaseModel):
    broker_fee: float
    transportation_price: list[City]
    ocean_ship: list[City]
    additional: AdditionalFeesOut
    totals: list[City]


class DefaultCalculator(BaseCalculator):
    auction_fee: float
    live_fee: float
    internet_fee: float


class EUCalculator(BaseCalculator):
    totals_without_default: list[City]
    taxes: Taxes
    custom_agency: float = 0.0
    tax_flags: TaxFlags | None = None


class CalculatorOut(BaseModel):
    currency: str
    calculator: DefaultCalculator
    eu_calculator: EUCalculator


class Calculator(BaseModel):
    calculator_in_dollars: CalculatorOut
    calculators_in_currencies: list[CalculatorOut]
    destinations: list[str]
    rate: float
