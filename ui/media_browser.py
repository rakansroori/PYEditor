"""
Enhanced Media Browser for PyVideoEditor
Includes thumbnails, metadata display, search functionality, and organization
"""

import sys
import os
import threading
from typing import Dict, List, Optional, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox, QProgressBar, QMenu,
    QSplitter, QListWidget, QListWidgetItem, QTabWidget, QFileDialog,
    QGroupBox, QCheckBox, QSpinBox, QMessageBox, QApplication
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize, QMimeData, QUrl
)
from PyQt6.QtGui import (
    QPixmap, QIcon, QPainter, QColor, QFont, QBrush, QPen,
    QDrag, QAction, QContextMenuEvent
)

class DraggableTreeWidget(QTreeWidget):
    """Tree widget with drag and drop support"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
    
    def startDrag(self, supportedActions):
        """Start drag operation for selected items"""
        selected_items = self.selectedItems()
        if not selected_items:
            return
            
        # Create drag object
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Add file paths to mime data
        file_paths = []
        urls = []
        for item in selected_items:
            file_path = item.data(0, Qt.ItemDataRole.UserRole)
            if file_path:
                file_paths.append(file_path)
                urls.append(QUrl.fromLocalFile(file_path))
        
        # Set mime data
        mime_data.setUrls(urls)
        mime_data.setText('\n'.join(file_paths))  # For internal use
        drag.setMimeData(mime_data)
        
        # Set drag pixmap (thumbnail of first item)
        if selected_items and selected_items[0].icon(0):
            drag.setPixmap(selected_items[0].icon(0).pixmap(64, 64))
        
        # Execute drag
        drag.exec(supportedActions)
import cv2
import numpy as np
from datetime import datetime, timedelta
import json

class MediaItem:
    """Represents a media item with metadata and thumbnail"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.file_size = 0
        self.duration = 0.0
        self.fps = 0.0
        self.resolution = (0, 0)
        self.format = ""
        self.codec = ""
        self.bitrate = 0
        self.thumbnail = None
        self.date_created = None
        self.date_modified = None
        self.tags = []
        self.rating = 0
        self.is_favorite = False
        self.metadata_loaded = False
        
        # Basic file info
        try:
            stat = os.stat(file_path)
            self.file_size = stat.st_size
            self.date_created = datetime.fromtimestamp(stat.st_ctime)
            self.date_modified = datetime.fromtimestamp(stat.st_mtime)
            self.format = os.path.splitext(file_path)[1].upper().replace('.', '')
        except:
            pass

class ThumbnailGenerator(QThread):
    """Background thread for generating video thumbnails"""
    
    thumbnail_ready = pyqtSignal(str, QPixmap, dict)  # file_path, thumbnail, metadata
    progress_updated = pyqtSignal(int, int)  # current, total
    
    def __init__(self):
        super().__init__()
        self.file_queue = []
        self.should_stop = False
        
    def add_file(self, file_path: str):
        """Add file to thumbnail generation queue"""
        if file_path not in self.file_queue:
            self.file_queue.append(file_path)
            
    def run(self):
        """Generate thumbnails for queued files"""
        total_files = len(self.file_queue)
        
        for i, file_path in enumerate(self.file_queue):
            if self.should_stop:
                break
                
            self.progress_updated.emit(i + 1, total_files)
            
            try:
                thumbnail, metadata = self.generate_thumbnail_and_metadata(file_path)
                if thumbnail:
                    self.thumbnail_ready.emit(file_path, thumbnail, metadata)
            except Exception as e:
                print(f"Error generating thumbnail for {file_path}: {e}")
                
        self.file_queue.clear()
        
    def generate_thumbnail_and_metadata(self, file_path: str) -> Tuple[Optional[QPixmap], Dict]:
        """Generate thumbnail and extract metadata from video file"""
        thumbnail = None
        metadata = {}
        
        try:
            # Use OpenCV to extract frame and metadata
            cap = cv2.VideoCapture(file_path)
            
            if cap.isOpened():
                # Get video properties
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                duration = frame_count / fps if fps > 0 else 0
                
                metadata = {
                    'duration': duration,
                    'fps': fps,
                    'resolution': (width, height),
                    'frame_count': frame_count
                }
                
                # Seek to 10% of duration for thumbnail
                seek_frame = int(frame_count * 0.1)
                cap.set(cv2.CAP_PROP_POS_FRAMES, seek_frame)
                
                ret, frame = cap.read()
                if ret:
                    # Resize frame for thumbnail
                    thumb_height = 60
                    thumb_width = int((width / height) * thumb_height)
                    frame_resized = cv2.resize(frame, (thumb_width, thumb_height))
                    
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                    
                    # Convert to QPixmap
                    h, w, ch = frame_rgb.shape
                    bytes_per_line = ch * w
                    from PyQt6.QtGui import QImage
                    q_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                    thumbnail = QPixmap.fromImage(q_image)
                    
            cap.release()
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            
        return thumbnail, metadata
        
    def stop(self):
        """Stop the thumbnail generation"""
        self.should_stop = True
        self.wait()

class MediaBrowserWidget(QWidget):
    """Enhanced media browser widget"""
    
    # Signals
    media_selected = pyqtSignal(str)  # file_path
    media_double_clicked = pyqtSignal(str)  # file_path
    
    def __init__(self):
        super().__init__()
        self.media_items: Dict[str, MediaItem] = {}
        self.current_folder = None
        self.thumbnail_generator = ThumbnailGenerator()
        self.thumbnail_generator.thumbnail_ready.connect(self.on_thumbnail_ready)
        self.thumbnail_generator.progress_updated.connect(self.on_progress_updated)
        self.thumbnail_generator.start()
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the media browser UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Title bar with search and controls
        title_bar = self.create_title_bar()
        layout.addWidget(title_bar)
        
        # Main splitter for folders and media
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Folder tree (left side)
        folder_panel = self.create_folder_panel()
        main_splitter.addWidget(folder_panel)
        
        # Media view (right side)
        media_panel = self.create_media_panel()
        main_splitter.addWidget(media_panel)
        
        # Set splitter proportions
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 3)
        
        layout.addWidget(main_splitter)
        
        # Progress bar for thumbnail generation
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
    def create_title_bar(self):
        """Create title bar with search and view controls"""
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title = QLabel("Media Browser")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: white; background-color: #2b2b2b; padding: 5px;")
        title_layout.addWidget(title)
        
        title_layout.addStretch()
        
        # Search box
        search_label = QLabel("Search:")
        search_label.setStyleSheet("color: white;")
        title_layout.addWidget(search_label)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search media...")
        self.search_box.textChanged.connect(self.filter_media)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background-color: #5a5a5a;
                color: white;
                border: 1px solid #777;
                padding: 3px;
                border-radius: 3px;
            }
        """)
        title_layout.addWidget(self.search_box)
        
        # View mode selector
        view_label = QLabel("View:")
        view_label.setStyleSheet("color: white;")
        title_layout.addWidget(view_label)
        
        self.view_combo = QComboBox()
        self.view_combo.addItems(["List", "Grid", "Details"])
        self.view_combo.currentTextChanged.connect(self.change_view_mode)
        self.view_combo.setStyleSheet("""
            QComboBox {
                background-color: #5a5a5a;
                color: white;
                border: 1px solid #777;
                padding: 3px;
            }
        """)
        title_layout.addWidget(self.view_combo)
        
        return title_widget
        
    def create_folder_panel(self):
        """Create folder navigation panel"""
        panel = QWidget()
        panel.setMinimumWidth(200)
        layout = QVBoxLayout(panel)
        
        # Folder tree
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderLabel("Folders")
        self.folder_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #3c3c3c;
                color: white;
                border: none;
            }
            QTreeWidget::item:selected {
                background-color: #094771;
            }
        """)
        
        # Add common folders
        self.add_common_folders()
        
        layout.addWidget(self.folder_tree)
        
        # Import buttons
        import_folder_btn = QPushButton("Import Folder")
        import_folder_btn.clicked.connect(self.import_folder)
        import_folder_btn.setStyleSheet(self.get_button_style())
        layout.addWidget(import_folder_btn)
        
        import_files_btn = QPushButton("Import Files")
        import_files_btn.clicked.connect(self.import_files)
        import_files_btn.setStyleSheet(self.get_button_style())
        layout.addWidget(import_files_btn)
        
        return panel
        
    def create_media_panel(self):
        """Create media display panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Media view with drag and drop support
        self.media_view = DraggableTreeWidget()
        self.media_view.setHeaderLabels(["", "Name", "Duration", "Resolution", "Size", "Modified"])
        self.media_view.setRootIsDecorated(False)
        self.media_view.setAlternatingRowColors(True)
        self.media_view.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.media_view.itemDoubleClicked.connect(self.on_media_double_clicked)
        self.media_view.itemSelectionChanged.connect(self.on_media_selection_changed)
        self.media_view.setStyleSheet("""
            QTreeWidget {
                background-color: #3c3c3c;
                color: white;
                border: none;
                alternate-background-color: #404040;
            }
            QTreeWidget::item:selected {
                background-color: #094771;
            }
        """)
        
        # Set column widths
        self.media_view.setColumnWidth(0, 80)   # Thumbnail
        self.media_view.setColumnWidth(1, 200)  # Name
        self.media_view.setColumnWidth(2, 80)   # Duration
        self.media_view.setColumnWidth(3, 100)  # Resolution
        self.media_view.setColumnWidth(4, 80)   # Size
        self.media_view.setColumnWidth(5, 120)  # Modified
        
        layout.addWidget(self.media_view)
        
        # Info panel for selected media
        info_panel = self.create_info_panel()
        layout.addWidget(info_panel)
        
        return panel
        
    def create_info_panel(self):
        """Create media info panel"""
        group = QGroupBox("Media Information")
        group.setMaximumHeight(150)
        layout = QVBoxLayout(group)
        
        self.info_label = QLabel("Select a media file to view information")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: white; padding: 10px;")
        layout.addWidget(self.info_label)
        
        return group
        
    def add_common_folders(self):
        """Add common media folders to the tree"""
        # Recent imports
        recent_item = QTreeWidgetItem(["Recent"])
        recent_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_DirIcon))
        self.folder_tree.addTopLevelItem(recent_item)
        
        # Favorites
        favorites_item = QTreeWidgetItem(["Favorites"])
        favorites_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_DirIcon))
        self.folder_tree.addTopLevelItem(favorites_item)
        
        # Project media
        project_item = QTreeWidgetItem(["Project Media"])
        project_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_DirIcon))
        self.folder_tree.addTopLevelItem(project_item)
        
    def get_button_style(self):
        """Get standard button style"""
        return """
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
        """
        
    def import_folder(self):
        """Import entire folder of media files"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Media Folder")
        if folder_path:
            self.scan_folder(folder_path)
            
    def import_files(self):
        """Import individual media files"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Import Media Files", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm);;Audio Files (*.mp3 *.wav *.aac *.flac);;Image Files (*.jpg *.jpeg *.png *.bmp *.tiff);;All Files (*)"
        )
        
        if file_paths:
            for file_path in file_paths:
                self.add_media_file(file_path)
                
    def scan_folder(self, folder_path: str):
        """Scan folder for media files"""
        supported_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', 
                               '.mp3', '.wav', '.aac', '.flac', '.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        
        media_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if os.path.splitext(file)[1].lower() in supported_extensions:
                    media_files.append(os.path.join(root, file))
        
        # Add files to browser
        for file_path in media_files:
            self.add_media_file(file_path)
            
        self.status_message(f"Imported {len(media_files)} media files from {folder_path}")
        
    def add_media_file(self, file_path: str):
        """Add media file to browser"""
        if file_path in self.media_items:
            return  # Already added
            
        # Create media item
        media_item = MediaItem(file_path)
        self.media_items[file_path] = media_item
        
        # Add to view
        self.add_media_to_view(media_item)
        
        # Queue for thumbnail generation
        if self.is_video_file(file_path):
            self.thumbnail_generator.add_file(file_path)
            
    def add_media_to_view(self, media_item: MediaItem):
        """Add media item to the current view"""
        # Create tree item
        item = QTreeWidgetItem()
        
        # Set data
        item.setText(1, media_item.file_name)
        item.setText(2, self.format_duration(media_item.duration))
        item.setText(3, f"{media_item.resolution[0]}x{media_item.resolution[1]}" if media_item.resolution[0] > 0 else "")
        item.setText(4, self.format_file_size(media_item.file_size))
        item.setText(5, media_item.date_modified.strftime("%m/%d/%Y %H:%M") if media_item.date_modified else "")
        
        # Store file path
        item.setData(0, Qt.ItemDataRole.UserRole, media_item.file_path)
        
        # Add to tree
        self.media_view.addTopLevelItem(item)
        
    def on_thumbnail_ready(self, file_path: str, thumbnail: QPixmap, metadata: dict):
        """Handle thumbnail generation completion"""
        if file_path in self.media_items:
            media_item = self.media_items[file_path]
            media_item.thumbnail = thumbnail
            
            # Update metadata
            media_item.duration = metadata.get('duration', 0.0)
            media_item.fps = metadata.get('fps', 0.0)
            media_item.resolution = metadata.get('resolution', (0, 0))
            media_item.metadata_loaded = True
            
            # Update view
            self.update_media_item_display(file_path)
            
    def update_media_item_display(self, file_path: str):
        """Update media item display with new information"""
        media_item = self.media_items[file_path]
        
        # Find item in tree
        for i in range(self.media_view.topLevelItemCount()):
            item = self.media_view.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == file_path:
                # Update thumbnail
                if media_item.thumbnail:
                    item.setIcon(0, QIcon(media_item.thumbnail))
                
                # Update metadata
                item.setText(2, self.format_duration(media_item.duration))
                item.setText(3, f"{media_item.resolution[0]}x{media_item.resolution[1]}" if media_item.resolution[0] > 0 else "")
                break
                
    def on_progress_updated(self, current: int, total: int):
        """Handle thumbnail generation progress"""
        if total > 0:
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
            
            if current >= total:
                self.progress_bar.setVisible(False)
        else:
            self.progress_bar.setVisible(False)
            
    def on_media_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle media item double click"""
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if file_path:
            self.media_double_clicked.emit(file_path)
            
    def on_media_selection_changed(self):
        """Handle media selection change"""
        selected_items = self.media_view.selectedItems()
        if selected_items:
            item = selected_items[0]
            file_path = item.data(0, Qt.ItemDataRole.UserRole)
            if file_path:
                self.media_selected.emit(file_path)
                self.update_info_panel(file_path)
                
    def update_info_panel(self, file_path: str):
        """Update info panel with media information"""
        if file_path in self.media_items:
            media_item = self.media_items[file_path]
            
            info_text = f"""
            <b>File:</b> {media_item.file_name}<br>
            <b>Path:</b> {media_item.file_path}<br>
            <b>Size:</b> {self.format_file_size(media_item.file_size)}<br>
            <b>Format:</b> {media_item.format}<br>
            <b>Duration:</b> {self.format_duration(media_item.duration)}<br>
            <b>Resolution:</b> {media_item.resolution[0]}x{media_item.resolution[1]}<br>
            <b>FPS:</b> {media_item.fps:.2f}<br>
            <b>Modified:</b> {media_item.date_modified.strftime("%m/%d/%Y %H:%M") if media_item.date_modified else "Unknown"}
            """
            
            self.info_label.setText(info_text)
        else:
            self.info_label.setText("Select a media file to view information")
            
    def filter_media(self, search_text: str):
        """Filter media based on search text"""
        for i in range(self.media_view.topLevelItemCount()):
            item = self.media_view.topLevelItem(i)
            file_name = item.text(1).lower()
            
            # Show/hide based on search
            visible = search_text.lower() in file_name if search_text else True
            item.setHidden(not visible)
            
    def change_view_mode(self, mode: str):
        """Change media view mode"""
        # This could switch between different view types
        # For now, we'll just update the header
        if mode == "Grid":
            # Could implement grid view here
            pass
        elif mode == "Details":
            # Show more detailed information
            pass
            
    def is_video_file(self, file_path: str) -> bool:
        """Check if file is a video file"""
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
        return os.path.splitext(file_path)[1].lower() in video_extensions
        
    def format_duration(self, seconds: float) -> str:
        """Format duration as MM:SS"""
        if seconds <= 0:
            return ""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
        
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f} {size_names[i]}"
        
    def status_message(self, message: str):
        """Display status message (can be connected to main window status bar)"""
        print(f"Media Browser: {message}")
        
    def closeEvent(self, event):
        """Handle widget close"""
        self.thumbnail_generator.stop()
        super().closeEvent(event)
