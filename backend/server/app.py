"""
Enhanced FastAPI Backend for GlyphMind AI
Comprehensive API with async endpoints, request routing, and real-time capabilities
"""
import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Import GlyphMind modules
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.ai_engine import ai_engine, get_ai_response, ResponseType
    from web_intel.web_intelligence import web_intelligence, web_search
    from knowledge_base.knowledge_manager import knowledge_manager, search_knowledge
    from evolution_engine.evolution_manager import evolution_engine, start_evolution, stop_evolution
    from router.request_router import request_router, RequestContext, RequestType, Priority
    from logs.logger import log_info, log_error, log_api_request
    from config.config_manager import get_config
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback imports for basic functionality
    def log_info(msg, *args): print(f"INFO: {msg}")
    def log_error(msg, *args): print(f"ERROR: {msg}")
    def log_api_request(*args): pass
    def get_config(): 
        class Config:
            class Server:
                host = "127.0.0.1"
                port = 8000
                reload = True
                workers = 1
                log_level = "info"
            server = Server()
        return Config()

# Pydantic models for API
class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description="User message")
    context: Optional[str] = Field(None, max_length=50000, description="Additional context")
    response_type: str = Field("text", description="Expected response type")
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")

class ChatResponse(BaseModel):
    reply: str
    response_type: str
    confidence: float
    processing_time: float
    model_used: str
    sources: Optional[List[str]] = None
    request_id: str
    timestamp: str

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    sources: Optional[List[str]] = Field(None, description="Specific sources to search")
    max_results: int = Field(10, ge=1, le=50)
    time_filter: Optional[str] = Field(None, description="Time filter: day, week, month, year")

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_results: int
    search_time: float
    sources_used: List[str]
    request_id: str

class KnowledgeRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    categories: Optional[List[str]] = None
    max_results: int = Field(10, ge=1, le=100)

class KnowledgeResponse(BaseModel):
    entries: List[Dict[str, Any]]
    total_entries: int
    search_time: float
    request_id: str

class StatusResponse(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: float
    system_info: Dict[str, Any]
    request_id: str

# Global state
app_start_time = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    log_info("Starting GlyphMind AI Backend")
    
    try:
        # Initialize all components if available
        initialization_tasks = []
        
        if 'ai_engine' in globals():
            initialization_tasks.append(ai_engine.initialize())
        if 'web_intelligence' in globals():
            initialization_tasks.append(web_intelligence.initialize())
        if 'knowledge_manager' in globals():
            initialization_tasks.append(knowledge_manager.initialize())
        if 'evolution_engine' in globals():
            initialization_tasks.append(evolution_engine.initialize())
        
        if initialization_tasks:
            await asyncio.gather(*initialization_tasks, return_exceptions=True)
        
        # Start background services if available
        if 'start_evolution' in globals():
            try:
                await start_evolution()
            except Exception as e:
                log_error(f"Failed to start evolution engine: {e}")
                
        if 'request_router' in globals():
            try:
                await request_router.start_workers()
            except Exception as e:
                log_error(f"Failed to start router workers: {e}")
        
        log_info("GlyphMind AI Backend initialized")
        
        yield
        
    except Exception as e:
        log_error(f"Error during startup: {e}")
        yield
        
    finally:
        # Cleanup
        log_info("Shutting down GlyphMind AI Backend")
        try:
            if 'stop_evolution' in globals():
                await stop_evolution()
            if 'request_router' in globals():
                await request_router.stop_workers()
        except Exception as e:
            log_error(f"Error during shutdown: {e}")

# Create FastAPI app
app = FastAPI(
    title="GlyphMind AI API",
    description="Advanced AI Assistant with Real-time Learning and Web Intelligence",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
# Get allowed origins from environment or use defaults
import os
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "").split(",") if os.environ.get("ALLOWED_ORIGINS") else []

# Default allowed origins for development and common deployments
default_origins = [
    "https://*.hf.space",
    "https://huggingface.co", 
    "http://localhost:7860",
    "http://127.0.0.1:7860",
]

# Add environment-specified origins
all_origins = default_origins + ALLOWED_ORIGINS

# Add wildcard for development (remove in production)
if os.environ.get("ENVIRONMENT", "development") == "development":
    all_origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=all_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request context dependency
async def get_request_context(request: Request):
    """Create request context from HTTP request"""
    if 'RequestContext' in globals() and 'RequestType' in globals():
        return RequestContext(
            request_id=str(uuid.uuid4()),
            request_type=RequestType.CHAT,  # Will be overridden by specific endpoints
            user_id=request.headers.get("X-User-ID"),
            session_id=request.headers.get("X-Session-ID"),
            metadata={
                "user_agent": request.headers.get("User-Agent"),
                "ip_address": request.client.host if request.client else None
            }
        )
    else:
        # Fallback context object
        class FallbackContext:
            def __init__(self):
                self.request_id = str(uuid.uuid4())
                self.request_type = "chat"
                self.user_id = request.headers.get("X-User-ID")
                self.session_id = request.headers.get("X-Session-ID")
                self.metadata = {
                    "user_agent": request.headers.get("User-Agent"),
                    "ip_address": request.client.host if request.client else None
                }
        return FallbackContext()

# Request handlers for router
async def handle_chat(context: RequestContext) -> Any:
    """Handle chat requests"""
    request_data = context.metadata.get("request_data")
    if not request_data:
        raise ValueError("No request data provided")
    
    try:
        # Try full AI response if available
        if 'get_ai_response' in globals():
            # Analyze query to determine response strategy
            query_analysis = {}
            if 'ai_engine' in globals():
                try:
                    query_analysis = await ai_engine.analyze_query(request_data.text)
                except:
                    query_analysis = {"requires_web_search": False, "requires_code_generation": False}
            
            # Enhance with web search if needed
            web_context = None
            if query_analysis.get("requires_web_search", False) and 'web_search' in globals():
                try:
                    search_results = await web_search(request_data.text, max_results=5)
                    if search_results:
                        web_context = "\n".join([
                            f"Source: {result.title}\n{result.snippet}"
                            for result in search_results[:3]
                        ])
                        
                        # Learn from search results if available
                        if 'knowledge_manager' in globals():
                            await knowledge_manager.learn_from_web_results(request_data.text, search_results)
                except Exception as e:
                    log_error("Error performing web search for chat", e)
            
            # Get AI response
            response_type_val = "code" if query_analysis.get("requires_code_generation") else "text"
            if 'ResponseType' in globals():
                response_type = ResponseType.CODE if query_analysis.get("requires_code_generation") else ResponseType.TEXT
            else:
                response_type = None
                
            ai_response = await get_ai_response(
                request_data.text,
                context=web_context or request_data.context,
                response_type=response_type
            )
            
            # Learn from user interaction if available
            if 'evolution_engine' in globals():
                try:
                    await evolution_engine.learn_from_user_interaction(
                        request_data.text,
                        ai_response.content
                    )
                except Exception as e:
                    log_error("Error learning from interaction", e)
            
            return ChatResponse(
                reply=ai_response.content,
                response_type=ai_response.response_type.value if hasattr(ai_response, 'response_type') else response_type_val,
                confidence=ai_response.confidence if hasattr(ai_response, 'confidence') else 0.8,
                processing_time=ai_response.processing_time if hasattr(ai_response, 'processing_time') else 0.1,
                model_used=ai_response.model_used if hasattr(ai_response, 'model_used') else "local_fallback",
                sources=ai_response.sources if hasattr(ai_response, 'sources') else None,
                request_id=context.request_id,
                timestamp=datetime.now().isoformat()
            )
        else:
            # Fallback response
            return ChatResponse(
                reply=f"I received your message: '{request_data.text}'. The full AI system is initializing. Please try again in a moment.",
                response_type="text",
                confidence=0.5,
                processing_time=0.01,
                model_used="fallback",
                sources=None,
                request_id=context.request_id,
                timestamp=datetime.now().isoformat()
            )
    except Exception as e:
        log_error("Error in chat handler", e)
        return ChatResponse(
            reply=f"I apologize, but I encountered an error processing your request: {str(e)}",
            response_type="text",
            confidence=0.1,
            processing_time=0.01,
            model_used="error_handler",
            sources=None,
            request_id=context.request_id,
            timestamp=datetime.now().isoformat()
        )

async def handle_search(context: RequestContext) -> Any:
    """Handle search requests"""
    request_data = context.metadata.get("request_data")
    if not request_data:
        raise ValueError("No request data provided")
        
    start_time = time.time()
    
    # Perform web search
    results = await web_search(
        request_data.query,
        sources=request_data.sources,
        max_results=request_data.max_results
    )
    
    search_time = time.time() - start_time
    
    # Convert results to dict format
    results_dict = []
    for result in results:
        results_dict.append({
            "title": result.title,
            "url": result.url,
            "snippet": result.snippet,
            "source": result.source,
            "relevance_score": result.relevance_score,
            "metadata": result.metadata
        })
    
    # Learn from search results in background
    if results:
        asyncio.create_task(
            knowledge_manager.learn_from_web_results(request_data.query, results)
        )
    
    return SearchResponse(
        results=results_dict,
        total_results=len(results),
        search_time=search_time,
        sources_used=list(set(result.source for result in results)),
        request_id=context.request_id
    )

async def handle_knowledge(context: RequestContext) -> Any:
    """Handle knowledge base requests"""
    request_data = context.metadata.get("request_data")
    if not request_data:
        raise ValueError("No request data provided")
        
    start_time = time.time()
    
    # Search knowledge base
    entries = await search_knowledge(
        request_data.query,
        categories=request_data.categories,
        max_results=request_data.max_results
    )
    
    search_time = time.time() - start_time
    
    # Convert entries to dict format
    entries_dict = []
    for entry in entries:
        entries_dict.append({
            "id": entry.id,
            "content": entry.content,
            "title": entry.title,
            "source": entry.source,
            "url": entry.url,
            "category": entry.category,
            "tags": entry.tags,
            "confidence": entry.confidence,
            "relevance_score": entry.relevance_score,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "updated_at": entry.updated_at.isoformat() if entry.updated_at else None
        })
    
    return KnowledgeResponse(
        entries=entries_dict,
        total_entries=len(entries),
        search_time=search_time,
        request_id=context.request_id
    )

async def handle_status(context: RequestContext) -> Any:
    """Handle status requests"""
    uptime = time.time() - app_start_time
    
    # Get system status from all components
    system_info = {}
    
    try:
        if 'ai_engine' in globals():
            system_info["ai_engine"] = await ai_engine.get_model_status()
        else:
            system_info["ai_engine"] = {"status": "not_loaded"}
    except Exception as e:
        system_info["ai_engine"] = {"error": str(e)}
    
    try:
        if 'web_intelligence' in globals():
            system_info["web_intelligence"] = await web_intelligence.get_source_status()
        else:
            system_info["web_intelligence"] = {"status": "not_loaded"}
    except Exception as e:
        system_info["web_intelligence"] = {"error": str(e)}
    
    try:
        if 'knowledge_manager' in globals():
            system_info["knowledge_base"] = await knowledge_manager.get_statistics()
        else:
            system_info["knowledge_base"] = {"status": "not_loaded"}
    except Exception as e:
        system_info["knowledge_base"] = {"error": str(e)}
    
    try:
        if 'evolution_engine' in globals():
            system_info["evolution_engine"] = await evolution_engine.get_learning_status()
        else:
            system_info["evolution_engine"] = {"status": "not_loaded"}
    except Exception as e:
        system_info["evolution_engine"] = {"error": str(e)}
    
    try:
        if 'request_router' in globals():
            system_info["router"] = request_router.get_stats()
        else:
            system_info["router"] = {"status": "not_loaded"}
    except Exception as e:
        system_info["router"] = {"error": str(e)}
    
    return StatusResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        uptime_seconds=uptime,
        system_info=system_info,
        request_id=context.request_id
    )

# Register handlers with router if available
if 'request_router' in globals():
    try:
        request_router.register_handler("handle_chat", handle_chat)
        request_router.register_handler("handle_search", handle_search)
        request_router.register_handler("handle_knowledge", handle_knowledge)
        request_router.register_handler("handle_status", handle_status)
    except Exception as e:
        log_error(f"Error registering handlers: {e}")

# API Endpoints
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    context = Depends(get_request_context)
):
    """Chat with GlyphMind AI"""
    try:
        if 'RequestType' in globals():
            context.request_type = RequestType.CHAT
        context.metadata["request_data"] = request
        
        # Try to use router if available, otherwise call handler directly
        if 'request_router' in globals():
            try:
                response = await request_router.route_request(context)
                return response
            except Exception as router_error:
                log_error(f"Router error, falling back to direct handler: {router_error}")
        
        # Direct handler call
        response = await handle_chat(context)
        return response
        
    except Exception as e:
        log_error("Chat endpoint error", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search", response_model=SearchResponse)
async def search_endpoint(
    request: SearchRequest,
    context: RequestContext = Depends(get_request_context)
):
    """Search the web for information"""
    context.request_type = RequestType.SEARCH
    context.metadata["request_data"] = request
    
    try:
        response = await request_router.route_request(context)
        return response
    except Exception as e:
        log_error("Search endpoint error", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge", response_model=KnowledgeResponse)
async def knowledge_endpoint(
    request: KnowledgeRequest,
    context: RequestContext = Depends(get_request_context)
):
    """Search the knowledge base"""
    context.request_type = RequestType.KNOWLEDGE
    context.metadata["request_data"] = request
    
    try:
        response = await request_router.route_request(context)
        return response
    except Exception as e:
        log_error("Knowledge endpoint error", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status", response_model=StatusResponse)
async def status_endpoint(
    context = Depends(get_request_context)
):
    """Get system status"""
    try:
        if 'RequestType' in globals():
            context.request_type = RequestType.STATUS
        
        # Try to use router if available, otherwise call handler directly
        if 'request_router' in globals():
            try:
                response = await request_router.route_request(context)
                return response
            except Exception as router_error:
                log_error(f"Router error, falling back to direct handler: {router_error}")
        
        # Direct handler call
        response = await handle_status(context)
        return response
        
    except Exception as e:
        log_error("Status endpoint error", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Simple health check endpoint for Render.com"""
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "port": os.environ.get("PORT", "8000"),
        "data_dir": os.environ.get("DATA_DIR", "data")
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "🧠 GlyphMind AI Backend",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

# Legacy endpoint for backward compatibility
@app.post("/chat-simple")
async def chat_simple(request: ChatRequest):
    """Simple chat endpoint for backward compatibility"""
    try:
        ai_response = await get_ai_response(request.text, context=request.context)
        return {"reply": ai_response.content}
    except Exception as e:
        log_error("Simple chat endpoint error", e)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import os
    
    # Get port from environment variable (required for Render.com)
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    log_level = os.environ.get("LOG_LEVEL", "info")
    
    print(f"🚀 Starting GlyphMind AI Backend on {host}:{port}")
    print(f"📊 Log level: {log_level}")
    
    uvicorn.run(
        "server.app:app",
        host=host,
        port=port,
        log_level=log_level
    )
