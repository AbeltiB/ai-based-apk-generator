"""
Comprehensive test of the complete AI service flow.
"""
import pika
import json
import time
from datetime import datetime


def test_multiple_requests():
    """Send multiple test requests"""
    
    print("\n" + "=" * 60)
    print("COMPREHENSIVE FLOW TEST")
    print("=" * 60)
    
    # Connect to RabbitMQ
    credentials = pika.PlainCredentials('admin', 'password')
    parameters = pika.ConnectionParameters('localhost', 5672, '/', credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    
    # Ensure queues exist
    channel.queue_declare(queue='ai-requests', durable=True)
    channel.queue_declare(queue='ai-responses', durable=True)
    
    # Test prompts
    test_prompts = [
        "Create a todo list app",
        "Build a simple calculator",
        "Make a weather app",
    ]
    
    print(f"\n📤 Sending {len(test_prompts)} test requests...")
    
    task_ids = []
    
    for i, prompt in enumerate(test_prompts, 1):
        task_id = f"test-{int(time.time())}-{i}"
        task_ids.append(task_id)
        
        request = {
            "task_id": task_id,
            "user_id": f"test_user_{i}",
            "session_id": f"test_session_{i}",
            "socket_id": f"test_socket_{i}",
            "prompt": prompt,
            "context": None,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        channel.basic_publish(
            exchange='',
            routing_key='ai-requests',
            body=json.dumps(request),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        print(f"   {i}. {prompt} (Task: {task_id})")
        time.sleep(0.5)  # Small delay between messages
    
    connection.close()
    
    print(f"\n✅ {len(test_prompts)} requests sent successfully!")
    print("\n📊 Check the AI service logs for processing details")
    print("=" * 60 + "\n")
    
    return task_ids


def check_queue_status():
    """Check RabbitMQ queue status"""
    
    print("\n" + "=" * 60)
    print("QUEUE STATUS CHECK")
    print("=" * 60)
    
    credentials = pika.PlainCredentials('admin', 'password')
    parameters = pika.ConnectionParameters('localhost', 5672, '/', credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    
    # Check ai-requests queue
    requests_queue = channel.queue_declare(queue='ai-requests', durable=True, passive=True)
    print(f"\n📥 ai-requests queue:")
    print(f"   Messages: {requests_queue.method.message_count}")
    
    # Check ai-responses queue
    responses_queue = channel.queue_declare(queue='ai-responses', durable=True, passive=True)
    print(f"\n📤 ai-responses queue:")
    print(f"   Messages: {responses_queue.method.message_count}")
    
    connection.close()
    
    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    # Send multiple test requests
    task_ids = test_multiple_requests()
    
    # Wait a bit for processing
    print("⏳ Waiting 5 seconds for processing...")
    time.sleep(5)
    
    # Check queue status
    check_queue_status()
    
    print("✅ Test complete!")
    print("\nNext steps:")
    print("  1. Check AI service logs for processing details")
    print("  2. Verify all responses were sent")
    print("  3. Check RabbitMQ management UI: http://localhost:15672")