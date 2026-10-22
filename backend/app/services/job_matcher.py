import json
import re
from typing import Dict, List, Optional, Set, Tuple
from app.models.job import JobListing
from app.models.profile import UserProfile
from app.schemas.job import JobMatchDetails

COMMON_TECH_WORDS = {
    "python", "javascript", "typescript", "react", "vue", "angular", "node", "nodejs",
    "fastapi", "django", "flask", "docker", "kubernetes", "aws", "azure", "gcp",
    "sql", "postgresql", "mysql", "mongodb", "redis", "git", "ci/cd", "rest", "graphql",
    "java", "spring", "c++", "c#", ".net", "golang", "go", "rust", "php", "ruby",
    "linux", "html", "css", "tailwind", "agile", "scrum", "microservices", "pandas",
    "numpy", "pytorch", "tensorflow", "kafka", "spark", "next.js", "express"
}

NON_TECH_PROFESSIONS = {
    "nurse", "nursing", "medical", "doctor", "physician", "therapist", "dentist", "pharmacist", "pharmacy",
    "driver", "truck", "delivery", "courier", "warehouse", "forklift",
    "plumber", "electrician", "mechanic", "carpenter", "construction", "welder",
    "chef", "cook", "restaurant", "waiter", "barista", "cashier", "retail", "bartender",
    "accountant", "accounting", "tax", "auditor", "audit", "bookkeeper", "banker", "teller",
    "realtor", "real estate", "broker", "paralegal", "attorney", "lawyer", "security guard",
    "cleaning", "janitor", "housekeeping", "teacher", "educator", "tutor"
}

SENIOR_KEYWORDS = {"senior", "lead", "principal", "staff", "architect", "director", "head", "vp", "manager", "chief"}
JUNIOR_KEYWORDS = {"junior", "entry", "associate", "graduate", "intern", "internship", "trainee", "fresher", "apprentice"}
JUNIOR_PROFILE_TERMS = {"student", "intern", "internship", "graduate", "fresher", "entry", "junior", "apprentice", "trainee", "fellow"}

DISCIPLINE_RULES = [
    {
        "id": "design",
        "name": "Design / UI / UX",
        "job_terms": {"designer", "design", "ux", "ui", "product design", "graphic design", "figma", "visual design", "wireframing"},
        "candidate_terms": {"designer", "design", "ux", "ui", "product design", "graphic design", "figma", "visual design"}
    },
    {
        "id": "project_management",
        "name": "Project / Program Management",
        "job_terms": {"project manager", "scrum master", "agile coach", "program manager", "delivery manager", "pmp"},
        "candidate_terms": {"project manager", "scrum master", "agile coach", "program manager", "delivery manager", "pmp"}
    },
    {
        "id": "product_management",
        "name": "Product Management",
        "job_terms": {"product manager", "head of product", "vp of product", "group product manager"},
        "candidate_terms": {"product manager", "product owner", "head of product"}
    },
    {
        "id": "sales_marketing",
        "name": "Sales / Marketing / HR",
        "job_terms": {"sales", "marketing", "account executive", "recruiter", "talent acquisition", "human resources", "business development"},
        "candidate_terms": {"sales", "marketing", "account executive", "recruiter", "talent acquisition", "human resources"}
    }
]


class JobMatcher:
    """
    Evaluates genuine relevance between a candidate's verified profile and a job listing.
    Prevents artificial inflation of match scores for unrelated roles or professions.
    Generates plain-language, honest reasons grounded exclusively in verified qualifications.
    """

    @classmethod
    def evaluate(
        cls,
        profile: Optional[UserProfile],
        job: JobListing,
        user_country_preference: Optional[str] = None
    ) -> JobMatchDetails:
        if not profile or not (profile.headline or profile.skills or profile.experiences):
            # Baseline when candidate has not yet uploaded a verified resume
            return JobMatchDetails(
                score=0.0,
                reasons=[
                    "No verified resume uploaded yet.",
                    "Upload and confirm your resume in Step 1 to see personalized skill and title matching!"
                ],
                matched_skills=[],
                unknown_skills=[],
                disclaimer="Match score is 0% until a verified resume is uploaded. Upload your resume to calculate personalized match scores."
            )

        candidate_skills = cls._extract_candidate_skills(profile)
        job_skills = cls._extract_job_skills(job)

        # 1. Skill overlap (Weight: 40%)
        skill_score, matched_skills, unknown_skills, skill_reason = cls._calculate_skills_score(
            candidate_skills, job_skills, job.description
        )

        # 2. Title & Role alignment (Weight: 30%)
        title_score, title_reason = cls._calculate_title_score(
            profile.headline, profile.experiences, job.title,
            candidate_skills=candidate_skills,
            summary=profile.summary
        )

        # 3. Experience & Seniority alignment (Weight: 15%)
        exp_score, exp_reason = cls._calculate_experience_score(
            profile.experiences, job.description, job.title,
            headline=profile.headline,
            summary=profile.summary
        )

        # 4. Location & Remote alignment (Weight: 10%)
        loc_score, loc_reason = cls._calculate_location_score(
            candidate_location=profile.location,
            job_location=job.location,
            job_country=job.country,
            is_remote=job.is_remote,
            user_country_preference=user_country_preference
        )

        # 5. Education alignment (Weight: 5%)
        edu_score, edu_reason = cls._calculate_education_score(
            profile.education, job.description
        )

        # Aggregate weighted score
        total_score = (
            (skill_score * 0.40) +
            (title_score * 0.30) +
            (exp_score * 0.15) +
            (loc_score * 0.10) +
            (edu_score * 0.05)
        )

        # Irrelevance Guardrail:
        # If title has near-zero relevance / different profession, drastically cap the score
        if title_score <= 20.0:
            total_score = min(total_score, 18.0)
        elif len(matched_skills) == 0 and title_score < 50.0:
            total_score = min(total_score, 20.0)

        # Seniority Mismatch Guardrail:
        # Severe seniority gap (e.g. junior applying to senior/staff/principal role):
        if exp_score <= 15.0:
            total_score = min(total_score, 18.0)
        elif exp_score <= 25.0:
            total_score = min(total_score, 24.0)

        # Country Mismatch Guardrail:
        if loc_score == 0.0:
            total_score = min(total_score, 10.0)

        total_score = round(max(5.0, min(99.0, total_score)), 1)

        # Compile honest, concise reasons
        reasons: List[str] = []
        if skill_reason:
            reasons.append(skill_reason)
        if title_reason:
            reasons.append(title_reason)
        if exp_reason:
            reasons.append(exp_reason)
        if loc_reason and loc_score >= 70.0:
            reasons.append(loc_reason)
        if edu_reason:
            reasons.append(edu_reason)

        if not reasons:
            if total_score < 30.0:
                reasons.append("Low relevance: Key skills and job title do not align with your target profile.")
            else:
                reasons.append("Matches your general technical background and location parameters.")

        return JobMatchDetails(
            score=total_score,
            reasons=reasons,
            matched_skills=matched_skills[:8],
            unknown_skills=unknown_skills[:6],
            disclaimer="Heuristic relevance score computed from verified resume attributes and job posting requirements."
        )

    @classmethod
    def _extract_candidate_skills(cls, profile: UserProfile) -> Set[str]:
        skills = set()
        raw_skills = json.loads(profile.skills or "[]")
        for s in raw_skills:
            if s and isinstance(s, str):
                skills.add(s.strip().lower())

        text_corpus = f"{profile.headline or ''} {profile.summary or ''}".lower()
        for tech in COMMON_TECH_WORDS:
            if re.search(rf"\b{re.escape(tech)}\b", text_corpus):
                skills.add(tech)

        return skills

    @classmethod
    def _extract_job_skills(cls, job: JobListing) -> Set[str]:
        skills = set()
        raw_job_skills = json.loads(job.skills_required or "[]")
        for s in raw_job_skills:
            if s and isinstance(s, str):
                skills.add(s.strip().lower())

        text = f"{job.title} {job.description}".lower()
        for tech in COMMON_TECH_WORDS:
            if re.search(rf"\b{re.escape(tech)}\b", text):
                skills.add(tech)

        return skills

    @classmethod
    def _calculate_skills_score(
        cls,
        candidate_skills: Set[str],
        job_skills: Set[str],
        job_description: str
    ) -> Tuple[float, List[str], List[str], Optional[str]]:
        if not candidate_skills and not job_skills:
            return 30.0, [], [], None

        matched: Set[str] = set()
        unknown: Set[str] = set()

        if job_skills:
            for js in job_skills:
                if js in candidate_skills:
                    matched.add(js.title())
                else:
                    unknown.add(js.title())

            if len(matched) == 0:
                score = 10.0
            else:
                ratio = len(matched) / max(len(job_skills), 1)
                score = 35.0 + (ratio * 65.0)
        else:
            desc_lower = job_description.lower()
            for cs in candidate_skills:
                if re.search(rf"\b{re.escape(cs)}\b", desc_lower):
                    matched.add(cs.title())

            if matched:
                score = min(95.0, 35.0 + (len(matched) * 15.0))
            else:
                score = 15.0

        score = min(100.0, max(5.0, score))
        matched_list = sorted(list(matched))
        unknown_list = sorted(list(unknown))

        reason = None
        if matched_list:
            count = len(matched_list)
            top_skills = ", ".join(matched_list[:4])
            if count == 1:
                reason = f"Direct match for 1 verified skill: {top_skills}."
            else:
                reason = f"Direct match for {count} verified skills: {top_skills}."
        elif unknown_list and len(unknown_list) > 0:
            missing_preview = ", ".join(unknown_list[:3])
            reason = f"Posting specifies skills not listed on your resume: {missing_preview}."

        return score, matched_list, unknown_list, reason

    @classmethod
    def _detect_candidate_seniority(
        cls,
        experiences_json: Optional[str],
        headline: Optional[str] = None,
        summary: Optional[str] = None
    ) -> str:
        """
        Detects candidate career stage: 'junior' (entry/intern/student), 'senior', or 'mid'.
        """
        context_text = f"{headline or ''} {summary or ''}".lower()

        # Explicit student/intern/junior keywords in headline or summary
        if any(re.search(rf"\b{re.escape(term)}\b", context_text) for term in JUNIOR_PROFILE_TERMS):
            return "junior"

        try:
            exps = json.loads(experiences_json or "[]")
        except Exception:
            exps = []

        total_jobs = len(exps)
        if total_jobs == 0:
            return "junior"

        exp_titles = [(e.get("title") or "").lower() for e in exps]

        # If all experience titles contain junior/intern terms
        all_interns = all(any(re.search(rf"\b{re.escape(term)}\b", t) for term in JUNIOR_PROFILE_TERMS) for t in exp_titles if t)
        if all_interns and exp_titles:
            return "junior"

        # Check for senior indicators in experience titles
        has_senior = any(any(re.search(rf"\b{re.escape(k)}\b", t) for k in SENIOR_KEYWORDS) for t in exp_titles)
        if (has_senior or total_jobs >= 5) and not any(re.search(rf"\b{re.escape(term)}\b", context_text) for term in JUNIOR_PROFILE_TERMS):
            return "senior"

        if total_jobs <= 1:
            return "junior"

        return "mid"

    @classmethod
    def _calculate_title_score(
        cls,
        headline: Optional[str],
        experiences_json: Optional[str],
        job_title: str,
        candidate_skills: Optional[Set[str]] = None,
        summary: Optional[str] = None
    ) -> Tuple[float, Optional[str]]:
        candidate_titles = []
        if headline:
            candidate_titles.append(headline.lower())

        try:
            exps = json.loads(experiences_json or "[]")
            for e in exps:
                t = e.get("title")
                if t:
                    candidate_titles.append(t.lower())
        except Exception:
            pass

        if not candidate_titles:
            return 40.0, None

        job_title_lower = job_title.lower()
        cand_seniority = cls._detect_candidate_seniority(experiences_json, headline, summary)

        # 1. Check Discipline Incompatibility (e.g. Software/AI Candidate vs Product Designer / Project Manager)
        cand_corpus = f"{' '.join(candidate_titles)} {' '.join(candidate_skills or set())}".lower()
        for rule in DISCIPLINE_RULES:
            job_matches_rule = any(re.search(rf"\b{re.escape(jt)}\b", job_title_lower) for jt in rule["job_terms"])
            if job_matches_rule:
                cand_matches_rule = any(re.search(rf"\b{re.escape(ct)}\b", cand_corpus) for ct in rule["candidate_terms"])
                if not cand_matches_rule:
                    return 10.0, f"Role ({job_title}) is in {rule['name']}, which is distinct from your technical profile."

        stopwords = {"a", "an", "the", "and", "or", "in", "at", "for", "with", "of", "to", "on", "by"}
        job_tokens = set(re.findall(r"\w+", job_title_lower)) - stopwords

        # 2. Check Non-Tech Profession
        if any(np in job_tokens for np in NON_TECH_PROFESSIONS):
            cand_tokens_all = set()
            for ct in candidate_titles:
                cand_tokens_all.update(re.findall(r"\w+", ct))
            if not any(np in cand_tokens_all for np in NON_TECH_PROFESSIONS):
                return 10.0, f"Role ({job_title}) is in a different profession from your profile."

        # Seniority status of job title
        job_is_exec = any(re.search(rf"\b{re.escape(k)}\b", job_title_lower) for k in ["staff", "principal", "director", "head", "vp", "chief"])
        job_is_senior = job_is_exec or any(re.search(rf"\b{re.escape(k)}\b", job_title_lower) for k in ["senior", "lead", "sr", "sr."])

        best_score = 15.0
        best_matching_title = None

        for ct in candidate_titles:
            cand_tokens = set(re.findall(r"\w+", ct)) - stopwords
            if not cand_tokens:
                continue

            intersection = job_tokens.intersection(cand_tokens)
            meaningful_intersection = intersection - SENIOR_KEYWORDS - JUNIOR_KEYWORDS
            if meaningful_intersection:
                jaccard = len(meaningful_intersection) / len(job_tokens.union(cand_tokens))
                score = 40.0 + (jaccard * 60.0)
                if score > best_score:
                    best_score = score
                    best_matching_title = ct

        # Check tech role affinity: e.g. "Software Engineer" vs "Python Developer"
        tech_roles = {"engineer", "developer", "programmer", "fullstack", "backend", "frontend", "web", "software"}
        cand_has_tech = any(any(tr in ct for tr in tech_roles) for ct in candidate_titles)
        job_has_tech = any(tr in job_tokens for tr in tech_roles)

        if cand_has_tech and job_has_tech and best_score < 50.0:
            best_score = 65.0
            reason = f"Role ({job_title}) aligns with your technical development background."
        elif best_score >= 70.0 and best_matching_title:
            reason = f"Strong title alignment ({job_title}) matching your experience as {best_matching_title.title()}."
        elif best_score >= 50.0:
            reason = f"Title ({job_title}) is in your target career category."
        else:
            reason = None

        # Apply Junior Seniority Barrier on Title
        if cand_seniority == "junior" and job_is_exec:
            best_score = min(best_score, 15.0)
            reason = f"Seniority barrier: Role ({job_title}) requires extensive leadership tenure beyond entry-level/student status."
        elif cand_seniority == "junior" and job_is_senior:
            best_score = min(best_score, 25.0)
            reason = f"Seniority barrier: Role ({job_title}) is targeted at senior professionals with advanced track record."

        return best_score, reason

    @classmethod
    def _calculate_experience_score(
        cls,
        experiences_json: Optional[str],
        job_description: str,
        job_title: str,
        headline: Optional[str] = None,
        summary: Optional[str] = None
    ) -> Tuple[float, Optional[str]]:
        try:
            exps = json.loads(experiences_json or "[]")
        except Exception:
            exps = []

        total_jobs = len(exps)
        combined_text = (job_title + " " + job_description).lower()
        job_title_lower = job_title.lower()

        job_is_exec = any(re.search(rf"\b{re.escape(k)}\b", job_title_lower) for k in ["staff", "principal", "director", "head", "vp", "chief", "architect"])
        job_is_senior = job_is_exec or any(re.search(rf"\b{re.escape(k)}\b", combined_text) for k in SENIOR_KEYWORDS) or "10+ years" in combined_text or "8+ years" in combined_text
        job_is_junior = any(re.search(rf"\b{re.escape(k)}\b", combined_text) for k in JUNIOR_KEYWORDS) or "entry level" in combined_text or "intern" in job_title_lower

        cand_level = cls._detect_candidate_seniority(experiences_json, headline, summary)

        score = 65.0
        reason = None

        if cand_level == "junior" and job_is_exec:
            score = 10.0
            reason = f"Seniority barrier: Executive/staff role ({job_title}) requires industry tenure beyond your student profile stage."
        elif cand_level == "junior" and job_is_senior:
            score = 15.0
            reason = f"Seniority mismatch: Role ({job_title}) specifies senior requirements beyond your current career stage."
        elif cand_level == "senior" and job_is_junior:
            score = 40.0
            reason = "Seniority mismatch: Role is introductory / entry-level."
        elif cand_level == "senior" and job_is_senior:
            score = 90.0
            reason = "Seniority match: Your leadership background meets the position requirements."
        elif cand_level == "junior" and job_is_junior:
            score = 90.0
            reason = "Experience stage match: Introductory requirements align with your current background."
        elif cand_level == "junior":
            score = 65.0
            reason = "General engineering position compatible with developing professional skills."
        elif total_jobs > 0:
            score = 75.0
            reason = "Your demonstrated work history aligns with core responsibilities."
        else:
            score = 55.0
            reason = None

        return score, reason

    @classmethod
    def _calculate_location_score(
        cls,
        candidate_location: Optional[str],
        job_location: str,
        job_country: Optional[str],
        is_remote: bool,
        user_country_preference: Optional[str]
    ) -> Tuple[float, Optional[str]]:
        loc_clean = (job_location or "").lower()
        cand_clean = (candidate_location or "").lower()
        pref_country = (user_country_preference or "").upper()

        # Strict foreign rejection
        if pref_country == "IN":
            from app.core.locations import is_location_in_europe, is_location_in_north_america
            if is_location_in_europe(loc_clean) or is_location_in_north_america(loc_clean):
                return 0.0, None

        score = 60.0
        reason = None

        if is_remote and any(w in loc_clean for w in ["worldwide", "anywhere", "global"]):
            score = 80.0
            reason = "Work mode matches: 100% Worldwide Remote."
        elif candidate_location and any(part.strip() in loc_clean for part in cand_clean.split(",") if len(part.strip()) > 2):
            score = 95.0
            reason = f"Location match: Role is situated in your city ({candidate_location})."
        elif pref_country and (job_country == pref_country or pref_country.lower() in loc_clean):
            score = 80.0
            from app.core.locations import SUPPORTED_COUNTRIES
            c_name = SUPPORTED_COUNTRIES.get(pref_country, {}).get("name", pref_country)
            reason = f"Location match: Position is based in your target country ({c_name})."

        return score, reason

    @classmethod
    def _calculate_education_score(
        cls,
        education_json: Optional[str],
        job_description: str
    ) -> Tuple[float, Optional[str]]:
        try:
            edu_items = json.loads(education_json or "[]")
        except Exception:
            edu_items = []

        desc_lower = job_description.lower()
        requires_degree = any(d in desc_lower for d in ["bachelor", "degree", "bs", "ba", "ms", "phd", "university"])

        if not requires_degree:
            return 80.0, None

        if edu_items and len(edu_items) > 0:
            deg = edu_items[0].get("degree") or "Degree"
            return 90.0, f"Education qualification met ({deg})."

        return 50.0, None
