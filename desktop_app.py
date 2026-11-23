
import sys
import threading

from PySide6.QtWebEngineCore import QWebEnginePermission
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl

from werkzeug.serving import make_server
from app import app as flask_app

class FlaskServer(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.server = make_server("127.0.0.1", 5000, flask_app)

    def run(self):
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()

class CodeSpeakDesktop(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CodeSpeak - Oral Mastery for Engineers")
        self.resize(1200, 800)

        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)

        self.browser.page().permissionRequested.connect(
            self.handle_permission
        )

        self.flask_server = FlaskServer()
        self.flask_server.start()

        self.browser.setUrl(QUrl("http://127.0.0.1:5000"))

    def closeEvent(self, event):
        self.flask_server.stop()
        event.accept()

    def handle_permission(self, permission):
        if permission.permissionType() == QWebEnginePermission.PermissionType.MediaAudioCapture:
            permission.grant()
            print("Microphone permission granted")
        else:
            permission.deny()

if __name__ == "__main__":
    qt_app = QApplication(sys.argv)

    window = CodeSpeakDesktop()
    window.showMaximized()

    sys.exit(qt_app.exec())