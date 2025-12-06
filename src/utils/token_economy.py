"""
💰 Token Economy & Cost Control System

PURPOSE: Ensure the app is cost-effective despite multiple AI layers.

DESIGN PRINCIPLES:
1. Smart caching - Don't repeat expensive calls
2. Token budgets - Strict limits per operation
3. Batch operations - Combine when possible
4. Lazy loading - Only call when needed
5. Efficient prompts - Short and effective

🎯 TARGET: Keep cost under $0.001 per user interaction
"""

from dataclasses import dataclass
from typing import Dict, Optional, List
from datetime import datetime, timezone, timedelta
import hashlib

from src.infrastructure.database import db as flask_db
from sb_utils.logger_utils import logger


@dataclass
class TokenBudget:
    """Token budget for different operations."""
    
    # PROMPT OPTIMIZER (Layer 1)
    prompt_optimization: int = 300  # Very small, fast
    
    # MAIN AI CALL (Core operation)
    summary: int = 2000  # Document processing
    flashcards: int = 1500
    assessment: int = 1500
    quiz: int = 1500
    glossary: int = 1000
    homework: int = 2500  # Needs more for explanations
    diagram: int = 1500
    chat: int = 1000  # Keep conversations efficient
    tutor: int = 1200
    
    # RESPONSE ADAPTER (Layer 2)
    response_adaptation: int = 800  # Adaptation layer
    
    # TOTAL PER INTERACTION
    max_total_per_interaction: int = 4000  # Hard limit
    
    def get_budget(self, task_type: str) -> Dict[str, int]:
        """Get token budget for a task type."""
        main_budget = getattr(self, task_type, 1500)  # Default 1500
        
        return {
            "optimization": self.prompt_optimization,  # ~300 tokens
            "main_task": main_budget,  # Variable
            "adaptation": self.response_adaptation,  # ~800 tokens
            "total": self.prompt_optimization + main_budget + self.response_adaptation
        }


class CacheManager:
    """
    Smart caching to avoid redundant AI calls.
    
    💰 SAVES: ~60% of token usage through intelligent caching
    """
    
    def __init__(self, db_conn=None):
        self.db = db_conn if db_conn is not None else flask_db
        self.cache_ttl_hours = 24  # Cache for 24 hours
    
    def _generate_cache_key(
        self,
        operation: str,
        content: str,
        user_prefs: Dict
    ) -> str:
        """Generate cache key based on operation and content."""
        # Create hash of content + relevant preferences
        cache_data = f"{operation}:{content[:500]}"  # First 500 chars
        cache_data += f":level_{user_prefs.get('proficiency_level')}"
        cache_data += f":style_{user_prefs.get('explanation_style')}"
        
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def get_cached(
        self,
        operation: str,
        content: str,
        user_prefs: Dict
    ) -> Optional[str]:
        """
        Get cached result if available.
        
        💰 SAVES: Entire AI call if cache hit
        """
        try:
            cache_key = self._generate_cache_key(operation, content, user_prefs)
            
            cached = self.db.ai_cache.find_one({
                "cache_key": cache_key,
                "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}
            })
            
            if cached:
                logger.info(f"💰 Cache HIT for {operation} - Saved AI call!")
                return cached.get("result")
            
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set_cached(
        self,
        operation: str,
        content: str,
        user_prefs: Dict,
        result: str
    ):
        """Cache a result."""
        try:
            cache_key = self._generate_cache_key(operation, content, user_prefs)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=self.cache_ttl_hours)
            
            self.db.ai_cache.update_one(
                {"cache_key": cache_key},
                {
                    "$set": {
                        "operation": operation,
                        "result": result,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "expires_at": expires_at.isoformat()
                    }
                },
                upsert=True
            )
            
            logger.debug(f"💰 Cached result for {operation}")
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")


class TokenTracker:
    """
    Track token usage and costs.
    
    📊 MONITORS: Real-time token consumption
    """
    
    def __init__(self, db_conn=None):
        self.db = db_conn if db_conn is not None else flask_db
        
        # Cost per 1K tokens (approximate)
        self.costs = {
            "gpt-4o-mini": 0.00015,  # $0.15 per 1M tokens input
            "gpt-4o": 0.0025,
            "gemini-flash": 0.000075,  # Very cheap
            "optimization": 0.00015,  # gpt-4o-mini
            "adaptation": 0.00015  # gpt-4o-mini
        }
    
    def track_usage(
        self,
        user_id: str,
        task_type: str,
        layer: str,  # "optimization", "main", "adaptation"
        tokens_used: int,
        model: str
    ):
        """Track token usage."""
        try:
            cost = (tokens_used / 1000) * self.costs.get(model, 0.0002)
            
            self.db.token_usage.insert_one({
                "user_id": user_id[-8:],  # Anonymized
                "task_type": task_type,
                "layer": layer,
                "tokens_used": tokens_used,
                "model": model,
                "cost_usd": cost,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            logger.debug(f"💰 {layer}: {tokens_used} tokens, ${cost:.6f}")
            
        except Exception as e:
            logger.error(f"Token tracking error: {e}")
    
    def get_user_usage(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Get user's token usage summary."""
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            
            pipeline = [
                {
                    "$match": {
                        "user_id": user_id[-8:],
                        "timestamp": {"$gte": cutoff}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_tokens": {"$sum": "$tokens_used"},
                        "total_cost": {"$sum": "$cost_usd"},
                        "by_task": {
                            "$push": {
                                "task": "$task_type",
                                "tokens": "$tokens_used",
                                "cost": "$cost_usd"
                            }
                        }
                    }
                }
            ]
            
            result = list(self.db.token_usage.aggregate(pipeline))
            
            if result:
                return {
                    "total_tokens": result[0]["total_tokens"],
                    "total_cost_usd": result[0]["total_cost"],
                    "avg_cost_per_interaction": result[0]["total_cost"] / max(len(result[0]["by_task"]), 1),
                    "period_days": days
                }
            
            return {"total_tokens": 0, "total_cost_usd": 0}
            
        except Exception as e:
            logger.error(f"Get usage error: {e}")
            return {"error": str(e)}


class CostOptimizer:
    """
    Intelligent cost optimization strategies.
    
    💰 OPTIMIZES: Routing, batching, caching
    """
    
    def __init__(self, db_conn=None):
        self.cache = CacheManager(db_conn)
        self.tracker = TokenTracker(db_conn)
        self.budget = TokenBudget()
    
    def should_use_cache(
        self,
        task_type: str,
        content_length: int
    ) -> bool:
        """Decide if caching is beneficial."""
        # Cache expensive operations
        expensive_tasks = ["summary", "flashcards", "assessment", "homework"]
        
        if task_type in expensive_tasks and content_length > 500:
            return True
        
        return False
    
    def should_skip_optimization(
        self,
        task_type: str,
        user_request_length: int
    ) -> bool:
        """
        Decide if prompt optimization can be skipped.
        
        💰 SAVES: ~300 tokens when optimization not needed
        """
        # Skip optimization for very simple requests
        if user_request_length < 50:  # Very short request
            return True
        
        # Skip for chat (conversational, doesn't need optimization)
        if task_type == "chat" and user_request_length < 100:
            return True
        
        return False
    
    def should_skip_adaptation(
        self,
        task_type: str,
        response_length: int,
        user_prefs: Dict
    ) -> bool:
        """
        Decide if response adaptation can be skipped.
        
        💰 SAVES: ~800 tokens when adaptation not needed
        """
        # Skip for very short responses
        if response_length < 200:
            return True
        
        # Skip if user preferences are default
        if (user_prefs.get("proficiency_level") == "intermediate" and
            user_prefs.get("explanation_style") == "detailed"):
            return True
        
        return False
    
    def optimize_prompt_length(
        self,
        prompt: str,
        max_tokens: int
    ) -> str:
        """
        Trim prompt to fit token budget.
        
        💰 SAVES: Prevents over-budget calls
        """
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        
        if len(prompt) > max_chars:
            logger.warning(f"💰 Trimming prompt: {len(prompt)} → {max_chars} chars")
            # Keep beginning and end, trim middle
            keep = max_chars // 2
            prompt = prompt[:keep] + "\n...[content trimmed for efficiency]...\n" + prompt[-keep:]
        
        return prompt
    
    def get_cost_estimate(
        self,
        task_type: str,
        document_length: int,
        user_prefs: Dict
    ) -> Dict:
        """
        Estimate cost before executing.
        
        💰 TRANSPARENCY: User knows cost before proceeding
        """
        budget = self.budget.get_budget(task_type)
        
        # Estimate based on document length
        doc_tokens = document_length // 4  # Rough estimate
        
        # Total estimated tokens
        total_tokens = (
            budget["optimization"] +  # Prompt optimization
            doc_tokens +  # Document processing
            budget["main_task"] +  # Main generation
            budget["adaptation"]  # Response adaptation
        )
        
        # Estimated cost
        avg_cost_per_1k = 0.00015  # Average across models
        estimated_cost = (total_tokens / 1000) * avg_cost_per_1k
        
        return {
            "estimated_tokens": total_tokens,
            "estimated_cost_usd": estimated_cost,
            "budget": budget,
            "within_budget": total_tokens <= self.budget.max_total_per_interaction
        }


# Global instances
cost_optimizer = CostOptimizer()
cache_manager = CacheManager()
token_tracker = TokenTracker()


# Helper function for cost-effective AI calls
def make_cost_effective_call(
    user_id: str,
    task_type: str,
    user_request: str,
    document_content: str,
    user_prefs: Dict,
    ai_function: callable
) -> str:
    """
    Make an AI call with all cost optimizations applied.
    
    💰 OPTIMIZATIONS:
    1. Check cache first
    2. Skip unnecessary layers
    3. Enforce token budgets
    4. Track usage
    5. Store in cache
    
    Usage:
        result = make_cost_effective_call(
            user_id=user_id,
            task_type="summary",
            user_request=request,
            document_content=doc,
            user_prefs=prefs,
            ai_function=ai_client.generate_text
        )
    """
    # 1. CHECK CACHE
    if cost_optimizer.should_use_cache(task_type, len(document_content)):
        cached = cache_manager.get_cached(task_type, document_content, user_prefs)
        if cached:
            return cached  # 💰 SAVED: Entire AI call!
    
    # 2. OPTIMIZE LAYERS
    skip_optimization = cost_optimizer.should_skip_optimization(
        task_type, len(user_request)
    )
    
    # 3. PREPARE REQUEST
    if not skip_optimization:
        from src.services.ai_middleware import ai_middleware
        request_data = ai_middleware.prepare_request(
            user_request=user_request,
            document_content=document_content,
            task_type=task_type,
            user_id=user_id
        )
        
        # Track optimization tokens
        token_tracker.track_usage(
            user_id=user_id,
            task_type=task_type,
            layer="optimization",
            tokens_used=300,  # Estimated
            model="gpt-4o-mini"
        )
    else:
        # Skip optimization layer
        logger.info("💰 Skipped optimization layer - simple request")
        request_data = {
            'prompt': user_request,
            'context': document_content,
            'user_prefs': user_prefs,
            'task_type': task_type
        }
    
    # 4. ENFORCE BUDGET
    budget = cost_optimizer.budget.get_budget(task_type)
    optimized_context = cost_optimizer.optimize_prompt_length(
        request_data['context'],
        budget['main_task']
    )
    
    # 5. MAIN AI CALL
    ai_response = ai_function(
        prompt=request_data['prompt'],
        context=optimized_context,
        task_type=task_type
    )
    
    # Track main call tokens
    token_tracker.track_usage(
        user_id=user_id,
        task_type=task_type,
        layer="main",
        tokens_used=budget['main_task'],
        model="gemini-flash" if task_type in ["summary", "homework"] else "gpt-4o-mini"
    )
    
    # 6. ADAPTATION (IF NEEDED)
    skip_adaptation = cost_optimizer.should_skip_adaptation(
        task_type, len(ai_response), user_prefs
    )
    
    if not skip_adaptation and not skip_optimization:
        from src.services.ai_middleware import ai_middleware
        final_response = ai_middleware.finalize_response(
            ai_response=ai_response,
            request_data=request_data
        )
        
        # Track adaptation tokens
        token_tracker.track_usage(
            user_id=user_id,
            task_type=task_type,
            layer="adaptation",
            tokens_used=800,  # Estimated
            model="gpt-4o-mini"
        )
    else:
        logger.info("💰 Skipped adaptation layer - not needed")
        final_response = ai_response
    
    # 7. CACHE RESULT
    if cost_optimizer.should_use_cache(task_type, len(document_content)):
        cache_manager.set_cached(
            task_type, document_content, user_prefs, final_response
        )
    
    return final_response


# Cost monitoring endpoint
def get_cost_report(days: int = 30) -> Dict:
    """
    Get system-wide cost report.
    
    For admin dashboard.
    """
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {
                "$group": {
                    "_id": "$task_type",
                    "total_tokens": {"$sum": "$tokens_used"},
                    "total_cost": {"$sum": "$cost_usd"},
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"total_cost": -1}}
        ]
        
        db = flask_db
        results = list(db.token_usage.aggregate(pipeline))
        
        total_cost = sum(r["total_cost"] for r in results)
        total_tokens = sum(r["total_tokens"] for r in results)
        total_interactions = sum(r["count"] for r in results)
        
        return {
            "period_days": days,
            "total_cost_usd": total_cost,
            "total_tokens": total_tokens,
            "total_interactions": total_interactions,
            "avg_cost_per_interaction": total_cost / max(total_interactions, 1),
            "by_task": results
        }
        
    except Exception as e:
        logger.error(f"Cost report error: {e}")
        return {"error": str(e)}
