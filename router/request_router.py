"""
Request Router for GlyphMind AI
Handles intelligent request routing, load balancing, and request prioritization
"""
import asyncio
import time
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
from pathlib import Path

from logs.logger import log_info, log_error, log_warning, log_api_request

class RequestType(Enum):
    """Types of requests"""
    CHAT = "chat"
    SEARCH = "search"
    KNOWLEDGE = "knowledge"
    STATUS = "status"
    ADMIN = "admin"

class Priority(Enum):
    """Request priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class RequestContext:
    """Context information for a request"""
    request_id: str
    request_type: RequestType
    priority: Priority = Priority.NORMAL
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None
    
@dataclass
class RouteRule:
    """Routing rule configuration"""
    name: str
    condition: Callable[[RequestContext], bool]
    handler: str  # Handler function name
    priority_boost: int = 0
    rate_limit: Optional[int] = None  # Requests per minute
    timeout_seconds: int = 30
    retry_attempts: int = 3
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class RequestStats:
    """Request statistics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    requests_by_type: Dict[str, int] = field(default_factory=dict)
    requests_by_priority: Dict[str, int] = field(default_factory=dict)
    last_reset: datetime = field(default_factory=datetime.now)

class RateLimiter:
    """Rate limiting implementation"""
    
    def __init__(self):
        self.requests: Dict[str, List[datetime]] = {}
        
    def is_allowed(self, key: str, limit: int, window_minutes: int = 1) -> bool:
        """Check if request is allowed under rate limit"""
        now = datetime.now()
        window_start = now - timedelta(minutes=window_minutes)
        
        # Clean old requests
        if key in self.requests:
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if req_time > window_start
            ]
        else:
            self.requests[key] = []
            
        # Check limit
        if len(self.requests[key]) >= limit:
            return False
            
        # Add current request
        self.requests[key].append(now)
        return True
        
    def get_remaining(self, key: str, limit: int, window_minutes: int = 1) -> int:
        """Get remaining requests in window"""
        now = datetime.now()
        window_start = now - timedelta(minutes=window_minutes)
        
        if key not in self.requests:
            return limit
            
        recent_requests = [
            req_time for req_time in self.requests[key]
            if req_time > window_start
        ]
        
        return max(0, limit - len(recent_requests))

class RequestQueue:
    """Priority-based request queue"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.queues: Dict[Priority, asyncio.Queue] = {
            priority: asyncio.Queue(maxsize=max_size // 4)
            for priority in Priority
        }
        
    async def put(self, context: RequestContext, handler: Callable) -> bool:
        """Add request to appropriate priority queue"""
        try:
            queue = self.queues[context.priority]
            await queue.put((context, handler))
            return True
        except asyncio.QueueFull:
            log_warning(f"Request queue full for priority {context.priority}")
            return False
            
    async def get(self) -> Optional[tuple]:
        """Get next request from highest priority queue"""
        # Check queues in priority order
        for priority in [Priority.CRITICAL, Priority.HIGH, Priority.NORMAL, Priority.LOW]:
            queue = self.queues[priority]
            if not queue.empty():
                try:
                    return await asyncio.wait_for(queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
        return None
        
    def size(self) -> Dict[str, int]:
        """Get queue sizes"""
        return {
            priority.name: queue.qsize()
            for priority, queue in self.queues.items()
        }

class RequestRouter:
    """Main request routing system"""
    
    def __init__(self):
        self.routes: List[RouteRule] = []
        self.handlers: Dict[str, Callable] = {}
        self.rate_limiter = RateLimiter()
        self.request_queue = RequestQueue()
        self.stats = RequestStats()
        self.is_processing = False
        self.worker_tasks: List[asyncio.Task] = []
        self.max_concurrent_workers = 10
        
        # Load routing rules
        self._load_routing_rules()
        
    def _load_routing_rules(self):
        """Load routing rules from configuration"""
        rules_file = Path("router/router_rules.json")
        
        try:
            if rules_file.exists():
                with open(rules_file, 'r') as f:
                    rules_data = json.load(f)
                    
                for rule_data in rules_data.get("rules", []):
                    self._create_rule_from_config(rule_data)
            else:
                self._create_default_rules()
                self._save_routing_rules()
                
        except Exception as e:
            log_error("Failed to load routing rules", e)
            self._create_default_rules()
            
    def _create_default_rules(self):
        """Create default routing rules"""
        # Chat requests
        self.add_route(RouteRule(
            name="chat_requests",
            condition=lambda ctx: ctx.request_type == RequestType.CHAT,
            handler="handle_chat",
            timeout_seconds=30,
            rate_limit=60  # 60 requests per minute
        ))
        
        # Search requests
        self.add_route(RouteRule(
            name="search_requests",
            condition=lambda ctx: ctx.request_type == RequestType.SEARCH,
            handler="handle_search",
            timeout_seconds=15,
            rate_limit=30
        ))
        
        # Knowledge requests
        self.add_route(RouteRule(
            name="knowledge_requests",
            condition=lambda ctx: ctx.request_type == RequestType.KNOWLEDGE,
            handler="handle_knowledge",
            timeout_seconds=10,
            rate_limit=100
        ))
        
        # Status requests
        self.add_route(RouteRule(
            name="status_requests",
            condition=lambda ctx: ctx.request_type == RequestType.STATUS,
            handler="handle_status",
            priority_boost=1,
            timeout_seconds=5,
            rate_limit=120
        ))
        
        # Admin requests
        self.add_route(RouteRule(
            name="admin_requests",
            condition=lambda ctx: ctx.request_type == RequestType.ADMIN,
            handler="handle_admin",
            priority_boost=2,
            timeout_seconds=60,
            rate_limit=10
        ))
        
    def _save_routing_rules(self):
        """Save routing rules to configuration file"""
        rules_file = Path("router/router_rules.json")
        rules_file.parent.mkdir(exist_ok=True)
        
        try:
            rules_data = {
                "rules": [
                    {
                        "name": rule.name,
                        "handler": rule.handler,
                        "priority_boost": rule.priority_boost,
                        "rate_limit": rule.rate_limit,
                        "timeout_seconds": rule.timeout_seconds,
                        "retry_attempts": rule.retry_attempts,
                        "metadata": rule.metadata
                    }
                    for rule in self.routes
                ]
            }
            
            with open(rules_file, 'w') as f:
                json.dump(rules_data, f, indent=2)
                
        except Exception as e:
            log_error("Failed to save routing rules", e)
            
    def _create_rule_from_config(self, rule_data: Dict[str, Any]):
        """Create routing rule from configuration data"""
        # This is a simplified version - in a full implementation,
        # you'd need to serialize/deserialize the condition functions
        name = rule_data.get("name", "unknown")
        handler = rule_data.get("handler", "default_handler")
        
        # Create condition based on name (simplified)
        if "chat" in name:
            condition = lambda ctx: ctx.request_type == RequestType.CHAT
        elif "search" in name:
            condition = lambda ctx: ctx.request_type == RequestType.SEARCH
        elif "knowledge" in name:
            condition = lambda ctx: ctx.request_type == RequestType.KNOWLEDGE
        elif "status" in name:
            condition = lambda ctx: ctx.request_type == RequestType.STATUS
        elif "admin" in name:
            condition = lambda ctx: ctx.request_type == RequestType.ADMIN
        else:
            condition = lambda ctx: True
            
        rule = RouteRule(
            name=name,
            condition=condition,
            handler=handler,
            priority_boost=rule_data.get("priority_boost", 0),
            rate_limit=rule_data.get("rate_limit"),
            timeout_seconds=rule_data.get("timeout_seconds", 30),
            retry_attempts=rule_data.get("retry_attempts", 3),
            metadata=rule_data.get("metadata")
        )
        
        self.routes.append(rule)
        
    def add_route(self, rule: RouteRule):
        """Add a routing rule"""
        self.routes.append(rule)
        log_info(f"Added routing rule: {rule.name}")
        
    def register_handler(self, name: str, handler: Callable):
        """Register a request handler"""
        self.handlers[name] = handler
        log_info(f"Registered handler: {name}")
        
    async def route_request(self, context: RequestContext, 
                          handler_override: Optional[Callable] = None) -> Any:
        """Route a request through the system"""
        start_time = time.time()
        
        try:
            # Update statistics
            self.stats.total_requests += 1
            self.stats.requests_by_type[context.request_type.value] = \
                self.stats.requests_by_type.get(context.request_type.value, 0) + 1
            self.stats.requests_by_priority[context.priority.name] = \
                self.stats.requests_by_priority.get(context.priority.name, 0) + 1
                
            # Find matching route
            matching_rule = self._find_matching_route(context)
            if not matching_rule:
                raise ValueError(f"No route found for request type: {context.request_type}")
                
            # Apply priority boost
            if matching_rule.priority_boost > 0:
                context.priority = Priority(min(4, context.priority.value + matching_rule.priority_boost))
                
            # Check rate limiting
            if matching_rule.rate_limit:
                rate_key = f"{context.user_id or 'anonymous'}:{context.request_type.value}"
                if not self.rate_limiter.is_allowed(rate_key, matching_rule.rate_limit):
                    remaining = self.rate_limiter.get_remaining(rate_key, matching_rule.rate_limit)
                    raise Exception(f"Rate limit exceeded. Try again later. Remaining: {remaining}")
                    
            # Get handler
            handler = handler_override or self.handlers.get(matching_rule.handler)
            if not handler:
                raise ValueError(f"Handler not found: {matching_rule.handler}")
                
            # Execute request with timeout and retries
            result = await self._execute_with_retries(
                handler, context, matching_rule.timeout_seconds, matching_rule.retry_attempts
            )
            
            # Update success statistics
            self.stats.successful_requests += 1
            
            return result
            
        except Exception as e:
            self.stats.failed_requests += 1
            log_error("Request routing failed", e, {
                "request_id": context.request_id,
                "request_type": context.request_type.value
            })
            raise
            
        finally:
            # Update response time statistics
            execution_time = time.time() - start_time
            self._update_response_time_stats(execution_time)
            
            # Log API request
            log_api_request(
                context.request_type.value,
                "POST",
                200 if self.stats.successful_requests > 0 else 500,
                execution_time,
                extra_data={
                    "request_id": context.request_id,
                    "priority": context.priority.name
                }
            )
            
    def _find_matching_route(self, context: RequestContext) -> Optional[RouteRule]:
        """Find the first matching route for a request"""
        for rule in self.routes:
            try:
                if rule.condition(context):
                    return rule
            except Exception as e:
                log_warning(f"Error evaluating route condition for {rule.name}: {e}")
                continue
        return None
        
    async def _execute_with_retries(self, handler: Callable, context: RequestContext,
                                  timeout_seconds: int, retry_attempts: int) -> Any:
        """Execute handler with timeout and retries"""
        last_exception = None
        
        for attempt in range(retry_attempts):
            try:
                return await asyncio.wait_for(
                    handler(context),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError as e:
                last_exception = e
                log_warning(f"Request timeout on attempt {attempt + 1}/{retry_attempts}")
                if attempt < retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                last_exception = e
                log_warning(f"Request failed on attempt {attempt + 1}/{retry_attempts}: {e}")
                if attempt < retry_attempts - 1:
                    await asyncio.sleep(1)
                    
        raise last_exception or Exception("All retry attempts failed")
        
    def _update_response_time_stats(self, execution_time: float):
        """Update average response time statistics"""
        total_requests = self.stats.successful_requests + self.stats.failed_requests
        if total_requests > 0:
            current_avg = self.stats.average_response_time
            self.stats.average_response_time = (
                (current_avg * (total_requests - 1) + execution_time) / total_requests
            )
            
    async def start_workers(self, num_workers: Optional[int] = None):
        """Start background worker tasks"""
        if self.is_processing:
            return
            
        num_workers = num_workers or self.max_concurrent_workers
        self.is_processing = True
        
        for i in range(num_workers):
            task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self.worker_tasks.append(task)
            
        log_info(f"Started {num_workers} router workers")
        
    async def stop_workers(self):
        """Stop background worker tasks"""
        self.is_processing = False
        
        for task in self.worker_tasks:
            task.cancel()
            
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
            
        self.worker_tasks.clear()
        log_info("Stopped router workers")
        
    async def _worker_loop(self, worker_id: str):
        """Background worker loop"""
        log_info(f"Router worker {worker_id} started")
        
        while self.is_processing:
            try:
                # Get next request from queue
                queue_item = await self.request_queue.get()
                if queue_item:
                    context, handler = queue_item
                    try:
                        await handler(context)
                    except Exception as e:
                        log_error(f"Worker {worker_id} failed to process request", e)
                else:
                    # No requests available, wait briefly
                    await asyncio.sleep(0.1)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                log_error(f"Error in worker {worker_id}", e)
                await asyncio.sleep(1)
                
        log_info(f"Router worker {worker_id} stopped")
        
    async def queue_request(self, context: RequestContext, handler: Callable) -> bool:
        """Queue a request for background processing"""
        return await self.request_queue.put(context, handler)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return {
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "success_rate": (
                self.stats.successful_requests / max(1, self.stats.total_requests) * 100
            ),
            "average_response_time_ms": round(self.stats.average_response_time * 1000, 2),
            "requests_by_type": self.stats.requests_by_type,
            "requests_by_priority": self.stats.requests_by_priority,
            "queue_sizes": self.request_queue.size(),
            "active_workers": len(self.worker_tasks),
            "is_processing": self.is_processing,
            "total_routes": len(self.routes),
            "registered_handlers": len(self.handlers)
        }
        
    def reset_stats(self):
        """Reset routing statistics"""
        self.stats = RequestStats()
        log_info("Router statistics reset")

# Global request router instance
request_router = RequestRouter()
