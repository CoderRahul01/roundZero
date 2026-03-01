# Vision Agents Integration - Utilities

This directory contains utility functions for the Vision Agents integration.

## MongoDB Index Creation

The `create_indexes.py` module provides functions to create and manage MongoDB indexes for optimal query performance.

### Requirements

- Requirements: 8.17, 8.18
- Creates indexes for `live_sessions` and `question_results` collections
- Supports index verification and management

### Indexes Created

#### live_sessions Collection

1. **Unique Index on session_id**
   - Field: `session_id`
   - Type: Unique
   - Purpose: Ensures session uniqueness and fast lookups by session ID

2. **Compound Index on (candidate_id, started_at)**
   - Fields: `candidate_id` (ascending), `started_at` (descending)
   - Purpose: Optimizes queries for candidate's sessions sorted by date
   - Example query: "Find all sessions for candidate X, most recent first"

3. **Index on started_at**
   - Field: `started_at`
   - Purpose: Optimizes time-based queries
   - Example query: "Find all sessions in date range"

#### question_results Collection

1. **Compound Index on (session_id, timestamp)**
   - Fields: `session_id` (ascending), `timestamp` (ascending)
   - Purpose: Optimizes session timeline queries
   - Example query: "Find all questions for a session, sorted by time"

### Usage

#### Command Line

Run the script directly to create all indexes:

```bash
# From backend directory
python -m agent.vision.utils.create_indexes

# Or with explicit Python path
python backend/agent/vision/utils/create_indexes.py
```

The script will:
1. Connect to MongoDB using environment variables
2. Create all required indexes
3. Verify indexes were created successfully
4. Display summary of created indexes

#### Environment Variables

Required environment variables (in `.env` file):

```bash
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=roundzero
```

#### Programmatic Usage

```python
from motor.motor_asyncio import AsyncIOMotorClient
from backend.agent.vision.utils.create_indexes import (
    create_all_indexes,
    verify_indexes,
    drop_all_indexes
)

# Connect to MongoDB
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["roundzero"]

# Create all indexes
created_indexes = await create_all_indexes(db)
print(f"Created indexes: {created_indexes}")

# Verify indexes exist
verified_indexes = await verify_indexes(db)
print(f"Verified indexes: {verified_indexes}")

# Drop all custom indexes (use with caution!)
dropped_counts = await drop_all_indexes(db)
print(f"Dropped {dropped_counts} indexes")
```

#### Individual Collection Indexes

```python
from backend.agent.vision.utils.create_indexes import (
    create_live_sessions_indexes,
    create_question_results_indexes
)

# Create indexes for specific collection
live_sessions_indexes = await create_live_sessions_indexes(db)
question_results_indexes = await create_question_results_indexes(db)
```

### Functions

#### `create_all_indexes(db: AsyncIOMotorDatabase) -> Dict[str, Dict[str, str]]`

Creates all indexes for Vision Agents integration collections.

**Returns:**
```python
{
    "live_sessions": {
        "session_id_unique": "session_id_unique",
        "candidate_started_compound": "candidate_started_compound",
        "started_at_index": "started_at_index"
    },
    "question_results": {
        "session_timestamp_compound": "session_timestamp_compound"
    }
}
```

#### `verify_indexes(db: AsyncIOMotorDatabase) -> Dict[str, List[Dict]]`

Verifies that all required indexes exist.

**Returns:**
```python
{
    "live_sessions": [
        {"name": "session_id_unique", "key": [("session_id", 1)], "unique": True},
        {"name": "candidate_started_compound", "key": [("candidate_id", 1), ("started_at", -1)], "unique": False},
        {"name": "started_at_index", "key": [("started_at", 1)], "unique": False}
    ],
    "question_results": [
        {"name": "session_timestamp_compound", "key": [("session_id", 1), ("timestamp", 1)], "unique": False}
    ]
}
```

#### `drop_all_indexes(db: AsyncIOMotorDatabase) -> Dict[str, int]`

Drops all custom indexes (excluding default `_id` index).

**WARNING:** Use with caution! This will drop all custom indexes.

**Returns:**
```python
{
    "live_sessions": 3,  # Number of indexes dropped
    "question_results": 1
}
```

### Testing

Run unit tests to verify index creation logic:

```bash
# From project root
python -m pytest backend/agent/vision/utils/test_create_indexes.py -v

# Run specific test
python -m pytest backend/agent/vision/utils/test_create_indexes.py::test_create_all_indexes -v
```

All tests use mocks and do not require a running MongoDB instance.

### Performance Impact

These indexes significantly improve query performance:

| Query Type | Without Index | With Index | Improvement |
|------------|---------------|------------|-------------|
| Find session by ID | O(n) scan | O(log n) | ~100-1000x |
| Find candidate sessions | O(n) scan | O(log n) | ~100-1000x |
| Time-based queries | O(n) scan | O(log n) | ~100-1000x |
| Session timeline | O(n) scan | O(log n) | ~100-1000x |

### Index Maintenance

MongoDB automatically maintains indexes as documents are inserted, updated, or deleted. No manual maintenance is required.

#### When to Recreate Indexes

- After dropping and recreating collections
- After database migration
- If index corruption is suspected (rare)

#### Monitoring Index Usage

Use MongoDB's built-in tools to monitor index usage:

```javascript
// In MongoDB shell
db.live_sessions.aggregate([{ $indexStats: {} }])
db.question_results.aggregate([{ $indexStats: {} }])
```

### Troubleshooting

#### Index Creation Fails

**Error:** `Index creation failed`

**Solution:**
1. Check MongoDB connection is active
2. Verify user has index creation permissions
3. Check for existing indexes with same name
4. Review MongoDB logs for detailed error

#### Duplicate Key Error

**Error:** `E11000 duplicate key error`

**Solution:**
1. Unique index on `session_id` requires all existing documents to have unique values
2. Clean up duplicate session_id values before creating index
3. Or drop and recreate the collection

#### Performance Issues

**Symptom:** Queries still slow after index creation

**Solution:**
1. Verify indexes are being used: `db.collection.explain("executionStats").find(...)`
2. Check index is appropriate for query pattern
3. Consider compound indexes for multi-field queries
4. Monitor index size and memory usage

### Integration with Application

The indexes are automatically used by MongoDB when executing queries. No code changes are required.

Example queries that benefit from indexes:

```python
# Fast: Uses session_id_unique index
session = await db["live_sessions"].find_one({"session_id": "session_123"})

# Fast: Uses candidate_started_compound index
sessions = await db["live_sessions"].find(
    {"candidate_id": "user_456"}
).sort("started_at", -1).to_list(length=10)

# Fast: Uses started_at_index
recent_sessions = await db["live_sessions"].find({
    "started_at": {"$gte": "2024-01-01T00:00:00Z"}
}).to_list(length=None)

# Fast: Uses session_timestamp_compound index
questions = await db["question_results"].find(
    {"session_id": "session_123"}
).sort("timestamp", 1).to_list(length=None)
```

### Related Files

- **Schemas**: `backend/agent/vision/schemas/live_session_schema.py`
- **Schemas**: `backend/agent/vision/schemas/question_result_schema.py`
- **Repository**: `backend/data/mongo_repository.py` (to be created in Task 2.4)

### References

- [MongoDB Indexes Documentation](https://docs.mongodb.com/manual/indexes/)
- [Motor Async Driver Documentation](https://motor.readthedocs.io/)
- Requirements: 8.17, 8.18 in `.kiro/specs/vision-agents-integration/requirements.md`
