
from collections import deque
from contextlib import closing
from datetime import datetime
from pathlib import Path
import sqlite3
import tempfile


SUPPORTED_PLATFORMS = {
    "youtube_shorts",
    "instagram_reels",
}


class TrackingEngine:
    """
    Handles short-video encounter counting and daily storage.

    Actual feed detection will be handled separately by
    Android and browser adapters.
    """

    def __init__(self, database_path=None):
        if database_path is None:
            database_path = (
                Path(__file__).resolve().parent
                / "scrollsense.sqlite3"
            )

        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        # Current feed item is kept in memory only.
        self._last_item_key = {}

        # Prevent recently repeated technical events.
        self._recent_event_ids = {
            platform: deque(maxlen=256)
            for platform in SUPPORTED_PLATFORMS
        }

        self._seen_event_ids = {
            platform: set()
            for platform in SUPPORTED_PLATFORMS
        }

        self._initialize_database()

    def _validate_platform(self, platform):
        if platform not in SUPPORTED_PLATFORMS:
            raise ValueError(
                f"Unsupported platform: {platform}"
            )

    @staticmethod
    def _local_date(at=None):
        """
        Return the date in the computer's local timezone.
        A platform adapter can supply an event timestamp.
        """
        timestamp = at or datetime.now().astimezone()
        return timestamp.astimezone().date().isoformat()

    def _initialize_database(self):
        with closing(
            sqlite3.connect(self.database_path)
        ) as connection:
            with connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS daily_stats (
                        local_date TEXT NOT NULL,
                        platform TEXT NOT NULL,
                        encounter_count INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (local_date, platform),
                        CHECK (encounter_count >= 0)
                    )
                """)

    def _remember_event_id(self, platform, event_id):
        if event_id is None:
            return

        recent = self._recent_event_ids[platform]
        seen = self._seen_event_ids[platform]

        if event_id in seen:
            return

        # Remove the oldest event when the cache is full.
        if len(recent) == recent.maxlen:
            oldest_event = recent.popleft()
            seen.discard(oldest_event)

        recent.append(event_id)
        seen.add(event_id)

    def record_feed_item(
        self,
        platform,
        item_key,
        event_id=None,
        at=None
    ):
        """
        Record a newly encountered feed item.

        Returns:
            True  -> A new encounter was recorded.
            False -> A duplicate event/item was ignored.
        """

        self._validate_platform(platform)

        if not isinstance(item_key, str) or not item_key:
            raise ValueError(
                "item_key must be a non-empty string"
            )

        if event_id is not None:
            if not isinstance(event_id, str) or not event_id:
                raise ValueError(
                    "event_id must be a non-empty string"
                )

            if event_id in self._seen_event_ids[platform]:
                return False

        # Repeated UI updates for the currently active item
        # must not increase the counter.
        if self._last_item_key.get(platform) == item_key:
            self._remember_event_id(platform, event_id)
            return False

        # A -> B -> A counts all three encounters.
        self._last_item_key[platform] = item_key
        self._remember_event_id(platform, event_id)

        local_date = self._local_date(at)

        with closing(
            sqlite3.connect(self.database_path)
        ) as connection:
            with connection:
                connection.execute("""
                    INSERT INTO daily_stats (
                        local_date,
                        platform,
                        encounter_count
                    )
                    VALUES (?, ?, 1)

                    ON CONFLICT(local_date, platform)
                    DO UPDATE SET
                        encounter_count =
                            encounter_count + 1
                """, (local_date, platform))

        return True

    def reset_active_item(self, platform):
        """
        Forget the current feed item when a feed session ends.
        The next detected item can then be counted.
        """
        self._validate_platform(platform)
        self._last_item_key.pop(platform, None)

    def get_daily_summary(self, at=None):
        """
        Return today's encounter counts for each platform.
        Previous dates remain stored in SQLite.
        """

        local_date = self._local_date(at)

        summary = {
            "date": local_date,
            "total_encounters": 0,
            "apps": {
                platform: {
                    "encounters": 0
                }
                for platform in sorted(SUPPORTED_PLATFORMS)
            }
        }

        with closing(
            sqlite3.connect(self.database_path)
        ) as connection:

            rows = connection.execute("""
                SELECT platform, encounter_count
                FROM daily_stats
                WHERE local_date = ?
            """, (local_date,)).fetchall()

        for platform, count in rows:
            summary["apps"][platform]["encounters"] = count
            summary["total_encounters"] += count

        return summary


def run_self_test():
    """
    Test the counting rules using a temporary database.
    No real usage data is created.
    """

    with tempfile.TemporaryDirectory() as temp_dir:

        database = Path(temp_dir) / "test.sqlite3"
        tracker = TrackingEngine(database)

        # First encounter: count.
        assert tracker.record_feed_item(
            "youtube_shorts", "A", "event-1"
        ) is True

        # Same item: ignore duplicate.
        assert tracker.record_feed_item(
            "youtube_shorts", "A", "event-2"
        ) is False

        # New item: count.
        assert tracker.record_feed_item(
            "youtube_shorts", "B", "event-3"
        ) is True

        # Revisiting A: count again.
        assert tracker.record_feed_item(
            "youtube_shorts", "A", "event-4"
        ) is True

        # Repeated technical event: ignore.
        assert tracker.record_feed_item(
            "youtube_shorts", "C", "event-4"
        ) is False

        # Ending and reopening the feed resets active-item state.
        tracker.reset_active_item("youtube_shorts")

        assert tracker.record_feed_item(
            "youtube_shorts", "A", "event-5"
        ) is True

        # Instagram maintains its own separate count.
        assert tracker.record_feed_item(
            "instagram_reels", "R1", "event-6"
        ) is True

        summary = tracker.get_daily_summary()

        assert summary["total_encounters"] == 5

        assert (
            summary["apps"]["youtube_shorts"]["encounters"]
            == 4
        )

        assert (
            summary["apps"]["instagram_reels"]["encounters"]
            == 1
        )

        print("All tracking tests passed!")
        print("Daily summary:")
        print(summary)


if __name__ == "__main__":
    run_self_test()
