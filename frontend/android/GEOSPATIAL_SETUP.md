# RoomFinder Geospatial AR setup

The AR activity uses ARCore Geospatial mode and resolves a terrain anchor about 18 metres ahead on the walking route. The route coordinates are passed from the existing backend route response. ARCore renders the camera and the arrow; no Google Maps SDK key is used.

## Google Cloud credential

1. Open or create a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **ARCore API** for that project.
3. Create an API key and restrict it to the **ARCore API** and the Android application.
4. Use package name `com.danicalla04.roomfinder` and the SHA-1 signing certificate for the build you are testing. For a debug build, Android Studio's Gradle `signingReport` task shows the debug SHA-1.
5. Put the key in `android/local.properties`, which is ignored by Git:

   ```properties
   ARCORE_API_KEY=your-restricted-key
   ```

Do not put the key in Vue source, `capacitor.config.json`, or a committed file. The Android manifest receives it from Gradle's local manifest placeholder.

## Build and install

From `frontend` in PowerShell:

```powershell
npm run build:android
npx cap sync android
npx cap open android
```

In Android Studio, build and install the debug app on a supported phone. On first use, allow camera and precise location, accept the AR data-use notice, and test outdoors with an internet connection. The app checks Geospatial support at runtime and needs good GPS/heading accuracy before resolving the ground arrow.
