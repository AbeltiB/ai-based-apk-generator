"""
complete_test.py - Full system test with comprehensive debugging
Run: poetry run python complete_test.py
"""
import asyncio
import aio_pika
import json
import time
import traceback
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class TestResult:
    """Container for test results with detailed analysis."""
    name: str
    passed: bool = False
    error: Optional[str] = None
    details: Dict = field(default_factory=dict)
    start_time: float = 0.0
    end_time: float = 0.0
    messages_received: List[Dict] = field(default_factory=list)
    progress_stages: List[str] = field(default_factory=list)
    errors_encountered: List[str] = field(default_factory=list)
    completion_data: Optional[Dict] = None
    latency_ms: float = 0.0
    
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    def success_rate(self) -> float:
        if not self.messages_received:
            return 0.0
        success_msgs = sum(1 for msg in self.messages_received 
                          if msg.get('type') not in ['error', 'failed'])
        return (success_msgs / len(self.messages_received)) * 100
    
    def has_architecture(self) -> bool:
        if self.completion_data and self.completion_data.get('result'):
            arch = self.completion_data['result'].get('architecture')
            return arch is not None and arch != {}
        return False
    
    def has_layout(self) -> bool:
        if self.completion_data and self.completion_data.get('result'):
            layout = self.completion_data['result'].get('layout')
            return layout is not None and layout != {}
        return False
    
    def has_blockly(self) -> bool:
        if self.completion_data and self.completion_data.get('result'):
            blockly = self.completion_data['result'].get('blockly')
            return blockly is not None and blockly != {}
        return False


class ComprehensiveSystemTester:
    """Complete system integration test with detailed validation."""
    
    def __init__(self, host: str = "localhost", port: int = 5672):
        self.rabbitmq_url = f"amqp://admin:password@{host}:{port}/"
        self.connection = None
        self.channel = None
        self.consumer_tag = None
        self.test_results: Dict[str, TestResult] = {}
        
    async def connect(self) -> bool:
        """Connect to RabbitMQ with retry logic."""
        print("🔌 Connecting to RabbitMQ...")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.connection = await aio_pika.connect_robust(
                    self.rabbitmq_url,
                    timeout=10
                )
                self.channel = await self.connection.channel()
                
                # Configure channel
                await self.channel.set_qos(prefetch_count=1)
                
                print("✅ Connected to RabbitMQ")
                return True
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⚠️  Connection failed (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"   Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"❌ Failed to connect after {max_retries} attempts: {e}")
                    return False
        return False
    
    async def validate_queue_exists(self, queue_name: str) -> bool:
        """Check if a queue exists and is accessible."""
        try:
            await self.channel.declare_queue(
                queue_name, 
                durable=True,
                passive=True  # Just check, don't create
            )
            print(f"✅ Queue '{queue_name}' exists")
            return True
        except aio_pika.exceptions.ChannelClosed as e:
            print(f"❌ Queue '{queue_name}' does not exist or is not accessible: {e}")
            return False
    
    async def send_test_request(self, test_name: str, prompt: str) -> Tuple[bool, str]:
        """Send a test AI generation request with validation."""
        
        # Start timing
        start_time = time.time()
        
        # Create test result tracker
        test_result = TestResult(name=test_name, start_time=start_time)
        self.test_results[test_name] = test_result
        
        # Validate queue
        if not await self.validate_queue_exists('ai-requests'):
            error = f"Queue 'ai-requests' not found"
            test_result.error = error
            test_result.end_time = time.time()
            return False, ""
        
        # Prepare request data
        now = datetime.now(timezone.utc)
        timestamp_str = now.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        
        request = {
            "task_id": f"test_{int(time.time())}_{hash(prompt) % 10000:04d}",
            "user_id": "test_user",
            "session_id": "test_session",
            "socket_id": f"test_socket_{test_name.lower().replace(' ', '_')}",
            "prompt": prompt,
            "context": {
                "test_mode": True,
                "complexity": "simple",
                "platform": "android"
            },
            "timestamp": timestamp_str,
            "test_name": test_name
        }
        
        print(f"\n📤 Sending {test_name} request:")
        print(f"   Task ID: {request['task_id']}")
        print(f"   Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
        print(f"   Timestamp: {timestamp_str}")
        print(f"   Context keys: {list(request['context'].keys())}")
        
        try:
            # Declare queue explicitly
            queue = await self.channel.declare_queue('ai-requests', durable=True)
            
            # Create message with headers for tracking
            message = aio_pika.Message(
                body=json.dumps(request).encode('utf-8'),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                headers={
                    'test_name': test_name,
                    'sent_timestamp': timestamp_str,
                    'source': 'system_test'
                }
            )
            
            # Publish with confirmation
            await self.channel.default_exchange.publish(
                message,
                routing_key='ai-requests',
                mandatory=True
            )
            
            print("✅ Request sent to ai-requests queue")
            print(f"   Message size: {len(message.body)} bytes")
            
            test_result.details['task_id'] = request['task_id']
            test_result.details['message_size'] = len(message.body)
            
            return True, request['task_id']
            
        except Exception as e:
            error_msg = f"Failed to send request: {str(e)}"
            print(f"❌ {error_msg}")
            traceback.print_exc()
            
            test_result.error = error_msg
            test_result.end_time = time.time()
            return False, ""
    
    async def listen_for_responses(self, test_name: str, task_id: str, 
                                 timeout: int = 120) -> TestResult:
        """Listen for responses with comprehensive validation."""
        
        test_result = self.test_results[test_name]
        
        print(f"\n👂 Listening for {test_name} responses (timeout: {timeout}s)...")
        
        # Validate response queue
        if not await self.validate_queue_exists('ai-responses'):
            test_result.error = "Response queue not found"
            test_result.end_time = time.time()
            return test_result
        
        # Set up message tracking
        messages_by_type = {}
        progress_updates = []
        last_progress = 0
        stage_sequence = []
        
        # Create callback for messages
        async def on_message(message: aio_pika.IncomingMessage):
            nonlocal last_progress
            
            try:
                async with message.process():
                    # Parse message
                    raw_body = message.body.decode('utf-8')
                    data = json.loads(raw_body)
                    
                    # Track all messages
                    test_result.messages_received.append(data)
                    
                    msg_type = data.get('type', 'unknown')
                    current_task_id = data.get('task_id', 'unknown')
                    
                    # Only process messages for our task
                    if current_task_id != task_id:
                        return
                    
                    # Categorize by type
                    if msg_type not in messages_by_type:
                        messages_by_type[msg_type] = []
                    messages_by_type[msg_type].append(data)
                    
                    # Handle different message types
                    if msg_type == 'progress':
                        stage = data.get('stage', 'unknown')
                        progress = data.get('progress', 0)
                        msg_text = data.get('message', '')
                        
                        # Track progress changes
                        if stage not in stage_sequence:
                            stage_sequence.append(stage)
                        
                        # Track detailed progress
                        progress_update = {
                            'stage': stage,
                            'progress': progress,
                            'message': msg_text,
                            'timestamp': datetime.now().isoformat()
                        }
                        progress_updates.append(progress_update)
                        
                        # Print progress with visual indicator
                        progress_bar = '█' * (progress // 5) + '░' * (20 - progress // 5)
                        print(f"   📊 [{progress_bar}] {stage} - {progress}%")
                        if msg_text and msg_text != "Starting AI processing...":
                            print(f"      ➤ {msg_text}")
                        
                        # Check for stuck progress
                        if progress <= last_progress and stage == stage_sequence[-1] if stage_sequence else False:
                            print(f"   ⚠️  Progress stalled at {progress}%")
                        
                        last_progress = progress
                        
                    elif msg_type == 'complete':
                        print(f"\n   ✅ COMPLETE MESSAGE RECEIVED")
                        test_result.completion_data = data
                        
                        result = data.get('result', {})
                        if result:
                            print(f"      ✓ Has architecture: {'Yes' if result.get('architecture') else 'No'}")
                            print(f"      ✓ Has layout: {'Yes' if result.get('layout') else 'No'}")
                            print(f"      ✓ Has blockly: {'Yes' if result.get('blockly') else 'No'}")
                            
                            # Validate structure
                            self._validate_completion_result(result)
                        
                        test_result.passed = True
                        
                    elif msg_type == 'error':
                        error = data.get('error', 'Unknown error')
                        details = data.get('details', '')
                        stage = data.get('stage', 'unknown')
                        
                        print(f"\n   ❌ ERROR at stage '{stage}':")
                        print(f"      Error: {error}")
                        if details:
                            print(f"      Details: {details}")
                        
                        test_result.errors_encountered.append({
                            'stage': stage,
                            'error': error,
                            'details': details,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        # Log the full error for debugging
                        test_result.details['error_data'] = data
                        
                    elif msg_type == 'failed':
                        error = data.get('error', 'Pipeline failed')
                        stage = data.get('stage', 'unknown')
                        
                        print(f"\n   ⚠️  PIPELINE FAILED at stage '{stage}':")
                        print(f"      Reason: {error}")
                        
                        test_result.errors_encountered.append({
                            'stage': stage,
                            'error': 'Pipeline failed',
                            'details': error,
                            'timestamp': datetime.now().isoformat()
                        })
                    
                    # Log message statistics
                    test_result.details['messages_by_type'] = messages_by_type
                    test_result.details['stage_sequence'] = stage_sequence
                    
            except json.JSONDecodeError as e:
                print(f"   ❗ Failed to parse message: {e}")
                print(f"   Raw message: {raw_body[:200] if 'raw_body' in locals() else 'N/A'}")
            except Exception as e:
                print(f"   ❗ Error processing message: {e}")
                traceback.print_exc()
        
        try:
            # Start consuming
            queue = await self.channel.declare_queue('ai-responses', durable=True)
            self.consumer_tag = await queue.consume(on_message)
            
            # Wait for completion with detailed timeout tracking
            start_time = time.time()
            check_interval = 2  # seconds
            
            while time.time() - start_time < timeout:
                elapsed = time.time() - start_time
                
                # Periodic status updates
                if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                    print(f"   ⏱️  Elapsed: {int(elapsed)}s, Messages: {len(test_result.messages_received)}")
                
                # Check if we have a final state
                if test_result.completion_data is not None or test_result.errors_encountered:
                    break
                
                await asyncio.sleep(check_interval)
            
            # Stop consuming
            if self.consumer_tag:
                await queue.cancel(self.consumer_tag)
            
            # Handle timeout
            if time.time() - start_time >= timeout:
                print(f"\n⏰ TIMEOUT after {timeout}s")
                print(f"   Messages received: {len(test_result.messages_received)}")
                test_result.error = f"Timeout after {timeout}s"
            
            # Calculate final metrics
            test_result.end_time = time.time()
            test_result.latency_ms = (test_result.end_time - test_result.start_time) * 1000
            test_result.progress_stages = stage_sequence
            
        except Exception as e:
            print(f"\n❌ Error in listener: {e}")
            traceback.print_exc()
            test_result.error = f"Listener error: {str(e)}"
            test_result.end_time = time.time()
        
        return test_result
    
    def _validate_completion_result(self, result: Dict):
        """Validate the structure of completion result."""
        print("\n   🔍 Validating result structure...")
        
        # Check required fields
        required_fields = ['architecture', 'layout', 'blockly']
        for field in required_fields:
            if field in result:
                if result[field]:
                    print(f"      ✓ {field}: Valid (non-empty)")
                else:
                    print(f"      ⚠️  {field}: Empty")
            else:
                print(f"      ❌ {field}: Missing")
        
        # Validate architecture structure
        if 'architecture' in result and result['architecture']:
            arch = result['architecture']
            if isinstance(arch, dict):
                print(f"      ✓ Architecture is a dict with {len(arch)} key(s)")
                if 'components' in arch:
                    print(f"      ✓ Architecture has components defined")
        
        # Validate layout structure
        if 'layout' in result and result['layout']:
            layout = result['layout']
            if isinstance(layout, dict):
                print(f"      ✓ Layout is a dict with {len(layout)} key(s)")
    
    async def run_single_test(self, test_name: str, prompt: str, 
                            timeout: int = 120) -> TestResult:
        """Run a single test end-to-end."""
        print(f"\n{'='*80}")
        print(f"  TEST: {test_name}")
        print(f"{'='*80}")
        
        # Step 1: Send request
        success, task_id = await self.send_test_request(test_name, prompt)
        if not success:
            return self.test_results[test_name]
        
        # Step 2: Listen for responses
        test_result = await self.listen_for_responses(test_name, task_id, timeout)
        
        return test_result
    
    def print_test_summary(self):
        """Print detailed test summary."""
        print(f"\n{'='*80}")
        print("  TEST SUMMARY REPORT")
        print(f"{'='*80}")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results.values() if r.passed)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result.passed else "❌ FAIL"
            duration = f"{result.duration():.2f}s"
            latency = f"{result.latency_ms:.0f}ms"
            messages = len(result.messages_received)
            
            print(f"\n{test_name}:")
            print(f"  Status: {status}")
            print(f"  Duration: {duration} (Latency: {latency})")
            print(f"  Messages: {messages}")
            print(f"  Success Rate: {result.success_rate():.1f}%")
            
            if result.errors_encountered:
                print(f"  Errors: {len(result.errors_encountered)}")
                for i, error in enumerate(result.errors_encountered, 1):
                    print(f"    {i}. Stage: {error['stage']}")
                    print(f"       Error: {error['error']}")
                    if error['details']:
                        print(f"       Details: {error['details'][:100]}...")
            
            if result.completion_data:
                print(f"  Completion: Yes")
                print(f"    Has Architecture: {result.has_architecture()}")
                print(f"    Has Layout: {result.has_layout()}")
                print(f"    Has Blockly: {result.has_blockly()}")
            
            if result.progress_stages:
                print(f"  Stages: {' → '.join(result.progress_stages)}")
        
        # Overall statistics
        print(f"\n{'='*80}")
        print("  OVERALL STATISTICS")
        print(f"{'='*80}")
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if total_tests > 0:
            avg_duration = sum(r.duration() for r in self.test_results.values()) / total_tests
            avg_messages = sum(len(r.messages_received) for r in self.test_results.values()) / total_tests
            print(f"Average Duration: {avg_duration:.2f}s")
            print(f"Average Messages: {avg_messages:.1f}")
        
        # Recommendations
        print(f"\n{'='*80}")
        print("  RECOMMENDATIONS")
        print(f"{'='*80}")
        
        for test_name, result in self.test_results.items():
            if not result.passed:
                print(f"\nFor '{test_name}':")
                if "context_building" in str(result.errors_encountered):
                    print("  ⚠️  Check context_building stage for None values")
                    print("  🔧 Fix: Add null checks in context building logic")
                if "timeout" in str(result.error or ""):
                    print("  ⚠️  Pipeline timeout - increase timeout or check for hangs")
                if not result.messages_received:
                    print("  ⚠️  No messages received - check RabbitMQ connection")
        
        if passed_tests == total_tests:
            print(f"\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} TEST(S) NEED ATTENTION")
        
        print(f"\n{'='*80}")
    
    async def run_health_check(self) -> bool:
        """Run basic RabbitMQ health check."""
        print("\n🏥 Running RabbitMQ Health Check...")
        
        try:
            # Check connection
            if not self.connection or self.connection.is_closed:
                print("❌ Connection is closed or not established")
                return False
            
            # Check channel
            if not self.channel or self.channel.is_closed:
                print("❌ Channel is closed")
                return False
            
            # Check queue accessibility
            queues_to_check = ['ai-requests', 'ai-responses']
            for queue in queues_to_check:
                try:
                    await self.channel.declare_queue(queue, passive=True)
                    print(f"✅ Queue '{queue}' is accessible")
                except:
                    print(f"❌ Queue '{queue}' is not accessible")
                    return False
            
            print("✅ Health check passed")
            return True
            
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
    
    async def close(self):
        """Close connections gracefully."""
        print("\n🔌 Cleaning up...")
        
        # Cancel consumer if active
        if self.consumer_tag and self.channel:
            try:
                await self.channel.cancel(self.consumer_tag)
            except:
                pass
        
        # Close connections
        if self.connection:
            try:
                await self.connection.close()
                print("✅ Disconnected from RabbitMQ")
            except Exception as e:
                print(f"⚠️  Error closing connection: {e}")


async def main():
    """Run comprehensive system test."""
    
    print("=" * 80)
    print("  COMPREHENSIVE SYSTEM TEST WITH DETAILED VALIDATION")
    print("=" * 80)
    
    tester = ComprehensiveSystemTester()
    
    try:
        # Step 1: Connect with health check
        if not await tester.connect():
            print("❌ Failed to connect to RabbitMQ. Exiting.")
            return
        
        # Step 2: Run health check
        if not await tester.run_health_check():
            print("❌ Health check failed. Exiting.")
            return
        
        # Step 3: Define test cases
        test_cases = [
            {
                "name": "Simple Counter App",
                "prompt": "Create a counter app with + and - buttons that displays the current count",
                "timeout": 90
            },
            {
                "name": "Todo List App", 
                "prompt": "Create a todo list with add, delete, and complete features including persistence",
                "timeout": 120
            },
            {
                "name": "Basic Calculator",
                "prompt": "Create a simple calculator with addition, subtraction, multiplication, division",
                "timeout": 90
            }
        ]
        
        # Step 4: Run all tests
        for test_case in test_cases:
            await tester.run_single_test(
                test_case["name"],
                test_case["prompt"],
                test_case["timeout"]
            )
        
        # Step 5: Print comprehensive summary
        tester.print_test_summary()
        
        # Step 6: Save detailed report
        await save_detailed_report(tester)
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        traceback.print_exc()
    finally:
        await tester.close()


async def save_detailed_report(tester: ComprehensiveSystemTester):
    """Save detailed test report to file."""
    import os
    from datetime import datetime
    
    # Create reports directory
    os.makedirs('test_reports', exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'test_reports/system_test_{timestamp}.json'
    
    # Prepare report data
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_tests': len(tester.test_results),
        'passed_tests': sum(1 for r in tester.test_results.values() if r.passed),
        'test_results': {}
    }
    
    for test_name, result in tester.test_results.items():
        report['test_results'][test_name] = {
            'passed': result.passed,
            'duration': result.duration(),
            'latency_ms': result.latency_ms,
            'messages_received': len(result.messages_received),
            'errors_encountered': len(result.errors_encountered),
            'progress_stages': result.progress_stages,
            'error': result.error,
            'has_architecture': result.has_architecture(),
            'has_layout': result.has_layout(),
            'has_blockly': result.has_blockly()
        }
    
    # Save to file
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📊 Detailed report saved to: {filename}")
    
    # Also create a simple summary file
    summary_file = f'test_reports/summary_{timestamp}.txt'
    with open(summary_file, 'w') as f:
        f.write(f"System Test Summary - {timestamp}\n")
        f.write("=" * 50 + "\n\n")
        
        for test_name, result in tester.test_results.items():
            status = "PASS" if result.passed else "FAIL"
            f.write(f"{test_name}: {status}\n")
            f.write(f"  Duration: {result.duration():.2f}s\n")
            f.write(f"  Messages: {len(result.messages_received)}\n")
            if result.errors_encountered:
                f.write(f"  Errors: {len(result.errors_encountered)}\n")
            f.write("\n")
    
    print(f"📝 Summary saved to: {summary_file}")


if __name__ == "__main__":
    # Set event loop policy for Windows if needed
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()