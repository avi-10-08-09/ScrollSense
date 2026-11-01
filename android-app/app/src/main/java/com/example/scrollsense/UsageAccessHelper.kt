
package com.example.scrollsense

import android.app.AppOpsManager
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Settings
import java.util.Calendar

data class AppUsageSummary(
    val youtubeMillis: Long = 0L,
    val instagramMillis: Long = 0L
) {
    val totalMillis: Long
        get() = youtubeMillis + instagramMillis
}

class UsageAccessHelper(private val context: Context) {

    private val usageStatsManager =
        context.getSystemService(Context.USAGE_STATS_SERVICE)
                as UsageStatsManager

    companion object {
        const val YOUTUBE_PACKAGE = "com.google.android.youtube"
        const val INSTAGRAM_PACKAGE = "com.instagram.android"
    }

    fun hasUsageAccess(): Boolean {
        val appOps = context.getSystemService(Context.APP_OPS_SERVICE)
                as AppOpsManager

        val mode = if (Build.VERSION.SDK_INT >= 29) {
            appOps.unsafeCheckOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                android.os.Process.myUid(),
                context.packageName
            )
        } else {
            @Suppress("DEPRECATION")
            appOps.checkOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                android.os.Process.myUid(),
                context.packageName
            )
        }

        return mode == AppOpsManager.MODE_ALLOWED
    }

    fun openUsageAccessSettings() {
        val intent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS)
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
    }

    fun getTodayUsageSummary(): AppUsageSummary {
        if (!hasUsageAccess()) {
            return AppUsageSummary()
        }

        val now = System.currentTimeMillis()

        val calendar = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, 0)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
        }

        val startOfDay = calendar.timeInMillis

        val stats = usageStatsManager.queryUsageStats(
            UsageStatsManager.INTERVAL_DAILY,
            startOfDay,
            now
        )

        val youtubeTime = stats
            .filter { it.packageName == YOUTUBE_PACKAGE }
            .sumOf { it.totalTimeInForeground }

        val instagramTime = stats
            .filter { it.packageName == INSTAGRAM_PACKAGE }
            .sumOf { it.totalTimeInForeground }

        return AppUsageSummary(
            youtubeMillis = youtubeTime,
            instagramMillis = instagramTime
        )
    }

    fun getRecentActivityEvents(): List<String> {
        if (!hasUsageAccess()) {
            return listOf("Usage Access permission not granted.")
        }

        val endTime = System.currentTimeMillis()
        val startTime = endTime - 10 * 60 * 1000L

        val events = usageStatsManager.queryEvents(startTime, endTime)
        val event = UsageEvents.Event()
        val results = mutableListOf<String>()

        while (events.hasNextEvent()) {
            events.getNextEvent(event)

            val eventName = when (event.eventType) {
                UsageEvents.Event.ACTIVITY_RESUMED -> "ACTIVITY_RESUMED"
                UsageEvents.Event.ACTIVITY_PAUSED -> "ACTIVITY_PAUSED"
                UsageEvents.Event.MOVE_TO_FOREGROUND -> "MOVE_TO_FOREGROUND"
                UsageEvents.Event.MOVE_TO_BACKGROUND -> "MOVE_TO_BACKGROUND"
                else -> null
            }

            if (eventName != null) {
                results.add("${event.packageName} : $eventName")
            }
        }

        return results
    }
}
