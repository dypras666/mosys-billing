import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread
from gui import MosysBillingGUI
import logging

# Import server ADB
from flask_app import app as adb_app, load_tv_data as load_adb_data

# Import server HDMI-CEC 
from hdmi_cec_app import app as cec_app, load_devices as load_cec_data

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MosysBilling")

class ADBFlaskThread(QThread):
    def run(self):
        logger.info("Starting ADB Server on port 1616")
        adb_app.run(host='0.0.0.0', port=1616, debug=False, use_reloader=False)

class CECFlaskThread(QThread):
    def run(self):
        logger.info("Starting HDMI-CEC Server on port 1618")
        cec_app.run(host='0.0.0.0', port=1618, debug=False, use_reloader=False)

class LANOptimizedADBFlaskThread(QThread):
    def run(self):
        logger.info("Starting LAN Optimized ADB Server on port 1617")
        # Jika Anda mengimplementasikan server LAN-optimized
        try:
            from lan_app import app as lan_app
            lan_app.run(host='0.0.0.0', port=1617, debug=False, use_reloader=False)
        except ImportError:
            logger.warning("LAN Optimized Server not available. Skipping.")

if __name__ == '__main__':
    logger.info("Initializing Mosys Billing System")
    
    # Load data untuk kedua server
    try:
        logger.info("Loading ADB TV data")
        load_adb_data()
    except Exception as e:
        logger.error(f"Error loading ADB TV data: {str(e)}")
    
    try:
        logger.info("Loading HDMI-CEC device data")
        load_cec_data()
    except Exception as e:
        logger.error(f"Error loading HDMI-CEC device data: {str(e)}")
    
    # Start Flask servers in separate threads
    logger.info("Starting server threads")
    
    # ADB server thread
    adb_thread = ADBFlaskThread()
    adb_thread.daemon = True  # Ensure thread closes when main program exits
    adb_thread.start()
    
    # HDMI-CEC server thread
    cec_thread = CECFlaskThread()
    cec_thread.daemon = True
    cec_thread.start()
    
    # Optional: LAN Optimized ADB server thread
    lan_thread = LANOptimizedADBFlaskThread()
    lan_thread.daemon = True
    lan_thread.start()
    
    # Start PyQt application
    logger.info("Starting GUI application")
    qt_app = QApplication(sys.argv)
    gui = MosysBillingGUI()
    gui.show()
    
    # Tunggu hingga GUI dimatikan
    exit_code = qt_app.exec_()
    logger.info("GUI application closed. Shutting down servers.")
    sys.exit(exit_code)