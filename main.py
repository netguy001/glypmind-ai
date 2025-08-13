"""
Main Entry Point for GlyphMind AI
Integrates all components and provides a unified interface
"""
import asyncio
from typing import Optional
from core.ai_engine import get_ai_response, ResponseType
from logs.logger import log_info, log_error

# Legacy function for backward compatibility
def run_ai(user_text: str) -> str:
    """Synchronous wrapper for AI response (legacy compatibility)"""
    try:
        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        response = loop.run_until_complete(
            get_ai_response(user_text, response_type=ResponseType.TEXT)
        )
        
        loop.close()
        return response.content
        
    except Exception as e:
        log_error("Error in legacy run_ai function", e)
        return f"GlyphMind AI encountered an error: {str(e)}"

async def async_run_ai(user_text: str, context: Optional[str] = None) -> str:
    """Async AI response function"""
    try:
        response = await get_ai_response(
            user_text, 
            context=context, 
            response_type=ResponseType.TEXT
        )
        return response.content
    except Exception as e:
        log_error("Error in async_run_ai function", e)
        return f"GlyphMind AI encountered an error: {str(e)}"

if __name__ == "__main__":
    print("🧠 GlyphMind AI - Main Entry Point")
    print("For full functionality, run:")
    print("  Backend: python server/app.py")
    print("  Frontend: python ui/ui.py")
    print("  Or use: ./runall.ps1")
    
    # Simple test
    test_query = "Hello, GlyphMind!"
    result = run_ai(test_query)
    print(f"\nTest Query: {test_query}")
    print(f"Response: {result}")
