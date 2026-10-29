# ScrollSense

**Make short-form scrolling visible.**

ScrollSense is a proposed digital-wellbeing app that aims to help people become more aware of how many short-form videos they encounter and how much time they spend scrolling.

The goal is to make scrolling habits more visible, provide gentle reminders, and encourage more intentional use of short-video platforms.

## 📄 Project Brief

**[Read the ScrollSense Project Brief (PDF)](ScrollSense_Project_Brief.pdf)**

The brief explains the project concept, planned technologies, architecture, development roadmap, and technical challenges.

## ✨ Planned Features

- A live counter for supported short-video feeds.
- Daily scrolling time and estimated feed-item counts.
- Customizable usage limits and pause reminders.
- A daily dashboard with summaries.
- Local-first data storage, with cloud syncing considered for a future version.

## 🛠️ Planned Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core logic, counting rules, time calculations, and summaries |
| Kotlin | Android-specific integration and system features |
| JavaScript | PC browser extension and feed detection |
| HTML & CSS | Website and interface styling |
| SQLite | Local storage for usage records and summaries |
| GitHub | Source code, documentation, and releases |

The final architecture may evolve as the tracking approach is tested.

## 🎯 Initial Scope

The first feasibility prototype will investigate tracking for:

- YouTube Shorts on Android
- Instagram Reels on Android

The project will also explore a browser extension for the corresponding websites on PC.

## 🗺️ Development Roadmap

1. Define the requirements and architecture.
2. Set up the development environment.
3. Test the feasibility and accuracy of feed tracking.
4. Build the Android app and its dashboard.
5. Develop the PC browser extension.
6. Test, document, and improve the application.
7. Publish the source code and website.
8. Prepare an Android release for Google Play review.

## 🔒 Privacy and Accuracy

The initial design favors local data storage and transparent user permissions.

Exact counting of individual Reels and Shorts is a technical challenge. A feed item encountered is not necessarily a video watched completely. Accuracy, platform limitations, and applicable app-store policies will be evaluated during development.

## 📌 Project Status

**Current stage: Planning and architecture.**

The full app has not yet been implemented. Features and technical decisions will be validated through prototypes and testing.

## 🤝 Contributions and Feedback

Suggestions and feedback are welcome as the project develops. Contribution guidelines and licensing details will be added when the project is ready for collaboration.
