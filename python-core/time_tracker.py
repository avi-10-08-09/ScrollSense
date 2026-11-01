from datetime import datetime, timedelta, time
from pathlib import Path
from contextlib import closing
import sqlite3
import tempfile


SUPPORTED_PLATFORMS = {
    "youtube_shorts",
    "instagram_reels",
}


class UsageTimer:
    """
    Tracks the time spent in supported short-video feeds.

    The Android or browser adapter will eventually tell this
    class when a supported feed becomes active or inactive.

    Uses monotonic time to measure elapsed duration, avoiding
    errors caused by ordinary system-clock adjustments.
    """

    def __init__(
        self,
        database_path=None,
        monotonic_clock=None,
        wall_clock=None,
    ):
        import time as time_module

        self.database_path = Path(
            database_path
            if database_path is not None
            else Path(__file__).resolve().parent
            / "scrollsense.sqlite3"
        )

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.monotonic_clock = (
            monotonic_clock or time_module.monotonic
        )

        self.wall_clock = (
            wall_clock
            or (lambda: datetime.now().astimezone())
        )

        # platform -> (monotonic start, wall-clock start)
        self.active_sessions = {}

        self._initialize_database()

    @staticmethod
    def _validate_platform(platform):
        if platform not in SUPPORTED_PLATFORMS:
            raise ValueError(
                f"Unsupported platform: {platform}"
            )

    @staticmethod
    def _as_local_datetime(value):
        if value.tzinfo is None:
            return value.astimezone()

        return value.astimezone()

    def _initialize_database(self):
        with closing(
            sqlite3.connect(self.database_path)
        ) as connection:
            with connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS daily_usage (
                        local_date TEXT NOT NULL,
                        platform TEXT NOT NULL,
                        duration_seconds REAL NOT NULL DEFAULT 0,
                        PRIMARY KEY (local_date, platform),
                        CHECK (duration_seconds >= 0)
                    )
                """)

    @staticmethod
    def _split_duration(start, end, elapsed):
        """
        Distribute elapsed time across local calendar days.

        Monotonic time determines the actual duration.
        Wall-clock timestamps determine how that duration
        is divided between dates.
        """

        if elapsed <= 0:
            return []

        wall_elapsed = (end - start).total_seconds()

        # If the system clock moved backwards, assign the
        # measured duration to the ending date.
        if wall_elapsed <= 0:
            return [
                (end.date().isoformat(), elapsed)
            ]

        segments = []
        cursor = start

        while cursor.date() < end.date():

            next_midnight = datetime.combine(
                cursor.date() + timedelta(days=1),
                time.min,
                tzinfo=cursor.tzinfo,
            )

            portion = (
                next_midnight - cursor
            ).total_seconds()

            if portion <= 0:
                break

            segments.append(
                (cursor.date().isoformat(), portion)
            )

            cursor = next_midnight

        remaining = (end - cursor).total_seconds()

        if remaining > 0:
            segments.append(
                (end.date().isoformat(), remaining)
            )

        total_wall_seconds = sum(
            seconds for _, seconds in segments
        )

        if total_wall_seconds <= 0:
            return [
                (end.date().isoformat(), elapsed)
            ]

        # Distribute monotonic duration proportionally.
        return [
            (
                local_date,
                elapsed * seconds / total_wall_seconds,
            )
            for local_date, seconds in segments
        ]

    def _save_duration(self, platform, start, end, elapsed):

        allocations = self._split_duration(
            start,
            end,
            elapsed,
        )

        if not allocations:
            return

        with closing(
            sqlite3.connect(self.database_path)
        ) as connection:

            with connection:
                for local_date, seconds in allocations:

                    connection.execute("""
                        INSERT INTO daily_usage (
                            local_date,
                            platform,
                            duration_seconds
                        )
                        VALUES (?, ?, ?)

                        ON CONFLICT(local_date, platform)
                        DO UPDATE SET
                            duration_seconds =
                                duration_seconds
                                + excluded.duration_seconds
                    """, (
                        local_date,
                        platform,
                        seconds,
                    ))

    def start_session(self, platform):
        """
        Start tracking the selected feed.

        Only one platform can be active at a time.
        Switching platforms automatically pauses the
        previously active platform.
        """

        self._validate_platform(platform)

        # Don't restart an already active session.
        if platform in self.active_sessions:
            return False

        # Pause any other active feed first.
        for active_platform in tuple(self.active_sessions):
            self.pause_session(active_platform)

        now_monotonic = self.monotonic_clock()

        now_wall = self._as_local_datetime(
            self.wall_clock()
        )

        self.active_sessions[platform] = (
            now_monotonic,
            now_wall,
        )

        return True

    def checkpoint_session(self, platform):
        """
        Save elapsed time without stopping the session.

        A future adapter can call this periodically to reduce
        data loss if the application closes unexpectedly.
        """

        self._validate_platform(platform)

        session = self.active_sessions.get(platform)

        if session is None:
            return 0.0

        start_monotonic, start_wall = session

        now_monotonic = self.monotonic_clock()

        now_wall = self._as_local_datetime(
            self.wall_clock()
        )

        elapsed = max(
            0.0,
            now_monotonic - start_monotonic,
        )

        self._save_duration(
            platform,
            start_wall,
            now_wall,
            elapsed,
        )

        # Begin the next measurement interval.
        self.active_sessions[platform] = (
            now_monotonic,
            now_wall,
        )

        return elapsed

    def pause_session(self, platform):
        """
        Save the final elapsed interval and stop the timer.
        """

        self._validate_platform(platform)

        if platform not in self.active_sessions:
            return 0.0

        elapsed = self.checkpoint_session(platform)

        self.active_sessions.pop(platform, None)

        return elapsed

    def get_daily_summary(self, at=None):
        """
        Return today's usage duration for both platforms.
        """

        current = self._as_local_datetime(
            at if at is not None else self.wall_clock()
        )

        local_date = current.date().isoformat()

        summary = {
            "date": local_date,
            "total_seconds": 0.0,
            "apps": {
                platform: {
                    "duration_seconds": 0.0
                }
                for platform in sorted(
                    SUPPORTED_PLATFORMS
                )
            },
        }

        with closing(
            sqlite3.connect(self.database_path)
        ) as connection:

            rows = connection.execute("""
                SELECT platform, duration_seconds
                FROM daily_usage
                WHERE local_date = ?
            """, (local_date,)).fetchall()

        for platform, seconds in rows:

            summary["apps"][platform][
                "duration_seconds"
            ] = seconds

            summary["total_seconds"] += seconds

        return summary


class FakeClock:
    """
    A controllable clock for repeatable tests.
    """

    def __init__(self, start):
        self.current_wall = start
        self.current_monotonic = 0.0

    def wall(self):
        return self.current_wall

    def monotonic(self):
        return self.current_monotonic

    def advance(self, seconds):
        self.current_monotonic += seconds

        self.current_wall += timedelta(
            seconds=seconds
        )


def run_self_test():

    with tempfile.TemporaryDirectory() as temp_dir:

        database = Path(temp_dir) / "test.sqlite3"

        clock = FakeClock(
            datetime.fromisoformat(
                "2026-10-30T23:59:50+05:30"
            )
        )

        timer = UsageTimer(
            database_path=database,
            monotonic_clock=clock.monotonic,
            wall_clock=clock.wall,
        )

        # Start YouTube tracking.
        assert timer.start_session(
            "youtube_shorts"
        ) is True

        # Don't create a second timer.
        assert timer.start_session(
            "youtube_shorts"
        ) is False

        # Cross midnight while tracking.
        clock.advance(15)

        # Save the first interval.
        assert timer.checkpoint_session(
            "youtube_shorts"
        ) == 15

        previous_day = timer.get_daily_summary(
            datetime.fromisoformat(
                "2026-10-30T23:59:55+05:30"
            )
        )

        next_day = timer.get_daily_summary()

        # 10 seconds belong to October 30.
        assert abs(
            previous_day["total_seconds"] - 10
        ) < 0.001

        # 5 seconds belong to October 31.
        assert abs(
            next_day["total_seconds"] - 5
        ) < 0.001

        # Pause YouTube tracking.
        clock.advance(10)

        timer.pause_session("youtube_shorts")

        # Track Instagram independently.
        assert timer.start_session(
            "instagram_reels"
        ) is True

        clock.advance(20)

        timer.pause_session("instagram_reels")

        final_summary = timer.get_daily_summary()

        assert abs(
            final_summary["apps"]["youtube_shorts"][
                "duration_seconds"
            ] - 15
        ) < 0.001

        assert abs(
            final_summary["apps"]["instagram_reels"][
                "duration_seconds"
            ] - 20
        ) < 0.001

        assert abs(
            final_summary["total_seconds"] - 35
        ) < 0.001

        # Pausing an inactive session is harmless.
        assert timer.pause_session(
            "youtube_shorts"
        ) == 0.0

        print("All time-tracking tests passed!")
        print("Previous day:", previous_day)
        print("Current day:", final_summary)


if __name__ == "__main__":
    run_self_test()