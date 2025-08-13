"""
GlyphMind AI Frontend for Hugging Face Spaces
Connects to Railway-hosted backend API
"""

import gradio as gr
import requests
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "https://glypmind-backend.onrender.com")
API_TIMEOUT = 30


def format_timestamp() -> str:
    """Format current timestamp"""
    return datetime.now().strftime("%H:%M:%S")


def make_api_request(
    endpoint: str, data: Dict[str, Any], method: str = "POST"
) -> Dict[str, Any]:
    """Make API request to backend with error handling"""
    try:
        url = f"{BACKEND_URL.rstrip('/')}/{endpoint.lstrip('/')}"

        if method.upper() == "POST":
            response = requests.post(url, json=data, timeout=API_TIMEOUT)
        else:
            response = requests.get(url, timeout=API_TIMEOUT)

        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {
            "error": "Request timed out. The backend might be starting up, please try again."
        }
    except requests.exceptions.ConnectionError:
        return {
            "error": f"Cannot connect to backend at {BACKEND_URL}. Please check if the backend is running."
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Invalid response from backend server."}


def chat_with_ai(message: str, history: List[List[str]]) -> tuple:
    """Chat with GlyphMind AI via backend API"""
    if not message.strip():
        return history, ""

    # Add user message to history
    timestamp = format_timestamp()
    user_entry = f"**You** ({timestamp}): {message}"

    # Make API request to backend
    request_data = {
        "text": message,
        "user_id": "hf_spaces_user",
        "session_id": "hf_spaces_session",
    }

    response = make_api_request("chat", request_data)

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
    """Search the web via backend API"""
    if not query.strip():
        return "Please enter a search query."

    # Parse sources
    source_list = (
        [s.strip() for s in sources.split(",") if s.strip()] if sources else None
    )

    request_data = {
        "query": query,
        "sources": source_list,
        "max_results": int(max_results),
    }

    response = make_api_request("search", request_data)

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
        if result.get("relevance_score", 0) > 0:
            output += f"**Relevance:** {result['relevance_score']:.2f}\n"
        output += "\n---\n\n"

    return output


def get_system_status() -> str:
    """Get system status from backend"""
    try:
        response = make_api_request("status", {}, method="GET")
    except Exception as e:
        return f"❌ Failed to get system status: {str(e)}"

    if "error" in response:
        return f"❌ Status Error: {response['error']}"

    # Format status information
    output = f"# 🧠 GlyphMind AI System Status\n\n"
    output += f"**Backend URL:** {BACKEND_URL}\n"
    output += f"**Status:** {response.get('status', 'Unknown')} ✅\n"
    output += f"**Uptime:** {response.get('uptime_seconds', 0)/3600:.1f} hours\n"
    output += f"**Last Updated:** {response.get('timestamp', 'Unknown')}\n\n"

    system_info = response.get("system_info", {})

    # AI Engine Status
    if "ai_engine" in system_info:
        ai_info = system_info["ai_engine"]
        output += "## 🤖 AI Engine\n"
        if isinstance(ai_info, dict):
            for model_name, model_info in ai_info.items():
                if isinstance(model_info, dict):
                    status_icon = (
                        "✅" if model_info.get("health_check", False) else "❌"
                    )
                    primary_icon = "⭐" if model_info.get("is_primary", False) else ""
                    output += f"- **{model_name}** {primary_icon}: {status_icon} ({model_info.get('model_type', 'unknown')})\n"
        output += "\n"

    # Web Intelligence Status
    if "web_intelligence" in system_info:
        web_info = system_info["web_intelligence"]
        output += "## 🌐 Web Intelligence\n"
        if isinstance(web_info, dict):
            for source_name, source_info in web_info.items():
                if isinstance(source_info, dict):
                    status_icon = (
                        "✅" if source_info.get("health_check", False) else "❌"
                    )
                    output += f"- **{source_name}**: {status_icon}\n"
        output += "\n"

    # Knowledge Base Status
    if "knowledge_base" in system_info:
        kb_info = system_info["knowledge_base"]
        output += "## 📚 Knowledge Base\n"
        if isinstance(kb_info, dict):
            output += f"- **Total Entries:** {kb_info.get('total_entries', 0)}\n"
            output += (
                f"- **Recent Entries (7d):** {kb_info.get('recent_entries_7d', 0)}\n"
            )
        output += "\n"

    return output


# Create the Gradio interface
with gr.Blocks(
    title="🧠 GlyphMind AI",
    theme=gr.themes.Soft(),
    css="""
    .gradio-container {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .status-container {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .dark .status-container {
        background-color: #1f2937;
    }
    """,
) as demo:

    # Header
    gr.HTML(
        f"""
        <div style="text-align: center; padding: 20px;">
            <h1>🧠 GlyphMind AI</h1>
            <h3>Local-First, Self-Evolving AI Assistant</h3>
            <p>Advanced AI with real-time learning, web intelligence, and continuous evolution</p>
            <p><small>Backend: <code>{BACKEND_URL}</code></small></p>
        </div>
    """
    )

    # Main interface tabs
    with gr.Tabs():

        # Chat Tab
        with gr.TabItem("💬 Chat", id="chat"):
            with gr.Row():
                with gr.Column(scale=4):
                    chatbot = gr.Chatbot(
                        label="Conversation",
                        height=500,
                        show_label=False,
                        container=False,
                        bubble_full_width=False,
                    )

                    with gr.Row():
                        msg = gr.Textbox(
                            label="Message",
                            placeholder="Ask me anything...",
                            lines=2,
                            max_lines=5,
                            show_label=False,
                            scale=4,
                        )
                        send_btn = gr.Button("Send 🚀", scale=1, variant="primary")

                    gr.Examples(
                        examples=[
                            "What are the latest AI developments?",
                            "Write a Python function to calculate fibonacci numbers",
                            "Explain quantum computing in simple terms",
                            "What's happening in technology today?",
                            "Help me solve this math problem: 2x + 5 = 15",
                        ],
                        inputs=msg,
                        label="Example Questions",
                    )

                with gr.Column(scale=1):
                    gr.HTML(
                        """
                        <div style="background-color: #f0f8ff; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                            <h4>✨ Features</h4>
                            <ul>
                                <li>🔍 Real-time web search</li>
                                <li>🧠 Continuous learning</li>
                                <li>📚 Knowledge base</li>
                                <li>🚀 Expert programming help</li>
                                <li>🔢 Mathematical problem solving</li>
                                <li>🌐 Multi-source intelligence</li>
                            </ul>
                        </div>
                    """
                    )

        # Web Search Tab
        with gr.TabItem("🔍 Web Search", id="search"):
            gr.HTML("<h2>🌐 Real-time Web Search</h2>")

            with gr.Row():
                with gr.Column():
                    search_query = gr.Textbox(
                        label="Search Query",
                        placeholder="Enter your search query...",
                        lines=2,
                    )

                    with gr.Row():
                        search_sources = gr.Textbox(
                            label="Sources (optional)",
                            placeholder="google, youtube, reddit",
                            value="google, youtube",
                            scale=2,
                        )
                        search_max_results = gr.Slider(
                            label="Max Results",
                            minimum=1,
                            maximum=20,
                            value=10,
                            step=1,
                            scale=1,
                        )

                    search_btn = gr.Button("🔍 Search", variant="primary")

                    gr.Examples(
                        examples=[
                            "latest AI breakthroughs 2024",
                            "Python programming best practices",
                            "climate change recent research",
                            "cryptocurrency market trends",
                            "space exploration news",
                        ],
                        inputs=search_query,
                    )

            search_results = gr.Markdown(
                label="Search Results",
                value="Enter a query and click Search to see results...",
            )

        # System Status Tab
        with gr.TabItem("⚙️ System Status", id="status"):
            gr.HTML("<h2>⚙️ System Status & Health</h2>")

            with gr.Row():
                status_refresh_btn = gr.Button("🔄 Refresh Status", variant="secondary")

            status_display = gr.Markdown(
                label="System Status",
                value="Click 'Refresh Status' to see system information...",
                elem_classes=["status-container"],
            )

    # Event handlers
    msg.submit(chat_with_ai, [msg, chatbot], [chatbot, msg])
    send_btn.click(chat_with_ai, [msg, chatbot], [chatbot, msg])

    search_btn.click(
        search_web, [search_query, search_sources, search_max_results], search_results
    )

    status_refresh_btn.click(get_system_status, outputs=status_display)

    # Load initial status
    demo.load(get_system_status, outputs=status_display)

if __name__ == "__main__":
    print("🧠 Starting GlyphMind AI Frontend...")
    print(f"🌐 Connecting to backend: {BACKEND_URL}")
    print("🎨 Frontend will be available shortly...")

    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        show_tips=True,
        enable_queue=True,
    )
