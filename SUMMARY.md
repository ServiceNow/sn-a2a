# Summary: ServiceNow A2A Agent Testing

## Current Status: BLOCKED ⚠️

The integration is blocked by a **contradictory push notification requirement** from the ServiceNow agent.

## Critical Issue: Push Notification Contradiction

### Error Messages

The ServiceNow agent returns **contradictory errors** depending on whether push notifications are included in the request:

**Error #1 - Without Push Notification URL:**
```
Script: sn_aia.AIAgentProviderA2AUtil: AIAgentProviderA2AUtil faced error with code: -32602
message: Invalid method parameters: Push Notification URL is required for asynchronous requests
method: _validateParams
```

**Error #2 - With Push Notification URL:**
```
Script: sn_aia.AIAgentProviderA2AUtil: AIAgentProviderA2AUtil faced error with code: -32003
message: Push Notification is not supported
method: _handleTaskSend
```

### The Problem

The system oscillates between these two contradictory errors:
- **WITHOUT** `pushNotificationConfig` → Error -32602: "Push Notification URL is required"
- **WITH** `pushNotificationConfig` → Error -32003: "Push Notification is not supported"

This suggests a **configuration mismatch** on the ServiceNow server side where:
1. The agent card advertises `"pushNotifications": true` in capabilities
2. The validation layer (`_validateParams`) requires push notification URL
3. The execution layer (`_handleTaskSend`) rejects push notifications as unsupported

## Issues Resolved

### Issue #1: Invalid acceptedOutputModes (RESOLVED - 2025-10-12)

**Error Message:**
```
Script: sn_aia.AIAgentProviderA2AUtil: AIAgentProviderA2AUtil faced error with code: -32602
message: Invalid method parameters: Invalid acceptedOutputModes value
```

**Root Cause:**
The A2A Inspector was requesting output modes the ServiceNow agent doesn't support:
```python
# WRONG - backend/app.py:344 (before fix)
accepted_output_modes=['text/plain', 'video/mp4', 'application/json']
```

The ServiceNow agent only supports:
```json
"defaultOutputModes": ["application/json"]
```

**Fix Applied:**
Updated [backend/app.py:344](../a2a-inspector/backend/app.py#L344) to only request supported modes:
```python
# CORRECT - backend/app.py:344 (after fix)
acceptedOutputModes=['application/json']
```

## Sample Payloads

### Payload WITHOUT Push Notification Config (Results in Error -32602)
```json
{
  "id": "msg-1760334652965-walfvwh96",
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "configuration": {
      "acceptedOutputModes": ["application/json"]
    },
    "message": {
      "kind": "message",
      "messageId": "msg-1760334652965-walfvwh96",
      "metadata": {},
      "parts": [
        {
          "kind": "text",
          "text": "Categorize ITSM Incident INC0019104"
        }
      ],
      "role": "user"
    }
  }
}
```

**Result:** Error -32602: "Push Notification URL is required for asynchronous requests"

### Payload WITH Push Notification Config (Results in Error -32003)
```json
{
  "id": "msg-1760334652965-walfvwh96",
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "configuration": {
      "acceptedOutputModes": ["application/json"],
      "pushNotificationConfig": {
        "url": "https://634585affe67.ngrok-free.app/push-notification"
      }
    },
    "message": {
      "kind": "message",
      "messageId": "msg-1760334652965-walfvwh96",
      "metadata": {},
      "parts": [
        {
          "kind": "text",
          "text": "Categorize ITSM Incident INC0019104"
        }
      ],
      "role": "user"
    }
  }
}
```

**Result:** Error -32003: "Push Notification is not supported"

## What Works

✅ **OAuth Token Refresh** - Successfully implemented `refresh_token()` function
✅ **Agent Card Retrieval** - Can fetch agent metadata and capabilities
✅ **Authentication** - OAuth scope `a2aauthscope` properly configured
✅ **A2A Inspector Backend** - Server runs and handles connections
✅ **acceptedOutputModes Fixed** - Now correctly sends only `["application/json"]`
✅ **Payload Construction** - Properly formatted JSON-RPC 2.0 requests

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

1. **Contact ServiceNow Admin** - This is a **server-side configuration issue** that must be fixed by the ServiceNow team:
   - The agent card claims `"pushNotifications": true` but the backend rejects push notifications
   - Either enable full push notification support OR update agent card to `"pushNotifications": false`
   - The validation layer (`_validateParams`) and execution layer (`_handleTaskSend`) are inconsistent

2. **Check AIAgentProviderA2AUtil.js** - The ServiceNow script has conflicting logic:
   - `_validateParams` method requires push notification URL when `pushNotifications: true`
   - `_handleTaskSend` method rejects requests with push notification config

3. **Investigate existing working implementations** - Check if other clients successfully connect:
   - How does the [langgraph-agent-dev](../agenticai/langgraph-agent-dev/main.py) handle this agent?
   - Are there other A2A clients that work with this ServiceNow instance?

## Files Created

- [../sn-a2a/main.py](../sn-a2a/main.py) - Simple CLI (blocked by push notification requirement)
- [../sn-a2a/.env](../sn-a2a/.env) - OAuth credentials
- [../sn-a2a/test_cli.py](../sn-a2a/test_cli.py) - Test script with token refresh
- [../sn-a2a/test_direct.py](../sn-a2a/test_direct.py) - Direct HTTP testing
- [../sn-a2a/test_with_inspector_api.py](../sn-a2a/test_with_inspector_api.py) - Inspector backend testing
- [../sn-a2a/TESTING_WITH_A2A_INSPECTOR.md](../sn-a2a/TESTING_WITH_A2A_INSPECTOR.md) - Usage guide

## Key Learnings

1. **Always check agent capabilities** before implementing clients - Review `defaultOutputModes` in agent card
2. **Match acceptedOutputModes to agent's capabilities** - ServiceNow validates this strictly on the server side
3. **Push notifications require publicly accessible endpoints** - Use ngrok for local development
4. **The A2A SDK handles many details**, but can't work around agent requirements
5. **Local development with async agents needs tunneling tools**
6. **Server-side validation errors** (like -32602 Invalid Params) often mean parameter mismatch with agent card specs
7. **This specific ServiceNow agent is designed for production server-to-server communication**
