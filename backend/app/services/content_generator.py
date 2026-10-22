import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import httpx
from app.core.config import settings
from app.models.application import JobApplicationWorkspace, RecruiterContact
from app.models.job import JobListing
from app.models.profile import UserProfile
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DuplicateOutreachDetector:
    """
    Guards against spamming and repeated outreach.
    Checks whether the user has already initiated or drafted an outreach email
    to the same company or recipient email address.
    """

    @classmethod
    def check_duplicate(
        cls,
        db: Session,
        user_id: int,
        current_job: JobListing,
        contact_email: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        # Find other workspaces for this user
        existing_workspaces = (
            db.query(JobApplicationWorkspace)
            .join(JobListing, JobApplicationWorkspace.job_id == JobListing.id)
            .filter(
                JobApplicationWorkspace.user_id == user_id,
                JobApplicationWorkspace.job_id != current_job.id,
                JobApplicationWorkspace.email_body.isnot(None)
            )
            .all()
        )

        for ws in existing_workspaces:
            other_job = ws.job
            # Check company match (case-insensitive)
            if other_job and other_job.company.strip().lower() == current_job.company.strip().lower():
                return True, (
                    f"Duplicate outreach notice: You already drafted an outreach email for {current_job.company} "
                    f"regarding the '{other_job.title}' role. Sending multiple inquiries to the same organization "
                    "simultaneously can appear as automated spam and damage your professional reputation."
                )

            # Check exact contact email match
            if contact_email and ws.contact_email and ws.contact_email.strip().lower() == contact_email.strip().lower():
                return True, (
                    f"Duplicate outreach notice: You already have an outreach email targeted to {contact_email} "
                    f"for the '{other_job.title}' position. Avoid sending repeated messages to the same contact."
                )

        return False, None


class LocalContentGenerator:
    """
    100% Offline, deterministic cover letter and recruiter email generator.
    Strictly uses ONLY qualifications and experiences verified in the user's profile.
    Never hallucinates unmentioned skills, degrees, or employers.
    """

    @classmethod
    def generate_cover_letter(
        cls,
        profile: Optional[UserProfile],
        job: JobListing,
        tone: str = "professional",
        template_style: str = "modern"
    ) -> str:
        name = (profile.full_name if profile and profile.full_name else "Applicant")
        headline = (profile.headline if profile and profile.headline else "Professional")
        email = (profile.email if profile and profile.email else "")
        phone = (profile.phone if profile and profile.phone else "")
        linkedin = (profile.linkedin_url if profile and profile.linkedin_url else "")

        # Extract parsed skills
        profile_skills = cls._extract_skills(profile)
        matched_skills = cls._find_matched_skills(profile_skills, job)
        
        # Extract parsed experiences and projects
        experiences = cls._extract_experiences(profile)
        projects = cls._extract_projects(profile)

        # Header block
        header = f"{name}\n"
        contact_line = " | ".join(filter(None, [email, phone, headline, linkedin]))
        if contact_line:
            header += f"{contact_line}\n"
        header += f"\nDate: {datetime.now(timezone.utc).strftime('%B %d, %Y')}\n"
        header += f"Hiring Team\n{job.company}\nRe: Application for {job.title}\n\n"

        # Salutation
        salutation = f"Dear Hiring Team at {job.company},\n\n"

        # Paragraph 1: Introduction / Hook
        if tone == "enthusiastic":
            intro = (
                f"I am writing with great enthusiasm to apply for the {job.title} position at {job.company}. "
                f"With my background as a {headline}, I have long admired {job.company}'s work and would be thrilled "
                "to contribute my energy, dedication, and technical foundation to your team's ongoing initiatives.\n\n"
            )
        elif tone == "concise":
            intro = (
                f"Please accept this letter as my formal application for the {job.title} role at {job.company}. "
                f"As a {headline}, I bring hands-on experience and a proven ability to deliver reliable results.\n\n"
            )
        elif tone == "technical":
            intro = (
                f"I am writing to express my strong interest in the {job.title} role at {job.company}. "
                f"As an engineering professional focusing on {headline}, my hands-on experience aligns closely "
                f"with the technical scope required for this position.\n\n"
            )
        else:  # professional default
            intro = (
                f"I am writing to express my sincere interest in the {job.title} role at {job.company}. "
                f"As an experienced {headline}, I offer a solid background of practical expertise and a track record "
                "of collaborating effectively across teams to achieve organizational goals.\n\n"
            )

        # Paragraph 2: Core Qualifications & Relevance
        qual_body = ""
        if template_style == "modern" or tone == "concise":
            if matched_skills:
                skills_str = ", ".join(matched_skills[:5])
                qual_body = (
                    f"In reviewing the responsibilities for {job.title}, several key areas of my background directly connect "
                    f"with your objectives:\n"
                    f"• Demonstrated Core Capabilities: Extensive hands-on practice in {skills_str}.\n"
                )
            elif profile_skills:
                skills_str = ", ".join(profile_skills[:5])
                qual_body = (
                    f"Throughout my career, I have cultivated strong core competencies in {skills_str}, which I look forward "
                    f"to applying directly to the initiatives at {job.company}.\n"
                )
            else:
                qual_body = (
                    f"My professional experience has equipped me with strong problem-solving skills, accountability, "
                    f"and an eagerness to master the specific workflows of {job.company}.\n"
                )

            if experiences:
                recent = experiences[0]
                company_exp = recent.get("company", "previous roles")
                role_exp = recent.get("title", "professional projects")
                qual_body += f"• Practical Impact: In my role as {role_exp} at {company_exp}, I consistently delivered high-standard work and collaborated closely with stakeholders.\n"

            if projects:
                proj = projects[0]
                p_name = proj.get("name", "Key Project")
                p_desc = proj.get("description", "")
                if p_desc:
                    qual_body += f"• Verified Project Experience: Developed {p_name}, {p_desc[:120].strip()}.\n"
            qual_body += "\n"

        else:  # standard / traditional template
            skills_highlight = f"such as {', '.join(matched_skills[:4])}" if matched_skills else "across modern engineering tools"
            qual_body = (
                f"Throughout my professional journey, I have developed a strong foundation in core technologies {skills_highlight}. "
                f"I take pride in writing maintainable solutions, following sound engineering principles, and actively "
                "contributing to high-functioning team environments.\n\n"
            )
            if experiences:
                recent = experiences[0]
                qual_body += (
                    f"Most recently, serving as {recent.get('title', 'an engineer')} at {recent.get('company', 'my prior employer')}, "
                    "I took ownership of key deliverables and focused on optimizing outcomes while meeting tight deadlines.\n\n"
                )

        # Paragraph 3: Closing & Call to Action
        if tone == "concise":
            closing = (
                f"I welcome the opportunity to discuss how my skill set matches {job.company}'s needs. "
                "Thank you for your time and consideration.\n\n"
            )
        else:
            closing = (
                f"I am eager to bring my background, analytical mindset, and commitment to excellence to {job.company}. "
                "Thank you for considering my application. I welcome the opportunity to discuss my qualifications further in an interview.\n\n"
            )

        signoff = f"Sincerely,\n{name}"

        return header + salutation + intro + qual_body + closing + signoff

    @classmethod
    def generate_recruiter_email(
        cls,
        profile: Optional[UserProfile],
        job: JobListing,
        contact: Optional[RecruiterContact],
        tone: str = "concise"
    ) -> Tuple[str, str]:
        name = (profile.full_name if profile and profile.full_name else "Applicant")
        headline = (profile.headline if profile and profile.headline else "Professional")
        email = (profile.email if profile and profile.email else "")
        phone = (profile.phone if profile and profile.phone else "")
        
        # Greeting
        recipient_name = contact.name if (contact and contact.name) else f"{job.company} Hiring Team"
        salutation = f"Dear {recipient_name},"

        # Subject line
        subject = f"Application: {job.title} - {name}"
        if job.source_id and len(job.source_id) < 15:
            subject += f" (Ref: {job.source_id})"

        # Body
        profile_skills = cls._extract_skills(profile)
        matched_skills = cls._find_matched_skills(profile_skills, job)
        skills_phrase = f"in {', '.join(matched_skills[:3])}" if matched_skills else "in software engineering and problem-solving"

        if tone == "formal":
            body = (
                f"{salutation}\n\n"
                f"I am writing to express my formal interest in the {job.title} opportunity currently open at {job.company}.\n\n"
                f"With my background as a {headline} and hands-on experience {skills_phrase}, I believe my qualifications "
                f"align well with the requirements of this role. I have reviewed the position details and am very interested in "
                f"how {job.company} approaches innovation in this space.\n\n"
                f"My resume is available for your review, and I would welcome the opportunity to speak with you briefly "
                f"regarding how my experience can benefit your team.\n\n"
                f"Thank you for your consideration.\n\n"
                f"Sincerely,\n{name}\n{email} | {phone}"
            )
        elif tone == "warm":
            body = (
                f"{salutation}\n\n"
                f"I hope this note finds you well! I recently came across the {job.title} opening at {job.company} and wanted "
                "to reach out directly.\n\n"
                f"As a {headline} with practical experience {skills_phrase}, I'm very excited about {job.company}'s work and "
                "would love to explore how I could contribute to your current projects.\n\n"
                f"I would be glad to share any additional details or chat at your convenience. Thank you so much for your time and consideration!\n\n"
                f"Best regards,\n{name}\n{email} | {phone}"
            )
        else:  # concise default
            body = (
                f"{salutation}\n\n"
                f"I am reaching out to express my interest in the {job.title} opening at {job.company}.\n\n"
                f"As a {headline} with proven background {skills_phrase}, I am confident I can contribute effectively to your team's goals. "
                f"I have reviewed the role requirements and my experience aligns closely with what you are seeking.\n\n"
                f"I would welcome the opportunity for a brief conversation to discuss how my background fits your team. Thank you for your time.\n\n"
                f"Sincerely,\n{name}\n{email} | {phone}"
            )

        return subject, body

    @classmethod
    def _extract_skills(cls, profile: Optional[UserProfile]) -> List[str]:
        if not profile or not profile.skills:
            return []
        try:
            parsed = json.loads(profile.skills)
            if isinstance(parsed, list):
                return [str(s).strip() for s in parsed if str(s).strip()]
        except Exception:
            pass
        return []

    @classmethod
    def _extract_experiences(cls, profile: Optional[UserProfile]) -> List[Dict[str, Any]]:
        if not profile or not profile.experiences:
            return []
        try:
            parsed = json.loads(profile.experiences)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return []

    @classmethod
    def _extract_projects(cls, profile: Optional[UserProfile]) -> List[Dict[str, Any]]:
        if not profile or not profile.projects:
            return []
        try:
            parsed = json.loads(profile.projects)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return []

    @classmethod
    def _find_matched_skills(cls, profile_skills: List[str], job: JobListing) -> List[str]:
        if not profile_skills:
            return []
        job_text = f"{job.title} {job.description} {job.skills_required}".lower()
        matched = []
        for skill in profile_skills:
            if skill.lower() in job_text:
                matched.append(skill)
        return matched


class ApplicationContentService:
    """
    Orchestrates personalized cover letter and recruiter email generation.
    Utilizes OpenRouter cloud LLM when configured, with seamless, 100% offline
    deterministic fallback to LocalContentGenerator.
    """

    @classmethod
    async def generate_cover_letter(
        cls,
        profile: Optional[UserProfile],
        job: JobListing,
        tone: str = "professional",
        template_style: str = "modern"
    ) -> str:
        # If OpenRouter is configured, try cloud generation
        if settings.OPENROUTER_API_KEY:
            try:
                cloud_result = await cls._generate_cloud_cover_letter(profile, job, tone, template_style)
                if cloud_result:
                    return cloud_result
            except Exception as e:
                logger.warning("OpenRouter cover letter generation failed (%s). Using local fallback.", e)

        # Fallback to deterministic local generator
        return LocalContentGenerator.generate_cover_letter(
            profile=profile,
            job=job,
            tone=tone,
            template_style=template_style
        )

    @classmethod
    async def generate_recruiter_email(
        cls,
        profile: Optional[UserProfile],
        job: JobListing,
        contact: Optional[RecruiterContact],
        tone: str = "concise"
    ) -> Tuple[str, str]:
        # If OpenRouter is configured, try cloud generation
        if settings.OPENROUTER_API_KEY:
            try:
                cloud_result = await cls._generate_cloud_recruiter_email(profile, job, contact, tone)
                if cloud_result:
                    return cloud_result
            except Exception as e:
                logger.warning("OpenRouter recruiter email generation failed (%s). Using local fallback.", e)

        # Fallback to deterministic local generator
        return LocalContentGenerator.generate_recruiter_email(
            profile=profile,
            job=job,
            contact=contact,
            tone=tone
        )

    @classmethod
    async def _generate_cloud_cover_letter(
        cls,
        profile: Optional[UserProfile],
        job: JobListing,
        tone: str,
        template_style: str
    ) -> Optional[str]:
        profile_skills = LocalContentGenerator._extract_skills(profile)
        experiences = LocalContentGenerator._extract_experiences(profile)
        projects = LocalContentGenerator._extract_projects(profile)

        system_prompt = (
            "You are a professional career coach writing a tailored, concise cover letter.\n"
            "STRICT RULES:\n"
            "1. NEVER invent or hallucinate missing qualifications, unheld degrees, or companies.\n"
            "2. Highlight ONLY skills and experiences provided in the candidate's verified profile.\n"
            "3. Do not promise or claim that this letter guarantees an interview or job offer.\n"
            "4. Return ONLY the plain text cover letter without conversational commentary.\n"
            f"5. Tone: {tone}. Template Style: {template_style}."
        )

        user_prompt = (
            f"Candidate Name: {profile.full_name if profile else 'Applicant'}\n"
            f"Candidate Headline: {profile.headline if profile else ''}\n"
            f"Verified Skills: {', '.join(profile_skills)}\n"
            f"Verified Experiences: {json.dumps(experiences[:2])}\n"
            f"Verified Projects: {json.dumps(projects[:2])}\n\n"
            f"Target Company: {job.company}\n"
            f"Target Job Title: {job.title}\n"
            f"Job Description Excerpt: {job.description[:1000]}\n"
        )

        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": settings.PROJECT_NAME,
            "Content-Type": "application/json"
        }
        payload = {
            "model": settings.OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                if content and len(content) > 100:
                    return content
        return None

    @classmethod
    async def _generate_cloud_recruiter_email(
        cls,
        profile: Optional[UserProfile],
        job: JobListing,
        contact: Optional[RecruiterContact],
        tone: str
    ) -> Optional[Tuple[str, str]]:
        profile_skills = LocalContentGenerator._extract_skills(profile)
        recipient = contact.name if (contact and contact.name) else f"{job.company} Hiring Team"

        system_prompt = (
            "You are an expert career advisor writing a concise, respectful, non-spammy recruiter outreach email.\n"
            "STRICT RULES:\n"
            "1. NEVER invent qualifications or make false claims.\n"
            "2. Keep it under 150 words. Avoid generic flattery or mass-outreach clichés.\n"
            "3. Output format must be strictly a JSON object with keys 'subject' and 'body'.\n"
            f"4. Tone: {tone}."
        )

        user_prompt = (
            f"Candidate: {profile.full_name if profile else 'Applicant'} ({profile.headline if profile else ''})\n"
            f"Verified Skills: {', '.join(profile_skills[:5])}\n"
            f"Recipient: {recipient}\n"
            f"Company: {job.company}\n"
            f"Job Title: {job.title}\n"
            f"Job Reference ID: {job.source_id or ''}\n"
        )

        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": settings.PROJECT_NAME,
            "Content-Type": "application/json"
        }
        payload = {
            "model": settings.OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
            "max_tokens": 500
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload
            )
            if resp.status_code == 200:
                data = resp.json()
                raw_json = json.loads(data["choices"][0]["message"]["content"])
                return raw_json.get("subject", f"Application: {job.title}"), raw_json.get("body", "")
        return None
