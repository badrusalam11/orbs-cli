from orbs.exception import DependencyException
from orbs.guard import orbs_guard
from orbs.config import config
from orbs.thread_context import get_context

@orbs_guard(DependencyException)
def check_dependencies():
    from orbs.cli import choose_device, ensure_appium_server, get_connected_devices, write_device_property

        # Start Appium server if needed
    ensure_appium_server()

    # Read default deviceName from appium.properties if present
    device_name = get_context("device_id", config.get("deviceName", ""))
    
    # If a placeholder or empty, prompt selection
    if not device_name or device_name.lower() in ('', 'auto', 'detect'):
        print("No deviceName set in context or config. Please select a device.")
        devices = get_connected_devices()
        device_name = choose_device(devices)
        write_device_property(device_name)