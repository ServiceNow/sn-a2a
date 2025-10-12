"""Test script to verify the CLI works with a sample prompt."""

import asyncio
import os
from uuid import uuid4

import httpx
from dotenv import load_dotenv

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import MessageSendParams, SendMessageRequest


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


async def test_cli():
    """Test the CLI with a sample prompt."""
    # Load environment variables
    load_dotenv()

    # Get configuration from .env
    base_url = os.getenv("A2A_CLIENT_BASE_URL")
    agent_card_path = (
        os.getenv("A2A_CLIENT_AGENT_CARD_PATH")
        + os.getenv("A2A_CLIENT_AGENT_ID")
        + os.getenv("A2A_CLIENT_AGENT_CARD_WELL_KNOWN_PATH")
    )
    client_id = os.getenv("A2A_CLIENT_ID")
    client_secret = os.getenv("A2A_CLIENT_SECRET")
    refresh_token_value = os.getenv("A2A_CLIENT_REFRESH_TOKEN")

    print("Step 1: Refreshing OAuth token...")
    try:
        auth_token = await refresh_token(
            base_url, client_id, client_secret, refresh_token_value
        )
        print(f"✓ Token refreshed successfully! (token starts with: {auth_token[:20]}...)")
    except Exception as e:
        print(f"✗ Error refreshing token: {e}")
        return

    print("\nStep 2: Connecting to agent...")
    timeout = httpx.Timeout(300.0)
    auth_headers = {"Authorization": f"Bearer {auth_token}"}

    # Create httpx client WITH default auth headers (for send_message calls)
    async with httpx.AsyncClient(timeout=timeout, headers=auth_headers) as httpx_client:
        try:
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=base_url,
                agent_card_path=agent_card_path,
            )
            # Pass auth headers only to get_agent_card
            agent_card = await resolver.get_agent_card(
                http_kwargs={"headers": auth_headers}
            )
            print(f"✓ Connected to agent: {agent_card.name}")
            print(f"  Description: {agent_card.description}")
        except Exception as e:
            print(f"✗ Error connecting to agent: {e}")
            return

        print("\nStep 3: Sending test message...")
        client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

        test_message = "Categorize ITSM Incident INC0019104"
        print(f"  Message: '{test_message}'")

        # Match the working code structure exactly - NO configuration section
        send_message_payload = {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": test_message}],
                "messageId": uuid4().hex,
            }
        }

        try:
            request = SendMessageRequest(
                id=str(uuid4()), params=MessageSendParams(**send_message_payload)
            )
            print(f"\n  DEBUG - Request payload:")
            print(f"  {request.model_dump(exclude_none=True)}")

            # DON'T pass http_kwargs - let the SDK handle auth via the httpx_client
            response = await client.send_message(request)

            result_obj = (
                getattr(response, "result", None)
                or getattr(response, "root", None).result
            )

            status_msg = result_obj.status.message
            parts = status_msg.parts
            response_text = "\n".join(
                getattr(part.root, "text", "")
                for part in parts
                if hasattr(part, "root") and hasattr(part.root, "text")
            )

            print(f"\n✓ Agent response received:")
            print(f"  {response_text}")
            print("\n✓ Test completed successfully!")

        except Exception as e:
            print(f"✗ Error sending message: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_cli())
