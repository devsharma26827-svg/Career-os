import subprocess
import re
import sys

def scan_files():
    res = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=True
    )
    files = [f.strip() for f in res.stdout.strip().splitlines() if f.strip()]

    secret_patterns = [
        (re.compile(r"sk-[a-zA-Z0-9_\-]{20,}"), "Potential OpenAI Secret Key"),
        (re.compile(r"sk-or-v1-[a-f0-9]{32,}"), "OpenRouter API Key"),
        (re.compile(r"AIzaSy[a-zA-Z0-9_\-]{30,}"), "Google API Key"),
        (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub Personal Access Token"),
        (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "Private Cryptographic Key"),
    ]

    findings = []
    for file_path in files:
        if any(x in file_path.lower() for x in ["test", "conftest", "mock", ".example", "package-lock.json", "bun.lock"]):
            continue
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_no, line in enumerate(f, 1):
                    for pat, label in secret_patterns:
                        match = pat.search(line)
                        if match:
                            matched_str = match.group(0)
                            if any(dummy in matched_str.lower() for dummy in ["example", "placeholder", "your_", "change-this"]):
                                continue
                            findings.append((file_path, line_no, label, matched_str[:12] + "..."))
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    if findings:
        print("ALERT: Potential secrets found:")
        for f, l, label, preview in findings:
            print(f"  {f}:{l} [{label}] {preview}")
        sys.exit(1)
    else:
        print(f"PASS: Secret scan clean! {len(files)} files checked. Zero secrets found.")

if __name__ == "__main__":
    scan_files()
