"""Simple CLI to communicate with ServiceNow AI Agent via A2A protocol."""

import argparse
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


async def main(agent_sys_id: str = None):
    """Run the CLI loop to communicate with the A2A agent.

    Args:
        agent_sys_id: Optional agent sys_id to override .env file value
    """
    # Load environment variables
    load_dotenv()

    # Get configuration from .env
    base_url = os.getenv("A2A_CLIENT_BASE_URL")

    # Use command line agent_sys_id if provided, otherwise use .env value
    agent_id = agent_sys_id if agent_sys_id else os.getenv("A2A_CLIENT_AGENT_ID")

    if not agent_id:
        print("Error: Agent sys_id not provided. Use --agent-id parameter or set A2A_CLIENT_AGENT_ID in .env")
        return

    agent_card_path = (
        os.getenv("A2A_CLIENT_AGENT_CARD_PATH")
        + agent_id
        + os.getenv("A2A_CLIENT_AGENT_CARD_WELL_KNOWN_PATH")
    )
    client_id = os.getenv("A2A_CLIENT_ID")
    client_secret = os.getenv("A2A_CLIENT_SECRET")
    refresh_token_value = os.getenv("A2A_CLIENT_REFRESH_TOKEN")
    existing_auth_token = os.getenv("A2A_CLIENT_AUTH_TOKEN")

    if not all([base_url, agent_card_path]):
        print("Error: Missing required environment variables (A2A_CLIENT_BASE_URL, agent card path)")
        return

    auth_token = None

    # Get or refresh the auth token
    if existing_auth_token:
        print("Using existing auth token from A2A_CLIENT_AUTH_TOKEN...")
        auth_token = existing_auth_token
    elif all([client_id, client_secret, refresh_token_value]):
        print("No existing token found. Refreshing OAuth token...")
        try:
            auth_token = await refresh_token(base_url, client_id, client_secret, refresh_token_value)
            print("Token refreshed successfully!")
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return
    else:
        print("Error: No auth token or refresh credentials provided in .env file")
        return

   

    # Initialize HTTP client - agent card doesn't need auth, but agent communication does
    timeout = httpx.Timeout(300.0)

    async with httpx.AsyncClient(timeout=timeout) as httpx_client:
        # Get agent card (no auth needed)
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
            print(f"Error getting agent card: {e}")
            return

        # Set auth token for agent communication
        httpx_client.headers["Authorization"] = f"Bearer {auth_token}"


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
        print("Type your question to the agent and press Enter to send.")
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

            except httpx.HTTPStatusError as e:
                # If we get 401/403, try refreshing the token and retry once
                if e.response.status_code in [401, 403] and refresh_token_value:
                    print(f"\nAuth error during communication (status {e.response.status_code}), refreshing token...")

                    if not all([client_id, client_secret, refresh_token_value]):
                        print("Error: Cannot refresh token - missing OAuth credentials\n")
                        continue

                    try:
                        # Refresh the token
                        auth_token = await refresh_token(base_url, client_id, client_secret, refresh_token_value)
                        print("Token refreshed successfully! Retrying message...\n")

                        # Update the httpx client's auth header
                        httpx_client.headers["Authorization"] = f"Bearer {auth_token}"

                        # Retry sending the message
                        response_text_parts = []
                        task = None

                        async for event in client.send_message(message):
                            if isinstance(event, Message):
                                for part in event.parts:
                                    if hasattr(part.root, "text"):
                                        response_text_parts.append(part.root.text)
                            elif isinstance(event, tuple) and len(event) == 2:
                                task, update_event = event
                                if task.status and task.status.message:
                                    for part in task.status.message.parts:
                                        if hasattr(part.root, "text"):
                                            response_text_parts.append(part.root.text)

                        # Update context_id for conversation continuity
                        if task:
                            new_context_id = getattr(task, "context_id", None)
                            status_state = getattr(task.status, "state", None) if task.status else None

                            if status_state == "completed":
                                context_id = None
                            else:
                                context_id = new_context_id

                        # Print agent response
                        response_text = "\n".join(response_text_parts)
                        print(f"\nAgent: {response_text}\n")

                    except Exception as retry_error:
                        print(f"\nError after token refresh: {retry_error}\n")
                else:
                    print(f"\nError communicating with agent: {e}\n")
            except Exception as e:
                print(f"\nError communicating with agent: {e}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CLI to communicate with A2A agents via the A2A protocol"
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        help="Agent sys_id (overrides A2A_CLIENT_AGENT_ID in .env file)",
        default=None
    )

    args = parser.parse_args()
    asyncio.run(main(agent_sys_id=args.agent_id))
