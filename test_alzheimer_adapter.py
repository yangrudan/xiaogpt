#!/usr/bin/env python3
"""Test script for the Alzheimer adapter.

This script demonstrates how to use the AlzheimerAdapter and includes
a simple mock server for testing.
"""

import asyncio
import logging
from aiohttp import web

from xiaogpt.adapters.alzheimer_adapter import AlzheimerAdapter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def mock_webhook(request):
    """Mock webhook endpoint for testing."""
    data = await request.json()
    print(f"\n✓ Mock webhook received data:")
    print(f"  - Text: {data.get('text')}")
    print(f"  - Device ID: {data.get('device_id')}")
    print(f"  - User ID: {data.get('user_id')}")
    print(f"  - Intent: {data.get('intent')}")
    print(f"  - Slots: {data.get('slots')}\n")
    
    # Check for authentication header
    auth_header = request.headers.get('Authorization')
    if auth_header:
        print(f"  - Authorization: {auth_header[:20]}...\n")
    
    return web.json_response({
        "status": "ok",
        "message": "Data received successfully",
        "echo": data
    })


async def start_mock_server():
    """Start a mock Alzheimer backend server."""
    app = web.Application()
    app.router.add_post('/api/voice/webhook', mock_webhook)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    print("🚀 Mock Alzheimer server started on http://localhost:8080")
    print("   Webhook endpoint: http://localhost:8080/api/voice/webhook\n")
    return runner


async def test_adapter():
    """Test the Alzheimer adapter."""
    print("=" * 60)
    print("Testing Alzheimer Adapter")
    print("=" * 60 + "\n")
    
    # Start mock server
    runner = await start_mock_server()
    
    # Wait a bit for server to be ready
    await asyncio.sleep(0.5)
    
    try:
        # Test 1: Basic forwarding without authentication
        print("Test 1: Basic forwarding (no authentication)")
        print("-" * 60)
        adapter1 = AlzheimerAdapter(base_url="http://localhost:8080")
        
        result1 = await adapter1.forward_text_as_intent(
            text="今天天气怎么样",
            device_id="test_device_123",
            user_id="user_456"
        )
        print(f"Result: {result1}\n")
        
        await asyncio.sleep(0.5)
        
        # Test 2: Forwarding with authentication
        print("Test 2: Forwarding with authentication token")
        print("-" * 60)
        adapter2 = AlzheimerAdapter(
            base_url="http://localhost:8080",
            api_token="test_secret_token_12345"
        )
        
        result2 = await adapter2.forward_text_as_intent(
            text="帮我打开客厅的灯",
            device_id="test_device_123",
            user_id="user_456",
            intent="control_device",
            slots={"device": "light", "room": "living_room", "action": "on"}
        )
        print(f"Result: {result2}\n")
        
        await asyncio.sleep(0.5)
        
        # Test 3: Disabled adapter (no base_url)
        print("Test 3: Disabled adapter (no base_url)")
        print("-" * 60)
        adapter3 = AlzheimerAdapter(base_url="")
        
        result3 = await adapter3.forward_text_as_intent(
            text="这条消息不应该被发送",
            device_id="test_device_123"
        )
        print(f"Result: {result3} (should be None)\n")
        
        await asyncio.sleep(0.5)
        
        # Test 4: Test with environment variables
        print("Test 4: Using environment variables")
        print("-" * 60)
        import os
        os.environ["ALZ_BASE_URL"] = "http://localhost:8080"
        os.environ["ALZ_API_TOKEN"] = "env_token_67890"
        
        adapter4 = AlzheimerAdapter()  # Should read from env vars
        result4 = await adapter4.forward_text_as_intent(
            text="测试环境变量配置",
            device_id="test_device_env"
        )
        print(f"Result: {result4}\n")
        
        print("=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        
    finally:
        # Cleanup
        await runner.cleanup()
        print("\n🛑 Mock server stopped")


if __name__ == "__main__":
    asyncio.run(test_adapter())
