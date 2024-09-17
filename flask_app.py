import asyncio 
import subprocess
from flask import Flask, request, jsonify
import json
import threading
import time
import logging
import ping3
import os
import tempfile
import shlex
import base64

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

tvs = {}
TV_DATA_FILE = 'tv_data.json'

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
# Define command_map at the global level
command_map = {
    'off': "input keyevent KEYCODE_POWER",
    'sleep': "input keyevent KEYCODE_SLEEP",
    'volume_up': "input keyevent KEYCODE_VOLUME_UP",
    'volume_down': "input keyevent KEYCODE_VOLUME_DOWN",
    'home': "input keyevent KEYCODE_HOME"  # Added home command
}
def load_tv_data():
    global tvs
    try:
        with open(TV_DATA_FILE, 'r') as f:
            tvs = json.load(f)
    except FileNotFoundError:
        tvs = {}

def save_tv_data():
    with open(TV_DATA_FILE, 'w') as f:
        json.dump(tvs, f)

def check_tv_status(ip):
    while True:
        try:
            response_time = ping3.ping(ip)
            if response_time is not None:
                tvs[ip]['status'] = 'Online'
                tvs[ip]['response_time'] = f"{response_time:.2f} ms"
            else:
                tvs[ip]['status'] = 'Offline'
                tvs[ip]['response_time'] = 'N/A'
            save_tv_data()
        except Exception as e:
            tvs[ip]['status'] = 'Error'
            tvs[ip]['response_time'] = 'N/A'
            logging.error(f"Error checking status for {ip}: {str(e)}")
        time.sleep(5)

@app.route('/add_tv', methods=['POST'])
def add_tv():
    data = request.json
    name = data.get('name')
    ip = data.get('ip')
    
    if name and ip:
        if ip in tvs:
            return jsonify({"error": "TV with this IP already exists"}), 400
        tvs[ip] = {'name': name, 'status': 'Checking', 'response_time': 'N/A'}
        threading.Thread(target=check_tv_status, args=(ip,), daemon=True).start()
        save_tv_data()
        logging.info(f"Added new TV: {name} ({ip})")
        return jsonify({"message": "TV added successfully", "tv": tvs[ip]}), 200
    else:
        return jsonify({"error": "Name and IP are required"}), 400

@app.route('/remove_tv', methods=['POST'])
def remove_tv():
    data = request.json
    ip = data.get('ip')
    
    if ip in tvs:
        del tvs[ip]
        save_tv_data()
        logging.info(f"Removed TV with IP: {ip}")
        return jsonify({"message": "TV removed successfully"}), 200
    else:
        return jsonify({"error": "TV not found"}), 404

@app.route('/edit_tv', methods=['POST'])
def edit_tv():
    data = request.json
    old_ip = data.get('old_ip')
    new_name = data.get('new_name')
    new_ip = data.get('new_ip')
    
    if old_ip in tvs:
        if new_ip != old_ip and new_ip in tvs:
            return jsonify({"error": "New IP already exists"}), 400
        tv_info = tvs.pop(old_ip)
        tv_info['name'] = new_name
        tvs[new_ip] = tv_info
        save_tv_data()
        logging.info(f"Edited TV: {new_name} ({new_ip})")
        return jsonify({"message": "TV edited successfully", "tv": tvs[new_ip]}), 200
    else:
        return jsonify({"error": "TV not found"}), 404

@app.route('/tv_status', methods=['GET'])
def get_tv_status():
    return jsonify(tvs)

# @app.route('/control_tv', methods=['POST'])
# def control_tv():
#     data = request.json
#     ip = data.get('ip')
#     action = data.get('action')
    
#     if ip not in tvs:
#         return jsonify({"error": "TV not found"}), 404
    
#     if action == 'on':
#         logging.warning("'On' action may not work via ADB")
#         return jsonify({"message": "TV on command sent (may not work via ADB)"}), 200
#     elif action in ['off', 'sleep', 'volume_up', 'volume_down']:
#         command_map = {
#             'off': "input keyevent KEYCODE_POWER",
#             'sleep': "input keyevent KEYCODE_SLEEP",
#             'volume_up': "input keyevent KEYCODE_VOLUME_UP",
#             'volume_down': "input keyevent KEYCODE_VOLUME_DOWN",
#             'home': "input keyevent KEYCODE_HOME"  # Added home command
#         }
#         result = run_adb_command(ip, command_map[action])
#         if result is not None:
#             logging.info(f"Successfully sent {action} command to {ip}")
#             return jsonify({"message": f"{action} command sent successfully"}), 200
#         else:
#             logging.error(f"Failed to send {action} command to {ip}")
#             return jsonify({"error": f"Failed to send {action} command"}), 500
#     else:
#         return jsonify({"error": "Invalid action"}), 400
    
# @app.route('/start_tv_timer', methods=['POST'])
# def start_tv_timer():
#     data = request.json
#     ip = data.get('ip')
#     seconds = data.get('seconds')
    
#     if ip not in tvs:
#         return jsonify({"error": "TV not found"}), 404
    
#     # Kirim perintah ke aplikasi TimerOverlay
#     command = f"am start -n com.mosys.billing/.MainActivity --ei seconds {seconds}"
#     result = run_adb_command(ip, command)
    
#     if result is not None:
#         logging.info(f"Started timer on TV {ip} for {seconds} seconds")
#         return jsonify({"message": f"Timer started on TV for {seconds} seconds"}), 200
#     else:
#         logging.error(f"Failed to start timer on TV {ip}")
#         return jsonify({"error": "Failed to start timer on TV"}), 500


@app.route('/stream_media/<ip>', methods=['POST'])
def stream_media(ip):
    if ip not in tvs:
        return jsonify({"error": "TV not found"}), 404
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = file.filename
        # Gunakan direktori yang dapat diakses oleh TV
        stream_dir = '/sdcard/Download'
        filepath = os.path.join(stream_dir, filename)
        
        # Simpan file ke server terlebih dahulu
        temp_filepath = os.path.join(tempfile.gettempdir(), filename)
        file.save(temp_filepath)
        
        # Kirim file ke TV menggunakan ADB push
        push_command = f"adb -s {ip} push {temp_filepath} {filepath}"
        push_result = os.system(push_command)
        
        if push_result != 0:
            return jsonify({"error": "Failed to transfer file to TV"}), 500
        
        # Hapus file temporary di server
        os.remove(temp_filepath)
        
        # Mulai pemutaran menggunakan aplikasi video default
        stream_command = f"am start -a android.intent.action.VIEW -d file://{filepath} -t video/*"
        result = run_adb_command(ip, stream_command)
        
        if result is not None:
            logging.info(f"Successfully started streaming {filename} to {ip}")
            return jsonify({"message": f"Started streaming {filename}"}), 200
        else:
            logging.error(f"Failed to start streaming {filename} to {ip}")
            return jsonify({"error": "Failed to start streaming"}), 500
        
@app.route('/start_tv_timer', methods=['POST'])
def start_tv_timer():
    data = request.json
    ip = data.get('ip')
    seconds = data.get('seconds')
    custom_text = data.get('custom_text', "Waktu rental mu sudah habis, silahkan ke kasir jika ingin menambah waktu!")
    
    if ip not in tvs:
        return jsonify({"error": "TV not found"}), 404
    
    encoded_text = base64.b64encode(custom_text.encode()).decode()
    
    adb_command = f'am start -n com.mosys.billing/.MainActivity --ei seconds {seconds} --es customText {shlex.quote(encoded_text)}'
    logger.debug(f"Executing ADB command: {adb_command}")
    
    result = run_adb_command(ip, adb_command)
    
    if result is not None:
        logger.info(f"Started timer on TV {ip} for {seconds} seconds with custom text: {custom_text}")
        return jsonify({"message": f"Timer started on TV for {seconds} seconds with custom text"}), 200
    else:
        logger.error(f"Failed to start timer on TV {ip}")
        return jsonify({"error": "Failed to start timer on TV"}), 500

# @app.route('/set_timer', methods=['POST'])
# def set_timer():
#     data = request.json
#     ip = data.get('ip')
#     action = data.get('action')
#     seconds = data.get('seconds')
    
#     if ip not in tvs:
#         return jsonify({"error": "TV not found"}), 404
    
#     if action not in command_map:
#         return jsonify({"error": "Invalid action"}), 400
    
#     async def timer_action():
#         logger.info(f"Timer started for {ip}, action: {action}, duration: {seconds} seconds")
#         await asyncio.sleep(seconds)
#         command = command_map[action]
#         result = run_adb_command(ip, command)
#         if result is not None:
#             logger.info(f"Timer executed {action} command on {ip}")
#         else:
#             logger.error(f"Timer failed to execute {action} command on {ip}")

#     loop.create_task(timer_action())
    
#     return jsonify({"message": f"Timer set for {seconds} seconds to {action}"}), 200
@app.route('/control_tv', methods=['POST'])
def control_tv():
    data = request.json
    ip = data.get('ip')
    action = data.get('action')
    
    if ip not in tvs:
        return jsonify({"error": "TV not found"}), 404
    
    if action == 'on':
        logging.warning("'On' action may not work via ADB")
        return jsonify({"message": "TV on command sent (may not work via ADB)"}), 200
    elif action in command_map:
        result = run_adb_command(ip, command_map[action])
        if result is not None:
            logging.info(f"Successfully sent {action} command to {ip}")
            return jsonify({"message": f"{action} command sent successfully"}), 200
        else:
            logging.error(f"Failed to send {action} command to {ip}")
            return jsonify({"error": f"Failed to send {action} command"}), 500
    else:
        return jsonify({"error": "Invalid action"}), 400
    
@app.route('/set_timer', methods=['POST'])
def set_timer():
    data = request.json
    ip = data.get('ip')
    action = data.get('action')
    seconds = data.get('seconds')
    
    if ip not in tvs:
        return jsonify({"error": "TV not found"}), 404
    
    if action not in command_map:
        return jsonify({"error": "Invalid action"}), 400
    
    def timer_action():
        logger.info(f"Timer started for {ip}, action: {action}, duration: {seconds} seconds")
        time.sleep(seconds)
        command = command_map[action]
        result = run_adb_command(ip, command)
        if result is not None:
            logger.info(f"Timer executed {action} command on {ip}")
        else:
            logger.error(f"Timer failed to execute {action} command on {ip}")

    threading.Thread(target=timer_action, daemon=True).start()
    
    return jsonify({"message": f"Timer set for {seconds} seconds to {action}"}), 200


def run_adb_command(ip, command):
    full_command = f"adb -s {ip}:5555 shell {command}"
    logger.debug(f"Full ADB command: {full_command}")
    try:
        result = subprocess.run(full_command, shell=True, check=True, capture_output=True, text=True, timeout=30)
        logger.debug(f"ADB command output: {result.stdout}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"ADB command failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return None
    except subprocess.TimeoutExpired:
        logger.error("ADB command timed out")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in run_adb_command: {str(e)}")
        return None





if __name__ == '__main__':
    load_tv_data()
    app.run(host='0.0.0.0', port=1616, loop=loop)
