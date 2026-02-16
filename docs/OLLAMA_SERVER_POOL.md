# Ollama Server Pool Implementation

## Overview

The joke pipeline now supports multiple Ollama servers with concurrent access control. This allows:

1. **Multiple Ollama servers** - Distribute LLM calls across multiple server instances
2. **Concurrency limiting** - Control how many concurrent requests each server handles
3. **Model-aware routing** - Automatically route requests to servers that have the required model loaded
4. **Cross-process locking** - Works correctly even when multiple cron jobs run stages independently
5. **Automatic retry with jitter** - Intelligently waits and retries when all servers are busy
6. **Clean shutdown** - Signal handlers (SIGINT/SIGTERM) automatically clean up locks

## Configuration

All configuration is in `config.py`:

```python
# Ollama Server Pool Configuration
OLLAMA_SERVERS = [
  {"url": "http://localhost:11434", "max_concurrent": 1},
  {"url": "http://server2:11434", "max_concurrent": 1},
  {"url": "http://server3:11434", "max_concurrent": 2},  # Can handle 2 concurrent requests
]

# Locking Configuration
OLLAMA_LOCK_DIR = "locks/ollama-servers"  # Directory for lock files
OLLAMA_LOCK_RETRY_WAIT = 5.0  # Base wait time between retries (seconds)
OLLAMA_LOCK_RETRY_MAX_ATTEMPTS = 12  # Max retry attempts (5s * 12 = 60s total)
OLLAMA_LOCK_RETRY_JITTER = 2.0  # Max random jitter to add to retry wait (seconds)
```

### Server Configuration

Each server in `OLLAMA_SERVERS` has:
- **url**: Base URL of the Ollama server (e.g., "http://localhost:11434")
- **max_concurrent**: Maximum number of concurrent requests this server can handle

### Model Configuration

Each stage still specifies its required model in the existing config dictionaries:
- `OLLAMA_CLEANLINESS_CHECK['OLLAMA_MODEL']`
- `OLLAMA_FORMATTING['OLLAMA_MODEL']`
- `OLLAMA_CATEGORIZATION['OLLAMA_MODEL']`
- `OLLAMA_TITLE_GENERATION['OLLAMA_MODEL']`

The server pool automatically:
1. Queries each server's `/api/tags` endpoint to get available models
2. Only uses servers that have the required model loaded
3. Returns an error if no servers have the required model

## How It Works

### File-Based Locking

The system uses file-based locks in `locks/ollama-servers/`:
- Lock files are named: `server-{hash}-{slot}.lock`
  - Example: `server-abc12345-0.lock` (slot 0 of server with hash abc12345)
- Each lock file contains JSON metadata:
  ```json
  {
    "pid": 12345,
    "timestamp": 1234567890.123,
    "stage": "cleanliness_check",
    "server_url": "http://localhost:11434"
  }
  ```
- Uses `fcntl.flock()` for atomic, cross-process locking
- Automatically detects and cleans up stale locks (when process no longer exists)

### Request Flow

1. **Acquire Server**:
   - Stage processor calls `OllamaClient.generate()`
   - Client requests a server from the pool with the required model
   - Pool checks which servers have the model loaded
   - Pool tries to acquire a lock on any available slot across all capable servers
   - If all busy, waits `OLLAMA_LOCK_RETRY_WAIT` + random jitter (0-`OLLAMA_LOCK_RETRY_JITTER`) seconds
   - Retries up to `OLLAMA_LOCK_RETRY_MAX_ATTEMPTS` times

2. **Use Server**:
   - Makes API request to the acquired server
   - Processes response

3. **Release Server**:
   - Releases lock (in `finally` block, so always happens)
   - Lock file is deleted
   - Server slot becomes available for other processes

### Load Balancing

- Servers are shuffled randomly before trying to acquire a lock
- This distributes load evenly across all available servers
- Jitter prevents thundering herd when multiple processes are waiting

### Signal Handling

Both `joke-pipeline.py` and individual stage scripts register signal handlers:
- **SIGINT** (Ctrl-C): Cleans up locks and exits gracefully
- **SIGTERM** (kill): Cleans up locks and exits gracefully

This prevents orphaned lock files when processes are killed.

## Usage

### Running the Pipeline

The pipeline automatically initializes the server pool:

```bash
# Run full pipeline (uses server pool automatically)
./joke-pipeline.py

# Run specific stage (also uses server pool)
./stage_deduped.py
```

### Cron Jobs

You can run multiple stages in parallel via cron:

```cron
# Run different stages every 5 minutes
*/5 * * * * cd /path/to/pipeline && ./stage_deduped.py >> logs/cron-deduped.log 2>&1
*/5 * * * * cd /path/to/pipeline && ./stage_clean_checked.py >> logs/cron-clean_checked.log 2>&1
*/5 * * * * cd /path/to/pipeline && ./stage_formatted.py >> logs/cron-formatted.log 2>&1
```

The server pool ensures they don't overwhelm the Ollama servers.

## Files Modified

### New Files
- `ollama_server_pool.py` - Server pool implementation with locking
- `stage_utils.py` - Shared initialization utilities for stage scripts
- `OLLAMA_SERVER_POOL.md` - This documentation

### Modified Files
- `config.py` - Added server pool configuration, removed `OLLAMA_API_URL` from stage configs
- `ollama_client.py` - Updated to use server pool instead of fixed URL
- `joke-pipeline.py` - Initialize server pool and signal handlers
- `stage_deduped.py` - Initialize environment in __main__
- `stage_clean_checked.py` - Initialize environment in __main__
- `stage_formatted.py` - Initialize environment in __main__
- `stage_categorized.py` - Initialize environment in __main__

## Monitoring

### Check Lock Files

```bash
# See active locks
ls -la locks/ollama-servers/

# View lock metadata
cat locks/ollama-servers/server-abc12345-0.lock | python3 -m json.tool
```

### Debug Logging

Run with `--verbose` to see detailed server pool activity:

```bash
./joke-pipeline.py --verbose
```

This shows:
- Which servers have which models
- Server acquisition attempts
- Retry delays with jitter
- Lock acquisitions and releases

## Troubleshooting

### "No available servers for model X"

**Cause**: No servers have the required model loaded.

**Solution**:
1. Check that Ollama servers are running: `curl http://localhost:11434/api/tags`
2. Verify the model is loaded: `ollama list` on each server
3. Check server URLs in `config.OLLAMA_SERVERS` are correct
4. Ensure model name in config matches exactly (including tag, e.g., `gemma3:12b`)

### All servers always busy

**Cause**: Too many concurrent processes for available server capacity.

**Solutions**:
1. Add more servers to `OLLAMA_SERVERS`
2. Increase `max_concurrent` for existing servers (if hardware allows)
3. Increase `OLLAMA_LOCK_RETRY_MAX_ATTEMPTS` to wait longer
4. Reduce number of parallel cron jobs

### Stale lock files

**Cause**: Process crashed or was killed without cleaning up.

**Solution**:
- Lock files are automatically cleaned up when detected (PID check)
- Manual cleanup: `rm locks/ollama-servers/*.lock`

### Performance tuning

Adjust these config values based on your setup:
- **More servers/higher concurrency**: Lower latency, higher throughput
- **Higher retry wait/jitter**: Reduces CPU usage when busy, increases latency
- **Lower retry wait**: Faster response when slot opens, more CPU usage
- **More retry attempts**: Less likely to fail under heavy load, longer max wait time

## Example Configurations

### Single powerful server
```python
OLLAMA_SERVERS = [
  {"url": "http://localhost:11434", "max_concurrent": 4},
]
```

### Multiple servers with different capacities
```python
OLLAMA_SERVERS = [
  {"url": "http://gpu-server-1:11434", "max_concurrent": 3},  # Powerful GPU
  {"url": "http://gpu-server-2:11434", "max_concurrent": 3},  # Powerful GPU
  {"url": "http://cpu-server:11434", "max_concurrent": 1},    # CPU fallback
]
```

### Development setup (disable model checking)
```python
# In your code:
initialize_server_pool(
  servers=config.OLLAMA_SERVERS,
  lock_dir=config.OLLAMA_LOCK_DIR,
  retry_wait=config.OLLAMA_LOCK_RETRY_WAIT,
  retry_max_attempts=config.OLLAMA_LOCK_RETRY_MAX_ATTEMPTS,
  retry_jitter=config.OLLAMA_LOCK_RETRY_JITTER,
  check_models=False  # Skip model availability checking
)
```
