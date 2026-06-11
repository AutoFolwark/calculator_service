import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

CANADIAN_PROVINCES: dict[str, str] = {
    "alberta": "AB",
    "manitoba": "MB",
    "ontario": "ON",
    "quebec": "QC",
    "saskatchewan": "SK",
    "nova scotia": "NS",
    "new brunswick": "NB",
    "british columbia": "BC",
    "newfoundland and labrador": "NL",
}

US_STATES: dict[str, str] = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
}

DIRECTIONS = frozenset({"north", "south", "east", "west", "central"})
NOISE_TOKENS = frozenset(
    {
        "st",
        "saint",
        "ft",
        "fort",
        "old",
        "sublot",
        "division",
        "network",
        "affiliates",
        "storage",
        "procurement",
        "center",
        "title",
        "consolidated",
    }
)

LOCATION_ALIASES: dict[str, str] = {
    "dc - washington dc": "MD - Washington Dc",
    "washington dc": "MD - Washington Dc",
    "metro dc (md)": "DC - Metro",
    "metro dc": "DC - Metro",
}

MATCH_THRESHOLD = 0.75


@dataclass
class ParsedLocation:
    raw: str
    city: str
    state: str | None
    core_tokens: set[str] = field(default_factory=set)
    direction_tokens: set[str] = field(default_factory=set)
    canonical_names: list[str] = field(default_factory=list)


def clean(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.lower().strip()
    value = value.replace("–", "-").replace("—", "-")
    value = value.replace("/", " ")
    value = re.sub(r"[.']", "", value)
    value = re.sub(r"\s+", " ", value)
    return value


def resolve_state(token: str) -> str | None:
    token = clean(token)
    if len(token) == 2 and token.isalpha():
        return token.upper()
    return US_STATES.get(token) or CANADIAN_PROVINCES.get(token)


def title_case_city(city: str) -> str:
    parts = re.split(r"([\s\-/]+)", city.strip())
    titled: list[str] = []
    for part in parts:
        if re.fullmatch(r"[\s\-/]+", part or ""):
            titled.append(part)
        else:
            titled.append(part[:1].upper() + part[1:].lower() if part else part)
    return "".join(titled)


def tokenize(city: str) -> set[str]:
    normalized = clean(city)
    parts = re.split(r"[\s\-/]+", normalized)
    return {part for part in parts if part not in NOISE_TOKENS and len(part) > 1}


def core_tokens_from(city: str) -> set[str]:
    return {token for token in tokenize(city) if token not in DIRECTIONS}


def direction_tokens_from(city: str) -> set[str]:
    return tokenize(city) & DIRECTIONS


def _strip_state_from_city(city: str, state: str | None) -> str:
    if not state or not city:
        return city

    normalized = clean(city)
    if not normalized:
        return city

    tokens = normalized.split()
    for full_name, abbrev in {**US_STATES, **CANADIAN_PROVINCES}.items():
        if abbrev != state:
            continue
        state_tokens = full_name.split()
        if normalized == full_name:
            continue
        if len(tokens) > len(state_tokens) and tokens[-len(state_tokens) :] == state_tokens:
            return " ".join(tokens[: -len(state_tokens)])

    return normalized


def apply_parsed_overrides(
    parsed: ParsedLocation,
    *,
    city: str | None = None,
    state: str | None = None,
) -> None:
    if city is not None:
        parsed.city = compact_city_label(city)
    if state is not None:
        parsed.state = state.upper()
    parsed.core_tokens = core_tokens_from(parsed.city)
    parsed.direction_tokens = direction_tokens_from(parsed.city)
    parsed.canonical_names = build_canonical_names(parsed.city, parsed.state)


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _fuzzy_token_match(left: str, right: str) -> bool:
    return similarity(left, right) >= 0.8


def _token_overlap(left: set[str], right: set[str]) -> set[str]:
    matched = set(left & right)
    for left_token in left:
        for right_token in right:
            if _fuzzy_token_match(left_token, right_token):
                matched.add(left_token)
                matched.add(right_token)
    return matched


def compact_city_label(city: str) -> str:
    parts = re.split(r"[\s\-/]+", clean(city))
    kept = [part for part in parts if part not in NOISE_TOKENS and len(part) > 1]
    return title_case_city(" ".join(kept))


def build_canonical_names(city: str, state: str | None) -> list[str]:
    if not city or not state:
        return []

    titled = title_case_city(city)
    hyphenated = title_case_city(city.replace(" ", "-"))
    names = [
        f"{state} - {titled}",
        f"{state} - {hyphenated}",
    ]
    deduped: list[str] = []
    seen: set[str] = set()
    for name in names:
        key = name.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(name)
    return deduped


def parse_location_name(name: str) -> ParsedLocation:
    raw = name.strip()
    alias = LOCATION_ALIASES.get(clean(raw))
    if alias:
        if " - " in alias:
            alias_state, alias_city = alias.split(" - ", 1)
            return ParsedLocation(
                raw=raw,
                city=alias_city,
                state=alias_state.upper(),
                core_tokens=core_tokens_from(alias_city),
                direction_tokens=direction_tokens_from(alias_city),
                canonical_names=[alias],
            )

    text = clean(raw)
    state: str | None = None

    street_address_match = re.search(r",\s*([^,]+?),\s*([a-z]{2})(?:\s+\d{5}(?:-\d{4})?)?\s*$", text)
    if street_address_match:
        state = resolve_state(street_address_match.group(2))
        city = compact_city_label(street_address_match.group(1))
        return ParsedLocation(
            raw=raw,
            city=city,
            state=state,
            core_tokens=core_tokens_from(city),
            direction_tokens=direction_tokens_from(city),
            canonical_names=build_canonical_names(city, state),
        )

    match = re.search(r"\(([^)]+)\)", text)
    if match:
        state = resolve_state(match.group(1))
        text = re.sub(r"\s*\([^)]*\)", "", text).strip()

    prefix_match = re.match(r"^([a-z]{2})\s*-\s*(.+)$", text)
    if prefix_match:
        prefix = prefix_match.group(1).upper()
        if prefix in {value for value in US_STATES.values()} | set(CANADIAN_PROVINCES.values()):
            state = state or prefix
            text = prefix_match.group(2).strip()

    if text.endswith(" dc") or text == "washington dc":
        state = state or "MD"

    city = re.sub(r"\s+", " ", text.replace("-", " ")).strip()
    city = _strip_state_from_city(city, state)
    city = compact_city_label(city)
    parsed = ParsedLocation(
        raw=raw,
        city=city,
        state=state,
        core_tokens=core_tokens_from(city),
        direction_tokens=direction_tokens_from(city),
    )
    parsed.canonical_names = build_canonical_names(parsed.city, parsed.state)
    return parsed


def _location_tokens(name: str | None, city: str | None) -> tuple[set[str], set[str]]:
    combined = " ".join(part for part in [name or "", city or ""] if part)
    normalized = clean(combined)
    if " - " in normalized:
        normalized = normalized.split(" - ", 1)[1]
    return core_tokens_from(normalized), direction_tokens_from(normalized)


def score_match(parsed: ParsedLocation, name: str | None, city: str | None, state: str | None) -> float:
    if parsed.state and state and parsed.state.upper() != state.upper():
        return 0.0

    db_core, db_directions = _location_tokens(name, city)
    if not parsed.core_tokens:
        return 0.0

    if parsed.direction_tokens != db_directions and (parsed.direction_tokens or db_directions):
        return 0.0

    overlap = _token_overlap(parsed.core_tokens, db_core)
    if len(parsed.core_tokens) >= 2 and len(overlap) < 2:
        return 0.0

    exact_overlap = parsed.core_tokens & db_core
    if parsed.core_tokens.issubset(db_core) or db_core.issubset(parsed.core_tokens) or overlap:
        union_size = len(parsed.core_tokens | db_core) or 1
        return 0.95 + 0.05 * (len(overlap or exact_overlap) / union_size)

    return 0.0


def is_match(parsed: ParsedLocation, name: str | None, city: str | None, state: str | None) -> bool:
    return score_match(parsed, name, city, state) >= MATCH_THRESHOLD
