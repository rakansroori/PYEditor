#!/usr/bin/env python3
"""
PyVideoEditor - Professional Video Editor
Main application entry point
"""

import sys
import os

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from ui.main_window import VideoEditor

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("PyVideoEditor")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("PyVideoEditor")
    
    # Create and show main window
    window = VideoEditor()
    window.show()
    
    # Start application event loop
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
