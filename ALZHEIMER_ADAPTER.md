# Alzheimer Adapter for xiaogpt

This adapter allows xiaogpt to forward voice input text and intent data to the [Alzheimer](https://github.com/yangrudan/alzheimer) backend system.

## Features

- **Non-invasive integration**: The adapter is disabled by default and only activates when configured
- **Asynchronous forwarding**: Text is forwarded to Alzheimer backend without blocking xiaogpt's normal operation
- **Optional authentication**: Supports Bearer token authentication for secure API access
- **Flexible configuration**: Can be configured via environment variables, CLI arguments, or config file

## Configuration

### Via Environment Variables

```bash
export ALZ_BASE_URL="https://alzheimer.example.com"
export ALZ_API_TOKEN="your_api_token_here"  # Optional
```

### Via Command Line Arguments

```bash
xiaogpt --hardware LX06 \
  --use_chatgpt_api \
  --alz_base_url "https://alzheimer.example.com" \
  --alz_api_token "your_api_token_here"
```

### Via Configuration File

Create or modify your `xiao_config.yaml`:

```yaml
hardware: "LX06"
use_chatgpt_api: true

# Alzheimer adapter settings
alz_base_url: "https://alzheimer.example.com"
alz_api_token: "your_api_token_here"  # Optional
```

Then run:

```bash
xiaogpt --config xiao_config.yaml
```

## How It Works

When enabled (by setting `alz_base_url`), the adapter:

1. Listens for voice queries processed by xiaogpt
2. Extracts the text content from the query
3. Forwards the data to `{alz_base_url}/api/voice/webhook` as a POST request
4. Includes device_id, user_id (if available), and the text content

### Payload Format

The adapter sends the following JSON payload:

```json
{
  "text": "用户说的话",
  "device_id": "xiaomi_device_id",
  "user_id": "xiaomi_user_id",
  "intent": null,
  "slots": null
}
```

### Authentication

If `alz_api_token` is configured, the adapter includes it in the request headers:

```
Authorization: Bearer {alz_api_token}
```

## Testing

### Test with a Mock Server

You can test the adapter with a simple mock server:

```python
# mock_alzheimer_server.py
from aiohttp import web

async def webhook(request):
    data = await request.json()
    print(f"Received webhook: {data}")
    return web.json_response({"status": "ok", "received": data})

app = web.Application()
app.router.add_post('/api/voice/webhook', webhook)

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=8080)
```

Run the mock server:

```bash
python mock_alzheimer_server.py
```

Then configure xiaogpt to use it:

```bash
export ALZ_BASE_URL="http://localhost:8080"
xiaogpt --hardware LX06 --use_chatgpt_api
```

## Disabling the Adapter

The adapter is disabled by default. To explicitly disable it:

- Don't set `ALZ_BASE_URL` environment variable
- Don't include `alz_base_url` in your config file
- Don't pass `--alz_base_url` as a CLI argument

## Troubleshooting

### Enable Verbose Logging

To see adapter activity:

```bash
xiaogpt --config xiao_config.yaml --verbose
# or
xiaogpt --config xiao_config.yaml -vv  # Even more verbose
```

### Check Logs

The adapter logs its activity:
- `INFO` level: Successful forwards
- `WARNING` level: Failed forwards
- `DEBUG` level: Adapter enabled/disabled status

### Common Issues

1. **Adapter not forwarding**
   - Check that `alz_base_url` is set and not empty
   - Verify the URL is accessible from your xiaogpt instance

2. **Authentication errors**
   - Verify your `alz_api_token` is correct
   - Check that the Alzheimer backend expects Bearer token authentication

3. **Connection timeouts**
   - Ensure the Alzheimer backend is running and accessible
   - Check firewall rules if running on different networks

## Integration with Alzheimer Backend

The Alzheimer backend should implement a webhook endpoint at `/api/voice/webhook` that:

- Accepts POST requests with JSON payload
- Expects fields: `text` (required), `device_id` (required), `user_id` (optional), `intent` (optional), `slots` (optional)
- Optionally validates Bearer token authentication
- Returns JSON response (any format is acceptable)

Example implementation in the Alzheimer backend:

```python
@app.post("/api/voice/webhook")
async def voice_webhook(request: VoiceWebhookRequest):
    # Process the incoming voice text
    text = request.text
    device_id = request.device_id
    user_id = request.user_id
    
    # Your processing logic here
    result = process_voice_input(text, device_id, user_id)
    
    return {"status": "ok", "result": result}
```

## Security Considerations

- Always use HTTPS for production deployments
- Keep your `alz_api_token` secret
- Consider implementing rate limiting on the Alzheimer backend
- Validate and sanitize incoming data on the backend

## License

This adapter is part of xiaogpt and is licensed under the MIT License.
