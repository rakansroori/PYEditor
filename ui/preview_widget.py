"""
Advanced Preview System for PyVideoEditor
Real-time video preview with timeline scrubbing, playback controls, and quality settings
"""

import sys
import threading
import time
from typing import Optional, Tuple, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSlider, QComboBox, QFrame, QSizePolicy, QSpacerItem,
    QProgressBar, QCheckBox, QSpinBox
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QMutex, QMutexLocker,
    QSize, QRect
)
from PyQt6.QtGui import (
    QPainter, QPixmap, QImage, QPalette, QFont, QColor,
    QBrush, QPen, QIcon
)
import cv2
import numpy as np

class VideoFrameCache:
    """Cache for video frames to improve playback performance"""
    
    def __init__(self, max_frames: int = 100):
        self.max_frames = max_frames
        self.frames = {}  # time -> frame
        self.access_order = []  # LRU order
        self.mutex = QMutex()
        
    def get_frame(self, time: float) -> Optional[np.ndarray]:
        """Get cached frame at specific time"""
        with QMutexLocker(self.mutex):
            if time in self.frames:
                # Move to end (most recently used)
                self.access_order.remove(time)
                self.access_order.append(time)
                return self.frames[time].copy()
        return None
        
    def cache_frame(self, time: float, frame: np.ndarray):
        """Cache a frame at specific time"""
        with QMutexLocker(self.mutex):
            # Remove if already exists
            if time in self.frames:
                self.access_order.remove(time)
            
            # Add new frame
            self.frames[time] = frame.copy()
            self.access_order.append(time)
            
            # Remove oldest if cache is full
            while len(self.frames) > self.max_frames:
                oldest_time = self.access_order.pop(0)
                del self.frames[oldest_time]
                
    def clear(self):
        """Clear all cached frames"""
        with QMutexLocker(self.mutex):
            self.frames.clear()
            self.access_order.clear()

class PreviewWorker(QThread):
    """Background thread for video frame processing"""
    
    frame_ready = pyqtSignal(float, np.ndarray)  # time, frame
    
    def __init__(self):
        super().__init__()
        self.video_clip = None
        self.current_time = 0.0
        self.is_playing = False
        self.fps = 30.0
        self.quality_scale = 1.0
        self.frame_cache = VideoFrameCache()
        self.mutex = QMutex()
        self.should_stop = False
        
    def set_video_clip(self, clip):
        """Set the video clip for preview"""
        with QMutexLocker(self.mutex):
            self.video_clip = clip
            self.frame_cache.clear()
            if clip:
                self.fps = clip.fps if hasattr(clip, 'fps') else 30.0
                
    def set_time(self, time: float):
        """Set current playback time"""
        with QMutexLocker(self.mutex):
            self.current_time = max(0, time)
            if self.video_clip and self.current_time > self.video_clip.duration:
                self.current_time = self.video_clip.duration
                
    def set_playing(self, playing: bool):
        """Set playback state"""
        with QMutexLocker(self.mutex):
            self.is_playing = playing
            
    def set_quality_scale(self, scale: float):
        """Set preview quality scale (0.25, 0.5, 1.0)"""
        with QMutexLocker(self.mutex):
            self.quality_scale = scale
            self.frame_cache.clear()  # Clear cache when quality changes
            
    def get_frame_at_time(self, time: float) -> Optional[np.ndarray]:
        """Get frame at specific time"""
        if not self.video_clip:
            return None
            
        # Check cache first
        cached_frame = self.frame_cache.get_frame(time)
        if cached_frame is not None:
            return cached_frame
            
        try:
            # Get frame from video clip
            frame = self.video_clip.get_frame(time)
            
            # Scale frame if needed
            if self.quality_scale != 1.0:
                height, width = frame.shape[:2]
                new_width = int(width * self.quality_scale)
                new_height = int(height * self.quality_scale)
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
                
            # Cache the frame
            self.frame_cache.cache_frame(time, frame)
            return frame
            
        except Exception as e:
            print(f"Error getting frame at time {time}: {e}")
            return None
            
    def run(self):
        """Main thread loop for video playback"""
        frame_interval = 1.0 / self.fps
        
        while not self.should_stop:
            with QMutexLocker(self.mutex):
                if self.is_playing and self.video_clip:
                    # Get current frame
                    frame = self.get_frame_at_time(self.current_time)
                    if frame is not None:
                        self.frame_ready.emit(self.current_time, frame)
                    
                    # Advance time
                    self.current_time += frame_interval
                    if self.current_time >= self.video_clip.duration:
                        self.current_time = 0.0  # Loop
                        
                elif not self.is_playing and self.video_clip:
                    # Still frame mode - show current frame
                    frame = self.get_frame_at_time(self.current_time)
                    if frame is not None:
                        self.frame_ready.emit(self.current_time, frame)
                        
            # Sleep for frame interval
            self.msleep(int(frame_interval * 1000))
            
    def stop(self):
        """Stop the worker thread"""
        self.should_stop = True
        self.wait()

class TimelineScrubbingWidget(QWidget):
    """Widget for timeline scrubbing with preview thumbnails"""
    
    time_changed = pyqtSignal(float)
    
    def __init__(self):
        super().__init__()
        self.duration = 60.0
        self.current_time = 0.0
        self.is_scrubbing = False
        self.setFixedHeight(60)
        self.setMouseTracking(True)
        
    def set_duration(self, duration: float):
        """Set video duration"""
        self.duration = max(1.0, duration)
        self.update()
        
    def set_time(self, time: float):
        """Set current time"""
        self.current_time = max(0, min(time, self.duration))
        self.update()
        
    def paintEvent(self, event):
        """Draw the scrubbing timeline"""
        painter = QPainter(self)
        rect = self.rect()
        
        # Background
        painter.fillRect(rect, QColor(40, 40, 40))
        
        # Timeline track
        track_rect = QRect(10, rect.height() // 2 - 5, rect.width() - 20, 10)
        painter.fillRect(track_rect, QColor(60, 60, 60))
        
        # Progress
        if self.duration > 0:
            progress_width = int((self.current_time / self.duration) * track_rect.width())
            progress_rect = QRect(track_rect.x(), track_rect.y(), progress_width, track_rect.height())
            painter.fillRect(progress_rect, QColor(70, 130, 180))
            
            # Playhead
            playhead_x = track_rect.x() + progress_width
            playhead_rect = QRect(playhead_x - 2, rect.y() + 5, 4, rect.height() - 10)
            painter.fillRect(playhead_rect, QColor(255, 255, 255))
            
        # Time markers
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.setFont(QFont("Arial", 8))
        
        # Draw time markers every 10 seconds
        marker_interval = 10.0
        for i in range(int(self.duration / marker_interval) + 1):
            time_pos = i * marker_interval
            x = int(track_rect.x() + (time_pos / self.duration) * track_rect.width())
            
            painter.drawLine(x, track_rect.bottom(), x, track_rect.bottom() + 5)
            
            # Time text
            time_text = f"{int(time_pos // 60):02d}:{int(time_pos % 60):02d}"
            painter.drawText(x - 15, rect.bottom() - 5, time_text)
            
    def mousePressEvent(self, event):
        """Handle mouse press for scrubbing"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_scrubbing = True
            self.update_time_from_mouse(event.position().x())
            
    def mouseMoveEvent(self, event):
        """Handle mouse move for scrubbing"""
        if self.is_scrubbing:
            self.update_time_from_mouse(event.position().x())
            
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_scrubbing = False
            
    def update_time_from_mouse(self, mouse_x: float):
        """Update time based on mouse position"""
        track_rect = QRect(10, self.rect().height() // 2 - 5, self.rect().width() - 20, 10)
        relative_x = max(0, min(mouse_x - track_rect.x(), track_rect.width()))
        
        if track_rect.width() > 0:
            new_time = (relative_x / track_rect.width()) * self.duration
            self.set_time(new_time)
            self.time_changed.emit(self.current_time)
class PreviewWidget(QWidget):
    """Simplified preview widget with video display and controls"""
    
    # Signals
    time_changed = pyqtSignal(float)
    frame_changed = pyqtSignal(float, np.ndarray)
    
    def __init__(self):
        super().__init__()
        self.video_clip = None
        self.current_time = 0.0
        self.duration = 0.0
        self.is_playing = False
        self.quality_scale = 1.0
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.advance_frame)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the preview UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Title bar with controls
        title_bar = self.create_title_bar()
        layout.addWidget(title_bar)
        
        # Main preview area
        self.preview_label = QLabel("No Video Loaded")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                color: #888;
                border: 2px solid #444;
                font-size: 16px;
                min-height: 300px;
            }
        """)
        self.preview_label.setScaledContents(True)
        layout.addWidget(self.preview_label)
        
        # Timeline scrubbing
        self.scrubbing_widget = TimelineScrubbingWidget()
        self.scrubbing_widget.time_changed.connect(self.seek_to_time)
        layout.addWidget(self.scrubbing_widget)
        
        # Playback controls
        controls_bar = self.create_controls_bar()
        layout.addWidget(controls_bar)
        
        # Set stretch factors
        layout.setStretchFactor(self.preview_label, 1)
        
    def create_title_bar(self):
        """Create title bar with quality and display controls"""
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title = QLabel("Program Monitor")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: white; background-color: #2b2b2b; padding: 5px;")
        title_layout.addWidget(title)
        
        title_layout.addStretch()
        
        # Quality selector
        quality_label = QLabel("Quality:")
        quality_label.setStyleSheet("color: white;")
        title_layout.addWidget(quality_label)
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["1/4 (25%)", "1/2 (50%)", "Full (100%)"])
        self.quality_combo.setCurrentIndex(2)  # Default to full quality
        self.quality_combo.currentTextChanged.connect(self.on_quality_changed)
        self.quality_combo.setStyleSheet("""
            QComboBox {
                background-color: #5a5a5a;
                color: white;
                border: 1px solid #777;
                padding: 3px;
                min-width: 80px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                border: none;
            }
        """)
        title_layout.addWidget(self.quality_combo)
        
        # Show safe areas checkbox
        self.safe_areas_cb = QCheckBox("Safe Areas")
        self.safe_areas_cb.setStyleSheet("color: white;")
        self.safe_areas_cb.toggled.connect(self.toggle_safe_areas)
        title_layout.addWidget(self.safe_areas_cb)
        
        return title_widget
        
    def create_controls_bar(self):
        """Create playback controls bar"""
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(5, 5, 5, 5)
        
        # Playback buttons
        self.play_button = QPushButton("▶")
        self.play_button.setFixedSize(40, 30)
        self.play_button.clicked.connect(self.toggle_playback)
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #5a5a5a;
                color: white;
                border: 1px solid #777;
                border-radius: 3px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #6a6a6a;
            }
        """)
        controls_layout.addWidget(self.play_button)
        
        # Stop button
        stop_button = QPushButton("⏹")
        stop_button.setFixedSize(30, 30)
        stop_button.clicked.connect(self.stop_playback)
        stop_button.setStyleSheet(self.play_button.styleSheet())
        controls_layout.addWidget(stop_button)
        
        # Previous/Next frame buttons
        prev_frame_button = QPushButton("⏮")
        prev_frame_button.setFixedSize(30, 30)
        prev_frame_button.clicked.connect(self.previous_frame)
        prev_frame_button.setStyleSheet(self.play_button.styleSheet())
        controls_layout.addWidget(prev_frame_button)
        
        next_frame_button = QPushButton("⏭")
        next_frame_button.setFixedSize(30, 30)
        next_frame_button.clicked.connect(self.next_frame)
        next_frame_button.setStyleSheet(self.play_button.styleSheet())
        controls_layout.addWidget(next_frame_button)
        
        controls_layout.addStretch()
        
        # Time display
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setFont(QFont("Courier", 10))
        self.time_label.setStyleSheet("color: white; background-color: #3a3a3a; padding: 5px; border-radius: 3px;")
        controls_layout.addWidget(self.time_label)
        
        # Loop checkbox
        self.loop_cb = QCheckBox("Repeat")
        self.loop_cb.setStyleSheet("color: white;")
        controls_layout.addWidget(self.loop_cb)
        
        return controls_widget
        
    def set_video_clip(self, clip):
        """Set video clip for preview"""
        try:
            self.video_clip = clip
            
            if clip:
                self.duration = clip.duration if hasattr(clip, 'duration') else 5.0
                self.scrubbing_widget.set_duration(self.duration)
                
                # Display first frame immediately
                self.display_frame_at_time(0.0)
                self.current_time = 0.0
            else:
                self.duration = 0.0
                self.preview_label.setText("No Video Loaded")
                self.preview_label.setStyleSheet("background-color: #2b2b2b; color: white; font-size: 16px;")
                
            self.update_time_display()
            
        except Exception as e:
            print(f"Error setting video clip: {e}")
            self.preview_label.setText("Error Loading Video")
            self.preview_label.setStyleSheet("background-color: #2b2b2b; color: red; font-size: 16px;")
    
    def display_frame_at_time(self, time: float):
        """Display frame at specific time"""
        try:
            if not self.video_clip:
                return
                
            # Get frame from video clip
            frame = self.video_clip.get_frame(time)
            
            if frame is not None:
                # Convert numpy array to QPixmap
                height, width, channels = frame.shape
                bytes_per_line = channels * width
                
                # Ensure frame is in RGB format
                if channels == 3:
                    # MoviePy frames are typically in RGB format already
                    frame_rgb = frame
                else:
                    frame_rgb = frame
                    
                # Create QImage
                q_image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(q_image)
                
                # Scale to fit preview area maintaining aspect ratio
                if pixmap and not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        self.preview_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.preview_label.setPixmap(scaled_pixmap)
                    self.preview_label.setScaledContents(False)
                    self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    self.preview_label.setText("Invalid Frame")
            else:
                self.preview_label.setText("No Frame Available")
                
        except Exception as e:
            print(f"Error displaying frame: {e}")
            self.preview_label.setText(f"Frame Error: {str(e)}")
        
    def seek_to_time(self, time: float):
        """Seek to specific time"""
        self.current_time = max(0, min(time, self.duration))
        self.display_frame_at_time(self.current_time)
        self.scrubbing_widget.set_time(self.current_time)
        self.update_time_display()
        self.time_changed.emit(self.current_time)
        
    def toggle_playback(self):
        """Toggle play/pause"""
        if not self.video_clip:
            return
            
        self.is_playing = not self.is_playing
        
        if self.is_playing:
            self.play_button.setText("⏸")
            # Start playback timer (30 FPS)
            self.playback_timer.start(33)  # ~30 FPS
        else:
            self.play_button.setText("▶")
            self.playback_timer.stop()
    
    def advance_frame(self):
        """Advance to next frame during playback"""
        if not self.is_playing or not self.video_clip:
            return
            
        # Calculate frame duration
        fps = getattr(self.video_clip, 'fps', 30.0)
        frame_duration = 1.0 / fps
        
        # Advance time
        new_time = self.current_time + frame_duration
        
        # Check if we've reached the end
        if new_time >= self.duration:
            if self.loop_cb.isChecked():
                new_time = 0.0  # Loop back to start
            else:
                self.is_playing = False
                self.playback_timer.stop()
                self.play_button.setText("▶")
                return
        
        # Update display
        self.seek_to_time(new_time)
            
    def stop_playback(self):
        """Stop playback and return to beginning"""
        self.is_playing = False
        self.playback_timer.stop()
        self.play_button.setText("▶")
        self.seek_to_time(0.0)
        
    def previous_frame(self):
        """Go to previous frame"""
        if self.video_clip:
            frame_duration = 1.0 / (self.video_clip.fps if hasattr(self.video_clip, 'fps') else 30.0)
            new_time = max(0, self.current_time - frame_duration)
            self.seek_to_time(new_time)
            
    def next_frame(self):
        """Go to next frame"""
        if self.video_clip:
            frame_duration = 1.0 / (self.video_clip.fps if hasattr(self.video_clip, 'fps') else 30.0)
            new_time = min(self.duration, self.current_time + frame_duration)
            self.seek_to_time(new_time)
            
    def on_quality_changed(self, quality_text: str):
        """Handle quality change"""
        if "25%" in quality_text:
            self.quality_scale = 0.25
        elif "50%" in quality_text:
            self.quality_scale = 0.5
        else:
            self.quality_scale = 1.0
            
        # Refresh current frame with new quality
        self.display_frame_at_time(self.current_time)
        
    def toggle_safe_areas(self, enabled: bool):
        """Toggle safe area overlay"""
        # This would overlay safe area guides on the preview
        self.update()
        
    def on_frame_ready(self, time: float, frame: np.ndarray):
        """Handle new frame from worker thread"""
        if frame is not None:
            # Convert frame to QPixmap
            height, width, channels = frame.shape
            bytes_per_line = channels * width
            
            # Convert BGR to RGB if needed
            if channels == 3:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                frame_rgb = frame
                
            q_image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            
            # Scale pixmap to fit preview area while maintaining aspect ratio
            preview_size = self.preview_label.size()
            scaled_pixmap = pixmap.scaled(
                preview_size, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.preview_label.setPixmap(scaled_pixmap)
            
            # Emit frame changed signal
            self.frame_changed.emit(time, frame)
            
        # Update time if playing
        if self.is_playing:
            self.current_time = time
            self.scrubbing_widget.set_time(time)
            self.update_time_display()
            
    def update_time_display(self):
        """Update time display"""
        current_str = self.format_time(self.current_time)
        duration_str = self.format_time(self.duration)
        self.time_label.setText(f"{current_str} / {duration_str}")
        
    def format_time(self, seconds: float) -> str:
        """Format time as MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
        
    def paintEvent(self, event):
        """Custom paint event for overlays"""
        super().paintEvent(event)
        
        # Draw safe areas if enabled
        if self.safe_areas_cb.isChecked() and self.preview_label.pixmap():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Get preview area
            preview_rect = self.preview_label.geometry()
            
            # Draw title safe area (90% of frame)
            title_safe_margin = 0.05
            title_rect = QRect(
                int(preview_rect.x() + preview_rect.width() * title_safe_margin),
                int(preview_rect.y() + preview_rect.height() * title_safe_margin),
                int(preview_rect.width() * (1 - 2 * title_safe_margin)),
                int(preview_rect.height() * (1 - 2 * title_safe_margin))
            )
            
            painter.setPen(QPen(QColor(255, 255, 0, 128), 2))
            painter.drawRect(title_rect)
            
            # Draw action safe area (95% of frame)
            action_safe_margin = 0.025
            action_rect = QRect(
                int(preview_rect.x() + preview_rect.width() * action_safe_margin),
                int(preview_rect.y() + preview_rect.height() * action_safe_margin),
                int(preview_rect.width() * (1 - 2 * action_safe_margin)),
                int(preview_rect.height() * (1 - 2 * action_safe_margin))
            )
            
            painter.setPen(QPen(QColor(255, 0, 0, 128), 2))
            painter.drawRect(action_rect)
            
    def closeEvent(self, event):
        """Handle widget close"""
        self.playback_timer.stop()
        super().closeEvent(event)
