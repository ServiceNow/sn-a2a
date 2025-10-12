"""Test the agent via the A2A Inspector backend API directly."""

import asyncio
import json
import os

import httpx
from dotenv import load_dotenv


async def refresh_token(
    base_url: str, client_id: str, client_secret: str, refresh_token: str
) -> str:
    """Refresh the OAuth access token using the refresh token."""
    token_url = f"{base_url.rstrip('/')}/oauth_token.do"

    payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            raise Exception(
                f"Failed to refresh token: {response.status_code} - {response.text}"
            )

        token_data = response.json()
        return token_data["access_token"]


async def test_via_inspector():
    """Test the agent via the A2A Inspector backend API."""
    load_dotenv()

    # Get configuration
    base_url = os.getenv("A2A_CLIENT_BASE_URL")
    agent_card_url = (
        f"{base_url}api/sn_aia/a2a/id/"
        f"{os.getenv('A2A_CLIENT_AGENT_ID')}/well_known/agent_json"
    )
    client_id = os.getenv("A2A_CLIENT_ID")
    client_secret = os.getenv("A2A_CLIENT_SECRET")
    refresh_token_value = os.getenv("A2A_CLIENT_REFRESH_TOKEN")

    print("Step 1: Refreshing OAuth token...")
    auth_token = await refresh_token(
        base_url, client_id, client_secret, refresh_token_value
    )
    print(f"✓ Token: {auth_token[:30]}...\n")

    print("Step 2: Testing via A2A Inspector backend API...")
    print(f"Inspector URL: http://127.0.0.1:5001")
    print(f"Agent Card URL: {agent_card_url}")
    print()

    # Test the /agent-card endpoint (this is how the UI connects)
    inspector_url = "http://127.0.0.1:5001"

    # Create a fake session ID for testing
    sid = "test-session-123"

    async with httpx.AsyncClient() as client:
        # Step 1: Get agent card via the inspector backend
        print("Step 3: Getting agent card via Inspector backend...")
        response = await client.post(
            f"{inspector_url}/agent-card",
            json={"url": agent_card_url, "sid": sid},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        print(f"Status: {response.status_code}")
        result = response.json()

        if "card" in result:
            print(f"✓ Connected to: {result['card']['name']}")
            print(f"  Description: {result['card']['description']}")

            if result.get("validation_errors"):
                print(f"\n⚠️  Validation errors: {result['validation_errors']}")
        else:
            print(f"✗ Error: {result}")
            return

    print("\n" + "="*60)
    print("SUCCESS! The A2A Inspector backend can connect to the agent.")
    print("="*60)
    print("\nTo use the web UI:")
    print("1. Open: http://127.0.0.1:5001")
    print("2. Click the '► HTTP Headers' section to expand it")
    print("3. Click '+ Add Header' button")
    print("4. Enter:")
    print(f"   - Header Name: Authorization")
    print(f"   - Header Value: Bearer <paste_your_fresh_token>")
    print(f"5. Enter Agent URL: {agent_card_url}")
    print("6. Click 'Connect'")
    print("7. Send message: 'Categorize ITSM Incident INC0019104'")
    print(f"\nYour current token (expires in ~30 mins): {auth_token[:30]}...")


if __name__ == "__main__":
    asyncio.run(test_via_inspector())
