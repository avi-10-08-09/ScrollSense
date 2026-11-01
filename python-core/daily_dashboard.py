from datetime import datetime
from pathlib import Path
from contextlib import closing
import tempfile

from tracking_engine import (
    TrackingEngine,
    SUPPORTED_PLATFORMS,
)

from time_tracker import UsageTimer


class ScrollSenseCore:
    """
    Combines feed encounter tracking and usage timers
    into a single daily dashboard.
    """

    def __init__(
        self,
        database_path=None,
        monotonic_clock=None,
        wall_clock=None,
    ):
        if database_path is None:
            database_path = (
                Path(__file__).resolve().parent
                / "scrollsense.sqlite3"
            )

        self.tracker = TrackingEngine(database_path)

        self.timer = UsageTimer(
            database_path=database_path,
            monotonic_clock=monotonic_clock,
            wall_clock=wall_clock,
        )

    def record_feed_item(
        self,
        platform,
        item_key,
        event_id=None,
        at=None,
    ):
        return self.tracker.record_feed_item(
            platform,
            item_key,
            event_id,
            at,
        )

    def start_feed(self, platform):
        return self.timer.start_session(platform)

    def pause_feed(self, platform):
        return self.timer.pause_session(platform)

    def reset_active_item(self, platform):
        self.tracker.reset_active_item(platform)

    @staticmethod
    def format_duration(seconds):
        total_seconds = max(0, int(round(seconds)))

        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours:
            return f"{hours}h {minutes}m {seconds}s"

        if minutes:
            return f"{minutes}m {seconds}s"

        return f"{seconds}s"

    def get_daily_summary(self, at=None):
        """
        Return encounter counts and usage durations
        for today's supported platforms.

        Active timer sessions are checkpointed before
        reading today's totals.
        """

        # Update active timers so the dashboard includes
        # the time elapsed since their previous checkpoint.
        if at is None:
            for platform in tuple(
                self.timer.active_sessions
            ):
                self.timer.checkpoint_session(platform)

        counts = self.tracker.get_daily_summary(at)

        usage = self.timer.get_daily_summary(at)

        apps = {}

        total_encounters = 0
        total_seconds = 0.0

        for platform in sorted(SUPPORTED_PLATFORMS):

            encounters = (
                counts["apps"][platform]["encounters"]
            )

            duration = (
                usage["apps"][platform]["duration_seconds"]
            )

            apps[platform] = {
                "encounters": encounters,
                "duration_seconds": round(duration, 2),
                "duration_display": self.format_duration(
                    duration
                ),
            }

            total_encounters += encounters
            total_seconds += duration

        return {
            "date": counts["date"],
            "total_encounters": total_encounters,
            "total_seconds": round(total_seconds, 2),
            "total_duration": self.format_duration(
                total_seconds
            ),
            "apps": apps,
        }


class FakeClock:
    """Deterministic clock used only for testing."""

    def __init__(self, start):
        self.current_wall = start
        self.current_monotonic = 0.0

    def wall(self):
        return self.current_wall

    def monotonic(self):
        return self.current_monotonic

    def advance(self, seconds):
        from datetime import timedelta

        self.current_monotonic += seconds

        self.current_wall += timedelta(
            seconds=seconds
        )


def run_self_test():

    with tempfile.TemporaryDirectory() as temp_dir:

        database = Path(temp_dir) / "test.sqlite3"

        clock = FakeClock(
            datetime.now().astimezone()
        )

        core = ScrollSenseCore(
            database_path=database,
            monotonic_clock=clock.monotonic,
            wall_clock=clock.wall,
        )

        # Encounter counting tests.

        assert core.record_feed_item(
            "youtube_shorts",
            "video_A",
            "event_1",
        ) is True

        # Same item must not count twice.

        assert core.record_feed_item(
            "youtube_shorts",
            "video_A",
            "event_2",
        ) is False

        assert core.record_feed_item(
            "youtube_shorts",
            "video_B",
            "event_3",
        ) is True

        assert core.record_feed_item(
            "instagram_reels",
            "reel_A",
            "event_4",
        ) is True

        # Time tracking tests.

        core.start_feed("youtube_shorts")

        clock.advance(65)

        core.start_feed("instagram_reels")

        clock.advance(25)

        # Retrieve the combined dashboard.

        summary = core.get_daily_summary()

        assert summary["total_encounters"] == 3

        assert summary["total_seconds"] == 90.0

        assert (
            summary["apps"]["youtube_shorts"]["encounters"]
            == 2
        )

        assert (
            summary["apps"]["instagram_reels"]["encounters"]
            == 1
        )

        assert (
            summary["apps"]["youtube_shorts"]["duration_seconds"]
            == 65.0
        )

        assert (
            summary["apps"]["instagram_reels"]["duration_seconds"]
            == 25.0
        )

        assert summary["total_duration"] == "1m 30s"

        print("All dashboard integration tests passed!")

        print("\nCombined daily dashboard:")

        print(summary)


if __name__ == "__main__":
    run_self_test()