import re

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base import BaseService
from app.database.models import DeliveryPrice, Location, VehicleType
from app.database.schemas.location import LocationCreate, LocationUpdate
from app.enums.auction import AuctionEnum
from app.services.location_search import (
    MATCH_THRESHOLD,
    ParsedLocation,
    apply_parsed_overrides,
    parse_location_name,
    score_match,
)


class LocationService(BaseService[Location, LocationCreate, LocationUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(Location, session)

    def _vehicle_type_filter(self, vehicle_type: VehicleType):
        return DeliveryPrice.vehicle_type_id == vehicle_type.id

    async def _find_with_condition(self, condition, vehicle_type: VehicleType) -> Location | None:
        result = await self.session.execute(
            select(Location)
            .join(DeliveryPrice)
            .where(and_(condition, self._vehicle_type_filter(vehicle_type)))
            .distinct()
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _search_by_canonical_names(self, parsed: ParsedLocation, vehicle_type: VehicleType) -> Location | None:
        for canonical_name in parsed.canonical_names:
            location = await self._find_with_condition(Location.name.ilike(canonical_name), vehicle_type)
            if location:
                return location
        return None

    async def _search_by_city_state(self, parsed: ParsedLocation, vehicle_type: VehicleType) -> Location | None:
        if not parsed.city or not parsed.state:
            return None

        conditions = [
            and_(Location.city.ilike(parsed.city), Location.state.ilike(parsed.state)),
            and_(Location.name.ilike(f"%{parsed.city}%"), Location.state.ilike(parsed.state)),
        ]
        for condition in conditions:
            location = await self._find_with_condition(condition, vehicle_type)
            if location:
                return location
        return None

    async def _search_by_token_score(self, parsed: ParsedLocation, vehicle_type: VehicleType) -> Location | None:
        if not parsed.core_tokens:
            return None

        longest_token = max(parsed.core_tokens, key=len)
        filters = [
            or_(
                Location.city.ilike(f"%{longest_token}%"),
                Location.name.ilike(f"%{longest_token}%"),
            )
        ]
        if parsed.state:
            filters.append(Location.state.ilike(parsed.state))

        result = await self.session.execute(
            select(Location)
            .join(DeliveryPrice)
            .where(and_(*filters, self._vehicle_type_filter(vehicle_type)))
            .distinct()
        )
        candidates = result.scalars().all()

        best: Location | None = None
        best_score = 0.0
        for candidate in candidates:
            candidate_score = score_match(parsed, candidate.name, candidate.city, candidate.state)
            if candidate_score > best_score:
                best_score = candidate_score
                best = candidate

        if best_score >= MATCH_THRESHOLD:
            return best
        return None

    async def get_location(
        self, location_name: str, vehicle_type: VehicleType, city: str | None = None, state: str | None = None
    ) -> Location | None:
        parsed = parse_location_name(location_name)
        if city is not None or state is not None:
            apply_parsed_overrides(parsed, city=city, state=state)
        elif parsed.city and parsed.state and not parsed.canonical_names:
            parsed.canonical_names = [
                f"{parsed.state} - {parsed.city}",
            ]

        location = await self._search_by_canonical_names(parsed, vehicle_type)
        if location:
            return location

        location = await self._search_by_city_state(parsed, vehicle_type)
        if location:
            return location

        location = await self._search_by_token_score(parsed, vehicle_type)
        if location:
            return location

        clean_name = re.sub(r"\s*\([^)]*\)", "", location_name).strip()
        legacy_conditions = [
            Location.name.ilike(location_name),
            Location.name.ilike(clean_name),
        ]
        if parsed.city:
            legacy_conditions.append(Location.name.ilike(f"%{parsed.city}%"))
        for condition in legacy_conditions:
            location = await self._find_with_condition(condition, vehicle_type)
            if location:
                return location

        return None

    async def get_location_fuzzy(
        self,
        location_name: str,
        vehicle_type: VehicleType,
        city: str | None = None,
        state: str | None = None,
        threshold: float = 0.6,
    ) -> Location | None:
        location = await self.get_location(location_name, vehicle_type, city, state)
        if location:
            return location

        if self.session.bind is None or self.session.bind.dialect.name != "postgresql":
            return None

        for term in filter(None, [location_name, city, state]):
            result = await self.session.execute(
                select(Location)
                .join(DeliveryPrice)
                .where(
                    and_(
                        self._vehicle_type_filter(vehicle_type),
                        or_(
                            func.similarity(Location.name, term) > threshold,
                            func.similarity(Location.city, term) > threshold,
                        ),
                    )
                )
                .order_by(
                    desc(func.greatest(func.similarity(Location.name, term), func.similarity(Location.city, term)))
                )
                .limit(1)
            )

            location = result.scalar_one_or_none()
            if location:
                return location

        return None

    async def find_location(
        self, location_name: str, vehicle_type: VehicleType, city: str | None = None, state: str | None = None
    ) -> Location | None:
        location = await self.get_location(location_name, vehicle_type, city, state)
        if location:
            return location

        return await self.get_location_fuzzy(location_name, vehicle_type, city, state)

    async def get_by_name(self, name: str) -> Location | None:
        result = await self.session.execute(select(Location).where(Location.name == name))
        return result.scalar_one_or_none()

    async def get_with_search_auction(
        self, search: str | None = None, auction: AuctionEnum | None = None, get_stmt: bool = False
    ):
        stmt = select(Location).distinct()

        filters = []

        if search:
            search_value = search.strip()
            if search_value:
                pattern = f"%{search_value}%"
                filters.append(
                    or_(Location.name.ilike(pattern), Location.city.ilike(pattern), Location.state.ilike(pattern))
                )

        if auction:
            stmt = stmt.join(DeliveryPrice).join(VehicleType)
            filters.append(VehicleType.auction == auction)

        if filters:
            stmt = stmt.where(and_(*filters))

        if get_stmt:
            return stmt

        result = await self.session.execute(stmt)
        return result.scalars().unique().all()
