"""
Diagnostic script to check the entire message flow.

Run this to see exactly what's happening at each step.
"""
import asyncio
import pika
import json
from datetime import datetime


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
        
        # Analysis
        print("\n" + "=" * 70)
        print("  ANALYSIS")
        print("=" * 70)
        
        if requests.method.message_count > 0 and requests.method.consumer_count == 0:
            print("\n⚠️  ISSUE FOUND:")
            print("   - Messages in ai-requests queue")
            print("   - NO consumers attached")
            print("   - AI service is NOT consuming messages")
            print("\n💡 Solution:")
            print("   1. Check if AI service is running: ps aux | grep uvicorn")
            print("   2. Check AI service logs for errors")
            print("   3. Restart AI service: poetry run uvicorn app.main:app --reload")
            return False
        
        elif requests.method.message_count > 0 and requests.method.consumer_count > 0:
            print("\n⚠️  ISSUE FOUND:")
            print("   - Messages in ai-requests queue")
            print("   - Consumer IS attached")
            print("   - Messages are NOT being processed")
            print("\n💡 Solution:")
            print("   1. Check AI service logs for errors")
            print("   2. Check if ANTHROPIC_API_KEY is set correctly")
            print("   3. Look for exception in message_handler")
            return False
        
        elif requests.method.consumer_count == 0:
            print("\n⚠️  WARNING:")
            print("   - NO consumer attached to ai-requests")
            print("   - AI service might not be running")
            print("\n💡 Start AI service:")
            print("   cd ai-service")
            print("   poetry run uvicorn app.main:app --reload")
            return False
        
        else:
            print("\n✅ Everything looks good!")
            print("   - Consumer is attached")
            print("   - Queues are being processed")
            return True
            
    except Exception as e:
        print(f"\n❌ Error checking queues: {e}")
        print("\n💡 Make sure RabbitMQ is running:")
        print("   cd infra && docker-compose ps")
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
        
        task_id = f"diagnostic-{int(datetime.utcnow().timestamp())}"
        
        request = {
            "task_id": task_id,
            "user_id": "diagnostic_user",
            "session_id": "diagnostic_session",
            "socket_id": "diagnostic_socket",
            "prompt": "Create a simple hello world button",
            "context": None,
            "timestamp": datetime.utcnow().isoformat() + "Z"
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


def check_responses(timeout=10):
    """Check for responses in ai-responses queue"""
    print("\n" + "=" * 70)
    print(f"  CHECKING FOR RESPONSES ({timeout}s)")
    print("=" * 70)
    
    try:
        credentials = pika.PlainCredentials('admin', 'password')
        parameters = pika.ConnectionParameters('localhost', 5672, '/', credentials)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        channel.queue_declare(queue='ai-responses', durable=True)
        
        responses = []
        start_time = datetime.utcnow().timestamp()
        
        def callback(ch, method, properties, body):
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
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
        
        channel.basic_consume(queue='ai-responses', on_message_callback=callback)
        
        print("\n👂 Listening for responses...")
        
        # Listen for timeout duration
        connection.call_later(timeout, lambda: connection.close())
        
        try:
            channel.start_consuming()
        except:
            pass
        
        print(f"\n✅ Received {len(responses)} response(s)")
        
        if len(responses) == 0:
            print("\n⚠️  No responses received!")
            print("   This means the AI service is NOT processing messages")
        
        return responses
        
    except Exception as e:
        print(f"\n❌ Error checking responses: {e}")
        return []


async def check_ai_service_logs():
    """Instructions for checking AI service logs"""
    print("\n" + "=" * 70)
    print("  AI SERVICE LOGS CHECK")
    print("=" * 70)
    
    print("\n📋 To check if AI service is processing:")
    print("\n1. In the AI service terminal, you should see:")
    print("   - '🚀 Starting pipeline for task: ...'")
    print("   - '▶️  Stage X/Y: ...'")
    print("   - '✅ Stage ... completed in ...ms'")
    
    print("\n2. If you DON'T see these logs:")
    print("   - The consumer isn't running")
    print("   - Or there's an error in the consumer")
    
    print("\n3. Common issues to check:")
    print("   - ANTHROPIC_API_KEY not set in .env")
    print("   - Python errors in consumer code")
    print("   - Database connection issues")


def main():
    """Run complete diagnostic"""
    print("\n" + "=" * 70)
    print("  AI SERVICE DIAGNOSTIC TOOL")
    print("=" * 70)
    
    # Step 1: Check current queue status
    print("\n[STEP 1] Checking current queue status...")
    healthy = check_rabbitmq_queues()
    
    # Step 2: Send diagnostic message
    print("\n[STEP 2] Sending diagnostic message...")
    task_id = send_diagnostic_message()
    
    if not task_id:
        print("\n❌ Cannot proceed - failed to send message")
        return 1
    
    # Step 3: Wait and check for responses
    import time
    time.sleep(10)
    
    print("\n[STEP 3] Checking for responses...")
    responses = check_responses(timeout=5)
    
    # Step 4: Re-check queues
    print("\n[STEP 4] Re-checking queue status...")
    check_rabbitmq_queues()
    
    # Step 5: Log instructions
    asyncio.run(check_ai_service_logs())
    
    # Summary
    print("\n" + "=" * 70)
    print("  DIAGNOSTIC SUMMARY")
    print("=" * 70)
    
    if len(responses) > 0:
        print("\n✅ SYSTEM IS WORKING!")
        print("   Messages are being processed correctly")
    else:
        print("\n❌ SYSTEM IS NOT WORKING")
        print("   Messages are not being processed")
        print("\n🔧 TROUBLESHOOTING STEPS:")
        print("   1. Check if AI service is running")
        print("   2. Check AI service logs for errors")
        print("   3. Verify ANTHROPIC_API_KEY in .env")
        print("   4. Check database connections")
        print("   5. Restart AI service")
    
    print("\n" + "=" * 70 + "\n")
    
    return 0 if len(responses) > 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())