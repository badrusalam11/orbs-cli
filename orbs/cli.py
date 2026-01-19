import os
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
from orbs.config import config


app = typer.Typer()
setup_app = typer.Typer()
app.add_typer(setup_app, name="setup")

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


def get_available_environments():
    """Get list of available environment files from environments directory"""
    env_dir = Path.cwd() / "environments"
    if not env_dir.exists():
        return []
    
    env_files = list(env_dir.glob("*.yml"))
    environments = [f.stem for f in env_files if f.stem != "README"]
    return sorted(environments)


def choose_environment() -> str:
    """Prompt user to choose an environment via arrow keys"""
    environments = get_available_environments()
    
    if not environments:
        typer.secho("❌ No environment files found in 'environments/' directory", fg=typer.colors.RED)
        typer.secho("💡 Create environment files like: environments/dev.yml, environments/uat.yml", fg=typer.colors.YELLOW)
        raise typer.Exit(1)
    
    choice = inquirer.select(
        message="Select environment:",
        choices=environments,
        default="default" if "default" in environments else environments[0]
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
    url = config.get("appium_url", "http://localhost:4723/wd/hub")
    status_url = url.rstrip('/') + '/status'
    try:
        if requests.get(status_url, timeout=2).status_code == 200:
            return
    except Exception:
        pass

    # Parse host and port
    parsed = urlparse(url)
    host = parsed.hostname or '0.0.0.0'
    port = parsed.port or 4723
    typer.secho(f"⚙️  Starting Appium server at {host}:{port}", fg=typer.colors.YELLOW)
    cmd = f"appium --address {host} --port {port}"
    try:
        # Use shell=True for Windows to pick up appium.cmd
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        # fallback to npx if installed
        try:
            subprocess.Popen(f"npx appium --address {host} --port {port}", shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            typer.secho(
                "❌ Could not start Appium. Ensure 'appium' or 'npx appium' is in your PATH.",
                fg=typer.colors.RED
            )
            raise typer.Exit(1)
    # Wait for server to be ready
    for _ in range(10):
        try:
            if requests.get(status_url, timeout=2).status_code == 200:
                typer.secho("✅ Appium server is up", fg=typer.colors.GREEN)
                return
        except Exception:
            time.sleep(1)
    typer.secho("❌ Failed to start Appium server", fg=typer.colors.RED)
    raise typer.Exit(1)


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
    env: str = typer.Option(None, "--env", "-e", help="Environment to run (dev, uat, staging, prod)"),
    platform: str = typer.Option(None, "--platform", "-p", help="Platform to run tests on (android, chrome, firefox)"),
    device_id: str = typer.Option(None, "--deviceId", help="Device ID for mobile testing")
):
    """Run a suite/case/feature with specified environment"""
    
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
    
    # Determine which environment to use
    selected_env = None
    
    # Priority 1: CLI argument --env
    if env:
        selected_env = env
        typer.secho(f"🌍 Using environment from CLI argument: {selected_env}", fg=typer.colors.CYAN)
    
    # Priority 2: ORBS_ENV environment variable
    elif os.getenv("ORBS_ENV"):
        selected_env = os.getenv("ORBS_ENV")
        typer.secho(f"🌍 Using environment from ORBS_ENV: {selected_env}", fg=typer.colors.CYAN)
    
    # Priority 3: Check .env file
    elif Path(".env").exists():
        load_dotenv()
        env_from_file = os.getenv("ORBS_ENV")
        if env_from_file:
            selected_env = env_from_file
            typer.secho(f"🌍 Using environment from .env file: {selected_env}", fg=typer.colors.CYAN)
    
    # Priority 4: Prompt user to select
    if not selected_env:
        typer.secho("⚠️  No environment specified. Please select one:", fg=typer.colors.YELLOW)
        selected_env = choose_environment()
        typer.secho(f"🌍 Selected environment: {selected_env}", fg=typer.colors.GREEN)
    
    # Validate that the environment file exists
    env_file_path = Path("environments") / f"{selected_env}.yml"
    if not env_file_path.exists():
        typer.secho(f"❌ Environment file not found: {env_file_path}", fg=typer.colors.RED)
        typer.secho(f"💡 Available environments: {', '.join(get_available_environments())}", fg=typer.colors.YELLOW)
        raise typer.Exit(1)
    
    # Set ORBS_ENV so config.py will load the correct environment
    os.environ["ORBS_ENV"] = selected_env
    
    # Execute the run with platform and device_id parameters
    run(target, platform, device_id)

@app.command()
def select_device():
    devices = get_connected_devices()
    device_name = choose_device(devices)
    write_device_property(device_name)    

@setup_app.command("android")
def setup_android():
    """Install required dependencies for Android mobile testing"""
    def install_nodejs_on_windows():
        import tempfile
        import urllib.request

        NODE_URL = "https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi"  # LTS version
        temp_dir = tempfile.gettempdir()
        installer_path = os.path.join(temp_dir, "nodejs_installer.msi")

        typer.secho("⬇️ Downloading Node.js installer...", fg=typer.colors.YELLOW)
        urllib.request.urlretrieve(NODE_URL, installer_path)

        typer.secho("⚙️ Running Node.js installer (silent)...", fg=typer.colors.YELLOW)
        try:
            subprocess.run(
                ["msiexec", "/i", installer_path, "/qn", "/norestart"],
                check=True,
            )
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
        # macOS/Linux fallback
        if shutil.which('brew'):
            subprocess.run("brew install node", shell=True, check=True)
        elif shutil.which('apt'):
            subprocess.run("sudo apt update && sudo apt install -y nodejs npm", shell=True, check=True)
        else:
            typer.secho("❌ Could not install Node.js automatically. Install it manually from https://nodejs.org/", fg=typer.colors.RED)
            raise typer.Exit(1)
            
    # Ensure Node.js & npm
    try:
        subprocess.run("npm --version", shell=True, check=True, stdout=subprocess.DEVNULL)
        typer.secho("✅ npm detected", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError:
        typer.secho("⚙️ npm not found. Installing Node.js...", fg=typer.colors.YELLOW)
        if os.name == 'nt':
            install_nodejs_on_windows()
        else:
            install_nodejs_on_posix()
    
    # Check & install Appium dependencies only if not installed
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
                typer.secho(f"❌ Failed to install {pkg}. Make sure npm works.", fg=typer.colors.RED)
                raise typer.Exit(1)

    typer.secho("✅ All mobile dependencies are ready", fg=typer.colors.GREEN)

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

if __name__ == "__main__":
    app()
