# -*- coding: utf-8 -*-
# splash.py
# Lightweight standalone splash screen for IBSimion 2.0.1.e3l

import sys
import os
from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

def main():
    app = QApplication(sys.argv)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pid_file = os.path.join(script_dir, "..", "early_splash.pid")
    
    # Save PID so it can be closed by the main application
    try:
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        print(f"Warning: Could not write early_splash.pid: {e}")
        
    icon_path = os.path.join(script_dir, "ibsimion_icon.png")
    if os.path.exists(icon_path):
        pixmap = QPixmap(icon_path)
        scaled_pixmap = pixmap.scaled(512, 512, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        splash = QSplashScreen(scaled_pixmap)
        splash.show()
        splash.showMessage(
            "IBSimion v2.0.1.e3l - Verificando dependências do sistema...",
            Qt.AlignBottom | Qt.AlignHCenter,
            Qt.white
        )
    else:
        print(f"Error: Icon not found at {icon_path}")
        sys.exit(1)
        
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
