# AXION Android Application

## Project Overview
AXION is an Android application that provides a WebView wrapper for the AXION Enterprise platform at https://axionenterprise.cloud.

## App Configuration
- **App Name**: AXION
- **Package**: com.axion.enterprise
- **Target URL**: https://axionenterprise.cloud
- **Platform**: Android
- **Minimum SDK**: 21 (Android 5.0)
- **Target SDK**: 33 (Android 13)

## Project Structure
```
android/
├── app/
│   ├── build.gradle                    # App-level build configuration
│   ├── src/main/
│   │   ├── AndroidManifest.xml        # App manifest
│   │   ├── java/com/axion/enterprise/
│   │   │   └── MainActivity.java       # Main activity with WebView
│   │   └── res/
│   │       ├── layout/
│   │       │   └── activity_main.xml  # Main layout with WebView
│   │       ├── values/
│   │       │   └── strings.xml        # App strings and metadata
│   │       └── mipmap-hdpi/
│   │           └── ic_launcher.png    # App icon
├── build.gradle                       # Project-level build configuration
├── gradle.properties                  # Gradle properties
├── settings.gradle                    # Gradle settings
└── gradlew                            # Gradle wrapper script
```

## Features
- WebView-based application loading AXION platform
- JavaScript enabled for full web functionality
- Back navigation support
- Responsive design with zoom controls
- Network permissions for internet access

## Build Instructions
1. Install Android Studio and SDK
2. Open the `android` directory in Android Studio
3. Sync Gradle files
4. Build and run the application

## Dependencies
- AndroidX AppCompat
- Material Design Components
- ConstraintLayout
- WebView (built-in)

## Permissions
- INTERNET: Required to load the web platform
- ACCESS_NETWORK_STATE: Check network connectivity
