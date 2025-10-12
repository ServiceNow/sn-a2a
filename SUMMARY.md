# Summary: ServiceNow A2A Agent Testing

## Problem Discovered

The **"Categorize ITSM incident AI agent"** on ServiceNow has a **mandatory requirement for push notifications** that makes it incompatible with simple CLI tools or the current A2A Inspector implementation.

### Root Cause

The agent's capabilities show:
```json
"capabilities": {
  "streaming": false,
  "pushNotifications": true,
  "stateTransitionHistory": false
}
```

This means:
- The agent operates **asynchronously**
- It **requires** a `push_notification_url` in the message configuration
- Responses are sent via HTTP POST callback, not returned synchronously
- The server must be publicly accessible for the agent to send callbacks

### Error Encountered

```
400 Bad Request
"Invalid method parameters: Push Notification URL is required for asynchronous requests"
```

Even when we add `push_notification_url: "http://127.0.0.1:5001/push-notification"`, the ServiceNow agent likely:
1. Validates that the URL is publicly accessible
2. Rejects localhost URLs
3. Requires HTTPS URLs

## What Works

✅ **OAuth Token Refresh** - Successfully implemented `refresh_token()` function
✅ **Agent Card Retrieval** - Can fetch agent metadata and capabilities
✅ **Authentication** - OAuth scope `a2aauthscope` properly configured
✅ **A2A Inspector Backend** - Server runs and handles connections

## What Doesn't Work

❌ **Sending Messages** - Agent rejects requests without valid push notification URL
❌ **Local Testing** - localhost URLs not acceptable for callbacks
❌ **Simple CLI** - Cannot receive async callbacks without a server

## Solutions

### Option 1: Use ngrok to Expose Local Server (Quick Fix)

1. Install ngrok: `brew install ngrok`
2. Expose local server:
   ```bash
   ngrok http 5001
   ```
3. Use the ngrok HTTPS URL as push_notification_url:
   ```python
   push_notification_url = "https://abc123.ngrok.io/push-notification"
   ```
4. Update the A2A Inspector backend to use this URL

### Option 2: Deploy A2A Inspector to Cloud (Production)

Deploy the A2A Inspector to a cloud service with a public HTTPS endpoint:
- AWS Lambda + API Gateway
- Google Cloud Run
- Azure Functions
- Heroku/Railway

### Option 3: Request ServiceNow Agent Configuration Change

Ask the ServiceNow admin to:
- Enable synchronous mode for the agent
- Allow localhost URLs for development/testing
- Add streaming support (currently disabled)

### Option 4: Use the Existing LangGraph Agent

The existing [langgraph-agent-dev](../agenticai/langgraph-agent-dev/main.py) appears to work with this agent. It might:
- Already have ngrok/tunneling configured
- Use a different approach
- Have server-side configuration we're missing

## Recommended Next Steps

1. **Try ngrok approach** (fastest for testing)
2. **Check if existing langgraph agent works** and how it's configured
3. **Contact ServiceNow admin** to understand agent requirements

## Files Created

- [../sn-a2a/main.py](../sn-a2a/main.py) - Simple CLI (blocked by push notification requirement)
- [../sn-a2a/.env](../sn-a2a/.env) - OAuth credentials
- [../sn-a2a/test_cli.py](../sn-a2a/test_cli.py) - Test script with token refresh
- [../sn-a2a/test_direct.py](../sn-a2a/test_direct.py) - Direct HTTP testing
- [../sn-a2a/test_with_inspector_api.py](../sn-a2a/test_with_inspector_api.py) - Inspector backend testing
- [../sn-a2a/TESTING_WITH_A2A_INSPECTOR.md](../sn-a2a/TESTING_WITH_A2A_INSPECTOR.md) - Usage guide

## Key Learnings

1. **Always check agent capabilities** before implementing clients
2. **Push notifications require publicly accessible endpoints**
3. **The A2A SDK handles many details**, but can't work around agent requirements
4. **Local development with async agents needs tunneling tools**
5. **This specific ServiceNow agent is designed for production server-to-server communication**
