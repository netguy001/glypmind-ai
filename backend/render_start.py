#!/usr/bin/env python3
"""
Render.com startup script for GlyphMind AI Backend
Handles environment setup and graceful startup for Render deployment
"""
import os
import sys
from pathlib import Path
import logging

def setup_render_environment():
    """Setup environment for Render.com deployment"""
    
    # Set up data directory for persistent storage
    data_dir = os.environ.get("DATA_DIR", "/opt/render/project/src/data")
    
    # Create necessary directories
    directories = [
        data_dir,
        os.path.join(data_dir, "cache"),
        os.path.join(data_dir, "logs"),
        os.path.join(data_dir, "models"),
    ]
    
    for directory in directories:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            print(f"✅ Created directory: {directory}")
        except Exception as e:
            print(f"⚠️  Could not create directory {directory}: {e}")
    
    # Set environment variables for the application
    os.environ.setdefault("DATA_DIR", data_dir)
    os.environ.setdefault("ENVIRONMENT", "production")
    
    # Log startup info
    print(f"🚀 Starting GlyphMind AI Backend on Render.com")
    print(f"📁 Data directory: {data_dir}")
    print(f"🌐 Port: {os.environ.get('PORT', '8000')}")
    print(f"🔧 Environment: {os.environ.get('ENVIRONMENT', 'production')}")
    
    # Check for API keys
    api_keys = [
        "GOOGLE_SEARCH_API_KEY",
        "YOUTUBE_API_KEY", 
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY"
    ]
    
    configured_keys = []
    for key in api_keys:
        if os.environ.get(key):
            configured_keys.append(key)
    
    if configured_keys:
        print(f"🔑 API keys configured: {', '.join(configured_keys)}")
    else:
        print("⚠️  No API keys configured - some features may be limited")

def main():
    """Main startup function"""
    try:
        # Setup environment
        setup_render_environment()
        
        # Import and start the application
        print("📦 Loading application modules...")
        
        # Import uvicorn and the app
        import uvicorn
        from server.app import app
        
        print("✅ Application loaded successfully")
        
        # Get configuration from environment
        host = os.environ.get("HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", 8000))
        log_level = os.environ.get("LOG_LEVEL", "info")
        
        print(f"🎯 Starting server on {host}:{port}")
        
        # Start the server
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=log_level,
            access_log=True
        )
        
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
