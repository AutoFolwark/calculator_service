import asyncio

import pytest

from app.database.crud.location import LocationService
from app.database.crud.vehicle_type import VehicleTypeService
from app.enums.auction import AuctionEnum
from app.enums.vehicle_type import VehicleTypeEnum
from app.services.location_search import (
    apply_parsed_overrides,
    build_canonical_names,
    core_tokens_from,
    parse_location_name,
    score_match,
)
from tests.conftest import LocationDb


@pytest.mark.parametrize(
    ("raw", "city", "state", "canonical"),
    [
        ("chicago-north (il)", "Chicago North", "IL", "IL - Chicago North"),
        ("tx - ft. worth", "Worth", "TX", "TX - Worth"),
        ("fl - ft. pierce", "Pierce", "FL", "FL - Pierce"),
        ("mn - st. cloud", "Cloud", "MN", "MN - Cloud"),
        ("ace - carson (ca)", "Ace Carson", "CA", "CA - Ace Carson"),
        ("dc - washington dc", "Washington Dc", "MD", "MD - Washington Dc"),
        ("avenel new jersey (nj)", "Avenel", "NJ", "NJ - Avenel"),
    ],
)
def test_parse_location_name(raw: str, city: str, state: str, canonical: str) -> None:
    parsed = parse_location_name(raw)
    assert parsed.city == city
    assert parsed.state == state
    assert canonical in parsed.canonical_names


@pytest.mark.parametrize(
    ("raw", "city", "state"),
    [
        ("505 IDLEWILD ROAD, GRAND PRAIRIE, TX 75051", "Grand Prairie", "TX"),
        ("123 main st, austin, tx 78701", "Austin", "TX"),
    ],
)
def test_parse_location_name_handles_street_address(raw: str, city: str, state: str) -> None:
    parsed = parse_location_name(raw)
    assert parsed.city == city
    assert parsed.state == state
    assert f"{state} - {city}" in parsed.canonical_names


def test_build_canonical_names_includes_hyphen_variant() -> None:
    names = build_canonical_names("Boston Shirley", "MA")
    assert "MA - Boston Shirley" in names
    assert "MA - Boston-Shirley" in names


def test_score_match_handles_common_typo() -> None:
    parsed = parse_location_name("akron-canton (oh)")
    score = score_match(parsed, "OH - Acron Canton", "Acron Canton", "OH")
    assert score >= 0.75


@pytest.mark.parametrize(
    ("raw", "city", "state"),
    [
        ("new york (ny)", "New York", "NY"),
        ("georgia (ga)", "Georgia", "GA"),
        ("new york mills (ny)", "New York Mills", "NY"),
        ("avenel new jersey (nj)", "Avenel", "NJ"),
    ],
)
def test_parse_location_name_preserves_state_named_cities(raw: str, city: str, state: str) -> None:
    parsed = parse_location_name(raw)
    assert parsed.city == city
    assert parsed.state == state
    assert parsed.core_tokens == core_tokens_from(city)


def test_apply_parsed_overrides_refreshes_derived_fields() -> None:
    parsed = parse_location_name("dc - washington dc")
    assert parsed.canonical_names == ["MD - Washington Dc"]

    apply_parsed_overrides(parsed, city="Chicago North", state="IL")
    assert parsed.city == "Chicago North"
    assert parsed.state == "IL"
    assert parsed.core_tokens == {"chicago"}
    assert parsed.direction_tokens == {"north"}
    assert "IL - Chicago North" in parsed.canonical_names


async def _find_location(location_db: LocationDb, query: str, auction: AuctionEnum):
    async with location_db.session() as db:
        vehicle_type = await VehicleTypeService(db).get_by_auction_and_type(auction, VehicleTypeEnum.CAR)
        return await LocationService(db).find_location(query, vehicle_type)


@pytest.mark.parametrize(
    ("query", "auction", "expected"),
    [
        ("chicago-north (il)", AuctionEnum.COPART, "IL - Chicago North"),
        ("miami-north (fl)", AuctionEnum.COPART, "FL - Miami North"),
        ("tx - ft. worth", AuctionEnum.COPART, "TX - Worth"),
        ("fl - ft. pierce", AuctionEnum.COPART, "FL - Pierce"),
        ("mn - st. cloud", AuctionEnum.COPART, "MN - Cloud"),
        ("pittsburgh-north (pa)", AuctionEnum.COPART, "PA - Pittsburgh North"),
        ("pa - philadelphia east-sublot", AuctionEnum.COPART, "PA - Philadelphia East"),
        ("orlando-north (fl)", AuctionEnum.COPART, "FL - Orlando North"),
        ("dc - washington dc", AuctionEnum.COPART, "MD - Washington Dc"),
        ("ace - carson (ca)", AuctionEnum.IAAI, "CA - Ace Carson"),
        ("akron-canton (oh)", AuctionEnum.IAAI, "OH - Acron Canton"),
        ("boston - shirley (ma)", AuctionEnum.IAAI, "MA - Boston-Shirley"),
        ("houston-north (tx)", AuctionEnum.IAAI, "TX - Houston North"),
        ("avenel new jersey (nj)", AuctionEnum.IAAI, "NJ - Avenel"),
        ("portland - gorham (me)", AuctionEnum.IAAI, "ME - Portland Gorham"),
        ("san antonio-south (tx)", AuctionEnum.IAAI, "TX - San Antonio South"),
    ],
)
def test_find_location_matches_existing_rows(
    location_db: LocationDb,
    query: str,
    auction: AuctionEnum,
    expected: str,
) -> None:
    location = asyncio.run(_find_location(location_db, query, auction))
    assert location is not None
    assert location.name == expected


@pytest.mark.parametrize(
    ("query", "auction"),
    [
        ("ca - san bernardino", AuctionEnum.COPART),
        ("boise (id)", AuctionEnum.COPART),
        ("ab - calgary", AuctionEnum.COPART),
    ],
)
def test_find_location_stays_missing_for_unknown_rows(
    location_db: LocationDb,
    query: str,
    auction: AuctionEnum,
) -> None:
    location = asyncio.run(_find_location(location_db, query, auction))
    assert location is None
