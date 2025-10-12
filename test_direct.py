"""Test direct HTTP call to see the actual error message."""

import asyncio
import json
import os
from uuid import uuid4

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


async def test_direct():
    """Test with direct HTTP call to see exact error."""
    load_dotenv()

    base_url = os.getenv("A2A_CLIENT_BASE_URL")
    client_id = os.getenv("A2A_CLIENT_ID")
    client_secret = os.getenv("A2A_CLIENT_SECRET")
    refresh_token_value = os.getenv("A2A_CLIENT_REFRESH_TOKEN")
    agent_id = os.getenv("A2A_CLIENT_AGENT_ID")

    print("Refreshing token...")
    auth_token = await refresh_token(base_url, client_id, client_secret, refresh_token_value)
    print(f"Token: {auth_token[:30]}...\n")

    # Direct HTTP POST
    url = f"{base_url}api/sn_aia/a2a/v1/agent/id/{agent_id}"

    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "role": "user",
                "parts": [{"kind": "text", "text": "Categorize ITSM Incident INC0019104"}],
                "messageId": uuid4().hex,
            }
            # Remove configuration section - working code doesn't use it
        }
    }

    print(f"Sending request to: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}\n")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response body:\n{json.dumps(response.json(), indent=2)}")


if __name__ == "__main__":
    asyncio.run(test_direct())
