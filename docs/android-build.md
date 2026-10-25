# Life Android 0.8.0

Package: `ru.vovan20.life`. Origin: `https://localhost`. Do not change either: updates must retain the signing certificate and WebView origin to retain local data.

## Build

Node 22+, JDK 21, Android SDK platform 36, build-tools 36.0.0.

```
npm ci
npm test
npm run sync
cd android
./gradlew assembleRelease
```

`www` is generated from the existing web UI. No website URL is loaded. The Android bundle disables service workers so an old web cache cannot override an installed update. Ordinary web deployment is unchanged. Android 7+ is supported by the selected Capacitor baseline.

## Signing and updates

The permanent signing key is private and is NEVER committed. Keep its backup: without it future APKs cannot replace this installation. Local signing uses `scripts/sign-apk.py` and environment variables `LIFE_KEYSTORE`, `LIFE_BUILD_TOOLS`, `LIFE_STORE_PASSWORD`, `LIFE_KEY_PASSWORD`, `LIFE_KEY_ALIAS=life`.

For automated releases, configure repository Actions secrets `LIFE_KEYSTORE_BASE64` (base64 of the SAME JKS used for the first APK), `LIFE_STORE_PASSWORD`, `LIFE_KEY_PASSWORD`. Do not create a new signing key in CI.

Increase package.json version, commit and push an `android-vX.Y.Z` tag matching that version. The workflow tests, bundles, builds, signs, verifies and publishes `Life-X.Y.Z.apk` and its SHA-256 checksum. Tag publishing fails closed when signing secrets are absent. Branch builds produce unsigned artifacts for build verification, not for installation.

The app's More → Updates checks `latest.json` in the separate `android-releases` branch on demand. Only versioned APK URLs in this repository are accepted. The first APK is stored on that branch; subsequent CI releases update this manifest after uploading a GitHub Release. It opens the APK download externally; the user downloads and confirms installation with Android. No silent/background installs and no remote JavaScript hot updates. The operating system checks the signing certificate. Offline use does not require GitHub.

## Data and limitations

This first APK retains existing localStorage storage WITHOUT encryption. Disable Android automatic backup; provide explicit JSON export through Filesystem + Share. Import uses the existing validated JSON importer. Installing the APK does not automatically import browser/PWA records: export there, import in Life.

Music is still the existing web player, with session-only file selection. Background playback, persistent music library, encrypted storage and biometrics are not implemented in this release. Demo records are still the existing mixed example set, not an isolated account.

Before real use: on a physical phone, add a record, close/reopen, export/import, try airplane mode. For an update test install a higher version signed by the SAME key over this version, then verify records and settings. Do not uninstall or clear app data during this test.

Work wallet accounting and data compatibility are documented in [work-wallet.md](work-wallet.md).
