"""
Structured Logging Configuration for Intelligent Search System
Replaces print-based logging with proper structured logging
"""
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# ============================================================================
# LOG DIRECTORY SETUP
# ============================================================================

LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Log files
QUERY_LOG = LOGS_DIR / "queries.jsonl"        # Structured query logs
ERROR_LOG = LOGS_DIR / "errors.log"           # Error tracking
PERF_LOG = LOGS_DIR / "performance.jsonl"     # Performance metrics
DEBUG_LOG = LOGS_DIR / "debug.log"            # Detailed debug info

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(level=logging.INFO):
    """
    Setup logging configuration for the application

    Args:
        level: Logging level (default: INFO)
    """
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            # Console handler (stdout)
            logging.StreamHandler(),
            # File handler for errors
            logging.FileHandler(ERROR_LOG, mode='a', encoding='utf-8')
        ]
    )

    # Set specific loggers
    logging.getLogger('anthropic').setLevel(logging.WARNING)  # Reduce API noise
    logging.getLogger('httpx').setLevel(logging.WARNING)      # Reduce HTTP noise


# ============================================================================
# STRUCTURED LOGGING HELPERS
# ============================================================================

def log_query(
    query: str,
    stage: str,
    status: str,
    details: Dict[str, Any] = None
):
    """
    Log query execution to structured JSONL file

    Args:
        query: The search query
        stage: Stage name (e.g., "parse", "retrieval", "validation")
        status: Status (e.g., "success", "failed", "initiated")
        details: Additional details dict
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "stage": stage,
        "status": status,
        "details": details or {}
    }

    try:
        with open(QUERY_LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        logging.error(f"Failed to write query log: {e}")


def log_performance(
    operation: str,
    duration_ms: float,
    metadata: Dict[str, Any] = None
):
    """
    Log performance metrics to structured JSONL file

    Args:
        operation: Operation name (e.g., "multi_stage_search", "llm_evaluation")
        duration_ms: Duration in milliseconds
        metadata: Additional metadata dict
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "operation": operation,
        "duration_ms": round(duration_ms, 2),
        "metadata": metadata or {}
    }

    try:
        with open(PERF_LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        logging.error(f"Failed to write performance log: {e}")


def log_rejection(
    candidate_name: str,
    stage: str,
    reason: str,
    details: Dict[str, Any] = None
):
    """
    Log candidate rejection for debugging

    Args:
        candidate_name: Name of rejected candidate
        stage: Stage where rejected (e.g., "expertise_validation", "venue_check")
        reason: Reason for rejection
        details: Additional details
    """
    logger = logging.getLogger("intelligent_agent")
    logger.debug(
        f"[REJECTED] {candidate_name} at {stage}: {reason}",
        extra={"details": details}
    )


# ============================================================================
# ANALYSIS HELPERS
# ============================================================================

def get_query_stats(hours: int = 24) -> Dict[str, Any]:
    """
    Analyze query logs from the last N hours

    Args:
        hours: Number of hours to look back

    Returns:
        Dictionary with query statistics
    """
    if not QUERY_LOG.exists():
        return {"error": "No query log found"}

    cutoff_time = datetime.now().timestamp() - (hours * 3600)
    queries = []

    try:
        with open(QUERY_LOG, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entry_time = datetime.fromisoformat(entry["timestamp"]).timestamp()
                    if entry_time >= cutoff_time:
                        queries.append(entry)
                except (json.JSONDecodeError, KeyError):
                    continue

        # Compute stats
        total_queries = len(set(q["query"] for q in queries if q["stage"] == "start"))
        successful = sum(1 for q in queries if q["status"] == "success" and q["stage"] == "complete")
        failed = sum(1 for q in queries if q["status"] == "failed")

        return {
            "period_hours": hours,
            "total_queries": total_queries,
            "successful": successful,
            "failed": failed,
            "success_rate": round(successful / total_queries * 100, 1) if total_queries > 0 else 0
        }

    except Exception as e:
        return {"error": str(e)}


def get_performance_stats(operation: str = None, hours: int = 24) -> Dict[str, Any]:
    """
    Analyze performance logs

    Args:
        operation: Filter by operation name (optional)
        hours: Number of hours to look back

    Returns:
        Performance statistics
    """
    if not PERF_LOG.exists():
        return {"error": "No performance log found"}

    cutoff_time = datetime.now().timestamp() - (hours * 3600)
    durations = []

    try:
        with open(PERF_LOG, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entry_time = datetime.fromisoformat(entry["timestamp"]).timestamp()

                    if entry_time >= cutoff_time:
                        if operation is None or entry["operation"] == operation:
                            durations.append(entry["duration_ms"])
                except (json.JSONDecodeError, KeyError):
                    continue

        if not durations:
            return {"message": "No data found"}

        import statistics
        return {
            "operation": operation or "all",
            "period_hours": hours,
            "count": len(durations),
            "avg_ms": round(statistics.mean(durations), 2),
            "median_ms": round(statistics.median(durations), 2),
            "min_ms": round(min(durations), 2),
            "max_ms": round(max(durations), 2)
        }

    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# INITIALIZE LOGGING
# ============================================================================

# Auto-setup logging on import
setup_logging()

# Get logger for this module
logger = logging.getLogger(__name__)
logger.info(f"Logging initialized. Logs directory: {LOGS_DIR}")
