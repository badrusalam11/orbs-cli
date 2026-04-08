"""
Firefox Cold Start Benchmark Test

Use this to diagnose Firefox startup performance issues.
Run: pytest tests/test_firefox_coldstart.py -v -s

Expected results:
- Windows: ~5-6 seconds
- macOS (Intel): ~8-10 seconds  
- macOS (Apple Silicon with native Firefox): ~6-8 seconds
- macOS (Apple Silicon with Rosetta): ~25-35 seconds (SLOW!)

If you see >20 seconds on macOS, check:
1. geckodriver architecture matches your Mac (arm64 vs x86_64)
2. Firefox is native Apple Silicon version
3. Gatekeeper has scanned Firefox (first run is slow)
"""
import os
import sys
import time
import platform
import subprocess

import pytest


def get_system_info() -> dict:
    """Get system information for diagnosis."""
    info = {
        "os": sys.platform,
        "os_version": platform.version(),
        "python_version": sys.version,
        "architecture": platform.machine(),
    }
    
    # Check if running on Apple Silicon
    if sys.platform == "darwin":
        info["is_apple_silicon"] = platform.machine() == "arm64"
        
        # Check Firefox architecture
        try:
            result = subprocess.run(
                ["file", "/Applications/Firefox.app/Contents/MacOS/firefox"],
                capture_output=True, text=True
            )
            if "arm64" in result.stdout:
                info["firefox_arch"] = "arm64 (native)"
            elif "x86_64" in result.stdout:
                info["firefox_arch"] = "x86_64 (Rosetta)"
            else:
                info["firefox_arch"] = "unknown"
        except Exception:
            info["firefox_arch"] = "unable to detect"
        
        # Check geckodriver architecture
        try:
            result = subprocess.run(
                ["file", subprocess.run(["which", "geckodriver"], capture_output=True, text=True).stdout.strip()],
                capture_output=True, text=True
            )
            if "arm64" in result.stdout:
                info["geckodriver_arch"] = "arm64 (native)"
            elif "x86_64" in result.stdout:
                info["geckodriver_arch"] = "x86_64 (Rosetta)"
            else:
                info["geckodriver_arch"] = "unknown"
        except Exception:
            info["geckodriver_arch"] = "unable to detect"
    
    return info


class TestFirefoxColdStart:
    """Benchmark Firefox cold start time."""
    
    def test_print_system_info(self):
        """Print system information for diagnosis."""
        info = get_system_info()
        
        print("\n" + "=" * 60)
        print("SYSTEM INFORMATION")
        print("=" * 60)
        for key, value in info.items():
            print(f"  {key}: {value}")
        print("=" * 60)
        
        # Warn about Rosetta
        if info.get("is_apple_silicon"):
            if "x86_64" in info.get("geckodriver_arch", ""):
                print("\n⚠️  WARNING: geckodriver is x86_64 running under Rosetta!")
                print("   This causes SIGNIFICANT startup delays (20-30+ seconds)")
                print("   Download arm64 geckodriver from:")
                print("   https://github.com/mozilla/geckodriver/releases")
            
            if "x86_64" in info.get("firefox_arch", ""):
                print("\n⚠️  WARNING: Firefox is running under Rosetta!")
                print("   Download native Apple Silicon Firefox for better performance.")
    
    def test_firefox_cold_start_default(self):
        """Test Firefox cold start with default settings."""
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
        
        print("\n" + "-" * 40)
        print("Firefox Cold Start - DEFAULT (no optimizations)")
        print("-" * 40)
        
        options = Options()
        
        start = time.perf_counter()
        driver = webdriver.Firefox(options=options)
        cold_start = time.perf_counter() - start
        driver.quit()
        
        print(f"Cold start time: {cold_start:.2f} seconds")
        
        # Assessment
        if cold_start > 20:
            print("❌ VERY SLOW - Check Rosetta/architecture issues")
        elif cold_start > 10:
            print("⚠️  SLOW - Consider Firefox optimizations")
        elif cold_start > 6:
            print("✓ ACCEPTABLE")
        else:
            print("✅ FAST")
        
        return cold_start
    
    def test_firefox_cold_start_optimized(self):
        """Test Firefox cold start with orbs optimizations."""
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service
        
        print("\n" + "-" * 40)
        print("Firefox Cold Start - OPTIMIZED")
        print("-" * 40)
        
        # Set environment variables BEFORE creating options
        os.environ['MOZ_CRASHREPORTER_DISABLE'] = '1'
        os.environ['MOZ_DISABLE_CONTENT_SANDBOX'] = '1'
        os.environ['MOZ_LOG'] = ''
        
        options = Options()
        
        # Core optimizations
        options.set_preference("browser.startup.homepage_override.mstone", "ignore")
        options.set_preference("browser.startup.page", 0)
        options.set_preference("browser.shell.checkDefaultBrowser", False)
        options.set_preference("toolkit.telemetry.enabled", False)
        options.set_preference("dom.ipc.processCount", 2)
        options.set_preference("browser.cache.disk.enable", False)
        options.page_load_strategy = 'eager'
        options.add_argument('-no-remote')
        
        # macOS specific
        if sys.platform == "darwin":
            options.set_preference("layers.acceleration.disabled", True)
            options.set_preference("gfx.webrender.all", False)
        
        # Suppress geckodriver logs
        service = Service(log_output=os.devnull)
        
        start = time.perf_counter()
        driver = webdriver.Firefox(service=service, options=options)
        cold_start = time.perf_counter() - start
        driver.quit()
        
        print(f"Cold start time: {cold_start:.2f} seconds")
        
        return cold_start
    
    def test_compare_firefox_chrome(self):
        """Compare Firefox vs Chrome cold start."""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from selenium.webdriver.firefox.options import Options as FirefoxOptions
        from selenium.webdriver.firefox.service import Service as FirefoxService
        from selenium.webdriver.chrome.service import Service as ChromeService
        
        print("\n" + "=" * 60)
        print("BROWSER COLD START COMPARISON")
        print("=" * 60)
        
        # Chrome
        chrome_opts = ChromeOptions()
        chrome_opts.add_argument("--disable-extensions")
        chrome_opts.add_argument("--no-first-run")
        chrome_opts.page_load_strategy = 'eager'
        
        try:
            chrome_service = ChromeService(log_output=os.devnull)
            start = time.perf_counter()
            chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_opts)
            chrome_time = time.perf_counter() - start
            chrome_driver.quit()
        except Exception as e:
            chrome_time = None
            print(f"Chrome failed: {e}")
        
        # Firefox
        os.environ['MOZ_CRASHREPORTER_DISABLE'] = '1'
        firefox_opts = FirefoxOptions()
        firefox_opts.set_preference("browser.startup.page", 0)
        firefox_opts.set_preference("dom.ipc.processCount", 2)
        firefox_opts.page_load_strategy = 'eager'
        
        try:
            firefox_service = FirefoxService(log_output=os.devnull)
            start = time.perf_counter()
            firefox_driver = webdriver.Firefox(service=firefox_service, options=firefox_opts)
            firefox_time = time.perf_counter() - start
            firefox_driver.quit()
        except Exception as e:
            firefox_time = None
            print(f"Firefox failed: {e}")
        
        # Results
        print(f"\nChrome:  {chrome_time:.2f}s" if chrome_time else "\nChrome:  FAILED")
        print(f"Firefox: {firefox_time:.2f}s" if firefox_time else "Firefox: FAILED")
        
        if chrome_time and firefox_time:
            ratio = firefox_time / chrome_time
            print(f"\nFirefox is {ratio:.1f}x {'slower' if ratio > 1 else 'faster'} than Chrome")
            
            if ratio > 5:
                print("\n⚠️  Firefox is significantly slower!")
                print("   Possible causes:")
                print("   - Rosetta translation (Apple Silicon)")
                print("   - Gatekeeper scanning (first run)")
                print("   - Antivirus scanning")


class TestFirefoxWarmStart:
    """Test warm start (consecutive launches) performance."""
    
    def test_warm_start_improvement(self):
        """Test if consecutive Firefox launches are faster (warm cache)."""
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service
        
        os.environ['MOZ_CRASHREPORTER_DISABLE'] = '1'
        
        print("\n" + "=" * 60)
        print("WARM START TEST (3 consecutive launches)")
        print("=" * 60)
        
        times = []
        for i in range(3):
            options = Options()
            options.set_preference("browser.startup.page", 0)
            options.page_load_strategy = 'eager'
            
            service = Service(log_output=os.devnull)
            
            start = time.perf_counter()
            driver = webdriver.Firefox(service=service, options=options)
            elapsed = time.perf_counter() - start
            driver.quit()
            
            times.append(elapsed)
            print(f"  Launch {i+1}: {elapsed:.2f}s")
        
        print(f"\nCold start (1st): {times[0]:.2f}s")
        print(f"Warm start (avg 2-3): {sum(times[1:])/2:.2f}s")
        
        if times[0] > times[2] * 1.2:
            print("✅ Warm cache is helping!")
        else:
            print("ℹ️  No significant warm cache benefit")


if __name__ == "__main__":
    print("Running Firefox Cold Start Diagnostics...")
    
    # Print system info
    info = get_system_info()
    print("\nSystem Info:")
    for k, v in info.items():
        print(f"  {k}: {v}")
    
    # Run benchmark
    test = TestFirefoxColdStart()
    default_time = test.test_firefox_cold_start_default()
    optimized_time = test.test_firefox_cold_start_optimized()
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Default:   {default_time:.2f}s")
    print(f"Optimized: {optimized_time:.2f}s")
    if default_time > optimized_time:
        print(f"Improvement: {(1 - optimized_time/default_time)*100:.1f}%")
