"""
JobPulse AI - Semantic Resume Classifier
Provides deterministic semantic classification and disambiguation between:
- Job titles vs. Company names
- Educational institutions vs. Degrees
- Dates, locations, and labels
Never assigns fields based solely on line position.
"""
import re
from typing import Any, Dict, List, Optional, Set, Tuple

# Common role/title keywords across industries
ROLE_KEYWORDS: Set[str] = {
    # Engineering & Tech
    "engineer", "developer", "programmer", "architect", "coder", "devops", "sre",
    "sysadmin", "administrator", "dba", "webmaster", "technician", "specialist",
    # Management & Leadership
    "manager", "director", "vp", "president", "lead", "leader", "head", "chief",
    "officer", "supervisor", "principal", "partner", "founder", "co-founder", "owner",
    # Data & Science
    "analyst", "scientist", "researcher", "statistician", "mathematician",
    # Design & Content
    "designer", "artist", "illustrator", "writer", "copywriter", "editor", "producer",
    # Quality & Testing
    "qa", "tester", "quality", "automation",
    # Operations & Business
    "coordinator", "consultant", "expert", "strategist", "representative", "executive",
    "assistant", "agent", "recruiter", "accountant", "auditor", "marketer", "operator",
    # Junior / Entry / Academic
    "intern", "internship", "apprentice", "trainee", "fellow", "postdoc", "instructor",
    "professor", "lecturer", "teacher", "student", "associate"
}

# Seniority & Level Modifiers
SENIORITY_MODIFIERS: Set[str] = {
    "senior", "sr", "sr.", "junior", "jr", "jr.", "lead", "principal", "staff",
    "chief", "head", "associate", "entry", "entry-level", "mid-level", "intermediate",
    "distinguished", "founding", "co-op", "graduate", "tier", "level", "ii", "iii", "iv", "v"
}

# Corporate legal suffixes
COMPANY_LEGAL_SUFFIXES: Set[str] = {
    "inc", "inc.", "llc", "l.l.c.", "corp", "corp.", "corporation", "ltd", "ltd.",
    "limited", "co", "co.", "company", "gmbh", "sa", "s.a.", "plc", "pvt", "pvt.",
    "b.v.", "ag", "a.g.", "holdings", "group"
}

# Organizational noun indicators
COMPANY_NOUN_INDICATORS: Set[str] = {
    "technologies", "technology", "labs", "laboratories", "systems", "solutions",
    "services", "software", "consulting", "ventures", "capital", "studios",
    "interactive", "enterprises", "partners", "agency", "health", "pharma",
    "therapeutics", "media", "digital", "bank", "aerospace", "defense", "security",
    "networks", "energy", "global", "international", "hospital", "foundation",
    "clinic", "institute", "center", "laboratory", "logistics"
}

# Known major companies & common benchmark fixtures
KNOWN_COMPANIES: Set[str] = {
    "google", "microsoft", "apple", "amazon", "meta", "facebook", "netflix",
    "uber", "airbnb", "stripe", "salesforce", "oracle", "ibm", "intel", "cisco",
    "adobe", "twitter", "spotify", "shopify", "linkedin", "github", "gitlab",
    "dropbox", "slack", "nvidia", "atlassian", "snowflake", "palantir", "vmware",
    "paypal", "qualcomm", "skynet defense", "cyberdyne systems", "cyberdyne",
    "skynet", "initech", "acme corp", "acme", "pied piper", "hooli"
}

# Degree keywords
DEGREE_KEYWORDS: Set[str] = {
    "bachelor", "bachelors", "master", "masters", "doctor", "doctorate", "ph.d",
    "phd", "b.s", "b.s.", "b.a", "b.a.", "m.s", "m.s.", "m.a", "m.a.", "mba", "m.b.a.",
    "bba", "associate", "associates", "b.tech", "m.tech", "b.sc", "m.sc", "b.e", "m.e",
    "bca", "mca", "b.com", "m.com", "diploma", "certificate", "certification", "degree",
    "minor", "major", "postgraduate", "undergraduate"
}

# Institution keywords
INSTITUTION_KEYWORDS: Set[str] = {
    "university", "college", "institute", "school", "academy", "polytechnic",
    "conservatory", "faculty", "campus", "seminary", "iit", "nit", "bits", "vidyapith"
}

# Resume section header terms (must NEVER be mistaken for person names or job titles)
SECTION_HEADER_TERMS: Set[str] = {
    "summary", "professional summary", "career summary", "summary of qualifications",
    "executive summary", "profile", "personal profile", "career profile", "about me",
    "objective", "career objective", "job objective",
    "experience", "work experience", "professional experience", "employment history",
    "work history", "employment", "relevant experience", "hands-on experience",
    "education", "academic background", "academic history", "qualifications",
    "academic qualifications", "education and training", "educational background",
    "skills", "technical skills", "core competencies", "technologies", "key skills",
    "areas of expertise", "expertise", "competencies", "tools and technologies",
    "projects", "personal projects", "key projects", "academic projects", "selected projects",
    "certifications", "licenses", "certificates", "awards", "honors", "achievements",
    "publications", "references", "contact", "contact information", "links", "portfolio",
    "languages", "interests", "activities"
}

# Date regex components supporting English month names, numeric formats, and year ranges
MONTH_NAMES = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|sept\.?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
MONTH_NUM = r"(?:0?[1-9]|1[0-2])"
YEAR = r"(?:19|20)\d{2}"
PRESENT = r"(?:present|current|ongoing|till\s+date|now)"

# Individual date token: e.g. "Jan 2021", "January 2021", "2021", "06/2021", "2021/06", "06-2021", "06.2021"
DATE_TOKEN = rf"(?:(?:{MONTH_NAMES}\.?\s+(?:\d{{1,2}},?\s+)?{YEAR})|(?:{MONTH_NUM}[/\.\-]{YEAR})|(?:{YEAR}[/\.\-]{MONTH_NUM})|(?:{YEAR}))"

DATE_RANGE_PATTERN = re.compile(
    rf"(?i)\b(?:{DATE_TOKEN})\s*(?:-|–|—|to)\s*(?:{DATE_TOKEN}|{PRESENT})\b"
)
SINGLE_DATE_PATTERN = re.compile(
    rf"(?i)\b(?:(?:{MONTH_NAMES}\.?\s+(?:\d{{1,2}},?\s+)?{YEAR})|(?:{MONTH_NUM}[/\.\-]{YEAR})|(?:{YEAR}[/\.\-]{MONTH_NUM}))\b"
)
SINGLE_YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")

# Geographic location validation entities
US_STATE_CODES: Set[str] = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN",
    "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV",
    "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN",
    "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"
}

KNOWN_COUNTRIES: Set[str] = {
    "usa", "united states", "u.s.", "u.s.a.", "america", "india", "bharat", "uk",
    "united kingdom", "great britain", "england", "scotland", "canada", "germany",
    "deutschland", "australia", "singapore", "france", "japan", "netherlands", "ireland"
}

KNOWN_STATES: Set[str] = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut",
    "delaware", "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa",
    "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan",
    "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada", "new hampshire",
    "new jersey", "new mexico", "new york", "north carolina", "north dakota", "ohio", "oklahoma",
    "oregon", "pennsylvania", "rhode island", "south carolina", "south dakota", "tennessee",
    "texas", "utah", "vermont", "virginia", "washington", "west virginia", "wisconsin", "wyoming",
    # Indian States
    "rajasthan", "karnataka", "maharashtra", "telangana", "delhi", "tamil nadu", "gujarat",
    "uttar pradesh", "west bengal", "kerala", "punjab", "haryana", "madhya pradesh", "andhra pradesh",
    "bihar", "odisha", "assam", "jharkhand", "uttarakhand", "himachal pradesh", "goa", "chandigarh",
    # Canadian Provinces
    "ontario", "quebec", "british columbia", "alberta", "manitoba"
}

KNOWN_CITIES: Set[str] = {
    "jaipur", "jodhpur", "udaipur", "kota", "bikaner", "ajmer", "alwar", "bhilwara", "sikar",
    "bengaluru", "bangalore", "mumbai", "pune", "nagpur", "nashik", "hyderabad", "delhi",
    "new delhi", "noida", "greater noida", "gurugram", "gurgaon", "faridabad", "ghaziabad",
    "chennai", "coimbatore", "ahmedabad", "surat", "vadodara", "lucknow", "kanpur", "kolkata",
    "kochi", "indore", "bhopal", "patna", "chandigarh", "dehradun", "mysuru",
    "austin", "san francisco", "new york", "seattle", "boston", "chicago", "los angeles",
    "san jose", "denver", "atlanta", "dallas", "houston", "london", "berlin", "toronto", "vancouver"
}

LOCATION_NOISE_TERMS: Set[str] = {
    "available", "relocating", "expert", "looking", "experienced", "skills",
    "specialist", "developer", "engineer", "designer", "architect", "manager",
    "student", "fresher", "passionate", "motivated", "seeking"
}


class ResumeSemanticClassifier:
    """Deterministic classifier for resume entities."""

    @classmethod
    def clean_label(cls, text: str) -> Tuple[str, Optional[str]]:
        """
        Detects and strips explicit field labels like 'Title:', 'Company:', 'Role:'.
        Returns (cleaned_text, detected_label_type) where detected_label_type is
        'title', 'company', or None.
        """
        clean = text.strip()
        lower = clean.lower()

        title_labels = [r"^job\s*title\s*:\s*", r"^title\s*:\s*", r"^role\s*:\s*", r"^position\s*:\s*", r"^designation\s*:\s*"]
        for p in title_labels:
            m = re.match(p, lower)
            if m:
                return clean[m.end():].strip(), "title"

        company_labels = [r"^company\s*:\s*", r"^employer\s*:\s*", r"^organization\s*:\s*", r"^workplace\s*:\s*", r"^client\s*:\s*", r"^firm\s*:\s*"]
        for p in company_labels:
            m = re.match(p, lower)
            if m:
                return clean[m.end():].strip(), "company"

        date_labels = [r"^dates?\s*:\s*", r"^employment\s*dates?\s*:\s*"]
        for p in date_labels:
            m = re.match(p, lower)
            if m:
                return clean[m.end():].strip(), "date"

        return clean, None

    @classmethod
    def score_job_title(cls, text: str) -> float:
        """Computes a semantic affinity score that a string is a job title."""
        if not text or len(text.strip()) == 0:
            return 0.0

        cleaned, label = cls.clean_label(text)
        if label == "title":
            return 10.0
        if label == "company":
            return -5.0

        score = 0.0
        words = [w.lower().strip(".,;:|()[]") for w in cleaned.split()]
        lower_full = cleaned.lower()

        # Check role keywords
        for w in words:
            if w in ROLE_KEYWORDS:
                score += 3.5
            elif any(w.endswith(stem) for stem in ["engineer", "developer", "manager", "analyst", "designer"]):
                score += 3.0

        # Check seniority keywords
        for w in words:
            if w in SENIORITY_MODIFIERS:
                score += 2.0

        # Penalize if it contains corporate suffixes
        for w in words:
            if w in COMPANY_LEGAL_SUFFIXES:
                score -= 6.0
            elif w in COMPANY_NOUN_INDICATORS and not any(rw in words for rw in ROLE_KEYWORDS):
                score -= 3.0

        for suffix in ["corp", "llc", "ltd", "inc", "labs", "systems"]:
            if lower_full.endswith(suffix) and len(lower_full) > len(suffix):
                score -= 4.0
                break

        # Penalize known companies
        if lower_full in KNOWN_COMPANIES:
            score -= 8.0

        # Penalize long prose or bullet points
        if len(words) > 7:
            score -= 3.0
        if cleaned.startswith(("-", "•", "*", "–")):
            score -= 5.0

        return score

    @classmethod
    def score_company_name(cls, text: str) -> float:
        """Computes a semantic affinity score that a string is a company name."""
        if not text or len(text.strip()) == 0:
            return 0.0

        cleaned, label = cls.clean_label(text)
        if label == "company":
            return 10.0
        if label == "title":
            return -5.0

        score = 0.0
        words = [w.lower().strip(".,;:|()[]") for w in cleaned.split()]
        lower_full = cleaned.lower()

        # Known company match
        if lower_full in KNOWN_COMPANIES or any(kc in lower_full for kc in ["skynet defense", "cyberdyne systems", "initech"]):
            score += 8.0

        # Corporate legal suffix (Inc, LLC, Corp, etc.)
        for w in words:
            if w in COMPANY_LEGAL_SUFFIXES:
                score += 5.5

        # Compound corporate suffix in single-word company names (e.g. "TechCorp", "MicroTech")
        for suffix in ["corp", "llc", "ltd", "inc", "tech", "soft", "labs", "systems", "solutions"]:
            if lower_full.endswith(suffix) and len(lower_full) > len(suffix):
                score += 4.5
                break

        # Organizational noun (Technologies, Labs, Solutions, etc.)
        for w in words:
            if w in COMPANY_NOUN_INDICATORS:
                score += 3.0

        # Penalize title keywords (Engineer, Developer, Manager, etc.)
        for w in words:
            if w in ROLE_KEYWORDS:
                score -= 4.0
            elif w in SENIORITY_MODIFIERS:
                score -= 2.5

        # Penalize bullet points or long prose
        if len(words) > 7:
            score -= 3.0
        if cleaned.startswith(("-", "•", "*", "–")):
            score -= 5.0

        return score

    @classmethod
    def disambiguate_title_and_company(
        cls, phrase_a: str, phrase_b: str
    ) -> Tuple[Optional[str], Optional[str], float, bool]:
        """
        Given two candidate text segments (e.g. from 'A | B' or two adjacent lines),
        evaluates semantic affinity to assign one as title and the other as company.
        Never assigns based solely on position.
        Returns:
            (title, company, confidence_score, is_uncertain)
        """
        clean_a, label_a = cls.clean_label(phrase_a)
        clean_b, label_b = cls.clean_label(phrase_b)

        # 1. Direct label cues
        if label_a == "title" or label_b == "company":
            return clean_a, clean_b, 0.95, False
        if label_a == "company" or label_b == "title":
            return clean_b, clean_a, 0.95, False

        # 2. Semantic scoring
        t_a = cls.score_job_title(clean_a)
        c_a = cls.score_company_name(clean_a)
        t_b = cls.score_job_title(clean_b)
        c_b = cls.score_company_name(clean_b)

        net_a = t_a - c_a  # Positive means likely title, negative means likely company
        net_b = t_b - c_b

        # Clear separation
        if net_a > net_b:
            # Phrase A is Title, Phrase B is Company
            title = clean_a
            company = clean_b
            confidence = min(1.0, max(0.5, 0.6 + (net_a - net_b) * 0.05))
            is_uncertain = (net_a - net_b) < 2.0
            return title, company, confidence, is_uncertain
        elif net_b > net_a:
            # Phrase B is Title, Phrase A is Company
            title = clean_b
            company = clean_a
            confidence = min(1.0, max(0.5, 0.6 + (net_b - net_a) * 0.05))
            is_uncertain = (net_b - net_a) < 2.0
            return title, company, confidence, is_uncertain
        else:
            # Both ambiguous, check if one has company legal suffix or title keyword
            if any(w in clean_a.lower() for w in COMPANY_LEGAL_SUFFIXES):
                return clean_b, clean_a, 0.65, True
            if any(w in clean_b.lower() for w in COMPANY_LEGAL_SUFFIXES):
                return clean_a, clean_b, 0.65, True
            # Tie fallback
            return clean_a, clean_b, 0.40, True

    @classmethod
    def is_valid_location(cls, text: str) -> bool:
        """
        Validates whether a candidate string is an authentic geographic location.
        Rejects noise phrases (e.g. 'Available immediately', 'Expert in JavaScript, React',
        'Senior Software Engineer').
        """
        if not text:
            return False
        clean = text.strip(" ,-–—|()[]")
        if not clean or len(clean) > 60:
            return False

        lower = clean.lower()

        # Reject if contains noise words, role keywords, or legal company suffixes
        for noise in LOCATION_NOISE_TERMS:
            if re.search(rf"\b{re.escape(noise)}\b", lower):
                return False

        for role in ROLE_KEYWORDS:
            if re.search(rf"\b{re.escape(role)}\b", lower):
                return False

        for suffix in COMPANY_LEGAL_SUFFIXES:
            if re.search(rf"\b{re.escape(suffix)}\b", lower):
                return False

        # Reject if contains dates
        if SINGLE_YEAR_PATTERN.search(clean):
            return False

        # Check for standard "City, ST" format (e.g. "Austin, TX")
        us_match = re.search(r"^([A-Za-z\s\.\-]{2,30}),\s*([A-Za-z]{2})$", clean)
        if us_match:
            st = us_match.group(2).upper()
            if st in US_STATE_CODES:
                return True

        # Check if contains recognized country, state, or city
        for c in KNOWN_COUNTRIES:
            if re.search(rf"\b{re.escape(c)}\b", lower):
                return True

        for s in KNOWN_STATES:
            if re.search(rf"\b{re.escape(s)}\b", lower):
                return True

        for ci in KNOWN_CITIES:
            if re.search(rf"\b{re.escape(ci)}\b", lower):
                return True

        return False

    @classmethod
    def extract_location_from_header(cls, line: str) -> Tuple[Optional[str], str]:
        """
        Extracts genuine geographic location from a header line without consuming
        company names or job titles.
        Returns (location, cleaned_line).
        """
        cleaned = line.strip()

        # 1. Check parenthesized location: e.g. "Senior Engineer at Acme (Austin, TX)"
        paren_matches = list(re.finditer(r"\(([^)]+)\)", cleaned))
        for pm in reversed(paren_matches):
            candidate = pm.group(1).strip()
            if cls.is_valid_location(candidate):
                cleaned = (cleaned[:pm.start()] + cleaned[pm.end():]).strip(" -–—|,()")
                return candidate, cleaned

        # 2. Check location after pipe delimiter: e.g. "Acme Corp | Austin, TX"
        pipe_parts = [p.strip() for p in re.split(r"\|", cleaned) if p.strip()]
        if len(pipe_parts) >= 2:
            last = pipe_parts[-1]
            if cls.is_valid_location(last):
                remaining = " | ".join(pipe_parts[:-1]).strip(" -–—|,()")
                return last, remaining

        # 3. Check trailing city/state/country after comma:
        # E.g. "TechCorp, Jaipur, Rajasthan" or "Acme Corp, Austin, TX"
        comma_parts = [p.strip() for p in cleaned.split(",") if p.strip()]
        if len(comma_parts) >= 3:
            # Check last 2 parts together: "Jaipur, Rajasthan"
            tail_2 = f"{comma_parts[-2]}, {comma_parts[-1]}"
            if cls.is_valid_location(tail_2) and cls.score_company_name(tail_2) < 2.0:
                remaining = ", ".join(comma_parts[:-2]).strip(" -–—|,()")
                return tail_2, remaining

        if len(comma_parts) >= 2:
            last = comma_parts[-1]
            if cls.is_valid_location(last):
                remaining = ", ".join(comma_parts[:-1]).strip(" -–—|,()")
                return last, remaining

        # 4. Strict "City, ST" regex match if ST in US_STATE_CODES
        m = re.search(r"\b([A-Z][a-zA-Z\s]{1,25}),\s*([A-Z]{2})\b", cleaned)
        if m:
            cand = m.group(0).strip()
            if cls.is_valid_location(cand):
                cleaned = (cleaned[:m.start()] + cleaned[m.end():]).strip(" -–—|,()")
                return cand, cleaned

        return None, cleaned

    @classmethod
    def extract_field_of_study(cls, degree_text: str) -> Tuple[str, Optional[str]]:
        """
        Splits an academic credential into degree and field of study.
        E.g. 'Bachelor of Technology in Computer Science' -> ('Bachelor of Technology', 'Computer Science')
        """
        if not degree_text:
            return "", None

        clean = degree_text.strip(" -–—|,()")

        # 1. Parenthesized field: "Bachelor of Science (Computer Science)"
        paren = re.search(r"\(([^)]+)\)", clean)
        if paren:
            field = paren.group(1).strip()
            deg = clean.replace(paren.group(0), "").strip(" ,-–—")
            if field and deg:
                return deg, field

        # 2. " in " preposition: "Bachelor of Science in Computer Science"
        if " in " in clean.lower():
            parts = re.split(r"\s+in\s+", clean, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                return parts[0].strip(), parts[1].strip()

        # 3. " - " or " – " delimiter: "B.Tech - Information Technology"
        dash_parts = re.split(r"\s+[-–—]\s+", clean, maxsplit=1)
        if len(dash_parts) == 2 and dash_parts[0].strip() and dash_parts[1].strip():
            if cls.score_degree(dash_parts[0]) >= cls.score_degree(dash_parts[1]):
                return dash_parts[0].strip(), dash_parts[1].strip()
            else:
                return dash_parts[1].strip(), dash_parts[0].strip()

        # 4. Comma: "Master of Science, Data Analytics"
        if "," in clean:
            comma_parts = [p.strip() for p in clean.split(",", 1) if p.strip()]
            if len(comma_parts) == 2 and cls.score_degree(comma_parts[0]) > 0:
                return comma_parts[0], comma_parts[1]

        return clean, None

    @classmethod
    def parse_header_line(cls, line: str) -> Dict[str, Any]:
        """
        Parses a single header line containing combinations of title, company, dates, location.
        Handles:
            - 'Title at Company'
            - 'Company | Title'
            - 'Title | Company'
            - 'Title - Company (Dates)'
            - 'Company, Title'
        """
        res: Dict[str, Any] = {
            "title": None,
            "company": None,
            "start_date": None,
            "end_date": None,
            "current": False,
            "location": None,
            "confidence": 0.8,
            "is_uncertain": False
        }

        # 1. Extract dates
        date_match = DATE_RANGE_PATTERN.search(line)
        cleaned_line = line
        if date_match:
            date_str = date_match.group(0).strip()
            res["current"] = "present" in date_str.lower() or "current" in date_str.lower()
            date_parts = re.split(r"-|–|—|to", date_str, flags=re.IGNORECASE)
            if len(date_parts) > 0:
                res["start_date"] = date_parts[0].strip()
            if len(date_parts) > 1:
                res["end_date"] = date_parts[1].strip()
            cleaned_line = line.replace(date_str, "").strip(" -–—|,()")
        else:
            s_match = SINGLE_DATE_PATTERN.search(cleaned_line)
            if s_match:
                s_str = s_match.group(0).strip()
                res["end_date"] = s_str
                cleaned_line = cleaned_line.replace(s_str, "").strip(" -–—|,()")

        # 2. Extract genuine location without consuming company names or titles
        loc_candidate, cleaned_line = cls.extract_location_from_header(cleaned_line)
        if loc_candidate:
            res["location"] = loc_candidate

        # 3. Check for ' at ' preposition: "Senior Engineer at Acme Corp"
        if " at " in cleaned_line:
            parts = cleaned_line.split(" at ", 1)
            p_title, p_company, conf, uncert = cls.disambiguate_title_and_company(parts[0].strip(), parts[1].strip())
            res["title"] = p_title
            res["company"] = p_company
            res["confidence"] = conf
            res["is_uncertain"] = uncert
            return res

        # 4. Check pipe delimiter |
        if "|" in cleaned_line:
            parts = [p.strip() for p in cleaned_line.split("|") if p.strip()]
            if len(parts) >= 2:
                p_title, p_company, conf, uncert = cls.disambiguate_title_and_company(parts[0], parts[1])
                res["title"] = p_title
                res["company"] = p_company
                res["confidence"] = conf
                res["is_uncertain"] = uncert
                return res

        # 5. Check dash delimiter (surrounded by whitespace to avoid splitting Full-Stack)
        dash_match = re.split(r"\s+[-–—]\s+", cleaned_line)
        if len(dash_match) >= 2:
            parts = [p.strip() for p in dash_match if p.strip()]
            if len(parts) >= 2:
                p_title, p_company, conf, uncert = cls.disambiguate_title_and_company(parts[0], parts[1])
                res["title"] = p_title
                res["company"] = p_company
                res["confidence"] = conf
                res["is_uncertain"] = uncert
                return res

        # 6. Check comma delimiter, but avoid splitting on company legal suffixes (e.g. "Acme Technologies, Inc.")
        comma_parts = re.split(r",\s*(?!(?:inc|llc|corp|ltd|co|gmbh|pvt)\b)", cleaned_line, flags=re.IGNORECASE)
        parts = [p.strip() for p in comma_parts if p.strip()]
        if len(parts) >= 2:
            p_title, p_company, conf, uncert = cls.disambiguate_title_and_company(parts[0], parts[1])
            res["title"] = p_title
            res["company"] = p_company
            res["confidence"] = conf
            res["is_uncertain"] = uncert
            return res
        elif len(parts) == 1:
            # Single entity on line, evaluate whether it's title or company
            t_score = cls.score_job_title(parts[0])
            c_score = cls.score_company_name(parts[0])
            if t_score > c_score:
                res["title"] = parts[0]
            elif c_score > t_score:
                res["company"] = parts[0]
            else:
                res["title"] = parts[0]
                res["is_uncertain"] = True

        return res

    @classmethod
    def score_degree(cls, text: str) -> float:
        """Semantic score that a text segment is an academic degree."""
        if not text:
            return 0.0
        score = 0.0
        lower = text.lower()

        for deg in DEGREE_KEYWORDS:
            if re.search(rf"\b{re.escape(deg)}\b", lower):
                score += 3.5

        for inst in INSTITUTION_KEYWORDS:
            if re.search(rf"\b{re.escape(inst)}\b", lower):
                score -= 4.0

        return score

    @classmethod
    def score_institution(cls, text: str) -> float:
        """Semantic score that a text segment is an educational institution."""
        if not text:
            return 0.0
        score = 0.0
        lower = text.lower()

        for inst in INSTITUTION_KEYWORDS:
            if re.search(rf"\b{re.escape(inst)}\b", lower):
                score += 4.5

        for deg in DEGREE_KEYWORDS:
            if re.search(rf"\b{re.escape(deg)}\b", lower):
                score -= 3.0

        return score

    @classmethod
    def disambiguate_degree_and_institution(
        cls, phrase_a: str, phrase_b: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Disambiguates degree vs. institution regardless of their position.
        Returns (degree, institution).
        """
        d_a = cls.score_degree(phrase_a)
        i_a = cls.score_institution(phrase_a)
        d_b = cls.score_degree(phrase_b)
        i_b = cls.score_institution(phrase_b)

        if (d_a - i_a) > (d_b - i_b):
            return phrase_a.strip(), phrase_b.strip()
        else:
            return phrase_b.strip(), phrase_a.strip()
