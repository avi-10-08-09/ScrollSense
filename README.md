# ScrollSense

**Make short-form scrolling visible.**

ScrollSense is an experimental digital-wellbeing application designed to help users become more aware of their short-form video consumption.

It aims to track how frequently users encounter short-form videos and how much time they spend using platforms such as YouTube Shorts and Instagram Reels.

The goal is simple: make mindless scrolling more visible and encourage healthier digital habits.

## Project Status

**Current stage: Prototype Development and Testing**

The initial Android application and Python integration are working. Feed-detection experiments have produced promising results on an Android emulator.

Individual video encounter counting and production-ready detection are still under development.

## Current Features

- Android application built with Kotlin and Jetpack Compose.
- Python tracking engine integrated using Chaquopy.
- SQLite database for persistent local storage.
- Daily YouTube and Instagram app-usage statistics.
- Experimental YouTube Shorts interface detection.
- Experimental Instagram Reels interface detection.
- Feed-session duration tracking.
- Dashboard displaying app usage and feed statistics.

## Technology Stack

| Component | Technology |
|---|---|
| Android application | Kotlin |
| User interface | Jetpack Compose |
| Core tracking logic | Python 3.13 |
| Python–Android integration | Chaquopy |
| Database | SQLite |
| Feed detection prototype | Android AccessibilityService |
| Android usage statistics | UsageStatsManager |
| Development environment | Android Studio |

## Architecture

ScrollSense uses a hybrid architecture.

- **Kotlin:** Handles Android functionality, permissions, accessibility events and the application interface.
- **Python:** Handles tracking logic, session timing, encounter management and daily summaries.
- **SQLite:** Stores tracking data locally.
- **Chaquopy:** Connects the Android application to the Python core.

## Current Detection Approach

The prototype investigates Android accessibility interface identifiers to distinguish supported short-form feeds.

Experimental YouTube Shorts signals include:
- `reel_recycler`
- `reel_player_page_container`

Experimental Instagram Reels signals include:
- `clips_viewer_view_pager`
- `clips_video_container`
- `clips_media_component`

These identifiers are implementation-dependent and may change between app versions.

The accessibility prototype currently inspects interface structure and component identifiers locally. It does not intentionally collect visible screen text.

## Important Limitations

ScrollSense is still experimental.

- Android app-usage statistics measure the entire YouTube and Instagram applications, not exclusively Shorts and Reels.
- Feed detection currently relies on experimental accessibility signals.
- Individual video transitions are not yet reliably identified or counted.
- Feed-session timing requires further testing, particularly when switching between applications.
- Detection accuracy may vary across devices and application versions.
- Google Play accessibility requirements and disclosures must be addressed before public release.

## Project Structure

```text
ScrollSense/
│
├── android-app/
│   ├── app/
│   └── gradle/
│
├── python-core/
│   ├── app_usage_store.py
│   ├── daily_dashboard.py
│   ├── scrollsense_bridge.py
│   ├── time_tracker.py
│   └── tracking_engine.py
│
├── docs/
│
├── browser-extension/
│
├── website/
│
├── tests/
│
├── .gitignore
├── README.md
└── ScrollSense_Project_Brief.pdf
```

## Roadmap

- [x] Initial project architecture.
- [x] Android application setup.
- [x] Python tracking engine.
- [x] SQLite integration.
- [x] Android–Python integration.
- [x] Daily app-usage tracking.
- [x] Experimental YouTube Shorts detection.
- [x] Experimental Instagram Reels detection.
- [x] Basic feed-session timing.
- [ ] Reliable app-exit detection.
- [ ] Individual Shorts and Reels encounter counting.
- [ ] More accurate feed-duration tracking.
- [ ] Improved dashboard and digital-wellbeing insights.
- [ ] Desktop browser extension.
- [ ] Project website.
- [ ] Testing across real Android devices.
- [ ] Google Play release preparation.

## Privacy

The current prototype stores usage statistics locally in an SQLite database.

Accessibility access is optional and must be explicitly enabled by the user. The prototype uses it to inspect supported application interface structures.

The project will continue to prioritize transparency, user consent and data minimization.

## Contributing

ScrollSense is currently a personal development project. Contributions, ideas and constructive feedback are welcome as the project evolves.

## License

A project license has not yet been selected.

---

**ScrollSense — Use technology to take control of your attention.**
