# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x   | Yes |
| < 2.0.0 | No                |

## Reporting a Vulnerability

We take the security and integrity of MercariBOT seriously. If you discover a security vulnerability, please follow the responsible disclosure guidelines below.

### How to Report

1. **Do NOT file a public issue** on GitHub for security vulnerabilities.
2. Please report security issues privately via GitHub Security Advisories or by emailing the project maintainer.
3. Provide a clear description of the vulnerability, including:
   - Steps to reproduce or proof-of-concept (PoC).
   - Potential impact and affected components.
   - Recommended mitigations if available.

### Response Time

- You will receive an acknowledgment of your report within 48 hours.
- A remediation plan will be communicated and tested before releasing a public patch.

## Security Controls Implemented

- **OWASP A01 (Access Control)**: POSIX 0600 file permissions on local secrets (`.env`) and database (`mercaribot.db`).
- **OWASP A02 (Cryptographic Hygiene)**: In-memory ephemeral ECDSA P-256 key pairs for DPoP signatures, TLS 1.2+ enforcement.
- **OWASP A03 (Injection)**: Parameterized SQL queries on SQLite, strict HTML escaping for Telegram messages.
- **OWASP A09 (Security Logging)**: Automatic real-time regex redaction of Telegram bot tokens and API credentials from logs.
- **OWASP A10 (SSRF Prevention)**: Strict domain whitelisting and protocol enforcement for remote image URLs.
- **Automated DevSecOps**: Continuous integration pipeline running `bandit` (SAST), `pip-audit` (SCA), and `ruff` on every commit.
