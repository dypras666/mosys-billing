import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread
from gui import MosysBillingGUI
from flask_app import app, load_tv_data

class FlaskThread(QThread):
    def run(self):
        app.run(host='0.0.0.0', port=1616)

if __name__ == '__main__':
    # Load TV data from JSON file
    load_tv_data()

    # Start Flask in a separate thread
    flask_thread = FlaskThread()
    flask_thread.start()

    # Start PyQt application
    qt_app = QApplication(sys.argv)
    gui = MosysBillingGUI()
    gui.show()
    sys.exit(qt_app.exec_())