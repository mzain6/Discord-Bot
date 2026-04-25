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
        """Create necessary tables if they don't already exist."""
        # Main jobs history table
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

        # Drop old ghost tables if they exist
        self.conn.execute("DROP TABLE IF EXISTS tracked_searches")
        self.conn.execute("DROP TABLE IF EXISTS seen_jobs")

        # Persistence for tracked keywords/searches
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tracked_keywords (
                keyword    VARCHAR(255) PRIMARY KEY,
                channel_id BIGINT,
                label      VARCHAR(255),
                added_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Migration: Add update tracking columns if they don't exist
        try:
            self.conn.execute("ALTER TABLE jobs ADD COLUMN last_published_at TIMESTAMP")
            self.conn.execute("ALTER TABLE jobs ADD COLUMN is_updated INTEGER DEFAULT 0")
            self.conn.execute("ALTER TABLE jobs ADD COLUMN updated_at TIMESTAMP")
        except sqlite3.OperationalError:
            # Columns already exist
            pass
            
        self.conn.commit()

    # ------------------------------------------------------------------
    # Core deduplication methods
    # ------------------------------------------------------------------

    def get_job_status(self, job_data: dict, keyword: str) -> str:
        """
        Determines the status of a job:
        - 'NEW': ID not seen.
        - 'UPDATE': ID seen, but significant fields (description, title, budget, etc) have changed.
        - 'SEEN': ID seen and no significant changes.
        """
        job_id = job_data.get('id')
        description = job_data.get('description', '')
        title = job_data.get('title', '')
        
        job_inner = (job_data.get('jobTile') or {}).get('job') or {}
        publish_time = job_inner.get('publishTime') or job_inner.get('createTime') or ""
        
        # Calculate budget string for comparison
        job_type = job_inner.get('jobType', '')
        if job_type == 'HOURLY':
            lo = job_inner.get('hourlyBudgetMin')
            hi = job_inner.get('hourlyBudgetMax')
            if lo and hi:
                budget = f"${lo}-${hi}/hr"
            elif lo:
                budget = f"From ${lo}/hr"
            elif hi:
                budget = f"Up to ${hi}/hr"
            else:
                budget = 'N/A'
        elif job_type == 'FIXED':
            amt = (job_inner.get('fixedPriceAmount') or {}).get('amount')
            budget = f"${amt}" if amt else 'N/A'
        else:
            budget = 'N/A'

        experience_level = job_inner.get('contractorTier', '')

        # 1. Check if ID exists
        cur = self.conn.execute(
            "SELECT description, title, budget, experience_level, last_published_at FROM jobs WHERE job_id = ? AND keyword = ?",
            (job_id, keyword)
        )
        row = cur.fetchone()
        
        if row:
            stored_desc = row['description']
            stored_title = row['title']
            stored_budget = row['budget']
            stored_exp = row['experience_level']
            stored_publish_time = row['last_published_at'] or ""
            
            # Check for any meaningful changes or if the publish time is strictly newer
            has_text_changed = (description != stored_desc) or (title != stored_title) or (budget != stored_budget) or (experience_level != stored_exp)
            is_newer_publish = (publish_time > stored_publish_time) if (publish_time and stored_publish_time) else False
            
            if has_text_changed or is_newer_publish:
                return 'UPDATE'
            return 'SEEN'
            
        return 'NEW'

    def is_seen(self, job_id: str, keyword: str, description: str = None) -> bool:
        """
        Returns True if this job has already been posted for this keyword.
        Checks by ID or by exact Description match.
        """
        # Check by ID
        cur = self.conn.execute(
            "SELECT 1 FROM jobs WHERE job_id = ? AND keyword = ?",
            (job_id, keyword)
        )
        if cur.fetchone():
            return True
            
        # Check by Description fallback
        if description:
            cur = self.conn.execute(
                "SELECT 1 FROM jobs WHERE description = ? AND keyword = ?",
                (description.strip(), keyword)
            )
            if cur.fetchone():
                return True
                
        return False

    def mark_job_updated(self, job_data: dict, keyword: str):
        """Updates a job record when an update is detected."""
        job_id = job_data.get('id')
        description = job_data.get('description')
        title = job_data.get('title')
        
        job_inner = (job_data.get('jobTile') or {}).get('job') or {}
        experience_level = job_inner.get('contractorTier', '')
        job_type = job_inner.get('jobType', '')
        publish_time = job_inner.get('publishTime') or job_inner.get('createTime')
        
        # Calculate budget string
        if job_type == 'HOURLY':
            lo = job_inner.get('hourlyBudgetMin')
            hi = job_inner.get('hourlyBudgetMax')
            if lo and hi:
                budget = f"${lo}-${hi}/hr"
            elif lo:
                budget = f"From ${lo}/hr"
            elif hi:
                budget = f"Up to ${hi}/hr"
            else:
                budget = 'N/A'
        elif job_type == 'FIXED':
            amt = (job_inner.get('fixedPriceAmount') or {}).get('amount')
            budget = f"${amt}" if amt else 'N/A'
        else:
            budget = 'N/A'
        
        self.conn.execute(
            """UPDATE jobs SET 
               is_updated = 1, 
               updated_at = CURRENT_TIMESTAMP, 
               last_published_at = ?, 
               raw_json = ?,
               description = ?,
               title = ?,
               budget = ?,
               experience_level = ?,
               job_type = ?
               WHERE job_id = ? AND keyword = ?""",
            (publish_time, json.dumps(job_data), description, title, budget, experience_level, job_type, job_id, keyword)
        )
        self.conn.commit()

    def save_job(self, job_data: dict, keyword: str, budget: str, job_url: str):
        """
        Saves full job details + matched keyword to the jobs table.
        Uses INSERT OR IGNORE so duplicate (job_id, keyword) pairs are silently skipped.
        """
        job = (job_data.get('jobTile') or {}).get('job') or {}
        publish_time = job.get('publishTime') or job.get('createTime')
        
        self.conn.execute(
            """INSERT OR IGNORE INTO jobs
               (job_id, keyword, title, description, job_type,
                budget, experience_level, posted_at, job_url, raw_json, last_published_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                publish_time
            )
        )
        self.conn.commit()

    def get_stats(self) -> dict:
        """Returns some high-level stats about the database."""
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

    def get_job_count(self, keyword: str) -> int:
        """Returns the total number of jobs stored for a specific keyword."""
        row = self.conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE keyword = ?",
            (keyword,)
        ).fetchone()
        return row[0] if row else 0

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
    # NEW: Tracked Keyword Management
    # ------------------------------------------------------------------

    def add_tracking(self, keyword: str, channel_id: int, label: str = None):
        """Adds a keyword to the tracking list."""
        self.conn.execute(
            "INSERT OR REPLACE INTO tracked_keywords (keyword, channel_id, label) VALUES (?, ?, ?)",
            (keyword, channel_id, label or keyword)
        )
        self.conn.commit()

    def remove_tracking(self, keyword: str):
        """Removes a keyword from the tracking list."""
        self.conn.execute("DELETE FROM tracked_keywords WHERE keyword = ?", (keyword,))
        self.conn.commit()

    def delete_keyword_data(self, keyword: str):
        """Completely wipes a keyword from tracking AND all its job history."""
        # 1. Remove from tracking
        self.conn.execute("DELETE FROM tracked_keywords WHERE keyword = ?", (keyword,))
        # 2. Remove all jobs associated with this keyword
        self.conn.execute("DELETE FROM jobs WHERE keyword = ?", (keyword,))
        self.conn.commit()

    def get_all_tracking(self) -> list:
        """Returns all currently tracked keywords as a list of dicts."""
        rows = self.conn.execute("SELECT * FROM tracked_keywords").fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    def is_new_job(self, job_id: str, keyword: str, description: str = None) -> bool:
        """
        Checks if this specific job_id for this keyword has been posted,
        or if the exact same description has already been shared.
        """
        return not self.is_seen(job_id, keyword, description)

    def mark_job_as_seen(self, job_id: str, keyword: str):
        """No-op here because save_job already handles this via the primary key on the jobs table."""
        pass

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------

    def close(self):
        """Cleanly closes the SQLite connection."""
        self.conn.close()
        print("[DB] Connection closed.")
