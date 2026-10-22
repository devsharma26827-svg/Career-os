# Security Policy

## Supported Versions

JobPulse AI provides active security updates and patches for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## Reporting a Vulnerability

We take the security and privacy of our users and their personal career data very seriously.

If you discover a security vulnerability, **please do NOT create a public GitHub issue.** Instead, responsibly disclose the issue by sending an email with detailed findings to:

**security@jobpulse.ai** (or contact repository maintainers directly via private GitHub security advisories)

### What to Include in Your Report
- A description of the vulnerability, including attack vector and potential impact.
- Step-by-step reproduction instructions or proof-of-concept scripts.
- Affected components (e.g. backend endpoint, authentication token handler, file upload parser, environment handling).
- Any proposed mitigations or remediation patches.

### Our Commitment
- We will acknowledge receipt of your vulnerability report within **48 hours**.
- We will provide an assessment of the vulnerability and keep you informed of progress toward a patch.
- We will publish a security advisory and credit the reporter once a fix is deployed.

---

## Security Best Practices in JobPulse AI

JobPulse AI implements multiple layers of defense:

1. **Authentication & Password Storage**:
   - Passwords are encrypted using **bcrypt** with salted hashing. Plaintext passwords are never stored or logged.
   - Session authentication uses short-lived or configurable **JWT tokens** signed with `HS256`.
2. **Credential Protection**:
   - Secrets (`SECRET_KEY`, `OPENROUTER_API_KEY`, `ADZUNA_APP_KEY`, `SMTP_PASSWORD`) are loaded strictly from server-side environment variables.
   - Client-facing APIs and health monitors strictly redact secret tokens and keys.
3. **File Upload Security**:
   - Resume uploads are restricted to `.pdf` and `.docx` extensions.
   - File size is strictly enforced (max 10MB default) both client-side and server-side.
   - Uploaded files are quarantined in isolated directories and never executed as server code.
4. **Data Isolation & Portability**:
   - Multi-tenant database queries enforce `user_id` filtering. Users cannot access or modify records of other candidates.
   - Users maintain full sovereignty with single-click complete personal data export (`GET /api/v1/auth/export-data`) and irreversible account deletion (`DELETE /api/v1/auth/delete-account`).
