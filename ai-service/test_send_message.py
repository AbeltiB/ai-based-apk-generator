"""
Test script to send messages to RabbitMQ ai-requests queue.

This simulates the API Gateway sending prompts to our AI service.
"""
import pika
import json
import time
from datetime import datetime, timezone

def send_test_message(prompt: str):
    """
    Send a test AI request to RabbitMQ.
    
    Args:
        prompt: User prompt to send
    """
    print("\n" + "=" * 60)
    print("SENDING TEST MESSAGE TO AI SERVICE")
    print("=" * 60)
    
    # Connect to RabbitMQ
    credentials = pika.PlainCredentials('admin', 'password')
    parameters = pika.ConnectionParameters(
        host='localhost',
        port=5672,
        virtual_host='/',
        credentials=credentials
    )
    
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    
    # Ensure queue exists
    channel.queue_declare(queue='ai-requests', durable=True)
    
    # Create test request
    test_request = {
        "task_id": f"test-{int(time.time())}",
        "user_id": "test_user_123",
        "session_id": "test_session_abc",
        "socket_id": "test_socket_xyz",
        "prompt": prompt,
        "context": None,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
    }
    
    # Publish message
    channel.basic_publish(
        exchange='',
        routing_key='ai-requests',
        body=json.dumps(test_request),
        properties=pika.BasicProperties(
            delivery_mode=2,  # Make message persistent
            content_type='application/json'
        )
    )
    
    print(f"\n✅ Message sent!")
    print(f"   Task ID: {test_request['task_id']}")
    print(f"   Prompt: {prompt}")
    print(f"   Queue: ai-requests")
    
    connection.close()
    
    print("\n" + "=" * 60)
    print("Check the AI service logs to see it being processed!")
    print("=" * 60 + "\n")


def listen_for_responses(duration: int = 10):
    """
    Listen for responses from AI service.
    
    Args:
        duration: How long to listen in seconds
    """
    print("\n" + "=" * 60)
    print(f"LISTENING FOR RESPONSES ({duration} seconds)...")
    print("=" * 60)
    
    # Connect to RabbitMQ
    credentials = pika.PlainCredentials('admin', 'password')
    parameters = pika.ConnectionParameters(
        host='localhost',
        port=5672,
        virtual_host='/',
        credentials=credentials
    )
    
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    
    # Ensure queue exists
    channel.queue_declare(queue='ai-responses', durable=True)
    
    received_count = 0
    
    def callback(ch, method, properties, body):
        nonlocal received_count
        received_count += 1
        
        response = json.loads(body.decode())
        print(f"\n📨 Response {received_count} received:")
        print(f"   Type: {response.get('type', 'unknown')}")
        print(f"   Task ID: {response.get('task_id', 'unknown')}")
        
        if response.get('type') == 'progress':
            print(f"   Stage: {response.get('stage')}")
            print(f"   Progress: {response.get('progress')}%")
            print(f"   Message: {response.get('message')}")
        elif response.get('type') == 'response':
            print(f"   Message: {response.get('message')}")
        elif response.get('type') == 'error':
            print(f"   Error: {response.get('error')}")
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
    
    # Start consuming
    channel.basic_consume(
        queue='ai-responses',
        on_message_callback=callback
    )
    
    print("\n👂 Listening for messages...")
    
    # Listen for specified duration
    connection.call_later(duration, lambda: connection.close())
    
    try:
        channel.start_consuming()
    except Exception:
        pass
    
    print("\n" + "=" * 60)
    print(f"✅ Received {received_count} message(s)")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import sys
    
    # Send test message
    send_test_message("Create a simple counter app with + and - buttons")
    
    # Listen for responses
    listen_for_responses(duration=10)