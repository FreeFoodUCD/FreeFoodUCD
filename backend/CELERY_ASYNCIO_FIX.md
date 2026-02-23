# Celery AsyncIO Event Loop Fix

## Problem
The application was experiencing `RuntimeError: Event loop is closed` and `RuntimeError: Task got Future attached to a different loop` errors when Celery workers tried to execute async tasks with SQLAlchemy.

### Root Cause
When Celery uses the default `fork` pool on Unix systems:
1. The parent process creates an async SQLAlchemy engine with connections
2. Child worker processes inherit these connections via fork
3. The inherited connections are attached to the parent's event loop
4. When `asyncio.run()` creates a new event loop in the child, there's a mismatch
5. SQLAlchemy tries to use connections from the old loop in the new loop → RuntimeError

## Solution
We implemented a multi-part fix:

### 1. Use Solo Pool (Primary Fix)
Changed Celery to use the `solo` pool instead of `fork`:
- **File**: `backend/app/workers/celery_app.py`
- **Change**: Added `worker_pool='solo'` to Celery config
- **Why**: Solo pool runs tasks in the main process, avoiding fork-related event loop issues

### 2. Update Startup Scripts
Updated all worker startup commands to explicitly use solo pool:
- **Files**: `backend/railway-start-all.sh`, `backend/Procfile`
- **Change**: Added `--pool=solo` flag to celery worker commands
- **Why**: Ensures solo pool is used even if config is overridden

### 3. Add Worker Process Hooks
Added proper engine disposal on worker initialization:
- **File**: `backend/app/workers/celery_app.py`
- **Changes**: 
  - Added `worker_process_init` signal handler to dispose inherited engines
  - Added `worker_process_shutdown` signal handler for cleanup
- **Why**: Ensures fresh database connections in each worker process (defense in depth)

### 4. Improve Database Engine Configuration
Enhanced the async engine with better pool settings:
- **File**: `backend/app/db/base.py`
- **Changes**:
  - Added explicit pool size and overflow settings
  - Added pool connection recycling (1 hour)
  - Added `dispose_engine()` helper function
- **Why**: Better connection management and easier cleanup

## Files Modified
1. `backend/app/workers/celery_app.py` - Added solo pool config and worker hooks
2. `backend/app/db/base.py` - Enhanced engine configuration
3. `backend/railway-start-all.sh` - Updated worker command
4. `backend/Procfile` - Updated worker command

## Deployment
To deploy the fix:

1. **Commit the changes**:
   ```bash
   git add backend/app/workers/celery_app.py backend/app/db/base.py backend/railway-start-all.sh backend/Procfile
   git commit -m "Fix Celery asyncio event loop issues with solo pool"
   ```

2. **Push to Railway**:
   ```bash
   git push
   ```

3. **Restart services** (if needed):
   - Railway will automatically restart on push
   - Or manually restart via Railway dashboard

## Verification
After deployment, check the logs for:
- ✅ No more "Event loop is closed" errors
- ✅ No more "attached to a different loop" errors
- ✅ Tasks executing successfully
- ✅ Log messages: "Initializing worker process" and "Disposed of inherited database engine"

## Performance Considerations
**Solo Pool Trade-offs**:
- ✅ **Pro**: Eliminates fork-related asyncio issues
- ✅ **Pro**: Simpler process model, easier debugging
- ✅ **Pro**: Works well with async/await code
- ⚠️ **Con**: Single-threaded execution (one task at a time per worker)
- ⚠️ **Con**: CPU-bound tasks can block other tasks

**Mitigation**:
- For our use case (I/O-bound tasks: database queries, API calls, notifications), solo pool is ideal
- If you need parallel execution, scale horizontally by running multiple worker instances
- Railway allows easy horizontal scaling via the dashboard

## Alternative Solutions (Not Implemented)
If solo pool doesn't meet your needs, consider:

1. **Gevent Pool**: `--pool=gevent` (requires gevent package)
   - Pros: Concurrent execution with greenlets
   - Cons: Requires gevent-compatible libraries

2. **Eventlet Pool**: `--pool=eventlet` (requires eventlet package)
   - Similar to gevent

3. **Threads Pool**: `--pool=threads`
   - Pros: True threading
   - Cons: GIL limitations, thread safety concerns

## References
- [Celery Concurrency Documentation](https://docs.celeryq.dev/en/stable/userguide/workers.html#concurrency)
- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Python asyncio Event Loop](https://docs.python.org/3/library/asyncio-eventloop.html)

---
*Fixed by Bob - 2026-02-23*