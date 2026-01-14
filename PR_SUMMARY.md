# PR Summary: Alzheimer Adapter for xiaogpt

## Overview
This PR adds an optional Alzheimer backend adapter to xiaogpt, enabling seamless integration with the [yangrudan/alzheimer](https://github.com/yangrudan/alzheimer) backend system.

## Key Features

### 1. Non-invasive Integration
- **Disabled by default**: The adapter is completely inactive unless explicitly configured
- **No breaking changes**: Existing xiaogpt functionality remains unchanged
- **Optional dependency**: Works with existing aiohttp dependency already in the project

### 2. Flexible Configuration
The adapter can be enabled via three methods:

**Environment Variables:**
```bash
export ALZ_BASE_URL="https://alzheimer.example.com"
export ALZ_API_TOKEN="your_token"  # Optional
```

**CLI Arguments:**
```bash
xiaogpt --hardware LX06 --use_chatgpt_api \
  --alz_base_url "https://alzheimer.example.com" \
  --alz_api_token "your_token"
```

**Configuration File:**
```yaml
alz_base_url: "https://alzheimer.example.com"
alz_api_token: "your_token"  # Optional
```

### 3. Performance Optimized
- **Session reuse**: Shares the existing aiohttp ClientSession to avoid connection overhead
- **Asynchronous**: Forwarding happens in background tasks without blocking xiaogpt
- **Proper cleanup**: Tasks are tracked and cleaned up on shutdown

### 4. Robust Error Handling
- **Specific exceptions**: Handles aiohttp.ClientError explicitly
- **Graceful degradation**: Failures don't affect xiaogpt's main operation
- **Comprehensive logging**: INFO, WARNING, and DEBUG levels for troubleshooting

## Files Changed

### New Files
1. **`xiaogpt/adapters/alzheimer_adapter.py`** (130 lines)
   - Core adapter implementation with `AlzheimerAdapter` class
   - `forward_text_as_intent()` async method for forwarding data
   - Support for optional authentication via Bearer token

2. **`xiaogpt/adapters/__init__.py`** (1 line)
   - Package initialization file

3. **`ALZHEIMER_ADAPTER.md`** (190 lines)
   - Comprehensive documentation
   - Usage examples and configuration options
   - Testing guide with mock server
   - Troubleshooting section

4. **`alzheimer_adapter_example.yaml`** (20 lines)
   - Example configuration file
   - Ready-to-use template

5. **`test_alzheimer_adapter.py`** (141 lines)
   - Test script with mock webhook server
   - Demonstrates all adapter features
   - Tests all configuration methods

### Modified Files
1. **`xiaogpt/config.py`** (+3 lines)
   - Added `alz_base_url` and `alz_api_token` configuration fields
   - Both default to environment variables

2. **`xiaogpt/cli.py`** (+11 lines)
   - Added `--alz_base_url` and `--alz_api_token` CLI arguments

3. **`xiaogpt/xiaogpt.py`** (+31 lines)
   - Initialize AlzheimerAdapter with shared session
   - Forward queries to adapter when enabled
   - Track and cleanup forwarding tasks

4. **`README.md`** (+20 lines)
   - Added Alzheimer adapter section
   - Configuration table entries
   - Quick start example

## Technical Implementation

### Payload Format
The adapter sends the following JSON to `{base_url}/api/voice/webhook`:

```json
{
  "text": "用户说的话",
  "device_id": "xiaomi_device_id",
  "user_id": "xiaomi_user_id",     // Optional
  "intent": null,                   // Optional
  "slots": null                     // Optional
}
```

### Authentication
If `alz_api_token` is configured:
```
Authorization: Bearer {alz_api_token}
```

### Integration Points
The adapter is invoked in `xiaogpt.py` at line 414, right after processing the query but before asking the GPT bot. This ensures:
- The original query is captured (after keyword removal)
- The forwarding doesn't block the response to the user
- Device ID and User ID are available from the session

## Testing

### Automated Tests
The `test_alzheimer_adapter.py` script validates:
1. ✅ Basic forwarding without authentication
2. ✅ Forwarding with Bearer token authentication
3. ✅ Adapter disabled when not configured
4. ✅ Environment variable configuration

All tests pass successfully.

### Security Scan
- ✅ CodeQL analysis: 0 vulnerabilities found
- ✅ No secrets in code
- ✅ Proper input validation

### Code Review
Addressed all review comments:
- ✅ Reuse ClientSession for better performance
- ✅ Store task references for proper cleanup
- ✅ Specific exception handling (aiohttp.ClientError)
- ✅ Task cleanup in close() method

## Verification Checklist

- [x] Adapter is disabled by default
- [x] Adapter can be enabled via environment variables
- [x] Adapter can be enabled via CLI arguments
- [x] Adapter can be enabled via config file
- [x] Forwarding works without authentication
- [x] Forwarding works with Bearer token authentication
- [x] Tasks are properly cleaned up
- [x] No performance impact when disabled
- [x] No breaking changes to existing code
- [x] Documentation is comprehensive
- [x] Tests pass successfully
- [x] Code review feedback addressed
- [x] Security scan passed (0 vulnerabilities)

## Usage Example

```bash
# 1. Enable the adapter
export ALZ_BASE_URL="https://alzheimer.example.com"
export ALZ_API_TOKEN="secret_token_123"

# 2. Run xiaogpt normally
xiaogpt --hardware LX06 --use_chatgpt_api

# 3. When you ask xiaogpt a question like "今天天气怎么样"
#    - xiaogpt processes it normally
#    - The adapter forwards it to Alzheimer backend asynchronously
#    - Both systems work independently
```

## Future Enhancements (Not in this PR)
- Support for extracting intent/slots from xiaogpt responses
- Batch forwarding for multiple queries
- Retry logic with exponential backoff
- Metrics/monitoring integration

## Statistics
- **Total lines added**: 547
- **Total lines removed**: 0
- **New files**: 5
- **Modified files**: 4
- **Test coverage**: 4 test cases (all passing)
- **Security issues**: 0

## Compatibility
- **Python version**: 3.9+ (same as xiaogpt)
- **Dependencies**: Uses existing aiohttp dependency
- **Backward compatibility**: 100% (no breaking changes)

---

**Ready to merge**: All checks passed ✅
