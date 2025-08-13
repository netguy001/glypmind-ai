"""
Evolution Engine for GlyphMind AI
Handles background learning, self-improvement, and autonomous knowledge acquisition
"""
import asyncio
import time
import random
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

from logs.logger import log_info, log_error, log_evolution, log_warning
from config.config_manager import get_config
from web_intel.web_intelligence import web_intelligence, WebIntelRequest
from knowledge_base.knowledge_manager import knowledge_manager

class LearningMode(Enum):
    """Learning modes for evolution engine"""
    PASSIVE = "passive"  # Learn from user interactions
    ACTIVE = "active"    # Proactively search for information
    ADAPTIVE = "adaptive"  # Adjust learning based on usage patterns

class TopicPriority(Enum):
    """Priority levels for learning topics"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

@dataclass
class LearningTopic:
    """Topic for autonomous learning"""
    name: str
    keywords: List[str]
    priority: TopicPriority = TopicPriority.MEDIUM
    last_updated: Optional[datetime] = None
    learning_frequency_hours: int = 24
    sources: List[str] = field(default_factory=lambda: ["google", "youtube", "reddit"])
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now() - timedelta(days=1)  # Force initial learning

@dataclass
class LearningSession:
    """Learning session data"""
    topic: str
    start_time: datetime
    end_time: Optional[datetime] = None
    results_found: int = 0
    knowledge_stored: int = 0
    errors: List[str] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

class EvolutionEngine:
    """Main evolution engine for autonomous learning"""
    
    def __init__(self):
        self.is_running = False
        self.learning_topics: Dict[str, LearningTopic] = {}
        self.learning_history: List[LearningSession] = []
        self.user_interaction_patterns: Dict[str, Any] = {}
        self.background_task: Optional[asyncio.Task] = None
        
        # Initialize default learning topics
        self._initialize_default_topics()
        
    def _initialize_default_topics(self):
        """Initialize default learning topics"""
        default_topics = [
            LearningTopic(
                name="ai_technology",
                keywords=["artificial intelligence", "machine learning", "neural networks", "AI news"],
                priority=TopicPriority.HIGH,
                learning_frequency_hours=12
            ),
            LearningTopic(
                name="programming",
                keywords=["programming languages", "software development", "coding best practices", "new frameworks"],
                priority=TopicPriority.HIGH,
                learning_frequency_hours=24
            ),
            LearningTopic(
                name="technology_trends",
                keywords=["technology trends", "tech news", "innovation", "startups"],
                priority=TopicPriority.MEDIUM,
                learning_frequency_hours=24
            ),
            LearningTopic(
                name="science_research",
                keywords=["scientific research", "breakthrough", "discoveries", "academic papers"],
                priority=TopicPriority.MEDIUM,
                learning_frequency_hours=48
            ),
            LearningTopic(
                name="mathematics",
                keywords=["mathematics", "mathematical proofs", "algorithms", "computational math"],
                priority=TopicPriority.MEDIUM,
                learning_frequency_hours=72
            ),
            LearningTopic(
                name="current_events",
                keywords=["world news", "current events", "global developments"],
                priority=TopicPriority.LOW,
                learning_frequency_hours=6
            )
        ]
        
        for topic in default_topics:
            self.learning_topics[topic.name] = topic
            
    async def initialize(self):
        """Initialize evolution engine"""
        log_info("Initializing Evolution Engine")
        
        config = get_config()
        if not config.evolution.background_learning_enabled:
            log_info("Background learning is disabled in configuration")
            return True
            
        # Load any saved learning topics and patterns
        await self._load_learning_state()
        
        log_info(f"Evolution Engine initialized with {len(self.learning_topics)} learning topics")
        return True
        
    async def start_background_learning(self):
        """Start background learning process"""
        if self.is_running:
            log_warning("Background learning is already running")
            return
            
        config = get_config()
        if not config.evolution.background_learning_enabled:
            log_info("Background learning is disabled")
            return
            
        self.is_running = True
        self.background_task = asyncio.create_task(self._background_learning_loop())
        log_info("Background learning started")
        
    async def stop_background_learning(self):
        """Stop background learning process"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.background_task:
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass
                
        log_info("Background learning stopped")
        
    async def _background_learning_loop(self):
        """Main background learning loop"""
        config = get_config()
        learning_interval = config.evolution.learning_interval_minutes * 60  # Convert to seconds
        
        log_evolution("Background learning loop started")
        
        while self.is_running:
            try:
                # Check which topics need learning
                topics_to_learn = self._get_topics_needing_update()
                
                if topics_to_learn:
                    # Limit concurrent learning sessions
                    max_concurrent = config.evolution.max_concurrent_searches
                    learning_tasks = []
                    
                    for topic in topics_to_learn[:max_concurrent]:
                        task = asyncio.create_task(self._learn_topic(topic))
                        learning_tasks.append(task)
                        
                    if learning_tasks:
                        await asyncio.gather(*learning_tasks, return_exceptions=True)
                        
                # Wait for next learning cycle
                await asyncio.sleep(learning_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                log_error("Error in background learning loop", e)
                await asyncio.sleep(60)  # Wait before retrying
                
        log_evolution("Background learning loop ended")
        
    def _get_topics_needing_update(self) -> List[LearningTopic]:
        """Get topics that need learning updates"""
        topics_to_learn = []
        current_time = datetime.now()
        
        for topic in self.learning_topics.values():
            time_since_update = current_time - topic.last_updated
            hours_since_update = time_since_update.total_seconds() / 3600
            
            if hours_since_update >= topic.learning_frequency_hours:
                topics_to_learn.append(topic)
                
        # Sort by priority and staleness
        topics_to_learn.sort(key=lambda t: (t.priority.value, -((current_time - t.last_updated).total_seconds())))
        
        return topics_to_learn
        
    async def _learn_topic(self, topic: LearningTopic):
        """Learn about a specific topic"""
        session = LearningSession(
            topic=topic.name,
            start_time=datetime.now()
        )
        
        log_evolution(f"Starting learning session for topic: {topic.name}")
        
        try:
            total_results = 0
            total_stored = 0
            
            # Search for information on each keyword
            for keyword in topic.keywords:
                try:
                    # Create web intelligence request
                    request = WebIntelRequest(
                        query=keyword,
                        source_types=topic.sources,
                        max_results=5,  # Limit results per keyword
                        time_filter="week"  # Focus on recent information
                    )
                    
                    # Perform search
                    results = await web_intelligence.search(request)
                    total_results += len(results)
                    
                    # Store knowledge from results
                    if results:
                        stored_count = await knowledge_manager.learn_from_web_results(keyword, results)
                        total_stored += stored_count
                        
                    # Small delay between searches
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    error_msg = f"Error learning keyword '{keyword}': {str(e)}"
                    session.errors.append(error_msg)
                    log_error("Error in topic learning", e, {"topic": topic.name, "keyword": keyword})
                    
            # Update topic learning timestamp
            topic.last_updated = datetime.now()
            
            # Complete session
            session.end_time = datetime.now()
            session.results_found = total_results
            session.knowledge_stored = total_stored
            
            # Log learning results
            learning_data = {
                "topic": topic.name,
                "keywords_searched": len(topic.keywords),
                "results_found": total_results,
                "knowledge_stored": total_stored,
                "duration_seconds": (session.end_time - session.start_time).total_seconds(),
                "errors": len(session.errors)
            }
            
            log_evolution(f"Completed learning session for {topic.name}", learning_data)
            
            # Store session history
            self.learning_history.append(session)
            
            # Limit history size
            if len(self.learning_history) > 100:
                self.learning_history = self.learning_history[-50:]
                
        except Exception as e:
            session.errors.append(f"Critical error: {str(e)}")
            log_error("Critical error in topic learning", e, {"topic": topic.name})
            
    async def learn_from_user_interaction(self, query: str, response: str, 
                                        user_feedback: Optional[str] = None):
        """Learn from user interactions"""
        try:
            # Extract topics from user query
            potential_topics = self._extract_topics_from_query(query)
            
            # Update interaction patterns
            self._update_interaction_patterns(query, potential_topics)
            
            # Adaptively create or update learning topics
            await self._adapt_learning_topics(potential_topics, query)
            
            log_evolution("Learned from user interaction", {
                "query_length": len(query),
                "extracted_topics": potential_topics,
                "has_feedback": user_feedback is not None
            })
            
        except Exception as e:
            log_error("Error learning from user interaction", e)
            
    def _extract_topics_from_query(self, query: str) -> List[str]:
        """Extract potential learning topics from user query"""
        query_lower = query.lower()
        topics = []
        
        # Technical topics
        if any(keyword in query_lower for keyword in ['programming', 'code', 'software', 'algorithm']):
            topics.append("programming")
            
        if any(keyword in query_lower for keyword in ['ai', 'artificial intelligence', 'machine learning', 'neural']):
            topics.append("ai_technology")
            
        if any(keyword in query_lower for keyword in ['math', 'mathematics', 'equation', 'formula', 'calculate']):
            topics.append("mathematics")
            
        if any(keyword in query_lower for keyword in ['science', 'research', 'study', 'experiment']):
            topics.append("science_research")
            
        if any(keyword in query_lower for keyword in ['news', 'current', 'today', 'recent', 'latest']):
            topics.append("current_events")
            
        if any(keyword in query_lower for keyword in ['technology', 'tech', 'innovation', 'digital']):
            topics.append("technology_trends")
            
        return topics
        
    def _update_interaction_patterns(self, query: str, topics: List[str]):
        """Update user interaction patterns"""
        current_hour = datetime.now().hour
        
        # Track query frequency by hour
        if "hourly_queries" not in self.user_interaction_patterns:
            self.user_interaction_patterns["hourly_queries"] = {}
            
        hour_key = str(current_hour)
        self.user_interaction_patterns["hourly_queries"][hour_key] = \
            self.user_interaction_patterns["hourly_queries"].get(hour_key, 0) + 1
            
        # Track topic interest
        if "topic_interest" not in self.user_interaction_patterns:
            self.user_interaction_patterns["topic_interest"] = {}
            
        for topic in topics:
            self.user_interaction_patterns["topic_interest"][topic] = \
                self.user_interaction_patterns["topic_interest"].get(topic, 0) + 1
                
    async def _adapt_learning_topics(self, user_topics: List[str], query: str):
        """Adaptively update learning topics based on user interests"""
        for topic_name in user_topics:
            if topic_name in self.learning_topics:
                # Increase learning frequency for topics user is interested in
                topic = self.learning_topics[topic_name]
                if topic.learning_frequency_hours > 12:  # Don't go below 12 hours
                    topic.learning_frequency_hours = max(12, topic.learning_frequency_hours - 2)
                    
                # Boost priority if user shows high interest
                interest_count = self.user_interaction_patterns.get("topic_interest", {}).get(topic_name, 0)
                if interest_count > 5 and topic.priority.value > TopicPriority.HIGH.value:
                    topic.priority = TopicPriority.HIGH
                    log_evolution(f"Boosted priority for topic {topic_name} due to user interest")
                    
    async def add_learning_topic(self, name: str, keywords: List[str], 
                               priority: TopicPriority = TopicPriority.MEDIUM,
                               frequency_hours: int = 24) -> bool:
        """Add a new learning topic"""
        try:
            topic = LearningTopic(
                name=name,
                keywords=keywords,
                priority=priority,
                learning_frequency_hours=frequency_hours
            )
            
            self.learning_topics[name] = topic
            log_evolution(f"Added new learning topic: {name}")
            return True
            
        except Exception as e:
            log_error("Failed to add learning topic", e, {"topic_name": name})
            return False
            
    async def remove_learning_topic(self, name: str) -> bool:
        """Remove a learning topic"""
        if name in self.learning_topics:
            del self.learning_topics[name]
            log_evolution(f"Removed learning topic: {name}")
            return True
        return False
        
    async def get_learning_status(self) -> Dict[str, Any]:
        """Get current learning status"""
        current_time = datetime.now()
        
        topic_status = {}
        for name, topic in self.learning_topics.items():
            hours_since_update = (current_time - topic.last_updated).total_seconds() / 3600
            needs_update = hours_since_update >= topic.learning_frequency_hours
            
            topic_status[name] = {
                "priority": topic.priority.value,
                "frequency_hours": topic.learning_frequency_hours,
                "hours_since_update": round(hours_since_update, 1),
                "needs_update": needs_update,
                "keywords_count": len(topic.keywords)
            }
            
        recent_sessions = [
            {
                "topic": session.topic,
                "start_time": session.start_time.isoformat(),
                "duration_seconds": (session.end_time - session.start_time).total_seconds() if session.end_time else None,
                "results_found": session.results_found,
                "knowledge_stored": session.knowledge_stored,
                "errors": len(session.errors)
            }
            for session in self.learning_history[-10:]  # Last 10 sessions
        ]
        
        return {
            "is_running": self.is_running,
            "total_topics": len(self.learning_topics),
            "topics": topic_status,
            "recent_sessions": recent_sessions,
            "interaction_patterns": self.user_interaction_patterns,
            "last_update": current_time.isoformat()
        }
        
    async def _load_learning_state(self):
        """Load learning state from storage"""
        # TODO: Implement persistent storage of learning state
        # For now, use defaults
        pass
        
    async def _save_learning_state(self):
        """Save learning state to storage"""
        # TODO: Implement persistent storage of learning state
        pass

# Global evolution engine instance
evolution_engine = EvolutionEngine()

async def start_evolution() -> bool:
    """Start the evolution engine"""
    try:
        await evolution_engine.initialize()
        await evolution_engine.start_background_learning()
        return True
    except Exception as e:
        log_error("Failed to start evolution engine", e)
        return False

async def stop_evolution():
    """Stop the evolution engine"""
    await evolution_engine.stop_background_learning()
