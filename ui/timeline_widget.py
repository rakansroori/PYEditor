"""
Professional Timeline Widget for PyVideoEditor
Adobe Premiere-style timeline with multi-track support, drag-and-drop, and scrubbing
"""

import sys
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
    QScrollArea, QFrame, QSizePolicy, QSpinBox, QComboBox, QToolBar,
    QButtonGroup
)
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer, pyqtSignal, QMimeData
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPixmap, QPalette,
    QMouseEvent, QDragEnterEvent, QDropEvent, QDrag, QShortcut
)
from typing import List, Dict, Optional, Tuple
import math
from enum import Enum
import copy

class TimelineTool(Enum):
    """Timeline editing tools"""
    SELECT = "select"
    RAZOR = "razor"
    ZOOM = "zoom"
    HAND = "hand"          # Pan tool
    SLIP = "slip"          # Slip edit
    SLIDE = "slide"        # Slide edit
    RIPPLE = "ripple"      # Ripple edit
    ROLLING = "rolling"    # Rolling edit

class TimelineClip:
    """Represents a clip on the timeline"""
    def __init__(self, clip_id: str, name: str, start_time: float, duration: float, track: int, clip_type: str = "video"):
        self.clip_id = clip_id
        self.name = name
        self.start_time = start_time
        self.duration = duration
        self.track = track
        self.clip_type = clip_type  # "video", "audio", or "both"
        self.color = QColor(70, 130, 180) if clip_type == "video" else QColor(50, 150, 50)
        self.selected = False
        self.thumbnail = None
        self.waveform_data = None  # Audio waveform data
        self.has_audio = False
        self.has_video = True if clip_type != "audio" else False
        
    def end_time(self) -> float:
        return self.start_time + self.duration
        
    def contains_time(self, time: float) -> bool:
        return self.start_time <= time <= self.end_time()

class AutomationTrack:
    """Represents an automation track for parameters like volume, opacity, etc."""
    def __init__(self, parent_track_id: int, parameter_name: str):
        self.parent_track_id = parent_track_id
        self.parameter_name = parameter_name  # "volume", "opacity", "pan", etc.
        self.keyframes = {}  # time -> value mapping
        self.enabled = False
        self.height = 40
        self.min_value = 0.0
        self.max_value = 1.0
        
    def add_keyframe(self, time: float, value: float):
        self.keyframes[time] = max(self.min_value, min(self.max_value, value))
        
    def remove_keyframe(self, time: float):
        if time in self.keyframes:
            del self.keyframes[time]
            
    def get_value_at_time(self, time: float) -> float:
        if not self.keyframes:
            return (self.min_value + self.max_value) / 2  # Default middle value
            
        # Find surrounding keyframes and interpolate
        times = sorted(self.keyframes.keys())
        
        if time <= times[0]:
            return self.keyframes[times[0]]
        if time >= times[-1]:
            return self.keyframes[times[-1]]
            
        # Linear interpolation between keyframes
        for i in range(len(times) - 1):
            if times[i] <= time <= times[i + 1]:
                t1, t2 = times[i], times[i + 1]
                v1, v2 = self.keyframes[t1], self.keyframes[t2]
                factor = (time - t1) / (t2 - t1)
                return v1 + (v2 - v1) * factor
                
        return (self.min_value + self.max_value) / 2

class TimelineTrack:
    """Represents a single track on the timeline"""
    def __init__(self, track_id: int, name: str, track_type: str = "video"):
        self.track_id = track_id
        self.name = name
        self.track_type = track_type  # "video", "audio", or "automation"
        self.clips: List[TimelineClip] = []
        self.muted = False
        self.locked = False
        self.solo = False
        self.height = 60 if track_type == "video" else 40 if track_type == "audio" else 40
        self.automation_tracks: List[AutomationTrack] = []
        self.show_automation = False
        
        # Create default automation tracks for audio
        if track_type == "audio":
            self.automation_tracks.append(AutomationTrack(track_id, "volume"))
            self.automation_tracks.append(AutomationTrack(track_id, "pan"))
        elif track_type == "video":
            self.automation_tracks.append(AutomationTrack(track_id, "opacity"))
            
    def add_automation_track(self, parameter_name: str):
        """Add a new automation track for a parameter"""
        automation = AutomationTrack(self.track_id, parameter_name)
        self.automation_tracks.append(automation)
        return automation
        
    def get_automation_track(self, parameter_name: str) -> Optional[AutomationTrack]:
        """Get automation track by parameter name"""
        for automation in self.automation_tracks:
            if automation.parameter_name == parameter_name:
                return automation
        return None
        
    def toggle_automation_visibility(self):
        """Toggle visibility of automation tracks"""
        self.show_automation = not self.show_automation
        
    def add_clip(self, clip: TimelineClip):
        self.clips.append(clip)
        self.clips.sort(key=lambda c: c.start_time)

    def move_clip(self, clip_id: str, new_start_time: float) -> bool:
        clip = self.get_clip_by_id(clip_id)
        if clip and not self.locked:
            clip.start_time = new_start_time
            self.clips.sort(key=lambda c: c.start_time)
            return True
        return False

    def get_clip_by_id(self, clip_id: str) -> Optional[TimelineClip]:
        for clip in self.clips:
            if clip.clip_id == clip_id:
                return clip
        return None

    def split_clip(self, clip_id: str, split_time: float) -> Optional[Tuple[TimelineClip, TimelineClip]]:
        """Split a clip at the specified time, returns (left_clip, right_clip) or None"""
        clip = self.get_clip_by_id(clip_id)
        if clip and clip.start_time < split_time < clip.end_time():
            # Calculate durations
            left_duration = split_time - clip.start_time
            right_duration = clip.end_time() - split_time
            
            # Create right clip
            right_clip = TimelineClip(
                f"{clip_id}_split",
                f"{clip.name} (2)",
                split_time,
                right_duration,
                clip.track
            )
            right_clip.color = clip.color
            
            # Update original clip (becomes left clip)
            clip.duration = left_duration
            clip.name = f"{clip.name} (1)" if not clip.name.endswith(" (1)") else clip.name
            
            # Add right clip to track
            self.add_clip(right_clip)
            
            return (clip, right_clip)
        return None
    def remove_clip(self, clip_id: str):
        self.clips = [clip for clip in self.clips if clip.clip_id != clip_id]
        
    def get_clip_at_time(self, time: float) -> Optional[TimelineClip]:
        for clip in self.clips:
            if clip.contains_time(time):
                return clip
        return None

class TimelineRuler(QWidget):
    """Timeline ruler showing time markers"""
    
    def __init__(self, timeline_widget):
        super().__init__()
        self.timeline_widget = timeline_widget
        self.setFixedHeight(20)  # Thinner ruler height
        self.setMouseTracking(True)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(45, 45, 45))
        
        # Get timeline parameters
        pixels_per_second = self.timeline_widget.pixels_per_second
        start_time = self.timeline_widget.scroll_offset / pixels_per_second
        width = self.width()
        
        # Draw time markers
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.setFont(QFont("Arial", 7))  # Smaller font for more compact look
        
        # Calculate marker interval based on zoom level
        if pixels_per_second > 100:
            interval = 0.5  # 0.5 second intervals
        elif pixels_per_second > 50:
            interval = 1.0  # 1 second intervals
        elif pixels_per_second > 20:
            interval = 5.0  # 5 second intervals
        else:
            interval = 10.0  # 10 second intervals
            
        # Draw markers
        start_marker = int(start_time / interval) * interval
        for i in range(int(width / (interval * pixels_per_second)) + 2):
            time = start_marker + i * interval
            x = int(time * pixels_per_second - self.timeline_widget.scroll_offset)
            
            if 0 <= x <= width:
                painter.drawLine(x, 20, x, 30)
                
                # Draw time text
                time_text = self.format_time(time)
                painter.drawText(x + 2, 15, time_text)
                
    def format_time(self, seconds: float) -> str:
        """Format time as MM:SS.ff"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        frames = int((seconds % 1) * 30)  # Assuming 30fps
        return f"{minutes:02d}:{secs:02d}.{frames:02d}"

class TimelineTrackWidget(QWidget):
    """Widget representing a single track"""
    
    clip_selected = pyqtSignal(str)  # clip_id
    clip_moved = pyqtSignal(str, float, int)  # clip_id, new_time, new_track
    
    def __init__(self, track: TimelineTrack, timeline_widget):
        super().__init__()
        self.track = track
        self.timeline_widget = timeline_widget
        self.setFixedHeight(track.height)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        
        self.dragging_clip = None
        self.drag_start_pos = None
        self.drag_offset = 0
        
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Track background
        bg_color = QColor(60, 60, 60) if self.track.track_type == "video" else QColor(50, 70, 50)
        painter.fillRect(self.rect(), bg_color)
        
        # Draw clips
        pixels_per_second = self.timeline_widget.pixels_per_second
        scroll_offset = self.timeline_widget.scroll_offset
        
        for clip in self.track.clips:
            clip_x = int(clip.start_time * pixels_per_second - scroll_offset)
            clip_width = int(clip.duration * pixels_per_second)
            clip_rect = QRect(clip_x, 5, clip_width, self.height() - 10)
            
            # Only draw if visible
            if clip_rect.right() >= 0 and clip_rect.left() <= self.width():
                self.draw_clip(painter, clip, clip_rect)
                
    def draw_clip(self, painter: QPainter, clip: TimelineClip, rect: QRect):
        """Draw a single clip with waveform for audio clips"""
        # Clip background
        color = clip.color
        if clip.selected:
            color = color.lighter(150)
            
        painter.fillRect(rect, color)
        
        # Draw waveform for audio clips or clips with audio
        if (clip.clip_type == "audio" or clip.has_audio) and clip.waveform_data:
            self.draw_waveform(painter, clip, rect)
        
        # Draw video thumbnail strip for video clips
        if clip.clip_type == "video" and self.track.track_type == "video":
            self.draw_video_thumbnails(painter, clip, rect)
        
        # Clip border
        border_color = QColor(255, 255, 255) if clip.selected else QColor(30, 30, 30)
        painter.setPen(QPen(border_color, 2 if clip.selected else 1))
        painter.drawRect(rect)
        
        # Clip name
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setFont(QFont("Arial", 8))  # Smaller font for clips
        
        # Truncate name if too long
        font_metrics = painter.fontMetrics()
        text = clip.name
        if font_metrics.horizontalAdvance(text) > rect.width() - 10:
            text = font_metrics.elidedText(text, Qt.TextElideMode.ElideRight, rect.width() - 10)
            
        painter.drawText(rect.x() + 5, rect.y() + 15, text)
        
        # Duration text
        duration_text = self.format_duration(clip.duration)
        painter.setFont(QFont("Arial", 6))  # Smaller duration text
        painter.drawText(rect.x() + 5, rect.bottom() - 3, duration_text)  # Closer to bottom
        
    def draw_waveform(self, painter: QPainter, clip: TimelineClip, rect: QRect):
        """Draw audio waveform inside the clip"""
        if not clip.waveform_data:
            return
            
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
        
        # Calculate waveform display parameters
        waveform_height = rect.height() - 20  # Leave space for text
        center_y = rect.y() + rect.height() // 2
        
        # Sample waveform data to fit the clip width
        samples_per_pixel = max(1, len(clip.waveform_data) // rect.width())
        
        for x in range(rect.width()):
            sample_index = x * samples_per_pixel
            if sample_index < len(clip.waveform_data):
                # Get max amplitude for this pixel
                max_amp = 0
                for i in range(samples_per_pixel):
                    if sample_index + i < len(clip.waveform_data):
                        max_amp = max(max_amp, abs(clip.waveform_data[sample_index + i]))
                
                # Draw waveform line
                wave_height = int(max_amp * waveform_height / 2)
                painter.drawLine(
                    rect.x() + x, center_y - wave_height,
                    rect.x() + x, center_y + wave_height
                )
                
    def draw_video_thumbnails(self, painter: QPainter, clip: TimelineClip, rect: QRect):
        """Draw video thumbnail strip inside the clip"""
        if not clip.thumbnail:
            # Draw placeholder for video
            painter.setPen(QPen(QColor(200, 200, 200, 50), 1))
            painter.drawText(rect.center(), "Video")
            return
            
        # TODO: Implement thumbnail strip drawing
        # This would require extracting thumbnails from video at regular intervals
        pass
        
    def format_duration(self, seconds: float) -> str:
        """Format duration as MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
        
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            clip = self.get_clip_at_position(event.position().toPoint())
            current_tool = self.timeline_widget.current_tool
            
            if current_tool == TimelineTool.RAZOR and clip:
                # Split clip at current position
                time = (event.position().x() + self.timeline_widget.scroll_offset) / self.timeline_widget.pixels_per_second
                self.track.split_clip(clip.clip_id, time)
                self.update()
                
            elif current_tool == TimelineTool.SELECT and clip:
                # Select clip
                self.select_clip(clip)
                self.clip_selected.emit(clip.clip_id)
                
                # Start drag
                self.dragging_clip = clip
                self.drag_start_pos = event.position().toPoint()
                self.drag_offset = event.position().x() - (clip.start_time * self.timeline_widget.pixels_per_second - self.timeline_widget.scroll_offset)
                
    def mouseMoveEvent(self, event: QMouseEvent):
        if (self.dragging_clip and event.buttons() & Qt.MouseButton.LeftButton and 
            self.timeline_widget.current_tool == TimelineTool.SELECT):
            # Calculate new time position
            new_x = event.position().x() - self.drag_offset
            new_time = (new_x + self.timeline_widget.scroll_offset) / self.timeline_widget.pixels_per_second
            new_time = max(0, new_time)  # Don't allow negative time
            
            # Enhanced snapping if enabled
            if self.timeline_widget.snap_enabled:
                new_time = self.timeline_widget.snap_time(new_time, self.dragging_clip)
            
            # Calculate new track ID
            new_y = event.position().y()
            track_index = self.indexForTrack(self.dragging_clip.track)  # Get current index
            new_track_index = track_index
            for i, track in enumerate(self.timeline_widget.tracks):
                # Check if position is over a new track
                if new_y >= i * track.height and new_y < (i + 1) * track.height:
                    new_track_index = i
                    break

            # Move clip to new track if needed
            if new_track_index != track_index:
                self.timeline_widget.move_clip_to_track(self.dragging_clip, new_track_index)

            self.dragging_clip.start_time = new_time
            self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release event to complete drag operation"""
        if event.button() == Qt.MouseButton.LeftButton and self.dragging_clip:
            # Emit clip moved signal
            self.clip_moved.emit(
                self.dragging_clip.clip_id, 
                self.dragging_clip.start_time, 
                self.dragging_clip.track
            )
            
            # Clear drag state
            self.dragging_clip = None
            self.drag_start_pos = None
            self.drag_offset = 0
            
            # Final update
            self.update()
    
    def get_clip_at_position(self, pos: QPoint) -> Optional[TimelineClip]:
        """Get clip at mouse position"""
        time = (pos.x() + self.timeline_widget.scroll_offset) / self.timeline_widget.pixels_per_second
        return self.track.get_clip_at_time(time)
        
    def select_clip(self, clip: TimelineClip):
        """Select a clip and deselect others"""
        for c in self.track.clips:
            c.selected = (c == clip)
        self.update()
    
    def indexForTrack(self, track_id: int) -> int:
        """Get the index of a track by its ID"""
        for i, track in enumerate(self.timeline_widget.tracks):
            if track.track_id == track_id:
                return i
        return 0  # Default to first track if not found
    
    def dragEnterEvent(self, event):
        """Handle drag enter event for movable components"""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move event"""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        """Handle drop event"""
        # Get file paths from drop
        file_paths = []
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_paths.append(url.toLocalFile())
        elif event.mimeData().hasText():
            file_paths = event.mimeData().text().split('\n')
        
        # Add files to timeline (let timeline widget handle track assignment)
        for file_path in file_paths:
            if file_path.strip():
                self.timeline_widget.add_media_file(file_path)
        
        event.acceptProposedAction()

class TimelineWidget(QWidget):
    """Main timeline widget"""
    
    time_changed = pyqtSignal(float)  # Current playhead time
    clip_selected = pyqtSignal(str)   # Selected clip ID
    media_dropped = pyqtSignal(str, str)  # clip_id, file_path
    
    def __init__(self):
        super().__init__()
        self.tracks: List[TimelineTrack] = []
        self.pixels_per_second = 50  # Zoom level
        self.scroll_offset = 0
        self.playhead_time = 0.0
        self.snap_enabled = True
        self.duration = 60.0  # Total timeline duration
        
        self.setup_ui()
        self.create_default_tracks()
        self.current_tool = TimelineTool.SELECT
        self.clipboard = []
        
    def setup_ui(self):
        # Main horizontal layout: tools on left, timeline on right
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)
        
        # Left side: Vertical tool panel
        tools_panel = self.create_tools_panel()
        main_layout.addWidget(tools_panel)
        
        # Right side: Timeline area
        timeline_area = self.create_timeline_area()
        main_layout.addWidget(timeline_area, 1)  # Take most of the space
        
    def create_tools_panel(self):
        """Create vertical tools panel on the left"""
        tools_panel = QWidget()
        tools_panel.setFixedWidth(80)  # Fixed width for tool panel
        tools_panel.setStyleSheet("""
            QWidget {
                background-color: #2d2d30;
                border-right: 1px solid #464647;
            }
        """)
        
        tools_layout = QVBoxLayout(tools_panel)
        tools_layout.setContentsMargins(5, 5, 5, 5)
        tools_layout.setSpacing(3)
        
        # Tool buttons group
        self.tool_group = QButtonGroup()
        
        # Style for tool buttons
        tool_button_style = """
            QPushButton {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
                font-size: 10px;
                text-align: center;
                min-height: 20px;
            }
            QPushButton:checked {
                background-color: #007acc;
                color: white;
                border-color: #007acc;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-color: #007acc;
            }
        """
        
        # Create tool buttons vertically
        self.select_tool_btn = QPushButton("Select\n(V)")
        self.select_tool_btn.setCheckable(True)
        self.select_tool_btn.setChecked(True)
        self.select_tool_btn.clicked.connect(lambda: self.set_tool(TimelineTool.SELECT))
        self.select_tool_btn.setStyleSheet(tool_button_style)
        self.tool_group.addButton(self.select_tool_btn)
        tools_layout.addWidget(self.select_tool_btn)
        
        self.razor_tool_btn = QPushButton("Razor\n(C)")
        self.razor_tool_btn.setCheckable(True)
        self.razor_tool_btn.clicked.connect(lambda: self.set_tool(TimelineTool.RAZOR))
        self.razor_tool_btn.setStyleSheet(tool_button_style)
        self.tool_group.addButton(self.razor_tool_btn)
        tools_layout.addWidget(self.razor_tool_btn)
        
        self.hand_tool_btn = QPushButton("Hand\n(H)")
        self.hand_tool_btn.setCheckable(True)
        self.hand_tool_btn.clicked.connect(lambda: self.set_tool(TimelineTool.HAND))
        self.hand_tool_btn.setStyleSheet(tool_button_style)
        self.tool_group.addButton(self.hand_tool_btn)
        tools_layout.addWidget(self.hand_tool_btn)
        
        self.ripple_tool_btn = QPushButton("Ripple\n(R)")
        self.ripple_tool_btn.setCheckable(True)
        self.ripple_tool_btn.clicked.connect(lambda: self.set_tool(TimelineTool.RIPPLE))
        self.ripple_tool_btn.setStyleSheet(tool_button_style)
        self.tool_group.addButton(self.ripple_tool_btn)
        tools_layout.addWidget(self.ripple_tool_btn)
        
        self.slip_tool_btn = QPushButton("Slip\n(Y)")
        self.slip_tool_btn.setCheckable(True)
        self.slip_tool_btn.clicked.connect(lambda: self.set_tool(TimelineTool.SLIP))
        self.slip_tool_btn.setStyleSheet(tool_button_style)
        self.tool_group.addButton(self.slip_tool_btn)
        tools_layout.addWidget(self.slip_tool_btn)
        
        tools_layout.addStretch()  # Push buttons to top
        
        return tools_panel
        
    def create_timeline_area(self):
        """Create the main timeline area"""
        timeline_widget = QWidget()
        layout = QVBoxLayout(timeline_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Timeline controls
        controls_layout = QHBoxLayout()
        
        # Zoom controls
        zoom_label = QLabel("Zoom:")
        controls_layout.addWidget(zoom_label)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 200)
        self.zoom_slider.setValue(self.pixels_per_second)
        self.zoom_slider.valueChanged.connect(self.set_zoom)
        self.zoom_slider.setFixedWidth(100)
        controls_layout.addWidget(self.zoom_slider)
        
        # Snap toggle
        self.snap_button = QPushButton("Snap")
        self.snap_button.setCheckable(True)
        self.snap_button.setChecked(self.snap_enabled)
        self.snap_button.clicked.connect(self.toggle_snap)
        self.snap_button.setFixedWidth(50)  # Reduced width
        controls_layout.addWidget(self.snap_button)
        
        # Automation toggle
        self.automation_button = QPushButton("Auto")
        self.automation_button.setCheckable(True)
        self.automation_button.setChecked(False)
        self.automation_button.clicked.connect(self.toggle_automation_tracks)
        self.automation_button.setFixedWidth(50)
        self.automation_button.setToolTip("Toggle automation tracks visibility")
        controls_layout.addWidget(self.automation_button)
        
        controls_layout.addStretch()
        
        controls_widget = QWidget()
        controls_widget.setLayout(controls_layout)
        controls_widget.setFixedHeight(25)  # Better height for controls
        controls_widget.setStyleSheet("""
            QWidget {
                background-color: #2d2d30;
                border-bottom: 1px solid #464647;
            }
            QLabel {
                color: #cccccc;
                font-size: 11px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: 1px solid #464647;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 10px;
                min-height: 18px;
            }
            QPushButton:checked {
                background-color: #1177bb;
                border-color: #007acc;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
        """)
        layout.addWidget(controls_widget)
        
        # Timeline ruler
        self.ruler = TimelineRuler(self)
        layout.addWidget(self.ruler)
        
        # Scrollable timeline area
        self.scroll_area = QScrollArea()
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.horizontalScrollBar().valueChanged.connect(self.on_scroll)
        
        # Timeline content widget
        self.timeline_content = QWidget()
        self.timeline_layout = QVBoxLayout(self.timeline_content)
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)
        self.timeline_layout.setSpacing(1)
        
        self.scroll_area.setWidget(self.timeline_content)
        layout.addWidget(self.scroll_area)
        
        # Update timeline size
        self.update_timeline_size()
        
        # Keyboard shortcuts
        self.setup_shortcuts()
        
        return timeline_widget
        
    def create_default_tracks(self):
        """Create default video and audio tracks with proper separation"""
        # Video tracks
        for i in range(3):
            track = TimelineTrack(i, f"Video {i+1}", "video")
            self.add_track(track)
            
        # Audio tracks (separate from video)
        for i in range(4):
            track = TimelineTrack(i+10, f"Audio {i+1}", "audio")  # Use different ID range
            self.add_track(track)
            
    def add_track(self, track: TimelineTrack):
        """Add a track to the timeline"""
        self.tracks.append(track)
        
        # Create track widget
        track_widget = TimelineTrackWidget(track, self)
        track_widget.clip_selected.connect(self.clip_selected.emit)
        track_widget.clip_moved.connect(self.on_clip_moved)
        
        self.timeline_layout.addWidget(track_widget)
        self.update_timeline_size()
        
    def add_clip_to_track(self, track_id: int, clip_name: str, start_time: float, duration: float) -> str:
        """Add a clip to a specific track and make it movable"""
        if track_id < len(self.tracks):
            clip_id = f"clip_{len(self.get_all_clips())}"
            clip = TimelineClip(clip_id, clip_name, start_time, duration, track_id)
            
            # Set color based on track type
            if self.tracks[track_id].track_type == "audio":
                clip.color = QColor(50, 150, 50)  # Green for audio
            
            self.tracks[track_id].add_clip(clip)
            self.update_tracks()
            return clip_id
        return ""
        
    def remove_clip(self, clip_id: str):
        """Remove a clip from timeline"""
        for track in self.tracks:
            track.remove_clip(clip_id)
        self.update_tracks()
        
    def get_all_clips(self) -> List[TimelineClip]:
        """Get all clips from all tracks"""
        clips = []
        for track in self.tracks:
            clips.extend(track.clips)
        return clips
        
    def set_zoom(self, zoom_level: int):
        """Set timeline zoom level"""
        self.pixels_per_second = zoom_level
        self.update_timeline_size()
        self.update_tracks()
        self.ruler.update()
        
    def toggle_snap(self, enabled: bool):
        """Toggle snap to grid"""
        self.snap_enabled = enabled
        
    def snap_time(self, time: float, dragging_clip: Optional[TimelineClip] = None) -> float:
        """Snap time to various targets: grid, clips, playhead"""
        if not self.snap_enabled:
            return time
            
        snap_threshold = 0.5 / self.pixels_per_second * 10  # 10 pixels threshold
        candidates = []
        
        # Snap to grid (1 second intervals)
        grid_interval = 1.0
        grid_time = round(time / grid_interval) * grid_interval
        if abs(time - grid_time) < snap_threshold:
            candidates.append(grid_time)
            
        # Snap to playhead
        if abs(time - self.playhead_time) < snap_threshold:
            candidates.append(self.playhead_time)
            
        # Snap to other clips
        for track in self.tracks:
            for clip in track.clips:
                if dragging_clip and clip.clip_id == dragging_clip.clip_id:
                    continue  # Skip the clip being dragged
                    
                # Snap to clip start
                if abs(time - clip.start_time) < snap_threshold:
                    candidates.append(clip.start_time)
                    
                # Snap to clip end
                clip_end = clip.end_time()
                if abs(time - clip_end) < snap_threshold:
                    candidates.append(clip_end)
                    
        # Return the closest snap candidate or original time
        if candidates:
            return min(candidates, key=lambda t: abs(t - time))
        return time
        
    def on_scroll(self, value: int):
        """Handle horizontal scrolling"""
        self.scroll_offset = value
        self.update_tracks()
        self.ruler.update()
        
    def on_clip_moved(self, clip_id: str, new_time: float, track_id: int):
        """Handle clip movement"""
        # Update clip position and emit signal
        self.update_tracks()
        
    def set_playhead_time(self, time: float):
        """Set playhead position"""
        self.playhead_time = time
        self.time_changed.emit(time)
        self.update_tracks()
        
    def update_timeline_size(self):
        """Update timeline content size based on duration and zoom"""
        width = int(self.duration * self.pixels_per_second)
        height = sum(track.height + 1 for track in self.tracks)
        self.timeline_content.setFixedSize(width, height)
        
    def update_tracks(self):
        """Update all track widgets"""
        for i in range(self.timeline_layout.count()):
            widget = self.timeline_layout.itemAt(i).widget()
            if isinstance(widget, TimelineTrackWidget):
                widget.update()
                
    def paintEvent(self, event):
        """Draw playhead"""
        super().paintEvent(event)
        
        if hasattr(self, 'scroll_area'):
            painter = QPainter(self)
            
            # Calculate playhead position
            playhead_x = int(self.playhead_time * self.pixels_per_second - self.scroll_offset)
            
            # Draw playhead line
            if 0 <= playhead_x <= self.width():
                painter.setPen(QPen(QColor(255, 0, 0), 2))
                y_start = self.ruler.height() + 30  # After controls and ruler
                y_end = self.height()
                painter.drawLine(playhead_x, y_start, playhead_x, y_end)
                
    def setup_shortcuts(self):
        """Setup keyboard shortcuts for timeline tools"""
        # Tool shortcuts
        select_shortcut = QShortcut("V", self)
        select_shortcut.activated.connect(lambda: self.set_tool(TimelineTool.SELECT))
        
        razor_shortcut = QShortcut("C", self)
        razor_shortcut.activated.connect(lambda: self.set_tool(TimelineTool.RAZOR))
        
        hand_shortcut = QShortcut("H", self)
        hand_shortcut.activated.connect(lambda: self.set_tool(TimelineTool.HAND))
        
        ripple_shortcut = QShortcut("R", self)
        ripple_shortcut.activated.connect(lambda: self.set_tool(TimelineTool.RIPPLE))
        
        slip_shortcut = QShortcut("Y", self)
        slip_shortcut.activated.connect(lambda: self.set_tool(TimelineTool.SLIP))
        
        # Edit shortcuts
        delete_shortcut = QShortcut("Delete", self)
        delete_shortcut.activated.connect(self.delete_selected_clips)
        
        copy_shortcut = QShortcut("Ctrl+C", self)
        copy_shortcut.activated.connect(self.copy_selected_clips)
        
        paste_shortcut = QShortcut("Ctrl+V", self)
        paste_shortcut.activated.connect(self.paste_clips)
        
        split_shortcut = QShortcut("S", self)
        split_shortcut.activated.connect(self.split_at_playhead)
        
    def set_tool(self, tool: TimelineTool):
        """Set the current editing tool"""
        self.current_tool = tool
        
        # Update button states
        self.select_tool_btn.setChecked(tool == TimelineTool.SELECT)
        self.razor_tool_btn.setChecked(tool == TimelineTool.RAZOR)
        self.hand_tool_btn.setChecked(tool == TimelineTool.HAND)
        self.ripple_tool_btn.setChecked(tool == TimelineTool.RIPPLE)
        self.slip_tool_btn.setChecked(tool == TimelineTool.SLIP)
        
        # Update cursor based on tool
        if tool == TimelineTool.RAZOR:
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif tool == TimelineTool.HAND:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif tool == TimelineTool.RIPPLE:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif tool == TimelineTool.SLIP:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            
    def get_selected_clips(self) -> List[TimelineClip]:
        """Get all currently selected clips"""
        selected = []
        for track in self.tracks:
            for clip in track.clips:
                if clip.selected:
                    selected.append(clip)
        return selected
        
    def delete_selected_clips(self):
        """Delete all selected clips"""
        selected_clips = self.get_selected_clips()
        for clip in selected_clips:
            self.remove_clip(clip.clip_id)
            
    def copy_selected_clips(self):
        """Copy selected clips to clipboard"""
        selected_clips = self.get_selected_clips()
        self.clipboard = [copy.deepcopy(clip) for clip in selected_clips]
        
    def paste_clips(self):
        """Paste clips from clipboard at playhead"""
        if not self.clipboard:
            return
            
        for clip_data in self.clipboard:
            # Create new clip at playhead position
            new_clip = copy.deepcopy(clip_data)
            new_clip.clip_id = f"clip_{len(self.get_all_clips())}"
            new_clip.start_time = self.playhead_time
            
            # Add to appropriate track
            if new_clip.track < len(self.tracks):
                self.tracks[new_clip.track].add_clip(new_clip)
                
        self.update_tracks()
        
    def split_at_playhead(self):
        """Split clips at playhead position"""
        for track in self.tracks:
            clip = track.get_clip_at_time(self.playhead_time)
            if clip:
                track.split_clip(clip.clip_id, self.playhead_time)
        self.update_tracks()
    
    def add_media_to_track(self, track_id: int, file_path: str, start_time: float):
        """Add media file to specific track at specific time"""
        try:
            import os
            from moviepy import VideoFileClip, AudioFileClip, ImageClip
            
            # Get file extension to determine type
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Define supported file types
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
            image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.tga']
            audio_extensions = ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a']
            
            duration = 5.0  # Default duration
            clip = None
            
            if file_ext in video_extensions:
                # Handle video files
                clip = VideoFileClip(file_path)
                duration = clip.duration
                clip.close()
                
            elif file_ext in image_extensions:
                # Handle image files - create a 5 second clip
                duration = 5.0
                
            elif file_ext in audio_extensions:
                # Handle audio files
                clip = AudioFileClip(file_path)
                duration = clip.duration
                clip.close()
                
                # For audio files, use audio track if available
                if track_id < 2:  # If trying to add to video track
                    # Find first available audio track
                    for i, track in enumerate(self.tracks):
                        if track.track_type == "audio":
                            track_id = i
                            break
            else:
                print(f"Unsupported file type: {file_ext}")
                return None
            
            # Add clip to track
            clip_id = self.add_clip_to_track(
                track_id=track_id,
                clip_name=os.path.basename(file_path),
                start_time=start_time,
                duration=duration
            )
            
            # Emit signal for main window to handle
            self.media_dropped.emit(clip_id, file_path)
            
            return clip_id
            
        except Exception as e:
            print(f"Error adding media to track: {e}")
            return None
    
    def add_media_file(self, file_path: str):
        """Add media file to timeline, automatically managing tracks and positioning"""
        try:
            import os
            from moviepy import VideoFileClip, AudioFileClip, ImageClip
            
            # Get file extension to determine type
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Define supported file types
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
            image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.tga']
            audio_extensions = ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a']
            
            duration = 5.0  # Default duration
            clip = None
            track_type = "video"  # Default track type
            
            if file_ext in video_extensions:
                # Handle video files
                clip = VideoFileClip(file_path)
                duration = clip.duration
                clip.close()
                track_type = "video"
                
            elif file_ext in image_extensions:
                # Handle image files - create a 5 second clip
                duration = 5.0
                track_type = "video"
                
            elif file_ext in audio_extensions:
                # Handle audio files
                clip = AudioFileClip(file_path)
                duration = clip.duration
                clip.close()
                track_type = "audio"
            else:
                print(f"Unsupported file type: {file_ext}")
                return None
            
            # Find or create an appropriate track
            target_track = self.find_or_create_track(track_type)
            
            # Calculate start time (end of timeline)
            start_time = self.get_timeline_end_time()
            
            # Add clip to track
            clip_id = self.add_clip_to_track(
                track_id=target_track.track_id,
                clip_name=os.path.basename(file_path),
                start_time=start_time,
                duration=duration
            )
            
            # Update timeline duration if necessary
            new_end_time = start_time + duration
            if new_end_time > self.duration:
                self.duration = new_end_time + 10  # Add 10 seconds buffer
                self.update_timeline_size()
            
            # Emit signal for main window to handle
            self.media_dropped.emit(clip_id, file_path)
            
            return clip_id
            
        except Exception as e:
            print(f"Error adding media file: {e}")
            return None
    
    def find_or_create_track(self, track_type: str) -> TimelineTrack:
        """Find an available track or create a new one"""
        # Look for existing tracks of the same type
        tracks_of_type = [track for track in self.tracks if track.track_type == track_type]
        
        # For now, always create a new track for each file to avoid overlaps
        # This ensures each file gets its own "line" as requested
        track_count = len(tracks_of_type)
        track_id = len(self.tracks)  # Use total track count as ID
        track_name = f"{track_type.capitalize()} {track_count + 1}"
        
        new_track = TimelineTrack(track_id, track_name, track_type)
        self.add_track(new_track)
        
        return new_track
    
    def get_timeline_end_time(self) -> float:
        """Get the end time of all clips on the timeline"""
        max_end_time = 0.0
        
        for track in self.tracks:
            for clip in track.clips:
                clip_end = clip.end_time()
                if clip_end > max_end_time:
                    max_end_time = clip_end
        
        return max_end_time
    
    def move_clip_to_track(self, clip: TimelineClip, new_track_id: int):
        """Move a clip from one track to another"""
        if new_track_id >= len(self.tracks):
            return False
            
        # Find current track containing the clip
        current_track = None
        for track in self.tracks:
            if clip in track.clips:
                current_track = track
                break
        
        if not current_track:
            return False
            
        # Remove from current track
        current_track.remove_clip(clip.clip_id)
        
        # Add to new track
        target_track = self.tracks[new_track_id]
        clip.track = new_track_id  # Update clip's track reference
        target_track.add_clip(clip)
        
        # Update display
        self.update_tracks()
        return True
        
    def toggle_automation_tracks(self):
        """Toggle automation tracks visibility for all tracks"""
        for track in self.tracks:
            if track.track_type in ["audio", "video"]:
                track.toggle_automation_visibility()
        self.update_timeline_display()
        
    def update_timeline_display(self):
        """Update the timeline display including automation tracks"""
        # Clear existing widgets
        for i in reversed(range(self.timeline_layout.count())):
            item = self.timeline_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
        
        # Add main tracks
        for track in self.tracks:
            track_widget = TimelineTrackWidget(track, self)
            track_widget.clip_selected.connect(self.clip_selected.emit)
            track_widget.clip_moved.connect(self.on_clip_moved)
            self.timeline_layout.addWidget(track_widget)
            
            # Add automation tracks if visible
            if track.show_automation:
                for automation in track.automation_tracks:
                    automation_widget = self.create_automation_widget(automation)
                    self.timeline_layout.addWidget(automation_widget)
        
        self.update_timeline_size()
        
    def create_automation_widget(self, automation: AutomationTrack) -> QWidget:
        """Create a widget for displaying automation tracks"""
        automation_widget = QWidget()
        automation_widget.setFixedHeight(automation.height)
        automation_widget.setStyleSheet("background-color: #2a2a2a; border: 1px solid #444444;")
        
        layout = QHBoxLayout(automation_widget)
        layout.setContentsMargins(5, 0, 5, 0)
        
        # Automation parameter label
        label = QLabel(f"{automation.parameter_name.title()}")
        label.setFixedWidth(80)
        label.setStyleSheet("font-size: 10px; color: #cccccc;")
        layout.addWidget(label)
        
        # TODO: Add automation curve drawing here
        curve_area = QWidget()
        curve_area.setStyleSheet("background-color: #333333;")
        layout.addWidget(curve_area)
        
        return automation_widget
        
    def generate_waveform_data(self, file_path: str, clip: TimelineClip):
        """Generate waveform data for audio clips"""
        try:
            from moviepy import VideoFileClip, AudioFileClip
            import numpy as np
            
            # Try to load as video first (might have audio)
            try:
                video_clip = VideoFileClip(file_path)
                if video_clip.audio:
                    audio_array = video_clip.audio.to_soundarray()
                    video_clip.close()
                else:
                    return None
            except:
                # Try as audio file
                try:
                    audio_clip = AudioFileClip(file_path)
                    audio_array = audio_clip.to_soundarray()
                    audio_clip.close()
                except:
                    return None
            
            # Convert stereo to mono by averaging channels
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)
            
            # Downsample for waveform display (every 100th sample)
            sample_rate = 100
            downsampled = audio_array[::len(audio_array)//sample_rate] if len(audio_array) > sample_rate else audio_array
            
            # Normalize to [-1, 1] range
            if np.max(np.abs(downsampled)) > 0:
                downsampled = downsampled / np.max(np.abs(downsampled))
            
            clip.waveform_data = downsampled.tolist()
            clip.has_audio = True
            
        except Exception as e:
            print(f"Error generating waveform data: {e}")
            clip.waveform_data = None
