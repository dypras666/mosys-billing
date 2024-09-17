import subprocess
import logging

def run_adb_command(ip, command):
    full_command = f"adb connect {ip}:5555 && adb shell {command}"
    try:
        result = subprocess.run(full_command, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            logging.error(f"ADB command failed: {result.stderr}")
            return None
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logging.error(f"ADB command timed out for IP: {ip}")
        return None
    except Exception as e:
        logging.error(f"Error running ADB command: {str(e)}")
        return None