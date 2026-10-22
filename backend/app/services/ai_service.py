import asyncio
import json
import logging
import random
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
import httpx
from app.core.config import settings
from app.schemas.profile import (
    EducationItem,
    ExperienceItem,
    ParsedResumeProfile,
    ProjectItem,
)
from app.services.semantic_classifier import (
    ResumeSemanticClassifier,
    DATE_RANGE_PATTERN,
    SINGLE_DATE_PATTERN,
    SINGLE_YEAR_PATTERN,
    SECTION_HEADER_TERMS,
    ROLE_KEYWORDS,
    US_STATE_CODES,
)

logger = logging.getLogger(__name__)

# Common industry skills database for heuristic matching
COMMON_SKILLS = [
    "Python", "JavaScript", "TypeScript", "React", "Next.js", "Vue.js", "Angular",
    "Node.js", "Express", "FastAPI", "Django", "Flask", "Ruby on Rails", "Java", "Spring Boot",
    "C", "C++", "C#", ".NET", "Go", "Golang", "Rust", "PHP", "Laravel", "Swift", "Kotlin",
    "SQL", "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Elasticsearch", "Cassandra",
    "Docker", "Kubernetes", "AWS", "Amazon Web Services", "Azure", "GCP", "Google Cloud",
    "Terraform", "CI/CD", "GitHub Actions", "GitLab CI", "Jenkins", "Git", "Linux",
    "HTML", "CSS", "Tailwind CSS", "Bootstrap", "Sass", "REST APIs", "GraphQL", "gRPC",
    "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "Scikit-Learn", "Pandas",
    "NumPy", "NLP", "Computer Vision", "LLMs", "Generative AI", "LangChain",
    "Agile", "Scrum", "Jira", "Project Management", "Team Leadership", "Data Analysis",
    "Unit Testing", "Jest", "PyTest", "Cypress", "Selenium", "Microservices"
]


class BaseAIService(ABC):
    @abstractmethod
    async def parse_resume_text(self, raw_text: str) -> ParsedResumeProfile:
        pass


class LocalHeuristicAIService(BaseAIService):
    """
    100% Offline, deterministic heuristic & regex parser.
    Uses ResumeSemanticClassifier to separate titles and companies by semantics,
    never by arbitrary line order or position.
    Never invents missing qualifications or experience.
    """

    async def parse_resume_text(self, raw_text: str) -> ParsedResumeProfile:
        return self.parse_text_sync(raw_text)

    def parse_text_sync(self, raw_text: str) -> ParsedResumeProfile:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        confidence_scores: Dict[str, float] = {}
        uncertain_fields: List[str] = []
        field_evidence: Dict[str, str] = {}

        # 1. Contact Info & Identity
        email, email_evidence = self._extract_email(raw_text)
        if email:
            confidence_scores["email"] = 0.99
            field_evidence["email"] = email_evidence or email

        phone, phone_evidence = self._extract_phone(raw_text)
        if phone:
            confidence_scores["phone"] = 0.92
            field_evidence["phone"] = phone_evidence or phone

        linkedin_url = self._extract_linkedin(raw_text)
        github_url = self._extract_github(raw_text)
        portfolio_url = self._extract_portfolio(raw_text, linkedin_url, github_url)

        full_name, name_evidence, name_conf = self._extract_name(lines, email)
        if full_name:
            confidence_scores["full_name"] = name_conf
            field_evidence["full_name"] = name_evidence or full_name

        location = self._extract_location(lines[:10])
        skills = self._extract_skills(raw_text)
        if skills:
            confidence_scores["skills"] = 0.90

        # 2. Section Parsing
        sections = self._split_into_sections(raw_text)

        summary = self._extract_summary(sections)
        headline = self._extract_headline(lines, summary)

        experiences, exp_conf, exp_uncertain, exp_evidence = self._extract_experiences(
            sections.get("EXPERIENCE", "")
        )
        confidence_scores.update(exp_conf)
        uncertain_fields.extend(exp_uncertain)
        field_evidence.update(exp_evidence)

        education, edu_conf, edu_uncertain, edu_evidence = self._extract_education(
            sections.get("EDUCATION", "")
        )
        confidence_scores.update(edu_conf)
        uncertain_fields.extend(edu_uncertain)
        field_evidence.update(edu_evidence)

        projects = self._extract_projects(sections.get("PROJECTS", ""))

        # 3. Missing Fields Calculation
        missing_fields = []
        if not full_name:
            missing_fields.append("full_name")
        if not email:
            missing_fields.append("email")
        if not phone:
            missing_fields.append("phone")
        if not headline and not summary:
            missing_fields.append("headline")
        if not skills:
            missing_fields.append("skills")
        if not experiences:
            missing_fields.append("experiences")
        if not education:
            missing_fields.append("education")

        return ParsedResumeProfile(
            full_name=full_name,
            email=email,
            phone=phone,
            location=location,
            headline=headline,
            summary=summary,
            linkedin_url=linkedin_url,
            github_url=github_url,
            portfolio_url=portfolio_url,
            skills=skills,
            experiences=experiences,
            education=education,
            projects=projects,
            missing_fields=missing_fields,
            confidence_scores=confidence_scores,
            uncertain_fields=uncertain_fields,
            field_evidence=field_evidence,
            parser_source="heuristic",
            raw_extracted_text=raw_text
        )

    def _extract_email(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
        if match:
            return match.group(0), match.group(0)
        return None, None

    def _extract_phone(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
        if match:
            clean = match.group(0).strip(".,;:- ")
            return clean, match.group(0)
        return None, None

    def _extract_linkedin(self, text: str) -> Optional[str]:
        match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)/?", text, re.IGNORECASE)
        if match:
            return f"https://linkedin.com/in/{match.group(1)}"
        return None

    def _extract_github(self, text: str) -> Optional[str]:
        match = re.search(r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_-]+)/?", text, re.IGNORECASE)
        if match:
            username = match.group(1).lower()
            if username not in ["orgs", "topics", "features", "pricing"]:
                return f"https://github.com/{match.group(1)}"
        return None

    def _extract_portfolio(self, text: str, linkedin: Optional[str], github: Optional[str]) -> Optional[str]:
        urls = re.findall(r"https?://(?:www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?", text)
        for url in urls:
            url_clean = url.rstrip(",;.:")
            if linkedin and linkedin in url_clean:
                continue
            if github and github in url_clean:
                continue
            return url_clean
        return None

    def _extract_name(self, lines: List[str], email: Optional[str]) -> Tuple[Optional[str], Optional[str], float]:
        email_parts = set()
        if email:
            uname = email.split("@")[0].lower()
            parts = re.split(r"[\._\-+0-9]+", uname)
            email_parts = {p for p in parts if len(p) >= 2}

        candidates: List[Tuple[str, str, float]] = []

        for line in lines[:8]:
            clean = line.strip()
            if not clean:
                continue

            lower_line = clean.lower()
            normalized_header = re.sub(r"^[\s#\*\-_:>]+", "", lower_line).strip(" :")

            # 1. Strict rejection of section headers (e.g. PROFESSIONAL SUMMARY, WORK EXPERIENCE, etc.)
            if normalized_header in SECTION_HEADER_TERMS or any(
                term == normalized_header for term in SECTION_HEADER_TERMS
            ):
                continue
            if any(term in normalized_header for term in [
                "summary", "objective", "curriculum vitae", "resume", "experience",
                "education", "skills", "projects", "certifications", "contact"
            ]):
                continue

            # 2. Rejection of contact details, web links, emails, numbers
            if "@" in clean or "http" in lower_line or "www." in lower_line or "linkedin" in lower_line or "github" in lower_line:
                continue
            if re.search(r"\d", clean):
                continue

            # 3. Rejection of lines with role keywords (e.g. "Senior Software Engineer")
            line_words = [w.lower().strip(".,;:|()[]") for w in clean.split()]
            if any(w in ROLE_KEYWORDS for w in line_words):
                continue

            # 4. Rejection of geographic locations (e.g. "Austin, TX" or "Jaipur, Rajasthan")
            if ResumeSemanticClassifier.is_valid_location(clean):
                continue

            # 5. Rejection of company names
            if ResumeSemanticClassifier.score_company_name(clean) >= 2.0:
                continue

            # Check words structure: typically 2 to 4 capitalized words (or ALL CAPS name like SARAH CONNOR)
            words = clean.split()
            if 2 <= len(words) <= 4:
                is_valid_casing = all(
                    len(w) >= 1 and (w.isupper() or (len(w) > 1 and w[0].isupper()))
                    for w in words
                )
                if is_valid_casing:
                    cand_name = " ".join(w.capitalize() for w in words)
                    cand_lower_words = [w.lower() for w in words]

                    # If candidate words match email tokens, this is an exact verified match!
                    if email_parts and any(cw in email_parts for cw in cand_lower_words):
                        return cand_name, clean, 1.0

                    candidates.append((cand_name, clean, 0.90))

        if candidates:
            return candidates[0]

        # Fallback to deriving name from email if email has name components
        if email_parts and len(email_parts) >= 2:
            fallback_name = " ".join(p.capitalize() for p in email_parts)
            return fallback_name, email, 0.70

        return None, None, 0.0

    def _extract_location(self, top_lines: List[str]) -> Optional[str]:
        # Scan top 12 lines for location
        for line in top_lines[:12]:
            clean = line.strip()
            if not clean:
                continue

            lower_line = clean.lower()

            # Skip obvious section headers
            if any(term in lower_line for term in ["summary", "experience", "education", "skills"]):
                continue

            # 1. Check explicit label: e.g. "Location: Austin, TX" or "Address: San Francisco, CA"
            label_match = re.search(r"(?i)\b(?:location|address|residence|city)\s*:\s*([^|\n•]+)", clean)
            if label_match:
                cand = label_match.group(1).strip(" ,-–—")
                if ResumeSemanticClassifier.is_valid_location(cand):
                    return cand

            # 2. Check prepositional phrase: e.g. "Relocating to Austin, TX" or "Based in Jaipur, India"
            prep_match = re.search(
                r"(?i)\b(?:relocating to|located in|based in|living in|in)\s+([A-Za-z\s]+,\s*(?:[A-Za-z]{2}|[A-Za-z\s]+))",
                clean
            )
            if prep_match:
                cand = prep_match.group(1).strip(" ,-–—.")
                if ResumeSemanticClassifier.is_valid_location(cand):
                    return cand

            # 3. Check pipe/bullet separated components on contact line:
            # e.g. "sarah@example.com | (310) 555-0199 | Los Angeles, CA"
            parts = [p.strip() for p in re.split(r"[|•·]", clean) if p.strip()]
            for part in parts:
                if ResumeSemanticClassifier.is_valid_location(part):
                    return part

            # 4. Check standard comma-separated City, ST pattern (e.g. "Austin, TX")
            m = re.search(r"\b([A-Z][a-zA-Z\s]{1,25}),\s*([A-Z]{2})\b", clean)
            if m:
                cand = m.group(0).strip()
                if ResumeSemanticClassifier.is_valid_location(cand):
                    return cand

            # 5. Check full line if it's a standalone location (e.g. "Jaipur, Rajasthan, India")
            if ResumeSemanticClassifier.is_valid_location(clean):
                return clean

        return None

    def _extract_skills(self, text: str) -> List[str]:
        matched_skills = set()
        text_lower = f" {text.lower()} "

        for skill in COMMON_SKILLS:
            escaped = re.escape(skill.lower())
            if re.search(rf"\b{escaped}\b", text_lower):
                matched_skills.add(skill)

        sections = self._split_into_sections(text)
        skills_section = sections.get("SKILLS", "")
        if skills_section:
            for item in re.split(r"[,•|\n/]+", skills_section):
                candidate = item.strip()
                if 2 <= len(candidate) <= 30 and not any(char in candidate for char in ["@", "http", ":", "$"]):
                    if len(candidate.split()) <= 3:
                        matched_skills.add(candidate.title())

        return sorted(list(matched_skills))[:30]

    def _split_into_sections(self, text: str) -> Dict[str, str]:
        section_headers = {
            "EXPERIENCE": [
                r"^\s*(?:#{1,3}\s*)?(?:\d+[\.\)]\s*)?(?:WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|EMPLOYMENT\s+HISTORY|WORK\s+HISTORY|EXPERIENCE)\s*:?\s*$"
            ],
            "EDUCATION": [
                r"^\s*(?:#{1,3}\s*)?(?:\d+[\.\)]\s*)?(?:ACADEMIC\s+BACKGROUND|ACADEMIC\s+HISTORY|EDUCATION|QUALIFICATIONS)\s*:?\s*$"
            ],
            "SKILLS": [
                r"^\s*(?:#{1,3}\s*)?(?:\d+[\.\)]\s*)?(?:TECHNICAL\s+SKILLS|CORE\s+COMPETENCIES|TECHNOLOGIES|SKILLS)\s*:?\s*$"
            ],
            "SUMMARY": [
                r"^\s*(?:#{1,3}\s*)?(?:\d+[\.\)]\s*)?(?:PROFESSIONAL\s+SUMMARY|CAREER\s+OBJECTIVE|ABOUT\s+ME|OBJECTIVE|SUMMARY)\s*:?\s*$"
            ],
            "PROJECTS": [
                r"^\s*(?:#{1,3}\s*)?(?:\d+[\.\)]\s*)?(?:PERSONAL\s+PROJECTS|KEY\s+PROJECTS|PROJECTS)\s*:?\s*$"
            ]
        }

        all_header_patterns = []
        for header, patterns in section_headers.items():
            for p in patterns:
                all_header_patterns.append((header, p))

        found_markers = []
        for canonical_name, pattern in all_header_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                found_markers.append((match.start(), canonical_name, match.group(0)))

        found_markers.sort(key=lambda x: x[0])

        sections: Dict[str, str] = {}
        for i, (start_pos, section_name, header_text) in enumerate(found_markers):
            content_start = start_pos + len(header_text)
            content_end = found_markers[i + 1][0] if i + 1 < len(found_markers) else len(text)
            section_content = text[content_start:content_end].strip()
            if section_name not in sections:
                sections[section_name] = section_content
            else:
                sections[section_name] += "\n" + section_content

        return sections

    def _extract_summary(self, sections: Dict[str, str]) -> Optional[str]:
        summary_text = sections.get("SUMMARY", "").strip()
        if summary_text:
            first_para = summary_text.split("\n\n")[0].strip()
            return first_para[:500] if len(first_para) > 20 else None
        return None

    def _extract_headline(self, lines: List[str], summary: Optional[str]) -> Optional[str]:
        for line in lines[1:5]:
            clean = line.strip()
            if any(term in clean.lower() for term in ["engineer", "developer", "manager", "designer", "architect", "lead", "specialist", "analyst"]):
                if len(clean) < 80 and not any(c in clean for c in ["@", "http", "(", ")"]):
                    return clean
        if summary:
            first_sentence = summary.split(".")[0].strip()
            if len(first_sentence) < 60:
                return first_sentence
        return None

    def _extract_experiences(
        self, exp_text: str
    ) -> Tuple[List[ExperienceItem], Dict[str, float], List[str], Dict[str, str]]:
        """
        Extracts work experience entries using semantic classification.
        Disambiguates company names from job titles using section headings,
        surrounding text, labels and structure. Never assigns based on position.
        """
        if not exp_text.strip():
            return [], {}, [], {}

        experiences: List[ExperienceItem] = []
        conf_scores: Dict[str, float] = {}
        uncertain_fields: List[str] = []
        field_evidence: Dict[str, str] = {}

        raw_lines = [l.strip() for l in exp_text.splitlines() if l.strip()]

        # Group lines into experience entry blocks
        blocks: List[List[str]] = []
        current_block: List[str] = []

        for line in raw_lines:
            is_bullet = line.startswith(("-", "•", "*", "–", "—")) or re.match(r"^\d+\.\s+", line) is not None
            has_date = bool(DATE_RANGE_PATTERN.search(line)) or bool(SINGLE_DATE_PATTERN.search(line))
            _, label = ResumeSemanticClassifier.clean_label(line)

            # Determine whether this line signals the start of a new experience block
            if current_block:
                current_has_bullets = any(l.startswith(("-", "•", "*", "–", "—")) for l in current_block)
                current_has_date = any(DATE_RANGE_PATTERN.search(l) or SINGLE_DATE_PATTERN.search(l) for l in current_block)

                if current_has_bullets and not is_bullet:
                    # Previous entry finished its bullet list, new non-bullet line starts new entry
                    blocks.append(current_block)
                    current_block = []
                elif current_has_date and has_date:
                    # Current block already has date, new date line begins next entry
                    blocks.append(current_block)
                    current_block = []
                elif current_has_date and not is_bullet and (
                    ResumeSemanticClassifier.score_job_title(line) > 2.0
                    or ResumeSemanticClassifier.score_company_name(line) > 2.0
                    or " at " in line
                    or "|" in line
                ):
                    # Current block has date and this non-bullet line starts a new job title or company
                    blocks.append(current_block)
                    current_block = []
                elif label in ["company", "title"] and (current_has_date or current_has_bullets):
                    blocks.append(current_block)
                    current_block = []

            current_block.append(line)

        if current_block:
            blocks.append(current_block)

        # Parse each candidate experience block
        for b_idx, block in enumerate(blocks):
            header_lines: List[str] = []
            bullet_lines: List[str] = []

            for l in block:
                is_b = l.startswith(("-", "•", "*", "–", "—")) or re.match(r"^\d+\.\s+", l) is not None
                if is_b or (len(bullet_lines) > 0 and len(l.split()) > 10):
                    bullet_lines.append(l)
                else:
                    if len(bullet_lines) == 0:
                        header_lines.append(l)
                    else:
                        bullet_lines.append(l)

            if not header_lines and bullet_lines:
                header_lines.append(bullet_lines.pop(0).lstrip("-•*–— "))

            # Extract dates, location, title, and company from header lines
            combined_header = " | ".join(header_lines)
            parsed_header = ResumeSemanticClassifier.parse_header_line(combined_header)

            title = parsed_header.get("title")
            company = parsed_header.get("company")
            start_date = parsed_header.get("start_date")
            end_date = parsed_header.get("end_date")
            current = parsed_header.get("current", False)
            location = parsed_header.get("location")
            conf = parsed_header.get("confidence", 0.8)
            is_uncertain = parsed_header.get("is_uncertain", False)

            # If multi-line header, disambiguate across individual header lines
            if len(header_lines) >= 2:
                cleaned_headers = [DATE_RANGE_PATTERN.sub("", h).strip(" -–—|,()") for h in header_lines]
                cleaned_headers = [h for h in cleaned_headers if len(h) > 0]
                if len(cleaned_headers) >= 2:
                    p_title, p_company, d_conf, d_uncert = ResumeSemanticClassifier.disambiguate_title_and_company(
                        cleaned_headers[0], cleaned_headers[1]
                    )
                    # If single-line parse was missing one or had lower confidence, use multi-line disambiguation
                    if not title or not company or conf < 0.7:
                        title = p_title
                        company = p_company
                        conf = d_conf
                        is_uncertain = d_uncert

            # Re-verify and clean up:
            # If title looks strongly like a company and company looks like a title, SWAP them!
            if title and company:
                t_score_title = ResumeSemanticClassifier.score_job_title(title)
                c_score_title = ResumeSemanticClassifier.score_company_name(title)
                t_score_comp = ResumeSemanticClassifier.score_job_title(company)
                c_score_comp = ResumeSemanticClassifier.score_company_name(company)

                if c_score_title > t_score_title and t_score_comp > c_score_comp:
                    logger.info("Semantic classifier detected inverted title/company pair ('%s', '%s'). Swapping.", title, company)
                    title, company = company, title
                    conf = 0.85
                    is_uncertain = False

            description = "\n".join(bullet_lines).strip()

            # Record entry if title or company exists
            if title or company:
                exp_item = ExperienceItem(
                    title=title,
                    company=company,
                    location=location,
                    start_date=start_date,
                    end_date=end_date,
                    current=current,
                    description=description if description else None
                )
                experiences.append(exp_item)

                idx_str = f"experiences[{len(experiences) - 1}]"
                conf_scores[f"{idx_str}.title"] = conf
                conf_scores[f"{idx_str}.company"] = conf
                field_evidence[idx_str] = combined_header

                if is_uncertain or not title or not company:
                    if not title:
                        uncertain_fields.append(f"{idx_str}.title")
                    if not company:
                        uncertain_fields.append(f"{idx_str}.company")
                    if is_uncertain and title and company:
                        uncertain_fields.append(f"{idx_str}.company")

        return experiences[:12], conf_scores, uncertain_fields, field_evidence

    def _extract_education(
        self, edu_text: str
    ) -> Tuple[List[EducationItem], Dict[str, float], List[str], Dict[str, str]]:
        """
        Extracts academic background, disambiguating degree vs. institution.
        Never assigns based solely on position.
        """
        if not edu_text.strip():
            return [], {}, [], {}

        education_items: List[EducationItem] = []
        conf_scores: Dict[str, float] = {}
        uncertain_fields: List[str] = []
        field_evidence: Dict[str, str] = {}

        lines = [line.strip() for line in edu_text.splitlines() if line.strip()]
        blocks: List[List[str]] = []
        curr: List[str] = []

        for line in lines:
            has_year = bool(SINGLE_YEAR_PATTERN.search(line))
            has_deg = ResumeSemanticClassifier.score_degree(line) > 2.0
            has_inst = ResumeSemanticClassifier.score_institution(line) > 2.0

            if curr and (has_deg or has_inst) and any(SINGLE_YEAR_PATTERN.search(l) for l in curr):
                blocks.append(curr)
                curr = []
            elif curr and has_deg and any(ResumeSemanticClassifier.score_degree(l) > 2.0 for l in curr):
                blocks.append(curr)
                curr = []
            elif curr and has_year and len(curr) >= 2:
                curr.append(line)
                blocks.append(curr)
                curr = []
                continue

            curr.append(line)

        if curr:
            blocks.append(curr)

        for b_idx, block in enumerate(blocks):
            combined = " | ".join(block)

            # Graduation year: For date ranges like "2018 - 2022", use the concluding year ("2022")
            all_years = SINGLE_YEAR_PATTERN.findall(combined)
            year = all_years[-1] if all_years else None

            # Remove date patterns from candidate string
            clean_str = DATE_RANGE_PATTERN.sub("", combined)
            clean_str = SINGLE_YEAR_PATTERN.sub("", clean_str).strip(" -–—|,()")
            # Split by pipe, newline, or whitespace-padded dash (avoid breaking on city commas in university names)
            parts = [p.strip() for p in re.split(r"\||\n|\s+[-–—]\s+", clean_str) if p.strip()]
            if len(parts) == 1 and "," in parts[0]:
                comma_split = [p.strip() for p in parts[0].split(",") if p.strip()]
                # If one is degree and one is institution, split them
                if any(ResumeSemanticClassifier.score_degree(p) > 2.0 for p in comma_split) and any(
                    ResumeSemanticClassifier.score_institution(p) > 2.0 for p in comma_split
                ):
                    parts = comma_split

            degree = None
            institution = None
            field_of_study = None

            # Score each candidate part
            scored_parts = []
            for p in parts:
                d_s = ResumeSemanticClassifier.score_degree(p)
                i_s = ResumeSemanticClassifier.score_institution(p)
                scored_parts.append((p, d_s, i_s))

            # Pick best degree part and best institution part
            best_deg_candidate = max(scored_parts, key=lambda x: x[1] - x[2]) if scored_parts else None
            best_inst_candidate = max(scored_parts, key=lambda x: x[2] - x[1]) if scored_parts else None

            if best_deg_candidate and best_deg_candidate[1] > 1.0:
                degree = best_deg_candidate[0]
            if best_inst_candidate and best_inst_candidate[2] > 1.0:
                institution = best_inst_candidate[0]

            # If fallback needed when scores are low:
            if not degree and not institution and len(parts) >= 2:
                degree, institution = ResumeSemanticClassifier.disambiguate_degree_and_institution(parts[0], parts[1])
            elif not degree and not institution and len(parts) == 1:
                if ResumeSemanticClassifier.score_institution(parts[0]) > ResumeSemanticClassifier.score_degree(parts[0]):
                    institution = parts[0]
                else:
                    degree = parts[0]
            elif not institution and len(parts) >= 2 and degree:
                remaining = [p for p in parts if p != degree]
                if remaining:
                    institution = remaining[0]
            elif not degree and len(parts) >= 2 and institution:
                remaining = [p for p in parts if p != institution]
                if remaining:
                    degree = remaining[0]

            # Extract field of study from degree string if present (e.g. "Bachelor of Technology in Computer Science")
            if degree:
                cleaned_deg, extracted_field = ResumeSemanticClassifier.extract_field_of_study(degree)
                degree = cleaned_deg
                if extracted_field:
                    field_of_study = extracted_field

            # If field of study not found yet, check remaining parts
            if not field_of_study:
                for p in parts:
                    if p != degree and p != institution:
                        if ResumeSemanticClassifier.score_institution(p) < 1.0 and ResumeSemanticClassifier.score_degree(p) < 1.0:
                            field_of_study = p
                            break

            if degree or institution:
                edu_item = EducationItem(
                    degree=degree,
                    institution=institution,
                    field_of_study=field_of_study,
                    graduation_year=year
                )
                education_items.append(edu_item)

                idx_str = f"education[{len(education_items) - 1}]"
                conf_scores[idx_str] = 0.90
                field_evidence[idx_str] = combined

                if not degree:
                    uncertain_fields.append(f"{idx_str}.degree")
                if not institution:
                    uncertain_fields.append(f"{idx_str}.institution")

        return education_items[:5], conf_scores, uncertain_fields, field_evidence

    def _extract_projects(self, proj_text: str) -> List[ProjectItem]:
        if not proj_text.strip():
            return []

        projects: List[ProjectItem] = []
        lines = [line.strip() for line in proj_text.splitlines() if line.strip()]
        current_proj: Optional[Dict[str, Any]] = None

        for line in lines:
            if line.startswith(("•", "-", "*", "–")):
                if current_proj:
                    current_desc = current_proj.get("description", "")
                    current_proj["description"] = (current_desc + " " + line.lstrip("•-*– ")).strip()
            elif len(line) < 70 and not line.endswith("."):
                if current_proj and (current_proj.get("name") or current_proj.get("description")):
                    projects.append(ProjectItem(**current_proj))

                url_match = re.search(r"https?://[^\s]+", line)
                clean_name = line
                proj_url = None
                if url_match:
                    proj_url = url_match.group(0).rstrip(".,;)")
                    clean_name = line.replace(proj_url, "").strip(" -–|,()")

                current_proj = {
                    "name": clean_name if clean_name else "Project",
                    "description": "",
                    "url": proj_url,
                    "technologies": []
                }
            elif current_proj:
                current_desc = current_proj.get("description", "")
                current_proj["description"] = (current_desc + " " + line).strip()

        if current_proj and (current_proj.get("name") or current_proj.get("description")):
            projects.append(ProjectItem(**current_proj))

        return projects[:6]


class OpenRouterAIService(BaseAIService):
    """
    AI-powered extraction using OpenRouter API.
    Enforces strict structured schema with post-validation and semantic correction.
    Gracefully and silently falls back to LocalHeuristicAIService on failure.
    Never invents missing qualifications or experience.
    """

    def __init__(self, fallback_service: LocalHeuristicAIService):
        self.fallback = fallback_service
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL
        self.fallback_model = getattr(settings, "OPENROUTER_FALLBACK_MODEL", None)
        self.base_url = settings.OPENROUTER_BASE_URL.rstrip("/")

    async def _call_model_with_retry(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        system_prompt: str,
        raw_text: str,
        model_name: str,
        max_retries: int = 3
    ) -> Optional[dict]:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Parse the following resume text:\n\n{raw_text[:8000]}"}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }

        for attempt in range(max_retries):
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )

                if response.status_code == 200:
                    return response.json()

                # Handle Rate Limit (HTTP 429)
                if response.status_code == 429:
                    retry_after_hdr = response.headers.get("Retry-After")
                    delay = 1.0
                    if retry_after_hdr:
                        try:
                            delay = min(5.0, max(0.5, float(retry_after_hdr)))
                        except ValueError:
                            delay = min(5.0, (1.0 * (2 ** attempt)) + random.uniform(0.1, 0.4))
                    else:
                        delay = min(5.0, (1.0 * (2 ** attempt)) + random.uniform(0.1, 0.4))

                    logger.warning(
                        "OpenRouter model '%s' rate limited (HTTP 429) on attempt %d/%d. Waiting %.2fs before retry.",
                        model_name, attempt + 1, max_retries, delay
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                        continue
                    else:
                        break

                # Handle Server Errors (HTTP 502, 503, 504)
                if response.status_code in [502, 503, 504]:
                    delay = min(4.0, (0.8 * (2 ** attempt)) + random.uniform(0.1, 0.3))
                    logger.warning(
                        "OpenRouter model '%s' returned HTTP %s on attempt %d/%d. Waiting %.2fs before retry.",
                        model_name, response.status_code, attempt + 1, max_retries, delay
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                        continue
                    else:
                        break

                # Non-transient errors (400, 401, 403, 404): Fail fast, do not retry!
                logger.warning(
                    "OpenRouter API returned non-retryable HTTP %s for model '%s'.",
                    response.status_code, model_name
                )
                break

            except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                logger.warning(
                    "OpenRouter connection error for model '%s' (attempt %d/%d): %s",
                    model_name, attempt + 1, max_retries, net_err
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(min(3.0, 1.0 + random.uniform(0.1, 0.3)))
                else:
                    break

        return None

    async def parse_resume_text(self, raw_text: str) -> ParsedResumeProfile:
        if not self.api_key:
            logger.info("OpenRouter API key not configured. Using local heuristic parser.")
            return await self.fallback.parse_resume_text(raw_text)

        system_prompt = (
            "You are a strict, objective, and accurate resume parser.\n"
            "CRITICAL RULES FOR ACCURACY:\n"
            "1. FULL NAME: Extract the candidate's personal name ONLY (e.g. 'Sarah Connor', 'John Doe'). NEVER use section headings like 'PROFESSIONAL SUMMARY', 'CAREER OBJECTIVE', 'RESUME', or job titles like 'SOFTWARE ENGINEER' as the name. If the name is not explicitly in the text, leave it as null.\n"
            "2. LOCATION: Extract the candidate's geographical location ONLY (City, State/Country, e.g. 'San Francisco, CA', 'Jaipur, Rajasthan, India'). NEVER output job availability, relocation phrases, or skills (e.g. 'Available immediately', 'Relocating to', 'Expert in JavaScript, React') in the location field.\n"
            "3. EXPERIENCES: NEVER mix up company names and job titles. A job title is a person's role or designation (e.g. 'Senior Software Engineer', 'Product Manager'). A company is an organization or employer (e.g. 'Google', 'Skynet Defense', 'Acme Corp'). Disambiguate by semantics, NOT by line order.\n"
            "4. EDUCATION: Set 'graduation_year' to the year of completion (for ranges like '2018 - 2022', use '2022'). Separate degree from field of study (e.g. degree: 'Bachelor of Technology', field_of_study: 'Computer Science').\n"
            "5. If a field or section is not explicitly present in the text, leave it as null or an empty list. NEVER invent, assume, or hallucinate missing qualifications, dates, companies, degrees, or contact information.\n"
            "6. Output ONLY a valid JSON object matching this schema:\n"
            "{\n"
            '  "full_name": string | null,\n'
            '  "email": string | null,\n'
            '  "phone": string | null,\n'
            '  "location": string | null,\n'
            '  "headline": string | null,\n'
            '  "summary": string | null,\n'
            '  "linkedin_url": string | null,\n'
            '  "github_url": string | null,\n'
            '  "portfolio_url": string | null,\n'
            '  "skills": string[],\n'
            '  "experiences": [{"title": string | null, "company": string | null, "location": string | null, "start_date": string | null, "end_date": string | null, "current": boolean, "description": string | null}],\n'
            '  "education": [{"degree": string | null, "institution": string | null, "field_of_study": string | null, "graduation_year": string | null}],\n'
            '  "projects": [{"name": string | null, "description": string | null, "url": string | null, "technologies": string[]}]\n'
            "}"
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ai-job-search.local",
            "X-Title": "AI Job Search Resume Intelligence",
        }

        try:
            data = None
            used_model = self.model
            async with httpx.AsyncClient(timeout=20.0) as client:
                # 1. Attempt primary model with bounded retries
                data = await self._call_model_with_retry(
                    client=client,
                    headers=headers,
                    system_prompt=system_prompt,
                    raw_text=raw_text,
                    model_name=self.model,
                    max_retries=3
                )

                # 2. If primary model fails or rate limited, attempt configured fallback model
                if not data and self.fallback_model and self.fallback_model != self.model:
                    logger.info(
                        "Primary OpenRouter model '%s' unavailable. Attempting secondary fallback model '%s'.",
                        self.model, self.fallback_model
                    )
                    used_model = self.fallback_model
                    data = await self._call_model_with_retry(
                        client=client,
                        headers=headers,
                        system_prompt=system_prompt,
                        raw_text=raw_text,
                        model_name=self.fallback_model,
                        max_retries=2
                    )

            if not data:
                logger.info("OpenRouter models unavailable or rate-limited. Falling back to local heuristic parser.")
                return await self.fallback.parse_resume_text(raw_text)

            content = data["choices"][0]["message"]["content"]
            parsed_json = json.loads(content)

            # Post-validation and semantic correction
            full_name = parsed_json.get("full_name")
            if full_name:
                fn_lower = full_name.lower().strip()
                norm_fn = re.sub(r"^[\s#\*\-_:>]+", "", fn_lower).strip(" :")
                if norm_fn in SECTION_HEADER_TERMS or any(k in norm_fn for k in ["summary", "objective", "experience", "resume"]):
                    logger.warning("AI incorrectly assigned section header '%s' to full_name. Correcting via heuristics.", full_name)
                    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
                    h_name, _, _ = self.fallback._extract_name(lines, parsed_json.get("email"))
                    full_name = h_name

            location = parsed_json.get("location")
            if location and not ResumeSemanticClassifier.is_valid_location(location):
                logger.warning("AI provided invalid location '%s'. Cleansing via heuristics.", location)
                top_lines = [l.strip() for l in raw_text.splitlines()[:12] if l.strip()]
                location = self.fallback._extract_location(top_lines)

            experiences: List[ExperienceItem] = []
            uncertain_fields: List[str] = []
            confidence_scores: Dict[str, float] = {}

            for idx, exp in enumerate(parsed_json.get("experiences", [])):
                raw_title = exp.get("title")
                raw_company = exp.get("company")

                # Check for swapped title/company in AI output
                if raw_title and raw_company:
                    t_score_t = ResumeSemanticClassifier.score_job_title(raw_title)
                    c_score_t = ResumeSemanticClassifier.score_company_name(raw_title)
                    t_score_c = ResumeSemanticClassifier.score_job_title(raw_company)
                    c_score_c = ResumeSemanticClassifier.score_company_name(raw_company)

                    if c_score_t > t_score_t and t_score_c > c_score_c:
                        logger.warning(
                            "AI inverted title '%s' and company '%s'. Correcting via semantic classifier.",
                            raw_title, raw_company
                        )
                        raw_title, raw_company = raw_company, raw_title

                if not raw_title:
                    uncertain_fields.append(f"experiences[{idx}].title")
                if not raw_company:
                    uncertain_fields.append(f"experiences[{idx}].company")

                confidence_scores[f"experiences[{idx}]"] = 0.90 if (raw_title and raw_company) else 0.60

                experiences.append(
                    ExperienceItem(
                        title=raw_title,
                        company=raw_company,
                        location=exp.get("location"),
                        start_date=exp.get("start_date"),
                        end_date=exp.get("end_date"),
                        current=bool(exp.get("current", False)),
                        description=exp.get("description")
                    )
                )

            education: List[EducationItem] = []
            for idx, edu in enumerate(parsed_json.get("education", [])):
                deg = edu.get("degree")
                inst = edu.get("institution")
                f_study = edu.get("field_of_study")
                grad_year = edu.get("graduation_year")

                # Check for swapped degree/institution
                if deg and inst:
                    d_score = ResumeSemanticClassifier.score_degree(deg)
                    i_score = ResumeSemanticClassifier.score_institution(deg)
                    if i_score > d_score:
                        deg, inst = inst, deg

                # Disambiguate field of study if in degree
                if deg and not f_study:
                    cleaned_d, extracted_f = ResumeSemanticClassifier.extract_field_of_study(deg)
                    deg = cleaned_d
                    f_study = extracted_f

                # Year range fix
                if grad_year and ("-" in grad_year or "–" in grad_year):
                    y_matches = SINGLE_YEAR_PATTERN.findall(grad_year)
                    if y_matches:
                        grad_year = y_matches[-1]

                education.append(
                    EducationItem(
                        degree=deg,
                        institution=inst,
                        field_of_study=f_study,
                        graduation_year=grad_year
                    )
                )

            projects = [ProjectItem(**proj) for proj in parsed_json.get("projects", [])]
            skills = [str(s).strip() for s in parsed_json.get("skills", []) if str(s).strip()]

            missing_fields = []
            if not parsed_json.get("full_name"):
                missing_fields.append("full_name")
            if not parsed_json.get("email"):
                missing_fields.append("email")
            if not parsed_json.get("phone"):
                missing_fields.append("phone")
            if not parsed_json.get("headline"):
                missing_fields.append("headline")
            if not skills:
                missing_fields.append("skills")
            if not experiences:
                missing_fields.append("experiences")
            if not education:
                missing_fields.append("education")

            return ParsedResumeProfile(
                full_name=parsed_json.get("full_name"),
                email=parsed_json.get("email"),
                phone=parsed_json.get("phone"),
                location=parsed_json.get("location"),
                headline=parsed_json.get("headline"),
                summary=parsed_json.get("summary"),
                linkedin_url=parsed_json.get("linkedin_url"),
                github_url=parsed_json.get("github_url"),
                portfolio_url=parsed_json.get("portfolio_url"),
                skills=skills,
                experiences=experiences,
                education=education,
                projects=projects,
                missing_fields=missing_fields,
                confidence_scores=confidence_scores,
                uncertain_fields=uncertain_fields,
                field_evidence={},
                parser_source="openrouter",
                raw_extracted_text=raw_text
            )

        except Exception as exc:
            logger.warning("Error invoking OpenRouter (%s). Falling back to local parser.", exc)
            return await self.fallback.parse_resume_text(raw_text)


def get_ai_service() -> BaseAIService:
    heuristic = LocalHeuristicAIService()
    if settings.OPENROUTER_API_KEY:
        return OpenRouterAIService(fallback_service=heuristic)
    return heuristic
