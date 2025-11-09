# Memastikan Semua Dependency Terinstall - Panduan Lengkap

## 🎯 Quick Start Commands

```bash
# 1. Install semua dependency sekaligus
orbs setup

# 2. Check status instalasi  
orbs doctor

# 3. Jika ada yang missing, check detail
orbs check-android
```

## 📋 Langkah-langkah Verifikasi

### 1. Gunakan Command `orbs doctor` (Recommended)
Command ini memberikan diagnosis lengkap dan saran perbaikan:

```bash
orbs doctor
```

**Output jika semua OK:**
```
🎉 All dependencies are installed and ready!

You can now:
• Create a new project: orbs init my-project
• Select device: orbs select-device  
• Run tests: orbs run testcase_name --platform=android
```

**Output jika ada yang missing:**
```
❌ Missing dependencies: Java, Appium

🔧 Recommended fixes:
1. Run 'orbs setup' for automatic installation
2. Manual installation (if automatic fails):
   • Java: Run 'brew install openjdk@11'
   • Appium: Run 'npm install -g appium'
```

### 2. Gunakan Command `orbs check-android`
Untuk detail status setiap component:

```bash
orbs check-android
```

Akan menunjukkan status untuk:
- ✅ Java + versi
- ✅ Android SDK location  
- ✅ Platform Tools (ADB)
- ✅ Build Tools
- ✅ Connected devices
- ✅ Node.js + versi
- ✅ npm + versi
- ✅ Appium + versi

### 3. Command Alias (Shortcut)
```bash
orbs check     # sama dengan orbs check-android
orbs status    # sama dengan orbs check-android  
orbs verify    # sama dengan orbs doctor
```

## 🔧 Perbaikan Manual (Jika Setup Gagal)

### Install Individual Dependencies

```bash
# Install Java saja
orbs install-java

# Install Node.js saja
orbs install-nodejs

# Install Appium saja (setelah Node.js)
orbs install-appium
```

### Manual Troubleshooting

#### Problem 1: Java "Unable to locate Java Runtime"
```bash
# macOS
brew install openjdk@11

# Windows  
winget install Microsoft.OpenJDK.11

# Atau download dari https://adoptopenjdk.net/
```

#### Problem 2: Android SDK Not Found
```bash
# Jalankan setup lagi (akan download & install SDK)
orbs setup

# Atau set ANDROID_HOME manual:
export ANDROID_HOME="/path/to/android/sdk"  # macOS/Linux
set ANDROID_HOME="C:\path\to\android\sdk"  # Windows
```

#### Problem 3: ADB Not Found
```bash
# Biasanya masalah PATH, restart terminal
# Atau install SDK tools manual:
orbs setup
```

#### Problem 4: Appium Not Found
```bash
# Install Node.js dulu
orbs install-nodejs

# Lalu install Appium
npm install -g appium
npm install -g appium-uiautomator2-driver
```

## 📱 Verifikasi Device Connection

Setelah semua dependency OK, pastikan device terhubung:

```bash
# Check connected devices
adb devices

# Atau via orbs
orbs select-device
```

## 🚀 Test Everything Works

```bash
# 1. Buat project test
orbs init test-project
cd test-project

# 2. Check device
orbs select-device

# 3. Run sample test
orbs run login --platform=android
```

## 💡 Tips Troubleshooting

### Environment Variables (macOS/Linux)
Jika ada masalah PATH, tambahkan ke shell profile:

```bash
# Edit ~/.zshrc atau ~/.bashrc
export ANDROID_HOME="$HOME/Library/Android/sdk"  # macOS
export ANDROID_HOME="$HOME/Android/Sdk"          # Linux
export PATH=$PATH:$ANDROID_HOME/tools
export PATH=$PATH:$ANDROID_HOME/platform-tools
```

### Windows PATH Issues
Jika command tidak ditemukan setelah install:
1. Restart Command Prompt/PowerShell
2. Restart VS Code/Terminal
3. Check PATH di Environment Variables

### Permission Issues (macOS/Linux)
Jika ada error permission:
```bash
# Fix npm permissions
sudo chown -R $(whoami) ~/.npm
sudo chown -R $(whoami) /usr/local/lib/node_modules
```

## 🔄 Re-verification Workflow

Setelah perbaikan manual:

```bash
# 1. Restart terminal
# 2. Check lagi
orbs doctor

# 3. Jika masih ada issue
orbs check-android

# 4. Test dengan device
orbs select-device
```

## ⚡ Quick Commands Summary

| Command | Fungsi |
|---------|--------|
| `orbs setup` | Install semua dependency |
| `orbs doctor` | Diagnosis lengkap + saran |
| `orbs check-android` | Status detail semua component |
| `orbs install-java` | Install Java saja |
| `orbs install-nodejs` | Install Node.js saja |
| `orbs install-appium` | Install Appium saja |
| `orbs select-device` | Pilih device untuk testing |

## ✅ Final Checklist

Semua dependency OK jika:
- [ ] `orbs doctor` shows "All dependencies are installed and ready!"
- [ ] `orbs check-android` shows all ✅ green checkmarks
- [ ] `orbs select-device` shows connected Android devices
- [ ] Bisa create project: `orbs init test`
- [ ] Bisa run test: `orbs run testcase --platform=android`

Jika semua checklist ✅, environment Anda siap untuk Android testing! 🎉