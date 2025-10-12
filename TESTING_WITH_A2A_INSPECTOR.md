# Testing the Categorize ITSM Incident Agent with A2A Inspector

The a2a-inspector is a web-based tool that provides a full interface for testing A2A agents. It handles push notifications properly, which is required by the "Categorize ITSM incident AI agent".

## Steps to Test

### 1. Navigate to the A2A Inspector Directory

```bash
cd /Users/vamsee.lakamsani/git/snc/main/itom-x/ml/a2a-inspector
```

### 2. Install Dependencies (if not already done)

```bash
uv sync
```

### 3. Start the A2A Inspector Server

```bash
uv run uvicorn backend.app:app --host 127.0.0.1 --port 5001
```

The server will start at `http://127.0.0.1:5001`

### 4. Open the Web Interface

Open your browser and go to:
```
http://127.0.0.1:5001
```

### 5. Configure the Agent Connection

In the web interface:

1. **Enter the Agent Card URL**:
   ```
   https://a2atwfmcp.service-now.com/api/sn_aia/a2a/id/900cf9f09f4f1210579fa9e9d90a1c4a/well_known/agent_json
   ```

2. **Add Custom Headers** (click "Add Custom Header"):
   - **Header Name**: `Authorization`
   - **Header Value**: `Bearer <YOUR_FRESH_TOKEN>`

   To get a fresh token, run this command (replace with your actual credentials from .env):
   ```bash
   curl -s --location '${A2A_CLIENT_BASE_URL}oauth_token.do' \
     --header 'Content-Type: application/x-www-form-urlencoded' \
     --data-urlencode 'grant_type=refresh_token' \
     --data-urlencode 'client_id=${A2A_CLIENT_ID}' \
     --data-urlencode 'client_secret=${A2A_CLIENT_SECRET}' \
     --data-urlencode 'refresh_token=${A2A_CLIENT_REFRESH_TOKEN}'
   ```

   Copy the `access_token` value from the response.

3. **Click "Connect to Agent"**

### 6. Test the Agent

Once connected, you should see:
- Agent name: "Categorize ITSM incident AI agent"
- Agent description and capabilities

Now you can send test messages:

**Example Test Messages:**
- `Categorize ITSM Incident INC0019104`
- `What is the status of incident INC0019104?`
- `Show me details for INC0019104`

### 7. View Responses

The a2a-inspector will:
- Show the request/response in the debug panel
- Display validation errors if any
- Show the agent's response in the chat interface

## Troubleshooting

### Token Expired (401/403 errors)
Get a fresh token using the curl command above and update the Authorization header.

### Connection Timeout
Check that:
- The ServiceNow instance is accessible
- The agent ID is correct
- Network connectivity is working

### Push Notification Errors
The a2a-inspector handles push notifications automatically through its backend server, so these should not occur.

## Features of A2A Inspector

- **Real-time Debugging**: See all requests/responses in JSON format
- **Validation**: Automatic validation of agent responses against A2A spec
- **Custom Headers**: Easy configuration of authentication headers
- **Agent Card Viewer**: View all agent capabilities and skills
- **Message History**: Track conversation context across multiple messages

## Alternative: Quick Token Refresh Script

You can also use our test script to get a token. Make sure your `.env` file is configured first:

```bash
cd /Users/vamsee.lakamsani/git/snc/main/itom-x/ml/sn-a2a
uv run python -c "
import asyncio
import os
from dotenv import load_dotenv
from test_cli import refresh_token

load_dotenv()

async def get_token():
    token = await refresh_token(
        os.getenv('A2A_CLIENT_BASE_URL'),
        os.getenv('A2A_CLIENT_ID'),
        os.getenv('A2A_CLIENT_SECRET'),
        os.getenv('A2A_CLIENT_REFRESH_TOKEN')
    )
    print(f'Bearer {token}')

asyncio.run(get_token())
"
```

Copy the entire output and use it as the Authorization header value.
