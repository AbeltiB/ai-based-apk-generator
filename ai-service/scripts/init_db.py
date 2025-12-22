"""
Database initialization script.

Creates all required tables, indexes, and initial data.
Run this before starting the service for the first time.
"""
import asyncio
import asyncpg
from loguru import logger
import sys

# Add parent directory to path
sys.path.insert(0, '..')

from app.config import settings


async def create_tables(conn: asyncpg.Connection) -> None:
    """Create all database tables."""
    
    logger.info("Creating tables...")
    
    # Enable UUID extension
    await conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
    
    # Conversations table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id VARCHAR(255) NOT NULL,
            session_id VARCHAR(255) NOT NULL,
            messages JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    # Projects table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id VARCHAR(255) NOT NULL,
            project_name VARCHAR(255),
            architecture JSONB NOT NULL,
            layout JSONB NOT NULL,
            blockly JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    # User preferences table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id VARCHAR(255) PRIMARY KEY,
            preferences JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    # Request metrics table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS request_metrics (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            task_id VARCHAR(255) NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            stage VARCHAR(50) NOT NULL,
            duration_ms INTEGER NOT NULL,
            success BOOLEAN NOT NULL,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    logger.info("✅ Tables created")


async def create_indexes(conn: asyncpg.Connection) -> None:
    """Create database indexes for performance."""
    
    logger.info("Creating indexes...")
    
    # Conversations indexes
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_user_session 
        ON conversations(user_id, session_id);
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_created_at 
        ON conversations(created_at DESC);
    """)
    
    # Projects indexes
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_projects_user_id 
        ON projects(user_id);
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_projects_updated_at 
        ON projects(updated_at DESC);
    """)
    
    # Request metrics indexes
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_metrics_task_id 
        ON request_metrics(task_id);
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_metrics_created_at 
        ON request_metrics(created_at DESC);
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_metrics_user_id 
        ON request_metrics(user_id);
    """)
    
    logger.info("✅ Indexes created")


async def seed_test_data(conn: asyncpg.Connection) -> None:
    """Insert test data for development."""
    
    logger.info("Seeding test data...")
    
    import json
    
    # Test user preferences
    await conn.execute("""
        INSERT INTO user_preferences (user_id, preferences)
        VALUES ($1, $2)
        ON CONFLICT (user_id) DO NOTHING
    """, "test_user_1", json.dumps({
        "theme": "dark",
        "component_style": "minimal"
    }))
    
    logger.info("✅ Test data seeded")


async def verify_tables(conn: asyncpg.Connection) -> None:
    """Verify all tables exist and are accessible."""
    
    logger.info("Verifying tables...")
    
    tables = await conn.fetch("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    
    expected = {'conversations', 'projects', 'user_preferences', 'request_metrics'}
    found = {row['table_name'] for row in tables}
    
    if expected.issubset(found):
        logger.info(f"✅ All required tables exist: {', '.join(sorted(expected))}")
    else:
        missing = expected - found
        logger.error(f"❌ Missing tables: {', '.join(missing)}")
        raise RuntimeError(f"Missing tables: {missing}")


async def main():
    """Main initialization function."""
    
    print("\n" + "=" * 60)
    print("DATABASE INITIALIZATION")
    print("=" * 60)
    
    try:
        # Connect to database
        logger.info(f"Connecting to {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
        
        conn = await asyncpg.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password
        )
        
        logger.info("✅ Connected to PostgreSQL")
        
        # Create tables
        await create_tables(conn)
        
        # Create indexes
        await create_indexes(conn)
        
        # Seed test data (optional)
        if settings.debug:
            await seed_test_data(conn)
        
        # Verify
        await verify_tables(conn)
        
        # Close connection
        await conn.close()
        
        print("\n" + "=" * 60)
        print("✅ DATABASE INITIALIZATION COMPLETE!")
        print("=" * 60)
        print("\nYou can now start the AI service:")
        print("  poetry run uvicorn app.main:app --reload")
        print("\n" + "=" * 60 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        print("\n" + "=" * 60)
        print("❌ INITIALIZATION FAILED")
        print("=" * 60)
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure PostgreSQL is running: docker-compose ps")
        print("  2. Check connection settings in .env")
        print("  3. Verify database exists: psql -U admin -d appbuilder")
        print("\n" + "=" * 60 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())