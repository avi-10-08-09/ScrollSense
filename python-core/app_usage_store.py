from datetime import datetime
from pathlib import Path
from contextlib import closing
import sqlite3


class AppUsageStore:
    """
    Stores daily Android app-usage snapshots separately
    from Shorts and Reels feed-level tracking.
    """

    def __init__(self, database_path):
        self.database_path = Path(database_path)

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize_database()

    def _initialize_database(self):
        with closing(
            sqlite3.connect(self.database_path)
        ) as connection:

            with connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS daily_app_usage (
                        local_date TEXT NOT NULL,
                        app TEXT NOT NULL,
                        duration_millis INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (local_date, app),
                        CHECK (duration_millis >= 0)
                    )
                """)

    @staticmethod
    def _get_local_date(at=None):
        current = at or datetime.now().astimezone()
        current = current.astimezone()

        return current.date().isoformat()

    @staticmethod
    def _validate_duration(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("Usage duration must be a number.")

        if value < 0:
            raise ValueError("Usage duration cannot be negative.")

        return int(value)

    def replace_today_snapshot(
        self,
        youtube_millis,
        instagram_millis,
        at=None,
    ):
        """
        Replace today's cumulative Android usage snapshot.

        Calling this repeatedly will not add duplicate time.
        """

        local_date = self._get_local_date(at)

        usage = {
            "youtube": self._validate_duration(
                youtube_millis
            ),
            "instagram": self._validate_duration(
                instagram_millis
            ),
        }

        with closing(
            sqlite3.connect(self.database_path)
        ) as connection:

            with connection:
                for app, duration in usage.items():

                    connection.execute("""
                        INSERT INTO daily_app_usage (
                            local_date,
                            app,
                            duration_millis
                        )
                        VALUES (?, ?, ?)

                        ON CONFLICT(local_date, app)
                        DO UPDATE SET
                            duration_millis =
                                excluded.duration_millis
                    """, (
                        local_date,
                        app,
                        duration,
                    ))

        return self.get_daily_summary(at)

    def get_daily_summary(self, at=None):
        local_date = self._get_local_date(at)

        summary = {
            "date": local_date,
            "total_millis": 0,
            "apps": {
                "youtube": {"duration_millis": 0},
                "instagram": {"duration_millis": 0},
            },
        }

        with closing(
            sqlite3.connect(self.database_path)
        ) as connection:

            rows = connection.execute("""
                SELECT app, duration_millis
                FROM daily_app_usage
                WHERE local_date = ?
            """, (local_date,)).fetchall()

        for app, duration in rows:
            summary["apps"][app][
                "duration_millis"
            ] = duration

            summary["total_millis"] += duration

        summary["total_seconds"] = round(
            summary["total_millis"] / 1000,
            2,
        )

        return summary