from fastapi import APIRouter

from app.api.api_v1.endpoints.public.calculator import calculator_api_router
from app.api.api_v1.endpoints.public.fee_type import fee_type_api_router
from app.api.api_v1.endpoints.public.location import location_api_router

public_v1_router = APIRouter(prefix="/v1/public")

public_v1_router.include_router(calculator_api_router)
public_v1_router.include_router(location_api_router)
public_v1_router.include_router(fee_type_api_router)
