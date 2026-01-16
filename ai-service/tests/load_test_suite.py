"""
ai-service/tests/load_test_suite.py

Comprehensive load test suite for AI service.
Tests 100 concurrent requests with various scenarios:
- Different app types (simple, medium, complex)
- Different screen counts (single, multi)
- Different users and priorities
- Queue processing
- Redis caching
- Database persistence
- Progress tracking

Usage:
    python tests/load_test_suite.py

Requirements:
    pip install asyncio aiohttp rich tabulate
"""
import asyncio
import aiohttp
import json
import time
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import sys
from pathlib import Path

# Rich for beautiful terminal output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Install 'rich' for better output: pip install rich")

# Tabulate for summary tables
try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False
    print("⚠️  Install 'tabulate' for summary: pip install tabulate")


# ============================================================================
# TEST SCENARIOS
# ============================================================================

class AppComplexity(str, Enum):
    """App complexity levels."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class AppType(str, Enum):
    """App types to test."""
    COUNTER = "counter"
    TODO = "todo"
    CALCULATOR = "calculator"
    TIMER = "timer"
    NOTES = "notes"
    WEATHER = "weather"
    CONTACTS = "contacts"
    ECOMMERCE = "ecommerce"
    SOCIAL = "social"
    GAMING = "gaming"


@dataclass
class TestScenario:
    """Test scenario definition."""
    name: str
    prompt: str
    complexity: AppComplexity
    priority: int
    user_id: str
    expected_screens: int
    tags: List[str] = field(default_factory=list)


# Define 100 test scenarios
TEST_SCENARIOS = [
    # === SIMPLE APPS (30 scenarios) ===
    # Counter apps (10)
    TestScenario("Simple Counter", "Create a counter app with + and - buttons", AppComplexity.SIMPLE, 1, "user_1", 1, ["counter", "simple"]),
    TestScenario("Counter with Reset", "Counter with increment, decrement, and reset", AppComplexity.SIMPLE, 2, "user_2", 1, ["counter", "simple"]),
    TestScenario("Step Counter", "Counter that increases by 5 each time", AppComplexity.SIMPLE, 1, "user_3", 1, ["counter", "simple"]),
    TestScenario("Countdown Timer", "Simple countdown from 10 to 0", AppComplexity.SIMPLE, 3, "user_1", 1, ["counter", "simple"]),
    TestScenario("Click Counter", "Track number of button clicks", AppComplexity.SIMPLE, 1, "user_4", 1, ["counter", "simple"]),
    TestScenario("Score Keeper", "Keep track of game score", AppComplexity.SIMPLE, 2, "user_2", 1, ["counter", "simple"]),
    TestScenario("Rep Counter", "Workout rep counter", AppComplexity.SIMPLE, 1, "user_5", 1, ["counter", "simple"]),
    TestScenario("Tally Counter", "Simple tally with reset", AppComplexity.SIMPLE, 1, "user_3", 1, ["counter", "simple"]),
    TestScenario("Vote Counter", "Yes/No vote counter", AppComplexity.SIMPLE, 2, "user_1", 1, ["counter", "simple"]),
    TestScenario("Page Counter", "Book page tracker", AppComplexity.SIMPLE, 1, "user_4", 1, ["counter", "simple"]),
    
    # Hello World variants (10)
    TestScenario("Hello World", "Simple hello world button", AppComplexity.SIMPLE, 1, "user_5", 1, ["basic", "simple"]),
    TestScenario("Welcome Screen", "Welcome message with button", AppComplexity.SIMPLE, 1, "user_2", 1, ["basic", "simple"]),
    TestScenario("Greeting App", "Show personalized greeting", AppComplexity.SIMPLE, 2, "user_1", 1, ["basic", "simple"]),
    TestScenario("Name Display", "Display user's name", AppComplexity.SIMPLE, 1, "user_3", 1, ["basic", "simple"]),
    TestScenario("Quote Display", "Show daily quote", AppComplexity.SIMPLE, 1, "user_4", 1, ["basic", "simple"]),
    TestScenario("Motivational", "Motivational message app", AppComplexity.SIMPLE, 2, "user_5", 1, ["basic", "simple"]),
    TestScenario("Status Display", "Display system status", AppComplexity.SIMPLE, 1, "user_2", 1, ["basic", "simple"]),
    TestScenario("Info Screen", "Show app information", AppComplexity.SIMPLE, 1, "user_1", 1, ["basic", "simple"]),
    TestScenario("Splash Screen", "Simple splash with logo", AppComplexity.SIMPLE, 2, "user_3", 1, ["basic", "simple"]),
    TestScenario("Loading Screen", "Loading indicator", AppComplexity.SIMPLE, 1, "user_4", 1, ["basic", "simple"]),
    
    # Calculator variants (10)
    TestScenario("Simple Calc", "Basic calculator with +,-,*,/", AppComplexity.SIMPLE, 2, "user_5", 1, ["calculator", "simple"]),
    TestScenario("Tip Calculator", "Calculate restaurant tip", AppComplexity.SIMPLE, 1, "user_1", 1, ["calculator", "simple"]),
    TestScenario("BMI Calculator", "Calculate body mass index", AppComplexity.SIMPLE, 2, "user_2", 1, ["calculator", "simple"]),
    TestScenario("Age Calculator", "Calculate age from birthdate", AppComplexity.SIMPLE, 1, "user_3", 1, ["calculator", "simple"]),
    TestScenario("Unit Converter", "Convert units", AppComplexity.SIMPLE, 1, "user_4", 1, ["calculator", "simple"]),
    TestScenario("Percentage Calc", "Calculate percentages", AppComplexity.SIMPLE, 2, "user_5", 1, ["calculator", "simple"]),
    TestScenario("Discount Calc", "Calculate discounts", AppComplexity.SIMPLE, 1, "user_1", 1, ["calculator", "simple"]),
    TestScenario("Split Bill", "Split bill between friends", AppComplexity.SIMPLE, 1, "user_2", 1, ["calculator", "simple"]),
    TestScenario("Loan Calculator", "Simple loan calculator", AppComplexity.SIMPLE, 2, "user_3", 1, ["calculator", "simple"]),
    TestScenario("Tax Calculator", "Calculate tax amount", AppComplexity.SIMPLE, 1, "user_4", 1, ["calculator", "simple"]),
    
    # === MEDIUM COMPLEXITY (40 scenarios) ===
    # Todo apps (10)
    TestScenario("Todo List", "Todo app with add and delete", AppComplexity.MEDIUM, 2, "user_5", 1, ["todo", "medium"]),
    TestScenario("Task Manager", "Manage daily tasks", AppComplexity.MEDIUM, 3, "user_1", 1, ["todo", "medium"]),
    TestScenario("Checklist", "Simple checklist app", AppComplexity.MEDIUM, 1, "user_2", 1, ["todo", "medium"]),
    TestScenario("Shopping List", "Grocery shopping list", AppComplexity.MEDIUM, 2, "user_3", 1, ["todo", "medium"]),
    TestScenario("Project Tasks", "Track project tasks", AppComplexity.MEDIUM, 1, "user_4", 1, ["todo", "medium"]),
    TestScenario("Goal Tracker", "Track personal goals", AppComplexity.MEDIUM, 3, "user_5", 1, ["todo", "medium"]),
    TestScenario("Habit Tracker", "Daily habit tracker", AppComplexity.MEDIUM, 2, "user_1", 1, ["todo", "medium"]),
    TestScenario("Bucket List", "Life bucket list app", AppComplexity.MEDIUM, 1, "user_2", 1, ["todo", "medium"]),
    TestScenario("Reading List", "Books to read tracker", AppComplexity.MEDIUM, 1, "user_3", 1, ["todo", "medium"]),
    TestScenario("Wish List", "Product wish list", AppComplexity.MEDIUM, 2, "user_4", 1, ["todo", "medium"]),
    
    # Notes apps (10)
    TestScenario("Note Taking", "Simple note taking app", AppComplexity.MEDIUM, 2, "user_5", 2, ["notes", "medium"]),
    TestScenario("Journal App", "Daily journal entries", AppComplexity.MEDIUM, 3, "user_1", 2, ["notes", "medium"]),
    TestScenario("Recipe Book", "Save favorite recipes", AppComplexity.MEDIUM, 2, "user_2", 2, ["notes", "medium"]),
    TestScenario("Diary", "Personal diary app", AppComplexity.MEDIUM, 1, "user_3", 2, ["notes", "medium"]),
    TestScenario("Ideas Collection", "Collect random ideas", AppComplexity.MEDIUM, 2, "user_4", 2, ["notes", "medium"]),
    TestScenario("Meeting Notes", "Take meeting notes", AppComplexity.MEDIUM, 3, "user_5", 2, ["notes", "medium"]),
    TestScenario("Study Notes", "Student note taking", AppComplexity.MEDIUM, 2, "user_1", 2, ["notes", "medium"]),
    TestScenario("Travel Journal", "Document travels", AppComplexity.MEDIUM, 1, "user_2", 2, ["notes", "medium"]),
    TestScenario("Workout Log", "Log workout sessions", AppComplexity.MEDIUM, 2, "user_3", 2, ["notes", "medium"]),
    TestScenario("Food Diary", "Track meals eaten", AppComplexity.MEDIUM, 1, "user_4", 2, ["notes", "medium"]),
    
    # Timer/Stopwatch (10)
    TestScenario("Stopwatch", "Simple stopwatch timer", AppComplexity.MEDIUM, 2, "user_5", 1, ["timer", "medium"]),
    TestScenario("Pomodoro Timer", "25-min work timer", AppComplexity.MEDIUM, 3, "user_1", 1, ["timer", "medium"]),
    TestScenario("Interval Timer", "HIIT interval timer", AppComplexity.MEDIUM, 2, "user_2", 1, ["timer", "medium"]),
    TestScenario("Cooking Timer", "Multiple cooking timers", AppComplexity.MEDIUM, 1, "user_3", 1, ["timer", "medium"]),
    TestScenario("Meditation Timer", "Meditation countdown", AppComplexity.MEDIUM, 2, "user_4", 1, ["timer", "medium"]),
    TestScenario("Tea Timer", "Tea brewing timer", AppComplexity.MEDIUM, 1, "user_5", 1, ["timer", "medium"]),
    TestScenario("Parking Timer", "Parking meter timer", AppComplexity.MEDIUM, 2, "user_1", 1, ["timer", "medium"]),
    TestScenario("Study Timer", "Study session timer", AppComplexity.MEDIUM, 3, "user_2", 1, ["timer", "medium"]),
    TestScenario("Lap Timer", "Track laps and splits", AppComplexity.MEDIUM, 2, "user_3", 1, ["timer", "medium"]),
    TestScenario("Sleep Timer", "Sleep countdown", AppComplexity.MEDIUM, 1, "user_4", 1, ["timer", "medium"]),
    
    # Multi-screen apps (10)
    TestScenario("Contact List", "Manage contacts", AppComplexity.MEDIUM, 2, "user_5", 2, ["contacts", "medium", "multi"]),
    TestScenario("Settings App", "App settings manager", AppComplexity.MEDIUM, 3, "user_1", 2, ["settings", "medium", "multi"]),
    TestScenario("Photo Gallery", "Browse photos", AppComplexity.MEDIUM, 2, "user_2", 2, ["gallery", "medium", "multi"]),
    TestScenario("Music Player", "Simple music player", AppComplexity.MEDIUM, 1, "user_3", 2, ["media", "medium", "multi"]),
    TestScenario("Weather App", "Weather forecast", AppComplexity.MEDIUM, 2, "user_4", 2, ["weather", "medium", "multi"]),
    TestScenario("News Reader", "Read news articles", AppComplexity.MEDIUM, 3, "user_5", 2, ["news", "medium", "multi"]),
    TestScenario("Product Catalog", "Browse products", AppComplexity.MEDIUM, 2, "user_1", 2, ["catalog", "medium", "multi"]),
    TestScenario("Restaurant Menu", "Digital menu", AppComplexity.MEDIUM, 1, "user_2", 2, ["menu", "medium", "multi"]),
    TestScenario("Event List", "Browse events", AppComplexity.MEDIUM, 2, "user_3", 2, ["events", "medium", "multi"]),
    TestScenario("Job Board", "Job listings", AppComplexity.MEDIUM, 1, "user_4", 2, ["jobs", "medium", "multi"]),
    
    # === COMPLEX APPS (30 scenarios) ===
    # E-commerce (10)
    TestScenario("Shopping Cart", "E-commerce with cart", AppComplexity.COMPLEX, 3, "user_5", 3, ["ecommerce", "complex", "multi"]),
    TestScenario("Online Store", "Full online store", AppComplexity.COMPLEX, 5, "user_1", 4, ["ecommerce", "complex", "multi"]),
    TestScenario("Marketplace", "Buy/sell marketplace", AppComplexity.COMPLEX, 4, "user_2", 3, ["ecommerce", "complex", "multi"]),
    TestScenario("Auction App", "Online auction system", AppComplexity.COMPLEX, 3, "user_3", 3, ["ecommerce", "complex", "multi"]),
    TestScenario("Booking System", "Appointment booking", AppComplexity.COMPLEX, 5, "user_4", 4, ["booking", "complex", "multi"]),
    TestScenario("Food Delivery", "Order food online", AppComplexity.COMPLEX, 4, "user_5", 3, ["delivery", "complex", "multi"]),
    TestScenario("Rental Platform", "Rent items", AppComplexity.COMPLEX, 3, "user_1", 3, ["rental", "complex", "multi"]),
    TestScenario("Service Marketplace", "Find services", AppComplexity.COMPLEX, 4, "user_2", 4, ["services", "complex", "multi"]),
    TestScenario("Subscription Box", "Monthly subscription", AppComplexity.COMPLEX, 5, "user_3", 3, ["subscription", "complex", "multi"]),
    TestScenario("Ticketing System", "Event tickets", AppComplexity.COMPLEX, 3, "user_4", 3, ["tickets", "complex", "multi"]),
    
    # Social apps (10)
    TestScenario("Social Feed", "Social media feed", AppComplexity.COMPLEX, 4, "user_5", 4, ["social", "complex", "multi"]),
    TestScenario("Chat App", "Messaging application", AppComplexity.COMPLEX, 5, "user_1", 3, ["chat", "complex", "multi"]),
    TestScenario("Forum", "Discussion forum", AppComplexity.COMPLEX, 3, "user_2", 3, ["forum", "complex", "multi"]),
    TestScenario("Dating App", "Dating profile matcher", AppComplexity.COMPLEX, 5, "user_3", 4, ["dating", "complex", "multi"]),
    TestScenario("Community Hub", "Local community", AppComplexity.COMPLEX, 4, "user_4", 4, ["community", "complex", "multi"]),
    TestScenario("Event Planning", "Plan group events", AppComplexity.COMPLEX, 3, "user_5", 3, ["planning", "complex", "multi"]),
    TestScenario("Photo Sharing", "Share photos socially", AppComplexity.COMPLEX, 4, "user_1", 3, ["photos", "complex", "multi"]),
    TestScenario("Blog Platform", "Personal blogging", AppComplexity.COMPLEX, 5, "user_2", 4, ["blog", "complex", "multi"]),
    TestScenario("Review Platform", "Rate and review", AppComplexity.COMPLEX, 3, "user_3", 3, ["reviews", "complex", "multi"]),
    TestScenario("Q&A Platform", "Questions and answers", AppComplexity.COMPLEX, 4, "user_4", 3, ["qa", "complex", "multi"]),
    
    # Gaming/Entertainment (10)
    TestScenario("Quiz Game", "Multiple choice quiz", AppComplexity.COMPLEX, 4, "user_5", 3, ["game", "complex", "multi"]),
    TestScenario("Trivia App", "Trivia questions", AppComplexity.COMPLEX, 3, "user_1", 3, ["game", "complex", "multi"]),
    TestScenario("Memory Game", "Card matching game", AppComplexity.COMPLEX, 5, "user_2", 2, ["game", "complex"]),
    TestScenario("Puzzle Game", "Sliding puzzle", AppComplexity.COMPLEX, 4, "user_3", 2, ["game", "complex"]),
    TestScenario("Word Game", "Word finding game", AppComplexity.COMPLEX, 3, "user_4", 3, ["game", "complex", "multi"]),
    TestScenario("Math Quiz", "Math practice game", AppComplexity.COMPLEX, 4, "user_5", 3, ["game", "complex", "multi"]),
    TestScenario("Flash Cards", "Study flash cards", AppComplexity.COMPLEX, 5, "user_1", 3, ["education", "complex", "multi"]),
    TestScenario("Language Learning", "Learn vocabulary", AppComplexity.COMPLEX, 4, "user_2", 4, ["education", "complex", "multi"]),
    TestScenario("Fitness Challenge", "Daily workout challenges", AppComplexity.COMPLEX, 3, "user_3", 3, ["fitness", "complex", "multi"]),
    TestScenario("Meditation Guide", "Guided meditations", AppComplexity.COMPLEX, 4, "user_4", 3, ["wellness", "complex", "multi"]),
]


# ============================================================================
# TEST RESULT TRACKING
# ============================================================================

@dataclass
class TestResult:
    """Individual test result."""
    scenario: TestScenario
    task_id: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "pending"  # pending, processing, completed, failed, timeout
    response_time_ms: Optional[int] = None
    error: Optional[str] = None
    progress_updates: List[Dict] = field(default_factory=list)
    final_result: Optional[Dict] = None
    cache_hit: bool = False
    
    @property
    def duration_ms(self) -> int:
        """Calculate duration in milliseconds."""
        if self.end_time:
            return int((self.end_time - self.start_time) * 1000)
        return int((time.time() - self.start_time) * 1000)
    
    @property
    def is_complete(self) -> bool:
        """Check if test is complete."""
        return self.status in ["completed", "failed", "timeout"]


# ============================================================================
# LOAD TEST RUNNER
# ============================================================================

class LoadTestRunner:
    """
    Comprehensive load test runner.
    
    Features:
    - Send 100 concurrent requests
    - Track progress in real-time
    - Monitor Redis, RabbitMQ, PostgreSQL
    - Display live statistics
    - Generate detailed report
    """
    
    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        concurrent_limit: int = 20,  # Max concurrent requests
        timeout_seconds: int = 300  # 5 minutes per request
    ):
        self.api_url = api_url
        self.concurrent_limit = concurrent_limit
        self.timeout_seconds = timeout_seconds
        
        # Results tracking
        self.results: List[TestResult] = []
        self.start_time = 0
        self.end_time = 0
        
        # Statistics
        self.stats = {
            'total': 0,
            'completed': 0,
            'failed': 0,
            'timeout': 0,
            'cache_hits': 0,
            'total_duration_ms': 0,
            'min_duration_ms': float('inf'),
            'max_duration_ms': 0,
            'by_complexity': {c: {'total': 0, 'completed': 0, 'failed': 0} for c in AppComplexity},
            'by_user': {}
        }
        
        # Console for rich output
        self.console = Console() if RICH_AVAILABLE else None
    
    async def run(self):
        """Run the complete load test suite."""
        self.print_header()
        
        self.start_time = time.time()
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.concurrent_limit)
        
        # Create tasks for all scenarios
        tasks = [
            self.run_single_test(scenario, semaphore, idx)
            for idx, scenario in enumerate(TEST_SCENARIOS, 1)
        ]
        
        # Run with progress tracking
        if RICH_AVAILABLE:
            await self.run_with_progress(tasks)
        else:
            await asyncio.gather(*tasks)
        
        self.end_time = time.time()
        
        # Generate report
        self.print_report()
    
    async def run_with_progress(self, tasks):
        """Run tests with rich progress bar."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            
            overall = progress.add_task(
                "[cyan]Overall Progress",
                total=len(tasks)
            )
            
            pending = progress.add_task(
                "[yellow]Pending",
                total=len(tasks)
            )
            
            processing = progress.add_task(
                "[blue]Processing",
                total=len(tasks)
            )
            
            completed = progress.add_task(
                "[green]Completed",
                total=len(tasks)
            )
            
            failed = progress.add_task(
                "[red]Failed",
                total=len(tasks)
            )
            
            # Update progress as tasks complete
            for coro in asyncio.as_completed(tasks):
                await coro
                
                # Update counters
                progress.update(overall, advance=1)
                
                pending_count = sum(1 for r in self.results if r.status == "pending")
                processing_count = sum(1 for r in self.results if r.status == "processing")
                completed_count = sum(1 for r in self.results if r.status == "completed")
                failed_count = sum(1 for r in self.results if r.status in ["failed", "timeout"])
                
                progress.update(pending, completed=pending_count)
                progress.update(processing, completed=processing_count)
                progress.update(completed, completed=completed_count)
                progress.update(failed, completed=failed_count)
    
    async def run_single_test(self, scenario: TestScenario, semaphore: asyncio.Semaphore, idx: int):
        """Run a single test scenario."""
        async with semaphore:
            result = TestResult(
                scenario=scenario,
                task_id="",
                start_time=time.time()
            )
            
            self.results.append(result)
            self.stats['total'] += 1
            
            try:
                # Submit request
                async with aiohttp.ClientSession() as session:
                    # Send generation request
                    request_data = {
                        "prompt": scenario.prompt,
                        "user_id": scenario.user_id,
                        "session_id": f"test_session_{idx}",
                        "priority": scenario.priority
                    }
                    
                    async with session.post(
                        f"{self.api_url}/api/v1/generate",
                        json=request_data,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 202:
                            data = await resp.json()
                            result.task_id = data['task_id']
                            result.status = "processing"
                            
                            self.log_progress(f"✓ [{idx:3d}/100] Submitted: {scenario.name}")
                        else:
                            result.status = "failed"
                            result.error = f"HTTP {resp.status}"
                            self.stats['failed'] += 1
                            return
                    
                    # Poll for completion
                    await self.poll_for_completion(result, session)
                    
            except asyncio.TimeoutError:
                result.status = "timeout"
                result.end_time = time.time()
                self.stats['timeout'] += 1
                self.log_error(f"✗ [{idx:3d}/100] Timeout: {scenario.name}")
                
            except Exception as e:
                result.status = "failed"
                result.error = str(e)
                result.end_time = time.time()
                self.stats['failed'] += 1
                self.log_error(f"✗ [{idx:3d}/100] Failed: {scenario.name} - {str(e)}")
            
            # Update statistics
            self.update_stats(result)
    
    async def poll_for_completion(self, result: TestResult, session: aiohttp.ClientSession):
        """Poll for task completion."""
        max_polls = self.timeout_seconds * 2  # Poll every 0.5s
        
        for _ in range(max_polls):
            try:
                async with session.get(
                    f"{self.api_url}/api/v1/task/{result.task_id}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        status = data.get('status')
                        
                        if status == 'completed':
                            result.status = "completed"
                            result.end_time = time.time()
                            result.final_result = data.get('result')
                            result.cache_hit = data.get('metadata', {}).get('cache_hit', False)
                            self.stats['completed'] += 1
                            
                            if result.cache_hit:
                                self.stats['cache_hits'] += 1
                            
                            self.log_success(f"✓ Completed: {result.scenario.name} ({result.duration_ms}ms)")
                            return
                        
                        elif status == 'failed':
                            result.status = "failed"
                            result.end_time = time.time()
                            result.error = data.get('error')
                            self.stats['failed'] += 1
                            return
                
            except Exception as e:
                pass
            
            await asyncio.sleep(0.5)
        
        # Timeout
        result.status = "timeout"
        result.end_time = time.time()
        self.stats['timeout'] += 1
    
    def update_stats(self, result: TestResult):
        """Update statistics."""
        if result.is_complete and result.end_time:
            duration = result.duration_ms
            
            self.stats['total_duration_ms'] += duration
            self.stats['min_duration_ms'] = min(self.stats['min_duration_ms'], duration)
            self.stats['max_duration_ms'] = max(self.stats['max_duration_ms'], duration)
            
            # By complexity
            complexity = result.scenario.complexity
            self.stats['by_complexity'][complexity]['total'] += 1
            
            if result.status == 'completed':
                self.stats['by_complexity'][complexity]['completed'] += 1
            else:
                self.stats['by_complexity'][complexity]['failed'] += 1
            
            # By user
            user = result.scenario.user_id
            if user not in self.stats['by_user']:
                self.stats['by_user'][user] = {'total': 0, 'completed': 0, 'failed': 0}
            
            self.stats['by_user'][user]['total'] += 1
            
            if result.status == 'completed':
                self.stats['by_user'][user]['completed'] += 1
            else:
                self.stats['by_user'][user]['failed'] += 1
    
    def print_header(self):
        """Print test header."""
        if RICH_AVAILABLE:
            self.console.print(Panel.fit(
                "[bold cyan]🚀 AI Service Load Test Suite[/bold cyan]\n"
                "[white]Testing 100 concurrent requests with various scenarios[/white]",
                box=box.DOUBLE,
                border_style="cyan"
            ))
        else:
            print("\n" + "=" * 70)
            print("🚀 AI SERVICE LOAD TEST SUITE")
            print("=" * 70)
            print("Testing 100 concurrent requests with various scenarios")
            print("=" * 70 + "\n")
    
    def print_report(self):
        """Print comprehensive test report."""
        total_duration = self.end_time - self.start_time
        
        if RICH_AVAILABLE:
            self.print_rich_report(total_duration)
        else:
            self.print_simple_report(total_duration)
    
        def print_rich_report(self, total_duration: float):
            """Print rich detailed report."""
            # Calculate statistics
            success_rate = (self.stats['completed'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
            avg_duration = (self.stats['total_duration_ms'] / self.stats['completed']) if self.stats['completed'] > 0 else 0
            cache_hit_rate = (self.stats['cache_hits'] / self.stats['completed'] * 100) if self.stats['completed'] > 0 else 0
        
            # Main layout
            layout = Layout()
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="summary", size=8),
                Layout(name="details", size=12),
                Layout(name="failures", size=10)
            )
            
            # Header
            layout["header"].update(
                Panel.fit(
                    f"[bold cyan]📊 LOAD TEST REPORT[/bold cyan] | "
                    f"[green]Total Duration: {total_duration:.1f}s[/green] | "
                    f"[white]{self.stats['total']} requests[/white]",
                    border_style="cyan",
                    box=box.DOUBLE
                )
            )
            
            # Summary panel
            summary_table = Table(title="📈 Overall Statistics", box=box.ROUNDED)
            summary_table.add_column("Metric", style="cyan", no_wrap=True)
            summary_table.add_column("Value", style="white")
            summary_table.add_column("Rate", style="yellow")
            
            summary_table.add_row("Total Requests", str(self.stats['total']), "100%")
            summary_table.add_row("Completed", str(self.stats['completed']), f"{success_rate:.1f}%")
            summary_table.add_row("Failed", str(self.stats['failed']), f"{self.stats['failed']/self.stats['total']*100:.1f}%")
            summary_table.add_row("Timeout", str(self.stats['timeout']), f"{self.stats['timeout']/self.stats['total']*100:.1f}%")
            summary_table.add_row("Cache Hits", str(self.stats['cache_hits']), f"{cache_hit_rate:.1f}%")
            summary_table.add_row("Min Duration", f"{self.stats['min_duration_ms']}ms", "-")
            summary_table.add_row("Avg Duration", f"{avg_duration:.0f}ms", "-")
            summary_table.add_row("Max Duration", f"{self.stats['max_duration_ms']}ms", "-")
            
            layout["summary"].update(summary_table)
            
            # Complexity breakdown
            complexity_table = Table(title="📊 Complexity Breakdown", box=box.ROUNDED)
            complexity_table.add_column("Complexity", style="cyan")
            complexity_table.add_column("Total", style="white")
            complexity_table.add_column("Completed", style="green")
            complexity_table.add_column("Failed", style="red")
            complexity_table.add_column("Success Rate", style="yellow")
            
            for complexity, stats in self.stats['by_complexity'].items():
                if stats['total'] > 0:
                    rate = (stats['completed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                    complexity_table.add_row(
                        complexity.value,
                        str(stats['total']),
                        str(stats['completed']),
                        str(stats['failed']),
                        f"{rate:.1f}%"
                    )
            
            # User breakdown
            user_table = Table(title="👥 User Breakdown", box=box.ROUNDED)
            user_table.add_column("User", style="cyan")
            user_table.add_column("Total", style="white")
            user_table.add_column("Completed", style="green")
            user_table.add_column("Failed", style="red")
            user_table.add_column("Success Rate", style="yellow")
            
            for user, stats in self.stats['by_user'].items():
                if stats['total'] > 0:
                    rate = (stats['completed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                    user_table.add_row(
                        user,
                        str(stats['total']),
                        str(stats['completed']),
                        str(stats['failed']),
                        f"{rate:.1f}%"
                    )
            
            # Combine details
            details_layout = Layout()
            details_layout.split_row(
                Layout(complexity_table, name="complexity"),
                Layout(user_table, name="users")
            )
            layout["details"].update(details_layout)
            
            # Failures section
            failed_tests = [r for r in self.results if r.status in ['failed', 'timeout']]
            if failed_tests:
                failure_table = Table(title="❌ Failed Tests", box=box.ROUNDED)
                failure_table.add_column("ID", style="white")
                failure_table.add_column("Name", style="cyan")
                failure_table.add_column("Status", style="red")
                failure_table.add_column("Error", style="yellow")
                failure_table.add_column("Duration", style="white")
                
                for idx, result in enumerate(failed_tests[:10], 1):  # Show first 10 failures
                    failure_table.add_row(
                        str(idx),
                        result.scenario.name[:30],
                        result.status,
                        result.error[:50] if result.error else "N/A",
                        f"{result.duration_ms}ms"
                    )
                
                if len(failed_tests) > 10:
                    failure_table.add_row(
                        "...",
                        f"{len(failed_tests) - 10} more failures",
                        "",
                        "",
                        ""
                    )
                
                layout["failures"].update(failure_table)
            else:
                layout["failures"].update(
                    Panel.fit(
                        "[bold green]🎉 All tests passed successfully![/bold green]",
                        border_style="green",
                        box=box.ROUNDED
                    )
                )
            
            # Print the complete layout
            self.console.print(layout)
            
            # Print recommendations
            self.console.print("\n" + "="*70)
            self.console.print("[bold]💡 Recommendations:[/bold]")
            
            if success_rate < 90:
                self.console.print("[yellow]⚠️  Success rate below 90% - consider:")
                self.console.print("  - Check Redis connection and memory usage")
                self.console.print("  - Monitor RabbitMQ queue size")
                self.console.print("  - Increase timeout settings for complex apps[/yellow]")
            
            if self.stats['timeout'] > 5:
                self.console.print("[yellow]⚠️  High timeout rate - consider:")
                self.console.print("  - Increase worker concurrency")
                self.console.print("  - Optimize AI model calls")
                self.console.print("  - Implement request timeouts[/yellow]")
            
            if cache_hit_rate < 20:
                self.console.print("[cyan]💡 Cache hit rate can be improved:")
                self.console.print("  - Increase Redis cache size")
                self.console.print("  - Adjust cache TTL settings")
                self.console.print("  - Improve prompt normalization[/cyan]")

    def print_simple_report(self, total_duration: float):
        """Print simple text-based report."""
        print("\n" + "="*70)
        print("📊 LOAD TEST REPORT")
        print("="*70)
        
        # Overall statistics
        success_rate = (self.stats['completed'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
        avg_duration = (self.stats['total_duration_ms'] / self.stats['completed']) if self.stats['completed'] > 0 else 0
        cache_hit_rate = (self.stats['cache_hits'] / self.stats['completed'] * 100) if self.stats['completed'] > 0 else 0
        
        print(f"\n📈 OVERALL STATISTICS")
        print(f"  Total Duration: {total_duration:.1f} seconds")
        print(f"  Total Requests: {self.stats['total']}")
        print(f"  Completed:      {self.stats['completed']} ({success_rate:.1f}%)")
        print(f"  Failed:         {self.stats['failed']} ({self.stats['failed']/self.stats['total']*100:.1f}%)")
        print(f"  Timeout:        {self.stats['timeout']} ({self.stats['timeout']/self.stats['total']*100:.1f}%)")
        print(f"  Cache Hits:     {self.stats['cache_hits']} ({cache_hit_rate:.1f}%)")
        print(f"  Min Duration:   {self.stats['min_duration_ms']}ms")
        print(f"  Avg Duration:   {avg_duration:.0f}ms")
        print(f"  Max Duration:   {self.stats['max_duration_ms']}ms")
        
        # Complexity breakdown
        print(f"\n📊 COMPLEXITY BREAKDOWN")
        complexity_data = []
        for complexity, stats in self.stats['by_complexity'].items():
            if stats['total'] > 0:
                rate = (stats['completed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                complexity_data.append([
                    complexity.value,
                    stats['total'],
                    stats['completed'],
                    stats['failed'],
                    f"{rate:.1f}%"
                ])
        
        if TABULATE_AVAILABLE and complexity_data:
            print(tabulate(complexity_data, 
                          headers=["Complexity", "Total", "Completed", "Failed", "Success Rate"],
                          tablefmt="grid"))
        else:
            for row in complexity_data:
                print(f"  {row[0]}: {row[1]} total, {row[2]} completed, {row[3]} failed ({row[4]})")
        
        # User breakdown
        print(f"\n👥 USER BREAKDOWN")
        user_data = []
        for user, stats in self.stats['by_user'].items():
            if stats['total'] > 0:
                rate = (stats['completed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                user_data.append([
                    user,
                    stats['total'],
                    stats['completed'],
                    stats['failed'],
                    f"{rate:.1f}%"
                ])
        
        if TABULATE_AVAILABLE and user_data:
            print(tabulate(user_data, 
                          headers=["User", "Total", "Completed", "Failed", "Success Rate"],
                          tablefmt="grid"))
        else:
            for row in user_data:
                print(f"  {row[0]}: {row[1]} total, {row[2]} completed, {row[3]} failed ({row[4]})")
        
        # Failures
        failed_tests = [r for r in self.results if r.status in ['failed', 'timeout']]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)})")
            failure_data = []
            for idx, result in enumerate(failed_tests[:10], 1):
                failure_data.append([
                    idx,
                    result.scenario.name[:30],
                    result.status,
                    result.error[:50] if result.error else "N/A",
                    f"{result.duration_ms}ms"
                ])
            
            if TABULATE_AVAILABLE and failure_data:
                print(tabulate(failure_data, 
                              headers=["#", "Name", "Status", "Error", "Duration"],
                              tablefmt="grid"))
            else:
                for row in failure_data:
                    print(f"  {row[0]}. {row[1]} [{row[2]}] - {row[3]} ({row[4]})")
            
            if len(failed_tests) > 10:
                print(f"  ... and {len(failed_tests) - 10} more failures")
        else:
            print(f"\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
        
        # Recommendations
        print("\n" + "="*70)
        print("💡 RECOMMENDATIONS:")
        
        if success_rate < 90:
            print("⚠️  Success rate below 90% - consider:")
            print("  - Check Redis connection and memory usage")
            print("  - Monitor RabbitMQ queue size")
            print("  - Increase timeout settings for complex apps")
        
        if self.stats['timeout'] > 5:
            print("⚠️  High timeout rate - consider:")
            print("  - Increase worker concurrency")
            print("  - Optimize AI model calls")
            print("  - Implement request timeouts")
        
        if cache_hit_rate < 20:
            print("💡 Cache hit rate can be improved:")
            print("  - Increase Redis cache size")
            print("  - Adjust cache TTL settings")
            print("  - Improve prompt normalization")
        
        print("="*70)
    
    def log_progress(self, message: str):
        """Log progress message."""
        if self.console:
            self.console.log(message)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def log_success(self, message: str):
        """Log success message."""
        if self.console:
            self.console.print(f"[green]✓ {message}[/green]")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ {message}")
    
    def log_error(self, message: str):
        """Log error message."""
        if self.console:
            self.console.print(f"[red]✗ {message}[/red]")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ {message}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Main entry point."""
    print("\n" + "="*70)
    print("🚀 AI SERVICE LOAD TEST SUITE")
    print("="*70)
    print("This test will simulate 100 concurrent app generation requests.")
    print("Make sure the AI service is running on http://localhost:8000")
    print("="*70)
    
    # Configuration
    api_url = input("\nEnter API URL (default: http://localhost:8000): ").strip()
    if not api_url:
        api_url = "http://localhost:8000"
    
    concurrent_limit = input("Enter concurrent limit (default: 20): ").strip()
    if concurrent_limit and concurrent_limit.isdigit():
        concurrent_limit = int(concurrent_limit)
    else:
        concurrent_limit = 20
    
    # Verify service is running
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{api_url}/health", timeout=5) as resp:
                if resp.status != 200:
                    print(f"❌ Service health check failed (Status: {resp.status})")
                    return
                print("✅ Service health check passed")
    except Exception as e:
        print(f"❌ Cannot connect to service at {api_url}: {e}")
        return
    
    # Run load test
    print(f"\n🚀 Starting load test with {len(TEST_SCENARIOS)} scenarios...")
    print(f"   API URL: {api_url}")
    print(f"   Concurrent limit: {concurrent_limit}")
    print("   Estimated time: 2-5 minutes\n")
    
    runner = LoadTestRunner(
        api_url=api_url,
        concurrent_limit=concurrent_limit,
        timeout_seconds=300
    )
    
    try:
        await runner.run()
        
        # Ask to save results
        save = input("\n💾 Save results to file? (y/n): ").strip().lower()
        if save == 'y':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"load_test_results_{timestamp}.json"
            
            results_data = {
                "timestamp": datetime.now().isoformat(),
                "config": {
                    "api_url": api_url,
                    "concurrent_limit": concurrent_limit,
                    "scenarios_count": len(TEST_SCENARIOS)
                },
                "statistics": runner.stats,
                "results": [
                    {
                        "scenario": {
                            "name": r.scenario.name,
                            "complexity": r.scenario.complexity.value,
                            "user_id": r.scenario.user_id,
                            "priority": r.scenario.priority
                        },
                        "status": r.status,
                        "duration_ms": r.duration_ms,
                        "cache_hit": r.cache_hit,
                        "error": r.error
                    }
                    for r in runner.results
                ]
            }
            
            import json
            with open(filename, 'w') as f:
                json.dump(results_data, f, indent=2, default=str)
            
            print(f"✅ Results saved to {filename}")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Load test interrupted by user")
    except Exception as e:
        print(f"\n❌ Load test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check requirements
    missing_modules = []
    try:
        import aiohttp
    except ImportError:
        missing_modules.append("aiohttp")
    
    try:
        import asyncio
    except ImportError:
        missing_modules.append("asyncio")
    
    if missing_modules:
        print("❌ Missing required modules:")
        for module in missing_modules:
            print(f"   - {module}")
        print("\nInstall with: pip install " + " ".join(missing_modules))
        sys.exit(1)
    
    # Run the main function
    asyncio.run(main())