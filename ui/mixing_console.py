"""
Mixing console UI for PyVideoEditor
Allows users to manage and mix multiple audio tracks
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
    QListWidget, QListWidgetItem, QGroupBox, QFormLayout, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal

class MixingConsole(QWidget):
    """Mixing console for audio tracks"""

    def __init__(self, audio_processor):
        super().__init__()
        self.audio_processor = audio_processor
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Mixing Console")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Track list
        self.track_list = QListWidget()
        layout.addWidget(self.track_list)

        # Controls panel
        controls_layout = QHBoxLayout()

        # Add track button
        self.add_track_button = QPushButton("Add Track")
        self.add_track_button.clicked.connect(self.add_track)
        controls_layout.addWidget(self.add_track_button)

        layout.addLayout(controls_layout)

    def add_track(self):
        """Add a new audio track to the console"""
        track_name, ok = QInputDialog.getText(self, "Add Track", "Enter track name:")
        if ok and track_name:
            self.audio_processor.add_track(track_name)
            self.track_list.addItem(track_name)

