# Zenflow Multi-Task Isolation Setup

## Overview

This directory contains templates for Zenflow task isolation. These templates ensure that multiple Zenflow tasks can run in parallel without port conflicts or resource contention.

## Files

- **`.env.task`**: Template for task-specific environment variables
- **`README.md`**: This documentation file

## Port Allocation Algorithm

To prevent port conflicts between parallel Zenflow tasks, we use a deterministic port allocation algorithm:

### Algorithm

1. **Extract numeric suffix from task ID**
   - Task ID format: `{name}-{numeric-suffix}`
   - Example: `ci-suite-tests-parallele-zenflow-9947` → suffix = `9947`

2. **Calculate base port**
   ```
   ZENFLOW_PORT_BASE = (task_id_suffix % 9000) + 1000
   ```
   - This ensures base ports are in range `1000-9999`
   - Example: `(9947 % 9000) + 1000 = 1947`

3. **Assign service-specific ports**
   ```
   POSTGRES_PORT  = 10000 + (base % 1000)  # Range: 10000-10999
   REDIS_PORT     = 16000 + (base % 1000)  # Range: 16000-16999
   BACKEND_PORT   = 18000 + (base % 1000)  # Range: 18000-18999
   FRONTEND_PORT  = 15000 + (base % 1000)  # Range: 15000-15999
   ```

### Example Calculation

For task ID `ci-suite-tests-parallele-zenflow-9947`:

```bash
# Extract suffix
task_id_suffix=9947

# Calculate base
base=$((9947 % 9000 + 1000))  # = 1947

# Assign ports
POSTGRES_PORT=$((10000 + 947))   # = 10947
REDIS_PORT=$((16000 + 947))      # = 16947
BACKEND_PORT=$((18000 + 947))    # = 18947
FRONTEND_PORT=$((15000 + 947))   # = 15947
```

### Port Ranges Summary

| Service   | Port Range    | Default | Purpose              |
|-----------|---------------|---------|----------------------|
| Postgres  | 10000-10999   | 10000   | Database             |
| Redis     | 16000-16999   | 16000   | Cache/Message Broker |
| Backend   | 18000-18999   | 18000   | Django API Server    |
| Frontend  | 15000-15999   | 15000   | Vite Dev Server      |

## Usage

### For New Zenflow Tasks

1. **Copy the template**
   ```bash
   cp .zenflow/tasks/template/.env.task .zenflow/tasks/{task-id}/.env.task
   ```

2. **Set task-specific values**
   ```bash
   # Edit .zenflow/tasks/{task-id}/.env.task
   ZENFLOW_TASK_ID=your-task-id-1234
   
   # Calculate ports based on task ID
   ZENFLOW_PORT_BASE=1234
   POSTGRES_PORT=10234
   REDIS_PORT=16234
   BACKEND_PORT=18234
   FRONTEND_PORT=15234
   ```

3. **Source the environment**
   ```bash
   source .zenflow/tasks/{task-id}/.env.task
   ```

4. **Run Docker Compose with Zenflow config**
   ```bash
   docker-compose -f infra/docker/docker-compose.yml \
                  -f docker-compose.zenflow.yml up
   ```

### For Running Tests

Use the Zenflow-aware test wrapper:

```bash
# Automatic detection (if ZENFLOW_TASK_ID is set)
./scripts/test_parallel_zenflow.sh

# With custom worker count
./scripts/test_parallel_zenflow.sh -n 4

# With specific test markers
./scripts/test_parallel_zenflow.sh -n 4 -m api

# Explicit task context
ZENFLOW_TASK_ID=my-task-123 ./scripts/test_parallel_zenflow.sh
```

The script will:
1. Detect `ZENFLOW_TASK_ID` from environment
2. Load `.zenflow/tasks/{task-id}/.env.task` if it exists
3. Configure pytest with appropriate worker count
4. Run tests with task-specific port isolation

## Integration with Docker Compose

The `docker-compose.zenflow.yml` file provides an overlay configuration that:

- Uses environment variables for all port mappings
- Creates task-specific Docker networks
- Isolates volumes per task
- Falls back to default ports if variables are not set

### Example: Multi-Task Parallel Execution

```bash
# Terminal 1 - Task A
export ZENFLOW_TASK_ID=task-a-1000
source .zenflow/tasks/task-a-1000/.env.task
docker-compose -f infra/docker/docker-compose.yml -f docker-compose.zenflow.yml up

# Terminal 2 - Task B (parallel)
export ZENFLOW_TASK_ID=task-b-2000
source .zenflow/tasks/task-b-2000/.env.task
docker-compose -f infra/docker/docker-compose.yml -f docker-compose.zenflow.yml up

# No port conflicts! Each task uses isolated ports and networks
```

## Troubleshooting

### Port Conflicts

If you still encounter port conflicts:

1. **Check active tasks**
   ```bash
   docker ps --format "table {{.Names}}\t{{.Ports}}" | grep zenflow
   ```

2. **Verify environment variables**
   ```bash
   echo "POSTGRES_PORT=$POSTGRES_PORT"
   echo "BACKEND_PORT=$BACKEND_PORT"
   ```

3. **Check port availability**
   ```bash
   netstat -tuln | grep -E "(10947|16947|18947|15947)"
   ```

### Database Isolation Issues

If tests are interfering with each other:

1. **Verify worker-specific databases**
   ```bash
   # Each pytest-xdist worker should use unique DB
   # Check backend/core/settings_test.py logs
   pytest -v -s  # Should show: test_viatique_gw0, test_viatique_gw1, etc.
   ```

2. **Check DATABASE_URL**
   ```bash
   echo $DATABASE_URL
   # Should include task-specific DB name
   ```

## Best Practices

1. **Always use the template** - Don't create `.env.task` files manually
2. **Document custom ports** - If you deviate from the algorithm, document why
3. **Clean up after tasks** - Remove Docker volumes when task is complete:
   ```bash
   docker-compose -f docker-compose.zenflow.yml down -v
   ```
4. **Test isolation** - Verify your task works with others running in parallel
5. **Use the wrapper script** - Prefer `test_parallel_zenflow.sh` over direct pytest

## Related Documentation

- Main parallel testing guide: `docs/development/PARALLEL_TESTING_GUIDE.md`
- Test suite configuration: `backend/pytest.ini`
- CI configuration: `.github/workflows/korrigo-ci.yml`
