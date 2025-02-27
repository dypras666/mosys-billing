import asyncio
import json
import logging
import socket
import threading
import time
from flask import Flask, request, jsonify
import subprocess
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Global variables
devices = {}
DEVICES_DATA_FILE = 'hdmi_cec_devices.json'

# CEC command codes (based on the CEC specification)
cec_commands = {
    'power_on': '0x04',                # Image View On
    'power_off': '0x36',               # Standby
    'volume_up': '0x41',               # Volume Up
    'volume_down': '0x42',             # Volume Down
    'mute': '0x43',                    # Mute
    'input_hdmi1': '0x67:0x10',        # Set HDMI 1 as input
    'input_hdmi2': '0x67:0x20',        # Set HDMI 2 as input
    'input_hdmi3': '0x67:0x30',        # Set HDMI 3 as input
    'menu': '0x09',                    # Menu
    'up': '0x01',                      # Up
    'down': '0x02',                    # Down
    'left': '0x03',                    # Left
    'right': '0x04',                   # Right
    'select': '0x00',                  # Select
    'back': '0x0D',                    # Back
    'home': '0x46',                    # Home
    'play': '0x44',                    # Play
    'pause': '0x46',                   # Pause
    'stop': '0x45',                    # Stop
    'forward': '0x49',                 # Fast forward
    'rewind': '0x48',                  # Rewind
}

def load_devices():
    """Load devices from the JSON file"""
    global devices
    try:
        with open(DEVICES_DATA_FILE, 'r') as f:
            devices = json.load(f)
        logger.info(f"Loaded {len(devices)} devices from {DEVICES_DATA_FILE}")
    except FileNotFoundError:
        devices = {}
        logger.info(f"No devices file found, starting with empty list")
    except json.JSONDecodeError:
        devices = {}
        logger.error(f"Error decoding JSON from {DEVICES_DATA_FILE}, starting with empty list")

def save_devices():
    """Save devices to the JSON file"""
    with open(DEVICES_DATA_FILE, 'w') as f:
        json.dump(devices, f, indent=2)
    logger.debug(f"Saved {len(devices)} devices to {DEVICES_DATA_FILE}")

def check_device_status(ip):
    """
    Periodically check if a device is online and get its status
    """
    while True:
        try:
            # Check if device is reachable
            response_time = ping_device(ip)
            if response_time is not None:
                devices[ip]['status'] = 'Online'
                devices[ip]['response_time'] = f"{response_time:.2f} ms"
                
                # Try to get additional info via HDMI-CEC
                try:
                    # Get power status
                    power_status = get_power_status(ip)
                    if power_status:
                        devices[ip]['power_status'] = power_status
                except Exception as e:
                    logger.error(f"Error getting power status for {ip}: {str(e)}")
            else:
                devices[ip]['status'] = 'Offline'
                devices[ip]['response_time'] = 'N/A'
                
            save_devices()
        except Exception as e:
            devices[ip]['status'] = 'Error'
            devices[ip]['response_time'] = 'N/A'
            logger.error(f"Error checking status for {ip}: {str(e)}")
            
        # Wait before next check
        time.sleep(10)

def ping_device(ip):
    """
    Ping a device to check if it's online and get response time
    """
    try:
        # Create socket connection to check if device is reachable
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        
        # Try standard HDMI-CEC port or fallback to HTTP port for web interface
        start_time = time.time()
        result = s.connect_ex((ip, 9740))  # 9740 is often used for HDMI-CEC over IP
        if result != 0:
            # Try HTTP port as fallback
            result = s.connect_ex((ip, 80))
        end_time = time.time()
        
        s.close()
        
        if result == 0:
            return (end_time - start_time) * 1000  # Return in milliseconds
        return None
    except Exception as e:
        logger.error(f"Error pinging {ip}: {str(e)}")
        return None

def get_power_status(ip):
    """
    Get the power status of a device via HDMI-CEC
    """
    # This would typically involve sending a CEC query to the device
    # Simplified implementation assuming a UDP or TCP socket connection
    try:
        # In a real implementation, this would use the appropriate CEC protocol
        # to query the device power status
        return "Unknown"  # In a real implementation, return "On" or "Off"
    except Exception as e:
        logger.error(f"Error getting power status for {ip}: {str(e)}")
        return "Unknown"

def send_cec_command(ip, command):
    """
    Send a CEC command to a device
    """
    if command not in cec_commands:
        logger.error(f"Unknown CEC command: {command}")
        return False
        
    # Get the CEC command code
    cec_code = cec_commands[command]
    
    try:
        # In a production environment, we would use a CEC library or directly communicate
        # with the HDMI-CEC hardware. For this example, we'll just log the command.
        logger.info(f"Sending CEC command {command} ({cec_code}) to {ip}")
        
        # This would typically use libCEC or a similar library to send the command
        # For example with 'cec-client' if it's installed:
        if os.path.exists("/usr/bin/cec-client"):
            # Example using cec-client (if available)
            # Format: echo "tx 10:04" | cec-client -s -d 1
            cmd = f'echo "tx {cec_code}" | cec-client -s -d 1'
            try:
                result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, timeout=5)
                logger.debug(f"CEC command output: {result.stdout}")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"CEC command failed: {e}")
                logger.error(f"Error output: {e.stderr}")
                return False
        else:
            # We would connect to the CEC bridge on the TV's IP
            # This is a placeholder for actual implementation
            logger.warning("No CEC client found, this is a simulation")
            return True  # Simulate success
            
    except Exception as e:
        logger.error(f"Error sending CEC command to {ip}: {str(e)}")
        return False

# -------------------- API Endpoints ---------------------

@app.route('/add_device', methods=['POST'])
def add_device():
    """Add a new HDMI-CEC device"""
    data = request.json
    name = data.get('name')
    ip = data.get('ip')
    
    if not name or not ip:
        return jsonify({"error": "Name and IP are required"}), 400
        
    if ip in devices:
        return jsonify({"error": "Device with this IP already exists"}), 400
        
    # Add the device
    devices[ip] = {
        'name': name,
        'status': 'Checking',
        'response_time': 'N/A',
        'added_on': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Save the updated devices list
    save_devices()
    
    # Start a thread to monitor this device
    threading.Thread(target=check_device_status, args=(ip,), daemon=True).start()
    
    logger.info(f"Added new device: {name} ({ip})")
    return jsonify({
        "message": "Device added successfully", 
        "device": devices[ip]
    }), 200

@app.route('/remove_device', methods=['POST'])
def remove_device():
    """Remove an HDMI-CEC device"""
    data = request.json
    ip = data.get('ip')
    
    if ip not in devices:
        return jsonify({"error": "Device not found"}), 404
        
    # Remove the device
    device_info = devices.pop(ip)
    save_devices()
    
    logger.info(f"Removed device: {device_info['name']} ({ip})")
    return jsonify({"message": "Device removed successfully"}), 200

@app.route('/edit_device', methods=['POST'])
def edit_device():
    """Edit an HDMI-CEC device"""
    data = request.json
    old_ip = data.get('old_ip')
    new_name = data.get('new_name')
    new_ip = data.get('new_ip')
    
    if old_ip not in devices:
        return jsonify({"error": "Device not found"}), 404
        
    if new_ip != old_ip and new_ip in devices:
        return jsonify({"error": "New IP already exists"}), 400
        
    # Update the device
    device_info = devices.pop(old_ip)
    device_info['name'] = new_name
    devices[new_ip] = device_info
    
    # Save the updated devices list
    save_devices()
    
    logger.info(f"Edited device: {new_name} ({new_ip})")
    return jsonify({
        "message": "Device edited successfully", 
        "device": devices[new_ip]
    }), 200

@app.route('/device_status', methods=['GET'])
def get_device_status():
    """Get status of all HDMI-CEC devices"""
    return jsonify(devices)

@app.route('/send_command', methods=['POST'])
def send_command():
    """Send a command to an HDMI-CEC device"""
    data = request.json
    ip = data.get('ip')
    command = data.get('command')
    
    if ip not in devices:
        return jsonify({"error": "Device not found"}), 404
        
    if not command or command not in cec_commands:
        return jsonify({
            "error": "Invalid command", 
            "available_commands": list(cec_commands.keys())
        }), 400
        
    # Send the command
    result = send_cec_command(ip, command)
    
    if result:
        logger.info(f"Successfully sent '{command}' command to {ip}")
        return jsonify({"message": f"Command '{command}' sent successfully"}), 200
    else:
        logger.error(f"Failed to send '{command}' command to {ip}")
        return jsonify({"error": f"Failed to send '{command}' command"}), 500

@app.route('/batch_command', methods=['POST'])
def batch_command():
    """Send a command to multiple HDMI-CEC devices"""
    data = request.json
    ips = data.get('ips', [])
    command = data.get('command')
    
    if not ips:
        return jsonify({"error": "No devices specified"}), 400
        
    if not command or command not in cec_commands:
        return jsonify({
            "error": "Invalid command", 
            "available_commands": list(cec_commands.keys())
        }), 400
        
    # Send the command to each device
    results = {}
    for ip in ips:
        if ip in devices:
            result = send_cec_command(ip, command)
            if result:
                results[ip] = {
                    "status": "success", 
                    "message": f"Command '{command}' sent successfully"
                }
            else:
                results[ip] = {
                    "status": "error", 
                    "message": f"Failed to send '{command}' command"
                }
        else:
            results[ip] = {"status": "error", "message": "Device not found"}
    
    logger.info(f"Batch command '{command}' sent to {len(ips)} devices")
    return jsonify({"results": results}), 200

@app.route('/scan_network', methods=['POST'])
def scan_network():
    """Scan the network for HDMI-CEC devices"""
    data = request.json
    subnet = data.get('subnet', '192.168.1')
    start = data.get('start', 1)
    end = data.get('end', 254)
    
    if end - start > 254:
        return jsonify({"error": "Scan range too large"}), 400
        
    def scan_thread():
        """Background thread to scan the network"""
        discovered = []
        
        logger.info(f"Starting network scan for HDMI-CEC devices on {subnet}.{start}-{end}")
        
        for i in range(start, end + 1):
            ip = f"{subnet}.{i}"
            try:
                # Try common HDMI-CEC over IP ports
                cec_found = False
                
                # Check HDMI-CEC port (9740 commonly used)
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                if s.connect_ex((ip, 9740)) == 0:
                    cec_found = True
                s.close()
                
                # If not found, try HTTP port which might be a Smart TV
                if not cec_found:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.5)
                    if s.connect_ex((ip, 80)) == 0:
                        # Found a device with web server, might be a TV
                        # Additional checks would be needed to confirm it supports CEC
                        cec_found = True
                    s.close()
                
                if cec_found:
                    # Try to get device name (would use UPnP/SSDP in a real implementation)
                    device_name = f"Unknown Device at {ip}"
                    discovered.append({"ip": ip, "name": device_name})
                    logger.info(f"Found potential HDMI-CEC device: {ip}")
            except Exception as e:
                logger.debug(f"Error scanning {ip}: {str(e)}")
        
        # Store scan results
        with open('hdmi_cec_scan_results.json', 'w') as f:
            json.dump({
                "timestamp": time.time(), 
                "devices": discovered
            }, f, indent=2)
        
        logger.info(f"Network scan completed. Found {len(discovered)} potential HDMI-CEC devices.")
    
    # Start scan in background thread
    threading.Thread(target=scan_thread, daemon=True).start()
    
    return jsonify({
        "message": f"Network scan started for range {subnet}.{start}-{end}"
    }), 200

@app.route('/scan_results', methods=['GET'])
def get_scan_results():
    """Get the results of the last network scan"""
    try:
        with open('hdmi_cec_scan_results.json', 'r') as f:
            scan_data = json.load(f)
            return jsonify(scan_data), 200
    except FileNotFoundError:
        return jsonify({"error": "No scan results available"}), 404

@app.route('/available_commands', methods=['GET'])
def get_available_commands():
    """Get a list of available HDMI-CEC commands"""
    return jsonify({
        "commands": list(cec_commands.keys()),
        "description": "HDMI-CEC commands for controlling TV and connected devices"
    }), 200

@app.route('/set_timer', methods=['POST'])
def set_timer():
    """Set a timer to send a command after a specified delay"""
    data = request.json
    ip = data.get('ip')
    command = data.get('command')
    seconds = data.get('seconds')
    
    if ip not in devices:
        return jsonify({"error": "Device not found"}), 404
        
    if not command or command not in cec_commands:
        return jsonify({
            "error": "Invalid command", 
            "available_commands": list(cec_commands.keys())
        }), 400
        
    if not seconds or not isinstance(seconds, (int, float)) or seconds <= 0:
        return jsonify({"error": "Invalid time value"}), 400
    
    def timer_action():
        logger.info(f"Timer started for {ip}, command: {command}, duration: {seconds} seconds")
        time.sleep(seconds)
        result = send_cec_command(ip, command)
        if result:
            logger.info(f"Timer executed '{command}' command on {ip}")
        else:
            logger.error(f"Timer failed to execute '{command}' command on {ip}")
    
    # Start timer in background thread
    threading.Thread(target=timer_action, daemon=True).start()
    
    logger.info(f"Timer set for {ip}: {command} in {seconds} seconds")
    return jsonify({
        "message": f"Timer set to send '{command}' command in {seconds} seconds"
    }), 200

# Start the application
if __name__ == '__main__':
    # Load saved devices
    load_devices()
    
    # Start status check threads for each device
    for ip in devices:
        threading.Thread(target=check_device_status, args=(ip,), daemon=True).start()
    
    # Start the Flask server
    app.run(host='0.0.0.0', port=1618)