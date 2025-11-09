# Android Setup for Orbs CLI

This document describes the enhanced Android setup functionality in Orbs CLI.

## New Features

### Enhanced `orbs setup` Command

The `orbs setup` command now automatically installs and configures all necessary dependencies for Android mobile testing:

#### What gets installed:
- **Java JDK** (OpenJDK 11)
- **Android SDK Command Line Tools**
- **Android Platform Tools** (includes ADB)
- **Android Build Tools**
- **Android Platform** (API Level 34)
- **Android Emulator**
- **Node.js** and **npm** (if not already installed)
- **Appium** and **Appium UIAutomator2 Driver**

#### Platform Support:
- **Windows**: Uses winget for Java installation, automatic PATH configuration via Windows Registry
- **macOS**: Uses Homebrew for Java installation, automatic shell profile configuration
- **Linux**: Basic support with manual configuration guidance

#### Environment Variables:
The command automatically sets up:
- `ANDROID_HOME` environment variable
- Adds Android SDK tools to PATH
- Configures shell profiles (.bashrc/.zshrc) on Unix systems

### New `orbs check-android` Command

A diagnostic command to verify your Android development environment:

```bash
orbs check-android
```

This command checks:
- Java installation and version
- Android SDK location and components
- ADB availability and version
- Connected Android devices
- Node.js and npm versions
- Appium installation

## Usage

### Initial Setup
```bash
# Install all Android testing dependencies
orbs setup

# Check installation status
orbs check-android

# Select connected device for testing
orbs select-device
```

### Environment Locations

#### Windows
- Android SDK: `%USERPROFILE%\AppData\Local\Android\Sdk`
- Environment variables: Set via Windows Registry

#### macOS
- Android SDK: `~/Library/Android/sdk`
- Environment variables: Added to `~/.zshrc` or `~/.bashrc`

#### Linux
- Android SDK: `~/Android/Sdk`
- Environment variables: Added to `~/.bashrc`

## Manual Installation Notes

If automatic installation fails, you may need to:

1. **Install Java manually**: Download from [AdoptOpenJDK](https://adoptopenjdk.net/)
2. **Install Android SDK**: Download from [Android Developer](https://developer.android.com/studio)
3. **Set environment variables manually**:
   ```bash
   export ANDROID_HOME="path/to/android/sdk"
   export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools
   ```

## Troubleshooting

### Common Issues

1. **ADB not found after installation**
   - Restart your terminal/command prompt
   - Check PATH manually: `echo $PATH` (Unix) or `echo %PATH%` (Windows)

2. **Java installation fails**
   - On Windows: Ensure winget is available or install manually
   - On macOS: Ensure Homebrew is installed first

3. **Permission errors during setup**
   - On Unix systems: Ensure you have write permissions to home directory
   - On Windows: Run as administrator if needed

### Verification Commands

```bash
# Check if tools are in PATH
java -version
adb version
node --version
npm --version
appium --version

# Check Android SDK location
echo $ANDROID_HOME  # Unix
echo %ANDROID_HOME% # Windows
```

## Next Steps

After successful setup:

1. Connect an Android device or start an emulator
2. Run `orbs select-device` to configure device for testing
3. Create a new project with `orbs init my-project`
4. Start testing with `orbs run testcase_name --platform=android`