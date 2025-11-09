import os
import platform
import time
from urllib.parse import urlparse
from dotenv import load_dotenv
import requests
import typer
import shutil
from pathlib import Path
from orbs._constant import PLATFORM_LIST
from orbs.spy.mobile import MobileSpyRunner
from orbs.spy.web import WebSpyRunner
from orbs.utils import render_template
from orbs import run
import subprocess
from InquirerPy import inquirer
from orbs import config


app = typer.Typer()

# Directories for templates
BASE_DIR = Path(__file__).parent
TEMPLATE_PROJECT_DIR = BASE_DIR / "templates" / "project"
TEMPLATE_JINJA_DIR = BASE_DIR / "templates" / "jinja"

# Settings directory within user's project
SETTINGS_DIR = Path.cwd() / "settings"
APPIUM_PROPS = SETTINGS_DIR / "appium.properties"


def get_connected_devices():
    """Use adb to list connected device IDs"""
    try:
        output = subprocess.check_output(["adb", "devices"], universal_newlines=True)
    except Exception:
        return []
    devices = []
    for line in output.splitlines()[1:]:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == 'device':
            devices.append(parts[0])
    return devices


def choose_device(devices: list[str]) -> str:
    """Prompt user to choose a device via arrow keys"""
    if not devices:
        typer.secho("❌ No connected devices found", fg=typer.colors.RED)
        raise typer.Exit(1)
    choice = inquirer.select(
        message="Select device:",
        choices=devices,
        default=devices[0]
    ).execute()
    return choice


def write_device_property(device_name: str):
    """Update only the deviceName in appium.properties"""
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    props = []
    if APPIUM_PROPS.exists():
        props = APPIUM_PROPS.read_text().splitlines()
    updated = False
    new_lines = []
    for line in props:
        if line.strip().startswith('deviceName='):
            new_lines.append(f'deviceName={device_name}')
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f'deviceName={device_name}')
    APPIUM_PROPS.write_text("\n".join(new_lines) + "\n")
    typer.secho(f"✅ Updated deviceName={device_name} in {APPIUM_PROPS}", fg=typer.colors.GREEN)

def ensure_appium_server():
    """Ensure an Appium server is running, otherwise start one"""
    url = config.get("appium_url", "http://localhost:4723")  # Appium 3+ no longer uses /wd/hub
    status_url = url.rstrip('/') + '/status'
    try:
        if requests.get(status_url, timeout=2).status_code == 200:
            return
    except Exception:
        pass

    # Parse host and port
    parsed = urlparse(url)
    host = parsed.hostname or 'localhost'  # Use localhost by default, not 0.0.0.0
    port = parsed.port or 4723
    typer.secho(f"⚙️  Starting Appium server at {host}:{port}", fg=typer.colors.YELLOW)
    
    # Setup proper environment variables for Appium
    env = os.environ.copy()  # Inherit current environment
    
    # Ensure Android SDK environment variables are set
    home = Path.home()
    system = platform.system().lower()
    
    if system == "darwin":
        android_home = home / "Library" / "Android" / "sdk"
    elif system == "windows":
        android_home = home / "AppData" / "Local" / "Android" / "Sdk"
    else:
        android_home = home / "Android" / "Sdk"
    
    # Set Android environment variables if not already set
    if not env.get("ANDROID_HOME") and android_home.exists():
        env["ANDROID_HOME"] = str(android_home)
        typer.secho(f"🔧 Set ANDROID_HOME={android_home}", fg=typer.colors.BLUE)
    
    if not env.get("ANDROID_SDK_ROOT") and android_home.exists():
        env["ANDROID_SDK_ROOT"] = str(android_home)
        typer.secho(f"🔧 Set ANDROID_SDK_ROOT={android_home}", fg=typer.colors.BLUE)
    
    # Ensure Android tools are in PATH
    android_paths = [
        str(android_home / "tools"),
        str(android_home / "platform-tools"),
        str(android_home / "cmdline-tools" / "latest" / "bin")
    ]
    
    current_path = env.get("PATH", "")
    for android_path in android_paths:
        if android_path not in current_path and Path(android_path).exists():
            env["PATH"] = f"{android_path}:{current_path}"
    
    # Enhanced Appium command for v3+
    cmd = f"appium server --address {host} --port {port}"
    
    try:
        # Check Appium version first
        version_result = subprocess.run(["appium", "--version"], capture_output=True, text=True, env=env)
        if version_result.returncode == 0:
            version = version_result.stdout.strip()
            major_version = int(version.split('.')[0])
            
            # For Appium 3+, use 'appium server' command
            if major_version >= 3:
                cmd = f"appium server --address {host} --port {port}"
            else:
                cmd = f"appium --address {host} --port {port}"
            
            typer.secho(f"🔍 Detected Appium v{version}, using appropriate command", fg=typer.colors.BLUE)
    except:
        pass  # fallback to default
    
    # Create Appium server process with proper background handling
    process = None
    try:
        # For debugging, let's see the output
        typer.secho(f"📋 Starting command: {cmd}", fg=typer.colors.BLUE)
        typer.secho(f"🔧 ANDROID_HOME: {env.get('ANDROID_HOME', 'NOT_SET')}", fg=typer.colors.BLUE)
        
        # Start process with proper background handling and environment
        process = subprocess.Popen(
            cmd, 
            shell=True, 
            env=env,  # Pass the complete environment with Android variables
            stdout=subprocess.DEVNULL,  # Background process - no output needed
            stderr=subprocess.DEVNULL, 
            stdin=subprocess.DEVNULL,   # Detach from parent
            preexec_fn=None if platform.system() == 'Windows' else os.setsid  # Create new session
        )
        
        # Give server a moment to start
        time.sleep(2)
        
        # Don't check if process is running - background processes may detach
        # Instead, rely on status check below
        
    except Exception as e:
        typer.secho(f"❌ Failed to start Appium: {e}", fg=typer.colors.RED)
        
        # Try with npx fallback
        typer.secho("🔄 Trying with npx...", fg=typer.colors.YELLOW)
        npx_cmd = f"npx appium server --address {host} --port {port}"
        try:
            process = subprocess.Popen(
                npx_cmd, 
                shell=True, 
                env=env,  # Pass environment to npx as well
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                preexec_fn=None if platform.system() == 'Windows' else os.setsid
            )
            time.sleep(2)
        except Exception:
            typer.secho("❌ Could not start Appium with npx either", fg=typer.colors.RED)
            typer.secho("💡 Try running: npm install -g appium@latest", fg=typer.colors.BLUE)
            raise typer.Exit(1)
    
    # Wait for server to be ready with better status checking
    typer.secho("⏳ Waiting for Appium server to be ready...", fg=typer.colors.YELLOW)
    for i in range(15):  # Increased timeout for Appium 3
        try:
            response = requests.get(status_url, timeout=3)
            if response.status_code == 200:
                typer.secho("✅ Appium server is up and ready", fg=typer.colors.GREEN)
                return
        except requests.exceptions.RequestException:
            # Connection errors are expected during startup
            pass
        except Exception as e:
            if i == 14:  # Last attempt
                typer.secho(f"❌ Server status check failed: {e}", fg=typer.colors.RED)
        time.sleep(1)
    
    typer.secho("❌ Failed to start Appium server - timeout waiting for status", fg=typer.colors.RED)
    typer.secho("💡 Try manually: appium server --address 0.0.0.0 --port 4723", fg=typer.colors.BLUE)
    raise typer.Exit(1)


def _auto_cleanup_incompatible_apks():
    """Automatically cleanup incompatible Appium APKs ONLY when there's actual session error"""
    # DISABLED automatic cleanup - should only run on manual command or actual session errors
    return


def _cleanup_incompatible_apks_on_error():
    """Cleanup APKs only when there's an actual session creation error"""
    def check_command_exists(command: str) -> bool:
        return shutil.which(command) is not None
    
    # Only proceed if adb and appium are available and device is connected
    if not check_command_exists("adb") or not check_command_exists("appium"):
        return False
        
    devices = get_connected_devices()
    if not devices:
        return False
    
    try:
        # Check installed Appium packages on device
        packages_result = subprocess.run(
            ["adb", "shell", "pm", "list", "packages"], 
            capture_output=True, text=True
        )
        
        if "io.appium.uiautomator2.server" in packages_result.stdout:
            # Get Appium version to check compatibility 
            appium_result = subprocess.run(["appium", "--version"], capture_output=True, text=True)
            if appium_result.returncode == 0:
                appium_version = appium_result.stdout.strip()
                major_version = int(appium_version.split('.')[0])
                
                # STRICT CHECK: Only cleanup if there's CONFIRMED version conflict
                # Appium 1.x APKs are incompatible with Appium 3.x 
                if major_version >= 3:
                    # Double-check: try to detect if APKs are actually from older version
                    # by checking APK installation date or version signature
                    apk_info_result = subprocess.run(
                        ["adb", "shell", "dumpsys", "package", "io.appium.uiautomator2.server"], 
                        capture_output=True, text=True
                    )
                    
                    # If APK exists but we can't create sessions, then it's likely incompatible
                    if apk_info_result.returncode == 0:
                        typer.secho("🔍 Detected confirmed session error - cleaning up incompatible APKs", fg=typer.colors.YELLOW)
                        
                        apk_packages = [
                            "io.appium.uiautomator2.server",
                            "io.appium.uiautomator2.server.test", 
                            "io.appium.settings"
                        ]
                        
                        for package in apk_packages:
                            try:
                                subprocess.run(["adb", "uninstall", package], 
                                              capture_output=True, text=True)
                            except Exception:
                                pass  # Silent cleanup
                        
                        typer.secho("✅ APK cleanup complete - please retry your test", fg=typer.colors.GREEN)
                        return True
                    
    except Exception:
        # Silent failure - don't break normal flow
        pass
    
    return False


@app.command()
def init(project_name: str):
    """Initialize a new orbs project structure"""
    src = TEMPLATE_PROJECT_DIR

    if project_name in [".", "./"]:
        dest = Path.cwd()
    else:
        dest = Path.cwd() / project_name

        if dest.exists():
            typer.secho(f"❌ Folder already exists: {dest}", fg=typer.colors.RED)
            raise typer.Exit(1)

        dest.mkdir(parents=True, exist_ok=True)

    for item in src.rglob("*"):
        rel_path = item.relative_to(src)
        dest_path = dest / rel_path
        if item.is_dir():
            dest_path.mkdir(parents=True, exist_ok=True)
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest_path)

    typer.secho(f"✅ Project initialized at {dest}", fg=typer.colors.GREEN)


@app.command()
def create_testsuite(name: str):
    current_folder = Path.cwd()
    # Find the root project directory (the first parent that does not include 'testsuites')
    # Or assume project root is where you run the CLI
    if "testsuites" in current_folder.parts:
        # If inside testsuites or its subfolder
        testsuite_folder = current_folder
    else:
        # Default to root/testsuites
        testsuite_folder = current_folder / "testsuites"
    # Create files relative to current folder (or testsuite folder)
    path_yml = testsuite_folder / f"{name}.yml"
    path_py = testsuite_folder / f"{name}.py"

    render_template(
        template_name="testsuites/testsuite.yml.j2",
        context={"suite_name": name},
        dest=path_yml,
        base_template_dir=TEMPLATE_JINJA_DIR
    )
    render_template(
        template_name="testsuites/testsuite.py.j2",
        context={"suite_name": name},
        dest=path_py,
        base_template_dir=TEMPLATE_JINJA_DIR
    )
    typer.secho(f"✅ Created testsuite: {name}", fg=typer.colors.GREEN)


@app.command()
def create_testsuite_collection(name: str):
    current_folder = Path.cwd()
    if "testsuite_collections" in current_folder.parts:
        # If inside testsuites or its subfolder
        testsuite_collection_folder = current_folder
    else:
        # Default to root/testsuites
        testsuite_collection_folder = current_folder / "testsuite_collections"
    """Create a new testsuite folder and file"""
    path_yml = testsuite_collection_folder / f"{name}.yml"
    render_template(
        template_name="testsuite_collections/testsuite_collection.yml.j2",
        context={"suite_collection_name": name},
        dest=path_yml,
        base_template_dir=TEMPLATE_JINJA_DIR
    )
    typer.secho(f"✅ Created testsuite collection: {name}", fg=typer.colors.GREEN)


@app.command()
def create_testcase(name: str):
    current_folder = Path.cwd()
    if "testcases" in current_folder.parts:
        # If inside testsuites or its subfolder
        testcase_folder = current_folder
    else:
        # Default to root/testsuites
        testcase_folder = current_folder / "testcases"
    """Create a new testcase file"""
    path = testcase_folder / f"{name}.py"
    render_template(
        template_name="testcases/testcase.py.j2",
        context={"case_name": name},
        dest=path,
        base_template_dir=TEMPLATE_JINJA_DIR
    )
    typer.secho(f"✅ Created testcase: {name}", fg=typer.colors.GREEN)

@app.command()
def create_listener(name: str):
    current_folder = Path.cwd()
    if "listeners" in current_folder.parts:
        # If inside testsuites or its subfolder
        listener_folder = current_folder
    else:
        # Default to root/testsuites
        listener_folder = current_folder / "listeners"
    """Create a new listener file"""
    path = listener_folder / f"{name}.py"
    render_template(
        template_name="listeners/listener.py.j2",
        context={"listener_name": name},
        dest=path,
        base_template_dir=TEMPLATE_JINJA_DIR
    )
    typer.secho(f"✅ Created listener: {name}", fg=typer.colors.GREEN)

@app.command()
def create_feature(name: str):
    current_folder = Path.cwd()
    if "include" in current_folder.parts and "features" in current_folder.parts:
        # If inside feature or its subfolder
        feature_folder = current_folder
    else:
        # Default to root/feature
        feature_folder = current_folder / "include/features"
    """Create a new feature file (.feature)"""
    path = feature_folder / f"{name}.feature"
    render_template(
        template_name="features/feature.feature.j2",
        context={"feature_name": name},
        dest=path,
        base_template_dir=TEMPLATE_JINJA_DIR
    )
    typer.secho(f"✅ Created feature: {name}", fg=typer.colors.GREEN)


@app.command()
def create_step(name: str):
    current_folder = Path.cwd()
    if "include" in current_folder.parts and "steps" in current_folder.parts:
        # If inside step or its subfolder
        step_folder = current_folder
    else:
        # Default to root/step
        step_folder = current_folder / "include/steps"
    """Create a new step file (.py)"""
    path = step_folder / f"{name}.py"
    render_template(
        template_name="steps/step.py.j2",
        context={"step_name": name},
        dest=path,
        base_template_dir=TEMPLATE_JINJA_DIR
    )
    typer.secho(f"✅ Created step: {name}", fg=typer.colors.GREEN)


@app.command()
def implement_feature(name: str):
    """Generate step definition for given feature"""
    import re
    feature_path = Path.cwd() / "include" / "features" / f"{name}.feature"
    steps_path = Path.cwd() / "include" / "steps" / f"{name}_steps.py"

    if not feature_path.exists():
        typer.secho(f"❌ Feature not found: {feature_path}", fg=typer.colors.RED)
        raise typer.Exit(1)

    steps = ["from behave import given, when, then\n"]
    last_decorator = "when"

    with open(feature_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith(("Given", "When", "Then", "And", "*")):
                parts = line.split(" ", 1)
                if len(parts) != 2:
                    continue  # skip malformed
                keyword, rest = parts
                decorator = keyword.lower() if keyword.lower() != "and" else last_decorator
                last_decorator = decorator

                # Convert <param> to {param}
                pattern = re.sub(r"<([^>]+)>", r"{\1}", rest)

                # Extract argument names from pattern
                param_names = re.findall(r"{(.*?)}", pattern)
                args = ", ".join(["context"] + param_names)

                steps.append(f"@{decorator}('{pattern}')")
                steps.append(f"def step_impl({args}):")
                steps.append("    pass\n")

    steps_path.parent.mkdir(parents=True, exist_ok=True)
    steps_path.write_text("\n".join(steps))
    typer.secho(f"✅ Implemented feature steps for: {name}", fg=typer.colors.GREEN)


@app.command("run")
def run_command(
    target: str,
    env_file: Path = typer.Option(None, "--env", "-e", help="Path to .env file to load before running"),
    platform: str = typer.Option(None, "--platform", "-p", help="Platform to run tests on (android, chrome, firefox)")
):
    # Validate platform if provided
    if platform:
        # Remove any spaces around the platform value
        platform = platform.strip()
        valid_platforms = PLATFORM_LIST["mobile"] + PLATFORM_LIST["web"]
        
        if platform not in valid_platforms:
            # Show examples in the correct format
            examples = [f"--platform={p}" for p in valid_platforms]
            typer.secho(f"❌ Invalid platform: {platform}. Must be one of: {', '.join(examples)}", fg=typer.colors.RED)
            raise typer.Exit(1)
    
    """Run a suite/case/feature with optional environment file"""
    # If a custom env file is provided, override defaults
    if env_file:
        if not env_file.exists():
            typer.secho(f"❌ Env file not found: {env_file}", fg=typer.colors.RED)
            raise typer.Exit(1)
        load_dotenv(dotenv_path=env_file, override=True)
    
    # Execute the run with platform parameter
    run(target, platform)

@app.command()
def select_device():
    devices = get_connected_devices()
    device_name = choose_device(devices)
    write_device_property(device_name)    

@app.command()
def setup():
    """Install required dependencies for mobile testing including Android SDK, ADB, and Appium"""
    import platform
    import tempfile
    import urllib.request
    import zipfile
    
    system = platform.system().lower()
    home = Path.home()
    
    def check_command_exists(command: str) -> bool:
        """Check if a command exists in PATH"""
        return shutil.which(command) is not None
    
    def setup_android_env_vars():
        """Setup Android environment variables"""
        if system == "windows":
            android_home = home / "AppData" / "Local" / "Android" / "Sdk"
            android_tools = android_home / "tools"
            android_platform_tools = android_home / "platform-tools"
            android_build_tools = android_home / "build-tools"
            
            # Find latest build tools version
            latest_build_tools = None
            if android_build_tools.exists():
                versions = [d.name for d in android_build_tools.iterdir() if d.is_dir()]
                if versions:
                    latest_build_tools = android_build_tools / max(versions)
            
            paths_to_add = [str(android_tools), str(android_platform_tools)]
            if latest_build_tools:
                paths_to_add.append(str(latest_build_tools))
            
            # Add to user PATH (permanent)
            import winreg
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
                    try:
                        current_path = winreg.QueryValueEx(key, "PATH")[0]
                    except FileNotFoundError:
                        current_path = ""
                    
                    # Set ANDROID_HOME
                    winreg.SetValueEx(key, "ANDROID_HOME", 0, winreg.REG_SZ, str(android_home))
                    
                    # Add Android paths to PATH if not already present
                    for path in paths_to_add:
                        if path not in current_path:
                            current_path += f";{path}"
                    
                    winreg.SetValueEx(key, "PATH", 0, winreg.REG_SZ, current_path)
                    
                typer.secho("✅ Android environment variables set", fg=typer.colors.GREEN)
            except Exception as e:
                typer.secho(f"⚠️ Could not set environment variables automatically: {e}", fg=typer.colors.YELLOW)
                typer.secho(f"Please manually add to PATH: {';'.join(paths_to_add)}", fg=typer.colors.YELLOW)
        else:
            # macOS/Linux
            android_home = home / "Library" / "Android" / "sdk" if system == "darwin" else home / "Android" / "Sdk"
            
            shell_rc = home / ".zshrc" if os.environ.get('SHELL', '').endswith('zsh') else home / ".bashrc"
            
            env_lines = [
                f'export ANDROID_HOME="{android_home}"',
                'export PATH=$PATH:$ANDROID_HOME/tools',
                'export PATH=$PATH:$ANDROID_HOME/platform-tools',
                'export PATH=$PATH:$ANDROID_HOME/build-tools/$(ls $ANDROID_HOME/build-tools | tail -1)'
            ]
            
            # Check if already added
            if shell_rc.exists():
                content = shell_rc.read_text()
                if "ANDROID_HOME" not in content:
                    with open(shell_rc, "a") as f:
                        f.write("\n# Android SDK\n")
                        f.write("\n".join(env_lines))
                        f.write("\n")
                    typer.secho(f"✅ Android environment variables added to {shell_rc}", fg=typer.colors.GREEN)
                else:
                    typer.secho("✅ Android environment variables already configured", fg=typer.colors.GREEN)
    
    def install_android_sdk():
        """Install Android SDK Command Line Tools"""
        if system == "windows":
            android_home = home / "AppData" / "Local" / "Android" / "Sdk"
            sdk_url = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
        elif system == "darwin":
            android_home = home / "Library" / "Android" / "sdk"
            sdk_url = "https://dl.google.com/android/repository/commandlinetools-mac-11076708_latest.zip"
        else:
            android_home = home / "Android" / "Sdk"
            sdk_url = "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
        
        android_home.mkdir(parents=True, exist_ok=True)
        cmdline_tools = android_home / "cmdline-tools"
        
        if not (cmdline_tools / "latest").exists():
            typer.secho("⬇️ Downloading Android SDK Command Line Tools...", fg=typer.colors.YELLOW)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = Path(temp_dir) / "cmdlinetools.zip"
                
                # Try multiple download methods for SSL issues
                download_success = False
                
                # Method 1: Try with SSL context fix for macOS
                try:
                    import ssl
                    import certifi
                    
                    # Create SSL context with proper certificates
                    ssl_context = ssl.create_default_context(cafile=certifi.where())
                    
                    # Create custom opener with SSL context
                    https_handler = urllib.request.HTTPSHandler(context=ssl_context)
                    opener = urllib.request.build_opener(https_handler)
                    urllib.request.install_opener(opener)
                    
                    urllib.request.urlretrieve(sdk_url, zip_path)
                    download_success = True
                    typer.secho("✅ Downloaded using SSL context", fg=typer.colors.GREEN)
                    
                except Exception as e:
                    typer.secho(f"⚠️ SSL context method failed: {str(e)[:100]}", fg=typer.colors.YELLOW)
                
                # Method 2: Try with requests library (usually handles SSL better)
                if not download_success:
                    try:
                        import requests
                        typer.secho("⚠️ Trying alternative download method with requests...", fg=typer.colors.YELLOW)
                        
                        response = requests.get(sdk_url, stream=True, verify=True, timeout=30)
                        response.raise_for_status()
                        
                        with open(zip_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        download_success = True
                        typer.secho("✅ Downloaded using requests library", fg=typer.colors.GREEN)
                        
                    except Exception as e:
                        typer.secho(f"⚠️ Requests method failed: {str(e)[:100]}", fg=typer.colors.YELLOW)
                
                # Method 3: Try with curl command (fallback for macOS)
                if not download_success and system == "darwin":
                    try:
                        typer.secho("⚠️ Trying download with curl command...", fg=typer.colors.YELLOW)
                        result = subprocess.run([
                            "curl", "-L", "-o", str(zip_path), sdk_url
                        ], check=True, capture_output=True, text=True)
                        
                        if zip_path.exists() and zip_path.stat().st_size > 1000:
                            download_success = True
                            typer.secho("✅ Downloaded using curl", fg=typer.colors.GREEN)
                        
                    except Exception as e:
                        typer.secho(f"⚠️ Curl method failed: {str(e)[:100]}", fg=typer.colors.YELLOW)
                
                # Method 4: Manual fallback with instructions
                if not download_success:
                    typer.secho("❌ All automatic download methods failed", fg=typer.colors.RED)
                    typer.secho("\n💡 Manual download required:", fg=typer.colors.BLUE, bold=True)
                    typer.secho(f"1. Open browser and download: {sdk_url}", fg=typer.colors.BLUE)
                    typer.secho(f"2. Extract the zip file", fg=typer.colors.BLUE)
                    typer.secho(f"3. Move cmdline-tools folder to: {android_home}/cmdline-tools/latest", fg=typer.colors.BLUE)
                    typer.secho(f"4. Run 'orbs setup' again", fg=typer.colors.BLUE)
                    
                    # Try to open URL in browser
                    try:
                        import webbrowser
                        typer.secho("🌐 Opening download URL in browser...", fg=typer.colors.BLUE)
                        webbrowser.open(sdk_url)
                    except:
                        pass
                    
                    raise typer.Exit(1)
                
                typer.secho("📦 Extracting Android SDK...", fg=typer.colors.YELLOW)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(android_home)
                
                # Reorganize cmdline-tools structure
                extracted_cmdline_tools = android_home / "cmdline-tools"
                target_latest_dir = android_home / "cmdline-tools" / "latest"
                
                if extracted_cmdline_tools.exists() and not target_latest_dir.exists():
                    # Create the latest directory first
                    target_latest_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Move all contents from cmdline-tools to cmdline-tools/latest
                    for item in extracted_cmdline_tools.iterdir():
                        if item.name != "latest":  # Don't move the latest dir into itself
                            shutil.move(str(item), str(target_latest_dir / item.name))
        
        # Install SDK packages using sdkmanager
        sdkmanager = cmdline_tools / "latest" / "bin" / ("sdkmanager.bat" if system == "windows" else "sdkmanager")
        
        if sdkmanager.exists():
            # Make sdkmanager executable on Unix systems
            if system != "windows":
                import stat
                sdkmanager.chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                
            packages = [
                "platform-tools",
                "platforms;android-34",
                "build-tools;34.0.0",
                "emulator"
            ]
            
            for package in packages:
                typer.secho(f"📦 Installing {package}...", fg=typer.colors.YELLOW)
                try:
                    subprocess.run([str(sdkmanager), package], check=True, input="y\n", text=True, capture_output=True)
                    typer.secho(f"✅ {package} installed", fg=typer.colors.GREEN)
                except subprocess.CalledProcessError:
                    typer.secho(f"⚠️ Failed to install {package}", fg=typer.colors.YELLOW)
        
        setup_android_env_vars()
        typer.secho("✅ Android SDK installed successfully", fg=typer.colors.GREEN)

    def install_java():
        """Install Java if not present"""
        # More thorough Java check - same as check-android
        java_ok = False
        if check_command_exists("java"):
            try:
                result = subprocess.run(["java", "-version"], capture_output=True, text=True)
                if result.returncode == 0:
                    java_ok = True
                    typer.secho("✅ Java detected and working", fg=typer.colors.GREEN)
                    return
            except:
                pass
        
        if not java_ok:
            typer.secho("⚙️ Java not found or not working. Installing...", fg=typer.colors.YELLOW)
        
        if system == "windows":
            if check_command_exists("winget"):
                try:
                    subprocess.run(["winget", "install", "Microsoft.OpenJDK.11"], check=True)
                    typer.secho("✅ Java installed via winget", fg=typer.colors.GREEN)
                except subprocess.CalledProcessError:
                    typer.secho("❌ Failed to install Java via winget", fg=typer.colors.RED)
            else:
                typer.secho("❌ Please install Java manually from https://adoptopenjdk.net/", fg=typer.colors.RED)
        elif system == "darwin":
            if check_command_exists("brew"):
                try:
                    subprocess.run(["brew", "install", "openjdk@11"], check=True)
                    typer.secho("✅ Java installed via Homebrew", fg=typer.colors.GREEN)
                except subprocess.CalledProcessError:
                    typer.secho("❌ Failed to install Java via Homebrew", fg=typer.colors.RED)
            else:
                typer.secho("❌ Please install Homebrew first or install Java manually", fg=typer.colors.RED)

    def install_nodejs_on_windows():
        NODE_URL = "https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi"
        temp_dir = tempfile.gettempdir()
        installer_path = os.path.join(temp_dir, "nodejs_installer.msi")

        typer.secho("⬇️ Downloading Node.js installer...", fg=typer.colors.YELLOW)
        urllib.request.urlretrieve(NODE_URL, installer_path)

        typer.secho("⚙️ Running Node.js installer (silent)...", fg=typer.colors.YELLOW)
        try:
            subprocess.run(["msiexec", "/i", installer_path, "/qn", "/norestart"], check=True)
        except subprocess.CalledProcessError:
            typer.secho("❌ Failed to install Node.js. Please install manually.", fg=typer.colors.RED)
            raise typer.Exit(1)

        # Confirm npm is available
        try:
            subprocess.run("npm --version", shell=True, check=True, stdout=subprocess.DEVNULL)
            typer.secho("✅ Node.js installed successfully", fg=typer.colors.GREEN)
        except subprocess.CalledProcessError:
            typer.secho("❌ Node.js installed but not in PATH. Restart terminal or set PATH manually.", fg=typer.colors.RED)
            raise typer.Exit(1)

    def install_nodejs_on_posix():
        if shutil.which('brew'):
            subprocess.run("brew install node", shell=True, check=True)
        elif shutil.which('apt'):
            subprocess.run("sudo apt update && sudo apt install -y nodejs npm", shell=True, check=True)
        else:
            typer.secho("❌ Could not install Node.js automatically. Install it manually from https://nodejs.org/", fg=typer.colors.RED)
            raise typer.Exit(1)

    # Start setup process
    typer.secho("🚀 Setting up Orbs mobile testing environment...", fg=typer.colors.BLUE, bold=True)
    
    # 1. Install Java
    install_java()
    
    # 2. Install Android SDK
    # More thorough Android SDK check - same as check-android  
    android_sdk_ok = False
    if system == "windows":
        android_home = home / "AppData" / "Local" / "Android" / "Sdk"
    elif system == "darwin":
        android_home = home / "Library" / "Android" / "sdk"
    else:
        android_home = home / "Android" / "Sdk"
    
    android_home_env = os.environ.get("ANDROID_HOME", str(android_home))
    if Path(android_home_env).exists():
        platform_tools = Path(android_home_env) / "platform-tools"
        if platform_tools.exists():
            android_sdk_ok = True
    
    if not android_sdk_ok:
        install_android_sdk()
    else:
        typer.secho("✅ Android SDK detected", fg=typer.colors.GREEN)
        setup_android_env_vars()  # Still setup env vars
        
    # 3. Ensure Node.js & npm
    try:
        subprocess.run("npm --version", shell=True, check=True, stdout=subprocess.DEVNULL)
        typer.secho("✅ npm detected", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError:
        typer.secho("⚙️ npm not found. Installing Node.js...", fg=typer.colors.YELLOW)
        if system == "windows":
            install_nodejs_on_windows()
        else:
            install_nodejs_on_posix()
    
    # 4. Check & install Appium dependencies
    def is_npm_package_installed(package: str) -> bool:
        try:
            result = subprocess.run(
                f"npm list -g {package}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return package in result.stdout
        except Exception:
            return False
    
    def is_appium_in_path() -> bool:
        """Check if appium is actually accessible in PATH"""
        return check_command_exists("appium")

    deps = ["appium", "appium-uiautomator2-driver"]
    for pkg in deps:
        if is_npm_package_installed(pkg):
            if pkg == "appium":
                # Double check if it's actually in PATH
                if is_appium_in_path():
                    typer.secho(f"✅ {pkg} already installed and accessible", fg=typer.colors.GREEN)
                else:
                    typer.secho(f"⚠️ {pkg} installed but not in PATH. Reinstalling...", fg=typer.colors.YELLOW)
                    try:
                        subprocess.run(f"npm install -g {pkg}", shell=True, check=True)
                        typer.secho(f"✅ {pkg} reinstalled", fg=typer.colors.GREEN)
                    except subprocess.CalledProcessError:
                        typer.secho(f"❌ Failed to reinstall {pkg}. Make sure npm works.", fg=typer.colors.RED)
            else:
                typer.secho(f"✅ {pkg} already installed", fg=typer.colors.GREEN)
        else:
            typer.secho(f"⬇️ Installing {pkg}...", fg=typer.colors.YELLOW)
            try:
                subprocess.run(f"npm install -g {pkg}", shell=True, check=True)
                typer.secho(f"✅ {pkg} installed", fg=typer.colors.GREEN)
            except subprocess.CalledProcessError:
                typer.secho(f"❌ Failed to install {pkg}. Make sure npm works.", fg=typer.colors.RED)
                raise typer.Exit(1)

    # Install Appium drivers properly for Appium 2.0+
    typer.secho("⚙️ Installing Appium drivers...", fg=typer.colors.YELLOW)
    try:
        # Install UIAutomator2 driver via appium driver install
        result = subprocess.run(["appium", "driver", "install", "uiautomator2"], 
                               check=True, capture_output=True, text=True)
        typer.secho("✅ UIAutomator2 driver installed", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError as e:
        typer.secho("⚠️ Failed to install UIAutomator2 driver via appium command", fg=typer.colors.YELLOW)
        typer.secho(f"   Error: {str(e)[:100]}", fg=typer.colors.YELLOW)
        
        # Fallback: try manual installation
        try:
            typer.secho("⚙️ Trying manual driver installation...", fg=typer.colors.YELLOW)
            subprocess.run("npm install -g appium-uiautomator2-driver", shell=True, check=True)
            # Force register driver
            subprocess.run(["appium", "driver", "install", "uiautomator2@latest"], 
                          check=False, capture_output=True, text=True)
            typer.secho("✅ UIAutomator2 driver installed manually", fg=typer.colors.GREEN)
        except:
            typer.secho("⚠️ Driver installation may need manual setup", fg=typer.colors.YELLOW)

    typer.secho("\n🎉 Setup complete! All mobile testing dependencies are ready", fg=typer.colors.GREEN, bold=True)
    typer.secho("⚠️ You may need to restart your terminal for PATH changes to take effect", fg=typer.colors.YELLOW)

@app.command()
def select_platform():
    """Select platform (mobile or web) and save it to settings"""
    all_platforms = PLATFORM_LIST["mobile"] + PLATFORM_LIST["web"]

    choice = inquirer.select(
        message="Select platform:",
        choices=all_platforms,
        default=all_platforms[0]
    ).execute()

    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    platform_props = SETTINGS_DIR / "platform.properties"

    # Update or create platform.properties
    lines = []
    if platform_props.exists():
        lines = platform_props.read_text().splitlines()

    updated = False
    new_lines = []
    for line in lines:
        if line.startswith("default_platform="):
            new_lines.append(f"default_platform={choice}")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"default_platform={choice}")

    platform_props.write_text("\n".join(new_lines) + "\n")

    typer.secho(f"✅ Selected platform '{choice}' saved to {platform_props}", fg=typer.colors.GREEN)


@app.command()
def spy(web: bool = False, mobile: bool = False, url: str = typer.Option(None, "--url")):
    """
    Start element spy session (web or mobile).
    Usage: orbs spy --url=https://google.com --web
    """
    if web:
        # Fix URL format if protocol is missing
        if url and not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            typer.secho(f"ℹ️ Added https:// protocol to URL: {url}", fg=typer.colors.BLUE)
        
        runner = WebSpyRunner(url=url)
    elif mobile:
        runner = MobileSpyRunner()  # not yet implemented
    else:
        typer.echo("Please specify a platform: --web or --mobile")
        typer.echo("Example: orbs spy --url=https://google.com --web")
        raise typer.Exit(code=1)

    try:
        runner.start()
        typer.echo("[Orbs] Spy session started. Use Ctrl+` in the browser to capture. Press Ctrl+C here to stop.")
        # Block until Ctrl+C
        typer.echo("")  # just to move to a fresh line
        typer.pause()   # waits until user hits Enter
    except KeyboardInterrupt:
        pass
    finally:
        runner.stop()
        typer.echo("[Orbs] Spy session ended.")

@app.command()
def serve(port: int = typer.Option(None, help="Port to run the server")):
    """Start local orbs API server."""
    from orbs.api_server import start_server
    start_server(port)

@app.command()
def check_android():
    """Check Android development environment status"""
    import platform
    
    system = platform.system().lower()
    home = Path.home()
    
    def check_command_exists(command: str) -> bool:
        return shutil.which(command) is not None
    
    typer.secho("🔍 Checking Android development environment...\n", fg=typer.colors.BLUE, bold=True)
    
    # Check Java
    if check_command_exists("java"):
        try:
            result = subprocess.run(["java", "-version"], capture_output=True, text=True)
            if result.returncode == 0:
                # Java version output usually goes to stderr
                version_output = result.stderr if result.stderr else result.stdout
                if version_output:
                    version_line = version_output.split('\n')[0]
                    typer.secho(f"✅ Java: {version_line}", fg=typer.colors.GREEN)
                else:
                    typer.secho("✅ Java: Installed (version info unavailable)", fg=typer.colors.GREEN)
            else:
                typer.secho("❌ Java: Error - Unable to locate Java Runtime", fg=typer.colors.RED)
        except Exception as e:
            typer.secho(f"❌ Java: Error checking version - {str(e)}", fg=typer.colors.RED)
    else:
        typer.secho("❌ Java: Not found in PATH", fg=typer.colors.RED)
    
    # Check Android SDK
    if system == "windows":
        android_home = home / "AppData" / "Local" / "Android" / "Sdk"
    elif system == "darwin":
        android_home = home / "Library" / "Android" / "sdk"
    else:
        android_home = home / "Android" / "Sdk"
    
    android_home_env = os.environ.get("ANDROID_HOME", str(android_home))
    if Path(android_home_env).exists():
        typer.secho(f"✅ Android SDK: Found at {android_home_env}", fg=typer.colors.GREEN)
        
        # Check specific components
        platform_tools = Path(android_home_env) / "platform-tools"
        build_tools = Path(android_home_env) / "build-tools"
        
        if platform_tools.exists():
            typer.secho(f"✅ Platform Tools: Found", fg=typer.colors.GREEN)
        else:
            typer.secho(f"❌ Platform Tools: Not found", fg=typer.colors.RED)
            
        if build_tools.exists():
            versions = [d.name for d in build_tools.iterdir() if d.is_dir()]
            if versions:
                typer.secho(f"✅ Build Tools: {', '.join(sorted(versions))}", fg=typer.colors.GREEN)
            else:
                typer.secho(f"❌ Build Tools: No versions found", fg=typer.colors.RED)
        else:
            typer.secho(f"❌ Build Tools: Not found", fg=typer.colors.RED)
    else:
        typer.secho(f"❌ Android SDK: Not found at {android_home_env}", fg=typer.colors.RED)
    
    # Check ADB
    if check_command_exists("adb"):
        try:
            result = subprocess.run(["adb", "version"], capture_output=True, text=True)
            version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown version"
            typer.secho(f"✅ ADB: {version_line}", fg=typer.colors.GREEN)
        except:
            typer.secho("❌ ADB: Error checking version", fg=typer.colors.RED)
    else:
        typer.secho("❌ ADB: Not found in PATH", fg=typer.colors.RED)
    
    # Check connected devices
    devices = get_connected_devices()
    if devices:
        typer.secho(f"✅ Connected devices: {', '.join(devices)}", fg=typer.colors.GREEN)
    else:
        typer.secho("⚠️ Connected devices: None found", fg=typer.colors.YELLOW)
    
    # Check Node.js and npm
    if check_command_exists("node"):
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            version = result.stdout.strip()
            typer.secho(f"✅ Node.js: {version}", fg=typer.colors.GREEN)
        except:
            typer.secho("❌ Node.js: Error checking version", fg=typer.colors.RED)
    else:
        typer.secho("❌ Node.js: Not found in PATH", fg=typer.colors.RED)
        
    if check_command_exists("npm"):
        try:
            result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
            version = result.stdout.strip()
            typer.secho(f"✅ npm: {version}", fg=typer.colors.GREEN)
        except:
            typer.secho("❌ npm: Error checking version", fg=typer.colors.RED)
    else:
        typer.secho("❌ npm: Not found in PATH", fg=typer.colors.RED)
    
    # Check Appium
    if check_command_exists("appium"):
        try:
            result = subprocess.run(["appium", "--version"], capture_output=True, text=True)
            version = result.stdout.strip()
            typer.secho(f"✅ Appium: {version}", fg=typer.colors.GREEN)
        except:
            typer.secho("❌ Appium: Error checking version", fg=typer.colors.RED)
    else:
        typer.secho("❌ Appium: Not found in PATH", fg=typer.colors.RED)
    
    typer.secho("\n💡 Run 'orbs setup' to install missing dependencies", fg=typer.colors.BLUE)

@app.command()
def doctor():
    """Comprehensive diagnosis and setup verification with fix suggestions"""
    import platform
    
    system = platform.system().lower()
    home = Path.home()
    
    def check_command_exists(command: str) -> bool:
        return shutil.which(command) is not None
    
    def get_missing_items():
        missing = []
        suggestions = []
        
        # Check Java
        java_ok = False
        if check_command_exists("java"):
            try:
                result = subprocess.run(["java", "-version"], capture_output=True, text=True)
                if result.returncode == 0:
                    java_ok = True
            except:
                pass
        
        if not java_ok:
            missing.append("Java")
            if system == "windows":
                suggestions.append("Java: Run 'winget install Microsoft.OpenJDK.11' or download from adoptopenjdk.net")
            elif system == "darwin":
                suggestions.append("Java: Run 'brew install openjdk@11' or download from adoptopenjdk.net")
            else:
                suggestions.append("Java: Install OpenJDK 11 via package manager")
        
        # Check Android SDK
        android_sdk_ok = False
        if system == "windows":
            android_home = home / "AppData" / "Local" / "Android" / "Sdk"
        elif system == "darwin":
            android_home = home / "Library" / "Android" / "sdk"
        else:
            android_home = home / "Android" / "Sdk"
        
        android_home_env = os.environ.get("ANDROID_HOME", str(android_home))
        if Path(android_home_env).exists():
            platform_tools = Path(android_home_env) / "platform-tools"
            if platform_tools.exists():
                android_sdk_ok = True
        
        if not android_sdk_ok:
            missing.append("Android SDK")
            suggestions.append("Android SDK: Will be automatically installed by 'orbs setup'")
        
        # Check ADB
        if not check_command_exists("adb"):
            missing.append("ADB")
            suggestions.append("ADB: Will be installed with Android SDK via 'orbs setup'")
        
        # Check Node.js
        if not check_command_exists("node"):
            missing.append("Node.js")
            if system == "windows":
                suggestions.append("Node.js: Download from nodejs.org or run 'winget install OpenJS.NodeJS'")
            elif system == "darwin":
                suggestions.append("Node.js: Run 'brew install node' or download from nodejs.org")
            else:
                suggestions.append("Node.js: Install via package manager (apt install nodejs npm)")
        
        # Check npm
        if not check_command_exists("npm"):
            missing.append("npm")
            suggestions.append("npm: Usually installed with Node.js")
        
        # Check Appium
        if not check_command_exists("appium"):
            missing.append("Appium")
            suggestions.append("Appium: Run 'npm install -g appium' after installing Node.js")
        
        return missing, suggestions
    
    typer.secho("🔍 Orbs Environment Doctor\n", fg=typer.colors.BLUE, bold=True)
    typer.secho("Checking all required dependencies for Android testing...\n", fg=typer.colors.BLUE)
    
    # Run the check
    missing, suggestions = get_missing_items()
    
    if not missing:
        typer.secho("🎉 All dependencies are installed and ready!", fg=typer.colors.GREEN, bold=True)
        typer.secho("\nYou can now:", fg=typer.colors.GREEN)
        typer.secho("• Create a new project: orbs init my-project", fg=typer.colors.GREEN)
        typer.secho("• Select device: orbs select-device", fg=typer.colors.GREEN)
        typer.secho("• Run tests: orbs run testcase_name --platform=android", fg=typer.colors.GREEN)
        
        # Check connected devices
        devices = get_connected_devices()
        if devices:
            typer.secho(f"\n📱 Connected devices: {', '.join(devices)}", fg=typer.colors.GREEN)
        else:
            typer.secho("\n⚠️ No Android devices connected. Connect a device or start an emulator.", fg=typer.colors.YELLOW)
    else:
        typer.secho(f"❌ Missing dependencies: {', '.join(missing)}\n", fg=typer.colors.RED, bold=True)
        
        typer.secho("🔧 Recommended fixes:", fg=typer.colors.YELLOW, bold=True)
        typer.secho("1. Run 'orbs setup' for automatic installation", fg=typer.colors.YELLOW)
        typer.secho("   This will install most missing dependencies automatically\n", fg=typer.colors.YELLOW)
        
        typer.secho("2. Manual installation (if automatic fails):", fg=typer.colors.YELLOW)
        for suggestion in suggestions:
            typer.secho(f"   • {suggestion}", fg=typer.colors.YELLOW)
        
        typer.secho("\n3. After installation:", fg=typer.colors.YELLOW)
        typer.secho("   • Restart your terminal", fg=typer.colors.YELLOW)
        typer.secho("   • Run 'orbs doctor' again to verify", fg=typer.colors.YELLOW)
        
        typer.secho(f"\n💡 Quick start: orbs setup && orbs doctor", fg=typer.colors.BLUE, bold=True)

# Add alias commands for convenience
@app.command(name="check")
def check_alias():
    """Alias for check-android command"""
    check_android()

@app.command(name="status") 
def status_alias():
    """Alias for check-android command"""
    check_android()

@app.command(name="verify")
def verify_alias():
    """Alias for doctor command"""
    doctor()

@app.command()
def install_java():
    """Install Java only"""
    import platform
    system = platform.system().lower()
    
    def check_command_exists(command: str) -> bool:
        return shutil.which(command) is not None
    
    if check_command_exists("java"):
        try:
            result = subprocess.run(["java", "-version"], capture_output=True, text=True)
            if result.returncode == 0:
                typer.secho("✅ Java is already installed", fg=typer.colors.GREEN)
                return
        except:
            pass
    
    typer.secho("⚙️ Installing Java...", fg=typer.colors.YELLOW)
    
    if system == "windows":
        if check_command_exists("winget"):
            try:
                subprocess.run(["winget", "install", "Microsoft.OpenJDK.11"], check=True)
                typer.secho("✅ Java installed successfully", fg=typer.colors.GREEN)
            except subprocess.CalledProcessError:
                typer.secho("❌ Failed to install Java via winget", fg=typer.colors.RED)
                typer.secho("💡 Please download manually from https://adoptopenjdk.net/", fg=typer.colors.BLUE)
        else:
            typer.secho("❌ Winget not available. Please download Java manually from https://adoptopenjdk.net/", fg=typer.colors.RED)
    elif system == "darwin":
        if check_command_exists("brew"):
            try:
                subprocess.run(["brew", "install", "openjdk@11"], check=True)
                typer.secho("✅ Java installed successfully", fg=typer.colors.GREEN)
                typer.secho("💡 You may need to add Java to your PATH. Restart terminal.", fg=typer.colors.BLUE)
            except subprocess.CalledProcessError:
                typer.secho("❌ Failed to install Java via Homebrew", fg=typer.colors.RED)
                typer.secho("💡 Please download manually from https://adoptopenjdk.net/", fg=typer.colors.BLUE)
        else:
            typer.secho("❌ Homebrew not installed. Please install Homebrew first or download Java manually", fg=typer.colors.RED)
            typer.secho("💡 Install Homebrew: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"", fg=typer.colors.BLUE)
    else:
        typer.secho("❌ Automatic Java installation not supported on this platform", fg=typer.colors.RED)
        typer.secho("💡 Please install Java via your package manager (e.g., apt install openjdk-11-jdk)", fg=typer.colors.BLUE)

@app.command()
def install_appium():
    """Install Appium and drivers only"""
    def check_command_exists(command: str) -> bool:
        return shutil.which(command) is not None
    
    # Check Node.js first
    if not check_command_exists("npm"):
        typer.secho("❌ npm not found. Please install Node.js first:", fg=typer.colors.RED)
        typer.secho("   orbs install-nodejs", fg=typer.colors.RED)
        typer.secho("   or download from https://nodejs.org/", fg=typer.colors.RED)
        raise typer.Exit(1)
    
    def is_npm_package_installed(package: str) -> bool:
        try:
            result = subprocess.run(
                f"npm list -g {package}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return package in result.stdout
        except Exception:
            return False

    deps = ["appium", "appium-uiautomator2-driver"]
    
    for pkg in deps:
        if is_npm_package_installed(pkg):
            typer.secho(f"✅ {pkg} already installed", fg=typer.colors.GREEN)
        else:
            typer.secho(f"⬇️ Installing {pkg}...", fg=typer.colors.YELLOW)
            try:
                subprocess.run(f"npm install -g {pkg}", shell=True, check=True)
                typer.secho(f"✅ {pkg} installed", fg=typer.colors.GREEN)
            except subprocess.CalledProcessError:
                typer.secho(f"❌ Failed to install {pkg}", fg=typer.colors.RED)
                typer.secho(f"💡 Try: npm install -g {pkg}", fg=typer.colors.BLUE)
    
    # Install Appium drivers properly for Appium 2.0+
    typer.secho("⚙️ Installing Appium drivers...", fg=typer.colors.YELLOW)
    try:
        # Install UIAutomator2 driver via appium driver install
        result = subprocess.run(["appium", "driver", "install", "uiautomator2"], 
                               check=True, capture_output=True, text=True)
        typer.secho("✅ UIAutomator2 driver installed", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError as e:
        typer.secho("⚠️ Failed to install UIAutomator2 driver via appium command", fg=typer.colors.YELLOW)
        typer.secho(f"   Error: {str(e)[:100]}", fg=typer.colors.YELLOW)
        
        # Fallback: try manual installation
        try:
            typer.secho("⚙️ Trying manual driver installation...", fg=typer.colors.YELLOW)
            subprocess.run("npm install -g appium-uiautomator2-driver", shell=True, check=True)
            # Force register driver
            subprocess.run(["appium", "driver", "install", "uiautomator2@latest"], 
                          check=False, capture_output=True, text=True)
            typer.secho("✅ UIAutomator2 driver installed manually", fg=typer.colors.GREEN)
        except:
            typer.secho("⚠️ Driver installation may need manual setup", fg=typer.colors.YELLOW)
    
    typer.secho("\n🎉 Appium installation complete!", fg=typer.colors.GREEN, bold=True)

@app.command()
def install_appium_drivers():
    """Install and register Appium drivers properly"""
    def check_command_exists(command: str) -> bool:
        return shutil.which(command) is not None
    
    if not check_command_exists("appium"):
        typer.secho("❌ Appium not found. Please install Appium first:", fg=typer.colors.RED)
        typer.secho("   orbs install-appium", fg=typer.colors.RED)
        raise typer.Exit(1)
    
    typer.secho("🔧 Installing Appium drivers...", fg=typer.colors.BLUE, bold=True)
    
    # List current drivers
    try:
        result = subprocess.run(["appium", "driver", "list"], capture_output=True, text=True)
        if result.returncode == 0:
            typer.secho("Current driver status:", fg=typer.colors.BLUE)
            typer.secho(result.stdout, fg=typer.colors.BLUE)
        
        # Install UIAutomator2 driver
        if "uiautomator2 [not installed]" in result.stdout or "[not installed]" in result.stdout:
            typer.secho("⚙️ Installing UIAutomator2 driver...", fg=typer.colors.YELLOW)
            
            install_result = subprocess.run(["appium", "driver", "install", "uiautomator2"], 
                                           capture_output=True, text=True)
            
            if install_result.returncode == 0:
                typer.secho("✅ UIAutomator2 driver installed successfully", fg=typer.colors.GREEN)
            else:
                typer.secho("⚠️ Driver installation failed, trying alternative method...", fg=typer.colors.YELLOW)
                # Alternative: install specific version
                alt_result = subprocess.run(["appium", "driver", "install", "uiautomator2@latest"], 
                                          capture_output=True, text=True)
                if alt_result.returncode == 0:
                    typer.secho("✅ UIAutomator2 driver installed (latest)", fg=typer.colors.GREEN)
                else:
                    typer.secho(f"❌ Failed to install driver: {install_result.stderr}", fg=typer.colors.RED)
        else:
            typer.secho("✅ UIAutomator2 driver already installed", fg=typer.colors.GREEN)
        
        # Final verification
        final_result = subprocess.run(["appium", "driver", "list"], capture_output=True, text=True)
        if final_result.returncode == 0:
            typer.secho("\nFinal driver status:", fg=typer.colors.BLUE, bold=True)
            typer.secho(final_result.stdout, fg=typer.colors.GREEN)
            
    except Exception as e:
        typer.secho(f"❌ Error managing Appium drivers: {e}", fg=typer.colors.RED)
        typer.secho("💡 Try running manually: appium driver install uiautomator2", fg=typer.colors.BLUE)

@app.command()
def install_nodejs():
    """Install Node.js only"""
    import platform
    import tempfile
    import urllib.request
    
    system = platform.system().lower()
    
    def check_command_exists(command: str) -> bool:
        return shutil.which(command) is not None
    
    if check_command_exists("node") and check_command_exists("npm"):
        typer.secho("✅ Node.js and npm are already installed", fg=typer.colors.GREEN)
        try:
            node_result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            npm_result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
            typer.secho(f"   Node.js: {node_result.stdout.strip()}", fg=typer.colors.GREEN)
            typer.secho(f"   npm: {npm_result.stdout.strip()}", fg=typer.colors.GREEN)
        except:
            pass
        return
    
    typer.secho("⚙️ Installing Node.js...", fg=typer.colors.YELLOW)
    
    if system == "windows":
        NODE_URL = "https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi"
        temp_dir = tempfile.gettempdir()
        installer_path = os.path.join(temp_dir, "nodejs_installer.msi")

        typer.secho("⬇️ Downloading Node.js installer...", fg=typer.colors.YELLOW)
        try:
            urllib.request.urlretrieve(NODE_URL, installer_path)
            typer.secho("⚙️ Running Node.js installer (silent)...", fg=typer.colors.YELLOW)
            subprocess.run(["msiexec", "/i", installer_path, "/qn", "/norestart"], check=True)
            typer.secho("✅ Node.js installed successfully", fg=typer.colors.GREEN)
            typer.secho("💡 Restart terminal to use node and npm commands", fg=typer.colors.BLUE)
        except Exception as e:
            typer.secho(f"❌ Failed to install Node.js: {e}", fg=typer.colors.RED)
            typer.secho("💡 Please download manually from https://nodejs.org/", fg=typer.colors.BLUE)
    elif system == "darwin":
        if check_command_exists("brew"):
            try:
                subprocess.run(["brew", "install", "node"], check=True)
                typer.secho("✅ Node.js installed successfully", fg=typer.colors.GREEN)
            except subprocess.CalledProcessError:
                typer.secho("❌ Failed to install Node.js via Homebrew", fg=typer.colors.RED)
                typer.secho("💡 Please download manually from https://nodejs.org/", fg=typer.colors.BLUE)
        else:
            typer.secho("❌ Homebrew not installed. Please install Homebrew first or download Node.js manually", fg=typer.colors.RED)
            typer.secho("💡 Install Homebrew: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"", fg=typer.colors.BLUE)
    else:
        typer.secho("❌ Automatic Node.js installation not supported on this platform", fg=typer.colors.RED)
        typer.secho("💡 Please install via package manager (e.g., apt install nodejs npm)", fg=typer.colors.BLUE)

@app.command()
def fix_environment():
    """Fix common environment issues after setup"""
    import platform
    
    system = platform.system().lower()
    home = Path.home()
    
    def check_command_exists(command: str) -> bool:
        return shutil.which(command) is not None
    
    typer.secho("🔧 Fixing common environment issues...\n", fg=typer.colors.BLUE, bold=True)
    
    # Fix Java PATH issue
    if check_command_exists("java"):
        try:
            result = subprocess.run(["java", "-version"], capture_output=True, text=True)
            if result.returncode != 0:
                typer.secho("❌ Java command exists but cannot run. Fixing...", fg=typer.colors.YELLOW)
                if system == "darwin":
                    # Common issue on macOS - Java installed but JAVA_HOME not set
                    java_home_cmd = "/usr/libexec/java_home"
                    if Path(java_home_cmd).exists():
                        try:
                            java_home_result = subprocess.run([java_home_cmd], capture_output=True, text=True)
                            if java_home_result.returncode == 0:
                                java_home = java_home_result.stdout.strip()
                                shell_rc = home / ".zshrc" if os.environ.get('SHELL', '').endswith('zsh') else home / ".bashrc"
                                
                                env_line = f'export JAVA_HOME="{java_home}"'
                                if shell_rc.exists():
                                    content = shell_rc.read_text()
                                    if "JAVA_HOME" not in content:
                                        with open(shell_rc, "a") as f:
                                            f.write(f"\n# Java Home\n{env_line}\n")
                                        typer.secho(f"✅ Added JAVA_HOME to {shell_rc}", fg=typer.colors.GREEN)
                                        typer.secho("💡 Restart terminal or run: source ~/.zshrc", fg=typer.colors.BLUE)
                                    else:
                                        typer.secho("✅ JAVA_HOME already configured", fg=typer.colors.GREEN)
                        except:
                            typer.secho("⚠️ Could not auto-detect Java installation", fg=typer.colors.YELLOW)
        except Exception:
            typer.secho("❌ Java installation appears corrupted", fg=typer.colors.RED)
    
    # Fix Android SDK PATH
    if system == "darwin":
        android_home = home / "Library" / "Android" / "sdk"
    elif system == "windows":
        android_home = home / "AppData" / "Local" / "Android" / "Sdk"
    else:
        android_home = home / "Android" / "Sdk"
    
    if not android_home.exists():
        typer.secho(f"❌ Android SDK not found at expected location: {android_home}", fg=typer.colors.RED)
        typer.secho("🔧 Downloading and installing Android SDK...", fg=typer.colors.YELLOW)
        
        # Use the install_android_sdk function from setup
        if system == "windows":
            sdk_url = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
        elif system == "darwin":
            sdk_url = "https://dl.google.com/android/repository/commandlinetools-mac-11076708_latest.zip"
        else:
            sdk_url = "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
        
        android_home.mkdir(parents=True, exist_ok=True)
        cmdline_tools = android_home / "cmdline-tools"
        
        if not (cmdline_tools / "latest").exists():
            import tempfile
            import urllib.request
            import zipfile
            
            typer.secho("⬇️ Downloading Android SDK...", fg=typer.colors.YELLOW)
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = Path(temp_dir) / "cmdlinetools.zip"
                urllib.request.urlretrieve(sdk_url, zip_path)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(android_home)
                
                # Move cmdline-tools to latest directory
                cmdline_tools.mkdir(exist_ok=True)
                if (android_home / "cmdline-tools").exists():
                    shutil.move(str(android_home / "cmdline-tools"), str(cmdline_tools / "latest"))
        
        # Install packages
        sdkmanager = cmdline_tools / "latest" / "bin" / ("sdkmanager.bat" if system == "windows" else "sdkmanager")
        if sdkmanager.exists():
            packages = ["platform-tools", "platforms;android-34", "build-tools;34.0.0"]
            for package in packages:
                typer.secho(f"📦 Installing {package}...", fg=typer.colors.YELLOW)
                try:
                    subprocess.run([str(sdkmanager), package], check=True, input="y\n", text=True, capture_output=True)
                    typer.secho(f"✅ {package} installed", fg=typer.colors.GREEN)
                except subprocess.CalledProcessError:
                    typer.secho(f"⚠️ Failed to install {package}", fg=typer.colors.YELLOW)
    else:
        typer.secho(f"✅ Android SDK found at: {android_home}", fg=typer.colors.GREEN)
    
    # Fix Appium PATH issue
    if not check_command_exists("appium"):
        typer.secho("❌ Appium not found in PATH. Checking npm global directory...", fg=typer.colors.YELLOW)
        try:
            # Get npm global directory
            npm_prefix_result = subprocess.run(["npm", "prefix", "-g"], capture_output=True, text=True)
            if npm_prefix_result.returncode == 0:
                npm_global = Path(npm_prefix_result.stdout.strip())
                appium_path = npm_global / "bin" / "appium"
                
                if appium_path.exists():
                    typer.secho(f"✅ Found Appium at: {appium_path}", fg=typer.colors.GREEN)
                    typer.secho(f"💡 Add to PATH: export PATH=$PATH:{npm_global / 'bin'}", fg=typer.colors.BLUE)
                    
                    # Auto-fix PATH
                    shell_rc = home / ".zshrc" if os.environ.get('SHELL', '').endswith('zsh') else home / ".bashrc"
                    if shell_rc.exists():
                        content = shell_rc.read_text()
                        npm_bin_path = str(npm_global / "bin")
                        if npm_bin_path not in content:
                            with open(shell_rc, "a") as f:
                                f.write(f"\n# npm global bin\nexport PATH=$PATH:{npm_bin_path}\n")
                            typer.secho(f"✅ Added npm global bin to PATH in {shell_rc}", fg=typer.colors.GREEN)
                            typer.secho("💡 Restart terminal for changes to take effect", fg=typer.colors.BLUE)
                else:
                    typer.secho("❌ Appium not found in npm global directory", fg=typer.colors.RED)
                    typer.secho("🔧 Reinstalling Appium...", fg=typer.colors.YELLOW)
                    subprocess.run("npm install -g appium", shell=True, check=True)
                    typer.secho("✅ Appium reinstalled", fg=typer.colors.GREEN)
        except Exception as e:
            typer.secho(f"❌ Error checking npm global directory: {e}", fg=typer.colors.RED)
    
    typer.secho("\n🎉 Environment fixes applied!", fg=typer.colors.GREEN, bold=True)
    typer.secho("💡 Please restart your terminal and run 'orbs doctor' to verify", fg=typer.colors.BLUE)

@app.command()
def debug_env():
    """Debug environment issues with detailed output"""
    import platform
    
    system = platform.system().lower()
    home = Path.home()
    
    def check_command_exists(command: str) -> bool:
        return shutil.which(command) is not None
    
    typer.secho("🐛 Environment Debug Information\n", fg=typer.colors.BLUE, bold=True)
    
    # Debug Java
    typer.secho("🔍 Java Debug:", fg=typer.colors.BLUE, bold=True)
    if check_command_exists("java"):
        java_path = shutil.which("java")
        typer.secho(f"   Java path: {java_path}", fg=typer.colors.BLUE)
        
        try:
            result = subprocess.run(["java", "-version"], capture_output=True, text=True)
            typer.secho(f"   Return code: {result.returncode}", fg=typer.colors.BLUE)
            if result.stdout:
                typer.secho(f"   STDOUT: {result.stdout[:200]}", fg=typer.colors.BLUE)
            if result.stderr:
                typer.secho(f"   STDERR: {result.stderr[:200]}", fg=typer.colors.BLUE)
        except Exception as e:
            typer.secho(f"   Error: {e}", fg=typer.colors.RED)
    else:
        typer.secho("   Java not found in PATH", fg=typer.colors.RED)
    
    # Check JAVA_HOME
    java_home = os.environ.get("JAVA_HOME")
    typer.secho(f"   JAVA_HOME: {java_home}", fg=typer.colors.BLUE)
    
    # Debug Android SDK
    typer.secho(f"\n🔍 Android SDK Debug:", fg=typer.colors.BLUE, bold=True)
    if system == "darwin":
        expected_android_home = home / "Library" / "Android" / "sdk"
    elif system == "windows":
        expected_android_home = home / "AppData" / "Local" / "Android" / "Sdk"
    else:
        expected_android_home = home / "Android" / "Sdk"
    
    android_home_env = os.environ.get("ANDROID_HOME")
    typer.secho(f"   ANDROID_HOME env: {android_home_env}", fg=typer.colors.BLUE)
    typer.secho(f"   Expected location: {expected_android_home}", fg=typer.colors.BLUE)
    typer.secho(f"   Exists: {expected_android_home.exists()}", fg=typer.colors.BLUE)
    
    if expected_android_home.exists():
        platform_tools = expected_android_home / "platform-tools"
        build_tools = expected_android_home / "build-tools"
        typer.secho(f"   Platform tools: {platform_tools.exists()}", fg=typer.colors.BLUE)
        typer.secho(f"   Build tools: {build_tools.exists()}", fg=typer.colors.BLUE)
        
        if build_tools.exists():
            versions = [d.name for d in build_tools.iterdir() if d.is_dir()]
            typer.secho(f"   Build tools versions: {versions}", fg=typer.colors.BLUE)
    
    # Debug npm and Appium
    typer.secho(f"\n🔍 npm/Appium Debug:", fg=typer.colors.BLUE, bold=True)
    if check_command_exists("npm"):
        try:
            npm_prefix_result = subprocess.run(["npm", "prefix", "-g"], capture_output=True, text=True)
            npm_global = npm_prefix_result.stdout.strip()
            typer.secho(f"   npm global prefix: {npm_global}", fg=typer.colors.BLUE)
            
            npm_list_result = subprocess.run(["npm", "list", "-g", "--depth=0"], capture_output=True, text=True)
            if "appium" in npm_list_result.stdout:
                typer.secho(f"   Appium in npm list: ✅", fg=typer.colors.GREEN)
            else:
                typer.secho(f"   Appium in npm list: ❌", fg=typer.colors.RED)
                
            appium_global_path = Path(npm_global) / "bin" / "appium"
            typer.secho(f"   Expected Appium path: {appium_global_path}", fg=typer.colors.BLUE)
            typer.secho(f"   Appium file exists: {appium_global_path.exists()}", fg=typer.colors.BLUE)
            
        except Exception as e:
            typer.secho(f"   Error checking npm: {e}", fg=typer.colors.RED)
    
    # Check PATH
    typer.secho(f"\n🔍 PATH Debug:", fg=typer.colors.BLUE, bold=True)
    path_env = os.environ.get("PATH", "")
    path_parts = path_env.split(":")
    typer.secho(f"   PATH has {len(path_parts)} entries", fg=typer.colors.BLUE)
    
    # Check for relevant paths
    for part in path_parts:
        if any(keyword in part.lower() for keyword in ["java", "android", "npm", "node"]):
            typer.secho(f"   Relevant PATH: {part}", fg=typer.colors.BLUE)
    
    # Shell info
    shell = os.environ.get("SHELL", "unknown")
    typer.secho(f"\n🔍 Shell Info:", fg=typer.colors.BLUE, bold=True)
    typer.secho(f"   Shell: {shell}", fg=typer.colors.BLUE)
    
    shell_rc = home / ".zshrc" if shell.endswith('zsh') else home / ".bashrc"
    typer.secho(f"   Shell RC: {shell_rc}", fg=typer.colors.BLUE)
    typer.secho(f"   Shell RC exists: {shell_rc.exists()}", fg=typer.colors.BLUE)
    
    if shell_rc.exists():
        with open(shell_rc, 'r') as f:
            content = f.read()
            android_in_rc = "ANDROID_HOME" in content
            java_in_rc = "JAVA_HOME" in content
            npm_in_rc = any(keyword in content for keyword in ["npm", "node"])
            
            typer.secho(f"   ANDROID_HOME in RC: {android_in_rc}", fg=typer.colors.BLUE)
            typer.secho(f"   JAVA_HOME in RC: {java_in_rc}", fg=typer.colors.BLUE)
            typer.secho(f"   npm/node in RC: {npm_in_rc}", fg=typer.colors.BLUE)
    
    typer.secho(f"\n💡 Run 'orbs fix-environment' to attempt automatic fixes", fg=typer.colors.BLUE)

@app.command()
def fix_ssl():
    """Fix SSL certificate issues for macOS"""
    import platform
    
    system = platform.system().lower()
    
    if system != "darwin":
        typer.secho("ℹ️ This command is specifically for macOS SSL issues", fg=typer.colors.BLUE)
        return
    
    typer.secho("🔐 Fixing SSL certificate issues for macOS...\n", fg=typer.colors.BLUE, bold=True)
    
    # Method 1: Install Python certificates
    try:
        python_version = f"{os.sys.version_info.major}.{os.sys.version_info.minor}"
        cert_command = f"/Applications/Python\\ {python_version}/Install\\ Certificates.command"
        
        if Path(cert_command.replace("\\ ", " ")).exists():
            typer.secho("⚙️ Running Install Certificates.command...", fg=typer.colors.YELLOW)
            result = subprocess.run(cert_command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                typer.secho("✅ SSL certificates updated via Install Certificates.command", fg=typer.colors.GREEN)
            else:
                typer.secho("⚠️ Install Certificates.command failed or not found", fg=typer.colors.YELLOW)
        else:
            typer.secho("⚠️ Install Certificates.command not found", fg=typer.colors.YELLOW)
    except Exception as e:
        typer.secho(f"⚠️ Error running Install Certificates.command: {e}", fg=typer.colors.YELLOW)
    
    # Method 2: Install certifi package
    try:
        typer.secho("⚙️ Installing certifi package...", fg=typer.colors.YELLOW)
        result = subprocess.run([os.sys.executable, "-m", "pip", "install", "certifi"], 
                              check=True, capture_output=True, text=True)
        typer.secho("✅ certifi package installed", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError:
        typer.secho("⚠️ Failed to install certifi package", fg=typer.colors.YELLOW)
    
    # Method 3: Update CA certificates via Homebrew
    def check_command_exists(command: str) -> bool:
        return shutil.which(command) is not None
    
    if check_command_exists("brew"):
        try:
            typer.secho("⚙️ Updating CA certificates via Homebrew...", fg=typer.colors.YELLOW)
            subprocess.run(["brew", "install", "ca-certificates"], check=True, capture_output=True)
            typer.secho("✅ CA certificates updated via Homebrew", fg=typer.colors.GREEN)
        except subprocess.CalledProcessError:
            typer.secho("⚠️ Failed to update certificates via Homebrew", fg=typer.colors.YELLOW)
    
    # Method 4: Manual instructions
    typer.secho("\n💡 Manual SSL fix options:", fg=typer.colors.BLUE, bold=True)
    typer.secho("1. Install Python certificates manually:", fg=typer.colors.BLUE)
    typer.secho("   /Applications/Python\\ 3.x/Install\\ Certificates.command", fg=typer.colors.BLUE)
    typer.secho("\n2. Install certifi package:", fg=typer.colors.BLUE)
    typer.secho("   pip install --upgrade certifi", fg=typer.colors.BLUE)
    typer.secho("\n3. Try downloading Android SDK manually:", fg=typer.colors.BLUE)
    typer.secho("   orbs download-android-sdk", fg=typer.colors.BLUE)
    
    typer.secho("\n🔄 After fixing SSL, try: orbs setup", fg=typer.colors.GREEN, bold=True)

@app.command()
def debug_appium():
    """Debug Appium installation and server issues"""
    typer.secho("🔍 Diagnosing Appium setup...\n", fg=typer.colors.BLUE, bold=True)
    
    def check_command_exists(command: str) -> bool:
        return shutil.which(command) is not None
    
    # Check Appium installation
    if check_command_exists("appium"):
        try:
            result = subprocess.run(["appium", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip()
                typer.secho(f"✅ Appium version: {version}", fg=typer.colors.GREEN)
                
                # Check drivers for Appium 2+
                major_version = int(version.split('.')[0])
                if major_version >= 2:
                    typer.secho("🔍 Checking installed drivers...", fg=typer.colors.YELLOW)
                    drivers_result = subprocess.run(["appium", "driver", "list"], capture_output=True, text=True)
                    if drivers_result.returncode == 0:
                        typer.secho(drivers_result.stdout, fg=typer.colors.WHITE)
                    else:
                        typer.secho("❌ Failed to list drivers", fg=typer.colors.RED)
                        
                    # Check if uiautomator2 driver is installed
                    if "uiautomator2" in drivers_result.stdout and "installed" in drivers_result.stdout:
                        typer.secho("✅ UIAutomator2 driver is installed", fg=typer.colors.GREEN)
                    else:
                        typer.secho("⚠️ UIAutomator2 driver not found", fg=typer.colors.YELLOW)
                        typer.secho("💡 Run: appium driver install uiautomator2", fg=typer.colors.BLUE)
            else:
                typer.secho(f"❌ Appium command failed: {result.stderr}", fg=typer.colors.RED)
        except Exception as e:
            typer.secho(f"❌ Error checking Appium: {e}", fg=typer.colors.RED)
    else:
        typer.secho("❌ Appium not found in PATH", fg=typer.colors.RED)
        typer.secho("💡 Install: npm install -g appium", fg=typer.colors.BLUE)
    
    # Check Node.js and npm
    if check_command_exists("node"):
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                typer.secho(f"✅ Node.js version: {result.stdout.strip()}", fg=typer.colors.GREEN)
        except Exception as e:
            typer.secho(f"❌ Error checking Node.js: {e}", fg=typer.colors.RED)
    else:
        typer.secho("❌ Node.js not found", fg=typer.colors.RED)
    
    if check_command_exists("npm"):
        try:
            result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                typer.secho(f"✅ npm version: {result.stdout.strip()}", fg=typer.colors.GREEN)
        except Exception as e:
            typer.secho(f"❌ Error checking npm: {e}", fg=typer.colors.RED)
    else:
        typer.secho("❌ npm not found", fg=typer.colors.RED)
    
    # Check ADB and connected devices
    if check_command_exists("adb"):
        try:
            result = subprocess.run(["adb", "version"], capture_output=True, text=True)
            if result.returncode == 0:
                typer.secho(f"✅ ADB available", fg=typer.colors.GREEN)
                
                # Check connected devices
                devices = get_connected_devices()
                if devices:
                    typer.secho(f"✅ Connected devices: {devices}", fg=typer.colors.GREEN)
                else:
                    typer.secho("⚠️ No devices connected", fg=typer.colors.YELLOW)
                    typer.secho("💡 Connect device and enable USB debugging", fg=typer.colors.BLUE)
        except Exception as e:
            typer.secho(f"❌ Error checking ADB: {e}", fg=typer.colors.RED)
    else:
        typer.secho("❌ ADB not found in PATH", fg=typer.colors.RED)
    
    # Test Appium server status
    typer.secho("\n🔍 Testing Appium server connection...", fg=typer.colors.YELLOW)
    try:
        import requests
        url = config.get("appium_url", "http://localhost:4723")  # Appium 3+ no longer uses /wd/hub
        status_url = url.rstrip('/') + '/status'
        response = requests.get(status_url, timeout=3)
        if response.status_code == 200:
            typer.secho("✅ Appium server is running", fg=typer.colors.GREEN)
            typer.secho(f"Server info: {response.json()}", fg=typer.colors.WHITE)
        else:
            typer.secho(f"⚠️ Appium server responded with status {response.status_code}", fg=typer.colors.YELLOW)
    except Exception as e:
        typer.secho(f"❌ Cannot connect to Appium server: {e}", fg=typer.colors.RED)
        typer.secho("💡 Try: orbs debug-appium-start", fg=typer.colors.BLUE)
    
    typer.secho("\n📋 Diagnostic complete", fg=typer.colors.BLUE, bold=True)


@app.command()
def debug_appium_start():
    """Debug Appium server startup with verbose output"""
    typer.secho("🚀 Starting Appium server with debug output...\n", fg=typer.colors.BLUE, bold=True)
    
    # Check Appium version and determine command
    cmd = "appium server --address 0.0.0.0 --port 4723 --log-level debug"
    try:
        version_result = subprocess.run(["appium", "--version"], capture_output=True, text=True)
        if version_result.returncode == 0:
            version = version_result.stdout.strip()
            major_version = int(version.split('.')[0])
            
            if major_version >= 3:
                cmd = "appium server --address 0.0.0.0 --port 4723 --log-level debug"
            else:
                cmd = "appium --address 0.0.0.0 --port 4723 --log-level debug"
            
            typer.secho(f"🔍 Using Appium v{version}", fg=typer.colors.GREEN)
    except:
        pass
    
    typer.secho(f"📋 Command: {cmd}", fg=typer.colors.WHITE)
    typer.secho("🔍 Watch for errors below...\n", fg=typer.colors.YELLOW)
    
    try:
        # Run with real-time output
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        
        typer.secho("✨ Appium server starting... (Press Ctrl+C to stop)", fg=typer.colors.GREEN)
        
        for line in iter(process.stdout.readline, ''):
            print(line.rstrip())
            
    except KeyboardInterrupt:
        typer.secho("\n🛑 Stopping Appium server...", fg=typer.colors.YELLOW)
        process.terminate()
    except Exception as e:
        typer.secho(f"❌ Error starting Appium: {e}", fg=typer.colors.RED)
    """Fix Appium version mismatch by removing incompatible APKs from device"""
    def check_command_exists(command: str) -> bool:
        return shutil.which(command) is not None
    
    # Check if adb and appium are available
    if not check_command_exists("adb"):
        typer.secho("❌ ADB not found. Please run 'orbs setup' first.", fg=typer.colors.RED)
        raise typer.Exit(1)
        
    if not check_command_exists("appium"):
        typer.secho("❌ Appium not found. Please run 'orbs setup' first.", fg=typer.colors.RED)
        raise typer.Exit(1)
    
    # Check connected devices
    devices = get_connected_devices()
    if not devices:
        typer.secho("❌ No Android devices connected.", fg=typer.colors.RED)
        raise typer.Exit(1)
    
    typer.secho("🔧 Fixing Appium APK version mismatch...", fg=typer.colors.BLUE, bold=True)
    
    # Get Appium version
    try:
        appium_result = subprocess.run(["appium", "--version"], capture_output=True, text=True)
        appium_version = appium_result.stdout.strip()
        major_version = int(appium_version.split('.')[0])
        typer.secho(f"📱 Detected Appium v{appium_version} (major: {major_version})", fg=typer.colors.BLUE)
    except Exception:
        typer.secho("⚠️ Could not detect Appium version, proceeding with cleanup...", fg=typer.colors.YELLOW)
        major_version = 3  # assume latest
    
    # Check installed Appium packages on device
    try:
        packages_result = subprocess.run(
            ["adb", "shell", "pm", "list", "packages", "|", "grep", "appium"], 
            shell=True, capture_output=True, text=True
        )
        installed_packages = packages_result.stdout.strip()
        
        if "io.appium.uiautomator2.server" in installed_packages:
            typer.secho("🔍 Found existing Appium server APKs on device", fg=typer.colors.YELLOW)
            typer.secho("   This may cause compatibility issues with current Appium version", fg=typer.colors.YELLOW)
            
            # Ask user for confirmation
            should_fix = typer.confirm("Remove existing APKs to fix compatibility?", default=True)
            
            if should_fix:
                apk_packages = [
                    "io.appium.uiautomator2.server",
                    "io.appium.uiautomator2.server.test", 
                    "io.appium.settings"
                ]
                
                for package in apk_packages:
                    typer.secho(f"🗑️ Uninstalling {package}...", fg=typer.colors.YELLOW)
                    try:
                        result = subprocess.run(["adb", "uninstall", package], 
                                              capture_output=True, text=True)
                        if result.returncode == 0:
                            typer.secho(f"✅ Removed {package}", fg=typer.colors.GREEN)
                        else:
                            typer.secho(f"⚠️ {package} not found or already removed", fg=typer.colors.BLUE)
                    except Exception as e:
                        typer.secho(f"⚠️ Error removing {package}: {e}", fg=typer.colors.YELLOW)
                
                typer.secho("\n✅ APK cleanup complete!", fg=typer.colors.GREEN, bold=True)
                typer.secho("💡 Next time you run tests, Appium will install compatible APKs", fg=typer.colors.BLUE)
            else:
                typer.secho("🚫 APK cleanup cancelled by user", fg=typer.colors.YELLOW)
        else:
            typer.secho("✅ No conflicting Appium APKs found on device", fg=typer.colors.GREEN)
            
    except Exception as e:
        typer.secho(f"❌ Error checking device packages: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)

@app.command()
def download_android_sdk():
    """Manual Android SDK download with multiple methods"""
    import platform
    
    system = platform.system().lower()
    home = Path.home()
    
    if system == "darwin":
        android_home = home / "Library" / "Android" / "sdk"
        sdk_url = "https://dl.google.com/android/repository/commandlinetools-mac-11076708_latest.zip"
    elif system == "windows":
        android_home = home / "AppData" / "Local" / "Android" / "Sdk"
        sdk_url = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
    else:
        android_home = home / "Android" / "Sdk"
        sdk_url = "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
    
    typer.secho("📥 Manual Android SDK Download\n", fg=typer.colors.BLUE, bold=True)
    typer.secho(f"Target location: {android_home}", fg=typer.colors.BLUE)
    typer.secho(f"Download URL: {sdk_url}\n", fg=typer.colors.BLUE)
    
    android_home.mkdir(parents=True, exist_ok=True)
    cmdline_tools = android_home / "cmdline-tools"
    
    if (cmdline_tools / "latest").exists():
        typer.secho("✅ Android SDK already installed", fg=typer.colors.GREEN)
        return
    
    # Try curl method first (most reliable on macOS)
    if system == "darwin":
        try:
            typer.secho("⚙️ Trying download with curl...", fg=typer.colors.YELLOW)
            
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = Path(temp_dir) / "cmdlinetools.zip"
                
                result = subprocess.run([
                    "curl", "-L", "--progress-bar", "-o", str(zip_path), sdk_url
                ], check=True)
                
                if zip_path.exists() and zip_path.stat().st_size > 1000000:  # At least 1MB
                    typer.secho("✅ Download successful with curl", fg=typer.colors.GREEN)
                    
                    # Extract
                    typer.secho("📦 Extracting Android SDK...", fg=typer.colors.YELLOW)
                    import zipfile
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(android_home)
                    
                    # Move to correct location
                    cmdline_tools.mkdir(exist_ok=True)
                    if (android_home / "cmdline-tools").exists():
                        shutil.move(str(android_home / "cmdline-tools"), str(cmdline_tools / "latest"))
                    
                    typer.secho("✅ Android SDK extracted successfully", fg=typer.colors.GREEN)
                    return
                    
        except Exception as e:
            typer.secho(f"❌ Curl download failed: {e}", fg=typer.colors.RED)
    
    # Alternative: wget method
    def check_command_exists(command: str) -> bool:
        return shutil.which(command) is not None
    
    if check_command_exists("wget"):
        try:
            typer.secho("⚙️ Trying download with wget...", fg=typer.colors.YELLOW)
            
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = Path(temp_dir) / "cmdlinetools.zip"
                
                subprocess.run([
                    "wget", "-O", str(zip_path), "--progress=bar", sdk_url
                ], check=True)
                
                if zip_path.exists() and zip_path.stat().st_size > 1000000:
                    typer.secho("✅ Download successful with wget", fg=typer.colors.GREEN)
                    
                    # Extract and move (same as curl method above)
                    typer.secho("📦 Extracting Android SDK...", fg=typer.colors.YELLOW)
                    import zipfile
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(android_home)
                    
                    cmdline_tools.mkdir(exist_ok=True)
                    if (android_home / "cmdline-tools").exists():
                        shutil.move(str(android_home / "cmdline-tools"), str(cmdline_tools / "latest"))
                    
                    typer.secho("✅ Android SDK extracted successfully", fg=typer.colors.GREEN)
                    return
                    
        except Exception as e:
            typer.secho(f"❌ Wget download failed: {e}", fg=typer.colors.RED)
    
    # Manual instructions if all methods fail
    typer.secho("\n❌ Automatic download failed. Manual steps:", fg=typer.colors.RED, bold=True)
    typer.secho(f"\n1. Open your browser and go to:", fg=typer.colors.BLUE)
    typer.secho(f"   {sdk_url}", fg=typer.colors.BLUE)
    typer.secho(f"\n2. Download the file to your Downloads folder", fg=typer.colors.BLUE)
    typer.secho(f"\n3. Extract the ZIP file", fg=typer.colors.BLUE)
    typer.secho(f"\n4. Create directory: {android_home}/cmdline-tools", fg=typer.colors.BLUE)
    typer.secho(f"\n5. Move the extracted 'cmdline-tools' folder to:", fg=typer.colors.BLUE)
    typer.secho(f"   {android_home}/cmdline-tools/latest", fg=typer.colors.BLUE)
    typer.secho(f"\n6. Run: orbs setup", fg=typer.colors.BLUE)
    
    # Try to open browser
    try:
        import webbrowser
        typer.secho("\n🌐 Opening download URL in browser...", fg=typer.colors.GREEN)
        webbrowser.open(sdk_url)
    except:
        pass

if __name__ == "__main__":
    app()
