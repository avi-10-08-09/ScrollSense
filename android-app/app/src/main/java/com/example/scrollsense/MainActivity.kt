package com.example.scrollsense

import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.lifecycleScope
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject





data class FeedStats(
    val totalEncounters: Int = 0,
    val totalDuration: String = "0s",
    val youtubeEncounters: Int = 0,
    val youtubeDuration: String = "0s",
    val instagramEncounters: Int = 0,
    val instagramDuration: String = "0s"
)

class MainActivity : ComponentActivity() {

    private lateinit var usageHelper: UsageAccessHelper

    private val accessState = mutableStateOf(false)
    private val summaryState = mutableStateOf(AppUsageSummary())
    private val pythonStatus = mutableStateOf("Starting Python...")
    private val feedStatsState = mutableStateOf(FeedStats())
    private val syncStatusState = mutableStateOf("Not synced yet")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        usageHelper = UsageAccessHelper(this)

        setContent {
            MaterialTheme {
                UsageDashboard(
                    hasAccess = accessState.value,
                    summary = summaryState.value,
                    feedStats = feedStatsState.value,
                    syncStatus = syncStatusState.value,
                    onOpenSettings = {
                        usageHelper.openUsageAccessSettings()
                    },
                    onRefresh = {
                        refreshDashboard()
                    },
                    onEnableFeedDetection = {
                        openAccessibilitySettings()
                    }
                )
            }
        }

    }

    override fun onResume() {
        super.onResume()

        if (::usageHelper.isInitialized) {
            refreshDashboard()
        }
    }

    private fun refreshDashboard() {
        val hasUsageAccess = usageHelper.hasUsageAccess()

        val currentSummary = if (hasUsageAccess) {
            usageHelper.getTodayUsageSummary()
        } else {
            AppUsageSummary()
        }

        accessState.value = hasUsageAccess
        summaryState.value = currentSummary

        lifecycleScope.launch(Dispatchers.IO) {
            var latestFeedStats = FeedStats()

            val resultMessage = try {

                // Start Python if it is not already running.
                if (!Python.isStarted()) {
                    Python.start(
                        AndroidPlatform(applicationContext)
                    )
                }

                val module = Python.getInstance()
                    .getModule("scrollsense_bridge")

                // Persistent database location.
                val databasePath = java.io.File(
                    applicationContext.filesDir,
                    "scrollsense.db"
                ).absolutePath

                // Initialize the Python core.
                val initResult = module.callAttr(
                    "initialize_core",
                    databasePath
                ).toString()

                // Replace today's Android usage snapshot.
                val syncResult = if (hasUsageAccess) {

                    module.callAttr(
                        "sync_android_usage_json",
                        currentSummary.youtubeMillis,
                        currentSummary.instagramMillis
                    ).toString()

                } else {
                    "Usage sync skipped: permission not granted. " +
                            "Previous saved data was preserved."
                }

                // Read saved Android app usage.
                val appUsage = module.callAttr(
                    "get_android_app_usage_json"
                ).toString()

                // Read Shorts/Reels feed-level tracking.
                val feedSummary = module.callAttr(
                    "get_daily_summary_json"
                ).toString()

                val feedJson = JSONObject(feedSummary)

                val appsJson = feedJson.optJSONObject("apps")
                    ?: JSONObject()

                val youtube = appsJson.optJSONObject("youtube_shorts")
                    ?: JSONObject()

                val instagram = appsJson.optJSONObject("instagram_reels")
                    ?: JSONObject()

                latestFeedStats = FeedStats(
                    totalEncounters = feedJson.optInt("total_encounters"),
                    totalDuration = feedJson.optString("total_duration", "0s"),

                    youtubeEncounters = youtube.optInt("encounters"),
                    youtubeDuration = youtube.optString(
                        "duration_display", "0s"
                    ),

                    instagramEncounters = instagram.optInt("encounters"),
                    instagramDuration = instagram.optString(
                        "duration_display", "0s"
                    )
                )

                """
                INITIALIZATION:
                $initResult

                ANDROID APP USAGE SYNC:
                $syncResult

                SAVED APP USAGE:
                $appUsage

                FEED-LEVEL SUMMARY:
                $feedSummary
            """.trimIndent()

            } catch (e: Exception) {
                "Python integration error: ${e.localizedMessage}"
            }

            withContext(Dispatchers.Main) {
                pythonStatus.value = resultMessage
                feedStatsState.value = latestFeedStats

                syncStatusState.value = if (hasUsageAccess) {
                    "Usage data synced"
                } else {
                    "Usage Access not granted"
                }
            }
        }
    }

    private fun openAccessibilitySettings() {
        startActivity(
            Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
        )
    }

}



@Composable
fun UsageDashboard(
    hasAccess: Boolean,
    summary: AppUsageSummary,
    feedStats: FeedStats,
    syncStatus: String,
    onOpenSettings: () -> Unit,
    onRefresh: () -> Unit,
    onEnableFeedDetection: () -> Unit
) {
    var showFeedDisclosure by remember {
        mutableStateOf(false)
    }

    var disclosureAcknowledged by remember {
        mutableStateOf(false)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp)
    ) {

        Text(
            text = "ScrollSense",
            style = MaterialTheme.typography.headlineLarge
        )

        Text(
            text = "Your daily scrolling overview",
            style = MaterialTheme.typography.bodyLarge
        )

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("TOTAL APP USAGE")

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = formatDuration(summary.totalMillis),
                    style = MaterialTheme.typography.headlineMedium
                )

                Text(
                    text = "Combined YouTube and Instagram usage today",
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }

        Text(
            text = "App breakdown",
            style = MaterialTheme.typography.titleLarge
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Card(modifier = Modifier.weight(1f)) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text("YouTube")
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = formatDuration(summary.youtubeMillis),
                        style = MaterialTheme.typography.titleLarge
                    )
                }
            }

            Card(modifier = Modifier.weight(1f)) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text("Instagram")
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = formatDuration(summary.instagramMillis),
                        style = MaterialTheme.typography.titleLarge
                    )
                }
            }
        }

        HorizontalDivider()

        Text(
            text = if (hasAccess) {
                "Usage Access: Granted"
            } else {
                "Usage Access: Not granted"
            }
        )

        Button(
            onClick = onRefresh,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Refresh Dashboard")
        }

        OutlinedButton(
            onClick = onOpenSettings,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Usage Access Settings")
        }

        OutlinedButton(
            onClick = {
                showFeedDisclosure = true
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Set Up Shorts/Reels Detection")
        }

        HorizontalDivider()

        Text(
            text = "Short-form Feed Activity",
            style = MaterialTheme.typography.titleLarge
        )

        Card(
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text(
                    text = "TOTAL ENCOUNTERS",
                    style = MaterialTheme.typography.labelMedium
                )

                Text(
                    text = feedStats.totalEncounters.toString(),
                    style = MaterialTheme.typography.headlineLarge
                )

                Text(
                    text = "Tracked feed duration: ${feedStats.totalDuration}"
                )
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Card(
                modifier = Modifier.weight(1f)
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text("YouTube Shorts")

                    Text(
                        text = feedStats.youtubeEncounters.toString(),
                        style = MaterialTheme.typography.headlineMedium
                    )

                    Text("Encounters")

                    Text(feedStats.youtubeDuration)
                }
            }

            Card(
                modifier = Modifier.weight(1f)
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text("Instagram Reels")

                    Text(
                        text = feedStats.instagramEncounters.toString(),
                        style = MaterialTheme.typography.headlineMedium
                    )

                    Text("Encounters")

                    Text(feedStats.instagramDuration)
                }
            }
        }

        Text(
            text = syncStatus,
            style = MaterialTheme.typography.bodySmall
        )

        Text(
            text = "App-level usage only. Shorts and Reels require " +
                    "separate feed-level detection.",
            style = MaterialTheme.typography.bodySmall
        )
    }

    if (showFeedDisclosure) {
        AlertDialog(
            onDismissRequest = {
                showFeedDisclosure = false
                disclosureAcknowledged = false
            },
            title = {
                Text("Feed Detection Permission")
            },
            text = {
                Column {
                    Text(
                        "ScrollSense uses Android Accessibility " +
                                "Service to inspect the interface structure " +
                                "of YouTube and Instagram while you use them."
                    )

                    Spacer(
                        modifier = Modifier.height(12.dp)
                    )

                    Text(
                        "The prototype reads UI component types and " +
                                "resource identifiers locally to investigate " +
                                "whether Shorts or Reels is open."
                    )

                    Spacer(
                        modifier = Modifier.height(12.dp)
                    )

                    Text(
                        "It does not read screen text or send this " +
                                "information to a server. Diagnostic identifiers " +
                                "are currently written to Android Logcat. " +
                                "Detection may not always be accurate."
                    )

                    Spacer(
                        modifier = Modifier.height(12.dp)
                    )

                    Row(
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Checkbox(
                            checked = disclosureAcknowledged,
                            onCheckedChange = {
                                disclosureAcknowledged = it
                            }
                        )

                        Text(
                            "I understand and want to continue."
                        )
                    }
                }
            },
            confirmButton = {
                TextButton(
                    enabled = disclosureAcknowledged,
                    onClick = {
                        showFeedDisclosure = false
                        disclosureAcknowledged = false
                        onEnableFeedDetection()
                    }
                ) {
                    Text("Continue")
                }
            },
            dismissButton = {
                TextButton(
                    onClick = {
                        showFeedDisclosure = false
                        disclosureAcknowledged = false
                    }
                ) {
                    Text("Cancel")
                }
            }
        )
    }
}

fun formatDuration(milliseconds: Long): String {
    val totalSeconds = milliseconds / 1000
    val hours = totalSeconds / 3600
    val minutes = (totalSeconds % 3600) / 60
    val seconds = totalSeconds % 60

    return when {
        hours > 0 -> "${hours}h ${minutes}m"
        minutes > 0 -> "${minutes}m ${seconds}s"
        else -> "${seconds}s"
    }
}