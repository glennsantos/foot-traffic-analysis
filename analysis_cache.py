"""Completed OSM results shared by workers, or by hosts when Redis is configured."""

import hashlib
import json
import logging
import sqlite3
import time
from datetime import datetime
from math import ceil
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)
# Bump when extraction or scoring changes to invalidate cached results and reports.
ANALYSIS_VERSION = "osm-screening-v1"


def analysis_key(lat, lon, radius):
    query = json.dumps([ANALYSIS_VERSION, lat, lon, radius], separators=(",", ":"))
    return "retail:analysis:" + hashlib.sha256(query.encode()).hexdigest()


class AnalysisCache:
    def __init__(self, path, ttl=3600, max_entries=512, redis_url=None):
        self.path = Path(path)
        self.ttl = ttl
        self.max_entries = max_entries
        self.redis = None
        if redis_url:
            from redis import Redis
            from redis.backoff import NoBackoff
            from redis.retry import Retry
            self.redis = Redis.from_url(
                redis_url, socket_connect_timeout=1, socket_timeout=1,
                retry=Retry(NoBackoff(), 0), decode_responses=True,
            )

    @contextmanager
    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=1)
        try:
            with connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS results "
                    "(key TEXT PRIMARY KEY, expires REAL NOT NULL, payload TEXT NOT NULL)"
                )
                yield connection
        finally:
            connection.close()

    def get(self, key):
        try:
            if self.redis is not None:
                payload = self.redis.get(key)
            else:
                with self._connect() as connection:
                    row = connection.execute(
                        "SELECT payload FROM results WHERE key = ? AND expires > ?",
                        (key, time.time()),
                    ).fetchone()
                payload = row[0] if row else None
            return json.loads(payload) if payload else None
        except Exception:
            # An unavailable cache must never prevent live analysis.
            logger.warning("Analysis cache read unavailable", exc_info=True)
            return None

    def set(self, key, value):
        try:
            payload = json.dumps(value, allow_nan=False, separators=(",", ":"))
            created = datetime.fromisoformat(value['timestamp']).timestamp() if 'timestamp' in value else time.time()
            expires = created + self.ttl
            remaining = ceil(expires - time.time())
            if remaining <= 0:
                return
            if self.redis is not None:
                self.redis.set(key, payload, ex=remaining)
            else:
                with self._connect() as connection:
                    connection.execute("DELETE FROM results WHERE expires <= ?", (time.time(),))
                    connection.execute(
                        "INSERT OR REPLACE INTO results VALUES (?, ?, ?)",
                        (key, expires, payload),
                    )
                    connection.execute(
                        "DELETE FROM results WHERE key IN "
                        "(SELECT key FROM results ORDER BY expires DESC LIMIT -1 OFFSET ?)",
                        (self.max_entries,),
                    )
        except Exception:
            logger.warning("Analysis cache write unavailable", exc_info=True)
