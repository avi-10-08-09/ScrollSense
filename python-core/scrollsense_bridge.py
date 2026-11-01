import sys
import json
from pathlib import Path

from daily_dashboard import ScrollSenseCore
from app_usage_store import AppUsageStore


_core = None
_app_usage_store = None
_database_path = None


def initialize_core(database_path):
    global _core, _app_usage_store, _database_path

    try:
        path = str(Path(database_path).resolve())

        # Preserve active sessions if already initialized.
        if _core is None or _database_path != path:
            _core = ScrollSenseCore(database_path=path)
            _app_usage_store = AppUsageStore(path)
            _database_path = path

        return json.dumps({
            "status": "success",
            "message": "ScrollSense core ready",
            "python_version": sys.version.split()[0]
        })

    except Exception as error:
        return json.dumps({
            "status": "error",
            "message": f"{type(error).__name__}: {error}"
        })


def set_feed_active_json(platform, active):
    if _core is None:
        return json.dumps({
            "status": "error",
            "message": "Python core is not initialized"
        })

    try:
        if active:
            started = _core.start_feed(platform)

            return json.dumps({
                "status": "success",
                "action": "started" if started else "already_active",
                "platform": platform
            })

        duration = _core.pause_feed(platform)

        return json.dumps({
            "status": "success",
            "action": "paused",
            "platform": platform,
            "duration_seconds": round(duration, 2)
        })

    except Exception as error:
        return json.dumps({
            "status": "error",
            "message": f"{type(error).__name__}: {error}"
        })


def checkpoint_active_feed_json():
    if _core is None:
        return json.dumps({
            "status": "error",
            "message": "Python core is not initialized"
        })

    try:
        active_platforms = list(
            _core.timer.active_sessions.keys()
        )

        for platform in active_platforms:
            _core.timer.checkpoint_session(platform)

        return json.dumps({
            "status": "success",
            "checkpointed": active_platforms
        })

    except Exception as error:
        return json.dumps({
            "status": "error",
            "message": f"{type(error).__name__}: {error}"
        })


def sync_android_usage_json(
    youtube_millis,
    instagram_millis
):
    if _app_usage_store is None:
        return json.dumps({
            "status": "error",
            "message": "Python core is not initialized"
        })

    try:
        summary = _app_usage_store.replace_today_snapshot(
            youtube_millis,
            instagram_millis
        )

        return json.dumps({
            "status": "success",
            "message": "Android app usage snapshot saved",
            "app_usage": summary
        })

    except Exception as error:
        return json.dumps({
            "status": "error",
            "message": f"{type(error).__name__}: {error}"
        })


def get_android_app_usage_json():
    if _app_usage_store is None:
        return json.dumps({
            "status": "error",
            "message": "Python core is not initialized"
        })

    try:
        return json.dumps(
            _app_usage_store.get_daily_summary()
        )

    except Exception as error:
        return json.dumps({
            "status": "error",
            "message": f"{type(error).__name__}: {error}"
        })


def get_daily_summary_json():
    if _core is None:
        return json.dumps({
            "status": "error",
            "message": "Python core is not initialized"
        })

    try:
        return json.dumps(
            _core.get_daily_summary()
        )

    except Exception as error:
        return json.dumps({
            "status": "error",
            "message": f"{type(error).__name__}: {error}"
        }) 	