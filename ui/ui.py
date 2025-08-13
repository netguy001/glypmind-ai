"""
Enhanced Gradio Frontend for GlyphMind AI
Beautiful, modern UI with comprehensive features and real-time capabilities
"""
import gradio as gr
import requests
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

# API Configuration
API_BASE_URL = "http://127.0.0.1:8000"
CHAT_URL = f"{API_BASE_URL}/chat"
SEARCH_URL = f"{API_BASE_URL}/search"
KNOWLEDGE_URL = f"{API_BASE_URL}/knowledge"
STATUS_URL = f"{API_BASE_URL}/status"

# Global state
conversation_history = []
system_status = {}

def format_timestamp() -> str:
    """Format current timestamp"""
    return datetime.now().strftime("%H:%M:%S")

def make_api_request(url: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Make API request with error handling"""
    try:
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. Please try again."}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to GlyphMind AI backend. Please ensure the server is running."}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Invalid response from server."}

def chat_with_ai(message: str, history: List[List[str]]) -> tuple:
    """Chat with GlyphMind AI"""
    if not message.strip():
        return history, ""
    
    # Add user message to history
    timestamp = format_timestamp()
    user_entry = f"**You** ({timestamp}): {message}"
    
    # Make API request
    request_data = {
        "text": message,
        "user_id": "gradio_user",
        "session_id": "gradio_session"
    }
    
    response = make_api_request(CHAT_URL, request_data)
    
    if "error" in response:
        ai_entry = f"**GlyphMind** ({timestamp}): ❌ {response['error']}"
    else:
        reply = response.get("reply", "No response received")
        model_used = response.get("model_used", "unknown")
        confidence = response.get("confidence", 0.0)
        processing_time = response.get("processing_time", 0.0)
        
        # Format AI response with metadata
        ai_entry = f"**GlyphMind** ({timestamp}): {reply}\n\n"
        ai_entry += f"*Model: {model_used} | Confidence: {confidence:.2f} | Time: {processing_time:.2f}s*"
        
        # Add sources if available
        if response.get("sources"):
            sources_text = ", ".join(response["sources"])
            ai_entry += f"\n*Sources: {sources_text}*"
    
    # Update history
    history.append([user_entry, ai_entry])
    
    return history, ""

def search_web(query: str, sources: str, max_results: float) -> str:
    """Search the web for information"""
    if not query.strip():
        return "Please enter a search query."
    
    # Parse sources
    source_list = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
    
    request_data = {
        "query": query,
        "sources": source_list,
        "max_results": int(max_results)
    }
    
    response = make_api_request(SEARCH_URL, request_data)
    
    if "error" in response:
        return f"❌ Search Error: {response['error']}"
    
    results = response.get("results", [])
    if not results:
        return "No search results found."
    
    # Format results
    output = f"# Search Results for: '{query}'\n\n"
    output += f"**Found {response.get('total_results', 0)} results in {response.get('search_time', 0):.2f}s**\n\n"
    
    for i, result in enumerate(results, 1):
        output += f"## {i}. {result.get('title', 'Untitled')}\n"
        output += f"**Source:** {result.get('source', 'Unknown')}\n"
        output += f"**URL:** {result.get('url', 'N/A')}\n"
        output += f"**Snippet:** {result.get('snippet', 'No description available')}\n"
        if result.get('relevance_score', 0) > 0:
            output += f"**Relevance:** {result['relevance_score']:.2f}\n"
        output += "\n---\n\n"
    
    return output

def get_system_status() -> str:
    """Get system status information"""
    try:
        response = requests.get(STATUS_URL, timeout=10)
        response.raise_for_status()
        status_data = response.json()
    except Exception as e:
        return f"❌ Failed to get system status: {str(e)}"
    
    if "error" in status_data:
        return f"❌ Status Error: {status_data['error']}"
    
    # Format status information
    output = f"# 🧠 GlyphMind AI System Status\n\n"
    output += f"**Status:** {status_data.get('status', 'Unknown')} ✅\n"
    output += f"**Uptime:** {status_data.get('uptime_seconds', 0)/3600:.1f} hours\n"
    output += f"**Last Updated:** {status_data.get('timestamp', 'Unknown')}\n\n"
    
    return output

# Create the Gradio interface
with gr.Blocks(
    title="🧠 GlyphMind AI",
    theme=gr.themes.Soft()
) as demo:
    
    # Header
    gr.HTML("""
        <div style="text-align: center; padding: 20px;">
            <h1>🧠 GlyphMind AI</h1>
            <h3>Local-First, Self-Evolving AI Assistant</h3>
            <p>Advanced AI with real-time learning, web intelligence, and continuous evolution</p>
        </div>
    """)
    
    # Main interface tabs
    with gr.Tabs():
        
        # Chat Tab
        with gr.TabItem("💬 Chat", id="chat"):
            chatbot = gr.Chatbot(
                label="Conversation",
                height=500,
                show_label=False
            )
            
            with gr.Row():
                msg = gr.Textbox(
                    label="Message",
                    placeholder="Ask me anything...",
                    lines=2,
                    show_label=False,
                    scale=4
                )
                send_btn = gr.Button("Send 🚀", scale=1, variant="primary")
            
            gr.Examples(
                examples=[
                    "What are the latest AI developments?",
                    "Write a Python function to calculate fibonacci numbers",
                    "Explain quantum computing in simple terms",
                    "What's happening in technology today?"
                ],
                inputs=msg,
                label="Example Questions"
            )
        
        # Web Search Tab
        with gr.TabItem("🔍 Web Search", id="search"):
            gr.HTML("<h2>🌐 Real-time Web Search</h2>")
            
            search_query = gr.Textbox(
                label="Search Query",
                placeholder="Enter your search query...",
                lines=2
            )
            
            with gr.Row():
                search_sources = gr.Textbox(
                    label="Sources (optional)",
                    placeholder="google, youtube, reddit",
                    value="google, youtube",
                    scale=2
                )
                search_max_results = gr.Slider(
                    label="Max Results",
                    minimum=1,
                    maximum=20,
                    value=10,
                    step=1,
                    scale=1
                )
            
            search_btn = gr.Button("🔍 Search", variant="primary")
            
            search_results = gr.Markdown(
                label="Search Results",
                value="Enter a query and click Search to see results..."
            )
        
        # System Status Tab
        with gr.TabItem("⚙️ System Status", id="status"):
            gr.HTML("<h2>⚙️ System Status & Health</h2>")
            
            status_refresh_btn = gr.Button("🔄 Refresh Status", variant="secondary")
            
            status_display = gr.Markdown(
                label="System Status",
                value="Click 'Refresh Status' to see system information..."
            )
    
    # Event handlers
    msg.submit(chat_with_ai, [msg, chatbot], [chatbot, msg])
    send_btn.click(chat_with_ai, [msg, chatbot], [chatbot, msg])
    
    search_btn.click(
        search_web,
        [search_query, search_sources, search_max_results],
        search_results
    )
    
    status_refresh_btn.click(get_system_status, outputs=status_display)
    
    # Load initial status
    demo.load(get_system_status, outputs=status_display)

if __name__ == "__main__":
    print("🧠 Starting GlyphMind AI Frontend...")
    print("🌐 Backend should be running at http://127.0.0.1:8000")
    print("🎨 Frontend will be available at http://127.0.0.1:7860")
    
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True
    )