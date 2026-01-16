"""
Diagnostic script to check the entire message flow - UPDATED FOR LLaMA3.

Run this to see exactly what's happening at each step.
"""
import asyncio
import pika
import json
import time
from datetime import datetime, UTC
import os
import subprocess
import sys

def check_environment():
    """Check environment variables and dependencies."""
    print("\n" + "=" * 70)
    print("  ENVIRONMENT CHECK (LLaMA3 + Heuristic)")
    print("=" * 70)
    
    issues = []
    
    # Check .env file
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        print(f"✅ .env file found: {env_file}")
        
        # Read .env file
        with open(env_file, 'r') as f:
            content = f.read()
            
        # Check for critical variables (Updated for LLaMA3)
        critical_vars = [
            ("DATABASE_URL", "PostgreSQL connection"),
            ("REDIS_URL", "Redis connection"),
            ("RABBITMQ_URL", "RabbitMQ connection"),
        ]
        
        # Optional variables (nice to have)
        optional_vars = [
            ("LLAMA_API_KEY", "LLaMA API key (optional for enhanced features)"),
            ("OLLAMA_BASE_URL", "Ollama base URL (optional)"),
        ]
        
        print("\n📋 CRITICAL VARIABLES:")
        for var_name, description in critical_vars:
            if f"{var_name}=" in content:
                # Check if it's not empty or placeholder
                lines = content.split('\n')
                for line in lines:
                    if line.startswith(f"{var_name}="):
                        value = line.split('=', 1)[1].strip()
                        if value and not any(placeholder in value.lower() 
                                           for placeholder in ['your_', 'placeholder', 'example', 'change_me']):
                            print(f"  ✅ {var_name}: Set")
                        else:
                            print(f"  ❌ {var_name}: EMPTY or placeholder")
                            issues.append(f"{var_name} is empty or placeholder")
                        break
            else:
                print(f"  ❌ {var_name}: MISSING")
                issues.append(f"{var_name} is missing")
        
        print("\n📋 OPTIONAL VARIABLES:")
        for var_name, description in optional_vars:
            if f"{var_name}=" in content:
                lines = content.split('\n')
                for line in lines:
                    if line.startswith(f"{var_name}="):
                        value = line.split('=', 1)[1].strip()
                        if value and not any(placeholder in value.lower() 
                                           for placeholder in ['your_', 'placeholder', 'example', 'change_me']):
                            print(f"  ✅ {var_name}: Set")
                        else:
                            print(f"  ⚠️  {var_name}: Not set (optional)")
                        break
            else:
                print(f"  ⚠️  {var_name}: Not set (optional)")
    else:
        print(f"❌ .env file NOT found at: {env_file}")
        issues.append(f"No .env file found")
    
    # Check service status
    print("\n📋 SERVICE STATUS:")
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if 'postgres' in result.stdout.lower():
            print("  ✅ PostgreSQL: Running")
        else:
            print("  ❌ PostgreSQL: NOT running")
            issues.append("PostgreSQL not running")
            
        if 'redis' in result.stdout.lower():
            print("  ✅ Redis: Running")
        else:
            print("  ❌ Redis: NOT running")
            issues.append("Redis not running")
            
        if 'rabbitmq' in result.stdout.lower():
            print("  ✅ RabbitMQ: Running")
        else:
            print("  ❌ RabbitMQ: NOT running")
            issues.append("RabbitMQ not running")
    except:
        print("  ⚠️  Docker check failed - make sure Docker is running")
    
    return issues

def check_rabbitmq_queues():
    """Check RabbitMQ queue status"""
    print("\n" + "=" * 70)
    print("  RABBITMQ QUEUE STATUS")
    print("=" * 70)
    
    try:
        credentials = pika.PlainCredentials('admin', 'password')
        parameters = pika.ConnectionParameters('localhost', 5672, '/', credentials)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Check ai-requests queue
        requests = channel.queue_declare(queue='ai-requests', durable=True, passive=True)
        print(f"\n📥 ai-requests queue:")
        print(f"   Messages waiting: {requests.method.message_count}")
        print(f"   Consumers: {requests.method.consumer_count}")
        
        # Check ai-responses queue
        responses = channel.queue_declare(queue='ai-responses', durable=True, passive=True)
        print(f"\n📤 ai-responses queue:")
        print(f"   Messages waiting: {responses.method.message_count}")
        print(f"   Consumers: {responses.method.consumer_count}")
        
        connection.close()
        
        print("\n" + "=" * 70)
        print("  ANALYSIS")
        print("=" * 70)
        
        if requests.method.message_count > 0 and requests.method.consumer_count == 0:
            print("\n⚠️  ISSUE FOUND:")
            print("   - Messages in ai-requests queue")
            print("   - NO consumers attached")
            print("   - AI service is NOT consuming messages")
            return False
        
        elif requests.method.message_count > 0 and requests.method.consumer_count > 0:
            print("\n⚠️  ISSUE FOUND:")
            print("   - Messages in ai-requests queue")
            print("   - Consumer IS attached")
            print("   - Messages are NOT being processed")
            return False
        
        elif requests.method.consumer_count == 0:
            print("\n⚠️  WARNING:")
            print("   - NO consumer attached to ai-requests")
            print("   - AI service might not be running")
            return False
        
        else:
            print("\n✅ Everything looks good!")
            print("   - Consumer is attached")
            print("   - Queues are being processed")
            return True
            
    except Exception as e:
        print(f"\n❌ Error checking queues: {e}")
        print("\n💡 Make sure RabbitMQ is running:")
        print("   docker ps | grep rabbitmq")
        return False

def send_diagnostic_message():
    """Send a diagnostic message to test the flow"""
    print("\n" + "=" * 70)
    print("  SENDING DIAGNOSTIC MESSAGE")
    print("=" * 70)
    
    try:
        credentials = pika.PlainCredentials('admin', 'password')
        parameters = pika.ConnectionParameters('localhost', 5672, '/', credentials)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Ensure queue exists
        channel.queue_declare(queue='ai-requests', durable=True)
        
        task_id = f"diagnostic-{int(datetime.now(UTC).timestamp())}"
        
        request = {
            "task_id": task_id,
            "user_id": "diagnostic_user",
            "session_id": "diagnostic_session",
            "socket_id": "diagnostic_socket",
            "prompt": "Create a simple hello world button",
            "context": None,
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds") + "Z"
        }
        
        channel.basic_publish(
            exchange='',
            routing_key='ai-requests',
            body=json.dumps(request),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        print(f"\n✅ Diagnostic message sent!")
        print(f"   Task ID: {task_id}")
        print(f"   Prompt: {request['prompt']}")
        
        connection.close()
        
        print("\n⏳ Wait 10 seconds, then check queues again...")
        return task_id
        
    except Exception as e:
        print(f"\n❌ Error sending message: {e}")
        return None

def check_responses(timeout=5):
    """Check for responses in ai-responses queue"""
    print("\n" + "=" * 70)
    print(f"  CHECKING FOR RESPONSES ({timeout}s)")
    print("=" * 70)
    
    responses = []
    
    try:
        credentials = pika.PlainCredentials('admin', 'password')
        parameters = pika.ConnectionParameters('localhost', 5672, '/', credentials)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        channel.queue_declare(queue='ai-responses', durable=True)
        
        # Get all messages from the queue
        while True:
            method_frame, header_frame, body = channel.basic_get(queue='ai-responses')
            if method_frame:
                response = json.loads(body.decode())
                responses.append(response)
                
                print(f"\n📨 Response received:")
                print(f"   Type: {response.get('type')}")
                print(f"   Task: {response.get('task_id')}")
                
                if response.get('type') == 'progress':
                    print(f"   Stage: {response.get('stage')}")
                    print(f"   Progress: {response.get('progress')}%")
                elif response.get('type') == 'complete':
                    print(f"   Status: {response.get('status')}")
                    print(f"   ✅ COMPLETE!")
                elif response.get('type') == 'error':
                    print(f"   Error: {response.get('error')}")
                    print(f"   Stage failed: {response.get('stage', 'unknown')}")
                
                channel.basic_ack(method_frame.delivery_tag)
            else:
                break
        
        connection.close()
        
        print(f"\n✅ Found {len(responses)} response(s) in queue")
        
        if len(responses) == 0:
            print("\n⚠️  No responses found in queue!")
        
        return responses
        
    except Exception as e:
        print(f"\n❌ Error checking responses: {e}")
        return []

def analyze_failures(responses):
    """Analyze failure patterns in responses."""
    print("\n" + "=" * 70)
    print("  FAILURE ANALYSIS")
    print("=" * 70)
    
    # Count failures by stage
    failures_by_stage = {}
    for response in responses:
        if response.get('type') == 'error':
            error_msg = response.get('error', '')
            stage = 'unknown'
            
            # Extract stage from error message
            if 'architecture_generation' in error_msg:
                stage = 'architecture_generation'
            elif 'context_building' in error_msg:
                stage = 'context_building'
            elif 'intent_analysis' in error_msg:
                stage = 'intent_analysis'
            elif 'layout_generation' in error_msg:
                stage = 'layout_generation'
            elif 'blockly_generation' in error_msg:
                stage = 'blockly_generation'
            
            failures_by_stage[stage] = failures_by_stage.get(stage, 0) + 1
    
    if failures_by_stage:
        print("\n📊 FAILURE DISTRIBUTION:")
        for stage, count in failures_by_stage.items():
            print(f"   {stage}: {count} failures")
        
        print("\n🔧 TROUBLESHOOTING BY STAGE:")
        
        if 'architecture_generation' in failures_by_stage:
            print(f"\n   ❌ Architecture Generation Failures ({failures_by_stage['architecture_generation']}):")
            print("      1. Check if Llama3 is accessible")
            print("      2. Check architecture_validator.py for errors")
            print("      3. Check if heuristic fallback is working")
            print("      4. Look for import errors in architecture_generator.py")
        
        if 'context_building' in failures_by_stage:
            print(f"\n   ❌ Context Building Failures ({failures_by_stage['context_building']}):")
            print("      1. Check Redis connection")
            print("      2. Check if semantic cache is initialized")
            print("      3. Check context_builder.py for errors")
            print("      4. Verify database connections")
        
        if 'intent_analysis' in failures_by_stage:
            print(f"\n   ❌ Intent Analysis Failures:")
            print("      1. Check intent_orchestrator.py")
            print("      2. Verify heuristic analyzer is working")
            print("      3. Check for Claude API key issues (if configured)")
        
        if 'layout_generation' in failures_by_stage:
            print(f"\n   ❌ Layout Generation Failures:")
            print("      1. Check for CollisionError import issue")
            print("      2. Verify layout_generator.py imports")
            print("      3. Check Llama3 availability for layout generation")
        
        if 'blockly_generation' in failures_by_stage:
            print(f"\n   ❌ Blockly Generation Failures:")
            print("      1. Check blockly_generator.py")
            print("      2. Verify Blockly XML generation")
            print("      3. Check for template rendering issues")
    
    else:
        print("\n✅ No failures detected in responses")

def check_ai_service_direct():
    """Check AI service directly via HTTP."""
    print("\n" + "=" * 70)
    print("  DIRECT AI SERVICE CHECK")
    print("=" * 70)
    
    try:
        import requests
        
        # Test health endpoint
        print("\n🔍 Testing HTTP endpoint...")
        try:
            resp = requests.get("http://localhost:8000/health", timeout=5)
            print(f"   Health endpoint: HTTP {resp.status}")
            if resp.status == 200:
                print(f"   ✅ Service is running")
                data = resp.json()
                print(f"   Status: {data.get('status', 'unknown')}")
                print(f"   Version: {data.get('version', 'unknown')}")
            else:
                print(f"   ❌ Service returned error")
        except requests.exceptions.ConnectionError:
            print("   ❌ Cannot connect to service")
            print("\n💡 Start AI service with:")
            print("   poetry run uvicorn app.main:app --reload")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
    except ImportError:
        print("\n⚠️  Install requests module to test HTTP:")
        print("   pip install requests")

def main():
    """Run complete diagnostic"""
    print("\n" + "=" * 70)
    print("  AI SERVICE DIAGNOSTIC TOOL (LLaMA3 + Heuristic)")
    print("=" * 70)
    
    # Step 1: Check environment
    print("\n[STEP 1] Checking environment...")
    issues = check_environment()
    
    if issues:
        print(f"\n⚠️  Found {len(issues)} issue(s):")
        for issue in issues:
            print(f"   • {issue}")
    
    # Step 2: Check service directly
    check_ai_service_direct()
    
    # Step 3: Check current queue status
    print("\n[STEP 2] Checking RabbitMQ queues...")
    healthy = check_rabbitmq_queues()
    
    # Step 4: Send diagnostic message
    print("\n[STEP 3] Sending diagnostic message...")
    task_id = send_diagnostic_message()
    
    if not task_id:
        print("\n❌ Cannot proceed - failed to send message")
        return 1
    
    # Step 5: Wait and check for responses
    print(f"\n⏳ Waiting 10 seconds for processing...")
    time.sleep(10)
    
    print("\n[STEP 4] Checking for responses...")
    responses = check_responses(timeout=2)
    
    # Step 6: Analyze failures
    analyze_failures(responses)
    
    # Step 7: Re-check queues
    print("\n[STEP 5] Final queue check...")
    check_rabbitmq_queues()
    
    # Summary
    print("\n" + "=" * 70)
    print("  DIAGNOSTIC SUMMARY")
    print("=" * 70)
    
    successful = any(r.get('type') == 'complete' for r in responses)
    errors = [r for r in responses if r.get('type') == 'error']
    
    if successful:
        print("\n✅ SUCCESS! At least one task completed.")
        print("   System is processing messages correctly.")
    elif errors:
        print(f"\n⚠️  PARTIAL FAILURE: {len(errors)} error(s)")
        print("   Messages are being processed but failing at specific stages.")
        
        # Most common failure stage
        stage_counts = {}
        for error in errors:
            error_msg = error.get('error', '')
            if 'architecture_generation' in error_msg:
                stage_counts['architecture_generation'] = stage_counts.get('architecture_generation', 0) + 1
            elif 'context_building' in error_msg:
                stage_counts['context_building'] = stage_counts.get('context_building', 0) + 1
        
        if stage_counts:
            most_common = max(stage_counts.items(), key=lambda x: x[1])
            print(f"   Most common failure: {most_common[0]} ({most_common[1]} times)")
        
        print("\n🔧 IMMEDIATE ACTIONS:")
        print("   1. Check AI service logs for Python exceptions")
        print("   2. Verify Llama3/heuristic fallback is working")
        print("   3. Check import statements in failing modules")
    else:
        print("\n❌ COMPLETE FAILURE: No responses received")
        print("   Messages are not being processed at all.")
        print("\n🔧 IMMEDIATE ACTIONS:")
        print("   1. Check if AI service consumer is running")
        print("   2. Look for startup errors in AI service logs")
        print("   3. Verify all dependencies are installed")
    
    print("\n" + "=" * 70 + "\n")
    
    return 0 if successful else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())