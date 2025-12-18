"""
Test connections to all infrastructure services
Run: poetry run python test_connections.py
"""
import sys
import time


def test_redis():
    """Test Redis connection"""
    print("\n[1/3] Testing Redis...")
    try:
        import redis
        
        client = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True,
            socket_connect_timeout=5
        )
        
        # Test PING
        response = client.ping()
        if not response:
            raise Exception("PING failed")
        
        # Test SET/GET
        client.set('test_key', 'test_value')
        value = client.get('test_key')
        if value != 'test_value':
            raise Exception("SET/GET failed")
        
        # Cleanup
        client.delete('test_key')
        
        print("  ✅ Redis: Connected and working")
        return True
        
    except Exception as e:
        print(f"  ❌ Redis: Failed - {e}")
        return False


def test_rabbitmq():
    """Test RabbitMQ connection"""
    print("\n[2/3] Testing RabbitMQ...")
    try:
        import pika
        
        # Connection parameters
        credentials = pika.PlainCredentials('admin', 'password')
        parameters = pika.ConnectionParameters(
            host='localhost',
            port=5672,
            virtual_host='/',
            credentials=credentials,
            connection_attempts=3,
            retry_delay=2
        )
        
        # Connect
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Declare a test queue
        queue = channel.queue_declare(queue='test_queue', durable=True)
        
        # Publish a test message
        channel.basic_publish(
            exchange='',
            routing_key='test_queue',
            body='Test message'
        )
        
        # Consume the message
        method, properties, body = channel.basic_get(queue='test_queue', auto_ack=True)
        
        if body != b'Test message':
            raise Exception("Message mismatch")
        
        # Cleanup
        channel.queue_delete(queue='test_queue')
        connection.close()
        
        print("  ✅ RabbitMQ: Connected and working")
        return True
        
    except Exception as e:
        print(f"  ❌ RabbitMQ: Failed - {e}")
        return False


def test_postgres():
    """Test PostgreSQL connection"""
    print("\n[3/3] Testing PostgreSQL...")
    try:
        # Try importing psycopg2
        try:
            import psycopg2
        except ImportError:
            print("  📦 Installing psycopg2-binary...")
            import subprocess
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "psycopg2-binary"],
                check=True,
                capture_output=True
            )
            import psycopg2
        
        # Connect
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="appbuilder",
            user="admin",
            password="password",
            connect_timeout=5
        )
        
        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        print("  ✅ PostgreSQL: Connected and working")
        return True
        
    except Exception as e:
        print(f"  ❌ PostgreSQL: Failed - {e}")
        return False


def main():
    """Run all connection tests"""
    print("=" * 60)
    print("  TESTING INFRASTRUCTURE CONNECTIONS")
    print("=" * 60)
    
    start_time = time.time()
    
    # Run all tests
    results = {
        'Redis': test_redis(),
        'RabbitMQ': test_rabbitmq(),
        'PostgreSQL': test_postgres()
    }
    
    elapsed = time.time() - start_time
    
    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for service, status in results.items():
        icon = "✅" if status else "❌"
        print(f"  {icon} {service}")
    
    print("-" * 60)
    print(f"  Passed: {passed}/{total}")
    print(f"  Time: {elapsed:.2f}s")
    print("=" * 60)
    
    if all(results.values()):
        print("\n🎉 All services connected successfully!\n")
        return 0
    else:
        print("\n⚠️  Some services failed to connect")
        print("\n💡 Troubleshooting:")
        print("  1. Check Docker Desktop is running")
        print("  2. Run: cd infra && docker-compose ps")
        print("  3. Check logs: docker-compose logs <service-name>\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())