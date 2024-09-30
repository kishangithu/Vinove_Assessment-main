import os
import json
import time
import threading
import boto3
from botocore.exceptions import NoCredentialsError
from PIL import ImageGrab, ImageFilter
from pynput import mouse, keyboard
import psutil
from cryptography.fernet import Fernet
from tzlocal import get_localzone
import schedule

aws_access_key = os.getenv("AWS_ACCESS_KEY")
aws_secret_key = os.getenv("AWS_SECRET_KEY")
aws_buket_name = os.getenv("AWS_S3_BUCKET")  # Correct variable name

s3 = boto3.client('s3', 
                  aws_access_key_id=aws_access_key,
                  aws_secret_access_key=aws_secret_key)


def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Config file not found. Exiting.")
        exit(1)

# Upload to Amazon S3
def upload_to_s3(file_name):
    bucket_name = config.get("s3_bucket_name")
    if not bucket_name:
        print("S3 bucket name not provided in config")
        return

    try:
        s3.upload_file(file_name, bucket_name, os.path.basename(file_name))
        print(f"Uploaded {file_name} to S3 bucket '{bucket_name}'")
    except FileNotFoundError:
        print(f"The file {file_name} was not found")
    except NoCredentialsError:
        print("Credentials not available")
    except PartialCredentialsError:
        print("Incomplete credentials provided")

# Encrypt and decrypt functions for security
def generate_key():
    return Fernet.generate_key()

def encrypt_file(file_name, key):
    fernet = Fernet(key)
    with open(file_name, "rb") as file:
        original = file.read()
    encrypted = fernet.encrypt(original)
    with open(file_name, "wb") as encrypted_file:
        encrypted_file.write(encrypted)

def decrypt_file(file_name, key):
    fernet = Fernet(key)
    with open(file_name, "rb") as file:
        encrypted = file.read()
    decrypted = fernet.decrypt(encrypted)
    with open(file_name, "wb") as decrypted_file:
        decrypted_file.write(decrypted)

# Capture screenshot
def capture_screenshot():
    try:
        print("Starting to capture screenshot...")
        screenshot = ImageGrab.grab()  # This may fail on some platforms (Linux servers)
        if config.get("screenshot_blurred", False):
            print("Applying blur to screenshot...")
            screenshot = screenshot.filter(ImageFilter.GaussianBlur(15))
        file_name = f"screenshot_{int(time.time())}.png"
        screenshot.save(file_name)

        print(f"Screenshot saved as {file_name}")

        encrypt_file(file_name, encryption_key)
        upload_to_s3(file_name)
        print(f"Captured and uploaded screenshot: {file_name}")

    except Exception as e:
        print(f"Error capturing screenshot: {e}")


# Monitor user activity
def on_move(x, y):
    print(f"Mouse moved to {(x, y)}")

def on_click(x, y, button, pressed):
    print(f"Mouse {'pressed' if pressed else 'released'} at {(x, y)}")

def on_key_press(key):
    print(f"Key {key} pressed")

# Set up mouse and keyboard listeners
def start_listeners():
    mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click)
    keyboard_listener = keyboard.Listener(on_press=on_key_press)

    mouse_listener.start()
    keyboard_listener.start()

# Schedule screenshots
def schedule_screenshots():
    schedule.every(config["screenshot_interval"]).seconds.do(capture_screenshot)
    while True:
        schedule.run_pending()
        time.sleep(1)

# Detect time zone
def detect_time_zone():
    local_tz = get_localzone()
    print(f"Detected time zone: {local_tz}")

# Low battery detection
def check_battery_status():
    try:
        battery = psutil.sensors_battery()
        if battery is None:
            print("No battery information available.")
            return

        print(
            f"Battery status: {battery.percent}% {'(Plugged in)' if battery.power_plugged else '(Not plugged in)'}"
        )

        if battery.percent < 20 and not battery.power_plugged:
            print("Warning: Battery low! Please connect your charger.")
    except Exception as e:
        print(f"Error checking battery status: {e}")

# Main function
if __name__ == "__main__":
    config = load_config()
    encryption_key = generate_key()

    detect_time_zone()
    capture_screenshot()

    # Prompt user for screenshot interval
    user_interval = input("Enter screenshot interval in minutes (e.g., 5 for 5 minutes, 10 for 10 minutes): ").strip()
    
    try:
        # Convert to seconds and update config
        screenshot_interval_minutes = int(user_interval)
        config["screenshot_interval"] = screenshot_interval_minutes * 60  # Convert minutes to seconds
        print(f"Screenshot interval set to {screenshot_interval_minutes} minutes.")
    except ValueError:
        print("Invalid input. Setting default screenshot interval to 5 minutes.")
        config["screenshot_interval"] = 5 * 60  # Default to 5 minutes if input is invalid

    monitor_activity = (
        input("Do you want to monitor user activity? (yes/no): ").strip().lower()
        == "yes"
    )
    capture_screenshots_enabled = (
        input("Do you want to capture screenshots? (yes/no): ").strip().lower() == "yes"
    )
    auto_update_enabled = (
        input("Do you want to enable auto-update? (yes/no): ").strip().lower() == "yes"
    )
    low_battery_detection_enabled = (
        input("Do you want to enable low battery detection? (yes/no): ").strip().lower()
        == "yes"
    )

    if auto_update_enabled:
        # Call your auto-update function if applicable
        pass

    if monitor_activity:
        start_listeners()

    if capture_screenshots_enabled:
        screenshot_thread = threading.Thread(target=schedule_screenshots)
        screenshot_thread.start()

    if low_battery_detection_enabled:
        def battery_check_loop():
            while True:
                check_battery_status()
                time.sleep(60)

        battery_check_thread = threading.Thread(target=battery_check_loop)
        battery_check_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting the application.")
