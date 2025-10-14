"""Simple CLI to communicate with Categorize ITSM Incident Agent via A2A protocol."""

import asyncio
import os

import httpx
from dotenv import load_dotenv

from a2a.client import A2ACardResolver, ClientConfig, ClientFactory, create_text_message_object
from a2a.types import Message, Task


async def refresh_token(
    base_url: str, client_id: str, client_secret: str, refresh_token: str
) -> str:
    """Refresh the OAuth access token using the refresh token.

    Args:
        base_url: Base URL of the ServiceNow instance
        client_id: OAuth client ID
        client_secret: OAuth client secret
        refresh_token: Refresh token for obtaining new access token

    Returns:
        New access token

    Raises:
        Exception: If token refresh fails
    """
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


async def main():
    """Run the CLI loop to communicate with the A2A agent."""
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

    if not all([base_url, agent_card_path, client_id, client_secret, refresh_token_value]):
        print("Error: Missing required environment variables in .env file")
        return

    # Refresh the OAuth token
    print("Refreshing OAuth token...")
    try:
        auth_token = await refresh_token(base_url, client_id, client_secret, refresh_token_value)
        print("Token refreshed successfully!")
    except Exception as e:
        print(f"Error refreshing token: {e}")
        return

    print("Connecting to Categorize ITSM Incident Agent...")

    # Initialize HTTP client with authentication
    timeout = httpx.Timeout(300.0)
    auth_headers = {"Authorization": f"Bearer {auth_token}"}

    async with httpx.AsyncClient(timeout=timeout, headers=auth_headers) as httpx_client:
        # Get agent card
        try:
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=base_url,
                agent_card_path=agent_card_path,
            )
            agent_card = await resolver.get_agent_card()
            print(f"Connected to agent: {agent_card.name}")
            print(f"Description: {agent_card.description}\n")
        except Exception as e:
            print(f"Error connecting to agent: {e}")
            return

        # Initialize A2A client using ClientFactory
        # Set accepted_output_modes to "application/json" as required by ServiceNow backend
        config = ClientConfig(
            httpx_client=httpx_client,
            accepted_output_modes=["application/json"]
        )
        factory = ClientFactory(config)
        client = factory.create(agent_card)

        # Track context for conversation continuity
        context_id = None

        # CLI loop
        print("Type your question (e.g., 'Categorize ITSM Incident INC0019104')")
        print("Type 'quit' or 'exit' to end the session\n")

        while True:
            # Get user input
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            # Check for exit commands
            if user_input.lower() in ["quit", "exit"]:
                print("Goodbye!")
                break

            # Skip empty input
            if not user_input:
                continue

            # Create message using helper
            message = create_text_message_object(content=user_input)

            # Add context_id if we have one from a previous exchange
            if context_id:
                message.context_id = context_id

            # Send message to agent
            try:
                # The new API returns an async iterator of events
                response_text_parts = []
                task = None

                async for event in client.send_message(message):
                    if isinstance(event, Message):
                        # Handle message response
                        for part in event.parts:
                            if hasattr(part.root, "text"):
                                response_text_parts.append(part.root.text)
                    elif isinstance(event, tuple) and len(event) == 2:
                        # Handle (Task, UpdateEvent) tuple
                        task, update_event = event
                        if task.status and task.status.message:
                            for part in task.status.message.parts:
                                if hasattr(part.root, "text"):
                                    response_text_parts.append(part.root.text)

                # Update context_id for conversation continuity
                if task:
                    new_context_id = getattr(task, "context_id", None)
                    status_state = getattr(task.status, "state", None) if task.status else None

                    # Clear context if conversation is completed
                    if status_state == "completed":
                        context_id = None
                    else:
                        context_id = new_context_id

                # Print agent response
                response_text = "\n".join(response_text_parts)
                print(f"\nAgent: {response_text}\n")

            except Exception as e:
                print(f"\nError communicating with agent: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
