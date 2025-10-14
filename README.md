# ServiceNow A2A CLI

A simple command-line interface to communicate with the "Categorize ITSM Incident Agent" using the A2A (Agent-to-Agent) protocol.

## Features

- Direct A2A protocol communication with ServiceNow incident categorization agent
- OAuth token refresh function for secure authentication
- Context-aware multi-turn conversations
- Simple setup using UV package manager

## Prerequisites

- Python 3.11 or higher
- UV package manager
- ServiceNow instance with A2A agent configured
- OAuth credentials with `a2aauthscope` permission

## Setup

1. **Copy the example environment file**:
   ```bash
   cp .env.example .env
   ```

2. **Configure your credentials in `.env`**:
   - `A2A_CLIENT_BASE_URL`: Your ServiceNow instance URL
   - `A2A_CLIENT_AGENT_ID`: The sys_id of your A2A agent
   - `A2A_CLIENT_ID`: OAuth client ID
   - `A2A_CLIENT_SECRET`: OAuth client secret
   - `A2A_CLIENT_REFRESH_TOKEN`: Long-lived refresh token

3. **Install dependencies**:
   ```bash
   uv sync
   ```
4. **Run it**:
* CLI loop: `uv run python main.py`

## Security Notes

- **Never commit `.env` files** - they contain secrets!
- The `.gitignore` file is configured to exclude `.env` files
- Use `.env.example` as a template (contains no real credentials)
- Refresh tokens are valid for 100 days; access tokens expire in 30 minutes


## Future Testing with Push notifications

Use the **A2A Inspector** web-based tool instead, which supports push notifications via ngrok:

See [TESTING_WITH_A2A_INSPECTOR.md](./TESTING_WITH_A2A_INSPECTOR.md) for complete instructions.

## Files in This Project

- `main.py` - Simple CLI (blocked by push notification requirement)
- `.env.example` - Template for environment variables (no secrets)
- `.env` - Your actual credentials (**git-ignored**)
- `TESTING_WITH_A2A_INSPECTOR.md` - How to use the web-based inspector

## Contributing

When contributing, remember:

1. Never commit `.env` files
2. Use environment variables for all credentials
3. Test with `.env.example` to ensure it has all required fields
4. Update documentation if adding new environment variables
