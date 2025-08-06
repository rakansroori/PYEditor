#!/usr/bin/env python3
"""
Test script for the enhanced media browser
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt
from ui.media_browser import MediaBrowserWidget

class MediaBrowserTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enhanced Media Browser Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        # Add some test media button (for demonstration)
        add_test_btn = QPushButton("Add Sample Media Items")
        add_test_btn.clicked.connect(self.add_sample_media)
        controls_layout.addWidget(add_test_btn)
        
        clear_btn = QPushButton("Clear All Media")
        clear_btn.clicked.connect(self.clear_media)
        controls_layout.addWidget(clear_btn)
        
        controls_layout.addStretch()
        
        controls_widget = QWidget()
        controls_widget.setLayout(controls_layout)
        layout.addWidget(controls_widget)
        
        # Media browser widget
        self.media_browser = MediaBrowserWidget()
        layout.addWidget(self.media_browser)
        
        # Connect signals
        self.media_browser.media_selected.connect(self.on_media_selected)
        self.media_browser.media_double_clicked.connect(self.on_media_double_clicked)
        
    def add_sample_media(self):
        """Add some sample media items for testing"""
        # Create some dummy media files for testing
        sample_files = [
            ("Sample_Video_1.mp4", "Video", 120.5, (1920, 1080), "MP4"),
            ("Sample_Video_2.avi", "Video", 85.2, (1280, 720), "AVI"),
            ("Sample_Audio.wav", "Audio", 180.0, (0, 0), "WAV"),
            ("Sample_Image.jpg", "Image", 0.0, (3840, 2160), "JPG"),
        ]
        
        # Note: In a real implementation, these would be actual files
        # For testing, we'll simulate the process
        print("In a real implementation, you would:")
        print("1. Use the 'Import Files' or 'Import Folder' buttons")
        print("2. Select actual media files from your system")
        print("3. The browser will automatically generate thumbnails and metadata")
        print("\nDemo features:")
        print("- Search functionality in the search box")
        print("- View mode selection (List/Grid/Details)")
        print("- Folder organization on the left")
        print("- Detailed media information panel at the bottom")
        
    def clear_media(self):
        """Clear all media from browser"""
        # Clear the media view
        self.media_browser.media_view.clear()
        self.media_browser.media_items.clear()
        print("Cleared all media items")
        
    def on_media_selected(self, file_path: str):
        """Handle media selection"""
        print(f"Media selected: {file_path}")
        
    def on_media_double_clicked(self, file_path: str):
        """Handle media double-click"""
        print(f"Media double-clicked: {file_path}")
        print("In the main application, this would load the media into the timeline and preview")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set enhanced dark theme
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
            color: white;
        }
        QWidget {
            background-color: #2b2b2b;
            color: white;
        }
        QPushButton {
            background-color: #5a5a5a;
            color: white;
            border: 1px solid #777;
            padding: 8px;
            border-radius: 4px;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #6a6a6a;
        }
        QLabel {
            color: white;
        }
        QTreeWidget {
            background-color: #3c3c3c;
            color: white;
            border: none;
            alternate-background-color: #404040;
        }
        QTreeWidget::item:selected {
            background-color: #094771;
        }
        QLineEdit {
            background-color: #5a5a5a;
            color: white;
            border: 1px solid #777;
            padding: 3px;
            border-radius: 3px;
        }
        QComboBox {
            background-color: #5a5a5a;
            color: white;
            border: 1px solid #777;
            padding: 3px;
        }
        QGroupBox {
            color: white;
            border: 1px solid #777;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 5px;
        }
        QGroupBox::title {
            color: white;
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QProgressBar {
            background-color: #5a5a5a;
            border: 1px solid #777;
            border-radius: 3px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #094771;
            border-radius: 2px;
        }
        QSplitter::handle {
            background-color: #555;
        }
        QSplitter::handle:horizontal {
            width: 3px;
        }
        QSplitter::handle:vertical {
            height: 3px;
        }
    """)
    
    window = MediaBrowserTestWindow()
    window.show()
    
    print("Enhanced Media Browser Test")
    print("=" * 50)
    print("Features to test:")
    print("1. Click 'Import Files' to add media files")
    print("2. Click 'Import Folder' to scan a folder")
    print("3. Use the search box to filter media")
    print("4. Try different view modes")
    print("5. Select media to see detailed information")
    print("6. Double-click media items")
    print("7. Watch thumbnail generation progress")
    print("=" * 50)
    
    sys.exit(app.exec())
