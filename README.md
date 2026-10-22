# JobPulse AI — Intelligent, Accessible, and Ethical Job Search Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.0-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-3178c6.svg)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-v4-38bdf8.svg)](https://tailwindcss.com/)
[![Three.js](https://img.shields.io/badge/Three.js-r128-black.svg)](https://threejs.org/)
[![Tests](https://img.shields.io/badge/Tests-83%20Passed-brightgreen.svg)](backend/tests/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **JobPulse AI** is an enterprise-grade, accessible career discovery and application platform. Combining real-time worldwide job discovery, deep resume intelligence, AI-guided relevance scoring, tailored document preparation, and verifiable application tracking, JobPulse AI empowers candidates of all experience levels while upholding strict anti-fabrication and user consent standards.

---

## Table of Contents

1. [Project Title & Introduction](#1-project-title--introduction)
2. [Core Vision & Unique Value Proposition](#2-core-vision--unique-value-proposition)
3. [Architecture Overview](#3-architecture-overview)
4. [Technology Stack Breakdown](#4-technology-stack-breakdown)
5. [Key Features & Workflows](#5-key-features--workflows)
   - [Authentication & Profile Sovereignty](#51-user-authentication--profile-management)
   - [Resume Intelligence & Offline Fallbacks](#52-resume-upload-parsing--data-extraction)
   - [Worldwide Job Discovery Engine](#53-worldwide--regional-job-discovery)
   - [Relevance Matching & Transparent Scoring](#54-real-time-ai-matching--scoring)
   - [Application Preparation & Tailored Drafts](#55-application-preparation--customization)
   - [Verifiable Multi-Channel Application Adapters](#56-verifiable-application-workflows)
   - [Application Tracker & Audit Trail](#57-application-tracking--audit-logging)
   - [Sensory Accessibility & Notification Drawer](#58-user-preferences--notifications)
6. [Ethical AI & Anti-Fabrication Principles](#6-ethical-ai-transparency--anti-fabrication-principles)
7. [Project Structure & Directory Layout](#7-project-structure--folder-layout)
8. [Prerequisites & System Requirements](#8-prerequisites--requirements)
9. [Zero-Configuration Windows Quickstart](#9-quick-start-guide-using-runbat--manual-startup)
10. [Backend Setup Guide](#10-backend-setup-instructions)
11. [Frontend Setup Guide](#11-frontend-setup-instructions)
12. [Database Configuration & Migrations](#12-database-configuration--schema-management)
13. [Environment Variables Reference](#13-environment-variables-reference-table)
14. [AI Provider Configuration (OpenRouter vs Local Heuristics)](#14-ai-provider-configuration)
15. [Job Sources Setup & API Integrations](#15-job-sources-setup--api-keys)
16. [Email & Outbound SMTP Setup](#16-email--outbound-smtp-setup)
17. [Running the Automated Test Suite](#17-running-tests)
18. [Resetting User Data for a Fresh Launch](#18-resetting-data-for-fresh-launch)
19. [Troubleshooting Guide](#19-troubleshooting-guide)
20. [Security & Privacy Practices](#20-security--privacy-practices)
21. [Contributing Guidelines](#21-contributing-guidelines)
22. [License](#22-license-information)
23. [Acknowledgments & Credits](#23-acknowledgments--credits)
24. [REST API Reference Summary](#24-api-reference-summary)
25. [Production Deployment Considerations](#25-production-deployment-considerations)
26. [Frequently Asked Questions (FAQ)](#26-frequently-asked-questions-faq)

---

## 1. Project Title & Introduction

**JobPulse AI** was engineered to solve fundamental flaws in current automated job searching: deceptive bot automation, spamming hiring managers, fabricated candidate credentials, fragile paid API dependencies, and false "application submitted" indicators.

By uniting an accessible, futuristic 3D interface (built in React 19, Tailwind CSS v4, and Three.js) with a resilient FastAPI backend, JobPulse AI provides job seekers with a verified command center for their career search.

---

## 2. Core Vision & Unique Value Proposition

Traditional job application bots damage candidate reputations by submitting generic applications to irrelevant jobs, hallucinating skills to force high keyword matches, and pretending applications succeeded when they merely opened a browser tab.

JobPulse AI takes the opposite approach:
- **Zero Simulation / Zero Fabrication**: We never pretend an action happened. If an employer portal requires manual completion, we provide an assisted application kit with direct links and 1-click clipboard items.
- **Strict User Consent**: Applications and outreach are never dispatched automatically in the background without explicit candidate authorization.
- **Resilient AI Without Paid API Lock-In**: Includes a deterministic local heuristic NLP engine that operates 100% offline with zero cost, seamlessly upgrading to OpenRouter LLMs when configured.
- **Multi-Source Worldwide Coverage**: Aggregates verified opportunities across Europe, North America, the UK, Asia, and remote roles from official permitted feeds (Arbeitnow, RemoteOK, Jobicy, Adzuna).

---

## 3. Architecture Overview

```mermaid
flowchart TD
    subgraph Client["Frontend Layer (React 19 + Vite + Three.js)"]
        UI["Futuristic CareerOS UI"]
        Globe["3D Particle Globe & Canvas"]
        Dropzone["Resume Dropzone & PDF Parser"]
        Review["Consent & Review Hub"]
        Tracker["Verifiable Application Tracker"]
    end

    subgraph API["FastAPI Backend (Port 8000)"]
        Router["API v1 Router (/api/v1)"]
        AuthSvc["Auth & Security (bcrypt, JWT)"]
        ParseSvc["Resume Parser (OpenRouter + Local Heuristic)"]
        JobSvc["Job Discovery & Sync Manager"]
        MatchSvc["Relevance & Explanation Engine"]
        AppSvc["Application Runner & Adapters"]
    end

    subgraph Data["Persistence & Storage"]
        SQLite[("SQLite / PostgreSQL Database")]
        Uploads["Encrypted Uploads (/uploads/resumes/)"]
    end

    subgraph External["External APIs & Feeds"]
        Feeds["Job Feeds (Arbeitnow, RemoteOK, Jobicy, Adzuna)"]
        OpenRouter["OpenRouter AI (Gemini 2.0 Flash)"]
        SMTP["Outbound SMTP Dispatch"]
    end

    UI --> Router
    Router --> AuthSvc
    Router --> ParseSvc
    Router --> JobSvc
    Router --> MatchSvc
    Router --> AppSvc

    AuthSvc --> SQLite
    ParseSvc --> Uploads
    ParseSvc -.-> OpenRouter
    JobSvc --> Feeds
    JobSvc --> SQLite
    MatchSvc --> SQLite
    AppSvc --> SMTP
    AppSvc --> SQLite
```

---

## 4. Technology Stack Breakdown

### Frontend
- **Framework**: React 19 (`react`, `react-dom`)
- **Build Tool**: Vite 6 with HMR
- **Language**: TypeScript 5.8
- **Styling**: Tailwind CSS v4 with modern theme variables and responsive utilities
- **3D Visuals & Graphics**: Three.js, Lucide Icons, Canvas 3D Particle Shaders
- **HTTP Client**: Axios with token interceptors and error normalization

### Backend
- **Web Framework**: FastAPI (ASGI)
- **ASGI Server**: Uvicorn with multi-worker support
- **ORM & Database**: SQLAlchemy 2.0 with SQLite (default) and PostgreSQL compatibility
- **Authentication**: OAuth2 Password Flow, JWT tokens (`pyjwt`), bcrypt password hashing (`passlib`/`bcrypt`)
- **Document Parsing**: `pdfplumber`, `pypdf`, `python-docx`
- **Validation**: Pydantic v2 schemas with strict typing
- **Testing**: `pytest`, `pytest-asyncio`, `httpx`

---

## 5. Key Features & Workflows

### 5.1 User Authentication & Profile Management
- Secure user registration, login, and session persistence with bcrypt-hashed credentials.
- Multi-tenant isolation: every record is tagged by `user_id` with authorization checks.
- Complete data sovereignty: `GET /api/v1/auth/export-data` for complete JSON data export, and `DELETE /api/v1/auth/delete-account` for permanent data wiping.

### 5.2 Resume Upload, Parsing & Data Extraction
- Drag-and-drop support for **PDF (`.pdf`)** and **Microsoft Word (`.docx`)** files (up to 10MB).
- Dual-tier parsing strategy:
  - **Tier 1 (AI-Powered)**: OpenRouter API calling `google/gemini-2.0-flash-001` with exponential backoff on HTTP 429 rate limits.
  - **Tier 2 (Deterministic Local Heuristic)**: Built-in offline pattern extractor extracting skills, work history, education, and contact links without sending data to external APIs.
- Candidate review: Extracted profile data is presented for review and inline editing before confirming.

### 5.3 Worldwide & Regional Job Discovery
- Multi-source search across **Arbeitnow**, **RemoteOK**, **Jobicy**, and optional **Adzuna**.
- Worldwide discovery by default, with precision country filters (US, UK, CA, DE, IN, AU, and Remote).
- State/province multi-selection dynamically filtered to the selected country.
- Separate storage for canonical employer URLs and aggregator links to prevent redirect traps.

### 5.4 Real-Time AI Matching & Scoring
- Compares candidate skills, years of experience, and role alignment against job requirements.
- Computes transparent 0–100% relevance scores accompanied by plain-English explanations.
- Honest matching: Unlisted skills are reported as *unknown*, never as disqualified.

### 5.5 Application Preparation & Customization
- Tailored cover letter drafting based exclusively on verified resume facts.
- Selectable tones: Professional, Enthusiastic, Concise, or Technical.
- Recruiter contact discovery with strict verification tagging (`VERIFIED`, `INFERRED`, `USER_VERIFIED`, `NOT_FOUND`).
- Anti-spam guard: Detects and warns against duplicate outreach to the same company or hiring contact.

### 5.6 Verifiable Application Workflows
JobPulse AI rejects simulated automation. Application dispatch is handled through three distinct adapters:
1. **Direct ATS API Adapter (`DirectApiApplicationAdapter`)**: Dispatches applications directly to partner applicant tracking systems that support authenticated API submissions.
2. **Email Application Adapter (`EmailApplicationAdapter`)**: Sends application packages directly to verified hiring manager email addresses via SMTP.
3. **Assisted Manual Portal Adapter (`ManualPortalRedirectAdapter`)**: For portals requiring logins, SSO, or CAPTCHAs (Workday, Greenhouse, Taleo, Lever), the platform generates a structured Assisted Application Kit with 1-click clipboard copying and direct links to the official employer posting.

### 5.7 Application Tracking & Audit Logging
- Searchable and filterable tracker monitoring status across all applications (`draft`, `review`, `in_progress`, `action_needed`, `submitted`, `failed`).
- Append-only audit logs recording timestamps, target destinations, and outcome details.
- Safe retry controller: Failed or action-needed applications can be reset to the review queue without losing previous draft edits.

### 5.8 User Preferences & Notifications
- Dynamic typography scaling: **Normal (16px)**, **Large (18px)**, and **Larger (20px)**.
- Reduced-motion toggle disabling 3D canvas particles and CSS animations.
- In-app notification bell with real-time unread badges and granular notification category preferences.

---

## 6. Ethical AI, Transparency & Anti-Fabrication Principles

JobPulse AI adheres strictly to the following foundational rules:
1. **No Hallucinated Credentials**: The platform will never invent degrees, certifications, job titles, or programming languages not present in the candidate's resume or manually confirmed profile.
2. **No Deceptive Submissions**: An application is only recorded as `submitted` when verified by an external partner API response, confirmed SMTP delivery, or explicit user action.
3. **No Background Spam**: No resumes or emails are dispatched without explicit candidate consent.
4. **Respect for Employer Safeguards**: JobPulse AI does not attempt CAPTCHA bypassing or unauthorized portal injection.

---

## 7. Project Structure & Folder Layout

```
Ai-Job-Search/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml            # Structured GitHub bug report template
│   │   └── feature_request.yml       # Structured feature request template
│   └── pull_request_template.md      # Pull request review checklist
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py               # Auth & dependency injection
│   │   │   └── v1/
│   │   │       ├── auth.py           # Signup, login, preferences, data export, account deletion
│   │   │       ├── resume.py         # Resume upload, parsing, and management
│   │   │       ├── profile.py        # Candidate profile confirmation and updates
│   │   │       ├── jobs.py           # Worldwide job discovery, matching, saved jobs
│   │   │       ├── applications.py   # Workspaces, batch apply, audit logs, tracker
│   │   │       ├── notifications.py  # In-app notifications and preferences
│   │   │       └── router.py         # API v1 master router
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic v2 settings & environment loading
│   │   │   ├── database.py           # SQLAlchemy engine & session maker
│   │   │   ├── security.py           # bcrypt password hashing & JWT tokens
│   │   │   ├── locations.py          # Geographic taxonomies & country isolation
│   │   │   └── migrations.py         # Automatic column migrations for SQLite
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   ├── schemas/                  # Pydantic request/response validation schemas
│   │   └── services/
│   │       ├── ai_service.py         # OpenRouter client with exponential backoff
│   │       ├── resume_parser.py      # Dual-tier parser (OpenRouter + Heuristic)
│   │       ├── job_matcher.py        # Resume-to-job relevance scoring engine
│   │       ├── job_sources/          # Feeds: Arbeitnow, RemoteOK, Jobicy, Adzuna
│   │       ├── application_runner.py # Background batch execution & cancellation
│   │       └── application_adapters/ # Direct API, Email, and Manual Portal adapters
│   ├── scripts/
│   │   ├── backup_data.py            # External timestamped database & uploads backup
│   │   └── reset_user_data.py        # Confirmed user data purge utility
│   ├── tests/                        # 83 automated backend tests
│   ├── uploads/resumes/              # Isolated candidate resume storage (.gitkeep)
│   ├── .env.example                  # Backend environment template
│   ├── requirements.txt              # Pinned Python package dependencies
│   └── run.py                        # Uvicorn entrypoint launcher
│
├── New Frontend/
│   ├── src/
│   │   ├── components/               # Navbar, JobCard, JobDetailModal, Modals, Footer
│   │   ├── pages/                    # ApplicationsPage, SavedJobsPage, ResumePage, etc.
│   │   ├── sections/                 # ResumeDropZone, JobResultsSection, FeaturesSection
│   │   ├── three/                    # Three.js 3D Particle Globe & Canvas
│   │   ├── services/                 # api.ts (Axios), jobService.ts, resumeService.ts, etc.
│   │   ├── types/                    # TypeScript interfaces and contracts
│   │   ├── App.tsx                   # Master interactive layout
│   │   └── main.tsx                  # React DOM entrypoint
│   ├── .env.example                  # Frontend environment template
│   ├── package.json                  # Frontend dependencies and scripts
│   ├── vite.config.ts                # Vite configuration with proxy
│   └── tsconfig.json                 # TypeScript compiler configuration
│
├── .env.example                      # Root project environment reference template
├── .gitignore                        # Comprehensive security & artifact ignore rules
├── CONTRIBUTING.md                   # Contribution workflow & guidelines
├── SECURITY.md                       # Security disclosure policy
├── run.bat                           # 1-Click Windows launch script
├── stop.bat                          # 1-Click Windows shutdown script
└── README.md                         # Complete project documentation
```

---

## 8. Prerequisites & Requirements

Before running JobPulse AI, ensure the following software is installed on your workstation:

| Requirement | Supported Version | Notes |
| ----------- | ----------------- | ----- |
| **Python**  | `3.10` to `3.12`  | Python 3.11 recommended. Ensure Python is added to `PATH`. |
| **Node.js** | `18.x` or `20.x+` | Node 20 LTS recommended. Includes `npm`. |
| **Git**     | `2.30+`           | Required for source version control. |
| **OS**      | Windows 10/11, macOS, Linux | Dedicated `.bat` scripts provided for Windows. |

---

## 9. Quick Start Guide (Using run.bat / Manual Startup)

### Option A: 1-Click Windows Launch (Recommended)
Double-click `run.bat` in the project root, or execute via PowerShell:
```cmd
.\run.bat
```
`run.bat` automatically:
1. Verifies Python 3.10+ and Node.js 18+ availability.
2. Creates and configures the Python virtual environment (`backend/venv`).
3. Installs missing Python and Node dependencies.
4. Generates default `.env` files if missing.
5. Verifies and clears ports `8000` and `5173`.
6. Launches FastAPI on `http://127.0.0.1:8000` and Vite on `http://localhost:5173`.
7. Opens your default web browser directly to JobPulse AI.

### To Stop All Services:
Double-click `stop.bat` or run:
```cmd
.\stop.bat
```

---

## 10. Backend Setup Instructions

To run the backend independently:

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate a virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env

# 5. Start the backend server
python run.py
```
The FastAPI backend will start on `http://127.0.0.1:8000`. Interactive documentation is available at `http://127.0.0.1:8000/docs`.

---

## 11. Frontend Setup Instructions

To run the frontend independently:

```bash
# 1. Navigate to New Frontend directory
cd "New Frontend"

# 2. Install dependencies
npm install

# 3. Configure environment variables
cp .env.example .env

# 4. Start the Vite development server
npm run dev
```
The frontend application will be live at `http://localhost:5173`.

---

## 12. Database Configuration & Schema Management

By default, JobPulse AI utilizes a zero-configuration SQLite database stored at `backend/sql_app.db`.

### Automatic Migrations
When FastAPI initializes, `backend/app/core/migrations.py` runs automatically to verify that all necessary tables and columns exist in the database, applying non-destructive `ALTER TABLE` migrations for any newly introduced columns.

### Switching to PostgreSQL
To use PostgreSQL in production, update `DATABASE_URL` in `backend/.env`:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/jobpulse_db
```
Ensure `psycopg2-binary` or `asyncpg` is installed in your virtual environment.

---

## 13. Environment Variables Reference Table

### Backend Configuration (`backend/.env`)

| Variable | Default Value | Description |
| -------- | ------------- | ----------- |
| `PROJECT_NAME` | `JobPulse AI` | Display name of the backend service. |
| `API_V1_STR` | `/api/v1` | URL prefix for version 1 API endpoints. |
| `SECRET_KEY` | *(Random string)* | Cryptographic key used to sign JWT session tokens. |
| `ALGORITHM` | `HS256` | JWT signature algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Session lifetime (1440 minutes = 24 hours). |
| `DATABASE_URL` | `sqlite:///./sql_app.db` | SQLAlchemy connection string. |
| `UPLOAD_DIR` | `./uploads/resumes` | Directory path for candidate resume files. |
| `MAX_UPLOAD_SIZE_BYTES` | `10485760` | Maximum file upload size in bytes (10MB). |
| `OPENROUTER_API_KEY` | *(Empty)* | Optional OpenRouter API key for LLM resume parsing. |
| `OPENROUTER_MODEL` | `google/gemini-2.0-flash-001` | LLM model identifier on OpenRouter. |
| `ADZUNA_APP_ID` | *(Empty)* | Optional Adzuna Application ID. |
| `ADZUNA_APP_KEY` | *(Empty)* | Optional Adzuna Application Key. |
| `SMTP_HOST` | `smtp.example.com` | Outbound email SMTP server hostname. |
| `SMTP_PORT` | `587` | SMTP port (587 for TLS). |
| `SMTP_USER` | *(Empty)* | SMTP account username. |
| `SMTP_PASSWORD` | *(Empty)* | SMTP account password. |
| `SMTP_FROM_EMAIL` | *(Empty)* | Default sender email address for outreach. |
| `SMTP_TLS` | `true` | Whether to enable STARTTLS for SMTP. |
| `CORS_ORIGINS` | `["http://localhost:5173", ...]` | JSON list of allowed browser origins. |

### Frontend Configuration (`New Frontend/.env`)

| Variable | Default Value | Description |
| -------- | ------------- | ----------- |
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000/api/v1` | Base URL of the running FastAPI backend. |
| `GEMINI_API_KEY` | *(Empty)* | Optional client-side Gemini key. |
| `APP_URL` | `http://localhost:5173` | Public URL where the frontend is hosted. |

---

## 14. AI Provider Configuration

JobPulse AI offers flexible AI integration with built-in resilience:

### 1. OpenRouter (Cloud AI)
If an `OPENROUTER_API_KEY` is provided:
- The system calls the OpenRouter chat completions endpoint with structured schema extraction.
- **Rate Limit Resilience**: If OpenRouter returns HTTP 429 (quota or concurrency limits), the backend applies exponential backoff and transparently falls back to the local heuristic parser without failing the user's upload.

### 2. Local Deterministic Heuristic Parser (Offline & Free)
If `OPENROUTER_API_KEY` is omitted:
- JobPulse AI immediately utilizes its built-in regex and NLP heuristic parser (`backend/app/services/resume_parser.py`).
- Accurately extracts candidate email, phone number, LinkedIn, GitHub, technical skills, and employment blocks.
- **Zero API costs, zero external network requests, zero downtime.**

---

## 15. Job Sources Setup & API Keys

JobPulse AI aggregates jobs from four distinct sources:

1. **Arbeitnow (Free & Public)**:
   - Does not require API keys.
   - Automatically provides European, US, and global technical job listings.
2. **RemoteOK (Free & Permitted Feed)**:
   - Does not require API keys.
   - Provides verified remote opportunities with published compensation brackets.
3. **Jobicy (Free & Public)**:
   - Does not require API keys.
   - Delivers international remote roles with clear geographic eligibility tags.
4. **Adzuna Global API (Optional)**:
   - To enable regional searches across 16+ countries, obtain free API keys from [Adzuna Developer Portal](https://developer.adzuna.com).
   - Add `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` to `backend/.env`.

---

## 16. Email & Outbound SMTP Setup

To enable automated recruiter outreach or application email dispatch:
1. Configure your SMTP provider in `backend/.env` (e.g. Gmail App Password, SendGrid, Amazon SES, or Mailgun):
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your_email@gmail.com
   SMTP_PASSWORD=your_app_specific_password
   SMTP_FROM_EMAIL=your_email@gmail.com
   SMTP_TLS=true
   ```
2. **Safety Guarantee**: If SMTP is not configured, JobPulse AI displays an honest `not_configured` notice and equips the user with a 1-click clipboard copy utility for the prepared outreach email. It will **never** claim an email was sent if credentials are not configured.

---

## 17. Running Tests

The backend includes a comprehensive automated test suite covering all modules, authentication flows, location filtering, parsing fallbacks, consent controls, and batch execution:

```powershell
# Navigate to backend directory and run pytest
cd backend
.\venv\Scripts\python.exe -m pytest tests/ -v
```

### Test Suite Summary:
```
======================= 83 passed, 1 warning in ~35s =======================
```
- `test_auth.py`: User registration, bcrypt hashing, JWT issuance, preference updates (7 tests).
- `test_resume_upload.py` & `test_resume_parsing.py`: PDF/Word parsing, OpenRouter fallbacks, local heuristics (23 tests).
- `test_jobs.py` & `test_location_and_matching.py`: Strict country filtering, state multi-select, AI match scoring (16 tests).
- `test_applications.py`, `test_auto_apply.py`, `test_auto_apply_workflow.py`: Consent enforcement, Direct API, Manual Portal kits, batch cancellation (23 tests).
- `test_module5.py`: Application tracker, safe retry, audit trail, data export, and notifications (7 tests).
- `test_worldwide_and_resiliency.py` & `test_verified_discovery_and_relevance.py`: Worldwide discovery, 429 recovery, URL hygiene (7 tests).

---

## 18. Resetting Data for Fresh Launch

To start the platform in a completely fresh state with **zero existing users, profiles, resumes, or application history** while preserving discovered public job listings:

### Safe Reset Utility (`backend/scripts/reset_user_data.py`)

1. **Create an automatic backup first**:
   ```bash
   python backend/scripts/backup_data.py
   ```
   *Creates a timestamped backup of `sql_app.db` and all uploaded files under `D:\projects\Ai-Job-Search_backups\`.*

2. **Run dry-run inspection**:
   ```bash
   python backend/scripts/reset_user_data.py --dry-run
   ```

3. **Execute confirmed reset**:
   ```bash
   python backend/scripts/reset_user_data.py --confirm
   ```

This utility safely purges all records in foreign-key safe order (`application_audit_logs` → `application_workspaces` → `saved_jobs` → `notifications` → `resumes` → `user_profiles` → `users`) and clears `backend/uploads/resumes/` while leaving `.gitkeep` intact and retaining all discovered public job listings.

---

## 19. Troubleshooting Guide

| Problem | Root Cause | Solution |
| ------- | ---------- | -------- |
| **Port 8000 or 5173 in use** | A previous instance is still running in the background. | Run `stop.bat` to terminate stranded processes, or use `netstat -ano \| findstr :8000` to find and kill the PID. |
| **OpenRouter returns HTTP 429** | Free tier upstream rate limits reached on shared model. | No action required: JobPulse AI automatically catches 429 and falls back to the deterministic local heuristic parser. |
| **Resume upload fails with 400** | Unsupported format or file size exceeded. | Ensure file is in `.pdf` or `.docx` format and smaller than 10MB. |
| **Frontend displays network error** | Backend is not running or CORS is misconfigured. | Verify backend is active on `http://127.0.0.1:8000` and check `VITE_API_BASE_URL` in `New Frontend/.env`. |
| **Missing database columns** | Older SQLite database version. | The backend runs `apply_migrations(engine)` automatically on boot to add any missing columns. |

---

## 20. Security & Privacy Practices

- **Zero Credential Exposure**: Passwords are never stored in plaintext and are salted using `bcrypt`.
- **Secret Redaction**: API keys and SMTP credentials are never sent to the browser client or logged.
- **Isolated Storage**: Resumes are stored with unique internal identifiers in isolated directories and cannot be accessed without an authorized JWT token.
- **Data Deletion Rights**: Candidates can permanently delete their entire account and all associated files at any time via `/settings` or `DELETE /api/v1/auth/delete-account`.

---

## 21. Contributing Guidelines

We welcome community contributions, bug fixes, and additional job feed adapters! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming conventions, pull request checklists, and code standards.

All pull requests must pass:
```bash
# Backend tests
pytest tests/

# Frontend typecheck & build
npm run build
```

---

## 22. License Information

JobPulse AI is licensed under the open-source **[MIT License](LICENSE)**. You are free to use, modify, distribute, and deploy this project in personal and commercial environments.

---

## 23. Acknowledgments & Credits

- [FastAPI](https://fastapi.tiangolo.com/) by Sebastián Ramírez
- [React](https://react.dev/) by the Meta team and open source community
- [Tailwind CSS](https://tailwindcss.com/) by Adam Wathan & Tailwind Labs
- [Three.js](https://threejs.org/) by Ricardo Cabello (mrdoob)
- [Arbeitnow](https://www.arbeitnow.com/), [RemoteOK](https://remoteok.com/), and [Jobicy](https://jobicy.com/) for maintaining free, open job listing APIs.

---

## 24. API Reference Summary

Interactive Swagger UI documentation is available at `http://127.0.0.1:8000/docs`. Key routes include:

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| `POST` | `/api/v1/auth/signup` | Register a new user account |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain JWT access token |
| `GET` | `/api/v1/auth/me` | Retrieve authenticated user profile |
| `GET` | `/api/v1/auth/export-data` | Export complete personal career archive (JSON) |
| `DELETE` | `/api/v1/auth/delete-account` | Permanently wipe account and data |
| `POST` | `/api/v1/resume/upload` | Upload and parse candidate resume (.pdf/.docx) |
| `GET` | `/api/v1/jobs/search` | Search opportunities with country and state filters |
| `GET` | `/api/v1/jobs/locations` | List supported countries and regions |
| `POST` | `/api/v1/jobs/{job_id}/select-apply` | Queue job for application preparation |
| `GET` | `/api/v1/applications/workspaces` | Get queued application workspaces |
| `POST` | `/api/v1/applications/{app_id}/apply` | Execute consent-verified application |
| `GET` | `/api/v1/applications/tracker` | Search and filter submitted applications |

---

## 25. Production Deployment Considerations

When deploying JobPulse AI to a production cloud server (AWS, GCP, DigitalOcean, Render, or Railway):
1. **Change SECRET_KEY**: Generate a cryptographically strong secret (`openssl rand -hex 32`) and update `backend/.env`.
2. **Use a Managed Database**: Set `DATABASE_URL` to a managed PostgreSQL cluster.
3. **Configure CORS**: Set `CORS_ORIGINS` to your exact production domain.
4. **Static Asset Hosting**: Build the frontend (`npm run build`) and serve via Nginx, Cloudflare Pages, or AWS S3/CloudFront.
5. **Worker Concurrency**: Run Uvicorn with multiple workers behind a reverse proxy (`gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`).

---

## 26. Frequently Asked Questions (FAQ)

#### Q: Does JobPulse AI apply to hundreds of jobs without my review?
**A**: **No.** JobPulse AI is designed around explicit user consent. Every application, cover letter, and recruiter email is staged in your Review Center for your approval before anything is sent.

#### Q: Do I need a paid OpenAI or OpenRouter subscription to use this?
**A**: **No.** The platform includes a deterministic local heuristic parser and template generator that works 100% offline without requiring paid API keys.

#### Q: Can employers detect that my application used JobPulse AI?
**A**: Because JobPulse AI does not use unauthorized bots or spam repetitive templates, but instead crafts tailored, truthful content and directs you to official employer portals, your applications look natural, professional, and authentic.

#### Q: How can I reset the application to a clean state for a new candidate?
**A**: Run `python backend/scripts/reset_user_data.py --confirm`. It immediately purges all user accounts and files while leaving the job opportunity cache intact.
