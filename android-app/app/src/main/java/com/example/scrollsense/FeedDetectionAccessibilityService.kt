package com.example.scrollsense

import android.accessibilityservice.AccessibilityService
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

import com.chaquo.python.Python
import com.chaquo.python.PyObject
import com.chaquo.python.android.AndroidPlatform

import java.util.concurrent.Executors

class FeedDetectionAccessibilityService : AccessibilityService() {

    companion object {
        private const val TAG = "ScrollSenseFeed"

        private const val YOUTUBE =
            "com.google.android.youtube"

        private const val INSTAGRAM =
            "com.instagram.android"

        private const val EXIT_GRACE_MS = 5000L
        private const val CHECKPOINT_INTERVAL_MS = 30000L
    }

    private val handler = Handler(Looper.getMainLooper())

    // Keep Python database operations sequential.
    private val pythonExecutor =
        Executors.newSingleThreadExecutor()

    private var activePlatform: String? = null

    private var pendingPause: Runnable? = null

    private val checkpointRunnable = object : Runnable {
        override fun run() {
            if (activePlatform == null) return

            pythonExecutor.execute {
                try {
                    val module = getPythonModule()

                    val result = module.callAttr(
                        "checkpoint_active_feed_json"
                    )

                    Log.d(TAG, "Checkpoint: $result")

                } catch (error: Exception) {
                    Log.e(TAG, "Checkpoint failed", error)
                }
            }

            handler.postDelayed(
                this,
                CHECKPOINT_INTERVAL_MS
            )
        }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()

        Log.i(TAG, "Accessibility service connected")

        // Initialize Python using the same database as MainActivity.
        pythonExecutor.execute {
            try {
                val module = getPythonModule()

                val databasePath = java.io.File(
                    applicationContext.filesDir,
                    "scrollsense.db"
                ).absolutePath

                val result = module.callAttr(
                    "initialize_core",
                    databasePath
                )

                Log.i(TAG, "Python initialized: $result")

            } catch (error: Exception) {
                Log.e(TAG, "Python initialization failed", error)
            }
        }
    }

    private fun getPythonModule(): PyObject {
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(applicationContext))
        }

        return Python.getInstance()
            .getModule("scrollsense_bridge")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        event ?: return

        val packageName = event.packageName?.toString() ?: return

        val platform = when (packageName) {
            YOUTUBE -> "youtube_shorts"
            INSTAGRAM -> "instagram_reels"
            else -> return
        }

        val root = rootInActiveWindow

        // An unavailable accessibility tree is uncertain.
        // Don't immediately stop the current session.
        if (root == null) {
            schedulePause()
            return
        }

        val visibleIds = linkedSetOf<String>()
        var inspectedNodes = 0

        fun inspectNode(
            node: AccessibilityNodeInfo?,
            depth: Int
        ) {
            if (
                node == null ||
                depth > 35 ||
                inspectedNodes >= 300
            ) {
                return
            }

            inspectedNodes++

            if (node.isVisibleToUser) {
                node.viewIdResourceName?.let {
                    visibleIds.add(it.substringAfterLast("/"))
                }
            }

            for (index in 0 until node.childCount) {
                inspectNode(node.getChild(index), depth + 1)
            }
        }

        try {
            inspectNode(root, 0)

            val isYoutubeShorts =
                platform == "youtube_shorts" &&
                        "reel_recycler" in visibleIds &&
                        "reel_player_page_container" in visibleIds

            val isInstagramReels =
                platform == "instagram_reels" &&
                        "clips_viewer_view_pager" in visibleIds &&
                        "clips_video_container" in visibleIds &&
                        (
                                "clips_media_component" in visibleIds ||
                                        "clips_single_media_component" in visibleIds
                                )

            val feedDetected =
                isYoutubeShorts || isInstagramReels

            if (feedDetected) {
                activateFeed(platform)
            } else {
                schedulePause()
            }

        } catch (error: Exception) {
            Log.e(TAG, "Feed inspection failed", error)
            schedulePause()
        }
    }

    private fun activateFeed(platform: String) {
        // Cancel a pending pause if the feed reappears.
        pendingPause?.let {
            handler.removeCallbacks(it)
        }
        pendingPause = null

        if (activePlatform == platform) return

        val previousPlatform = activePlatform
        activePlatform = platform

        pythonExecutor.execute {
            try {
                val module = getPythonModule()

                // Stop the previous feed if switching platforms.
                if (previousPlatform != null) {
                    module.callAttr(
                        "set_feed_active_json",
                        previousPlatform,
                        false
                    )
                }

                val result = module.callAttr(
                    "set_feed_active_json",
                    platform,
                    true
                )

                Log.i(
                    TAG,
                    "Feed session started: $platform, result=$result"
                )

            } catch (error: Exception) {
                Log.e(TAG, "Could not start feed session", error)
            }
        }

        if (previousPlatform == null) {
            handler.removeCallbacks(checkpointRunnable)

            handler.postDelayed(
                checkpointRunnable,
                CHECKPOINT_INTERVAL_MS
            )
        }
    }

    private fun schedulePause() {
        val platform = activePlatform ?: return

        // Don't create multiple pause timers.
        if (pendingPause != null) return

        val pauseRunnable = Runnable {
            if (activePlatform == platform) {
                activePlatform = null
                pendingPause = null

                pythonExecutor.execute {
                    try {
                        val module = getPythonModule()

                        val result = module.callAttr(
                            "set_feed_active_json",
                            platform,
                            false
                        )

                        Log.i(
                            TAG,
                            "Feed session paused: $platform, result=$result"
                        )

                    } catch (error: Exception) {
                        Log.e(TAG, "Could not pause feed session", error)
                    }
                }

                handler.removeCallbacks(checkpointRunnable)
            }
        }

        pendingPause = pauseRunnable

        handler.postDelayed(
            pauseRunnable,
            EXIT_GRACE_MS
        )
    }

    override fun onInterrupt() {
        Log.w(TAG, "Accessibility service interrupted")
    }

    override fun onDestroy() {
        val previousPlatform = activePlatform

        activePlatform = null

        pendingPause?.let {
            handler.removeCallbacks(it)
        }

        handler.removeCallbacks(checkpointRunnable)

        if (previousPlatform != null) {
            pythonExecutor.execute {
                try {
                    val module = getPythonModule()

                    module.callAttr(
                        "set_feed_active_json",
                        previousPlatform,
                        false
                    )

                } catch (error: Exception) {
                    Log.e(TAG, "Final pause failed", error)
                }
            }
        }

        pythonExecutor.shutdown()

        super.onDestroy()
    }
}