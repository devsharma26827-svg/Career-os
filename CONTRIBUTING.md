# Contributing to JobPulse AI

Thank you for your interest in contributing to JobPulse AI! We welcome contributions that preserve our core principles of **candidate privacy**, **ethical automation**, **zero fabrication**, and **accessible, high-performance UI engineering**.

---

## Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free environment for everyone. Please be respectful and constructive in all communications and reviews.

---

## Architectural Principles & Constraints

When developing or proposing changes for JobPulse AI:

1. **Anti-Fabrication Policy**:
   - The platform must **never** hallucinate, invent, or extrapolate candidate skills, qualifications, work authorizations, dates, or application responses.
   - Applications must never report `applied` or `submitted` status without verifiable external proof (e.g., successful partner ATS response, confirmed SMTP delivery receipt, or explicit user confirmation for manual portals).
2. **Strict User Consent**:
   - All external dispatches (portal applications, outbound recruiter emails) require explicit, affirmative user authorization.
   - Background or automated submissions without user awareness are strictly prohibited.
3. **Provider Fallback & Zero Paid Lock-In**:
   - Features must operate gracefully offline or with free tiers.
   - The resume parser and content generator must maintain a deterministic local heuristic fallback if LLM/API keys are omitted or rate-limited.
4. **UI Design & Accessibility**:
   - All new UI elements must support dynamic typography scaling (`16px`, `18px`, `20px`), reduced-motion mode, visible keyboard focus indicators, and WCAG AA contrast standards.
   - Do not replace or simplify the futuristic Three.js particle globe or visual design system without prior consensus.

---

## Development Setup

### Prerequisites
- **Python 3.10+** (Python 3.11 recommended)
- **Node.js 18+** (Node.js 20 LTS recommended)
- **Git**

### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Run database migrations and start development server
python run.py
```
Backend API will be accessible at `http://127.0.0.1:8000`. Swagger documentation is available at `http://127.0.0.1:8000/docs`.

### Frontend Setup
```bash
# Navigate to New Frontend directory
cd "New Frontend"

# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Start Vite dev server
npm run dev
```
Frontend will be accessible at `http://localhost:5173`.

---

## Running Tests

All pull requests must pass the complete backend test suite and frontend type/lint checks.

### Backend Tests
```bash
cd backend
python -m pytest tests/ -v
```

### Frontend Build & Lint Checks
```bash
cd "New Frontend"
npm run lint
npm run build
```

---

## Submitting Pull Requests

1. **Fork the repository** and create a feature branch (`git checkout -b feature/amazing-feature`).
2. **Follow commit conventions**: Use clear Conventional Commit prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
3. **Write tests**: Add unit or integration tests for any new endpoints, parser rules, or services.
4. **Run linters and tests**: Ensure `pytest` passes with 0 failures and `npm run build` generates a clean bundle.
5. **Open a Pull Request**: Fill out the PR template describing the changes, motivation, test results, and any security or privacy implications.
