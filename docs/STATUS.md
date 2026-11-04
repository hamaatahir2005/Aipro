# Verification and release status

This is an initial implementation, **not a production-approved application**.

## Verified in this workspace
- Empty remote repository inspected using the GitHub connector.
- 12 standard-library quantitative/risk/research tests pass.
- Python sources compile with compileall.

## Blocked verification
- Python dependency installation failed because the execution sandbox could not reach its HTTP proxy. SQLAlchemy, psycopg, PyJWT, Redis, pytest are unavailable locally. FastAPI routes and migrations have not been runtime-tested here.
- Flutter, Dart, Android SDK and Gradle wrapper are absent. Dart analysis, widget tests, iOS compilation and APK compilation have not run.
- No provider credentials were configured. Twelve Data, Gemini, OpenAI image generation and remove.bg have not been exercised against live accounts.
- Docker services have not been launched.

## Remaining release work
- Run API integration tests on PostgreSQL and Redis, including concurrent order submission/refresh rotation and recovery from provider outages.
- Validate Flutter code with current stable Flutter, resolve analyzer/build findings, and test on Android/iOS devices. Generate missing platform boilerplate/wrapper using documented commands.
- Complete native iOS entitlement/signing setup. Android configuration is supplied but unbuilt.
- Biometric verification currently verifies device identity on request; it does not yet gate the entire app after backgrounding.
- English, Sorani and Arabic navigation/login strings and RTL exist; all remaining copy still requires translation and native review. Sorani currently uses Arabic Material built-in strings.
- UI charts currently show completed candles with refresh, not tick streaming, pinch/zoom, or interactive chart inspection. The backend WebSocket transports polled completed bars. Connect it to the Flutter chart and handle reconnects before calling the chart real-time.
- The demo equity chart and constrained risk-settings UI are implemented but unbuilt; strategy comparison visualizations still need expansion. Automation defaults off.
- Live signal confidence intentionally remains null. The research endpoint calculates historical calibration evidence; deploying a calibrated model requires an independently reviewed larger dataset and versioned artifact.
- Indicator definitions use rolling-window RSI/ATR and rolling directional-index ADX; they are not Wilder-smoothed versions.
- Backtest is directional next-bar research, distinct from the binary payout demo ledger. Do not compare their returns as equivalent products.
- Binary payout and fees are fixed server defaults in the API (configurable Position domain objects); add constrained settings endpoints before claiming user-configurable payouts.
- Design editor supports drag, text, layers, import, center crop, resize, brand colors, project save/load and exports. It lacks arbitrary crop handles, undo/redo and advanced typography. Templates are aspect-ratio presets rather than a curated template library. Imported images are center-cropped into square layers.
- Add object storage, asset retention/quotas and media scanning. The project JSON currently contains base64 image data with a 1MB saved-project ceiling. Generated asset metadata retention needs expansion.
- Persist/query market history with uniqueness and retention policies, rather than only requesting history from provider. Market-history schema exists but ingestion is not implemented.
- Domain modules are separated, but service/repository boundaries and typed relational strategy/trade tables need further refinement; several records currently use user-scoped JSON documents.
- Add account recovery, email verification, stronger login-specific throttles, secure backup rotation, secret manager integration, key rotation and audit-log retention/tamper protection.
- SQLite is local development only: PostgreSQL is mandatory for row-lock trading safety.
- Real-money execution stays disabled; authorization/compliance checks are not represented as completed.
