#!/usr/bin/env python3
"""
Local development server for GlyphMind AI Frontend
"""
import os

if __name__ == "__main__":
    # Set development environment variables
    os.environ.setdefault("BACKEND_URL", "http://127.0.0.1:8000")
    
    print("🎨 Starting GlyphMind AI Frontend (Local Development)")
    print(f"🌐 Frontend will be available at: http://127.0.0.1:7860")
    print(f"🔗 Connecting to backend: {os.environ['BACKEND_URL']}")
    
    # Import and run the app
    from app import demo
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
        show_tips=True,
        enable_queue=True
    )
