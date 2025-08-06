#!/usr/bin/env python3
"""
Test script for the advanced preview system
"""

import sys
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
from ui.preview_widget import PreviewWidget

# Mock video clip class for testing without MoviePy
class MockVideoClip:
    def __init__(self, duration=10.0, fps=30.0, size=(640, 480)):
        self.duration = duration
        self.fps = fps
        self.size = size
        
    def get_frame(self, time):
        """Generate a test frame with time display"""
        # Create a test frame with gradient and time display
        width, height = self.size
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Create gradient background
        for y in range(height):
            for x in range(width):
                frame[y, x, 0] = int((x / width) * 255)  # Red gradient
                frame[y, x, 1] = int((y / height) * 255)  # Green gradient
                frame[y, x, 2] = int(((x + y) / (width + height)) * 255)  # Blue gradient
        
        # Add time indicator (simple text simulation)
        time_indicator = int((time / self.duration) * width)
        if 0 <= time_indicator < width:
            frame[:, time_indicator:time_indicator+5, :] = [255, 255, 255]  # White line
            
        # Add frame number indicator
        frame_num = int(time * self.fps)
        indicator_height = min(frame_num % 100, height - 1)
        frame[indicator_height:indicator_height+5, 10:15, :] = [255, 0, 0]  # Red square
        
        return frame

class PreviewTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced Preview System Test")
        self.setGeometry(100, 100, 1000, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        load_button = QPushButton("Load Test Video")
        load_button.clicked.connect(self.load_test_video)
        controls_layout.addWidget(load_button)
        
        clear_button = QPushButton("Clear Video")
        clear_button.clicked.connect(self.clear_video)
        controls_layout.addWidget(clear_button)
        
        controls_layout.addStretch()
        
        controls_widget = QWidget()
        controls_widget.setLayout(controls_layout)
        layout.addWidget(controls_widget)
        
        # Preview widget
        self.preview_widget = PreviewWidget()
        layout.addWidget(self.preview_widget)
        
        # Connect signals
        self.preview_widget.time_changed.connect(self.on_time_changed)
        self.preview_widget.frame_changed.connect(self.on_frame_changed)
        
    def load_test_video(self):
        """Load a test video clip"""
        # Create mock video clip
        test_clip = MockVideoClip(duration=15.0, fps=30.0, size=(800, 600))
        self.preview_widget.set_video_clip(test_clip)
        print("Loaded test video: 15 seconds, 30fps, 800x600")
        
    def clear_video(self):
        """Clear the video"""
        self.preview_widget.set_video_clip(None)
        print("Cleared video")
        
    def on_time_changed(self, time: float):
        """Handle time changes"""
        print(f"Preview time: {time:.2f}s")
        
    def on_frame_changed(self, time: float, frame):
        """Handle frame changes"""
        # This could be used for analysis or effects
        pass

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
        QComboBox {
            background-color: #5a5a5a;
            color: white;
            border: 1px solid #777;
            padding: 3px;
        }
        QCheckBox {
            color: white;
        }
    """)
    
    window = PreviewTestWindow()
    window.show()
    
    sys.exit(app.exec())
