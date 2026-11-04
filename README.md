# TradeMind AI OS

Flutter mobile client and FastAPI backend for **independent simulated trading**, quantitative research, AI explanations and graphic design. Initial implementation; see [verification and remaining work](docs/STATUS.md). No profitability claims and no real broker execution.

## Source layout

- `backend/app/quant.py`: causal indicators, signals, next-bar backtesting and walk-forward evaluation.
- `backend/app/research.py`: training-only parameter selection and historical calibration evidence.
- `backend/app/trading.py`: deterministic risk checks and decimal binary settlement.
- `backend/app/main.py`: authenticated REST/WebSocket routes, demo ledger, assistant, design projects.
- `backend/app/worker.py`: opt-in autonomous demo scheduling and Redis heartbeat.
- `backend/migrations`: versioned initial relational schema.
- `mobile/lib`: secure-token client, dashboard, research, chat and layer canvas.
- `docs/BROKER_REVIEW.md`: official broker integration investigation and restrictions.

## Backend setup

Use Python 3.12, PostgreSQL 16 and Redis 7. Docker Engine with Compose v2 is recommended. No secrets belong in source control.

```sh
cp .env.example .env
# Edit .env: set strong random POSTGRES_PASSWORD and JWT_SECRET.
# Configure provider keys only if your account and intended use are authorized.
docker compose up --build -d
curl http://localhost:8000/health
```

Compose runs `alembic upgrade head` before starting the API. API reference: `http://localhost:8000/docs`. Bind a TLS reverse proxy to the loopback API for mobile use; do not expose a plain HTTP API publicly. Use URL-safe database passwords or URL-encode the password in DATABASE_URL. Use an encrypted database volume, backups and production secret manager.

For local development:

```sh
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export JWT_SECRET='replace-with-at-least-32-random-characters'
# Optional local SQLite database; never use SQLite for concurrent trading.
alembic upgrade head
uvicorn app.main:app --reload
```

No keys means clear setup errors, not generated demo market data. Twelve Data requires subscription entitlements for each asset, interval, retention and redistribution use. User is responsible for licensing. Gemini handles explanations only. `OPENAI_IMAGE_API_KEY` enables image generation; `REMOVE_BG_API_KEY` enables remove.bg. All provider secrets stay on the server.

## Working API flow

1. Register through `POST /auth/register` with email and a 12-character minimum password. Keep tokens in secure storage. Send access token as `Authorization: Bearer ...`.
2. Fetch `/account`, `/market`, `/signals`, `/analysis/multi`.
3. Submit `POST /demo/orders` with symbol, BUY/SELL, stake, expiry and a unique idempotency key (16+ characters). Every record is marked SIMULATED.
4. Orders start pending. A fill uses the first observed minute open after 1 second assumed latency, plus 2bps adverse slippage. No past quote is invented as a current executable price. Expiry rounds up to a minute boundary. Missing bars leave trades unresolved.
5. `POST /demo/settle` fills and settles using observed historical candles. A win pays stake × 0.8; loss costs stake; ties refund stake; fee is stake × 0.001 in every outcome. Settlement is delayed until the corresponding candle is available. Provider data is independent of any broker's OTC feed.
6. Enable `/demo/automation` explicitly (`{"enabled":true,"symbol":"EUR/USD"}`). Worker defaults to $50 stakes and observes all risk controls. `/risk/stop` blocks new positions; settlement continues. `/worker/status` reports heartbeat health.
7. Research endpoints: `/research/backtest`, `/research/optimize`. Confidence is not a guaranteed probability. Live signals keep confidence null pending validated deployment.
8. `/assistant` explains supplied account context; it has no transaction execution tool.
9. `/design/projects`, `/design/generate`, `/design/remove-background` back the design studio.
10. `/real/orders` always returns 403.

Default limits: 1% of available balance per trade (including fee), 3% of initial balance daily loss budget, 10% peak drawdown, 1 simultaneous pending/open position, 3 consecutive losses, 10 entries per UTC day. Open risk is reserved in validation. No martingale. Emergency stop is persistent; there is deliberately no automatic resume.

## Tests

```sh
cd backend
python -m unittest discover -s tests -p 'test_quant.py' -v
pytest tests/test_api.py -v
```

API tests use isolated SQLite only for route behavior; production concurrency verification still needs PostgreSQL. For mobile, run `flutter analyze` and `flutter test`. See [STATUS](docs/STATUS.md) for what actually ran in this workspace.

## Flutter and Android APK

Required: current stable Flutter (Dart >=3.4), Android SDK/API requested by Flutter, platform tools, JDK 17, Android licenses. No Flutter/Android SDK was available here, so **no APK has been generated**.

Platform wrapper files are not generated in this workspace. Bootstrap with installed Flutter (review generated changes to preserve supplied application and signing settings):

```sh
cd mobile
flutter create --platforms=android,ios --org com.trademind --project-name trademind .
flutter pub get
flutter doctor -v
flutter doctor --android-licenses
flutter analyze
flutter test
flutter build apk --release --dart-define=API_URL=https://your-api.example.com
```

The client targets an Android emulator development URL by default; Android release disallows cleartext HTTP. Always supply a trusted HTTPS API URL. Use a development-only manifest override if testing a local HTTP emulator server. Do not disable release TLS protection.

For signing:

```sh
keytool -genkeypair -v -keystore /secure/path/trademind-release.jks -alias trademind -keyalg RSA -keysize 4096 -validity 10000
```

Create ignored `mobile/android/key.properties`:

```properties
storeFile=/secure/path/trademind-release.jks
storePassword=YOUR_STORE_PASSWORD
keyAlias=trademind
keyPassword=YOUR_KEY_PASSWORD
```

Keep the keystore and passwords outside git. Retain the supplied release signing configuration after bootstrapping. Build with the command above; output: `mobile/build/app/outputs/flutter-apk/app-release.apk`. Install with `adb install -r build/app/outputs/flutter-apk/app-release.apk`. Android biometric plugin uses FlutterFragmentActivity and USE_BIOMETRIC permission in the supplied configuration; preserve those settings after regeneration.

For iOS, use macOS/Xcode, generated `ios` project, valid signing team, photo-library usage strings and `NSFaceIDUsageDescription`, then `flutter build ipa --release --dart-define=API_URL=https://your-api.example.com`. Device verification and distribution signing remain required.

## Continuous integration

`.github/workflows/verify.yml` installs dependencies, runs domain/API tests, applies migrations to a PostgreSQL service, then bootstraps Flutter platform wrappers and runs analysis, widget tests and a debug APK build. It uploads the debug APK as a workflow artifact if the build succeeds. This workflow was authored but has not been observed running here. The debug artifact has an intentionally nonworking placeholder API URL; build your installation with your own HTTPS API.

## Deployment and recovery

Expose only a TLS reverse proxy, not PostgreSQL/Redis. Back up PostgreSQL and Redis volumes; test restores. Monitor `/health`, worker heartbeat, provider errors, rejected order audit events and unresolved pending positions. Worker retries each minute. Redis rate-limiter failure returns 503 instead of silently dropping controls. Disable automation and use the emergency stop while investigating stale data. Migrations must run as a one-shot deployment job before API replicas.

Do not treat this initial implementation as ready for financial production: finish the documented verification and release gates first.
