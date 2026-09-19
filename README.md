# MercariBOT

A lightweight, asynchronous, and security-hardened monitoring bot for Mercari Japan listings, providing instant Telegram notifications and real-time currency conversion.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
  - [Telegram Setup](#telegram-setup)
  - [Environment Variables (.env)](#environment-variables-env)
  - [Search Rules (config.toml)](#search-rules-configtoml)
- [Running the Bot](#running-the-bot)
  - [Windows](#windows)
  - [Linux and macOS](#linux-and-macos)
  - [Docker](#docker)
- [Command-Line Options](#command-line-options)
- [Security and Hardening](#security-and-hardening)
- [Testing](#testing)
- [Acknowledgments and Inspiration](#acknowledgments-and-inspiration)
- [License](#license)

---

## Overview

Mercari Japan (jp.mercari.com) is one of the largest Japanese consumer-to-consumer marketplaces. However, tracking rare, vintage, or collectible items in real time requires continuous checking.

MercariBOT automates this monitoring process by periodically querying the Mercari Japan API for configured keywords, deduplicating newly listed items using a local SQLite database, and dispatching rich alerts to your Telegram chat with product images and prices converted to your local currency (EUR, USD, GBP, etc.).

---

## How It Works

1. **Asynchronous Scraping Engine**: Built on Python's `asyncio` and `httpx` connection pooling. It scans multiple keywords concurrently with controlled throttling to avoid rate-limiting.
2. **DPoP Authentication**: Mercari Japan requires Demonstrating Proof-of-Possession (DPoP) authentication headers for its search endpoints. The bot generates compliant in-memory ECDSA P-256 signatures with automated key rotation.
3. **Local SQLite Deduplication**: Replaces brittle JSON caches with an atomic local SQLite database in Write-Ahead Logging (WAL) mode. Only unseen items trigger alerts.
4. **Live Currency Conversion**: Fetches daily official foreign exchange rates from the European Central Bank via the Frankfurter API and caches rates for 12 hours. If offline, it smoothly falls back to a static configured rate.
5. **Telegram Dispatcher**: Formats and sends high-resolution product images and details with HTML escaping, respecting Telegram API quotas and backoff policies.

---

## Prerequisites

- Python 3.10 or higher
- A Telegram account and a bot token created via @BotFather

---

## Configuration

### Telegram Setup

1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow the prompts to choose a name and username.
3. Copy the HTTP API token provided by BotFather.
4. Obtain your personal or channel numerical Chat ID (for example, by messaging your bot and querying `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`, or by using `@userinfobot`).

### Environment Variables (.env)

Create a `.env` file in the project root based on `.env.example`:

```bash
cp .env.example .env
```

Set your credentials:

```env
TELEGRAM_TOKEN="123456789:ABCDefghIJKlmnoPQRstuvWXYZ"
TELEGRAM_CHAT_ID="123456789"
```

### Search Rules (config.toml)

Create a `config.toml` file based on `config.toml.example`:

```bash
cp config.toml.example config.toml
```

Configure your parameters and target searches:

```toml
# Interval in seconds between full scan sweeps
delay = 60

# Delay in seconds between individual keyword requests
request_delay = 1.5

# Maximum concurrent requests to Mercari API
max_concurrent_requests = 2

# Send product photo with caption (true) or text only (false)
downloadphotos = true

# Currency settings
auto_currency = true
target_currency = "EUR"
changerate = 0.0055

# Monitored searches
[[searches]]
keywords = "vintage jacket"
exclude_keywords = "damaged broken"

[[searches]]
keywords = "playstation 5"

[[searches]]
keywords = "pokemon card"
```

---

## Running the Bot

### Windows

#### Interactive Console
Double-click `run.bat`. This script automatically:
- Checks for Python in your system PATH.
- Creates the local virtual environment (`.venv`) if missing.
- Installs or updates dependencies.
- Starts MercariBOT in an interactive console window.

#### Silent Background Execution
Double-click `MercariBOT.vbs`. This script runs the bot silently in the background without opening a terminal window.

---

### Linux and macOS

#### Using the Automatic Launcher
Run the shell script:

```bash
./run.sh
```

#### Manual Installation and Execution
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python main.py
```

---

### Docker

Build and run the container using the hardened non-root image:

```bash
docker build -t mercaribot .

docker run -d \
  --name mercaribot \
  --restart unless-stopped \
  -v $(pwd)/config.toml:/app/config.toml \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/mercaribot.db:/app/mercaribot.db \
  mercaribot
```

---

## Command-Line Options

```bash
python main.py --help
```

| Argument | Description |
| :--- | :--- |
| `-c, --config <path>` | Specify a custom path to `config.toml` |
| `-e, --env <path>` | Specify a custom path to `.env` |
| `--dry-run` | Run search queries and test database deduplication without sending Telegram messages |
| `--test-telegram` | Send a test notification to Telegram to verify credentials, then exit |
| `--import-cache <path>` | Import item IDs from a legacy JSON cache into the SQLite database and exit |
| `-v, --verbose` | Enable verbose DEBUG logs |

---

## Security and Hardening

This project adheres to OWASP secure coding practices and DevSecOps principles:

- **OWASP A01 (Access Control)**: Restricts POSIX file permissions on `.env` and `mercaribot.db` to mode `0600` (read/write for owner only).
- **OWASP A02 (Cryptographic Failures)**: Ephemeral ECDSA P-256 key pairs for DPoP authentication are stored exclusively in memory and never written to persistent storage. HTTPS is enforced for all outbound traffic.
- **OWASP A03 (Injection)**: Uses 100% parameterized SQLite statements (`?`) to prevent SQL injection. All user-generated seller listings are sanitized using deterministic HTML entity escaping before rendering in Telegram messages.
- **OWASP A05 (Security Misconfiguration)**: The Docker container executes under a dedicated, unprivileged non-root user (`mercaribot`, UID 10001). Sensitive files are excluded via comprehensive `.gitignore` rules.
- **OWASP A09 (Security Logging)**: Integrated `SecretMaskingFilter` intercepts all log records in real time and automatically redacts Telegram bot tokens and API credentials to prevent sensitive data leaks.
- **OWASP A10 (Server-Side Request Forgery)**: Image URLs from API payloads are validated against a strict domain whitelist (`*.mercdn.net`, `*.mercari-shops-static.com`) and reject private IP addresses, loopback addresses, and cloud metadata endpoints.
- **DevSecOps Pipeline**: Automated GitHub Actions CI pipeline running Bandit (SAST), Pip-Audit (SCA), Ruff (linter), and Pytest.

---

## Testing

Run the full automated test suite covering crypto signatures, SQLite persistence, input validation, currency conversion, and SSRF filtering:

```bash
pytest -v
```

---

## Acknowledgments and Inspiration

This project was originally inspired by the concept of `mercari-watchdog` by Thibaut Bremand. It has been completely redesigned and rewritten from the ground up as a modern, asynchronous, robust, and security-hardened tool.

---

## License

This project is licensed under the [MIT License](LICENSE).
