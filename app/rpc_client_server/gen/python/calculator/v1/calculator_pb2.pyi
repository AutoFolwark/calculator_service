from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GetRatesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetRatesResponse(_message.Message):
    __slots__ = ("rate",)
    RATE_FIELD_NUMBER: _ClassVar[int]
    rate: float
    def __init__(self, rate: _Optional[float] = ...) -> None: ...

class GetDetailedFeeTypeRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class GetDetailedFeeTypeResponse(_message.Message):
    __slots__ = ("auction", "fee_type")
    AUCTION_FIELD_NUMBER: _ClassVar[int]
    FEE_TYPE_FIELD_NUMBER: _ClassVar[int]
    auction: str
    fee_type: str
    def __init__(self, auction: _Optional[str] = ..., fee_type: _Optional[str] = ...) -> None: ...

class GetDetailedLocationRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class GetDetailedLocationResponse(_message.Message):
    __slots__ = ("name", "city", "state", "postal_code", "email")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CITY_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    POSTAL_CODE_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    name: str
    city: str
    state: str
    postal_code: str
    email: str
    def __init__(self, name: _Optional[str] = ..., city: _Optional[str] = ..., state: _Optional[str] = ..., postal_code: _Optional[str] = ..., email: _Optional[str] = ...) -> None: ...

class GetDetailedTerminalRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class GetDetailedTerminalResponse(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class GetDetailedDestinationRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class GetDetailedDestinationResponse(_message.Message):
    __slots__ = ("name", "is_default")
    NAME_FIELD_NUMBER: _ClassVar[int]
    IS_DEFAULT_FIELD_NUMBER: _ClassVar[int]
    name: str
    is_default: bool
    def __init__(self, name: _Optional[str] = ..., is_default: bool = ...) -> None: ...

class GetCalculatorWithDataRequest(_message.Message):
    __slots__ = ("price", "auction", "fee_type", "vehicle_type", "destination", "location", "year", "purchase_for_company")
    PRICE_FIELD_NUMBER: _ClassVar[int]
    AUCTION_FIELD_NUMBER: _ClassVar[int]
    FEE_TYPE_FIELD_NUMBER: _ClassVar[int]
    VEHICLE_TYPE_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    YEAR_FIELD_NUMBER: _ClassVar[int]
    PURCHASE_FOR_COMPANY_FIELD_NUMBER: _ClassVar[int]
    price: int
    auction: str
    fee_type: str
    vehicle_type: str
    destination: str
    location: str
    year: int
    purchase_for_company: bool
    def __init__(self, price: _Optional[int] = ..., auction: _Optional[str] = ..., fee_type: _Optional[str] = ..., vehicle_type: _Optional[str] = ..., destination: _Optional[str] = ..., location: _Optional[str] = ..., year: _Optional[int] = ..., purchase_for_company: bool = ...) -> None: ...

class GetCalculatorWithIdsRequest(_message.Message):
    __slots__ = ("price", "auction", "fee_type_id", "vehicle_type", "destination_id", "location_id", "year", "purchase_for_company")
    PRICE_FIELD_NUMBER: _ClassVar[int]
    AUCTION_FIELD_NUMBER: _ClassVar[int]
    FEE_TYPE_ID_FIELD_NUMBER: _ClassVar[int]
    VEHICLE_TYPE_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_ID_FIELD_NUMBER: _ClassVar[int]
    LOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    YEAR_FIELD_NUMBER: _ClassVar[int]
    PURCHASE_FOR_COMPANY_FIELD_NUMBER: _ClassVar[int]
    price: int
    auction: str
    fee_type_id: int
    vehicle_type: str
    destination_id: int
    location_id: int
    year: int
    purchase_for_company: bool
    def __init__(self, price: _Optional[int] = ..., auction: _Optional[str] = ..., fee_type_id: _Optional[int] = ..., vehicle_type: _Optional[str] = ..., destination_id: _Optional[int] = ..., location_id: _Optional[int] = ..., year: _Optional[int] = ..., purchase_for_company: bool = ...) -> None: ...

class GetCalculatorBatchRequest(_message.Message):
    __slots__ = ("data", "lot_id")
    DATA_FIELD_NUMBER: _ClassVar[int]
    LOT_ID_FIELD_NUMBER: _ClassVar[int]
    data: GetCalculatorWithDataRequest
    lot_id: str
    def __init__(self, data: _Optional[_Union[GetCalculatorWithDataRequest, _Mapping]] = ..., lot_id: _Optional[str] = ...) -> None: ...

class GetCalculatorWithDataBatchRequest(_message.Message):
    __slots__ = ("data",)
    DATA_FIELD_NUMBER: _ClassVar[int]
    data: _containers.RepeatedCompositeFieldContainer[GetCalculatorBatchRequest]
    def __init__(self, data: _Optional[_Iterable[_Union[GetCalculatorBatchRequest, _Mapping]]] = ...) -> None: ...

class GetCalculatorWithoutDataRequest(_message.Message):
    __slots__ = ("price", "auction", "lot_id", "destination", "purchase_for_company", "year")
    PRICE_FIELD_NUMBER: _ClassVar[int]
    AUCTION_FIELD_NUMBER: _ClassVar[int]
    LOT_ID_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_FIELD_NUMBER: _ClassVar[int]
    PURCHASE_FOR_COMPANY_FIELD_NUMBER: _ClassVar[int]
    YEAR_FIELD_NUMBER: _ClassVar[int]
    price: int
    auction: str
    lot_id: str
    destination: str
    purchase_for_company: bool
    year: int
    def __init__(self, price: _Optional[int] = ..., auction: _Optional[str] = ..., lot_id: _Optional[str] = ..., destination: _Optional[str] = ..., purchase_for_company: bool = ..., year: _Optional[int] = ...) -> None: ...

class GetCalculatorWithDataResponse(_message.Message):
    __slots__ = ("data", "detailed_data", "message", "success")
    DATA_FIELD_NUMBER: _ClassVar[int]
    DETAILED_DATA_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    data: Calculator
    detailed_data: DetailedCalculatorData
    message: str
    success: bool
    def __init__(self, data: _Optional[_Union[Calculator, _Mapping]] = ..., detailed_data: _Optional[_Union[DetailedCalculatorData, _Mapping]] = ..., message: _Optional[str] = ..., success: bool = ...) -> None: ...

class Terminal(_message.Message):
    __slots__ = ("terminal_id", "terminal_name")
    TERMINAL_ID_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_NAME_FIELD_NUMBER: _ClassVar[int]
    terminal_id: int
    terminal_name: str
    def __init__(self, terminal_id: _Optional[int] = ..., terminal_name: _Optional[str] = ...) -> None: ...

class Destination(_message.Message):
    __slots__ = ("destination_id", "destination_name")
    DESTINATION_ID_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_NAME_FIELD_NUMBER: _ClassVar[int]
    destination_id: int
    destination_name: str
    def __init__(self, destination_id: _Optional[int] = ..., destination_name: _Optional[str] = ...) -> None: ...

class DetailedCalculatorData(_message.Message):
    __slots__ = ("location_id", "location_data", "terminals", "fee_type_id", "fee_type_data", "available_destinations")
    LOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    LOCATION_DATA_FIELD_NUMBER: _ClassVar[int]
    TERMINALS_FIELD_NUMBER: _ClassVar[int]
    FEE_TYPE_ID_FIELD_NUMBER: _ClassVar[int]
    FEE_TYPE_DATA_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_DESTINATIONS_FIELD_NUMBER: _ClassVar[int]
    location_id: int
    location_data: Location
    terminals: _containers.RepeatedCompositeFieldContainer[Terminal]
    fee_type_id: int
    fee_type_data: FeeType
    available_destinations: _containers.RepeatedCompositeFieldContainer[Destination]
    def __init__(self, location_id: _Optional[int] = ..., location_data: _Optional[_Union[Location, _Mapping]] = ..., terminals: _Optional[_Iterable[_Union[Terminal, _Mapping]]] = ..., fee_type_id: _Optional[int] = ..., fee_type_data: _Optional[_Union[FeeType, _Mapping]] = ..., available_destinations: _Optional[_Iterable[_Union[Destination, _Mapping]]] = ...) -> None: ...

class GetCalculatorWithIdsResponse(_message.Message):
    __slots__ = ("calculator", "location", "terminal_name", "destination_name", "fee_type")
    CALCULATOR_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    TERMINAL_NAME_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_NAME_FIELD_NUMBER: _ClassVar[int]
    FEE_TYPE_FIELD_NUMBER: _ClassVar[int]
    calculator: Calculator
    location: Location
    terminal_name: str
    destination_name: str
    fee_type: FeeType
    def __init__(self, calculator: _Optional[_Union[Calculator, _Mapping]] = ..., location: _Optional[_Union[Location, _Mapping]] = ..., terminal_name: _Optional[str] = ..., destination_name: _Optional[str] = ..., fee_type: _Optional[_Union[FeeType, _Mapping]] = ...) -> None: ...

class Location(_message.Message):
    __slots__ = ("name", "city", "state", "postal_code", "email")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CITY_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    POSTAL_CODE_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    name: str
    city: str
    state: str
    postal_code: str
    email: str
    def __init__(self, name: _Optional[str] = ..., city: _Optional[str] = ..., state: _Optional[str] = ..., postal_code: _Optional[str] = ..., email: _Optional[str] = ...) -> None: ...

class FeeType(_message.Message):
    __slots__ = ("auction", "fee_type")
    AUCTION_FIELD_NUMBER: _ClassVar[int]
    FEE_TYPE_FIELD_NUMBER: _ClassVar[int]
    auction: str
    fee_type: str
    def __init__(self, auction: _Optional[str] = ..., fee_type: _Optional[str] = ...) -> None: ...

class GetCalculatorWithoutDataResponse(_message.Message):
    __slots__ = ("data", "detailed_data", "message", "success")
    DATA_FIELD_NUMBER: _ClassVar[int]
    DETAILED_DATA_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    data: Calculator
    detailed_data: DetailedCalculatorData
    message: str
    success: bool
    def __init__(self, data: _Optional[_Union[Calculator, _Mapping]] = ..., detailed_data: _Optional[_Union[DetailedCalculatorData, _Mapping]] = ..., message: _Optional[str] = ..., success: bool = ...) -> None: ...

class CalculatorBatchItem(_message.Message):
    __slots__ = ("calculator", "lot_id")
    CALCULATOR_FIELD_NUMBER: _ClassVar[int]
    LOT_ID_FIELD_NUMBER: _ClassVar[int]
    calculator: Calculator
    lot_id: str
    def __init__(self, calculator: _Optional[_Union[Calculator, _Mapping]] = ..., lot_id: _Optional[str] = ...) -> None: ...

class GetCalculatorWithDataBatchResponse(_message.Message):
    __slots__ = ("data", "message", "success")
    DATA_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    data: _containers.RepeatedCompositeFieldContainer[CalculatorBatchItem]
    message: str
    success: bool
    def __init__(self, data: _Optional[_Iterable[_Union[CalculatorBatchItem, _Mapping]]] = ..., message: _Optional[str] = ..., success: bool = ...) -> None: ...

class City(_message.Message):
    __slots__ = ("name", "price")
    NAME_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    name: str
    price: float
    def __init__(self, name: _Optional[str] = ..., price: _Optional[float] = ...) -> None: ...

class Taxes(_message.Message):
    __slots__ = ("vats", "duties")
    VATS_FIELD_NUMBER: _ClassVar[int]
    DUTIES_FIELD_NUMBER: _ClassVar[int]
    vats: _containers.RepeatedCompositeFieldContainer[City]
    duties: _containers.RepeatedCompositeFieldContainer[City]
    def __init__(self, vats: _Optional[_Iterable[_Union[City, _Mapping]]] = ..., duties: _Optional[_Iterable[_Union[City, _Mapping]]] = ...) -> None: ...

class TaxFlags(_message.Message):
    __slots__ = ("is_monument", "purchase_for_company", "duty_category", "duty_rate", "vat_rate")
    IS_MONUMENT_FIELD_NUMBER: _ClassVar[int]
    PURCHASE_FOR_COMPANY_FIELD_NUMBER: _ClassVar[int]
    DUTY_CATEGORY_FIELD_NUMBER: _ClassVar[int]
    DUTY_RATE_FIELD_NUMBER: _ClassVar[int]
    VAT_RATE_FIELD_NUMBER: _ClassVar[int]
    is_monument: bool
    purchase_for_company: bool
    duty_category: str
    duty_rate: float
    vat_rate: float
    def __init__(self, is_monument: bool = ..., purchase_for_company: bool = ..., duty_category: _Optional[str] = ..., duty_rate: _Optional[float] = ..., vat_rate: _Optional[float] = ...) -> None: ...

class SpecialFee(_message.Message):
    __slots__ = ("price", "name")
    PRICE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    price: float
    name: str
    def __init__(self, price: _Optional[float] = ..., name: _Optional[str] = ...) -> None: ...

class AdditionalFeesOut(_message.Message):
    __slots__ = ("summ", "fees", "auction_fee", "internet_fee", "live_fee")
    SUMM_FIELD_NUMBER: _ClassVar[int]
    FEES_FIELD_NUMBER: _ClassVar[int]
    AUCTION_FEE_FIELD_NUMBER: _ClassVar[int]
    INTERNET_FEE_FIELD_NUMBER: _ClassVar[int]
    LIVE_FEE_FIELD_NUMBER: _ClassVar[int]
    summ: float
    fees: _containers.RepeatedCompositeFieldContainer[SpecialFee]
    auction_fee: float
    internet_fee: float
    live_fee: float
    def __init__(self, summ: _Optional[float] = ..., fees: _Optional[_Iterable[_Union[SpecialFee, _Mapping]]] = ..., auction_fee: _Optional[float] = ..., internet_fee: _Optional[float] = ..., live_fee: _Optional[float] = ...) -> None: ...

class BaseCalculator(_message.Message):
    __slots__ = ("broker_fee", "transportation_price", "ocean_ship", "additional", "totals")
    BROKER_FEE_FIELD_NUMBER: _ClassVar[int]
    TRANSPORTATION_PRICE_FIELD_NUMBER: _ClassVar[int]
    OCEAN_SHIP_FIELD_NUMBER: _ClassVar[int]
    ADDITIONAL_FIELD_NUMBER: _ClassVar[int]
    TOTALS_FIELD_NUMBER: _ClassVar[int]
    broker_fee: float
    transportation_price: _containers.RepeatedCompositeFieldContainer[City]
    ocean_ship: _containers.RepeatedCompositeFieldContainer[City]
    additional: AdditionalFeesOut
    totals: _containers.RepeatedCompositeFieldContainer[City]
    def __init__(self, broker_fee: _Optional[float] = ..., transportation_price: _Optional[_Iterable[_Union[City, _Mapping]]] = ..., ocean_ship: _Optional[_Iterable[_Union[City, _Mapping]]] = ..., additional: _Optional[_Union[AdditionalFeesOut, _Mapping]] = ..., totals: _Optional[_Iterable[_Union[City, _Mapping]]] = ...) -> None: ...

class DefaultCalculator(_message.Message):
    __slots__ = ("broker_fee", "transportation_price", "ocean_ship", "additional", "totals", "auction_fee", "live_fee", "internet_fee")
    BROKER_FEE_FIELD_NUMBER: _ClassVar[int]
    TRANSPORTATION_PRICE_FIELD_NUMBER: _ClassVar[int]
    OCEAN_SHIP_FIELD_NUMBER: _ClassVar[int]
    ADDITIONAL_FIELD_NUMBER: _ClassVar[int]
    TOTALS_FIELD_NUMBER: _ClassVar[int]
    AUCTION_FEE_FIELD_NUMBER: _ClassVar[int]
    LIVE_FEE_FIELD_NUMBER: _ClassVar[int]
    INTERNET_FEE_FIELD_NUMBER: _ClassVar[int]
    broker_fee: float
    transportation_price: _containers.RepeatedCompositeFieldContainer[City]
    ocean_ship: _containers.RepeatedCompositeFieldContainer[City]
    additional: AdditionalFeesOut
    totals: _containers.RepeatedCompositeFieldContainer[City]
    auction_fee: float
    live_fee: float
    internet_fee: float
    def __init__(self, broker_fee: _Optional[float] = ..., transportation_price: _Optional[_Iterable[_Union[City, _Mapping]]] = ..., ocean_ship: _Optional[_Iterable[_Union[City, _Mapping]]] = ..., additional: _Optional[_Union[AdditionalFeesOut, _Mapping]] = ..., totals: _Optional[_Iterable[_Union[City, _Mapping]]] = ..., auction_fee: _Optional[float] = ..., live_fee: _Optional[float] = ..., internet_fee: _Optional[float] = ...) -> None: ...

class EUCalculator(_message.Message):
    __slots__ = ("broker_fee", "transportation_price", "ocean_ship", "additional", "totals", "taxes", "custom_agency", "totals_without_default", "tax_flags")
    BROKER_FEE_FIELD_NUMBER: _ClassVar[int]
    TRANSPORTATION_PRICE_FIELD_NUMBER: _ClassVar[int]
    OCEAN_SHIP_FIELD_NUMBER: _ClassVar[int]
    ADDITIONAL_FIELD_NUMBER: _ClassVar[int]
    TOTALS_FIELD_NUMBER: _ClassVar[int]
    TAXES_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_AGENCY_FIELD_NUMBER: _ClassVar[int]
    TOTALS_WITHOUT_DEFAULT_FIELD_NUMBER: _ClassVar[int]
    TAX_FLAGS_FIELD_NUMBER: _ClassVar[int]
    broker_fee: float
    transportation_price: _containers.RepeatedCompositeFieldContainer[City]
    ocean_ship: _containers.RepeatedCompositeFieldContainer[City]
    additional: AdditionalFeesOut
    totals: _containers.RepeatedCompositeFieldContainer[City]
    taxes: Taxes
    custom_agency: float
    totals_without_default: _containers.RepeatedCompositeFieldContainer[City]
    tax_flags: TaxFlags
    def __init__(self, broker_fee: _Optional[float] = ..., transportation_price: _Optional[_Iterable[_Union[City, _Mapping]]] = ..., ocean_ship: _Optional[_Iterable[_Union[City, _Mapping]]] = ..., additional: _Optional[_Union[AdditionalFeesOut, _Mapping]] = ..., totals: _Optional[_Iterable[_Union[City, _Mapping]]] = ..., taxes: _Optional[_Union[Taxes, _Mapping]] = ..., custom_agency: _Optional[float] = ..., totals_without_default: _Optional[_Iterable[_Union[City, _Mapping]]] = ..., tax_flags: _Optional[_Union[TaxFlags, _Mapping]] = ...) -> None: ...

class CalculatorOut(_message.Message):
    __slots__ = ("calculator", "eu_calculator", "currency")
    CALCULATOR_FIELD_NUMBER: _ClassVar[int]
    EU_CALCULATOR_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_FIELD_NUMBER: _ClassVar[int]
    calculator: DefaultCalculator
    eu_calculator: EUCalculator
    currency: str
    def __init__(self, calculator: _Optional[_Union[DefaultCalculator, _Mapping]] = ..., eu_calculator: _Optional[_Union[EUCalculator, _Mapping]] = ..., currency: _Optional[str] = ...) -> None: ...

class Calculator(_message.Message):
    __slots__ = ("calculator_in_dollars", "calculators_in_currencies", "destinations", "rate")
    CALCULATOR_IN_DOLLARS_FIELD_NUMBER: _ClassVar[int]
    CALCULATORS_IN_CURRENCIES_FIELD_NUMBER: _ClassVar[int]
    DESTINATIONS_FIELD_NUMBER: _ClassVar[int]
    RATE_FIELD_NUMBER: _ClassVar[int]
    calculator_in_dollars: CalculatorOut
    calculators_in_currencies: _containers.RepeatedCompositeFieldContainer[CalculatorOut]
    destinations: _containers.RepeatedScalarFieldContainer[str]
    rate: float
    def __init__(self, calculator_in_dollars: _Optional[_Union[CalculatorOut, _Mapping]] = ..., calculators_in_currencies: _Optional[_Iterable[_Union[CalculatorOut, _Mapping]]] = ..., destinations: _Optional[_Iterable[str]] = ..., rate: _Optional[float] = ...) -> None: ...
