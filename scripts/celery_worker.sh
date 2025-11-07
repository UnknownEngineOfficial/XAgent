#!/bin/bash
# Celery Worker Management Script for X-Agent
# Usage: ./scripts/celery_worker.sh [start|stop|restart|status|scale]

set -e

WORKER_NAME="xagent-worker"
LOG_DIR="./logs"
PID_FILE="./logs/celery.pid"
CONCURRENCY=${CELERY_CONCURRENCY:-2}
QUEUES=${CELERY_QUEUES:-cognitive,tools,goals,maintenance}
LOGLEVEL=${CELERY_LOGLEVEL:-info}

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

function print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

function print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

function start_worker() {
    print_status "Starting Celery worker..."
    
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        print_warning "Worker is already running (PID: $(cat $PID_FILE))"
        return 1
    fi
    
    celery -A xagent.tasks.queue worker \
        --loglevel="$LOGLEVEL" \
        --concurrency="$CONCURRENCY" \
        --queues="$QUEUES" \
        --max-tasks-per-child=1000 \
        --pidfile="$PID_FILE" \
        --logfile="$LOG_DIR/celery-worker.log" \
        --detach
    
    sleep 2
    
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        print_status "Worker started successfully (PID: $(cat $PID_FILE))"
        print_status "Logs: $LOG_DIR/celery-worker.log"
    else
        print_error "Failed to start worker"
        return 1
    fi
}

function stop_worker() {
    print_status "Stopping Celery worker..."
    
    if [ ! -f "$PID_FILE" ]; then
        print_warning "PID file not found. Worker may not be running."
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ! kill -0 "$PID" 2>/dev/null; then
        print_warning "Worker process (PID: $PID) is not running"
        rm -f "$PID_FILE"
        return 1
    fi
    
    # Try graceful shutdown first
    kill -TERM "$PID"
    
    # Wait for up to 30 seconds for graceful shutdown
    for i in {1..30}; do
        if ! kill -0 "$PID" 2>/dev/null; then
            print_status "Worker stopped gracefully"
            rm -f "$PID_FILE"
            return 0
        fi
        sleep 1
    done
    
    # Force kill if still running
    print_warning "Graceful shutdown timed out, forcing shutdown..."
    kill -KILL "$PID" 2>/dev/null || true
    rm -f "$PID_FILE"
    print_status "Worker stopped (forced)"
}

function restart_worker() {
    print_status "Restarting Celery worker..."
    stop_worker || true
    sleep 2
    start_worker
}

function worker_status() {
    print_status "Checking worker status..."
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            print_status "Worker is running (PID: $PID)"
            
            # Try to get more info from Celery
            echo ""
            print_status "Worker details:"
            celery -A xagent.tasks.queue inspect active -d "celery@$(hostname)" 2>/dev/null || \
                print_warning "Could not retrieve active tasks"
            
            echo ""
            print_status "Queue stats:"
            celery -A xagent.tasks.queue inspect reserved -d "celery@$(hostname)" 2>/dev/null || \
                print_warning "Could not retrieve queue stats"
            
            return 0
        else
            print_warning "PID file exists but process is not running"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        print_warning "Worker is not running (PID file not found)"
        return 1
    fi
}

function scale_workers() {
    local new_concurrency=$1
    
    if [ -z "$new_concurrency" ]; then
        print_error "Please specify concurrency level: ./celery_worker.sh scale <number>"
        return 1
    fi
    
    if [ ! -f "$PID_FILE" ] || ! kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        print_error "Worker is not running. Start it first with: ./celery_worker.sh start"
        return 1
    fi
    
    print_status "Scaling worker to $new_concurrency concurrent processes..."
    celery -A xagent.tasks.queue control pool_grow "$new_concurrency" -d "celery@$(hostname)"
    
    print_status "Worker scaled successfully"
}

function show_logs() {
    if [ ! -f "$LOG_DIR/celery-worker.log" ]; then
        print_error "Log file not found: $LOG_DIR/celery-worker.log"
        return 1
    fi
    
    print_status "Showing last 50 lines of worker logs:"
    echo ""
    tail -n 50 "$LOG_DIR/celery-worker.log"
}

function purge_tasks() {
    read -p "Are you sure you want to purge all pending tasks? (yes/no): " -r
    echo
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        print_status "Purging all pending tasks..."
        celery -A xagent.tasks.queue purge -f
        print_status "All pending tasks purged"
    else
        print_status "Purge cancelled"
    fi
}

# Main command handler
case "${1:-}" in
    start)
        start_worker
        ;;
    stop)
        stop_worker
        ;;
    restart)
        restart_worker
        ;;
    status)
        worker_status
        ;;
    scale)
        scale_workers "$2"
        ;;
    logs)
        show_logs
        ;;
    purge)
        purge_tasks
        ;;
    *)
        echo "Celery Worker Management Script"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|scale|logs|purge}"
        echo ""
        echo "Commands:"
        echo "  start       - Start the Celery worker"
        echo "  stop        - Stop the Celery worker"
        echo "  restart     - Restart the Celery worker"
        echo "  status      - Check worker status and show active tasks"
        echo "  scale <n>   - Scale worker to n concurrent processes"
        echo "  logs        - Show last 50 lines of worker logs"
        echo "  purge       - Purge all pending tasks (requires confirmation)"
        echo ""
        echo "Environment Variables:"
        echo "  CELERY_CONCURRENCY  - Number of concurrent worker processes (default: 2)"
        echo "  CELERY_QUEUES       - Comma-separated list of queues (default: cognitive,tools,goals,maintenance)"
        echo "  CELERY_LOGLEVEL     - Log level (default: info)"
        echo ""
        exit 1
        ;;
esac
