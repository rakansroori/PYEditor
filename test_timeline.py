#!/usr/bin/env python3
"""
Simple test script for the new timeline widget
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import Qt
from ui.timeline_widget import TimelineWidget

class TimelineTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Timeline Widget Test")
        self.setGeometry(100, 100, 1200, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add test button
        test_button = QPushButton("Add Test Clip")
        test_button.clicked.connect(self.add_test_clip)
        layout.addWidget(test_button)
        
        # Timeline widget
        self.timeline = TimelineWidget()
        layout.addWidget(self.timeline)
        
        # Connect signals
        self.timeline.time_changed.connect(self.on_time_changed)
        self.timeline.clip_selected.connect(self.on_clip_selected)
        
        self.clip_counter = 0
        
    def add_test_clip(self):
        """Add a test clip to the timeline"""
        self.clip_counter += 1
        clip_name = f"Test Clip {self.clip_counter}"
        start_time = (self.clip_counter - 1) * 5.0  # 5 second intervals
        duration = 4.0  # 4 second clips
        track = 0  # First video track
        
        clip_id = self.timeline.add_clip_to_track(track, clip_name, start_time, duration)
        print(f"Added clip: {clip_id} - {clip_name} at {start_time}s for {duration}s")
        
    def on_time_changed(self, time: float):
        """Handle timeline time changes"""
        print(f"Time changed: {time:.2f}s")
        
    def on_clip_selected(self, clip_id: str):
        """Handle clip selection"""
        print(f"Clip selected: {clip_id}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set dark theme
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
            padding: 5px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #6a6a6a;
        }
    """)
    
    window = TimelineTestWindow()
    window.show()
    
    sys.exit(app.exec())
