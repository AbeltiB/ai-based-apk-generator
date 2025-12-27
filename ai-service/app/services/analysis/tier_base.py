"""
Base classification tier interface.

All classification tiers (Claude, Groq, Heuristic) inherit from this.
"""
import time
import asyncio
from typing import Optional
from loguru import logger
from abc import ABC, abstractmethod

from app.services.analysis.intent_config import config, RetryConfig, ClassificationTier
from app.services.analysis.intent_schemas import (
    IntentAnalysisResult, ClassificationRequest, TierMetrics
)


class ClassificationTierBase(ABC):
    """
    Abstract base class for all classification tiers.
    
    Provides:
    - Retry logic with exponential backoff
    - Performance monitoring
    - Circuit breaker pattern
    - Error handling
    """
    
    def __init__(self, tier: ClassificationTier, retry_config: RetryConfig):
        """
        Initialize classification tier.
        
        Args:
            tier: Tier identifier
            retry_config: Retry configuration
        """
        self.tier = tier
        self.retry_config = retry_config
        
        # Circuit breaker state
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        self.last_failure_time = 0
        self.circuit_open_duration = 60  # seconds
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'total_latency_ms': 0,
            'total_cost_usd': 0.0
        }
    
    @abstractmethod
    async def _classify_internal(
        self,
        request: ClassificationRequest
    ) -> IntentAnalysisResult:
        """
        Internal classification method - must be implemented by subclass.
        
        Args:
            request: Classification request
            
        Returns:
            IntentAnalysisResult
            
        Raises:
            Exception: If classification fails
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get tier name for logging"""
        pass
    
    async def classify(
        self,
        request: ClassificationRequest
    ) -> Optional[IntentAnalysisResult]:
        """
        Classify intent with retry logic.
        
        Args:
            request: Classification request
            
        Returns:
            IntentAnalysisResult or None if all retries failed
        """
        self.stats['total_requests'] += 1
        
        # Check circuit breaker
        if self.should_skip():
            logger.warning(f"⏭️  Skipping {self.get_name()} (circuit open)")
            return None
        
        tier_attempts = []
        
        for attempt in range(1, self.retry_config.max_attempts + 1):
            start_time = time.time()
            
            try:
                logger.info(
                    f"🔄 {self.get_name()} attempt {attempt}/{self.retry_config.max_attempts}"
                )
                
                # Call internal classification
                result = await self._classify_internal(request)
                
                # Calculate metrics
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Record success
                tier_attempts.append(TierMetrics(
                    tier=self.tier,
                    attempt_number=attempt,
                    success=True,
                    latency_ms=latency_ms,
                    error_message=None,
                    tokens_used=getattr(result, 'tokens_used', None),
                    estimated_cost_usd=getattr(result, 'cost_usd', 0.0)
                ))
                
                # Update result with attempts
                result.tier_attempts = tier_attempts
                result.total_latency_ms = latency_ms
                
                # Update statistics
                self.stats['successful'] += 1
                self.stats['total_latency_ms'] += latency_ms
                self.stats['total_cost_usd'] += getattr(result, 'cost_usd', 0.0)
                
                # Reset circuit breaker
                self.consecutive_failures = 0
                
                logger.info(
                    f"✅ {self.get_name()} succeeded in {latency_ms}ms "
                    f"(attempt {attempt})"
                )
                
                return result
                
            except Exception as e:
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Record failure
                tier_attempts.append(TierMetrics(
                    tier=self.tier,
                    attempt_number=attempt,
                    success=False,
                    latency_ms=latency_ms,
                    error_message=str(e)
                ))
                
                logger.warning(
                    f"⚠️  {self.get_name()} attempt {attempt} failed: {e}"
                )
                
                # If not last attempt, wait before retry
                if attempt < self.retry_config.max_attempts:
                    delay = self._calculate_retry_delay(attempt)
                    logger.debug(f"⏳ Waiting {delay:.2f}s before retry...")
                    await asyncio.sleep(delay)
        
        # All retries failed
        self.stats['failed'] += 1
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        
        logger.error(
            f"❌ {self.get_name()} failed after {self.retry_config.max_attempts} attempts"
        )
        
        return None
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """
        Calculate retry delay with exponential backoff and jitter.
        
        Args:
            attempt: Current attempt number
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = min(
            self.retry_config.initial_delay * (self.retry_config.exponential_base ** (attempt - 1)),
            self.retry_config.max_delay
        )
        
        # Add jitter if enabled
        if self.retry_config.jitter:
            import random
            jitter = delay * 0.1 * random.random()
            delay += jitter
        
        return delay
    
    def should_skip(self) -> bool:
        """
        Check if tier should be skipped (circuit breaker).
        
        Returns:
            True if should skip
        """
        # Check if too many consecutive failures
        if self.consecutive_failures < self.max_consecutive_failures:
            return False
        
        # Check if enough time has passed since last failure
        time_since_failure = time.time() - self.last_failure_time
        
        if time_since_failure > self.circuit_open_duration:
            # Try to close circuit
            logger.info(f"🔄 Attempting to close circuit for {self.get_name()}")
            self.consecutive_failures = 0
            return False
        
        return True
    
    def get_stats(self) -> dict:
        """Get tier statistics"""
        total = self.stats['total_requests']
        
        return {
            **self.stats,
            'success_rate': (self.stats['successful'] / total * 100) if total > 0 else 0,
            'avg_latency_ms': (self.stats['total_latency_ms'] / self.stats['successful']) 
                if self.stats['successful'] > 0 else 0,
            'avg_cost_usd': (self.stats['total_cost_usd'] / self.stats['successful'])
                if self.stats['successful'] > 0 else 0
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'total_latency_ms': 0,
            'total_cost_usd': 0.0
        }