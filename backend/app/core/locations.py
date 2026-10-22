import re
from typing import Any, Dict, List, Optional, Set, Tuple


SUPPORTED_COUNTRIES: Dict[str, Dict] = {
    "US": {
        "code": "US",
        "name": "United States",
        "aliases": ["usa", "united states", "u.s.", "u.s.a.", "america"],
        "states": {
            "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
            "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
            "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
            "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
            "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
            "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
            "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
            "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
            "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
            "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
            "DC": "District of Columbia"
        }
    },
    "GB": {
        "code": "GB",
        "name": "United Kingdom",
        "aliases": ["uk", "united kingdom", "great britain", "england", "scotland", "wales", "britain"],
        "states": {
            "ENG": "England", "SCT": "Scotland", "WLS": "Wales", "NIR": "Northern Ireland",
            "LON": "Greater London", "MAN": "Greater Manchester", "WMD": "West Midlands",
            "YOR": "Yorkshire"
        }
    },
    "CA": {
        "code": "CA",
        "name": "Canada",
        "aliases": ["canada", "can"],
        "states": {
            "ON": "Ontario", "QC": "Quebec", "BC": "British Columbia", "AB": "Alberta",
            "MB": "Manitoba", "SK": "Saskatchewan", "NS": "Nova Scotia", "NB": "New Brunswick",
            "NL": "Newfoundland and Labrador", "PE": "Prince Edward Island"
        }
    },
    "DE": {
        "code": "DE",
        "name": "Germany",
        "aliases": ["germany", "deutschland"],
        "states": {
            "BW": "Baden-Württemberg", "BY": "Bavaria (Bayern)", "BE": "Berlin", "BB": "Brandenburg",
            "HB": "Bremen", "HH": "Hamburg", "HE": "Hesse (Hessen)", "NI": "Lower Saxony",
            "NW": "North Rhine-Westphalia", "RP": "Rhineland-Palatinate", "SN": "Saxony", "ST": "Saxony-Anhalt"
        }
    },
    "IN": {
        "code": "IN",
        "name": "India",
        "aliases": ["india", "bharat", "republic of india"],
        "states": {
            "RJ": "Rajasthan",
            "KA": "Karnataka",
            "MH": "Maharashtra",
            "TG": "Telangana",
            "DL": "Delhi NCR",
            "TN": "Tamil Nadu",
            "GJ": "Gujarat",
            "UP": "Uttar Pradesh",
            "WB": "West Bengal",
            "KL": "Kerala",
            "PB": "Punjab",
            "HR": "Haryana",
            "MP": "Madhya Pradesh",
            "AP": "Andhra Pradesh",
            "BR": "Bihar",
            "OD": "Odisha",
            "AS": "Assam",
            "JH": "Jharkhand",
            "UT": "Uttarakhand",
            "HP": "Himachal Pradesh",
            "GA": "Goa",
            "CH": "Chandigarh"
        }
    },
    "AU": {
        "code": "AU",
        "name": "Australia",
        "aliases": ["australia", "aus"],
        "states": {
            "NSW": "New South Wales", "VIC": "Victoria", "QLD": "Queensland",
            "WA": "Western Australia", "SA": "South Australia", "TAS": "Tasmania", "ACT": "Australian Capital Territory"
        }
    },
    "REMOTE": {
        "code": "REMOTE",
        "name": "Remote / Worldwide",
        "aliases": ["worldwide", "anywhere", "global", "work from anywhere", "universal remote"],
        "states": {}
    }
}

# European geographical terms that designate European residency or business hours
EUROPE_INDICATORS: Set[str] = {
    "europe", "eu", "emea", "germany", "deutschland", "berlin", "munich", "frankfurt", "hamburg",
    "uk", "united kingdom", "great britain", "england", "scotland", "wales", "london", "manchester", "birmingham",
    "france", "paris", "spain", "madrid", "barcelona", "italy", "rome", "milan",
    "netherlands", "amsterdam", "rotterdam", "poland", "warsaw", "krakow", "ireland", "dublin",
    "switzerland", "zurich", "geneva", "sweden", "stockholm", "norway", "oslo", "denmark", "copenhagen",
    "finland", "helsinki", "austria", "vienna", "belgium", "brussels", "portugal", "lisbon",
    "czech republic", "czechia", "prague", "romania", "bucharest", "hungary", "budapest",
    "bulgaria", "sofia", "estonia", "tallinn", "latvia", "riga", "lithuania", "vilnius",
    "croatia", "zagreb", "slovakia", "bratislava", "slovenia", "ljubljana", "luxembourg", "cyprus", "malta", "greece"
}

NORTH_AMERICA_INDICATORS: Set[str] = {
    "united states", "usa", "u.s.", "u.s.a.", "us only", "canada", "mexico"
}

# Major Indian cities mapped to state codes
INDIAN_CITIES_TO_STATE: Dict[str, str] = {
    "jaipur": "RJ", "jodhpur": "RJ", "udaipur": "RJ", "kota": "RJ", "bikaner": "RJ",
    "ajmer": "RJ", "alwar": "RJ", "bhilwara": "RJ", "sikar": "RJ", "pali": "RJ",
    "bengaluru": "KA", "bangalore": "KA", "mysuru": "KA", "mangalore": "KA", "hubli": "KA",
    "mumbai": "MH", "pune": "MH", "nagpur": "MH", "nashik": "MH", "thane": "MH", "navi mumbai": "MH",
    "hyderabad": "TG", "warangal": "TG", "secunderabad": "TG",
    "delhi": "DL", "new delhi": "DL", "noida": "UP", "greater noida": "UP", "ghaziabad": "UP",
    "gurugram": "HR", "gurgaon": "HR", "faridabad": "HR",
    "chennai": "TN", "coimbatore": "TN", "madurai": "TN", "trichy": "TN",
    "ahmedabad": "GJ", "surat": "GJ", "vadodara": "GJ", "gandhinagar": "GJ", "rajkot": "GJ",
    "lucknow": "UP", "kanpur": "UP", "varanasi": "UP", "agra": "UP",
    "kolkata": "WB", "howrah": "WB", "siliguri": "WB",
    "kochi": "KL", "thiruvananthapuram": "KL", "trivandrum": "KL", "calicut": "KL", "kozhikode": "KL",
    "chandigarh": "PB", "mohali": "PB", "ludhiana": "PB", "amritsar": "PB",
    "indore": "MP", "bhopal": "MP", "gwalior": "MP",
    "patna": "BR", "bhubaneswar": "OD", "ranchi": "JH", "guwahati": "AS",
    "dehradun": "UT", "shimla": "HP", "panaji": "GA", "visakhapatnam": "AP", "vijayawada": "AP"
}

# Nearby / Radius clusters for intelligent expansion (commuting/local radius <= 150km)
NEARBY_CITIES_MAP: Dict[str, List[Tuple[str, int]]] = {
    "jaipur": [("Dausa", 55), ("Tonk", 95), ("Sikar", 115), ("Ajmer", 130), ("Alwar", 150)],
    "jodhpur": [("Pali", 70), ("Nagaur", 135)],
    "udaipur": [("Rajsamand", 65), ("Chittorgarh", 115), ("Bhilwara", 150)],
    "kota": [("Bundi", 40), ("Baran", 75), ("Jhalawar", 85)],
    "bengaluru": [("Hosur", 40), ("Tumakuru", 70), ("Mysuru", 145)],
    "mumbai": [("Thane", 25), ("Navi Mumbai", 30), ("Kalyan", 40)],
    "pune": [("Pimpri-Chinchwad", 15), ("Talegaon", 35), ("Lonavala", 65)],
    "delhi": [("Noida", 25), ("Gurugram", 30), ("Faridabad", 30), ("Ghaziabad", 30)],
    "gurugram": [("Delhi", 30), ("Faridabad", 35), ("Noida", 45)],
    "noida": [("Delhi", 25), ("Ghaziabad", 20), ("Faridabad", 35), ("Gurugram", 45)]
}


def get_supported_locations():
    """Returns list of countries and their available states for frontend selection."""
    locations = []
    for code, info in SUPPORTED_COUNTRIES.items():
        states_list = [{"code": sc, "name": sname} for sc, sname in info["states"].items()]
        locations.append({
            "code": code,
            "name": info["name"],
            "states": states_list
        })
    return locations


def is_location_in_europe(loc_clean: str) -> bool:
    """Detects whether a location string explicitly specifies European geography."""
    for euro in EUROPE_INDICATORS:
        if re.search(rf"\b{re.escape(euro)}\b", loc_clean):
            return True
    return False


def is_location_in_north_america(loc_clean: str) -> bool:
    """Detects whether a location string explicitly specifies North American geography."""
    loc_clean = (loc_clean or "").lower()
    # Handle US states abbreviation like ", CA", ", NY", ", TX", etc.
    if re.search(r",\s*(?:al|ak|az|ar|ca|co|ct|de|fl|ga|hi|id|il|in|ia|ks|ky|la|me|md|ma|mi|mn|ms|mo|mt|ne|nv|nh|nj|nm|ny|nc|nd|oh|ok|or|pa|ri|sc|sd|tn|tx|ut|vt|va|wa|wv|wi|wy|dc)\b", loc_clean):
        return True
    for na in NORTH_AMERICA_INDICATORS:
        if re.search(rf"\b{re.escape(na)}\b", loc_clean):
            return True
    # Handle full US state names (e.g. Ohio, California, Texas)
    for st_name in SUPPORTED_COUNTRIES["US"]["states"].values():
        if re.search(rf"\b{re.escape(st_name.lower())}\b", loc_clean):
            return True
    return False


def normalize_job_location(
    raw_location: str,
    raw_country: Optional[str] = None,
    raw_is_remote: bool = False
) -> Dict[str, Any]:
    """
    Parses and canonicalizes job location metadata.
    Prevents European or US-only remote jobs from masquerading as universal or Indian jobs.
    """
    loc_clean = (raw_location or "").strip()
    loc_lower = loc_clean.lower()
    
    is_remote = raw_is_remote or bool(re.search(r"\b(remote|telecommute|work from home|wfh)\b", loc_lower))
    
    detected_country = raw_country
    detected_state = None
    detected_city = None

    # 1. European Detection
    if is_location_in_europe(loc_lower):
        if "germany" in loc_lower or "berlin" in loc_lower or "munich" in loc_lower:
            detected_country = "DE"
        elif "uk" in loc_lower or "united kingdom" in loc_lower or "london" in loc_lower:
            detected_country = "GB"
        else:
            detected_country = "EU"

    # 2. North American Detection
    elif is_location_in_north_america(loc_lower):
        if "canada" in loc_lower:
            detected_country = "CA"
        elif "mexico" in loc_lower:
            detected_country = "MX"
        else:
            detected_country = "US"
            # Extract state if present (e.g. "Columbus, IN")
            st_match = re.search(r",\s*([a-zA-Z]{2})\b", loc_lower)
            if st_match:
                candidate_st = st_match.group(1).upper()
                if candidate_st in SUPPORTED_COUNTRIES["US"]["states"]:
                    detected_state = candidate_st

    # 3. Indian Detection
    elif any(re.search(rf"\b{re.escape(alias)}\b", loc_lower) for alias in ["india", "bharat"]) or (raw_country == "IN"):
        detected_country = "IN"

    # Check for Indian Cities / States in location string
    for city_name, st_code in INDIAN_CITIES_TO_STATE.items():
        if re.search(rf"\b{re.escape(city_name)}\b", loc_lower):
            detected_country = "IN"
            detected_state = st_code
            detected_city = city_name.title()
            break

    if not detected_state and detected_country == "IN":
        for st_code, st_name in SUPPORTED_COUNTRIES["IN"]["states"].items():
            if re.search(rf"\b{re.escape(st_name.lower())}\b", loc_lower) or re.search(rf"\b{re.escape(st_code.lower())}\b", loc_lower):
                detected_state = st_code
                break

    # Determine remote scope
    remote_scope = "none"
    if is_remote:
        if any(w in loc_lower for w in ["worldwide", "anywhere", "global", "work from anywhere"]):
            remote_scope = "worldwide"
            if not detected_country or detected_country == "REMOTE":
                detected_country = "REMOTE"
        elif detected_country in ["EU", "DE", "GB"]:
            remote_scope = "regional_europe"
        elif detected_country in ["US", "CA"]:
            remote_scope = "regional_americas"
        elif detected_country == "IN":
            remote_scope = "country_india"
        else:
            remote_scope = "unspecified_remote"

    return {
        "country": detected_country or ("REMOTE" if (is_remote and remote_scope == "worldwide") else "UNKNOWN"),
        "state": detected_state,
        "city": detected_city,
        "is_remote": is_remote,
        "remote_scope": remote_scope,
        "canonical_location": loc_clean
    }


def is_remote_eligible_for_country(loc_clean: str, target_country: str) -> Tuple[bool, str]:
    """
    Verifies whether a remote job's stated geographic eligibility encompasses the target country.
    """
    target = (target_country or "").upper()
    loc_clean = (loc_clean or "").lower()
    
    # Target Country: INDIA (IN)
    if target == "IN":
        # Disqualify jobs explicitly designated for Europe, UK, or Americas
        if is_location_in_europe(loc_clean):
            return False, "Restricted to Europe/UK geography"
        if is_location_in_north_america(loc_clean):
            return False, "Restricted to North American geography"
        
        # Qualified if specifically India, APAC, or explicitly Worldwide
        if any(w in loc_clean for w in ["india", "bharat", "apac", "asia"]):
            return True, "Eligible in India / APAC"
        if any(w in loc_clean for w in ["worldwide", "anywhere", "global", "work from anywhere"]):
            return True, "Worldwide Remote"
        
        # If generic "Remote" with zero regional info, disqualify for strict country search
        return False, "Unverified remote eligibility"

    # Target Country: UNITED STATES (US)
    if target == "US":
        if is_location_in_europe(loc_clean) and not any(w in loc_clean for w in ["us", "usa", "worldwide", "global"]):
            return False, "Restricted to Europe"
        if any(w in loc_clean for w in ["us", "usa", "united states", "north america", "worldwide", "global", "anywhere"]):
            return True, "Eligible in US / Worldwide"
        return True, "Remote"

    # Default check
    if any(w in loc_clean for w in ["worldwide", "anywhere", "global"]):
        return True, "Worldwide Remote"
    
    return False, "Unverified remote eligibility"


def matches_location_filter(
    job_location: str,
    job_country: Optional[str] = None,
    job_is_remote: bool = False,
    filter_country: Optional[str] = None,
    filter_states: Optional[List[str]] = None,
    filter_city: Optional[str] = None,
    remote_only: bool = False,
    job_title: Optional[str] = None
) -> bool:
    """
    Evaluates whether a job matches location filters.
    Strictly enforces country boundaries:
    - If India (IN) is selected, European, US, and regional foreign jobs are STRICTLY excluded.
    - Differentiates US state abbreviations (e.g. 'Columbus, IN') from India.
    - Verifies remote eligibility.
    """
    loc_clean = (job_location or "").lower()
    
    # 1. Remote Only requirement
    if remote_only:
        is_remote_loc = (
            job_is_remote or
            any(w in loc_clean for w in ["remote", "anywhere", "telecommute", "work from home", "worldwide", "global"])
        )
        if not is_remote_loc:
            return False

    # 2. No country or global wildcard
    if not filter_country or filter_country.upper() in ["ALL", "ANY", "WORLDWIDE", "GLOBAL"]:
        return True

    target_country = filter_country.upper()
    if target_country == "REMOTE":
        return (
            job_is_remote or
            any(w in loc_clean for w in ["remote", "anywhere", "telecommute", "worldwide", "global"])
        )

    # 3. Strict Country Boundary Check
    if target_country == "IN":
        # Disallow jobs whose title explicitly bounds them to US or Europe
        if job_title:
            jt_lower = job_title.lower()
            if is_location_in_north_america(jt_lower) or is_location_in_europe(jt_lower):
                return False

        # Disallow European jobs completely
        if is_location_in_europe(loc_clean):
            return False
        # Disallow North American jobs (including Columbus, IN in Indiana!)
        if is_location_in_north_america(loc_clean):
            return False
        # Disallow other explicit foreign country codes
        if job_country and job_country.upper() not in ["IN", "REMOTE"]:
            return False

        # If job is remote, verify it's genuinely eligible in India
        if job_is_remote:
            eligible, _ = is_remote_eligible_for_country(loc_clean, "IN")
            if not eligible and not any(re.search(rf"\b{re.escape(alias)}\b", loc_clean) for alias in ["india", "bharat"]):
                # Check if it mentions an Indian city
                if not any(re.search(rf"\b{re.escape(c)}\b", loc_clean) for c in INDIAN_CITIES_TO_STATE.keys()):
                    return False

        # If on-site (not remote), verify it belongs to India
        if not job_is_remote:
            is_indian = (
                job_country == "IN" or
                any(re.search(rf"\b{re.escape(a)}\b", loc_clean) for a in ["india", "bharat"]) or
                any(re.search(rf"\b{re.escape(c)}\b", loc_clean) for c in INDIAN_CITIES_TO_STATE.keys()) or
                any(re.search(rf"\b{re.escape(s.lower())}\b", loc_clean) for s in SUPPORTED_COUNTRIES["IN"]["states"].values())
            )
            if not is_indian:
                return False

    else:
        # Standard country check for other countries
        country_info = SUPPORTED_COUNTRIES.get(target_country)
        if country_info:
            country_matched = False
            effective_country = job_country.upper() if job_country else None
            if not effective_country:
                normalized = normalize_job_location(loc_clean, raw_country=job_country, raw_is_remote=job_is_remote)
                effective_country = normalized.get("country")

            if effective_country == country_info["code"]:
                country_matched = True

            if not country_matched:
                for alias in country_info["aliases"]:
                    if re.search(rf"\b{re.escape(alias)}\b", loc_clean):
                        country_matched = True
                        break

            if not country_matched:
                for st_code, st_name in country_info.get("states", {}).items():
                    if re.search(rf"\b{re.escape(st_name.lower())}\b", loc_clean) or re.search(rf"\b{re.escape(st_code.lower())}\b", loc_clean):
                        country_matched = True
                        break

            if not country_matched and job_is_remote:
                eligible, _ = is_remote_eligible_for_country(loc_clean, target_country)
                country_matched = eligible

            if not country_matched:
                return False

    # 4. State / Region Filter Check
    if filter_states and len(filter_states) > 0:
        requested_states = [s.upper() for s in filter_states]
        state_matched = False

        if target_country == "IN":
            for st in requested_states:
                st_name = SUPPORTED_COUNTRIES["IN"]["states"].get(st, "").lower()
                # Check state name (e.g. "rajasthan")
                if st_name and st_name in loc_clean:
                    state_matched = True
                    break
                # Check state code with word boundaries
                if re.search(rf"\b{re.escape(st.lower())}\b", loc_clean):
                    state_matched = True
                    break
                # Check cities in that state
                for city_k, state_v in INDIAN_CITIES_TO_STATE.items():
                    if state_v == st and re.search(rf"\b{re.escape(city_k)}\b", loc_clean):
                        state_matched = True
                        break
                if state_matched:
                    break

            # If user selected Rajasthan, reject jobs located in other Indian states (e.g. Karnataka, Maharashtra)
            if not state_matched:
                for other_code, other_name in SUPPORTED_COUNTRIES["IN"]["states"].items():
                    if other_code not in requested_states:
                        if other_name.lower() in loc_clean or re.search(rf"\b{re.escape(other_code.lower())}\b", loc_clean):
                            return False
                        # Check other state's cities
                        for other_city, other_st_code in INDIAN_CITIES_TO_STATE.items():
                            if other_st_code == other_code and re.search(rf"\b{re.escape(other_city)}\b", loc_clean):
                                return False
                
                # If job is general India Remote with no specific state restrictions, it can match state filter
                if job_is_remote and any(w in loc_clean for w in ["worldwide", "anywhere", "india", "global"]):
                    state_matched = True
                else:
                    return False

        else:
            country_info = SUPPORTED_COUNTRIES.get(target_country)
            if country_info:
                for st in requested_states:
                    st_full = country_info["states"].get(st, "").lower()
                    if re.search(rf"\b{re.escape(st.lower())}\b", loc_clean) or (st_full and st_full in loc_clean):
                        state_matched = True
                        break
                if not state_matched and not (job_is_remote and "remote" in loc_clean):
                    return False

    # 5. City Filter Check
    if filter_city and filter_city.strip():
        city_lower = filter_city.strip().lower()
        city_matched = city_lower in loc_clean
        if not city_matched:
            # Check nearby cities for radius matching
            nearby = [c[0].lower() for c in NEARBY_CITIES_MAP.get(city_lower, [])]
            if any(nc in loc_clean for nc in nearby):
                city_matched = True

        if not city_matched:
            return False

    return True


def classify_location_hierarchy(
    job_city: Optional[str] = None,
    job_state: Optional[str] = None,
    job_country: Optional[str] = None,
    job_location: str = "",
    filter_city: Optional[str] = None,
    filter_states: Optional[List[str]] = None,
    filter_country: Optional[str] = None,
    is_remote: bool = False
) -> Tuple[str, str]:
    """
    Classifies where a matching job sits in the expansion hierarchy:
    - "city": Exact city match
    - "nearby": Nearby city within commuting/regional radius
    - "state": Expanded to state level
    - "country": Expanded to country level or eligible remote
    """
    loc_lower = (job_location or "").lower()
    
    # 1. Exact City Match
    if filter_city and filter_city.strip():
        req_city = filter_city.strip().lower()
        if (job_city and job_city.lower() == req_city) or (req_city in loc_lower):
            return "city", f"Direct match in {filter_city.strip()}"

        # 2. Nearby Radius Match
        nearby_entries = NEARBY_CITIES_MAP.get(req_city, [])
        for nearby_city, dist_km in nearby_entries:
            if (job_city and job_city.lower() == nearby_city.lower()) or (nearby_city.lower() in loc_lower):
                return "nearby", f"Nearby location: {nearby_city} (~{dist_km} km from {filter_city.strip()})"

    fc = (filter_country or "").upper()

    # 3. State Match
    if filter_states and len(filter_states) > 0:
        for st in filter_states:
            st_upper = st.upper()
            country_states = SUPPORTED_COUNTRIES.get(fc, {}).get("states", {}) if fc else {}
            st_name = country_states.get(st_upper, st_upper)
            if job_state and job_state.upper() == st_upper:
                return "state", f"Expanded to state: {st_name}"
            if (st_name and st_name.lower() in loc_lower) or re.search(rf"\b{re.escape(st.lower())}\b", loc_lower):
                return "state", f"Expanded to state: {st_name}"

    # 4. Country Fallback / Remote / Global
    if not filter_country or fc in ["ALL", "ANY", "WORLDWIDE", "GLOBAL"]:
        if is_remote:
            return "country", "Worldwide Remote Opportunity"
        return "country", f"Global Opportunity ({job_location or 'Worldwide'})"

    c_info = SUPPORTED_COUNTRIES.get(fc, {})
    c_name = c_info.get("name", filter_country)
    if is_remote:
        return "country", f"Expanded to national remote ({c_name} eligible)"
    return "country", f"Expanded to country: {c_name}"
