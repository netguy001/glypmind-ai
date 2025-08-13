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
from core.ai_engine import ai_engine, get_ai_response, ResponseType
from web_intel.web_intelligence import web_intelligence, web_search
from knowledge_base.knowledge_manager import knowledge_manager, search_knowledge
from evolution_engine.evolution_manager import evolution_engine, start_evolution, stop_evolution
from router.request_router import request_router, RequestContext, RequestType, Priority
from logs.logger import log_info, log_error, log_api_request
from config.config_manager import get_config

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
    
    # Initialize all components
    initialization_tasks = [
        ai_engine.initialize(),
        web_intelligence.initialize(),
        knowledge_manager.initialize(),
        evolution_engine.initialize()
    ]
    
    try:
        await asyncio.gather(*initialization_tasks)
        
        # Start background services
        await start_evolution()
        await request_router.start_workers()
        
        log_info("GlyphMind AI Backend fully initialized")
        
        yield
        
    finally:
        # Cleanup
        log_info("Shutting down GlyphMind AI Backend")
        await stop_evolution()
        await request_router.stop_workers()

# Create FastAPI app
app = FastAPI(
    title="GlyphMind AI API",
    description="Advanced AI Assistant with Real-time Learning and Web Intelligence",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request context dependency
async def get_request_context(request: Request) -> RequestContext:
    """Create request context from HTTP request"""
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

# Request handlers for router
async def handle_chat(context: RequestContext) -> Any:
    """Handle chat requests"""
    request_data = context.metadata.get("request_data")
    if not request_data:
        raise ValueError("No request data provided")
        
    # Analyze query to determine response strategy
    query_analysis = await ai_engine.analyze_query(request_data.text)
    
    # Enhance with web search if needed
    web_context = None
    if query_analysis.get("requires_web_search", False):
        try:
            search_results = await web_search(request_data.text, max_results=5)
            if search_results:
                web_context = "\n".join([
                    f"Source: {result.title}\n{result.snippet}"
                    for result in search_results[:3]
                ])
                
                # Learn from search results
                await knowledge_manager.learn_from_web_results(request_data.text, search_results)
        except Exception as e:
            log_error("Error performing web search for chat", e)
    
    # Get AI response
    response_type = ResponseType.CODE if query_analysis.get("requires_code_generation") else ResponseType.TEXT
    ai_response = await get_ai_response(
        request_data.text,
        context=web_context or request_data.context,
        response_type=response_type
    )
    
    # Learn from user interaction
    await evolution_engine.learn_from_user_interaction(
        request_data.text,
        ai_response.content
    )
    
    return ChatResponse(
        reply=ai_response.content,
        response_type=ai_response.response_type.value,
        confidence=ai_response.confidence,
        processing_time=ai_response.processing_time,
        model_used=ai_response.model_used,
        sources=ai_response.sources,
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
    system_info = {
        "ai_engine": await ai_engine.get_model_status(),
        "web_intelligence": await web_intelligence.get_source_status(),
        "knowledge_base": await knowledge_manager.get_statistics(),
        "evolution_engine": await evolution_engine.get_learning_status(),
        "router": request_router.get_stats()
    }
    
    return StatusResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        uptime_seconds=uptime,
        system_info=system_info,
        request_id=context.request_id
    )

# Register handlers with router
request_router.register_handler("handle_chat", handle_chat)
request_router.register_handler("handle_search", handle_search)
request_router.register_handler("handle_knowledge", handle_knowledge)
request_router.register_handler("handle_status", handle_status)

# API Endpoints
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    context: RequestContext = Depends(get_request_context)
):
    """Chat with GlyphMind AI"""
    context.request_type = RequestType.CHAT
    context.metadata["request_data"] = request
    
    try:
        response = await request_router.route_request(context)
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
    context: RequestContext = Depends(get_request_context)
):
    """Get system status"""
    context.request_type = RequestType.STATUS
    
    try:
        response = await request_router.route_request(context)
        return response
    except Exception as e:
        log_error("Status endpoint error", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

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
    config = get_config()
    uvicorn.run(
        "server.app:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
        log_level=config.server.log_level,
        workers=config.server.workers
    )
