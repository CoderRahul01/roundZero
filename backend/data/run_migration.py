"""
Run database migrations for Enhanced Interview Experience.

This script applies SQL migrations to the Postgres database (Neon/Supabase).
"""

import asyncio
import asyncpg
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_migration(migration_file: Path):
    """
    Run a single migration file.
    
    Args:
        migration_file: Path to SQL migration file
    """
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise ValueError("DATABASE_URL environment variable not set")
    
    logger.info(f"Connecting to database...")
    conn = await asyncpg.connect(dsn)
    
    try:
        # Read migration SQL
        logger.info(f"Reading migration: {migration_file.name}")
        sql = migration_file.read_text()
        
        # Execute migration
        logger.info(f"Executing migration: {migration_file.name}")
        await conn.execute(sql)
        
        logger.info(f"✅ Migration {migration_file.name} completed successfully")
        
        # Verify new columns exist
        logger.info("Verifying new columns...")
        result = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'sessions'
            AND column_name IN (
                'onboarding_completed',
                'onboarding_duration_seconds',
                'current_question_number',
                'total_questions',
                'average_confidence',
                'average_relevance',
                'average_completeness',
                'overall_performance',
                'status',
                'last_update_timestamp'
            )
            ORDER BY column_name;
        """)
        
        logger.info("\n📊 New Columns Added:")
        for row in result:
            logger.info(f"  • {row['column_name']}: {row['data_type']} "
                       f"(nullable: {row['is_nullable']}, default: {row['column_default']})")
        
        # Verify indexes
        logger.info("\nVerifying indexes...")
        indexes = await conn.fetch("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'sessions'
            AND indexname IN ('idx_sessions_status', 'idx_sessions_user_created');
        """)
        
        logger.info("\n📊 New Indexes Created:")
        for idx in indexes:
            logger.info(f"  • {idx['indexname']}")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()
        logger.info("\n✓ Closed database connection")


async def verify_migration():
    """Verify that the migration was applied successfully."""
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise ValueError("DATABASE_URL environment variable not set")
    
    conn = await asyncpg.connect(dsn)
    
    try:
        # Check if all new columns exist
        required_columns = [
            'onboarding_completed',
            'onboarding_duration_seconds',
            'current_question_number',
            'total_questions',
            'average_confidence',
            'average_relevance',
            'average_completeness',
            'overall_performance',
            'status',
            'last_update_timestamp'
        ]
        
        result = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns 
            WHERE table_name = 'sessions'
            AND column_name = ANY($1::text[]);
        """, required_columns)
        
        existing_columns = {row['column_name'] for row in result}
        
        logger.info("\n🔍 Verification Results:")
        all_exist = True
        
        for col in required_columns:
            exists = col in existing_columns
            status = "✓" if exists else "✗"
            logger.info(f"  {status} {col}")
            all_exist = all_exist and exists
        
        if all_exist:
            logger.info("\n✅ All required columns exist!")
        else:
            logger.warning("\n⚠️  Some columns are missing!")
        
        return all_exist
        
    finally:
        await conn.close()


async def main():
    """Main migration runner."""
    print("=" * 60)
    print("Enhanced Interview Experience - Database Migration")
    print("=" * 60)
    print()
    
    # Get migration file
    migrations_dir = Path(__file__).parent / "migrations"
    migration_file = migrations_dir / "001_extend_sessions_table.sql"
    
    if not migration_file.exists():
        logger.error(f"❌ Migration file not found: {migration_file}")
        return
    
    # Run migration
    await run_migration(migration_file)
    
    print()
    print("=" * 60)
    print("Verifying Migration")
    print("=" * 60)
    print()
    
    # Verify migration
    await verify_migration()


if __name__ == "__main__":
    asyncio.run(main())
