# CHANGELOG — TELEGRAM SOFTWARE STORE BOT

---

## [v1.0.0] — 2026-08-08 (Production Release)

### Added
- **User Center & Profile Dashboard**: `👤 Profilim` main menu item with aggregate downloads, favorites, ratings, reviews history and settings management.
- **Advanced Analytics & Intelligence Dashboard**: Admin `📊 Analytics` dashboard featuring KPI Comparisons, DAU/WAU/MAU metrics, Search Analytics (Zero-result queries), Conversion Rates, Star Ratings distribution, Notification delivery metrics, and System Health Alerts (`⚠️ Alerts`).
- **Software Version Management & Update Notifications**: `ProgramVersion` architecture with automated user update subscriptions and background rate-limited delivery worker.
- **Advanced Search & Multi-Filtering**: 6 Sort modes (Relevance, Popular, New, Rating, Name, Size) and filters (Category, OS, Architecture, License, Size, Rating, Free).
- **Performance & Scalability**: SQLite WAL mode, composite database indexes, thread-safe In-Memory TTL Cache Layer (`CacheService`), and Telegram 429 RetryAfter automated backoff.
- **Production Hardening & Reliability**: System states (`STARTING`, `READY`, `DEGRADED`, `STOPPING`, `STOPPED`), disk usage monitoring, full test suite (Stage 1 to 19), and production runbooks (`docs/`).

### Security
- User Data Isolation enforcement (User A cannot view or modify User B's private data).
- Strict callback ownership validation and admin role permission middleware.
- Environment secret protection and startup configuration validation.
