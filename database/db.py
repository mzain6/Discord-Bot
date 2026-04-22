import sqlite3
import json
from pathlib import Path


class JobDatabase:
    """
    SQLite database wrapper for the Upwork Discord bot.

    Single table: `jobs`
    - Stores full details of every job that was posted to Discord.
    - Composite primary key (job_id, keyword) allows the same job to be
      posted to multiple keyword channels (e.g. python vs django) without
      duplication within the same channel.
    """

    DB_PATH = Path("database/jobs.db")

    def __init__(self):
        self.DB_PATH.parent.mkdir(exist_ok=True)
        # check_same_thread=False — safe here because we only write from
        # the main asyncio thread; the auth refresh thread only reads scraper,
        # not the DB.
        self.conn = sqlite3.connect(str(self.DB_PATH), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        print(f"[DB] Connected to {self.DB_PATH}")

    def _create_tables(self):
        """Create the jobs table if it doesn't already exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id           VARCHAR(255),
                keyword          VARCHAR(255),
                title            TEXT,
                description      TEXT,
                job_type         VARCHAR(20),
                budget           VARCHAR(50),
                experience_level VARCHAR(20),
                posted_at        TIMESTAMP,
                detected_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                job_url          TEXT,
                raw_json         TEXT,
                PRIMARY KEY (job_id, keyword)
            )
        """)
        self.conn.commit()

    # ------------------------------------------------------------------
    # Core deduplication methods
    # ------------------------------------------------------------------

    def is_seen(self, job_id: str, keyword: str) -> bool:
        """
        Returns True if this job has already been posted for this keyword.
        Used to prevent duplicate Discord posts.
        """
        cur = self.conn.execute(
            "SELECT 1 FROM jobs WHERE job_id = ? AND keyword = ?",
            (job_id, keyword)
        )
        return cur.fetchone() is not None

    def save_job(self, job_data: dict, keyword: str, budget: str, job_url: str):
        """
        Saves full job details + matched keyword to the jobs table.
        Uses INSERT OR IGNORE so duplicate (job_id, keyword) pairs are silently skipped.
        """
        job = job_data.get('jobTile', {}).get('job', {}) or {}
        self.conn.execute(
            """INSERT OR IGNORE INTO jobs
               (job_id, keyword, title, description, job_type,
                budget, experience_level, posted_at, job_url, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job_data.get('id'),
                keyword,
                job_data.get('title'),
                job_data.get('description'),
                job.get('jobType'),
                budget,
                job.get('contractorTier'),
                job.get('createTime'),
                job_url,
                json.dumps(job_data),   # full raw API response as backup
            )
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Analytics / reporting
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """
        Returns statistics used by the !stats Discord command.
        - total_unique_jobs: count of distinct job IDs in the table
        - by_keyword: dict of { keyword: count }
        """
        total = self.conn.execute(
            "SELECT COUNT(DISTINCT job_id) FROM jobs"
        ).fetchone()[0]

        rows = self.conn.execute(
            "SELECT keyword, COUNT(*) as cnt FROM jobs GROUP BY keyword ORDER BY cnt DESC"
        ).fetchall()

        return {
            "total_unique_jobs": total,
            "by_keyword": {row["keyword"]: row["cnt"] for row in rows},
        }

    def get_recent_jobs(self, keyword: str = None, limit: int = 10) -> list:
        """
        Returns the most recently detected jobs.
        Optionally filter by keyword.
        """
        if keyword:
            rows = self.conn.execute(
                "SELECT title, budget, job_url, detected_at FROM jobs "
                "WHERE keyword = ? ORDER BY detected_at DESC LIMIT ?",
                (keyword, limit)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT title, budget, job_url, detected_at FROM jobs "
                "ORDER BY detected_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------

    def close(self):
        """Cleanly closes the SQLite connection."""
        self.conn.close()
        print("[DB] Connection closed.")
