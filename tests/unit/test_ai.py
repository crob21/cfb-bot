#!/usr/bin/env python3
"""
Test script for AI integration
This will test if your OpenAI API key works without needing Discord
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_openai_api():
    """Test OpenAI API connection"""
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY not found in .env file")
        return False
    
    print(f"🔑 API Key found: {api_key[:20]}...")
    
    try:
        import aiohttp
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Simple test request
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {'role': 'user', 'content': 'Say "CFB League Bot AI test successful!"'}
            ],
            'max_tokens': 50
        }
        
        print("🔄 Testing OpenAI API connection...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    ai_response = result['choices'][0]['message']['content']
                    print(f"✅ OpenAI API working!")
                    print(f"🤖 AI Response: {ai_response}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ OpenAI API error: {response.status}")
                    print(f"Error details: {error_text}")
                    return False
                    
    except ImportError:
        print("❌ aiohttp not installed. Run: pip install aiohttp")
        return False
    except Exception as e:
        print(f"❌ Error testing OpenAI API: {e}")
        return False

async def test_ai_integration():
    """Test the AI integration module"""
    try:
        from src.cfb_bot.ai.ai_integration import AICharterAssistant
        
        print("🔄 Testing AI integration module...")
        
        assistant = AICharterAssistant()
        
        # Test with a simple question
        question = "What are the recruiting rules?"
        print(f"❓ Testing question: {question}")
        
        response = await assistant.ask_ai(question)
        
        if response:
            print("✅ AI integration working!")
            print(f"🤖 Response: {response[:200]}...")
            return True
        else:
            print("❌ AI integration failed - no response")
            return False
            
    except ImportError as e:
        print(f"❌ Error importing AI integration: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing AI integration: {e}")
        return False

async def main():
    """Main test function"""
    print("🏈 CFB League Bot - AI Integration Test")
    print("=" * 50)
    
    # Test 1: Basic API connection
    print("\n1️⃣ Testing OpenAI API connection...")
    api_works = await test_openai_api()
    
    # Test 2: AI integration module
    print("\n2️⃣ Testing AI integration module...")
    integration_works = await test_ai_integration()
    
    # Summary
    print("\n📊 Test Results:")
    print("=" * 20)
    print(f"OpenAI API: {'✅ Working' if api_works else '❌ Failed'}")
    print(f"AI Integration: {'✅ Working' if integration_works else '❌ Failed'}")
    
    if api_works and integration_works:
        print("\n🎉 All tests passed! Your AI integration is ready!")
        print("You can now run the Discord bot and use /ask commands.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        if not api_works:
            print("- Verify your OpenAI API key in .env file")
            print("- Check your OpenAI account has credits")
        if not integration_works:
            print("- Check that ai_integration.py is in the same directory")

if __name__ == "__main__":
    asyncio.run(main())
