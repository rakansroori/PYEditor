import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, 
    QSlider, QLabel, QWidget, QGroupBox, QFileDialog, QTabWidget,
    QSplitter, QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem,
    QScrollArea, QFrame, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox,
    QCheckBox, QProgressBar, QStatusBar, QMenuBar, QMenu, QToolBar,
    QDockWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from ui.timeline_widget import TimelineWidget
from ui.preview_widget import PreviewWidget
from ui.media_browser import MediaBrowserWidget
from PyQt6.QtGui import QAction, QPixmap, QPainter, QColor, QFont
from core.video_processor import VideoProcessor
from .project_manager_dialog import ProjectManagerDialog
from core.color_grading import ColorGrading
from core.audio_editing import AudioProcessor, WaveformWidget, AudioEffectsManager
from core.keyframing import AnimationManager
from core.timeline import Timeline
from core.chroma_key import ChromaKeyManager
from core.text_system import TitleSystem, TextStyle, TextAnimationConfig

class VideoEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set recursion limit to prevent crashes
        import sys
        sys.setrecursionlimit(1500)
        
        # Initialize flags to prevent recursive loading and time sync
        self._loading_media = False
        self._syncing_time = False
        self.video_processor = VideoProcessor()
        self.color_grading = ColorGrading()
        self.audio_processor = AudioProcessor()
        self.audio_effects = AudioEffectsManager()
        self.timeline = Timeline()
        self.animation_manager = AnimationManager()
        self.chroma_key_manager = ChromaKeyManager()
        self.title_system = TitleSystem()
        self.current_clip_id = None
        self.current_project_id = None
        self.timeline_clips = {}  # Dictionary to store clip_id -> file_path mapping
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("PyVideoEditor - Professional Video Editor")
        self.setGeometry(100, 100, 1600, 1000)  # Larger window size for single-window layout
        
        # Apply Adobe Premiere Pro dark theme
        self.apply_premiere_theme()
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Create main layout with Adobe Premiere-style panels
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create the tabbed corner layout structure
        self.create_premiere_tabbed_layout(central_widget)
        
        # Store original clip for reset purposes
        self.original_clip = None
        
        # Connect timeline signals (with error handling)
        try:
            self.timeline_widget.time_changed.connect(self.on_timeline_time_changed)
            self.timeline_widget.clip_selected.connect(self.on_timeline_clip_selected)
            self.timeline_widget.media_dropped.connect(self.on_media_added_to_timeline)
        except Exception as e:
            print(f"Error connecting timeline signals: {e}")
            
        # Note: Timeline track signals will be connected when tracks are created
        
        # Connect preview widget signals (with error handling)
        try:
            self.preview_widget.time_changed.connect(self.on_preview_time_changed)
            self.preview_widget.frame_changed.connect(self.on_preview_frame_changed)
        except Exception as e:
            print(f"Error connecting preview signals: {e}")
        
        # Connect media browser signals (with error handling)
        try:
            self.media_browser.media_selected.connect(self.on_media_selected)
            self.media_browser.media_double_clicked.connect(self.on_media_double_clicked)
        except Exception as e:
            print(f"Error connecting media browser signals: {e}")
        
        # Show startup project manager
        QTimer.singleShot(500, self.show_startup_project_manager)
        
        # Connect existing track widget signals
        self.connect_track_signals()
    
    def connect_track_signals(self):
        """Connect signals from timeline track widgets"""
        try:
            # Connect signals from existing track widgets
            for i in range(self.timeline_widget.timeline_layout.count()):
                item = self.timeline_widget.timeline_layout.itemAt(i)
                if item and item.widget():
                    track_widget = item.widget()
                    if hasattr(track_widget, 'clip_moved'):
                        track_widget.clip_moved.connect(self.on_clip_moved)
        except Exception as e:
            print(f"Error connecting track signals: {e}")
    
    def apply_premiere_theme(self):
        """Apply Adobe Premiere Pro dark theme"""
        premiere_style = """
        /* Main Application */
        QMainWindow {
            background-color: #1e1e1e;
            color: #cccccc;
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 12px;
        }
        
        /* Central Widget */
        QWidget {
            background-color: #1e1e1e;
            color: #cccccc;
            border: none;
        }
        
        /* Menu Bar - Adobe Premiere Style */
        QMenuBar {
            background-color: #2d2d30;
            color: #cccccc;
            border: none;
            padding: 4px;
            font-weight: 500;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 6px 12px;
            margin: 0px 2px;
            border-radius: 3px;
        }
        
        QMenuBar::item:selected {
            background-color: #3f3f46;
            color: #ffffff;
        }
        
        QMenuBar::item:pressed {
            background-color: #007acc;
        }
        
        /* Menu Dropdowns */
        QMenu {
            background-color: #2d2d30;
            color: #cccccc;
            border: 1px solid #464647;
            padding: 4px;
        }
        
        QMenu::item {
            padding: 6px 30px 6px 20px;
            border-radius: 3px;
            margin: 1px;
        }
        
        QMenu::item:selected {
            background-color: #007acc;
            color: #ffffff;
        }
        
        QMenu::separator {
            height: 1px;
            background-color: #464647;
            margin: 4px 0px;
        }
        
        /* Status Bar */
        QStatusBar {
            background-color: #2d2d30;
            color: #cccccc;
            border-top: 1px solid #464647;
            font-size: 11px;
        }
        
        /* Splitters */
        QSplitter::handle {
            background-color: #464647;
            border: none;
        }
        
        QSplitter::handle:horizontal {
            width: 4px;
            margin: 0px 2px;
        }
        
        QSplitter::handle:vertical {
            height: 4px;
            margin: 2px 0px;
        }
        
        QSplitter::handle:hover {
            background-color: #007acc;
        }
        
        /* Panels and Group Boxes */
        QGroupBox {
            background-color: #252526;
            border: 1px solid #464647;
            border-radius: 4px;
            margin-top: 10px;
            font-weight: bold;
            color: #cccccc;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 8px 0 8px;
            color: #ffffff;
            background-color: #252526;
        }
        
        /* Buttons - Adobe Premiere Style */
        QPushButton {
            background-color: #0e639c;
            color: #ffffff;
            border: none;
            padding: 4px 12px;  /* More compact padding */
            border-radius: 3px;  /* Slightly smaller radius */
            font-weight: 500;
            min-height: 16px;    /* Reduced height */
            font-size: 11px;     /* Smaller font */
        }
        
        QPushButton:hover {
            background-color: #1177bb;
        }
        
        QPushButton:pressed {
            background-color: #005a9e;
        }
        
        QPushButton:disabled {
            background-color: #464647;
            color: #808080;
        }
        
        /* Secondary Buttons */
        QPushButton[class="secondary"] {
            background-color: #3c3c3c;
            color: #cccccc;
            border: 1px solid #5a5a5a;
        }
        
        QPushButton[class="secondary"]:hover {
            background-color: #4a4a4a;
            border-color: #007acc;
        }
        
        /* Sliders - Premiere Style */
        QSlider::groove:horizontal {
            background-color: #464647;
            height: 3px;  /* Thinner groove */
            border-radius: 2px;
        }
        
        QSlider::handle:horizontal {
            background-color: #007acc;
            border: none;
            width: 14px;  /* Smaller handle */
            height: 14px;
            border-radius: 7px;
            margin: -5px 0;  /* Adjusted margin */
        }
        
        QSlider::handle:horizontal:hover {
            background-color: #1177bb;
        }
        
        QSlider::handle:horizontal:pressed {
            background-color: #005a9e;
        }
        
        QSlider::sub-page:horizontal {
            background-color: #007acc;
            border-radius: 2px;
        }
        
        /* Labels */
        QLabel {
            color: #cccccc;
            background-color: transparent;
        }
        
        QLabel[class="title"] {
            color: #ffffff;
            font-weight: bold;
            font-size: 14px;
        }
        
        QLabel[class="panel-title"] {
            background-color: #2d2d30;
            color: #ffffff;
            padding: 8px;
            font-weight: bold;
            border-bottom: 1px solid #464647;
        }
        
        /* List Widgets - Project Panel Style */
        QListWidget {
            background-color: #252526;
            color: #cccccc;
            border: 1px solid #464647;
            alternate-background-color: #2a2a2b;
            selection-background-color: #007acc;
            selection-color: #ffffff;
            outline: none;
            border-radius: 4px;
        }
        
        QListWidget::item {
            padding: 6px;
            border-bottom: 1px solid #333333;
        }
        
        QListWidget::item:selected {
            background-color: #007acc;
            color: #ffffff;
        }
        
        QListWidget::item:hover {
            background-color: #3f3f46;
        }
        
        /* Tree Widget */
        QTreeWidget {
            background-color: #252526;
            color: #cccccc;
            border: 1px solid #464647;
            alternate-background-color: #2a2a2b;
            selection-background-color: #007acc;
            selection-color: #ffffff;
            outline: none;
            border-radius: 4px;
        }
        
        QTreeWidget::item {
            padding: 4px;
            border-bottom: 1px solid #333333;
        }
        
        QTreeWidget::item:selected {
            background-color: #007acc;
            color: #ffffff;
        }
        
        QTreeWidget::item:hover {
            background-color: #3f3f46;
        }
        
        QTreeWidget::branch:has-children:closed {
            image: url(none);
            border-image: none;
        }
        
        QTreeWidget::branch:has-children:open {
            image: url(none);
            border-image: none;
        }
        
        /* Tab Widget - Adobe Premiere Style */
        QTabWidget::pane {
            background-color: #1e1e1e;
            border: 1px solid #333333;
            border-top: none;
        }
        
        QTabWidget::tab-bar {
            alignment: left;
        }
        
        QTabBar {
            background-color: #252526;
            border: none;
        }
        
        QTabBar::tab {
            background-color: #3c3c3c;
            color: #b8b8b8;
            padding: 12px 20px 10px 20px;
            margin-right: 1px;
            margin-bottom: 0px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            border: 1px solid #555555;
            border-bottom: none;
            font-weight: 500;
            font-size: 11px;
            min-width: 100px;
        }
        
        QTabBar::tab:selected {
            background-color: #1e1e1e;
            color: #ffffff;
            border-color: #007acc;
            border-bottom: 2px solid #007acc;
            font-weight: bold;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #464646;
            color: #ffffff;
            border-color: #666666;
        }
        
        QTabBar::tab:pressed {
            background-color: #007acc;
            color: #ffffff;
        }
        
        /* Scroll Bars */
        QScrollBar:vertical {
            background-color: #2d2d30;
            width: 16px;
            border: none;
        }
        
        QScrollBar::handle:vertical {
            background-color: #464647;
            border-radius: 8px;
            min-height: 20px;
            margin: 2px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #5a5a5a;
        }
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        QScrollBar:horizontal {
            background-color: #2d2d30;
            height: 16px;
            border: none;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #464647;
            border-radius: 8px;
            min-width: 20px;
            margin: 2px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #5a5a5a;
        }
        
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        
        /* Text Inputs */
        QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
            background-color: #3c3c3c;
            color: #ffffff;
            border: 1px solid #5a5a5a;
            border-radius: 3px;
            padding: 6px;
            selection-background-color: #007acc;
        }
        
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: #007acc;
            background-color: #404040;
        }
        
        /* Combo Boxes */
        QComboBox {
            background-color: #3c3c3c;
            color: #ffffff;
            border: 1px solid #5a5a5a;
            border-radius: 3px;
            padding: 6px;
            min-width: 100px;
        }
        
        QComboBox:hover {
            border-color: #007acc;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        
        QComboBox::down-arrow {
            image: url(none);
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #cccccc;
            margin-right: 5px;
        }
        
        QComboBox QAbstractItemView {
            background-color: #2d2d30;
            color: #cccccc;
            border: 1px solid #464647;
            selection-background-color: #007acc;
        }
        
        /* Check Boxes */
        QCheckBox {
            color: #cccccc;
            spacing: 8px;
        }
        
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            background-color: #3c3c3c;
            border: 1px solid #5a5a5a;
            border-radius: 3px;
        }
        
        QCheckBox::indicator:checked {
            background-color: #007acc;
            border-color: #007acc;
        }
        
        QCheckBox::indicator:hover {
            border-color: #007acc;
        }
        
        /* Progress Bars */
        QProgressBar {
            background-color: #3c3c3c;
            color: #ffffff;
            border: 1px solid #5a5a5a;
            border-radius: 4px;
            text-align: center;
            padding: 2px;
        }
        
        QProgressBar::chunk {
            background-color: #007acc;
            border-radius: 3px;
            margin: 1px;
        }
        
        /* Tool Tips */
        QToolTip {
            background-color: #2d2d30;
            color: #ffffff;
            border: 1px solid #464647;
            padding: 6px;
            border-radius: 4px;
            font-size: 11px;
        }
        
        /* Dock Widgets */
        QDockWidget {
            background-color: #252526;
            color: #cccccc;
            titlebar-close-icon: url(none);
            titlebar-normal-icon: url(none);
        }
        
        QDockWidget::title {
            background-color: #2d2d30;
            color: #ffffff;
            padding: 8px;
            font-weight: bold;
            border-bottom: 1px solid #464647;
        }
        
        QDockWidget::close-button, QDockWidget::float-button {
            background-color: transparent;
            border: none;
            padding: 2px;
        }
        
        QDockWidget::close-button:hover, QDockWidget::float-button:hover {
            background-color: #464647;
        }
        """
        
        self.setStyleSheet(premiere_style)
    
    def create_premiere_tabbed_layout(self, central_widget):
        """Create layout with timeline at bottom, tabbed corners, and center preview"""
        # Initialize media browser first
        self.media_browser = MediaBrowserWidget()
        
        # Main vertical layout: top area + timeline
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Top area with corner tabs and center preview
        top_area = self.create_top_area_with_tabs()
        main_layout.addWidget(top_area, 1)  # Top half
        
        # Timeline taking full bottom half
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.setMinimumHeight(300)
        main_layout.addWidget(self.timeline_widget, 1)  # Bottom half
    
    
    def create_top_area_with_tabs(self):
        """Create top area with corner tabs and center preview"""
        # Use QSplitter for movable panels
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(8)
        
        # Left corner tabs (Graphics/Project)
        left_tabs = self.create_left_corner_tabs()
        main_splitter.addWidget(left_tabs)
        
        # Center preview
        self.preview_widget = PreviewWidget()
        self.preview_widget.setMinimumSize(600, 400)
        main_splitter.addWidget(self.preview_widget)
        
        # Right corner tabs (Audio)
        right_tabs = self.create_right_corner_tabs()
        main_splitter.addWidget(right_tabs)
        
        # Set proportions: left 25%, center 50%, right 25%
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)
        main_splitter.setStretchFactor(2, 1)
        
        # Make splitter handle visible and responsive
        main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #464647;
                border: 1px solid #464647;
                margin: 1px;
            }
            QSplitter::handle:hover {
                background-color: #007acc;
            }
            QSplitter::handle:horizontal {
                width: 8px;
            }
        """)
        
        return main_splitter
    
    def create_left_corner_tabs(self):
        """Create left corner tabbed panel with Graphics and Project"""
        left_tabs = QTabWidget()
        left_tabs.setMinimumWidth(300)
        left_tabs.setMaximumWidth(400)
        
        # Graphics tab (Text/Titles)
        graphics_widget = QWidget()
        graphics_layout = QVBoxLayout(graphics_widget)
        
        # Project browser
        project_scroll = QScrollArea()
        project_scroll.setWidget(self.media_browser)
        project_scroll.setWidgetResizable(True)
        graphics_layout.addWidget(project_scroll)
        
        # Text controls
        text_controls = self.create_text_controls()
        graphics_layout.addWidget(text_controls)
        
        left_tabs.addTab(graphics_widget, "Graphics")
        
        # Project tab
        project_widget = QWidget()
        project_layout = QVBoxLayout(project_widget)
        
        # Effects panel
        effects_widget = self.create_effects_panel()
        project_layout.addWidget(effects_widget)
        
        left_tabs.addTab(project_widget, "Effects")
        
        return left_tabs
    
    def create_right_corner_tabs(self):
        """Create right corner tabbed panel with Audio controls"""
        right_tabs = QTabWidget()
        right_tabs.setMinimumWidth(300)
        right_tabs.setMaximumWidth(400)
        
        # Audio tab
        audio_widget = QWidget()
        audio_layout = QVBoxLayout(audio_widget)
        
        # Audio controls
        audio_controls = self.create_audio_controls()
        audio_layout.addWidget(audio_controls)
        
        # Color grading controls
        color_controls = self.create_color_grading_controls()
        audio_layout.addWidget(color_controls)
        
        # Chroma key controls
        chroma_controls = self.create_chroma_key_controls()
        audio_layout.addWidget(chroma_controls)
        
        audio_layout.addStretch()
        right_tabs.addTab(audio_widget, "Audio")
        
        # Effect Controls tab
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        properties_panel = self.create_properties_panel()
        controls_layout.addWidget(properties_panel)
        right_tabs.addTab(controls_widget, "Controls")
        
        return right_tabs
    
    def create_center_panel(self):
        """Create center panel with preview and timeline"""
        center_splitter = QSplitter(Qt.Orientation.Vertical)

        # Preview
        self.preview_widget = PreviewWidget()
        center_splitter.addWidget(self.preview_widget)

        # Timeline
        self.timeline_widget = TimelineWidget()
        center_splitter.addWidget(self.timeline_widget)

        # Set proportions between preview and timeline
        center_splitter.setStretchFactor(0, 3)
        center_splitter.setStretchFactor(1, 1)

        return center_splitter
    
    def create_right_panel(self):
        """Create right panel with effect controls and audio controls"""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel_layout = QVBoxLayout(panel)

        # Audio Controls
        audio_group = QGroupBox("Audio Controls")
        audio_layout = QVBoxLayout(audio_group)
        audio_widget = self.create_audio_panel()
        audio_layout.addWidget(audio_widget)
        panel_layout.addWidget(audio_group)

        return panel
    
    def create_project_panel(self):
        """Create Project panel - now unused since media browser is in left tabs"""
        # This method is now deprecated as we use the unified left tabs
        return QWidget()
    
    def create_monitor_panel(self):
        """Create Monitor panel with Source/Program tabs (like Adobe)"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create tabbed widget for monitors
        monitor_tabs = QTabWidget()
        monitor_tabs.setTabPosition(QTabWidget.TabPosition.North)
        
        # Source Monitor tab
        source_widget = QWidget()
        source_layout = QVBoxLayout(source_widget)
        source_label = QLabel("Source Monitor")
        source_label.setStyleSheet("padding: 10px; font-weight: bold; text-align: center;")
        source_layout.addWidget(source_label)
        source_layout.addStretch()
        monitor_tabs.addTab(source_widget, "Source")
        
        # Program Monitor tab (our main preview)
        self.preview_widget = PreviewWidget()
        monitor_tabs.addTab(self.preview_widget, "Program")
        
        # Set Program as default
        monitor_tabs.setCurrentIndex(1)
        
        layout.addWidget(monitor_tabs)
        return panel
    
    def create_timeline_panel(self):
        """Create Timeline panel - Enhanced for better visibility"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)  # Add padding for better visibility
        layout.setSpacing(5)
        
        # Panel title - smaller for thinner timeline
        title = QLabel("Timeline")
        title.setProperty("class", "panel-title")
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                background-color: #2d2d30;
                border: 1px solid #464647;
                padding: 4px;
                margin-bottom: 2px;
            }
        """)
        layout.addWidget(title)
        
        # Timeline widget - thinner version
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.setMinimumHeight(140)  # Reduced height for thinner timeline
        from PyQt6.QtWidgets import QSizePolicy
        self.timeline_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding  # Allow timeline to expand vertically
        )
        layout.addWidget(self.timeline_widget)
        
        # Movable placeholder
        placeholder_label = QLabel("Movable Panel - Customize!")
        layout.addWidget(placeholder_label)
        return panel
    
    
    def create_effect_controls_panel(self):
        """Create Effect Controls panel - now unused since it's in left tabs"""
        # This method is now deprecated as we use the unified left tabs
        return QWidget()
    
    def create_audio_panel(self):
        """Create Audio panel with controls"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Audio controls
        audio_controls = self.create_audio_controls()
        layout.addWidget(audio_controls)
        
        # Essential Sound section
        essential_label = QLabel("Essential Sound")
        essential_label.setStyleSheet("padding: 10px; font-weight: bold; color: #cccccc;")
        layout.addWidget(essential_label)
        
        # Placeholder for additional audio features
        placeholder = QLabel("Additional audio features coming soon...")
        placeholder.setStyleSheet("padding: 10px; color: #888888; font-style: italic;")
        layout.addWidget(placeholder)
        
        layout.addStretch()
        return panel


    def create_menu_bar(self):
        """Create Adobe Premiere-style menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        new_action = QAction('New Project', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction('Open Project', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_project_manager)
        file_menu.addAction(open_action)
        
        import_action = QAction('Import Media...', self)
        import_action.setShortcut('Ctrl+I')
        import_action.triggered.connect(self.load_video)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        export_action = QAction('Export...', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_video)
        file_menu.addAction(export_action)
        
        # Edit menu
        edit_menu = menubar.addMenu('Edit')
        edit_menu.addAction('Undo')
        edit_menu.addAction('Redo')
        edit_menu.addSeparator()
        edit_menu.addAction('Cut')
        edit_menu.addAction('Copy')
        edit_menu.addAction('Paste')
        
        # Window menu
        window_menu = menubar.addMenu('Window')
        # Window menu items can be added here as needed
        
        
    def create_effects_panel(self):
        """Create effects panel similar to Premiere's Effects panel - Thinner version"""
        panel = QWidget()
        panel.setMinimumWidth(150)  # Further reduced minimum width
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)  # Minimal padding
        layout.setSpacing(2)  # Minimal spacing
        
        # Panel title - Thinner Adobe Premiere style
        title = QLabel("Effects")
        title.setProperty("class", "panel-title")
        title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))  # Smaller font
        title.setStyleSheet("padding: 2px; margin: 1px;")
        layout.addWidget(title)
        
        # Effects list
        self.effects_list = QListWidget()
        self.effects_list.setStyleSheet("""
            QListWidget {
                background-color: #3c3c3c;
                color: white;
                border: none;
                font-size: 10px;
            }
            QListWidget::item {
                padding: 2px;
                height: 16px;
            }
            QListWidget::item:selected {
                background-color: #094771;
            }
        """)

        # Fetch available effects dynamically
        available_effects = self.video_processor.list_available_effects()
        for effect_name in available_effects:
            self.effects_list.addItem(QListWidgetItem(effect_name.capitalize()))

        layout.addWidget(self.effects_list)

        # Effects apply button - thinner
        apply_effect_button = QPushButton("Apply Effect")
        apply_effect_button.setMaximumHeight(24)  # Compact button
        apply_effect_button.setStyleSheet("font-size: 10px; padding: 2px;")
        apply_effect_button.clicked.connect(self.apply_selected_effect)
        layout.addWidget(apply_effect_button)

        # Transitions list
        self.transitions_list = QListWidget()
        self.transitions_list.setStyleSheet("""
            QListWidget {
                background-color: #3c3c3c;
                color: white;
                border: none;
            }
            QListWidget::item:selected {
                background-color: #094771;
            }
        """)

        # Fetch available transitions dynamically
        available_transitions = self.video_processor.list_available_transitions()
        for transition_name in available_transitions:
            self.transitions_list.addItem(QListWidgetItem(transition_name.replace('_', ' ').capitalize()))

        layout.addWidget(self.transitions_list)

        # Transitions apply button - thinner
        apply_transition_button = QPushButton("Apply Transition")
        apply_transition_button.setMaximumHeight(24)  # Compact button
        apply_transition_button.setStyleSheet("font-size: 10px; padding: 2px;")
        apply_transition_button.clicked.connect(self.apply_selected_transition)
        layout.addWidget(apply_transition_button)
        return panel
    
    def create_transitions_panel(self):
        """Create transitions panel"""
        panel = QWidget()
        panel.setMinimumWidth(150)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Panel title
        title = QLabel("Transitions")
        title.setProperty("class", "panel-title")
        title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        title.setStyleSheet("padding: 2px; margin: 1px;")
        layout.addWidget(title)
        
        # Transitions list
        self.transitions_list = QListWidget()
        self.transitions_list.setStyleSheet("""
            QListWidget {
                background-color: #3c3c3c;
                color: white;
                border: none;
                font-size: 10px;
            }
            QListWidget::item {
                padding: 2px;
                height: 16px;
            }
            QListWidget::item:selected {
                background-color: #094771;
            }
        """)
        
        # Fetch available transitions dynamically
        available_transitions = self.video_processor.list_available_transitions()
        for transition_name in available_transitions:
            self.transitions_list.addItem(QListWidgetItem(transition_name.replace('_', ' ').capitalize()))
            
        layout.addWidget(self.transitions_list)
        
        # Transitions apply button
        apply_transition_button = QPushButton("Apply Transition")
        apply_transition_button.setMaximumHeight(24)
        apply_transition_button.setStyleSheet("font-size: 10px; padding: 2px;")
        apply_transition_button.clicked.connect(self.apply_selected_transition)
        layout.addWidget(apply_transition_button)
        
        return panel
        
    def create_properties_panel(self):
        """Create properties panel similar to Premiere's Effect Controls"""
        panel = QWidget()
        panel.setMinimumWidth(300)
        layout = QVBoxLayout(panel)
        
        # Panel title - Adobe Premiere style
        title = QLabel("Effect Controls")
        title.setProperty("class", "panel-title")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Scroll area for controls
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #3c3c3c;
                border: none;
            }
        """)
        
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        
        # Color Grading controls
        color_group = self.create_color_grading_controls()
        controls_layout.addWidget(color_group)
        
        # Audio controls
        audio_group = self.create_audio_controls()
        controls_layout.addWidget(audio_group)
        
        # Chroma Key controls
        chroma_group = self.create_chroma_key_controls()
        controls_layout.addWidget(chroma_group)
        
        # Text controls
        text_group = self.create_text_controls()
        controls_layout.addWidget(text_group)
        
        controls_layout.addStretch()
        scroll.setWidget(controls_widget)
        layout.addWidget(scroll)
        
        return panel
    
    def on_timeline_time_changed(self, time: float):
        """Handle timeline playhead changes"""
        self.status_bar.showMessage(f"Time: {self.format_time(time)}")
        
    def on_timeline_clip_selected(self, clip_id: str):
        """Handle clip selection in timeline"""
        self.status_bar.showMessage(f"Selected clip: {clip_id}")
    
    def on_preview_time_changed(self, time: float):
        """Handle preview time changes"""
        # Sync timeline with preview time
        self.timeline_widget.set_playhead_time(time)
        
    def on_preview_frame_changed(self, time: float, frame):
        """Handle preview frame changes"""
        # This could be used for real-time effects preview
        pass
    
    def on_media_selected(self, file_path: str):
        """Handle media selection in browser"""
        self.status_bar.showMessage(f"Selected: {os.path.basename(file_path)}")
        
    def on_media_double_clicked(self, file_path: str):
        """Handle media double-click (load into timeline/preview)"""
        self.load_media_file(file_path)
        
    def import_media(self):
        """Import media files using the enhanced browser"""
        # This will be handled by the media browser widget
        pass
        
    def load_media_file(self, file_path: str):
        """Load a specific media file with proper error handling"""
        # Prevent recursive loading
        if self._loading_media:
            return
            
        if not file_path or not os.path.exists(file_path):
            self.status_bar.showMessage("Invalid file path")
            return
            
        # Set loading flag
        self._loading_media = True
            
        try:
            # Check if file is an image or video
            file_ext = os.path.splitext(file_path)[1].lower()
            image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff']
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
            
            if file_ext in image_extensions:
                # Handle image files differently
                self.load_image_file(file_path)
                return
                
            if file_ext not in video_extensions:
                self.status_bar.showMessage(f"Unsupported file format: {file_ext}")
                return
            
            # Load video
            success = self.video_processor.load_video(file_path)
            if success and self.video_processor.current_clip:
                self.original_clip = self.video_processor.current_clip
                
                # Add clip to timeline widget
                clip_name = os.path.basename(file_path)
                duration = self.video_processor.current_clip.duration
                
                # Only add to timeline if we have valid duration
                if duration > 0:
                    self.current_clip_id = self.timeline_widget.add_clip_to_track(0, clip_name, 0.0, duration)
                
                # Set video in preview widget (with error handling)
                try:
                    self.preview_widget.set_video_clip(self.video_processor.current_clip)
                except Exception as e:
                    print(f"Error setting preview clip: {e}")
                
                # Load audio for processing (with error handling)
                try:
                    if hasattr(self.video_processor.current_clip, 'audio') and self.video_processor.current_clip.audio:
                        self.audio_processor.load_audio_from_clip(self.video_processor.current_clip)
                        self.update_waveform_display()
                except Exception as e:
                    print(f"Error loading audio: {e}")
                
                self.status_bar.showMessage(f"Loaded: {clip_name}")
            else:
                self.status_bar.showMessage("Failed to load video file")
                
        except Exception as e:
            print(f"Error loading media file {file_path}: {e}")
            self.status_bar.showMessage(f"Error loading file: {str(e)}")
        finally:
            # Always reset loading flag
            self._loading_media = False
    
    def load_image_file(self, file_path: str):
        """Load an image file as a video clip"""
        try:
            from moviepy import ImageClip
            # Create a 5-second image clip
            image_clip = ImageClip(file_path, duration=5.0)
            
            # Store as current clip
            self.video_processor.current_clip = image_clip
            self.original_clip = image_clip
            
            # Add to timeline
            clip_name = os.path.basename(file_path)
            self.current_clip_id = self.timeline_widget.add_clip_to_track(0, clip_name, 0.0, 5.0)
            
            # Set in preview
            self.preview_widget.set_video_clip(image_clip)
            
            self.status_bar.showMessage(f"Loaded image: {clip_name}")
            
        except Exception as e:
            print(f"Error loading image: {e}")
            self.status_bar.showMessage(f"Error loading image: {str(e)}")
        
    def format_time(self, seconds: float) -> str:
        """Format time as MM:SS.ff"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        frames = int((seconds % 1) * 30)
        return f"{minutes:02d}:{secs:02d}.{frames:02d}"
    
    def update_waveform_display(self):
        """Safely update waveform display"""
        try:
            if hasattr(self, 'waveform_widget') and self.waveform_widget:
                # Update waveform if widget exists
                self.waveform_widget.update_waveform()
        except Exception as e:
            print(f"Error updating waveform: {e}")
    
    def create_color_grading_controls(self):
        """Create color grading control group"""
        group = QGroupBox("Color Grading")
        group.setStyleSheet("QGroupBox { font-size: 11px; font-weight: bold; padding-top: 8px; }")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)  # Tighter margins
        layout.setSpacing(4)  # Reduced spacing
        
        # Hue slider
        hue_layout = QHBoxLayout()
        hue_layout.addWidget(QLabel("Hue:"))
        self.hue_slider = QSlider(Qt.Orientation.Horizontal)
        self.hue_slider.setRange(-180, 180)
        self.hue_slider.setValue(0)
        self.hue_slider.valueChanged.connect(self.apply_color_grading)
        self.hue_value_label = QLabel("0")
        hue_layout.addWidget(self.hue_slider)
        hue_layout.addWidget(self.hue_value_label)
        layout.addLayout(hue_layout)
        
        # Saturation slider
        sat_layout = QHBoxLayout()
        sat_layout.addWidget(QLabel("Saturation:"))
        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setRange(0, 200)
        self.saturation_slider.setValue(100)
        self.saturation_slider.valueChanged.connect(self.apply_color_grading)
        self.sat_value_label = QLabel("1.0")
        sat_layout.addWidget(self.saturation_slider)
        sat_layout.addWidget(self.sat_value_label)
        layout.addLayout(sat_layout)
        
        # Luminance slider
        lum_layout = QHBoxLayout()
        lum_layout.addWidget(QLabel("Luminance:"))
        self.luminance_slider = QSlider(Qt.Orientation.Horizontal)
        self.luminance_slider.setRange(0, 200)
        self.luminance_slider.setValue(100)
        self.luminance_slider.valueChanged.connect(self.apply_color_grading)
        self.lum_value_label = QLabel("1.0")
        lum_layout.addWidget(self.luminance_slider)
        lum_layout.addWidget(self.lum_value_label)
        layout.addLayout(lum_layout)
        
        # Reset button
        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self.reset_color_grading)
        layout.addWidget(reset_button)
        
        return group
    
    def create_audio_controls(self):
        """Create audio control group"""
        group = QGroupBox("Audio Effects")
        group.setStyleSheet("QGroupBox { font-size: 11px; font-weight: bold; padding-top: 8px; }")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)  # Tighter margins
        layout.setSpacing(4)  # Reduced spacing
        
        # Volume slider
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Volume:"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 200)
        self.volume_slider.setValue(100)
        self.volume_slider.valueChanged.connect(self.apply_audio_effects)
        self.volume_value_label = QLabel("1.0")
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_value_label)
        layout.addLayout(volume_layout)
        
        # Echo effect
        echo_button = QPushButton("Apply Echo")
        echo_button.clicked.connect(lambda: self.apply_audio_effect("echo", delay=0.5, decay=0.3))
        layout.addWidget(echo_button)
        
        # Normalize effect
        normalize_button = QPushButton("Normalize Audio")
        normalize_button.clicked.connect(lambda: self.apply_audio_effect("normalize"))
        layout.addWidget(normalize_button)
        
        return group
    
    def create_chroma_key_controls(self):
        """Create chroma key control group"""
        group = QGroupBox("Chroma Key")
        group.setStyleSheet("QGroupBox { font-size: 11px; font-weight: bold; padding-top: 8px; }")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)  # Tighter margins
        layout.setSpacing(4)  # Reduced spacing
        
        # Apply chroma effect
        apply_chroma_button = QPushButton("Apply Chroma Key")
        apply_chroma_button.clicked.connect(self.apply_chroma_key)
        layout.addWidget(apply_chroma_button)
        
        # Load background button
        load_bg_button = QPushButton("Load Background")
        load_bg_button.clicked.connect(self.load_background_image)
        layout.addWidget(load_bg_button)
        
        # Tolerance slider
        tolerance_layout = QHBoxLayout()
        tolerance_layout.addWidget(QLabel("Tolerance:"))
        self.tolerance_slider = QSlider(Qt.Orientation.Horizontal)
        self.tolerance_slider.setRange(0, 100)
        self.tolerance_slider.setValue(40)
        tolerance_layout.addWidget(self.tolerance_slider)
        layout.addLayout(tolerance_layout)
        
        return group
    
    def create_text_controls(self):
        """Create text control group"""
        group = QGroupBox("Text Overlays")
        group.setStyleSheet("QGroupBox { font-size: 11px; font-weight: bold; padding-top: 8px; }")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)  # Tighter margins
        layout.setSpacing(4)  # Reduced spacing
        
        self.add_text_button = QPushButton("Add Text Overlay")
        self.add_text_button.clicked.connect(self.add_text_overlay)
        layout.addWidget(self.add_text_button)
        
        # Template selection
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("Template:"))
        self.template_combo = QComboBox()
        for template_name in self.title_system.list_templates():
            self.template_combo.addItem(template_name)
        template_layout.addWidget(self.template_combo)
        layout.addLayout(template_layout)
        
        return group
        color_layout.addLayout(hue_layout)
        
        # Saturation slider
        sat_layout = QHBoxLayout()
        sat_layout.addWidget(QLabel("Saturation:"))
        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setRange(0, 200)
        self.saturation_slider.setValue(100)
        self.saturation_slider.valueChanged.connect(self.apply_color_grading)
        self.sat_value_label = QLabel("1.0")
        sat_layout.addWidget(self.saturation_slider)
        sat_layout.addWidget(self.sat_value_label)
        color_layout.addLayout(sat_layout)
        
        # Luminance slider
        lum_layout = QHBoxLayout()
        lum_layout.addWidget(QLabel("Luminance:"))
        self.luminance_slider = QSlider(Qt.Orientation.Horizontal)
        self.luminance_slider.setRange(0, 200)
        self.luminance_slider.setValue(100)
        self.luminance_slider.valueChanged.connect(self.apply_color_grading)
        self.lum_value_label = QLabel("1.0")
        lum_layout.addWidget(self.luminance_slider)
        lum_layout.addWidget(self.lum_value_label)
        color_layout.addLayout(lum_layout)
        
        # Reset button
        reset_button = QPushButton("Reset Color Grading")
        reset_button.clicked.connect(self.reset_color_grading)
        color_layout.addWidget(reset_button)
        
        controls_layout.addWidget(color_group)
        
        # Audio controls
        audio_group = QGroupBox("Audio Effects")
        audio_layout = QVBoxLayout(audio_group)

        # Volume slider
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Volume:"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 200)
        self.volume_slider.setValue(100)
        self.volume_slider.valueChanged.connect(self.apply_audio_effects)
        self.volume_value_label = QLabel("1.0")
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_value_label)
        audio_layout.addLayout(volume_layout)

        # Echo effect
        echo_button = QPushButton("Apply Echo")
        echo_button.clicked.connect(lambda: self.apply_audio_effect("echo", delay=0.5, decay=0.3))
        audio_layout.addWidget(echo_button)

        # Normalize effect
        normalize_button = QPushButton("Normalize Audio")
        normalize_button.clicked.connect(lambda: self.apply_audio_effect("normalize"))
        audio_layout.addWidget(normalize_button)

        controls_layout.addWidget(audio_group)

        # Waveform display
        self.waveform_widget = WaveformWidget()
        controls_layout.addWidget(self.waveform_widget)
        
        # Keyframe controls
        keyframe_group = QGroupBox("Keyframing")
        keyframe_layout = QVBoxLayout(keyframe_group)

        # Add keyframe button
        add_keyframe_button = QPushButton("Add Keyframe")
        add_keyframe_button.clicked.connect(self.add_keyframe)
        keyframe_layout.addWidget(add_keyframe_button)

        # Remove keyframe button
        remove_keyframe_button = QPushButton("Remove Keyframe")
        remove_keyframe_button.clicked.connect(self.remove_keyframe)
        keyframe_layout.addWidget(remove_keyframe_button)

        controls_layout.addWidget(keyframe_group)

        # Add stretch to push controls to top
        # Text overlay controls
        text_group = QGroupBox("Text Overlays")
        text_layout = QVBoxLayout(text_group)

        self.add_text_button = QPushButton("Add Text Overlay")
        self.add_text_button.clicked.connect(self.add_text_overlay)
        text_layout.addWidget(self.add_text_button)

        self.template_combo = QTabWidget()
        for template_name in self.title_system.list_templates():
            template_tab = QWidget()
            template_layout = QVBoxLayout(template_tab)
            template_layout.addWidget(QLabel(f"Template: {template_name}"))
            self.template_combo.addTab(template_tab, template_name)
        text_layout.addWidget(self.template_combo)

        controls_layout.addWidget(text_group)

        controls_layout.addStretch()
        
        # Preview area (placeholder)
        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        
        # Store original clip for reset purposes
        self.original_clip = None
    
    def load_video(self):
        """Load a video file (legacy method - now delegates to media browser)"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Video File", "", 
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv);;All Files (*)"
        )
        
        if file_path:
            # Add to media browser first
            self.media_browser.add_media_file(file_path)
            # Then load it
            self.load_media_file(file_path)
    
    def export_video(self):
        """Export the current video"""
        if not self.video_processor.current_clip:
            self.status_bar.showMessage("No video loaded to export")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Video File", "", 
            "MP4 Files (*.mp4);;AVI Files (*.avi);;All Files (*)"
        )
        
        if file_path:
            # Add current clip to timeline for export
            self.video_processor.timeline_clips = [{
                'clip': self.video_processor.current_clip,
                'start_time': 0,
                'duration': self.video_processor.current_clip.duration
            }]
            
            success = self.video_processor.export_video(file_path)
            if success:
                self.status_bar.showMessage(f"Exported: {file_path}")
            else:
                self.status_bar.showMessage("Failed to export video")
    
    def apply_color_grading(self):
        """Apply color grading based on slider values"""
        if not self.original_clip:
            return
            
        # Get slider values
        hue_shift = self.hue_slider.value()
        saturation_factor = self.saturation_slider.value() / 100.0
        luminance_factor = self.luminance_slider.value() / 100.0
        
        # Update value labels
        self.hue_value_label.setText(str(hue_shift))
        self.sat_value_label.setText(f"{saturation_factor:.1f}")
        self.lum_value_label.setText(f"{luminance_factor:.1f}")
        
        # Apply color grading
        try:
            clip = self.original_clip
            
            if hue_shift != 0:
                clip = self.color_grading.adjust_hue(clip, hue_shift)
            
            if saturation_factor != 1.0:
                clip = self.color_grading.adjust_saturation(clip, saturation_factor)
            
            if luminance_factor != 1.0:
                clip = self.color_grading.adjust_luminance(clip, luminance_factor)
            
            self.video_processor.current_clip = clip
            self.status_bar.showMessage("Color grading applied")
            
        except Exception as e:
            self.status_bar.showMessage(f"Error applying color grading: {str(e)}")
    
    def reset_color_grading(self):
        """Reset all color grading to default values"""
        self.hue_slider.setValue(0)
        self.saturation_slider.setValue(100)
        self.luminance_slider.setValue(100)
        
        if self.original_clip:
            self.video_processor.current_clip = self.original_clip
            self.status_bar.showMessage("Color grading reset")
    
    def apply_audio_effects(self):
        """Apply audio effects based on slider values"""
        if not self.original_clip:
            return
            
        # Get volume value
        volume_factor = self.volume_slider.value() / 100.0
        self.volume_value_label.setText(f"{volume_factor:.1f}")
        
        # Apply volume adjustment
        try:
            clip = self.original_clip
            if volume_factor != 1.0:
                clip = self.audio_effects.apply_effect(clip, "volume", volume_factor=volume_factor)
            
            self.video_processor.current_clip = clip
            self.update_waveform_display()
            self.status_bar.showMessage("Audio effects applied")
            
        except Exception as e:
            self.status_bar.showMessage(f"Error applying audio effects: {str(e)}")
    
    def apply_audio_effect(self, effect_name: str, **kwargs):
        """Apply a specific audio effect"""
        if not self.video_processor.current_clip:
            self.status_bar.showMessage("No video loaded")
            return
            
        try:
            clip = self.audio_effects.apply_effect(
                self.video_processor.current_clip, effect_name, **kwargs
            )
            self.video_processor.current_clip = clip
            self.update_waveform_display()
            self.status_bar.showMessage(f"Applied {effect_name} effect")
            
        except Exception as e:
            self.status_bar.showMessage(f"Error applying {effect_name}: {str(e)}")
    
    def update_waveform_display(self):
        """Update the waveform display with current audio"""
        if hasattr(self, 'waveform_widget') and self.video_processor.current_clip:
            try:
                audio_array, sample_rate = self.audio_effects.get_waveform_data(
                    self.video_processor.current_clip
                )
                if audio_array is not None:
                    # Note: waveform display is now in timeline widget
                    pass
                else:
                    pass
            except Exception as e:
                self.status_bar.showMessage(f"Error updating waveform: {str(e)}")
    

    def add_keyframe(self):
        """Add keyframe at current time for selected property"""
        if not self.current_clip_id:
            self.status_bar.showMessage("No clip selected for keyframing")
            return
            
        # For demo purposes, add position keyframe at current time
        current_time = 2.0  # This should come from a timeline scrubber
        position_value = (100, 50)  # This should come from property controls
        
        # Note: Keyframing integration with new timeline widget would go here
        self.status_bar.showMessage(f"Added position keyframe at {current_time}s")
    
    def remove_keyframe(self):
        """Remove keyframe at current time"""
        if not self.current_clip_id:
            self.status_bar.showMessage("No clip selected for keyframing")
            return
            
        current_time = 2.0  # This should come from a timeline scrubber
        
        # Note: Keyframing integration with new timeline widget would go here
        self.status_bar.showMessage(f"Removed keyframe at {current_time}s")
    
    def add_text_overlay(self):
        """Add text overlay to current video"""
        if not self.video_processor.current_clip:
            self.status_bar.showMessage("No video loaded")
            return
        
        # Get selected template
        selected_template = self.template_combo.currentText()
        if not selected_template:
            selected_template = 'main_title'
        
        # Create text overlay with sample text
        text_overlay = self.title_system.create_text_overlay(
            text="Sample Text Overlay",
            template_name=selected_template,
            duration=5.0,
            position=('center', 'center')
        )
        
        try:
            # Composite text with current video
            from moviepy import CompositeVideoClip
            
            # Resize text clip to match video dimensions if needed
            text_clip = text_overlay['clip']
            if hasattr(self.video_processor.current_clip, 'size'):
                video_size = self.video_processor.current_clip.size
                text_clip = text_clip.with_duration(min(text_clip.duration, self.video_processor.current_clip.duration))
            
            # Create composite
            composite_clip = CompositeVideoClip([
                self.video_processor.current_clip,
                text_clip
            ])
            
            self.video_processor.current_clip = composite_clip
            self.status_bar.showMessage(f"Added text overlay using template: {selected_template}")
            
        except Exception as e:
            self.status_bar.showMessage(f"Error adding text overlay: {str(e)}")
    
    def preview_with_animation(self):
        """Preview video with keyframe animations applied"""
        if not self.current_clip_id:
            self.status_bar.showMessage("No clip loaded")
            return
            
        current_time = 2.0  # This should come from timeline scrubber
        
        try:
            # Render frame with animations (not currently supported here)
            # animated_frame = self.timeline_widget.render_frame_at_time(current_time)
            
            # Fallback to regular preview
            self.video_processor.current_clip.preview()
            self.status_bar.showMessage("Previewing")
            
        except Exception as e:
            self.status_bar.showMessage(f"Error previewing animation: {str(e)}")
    
    def play_video(self):
        """Simple play action"""
        if self.video_processor.current_clip:
            try:
                # Check if we have keyframes and should preview with animation
                # Preview currently does not support keyframe animations
                self.video_processor.current_clip.preview()
            except Exception as e:
                self.status_bar.showMessage(f"Error playing video: {str(e)}")
    
    def load_background_image(self):
        """Load background image for chroma key"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Background Image", "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff);;All Files (*)"
        )
        
        if file_path:
            success = self.chroma_key_manager.set_background_image(file_path)
            if success:
                self.status_bar.showMessage(f"Background loaded: {file_path}")
            else:
                self.status_bar.showMessage("Failed to load background image")
    
    def apply_chroma_key(self):
        """Apply chroma key effect to current video"""
        if not self.video_processor.current_clip:
            self.status_bar.showMessage("No video loaded for chroma key")
            return
            
        try:
            # Get tolerance value from slider
            tolerance = self.tolerance_slider.value()
            
            # Apply chroma key with default green screen settings
            processed_clip = self.chroma_key_manager.apply_chroma_key(
                self.video_processor.current_clip,
                key_color=(0, 255, 0),  # Green screen
                tolerance=tolerance,
                edge_softness=5,
                spill_suppression=0.5
            )
            
            # Update current clip
            self.video_processor.current_clip = processed_clip
            self.status_bar.showMessage("Chroma key applied successfully")
            
        except Exception as e:
            self.status_bar.showMessage(f"Error applying chroma key: {str(e)}")
    
    def preview_chroma_mask(self):
        """Preview the chroma key mask"""
        if not self.video_processor.current_clip:
            self.status_bar.showMessage("No video loaded")
            return
            
        try:
            # Get mask preview at time 0
            mask = self.chroma_key_manager.preview_mask(self.video_processor.current_clip, 0.0)
            
            # Display mask (this would be shown in a preview window in full implementation)
            self.status_bar.showMessage("Mask preview generated")
            
        except Exception as e:
            self.status_bar.showMessage(f"Error generating mask preview: {str(e)}")

    def new_project(self):
        """Create a new project"""
        dialog = ProjectManagerDialog(self)
        dialog.project_selected.connect(self.load_project)
        dialog.exec()

    def open_project_manager(self):
        """Open project manager dialog"""
        dialog = ProjectManagerDialog(self)
        dialog.project_selected.connect(self.load_project)
        dialog.exec()

    def load_project(self, project_id: str):
        """Load a project by ID"""
        self.current_project_id = project_id
        # Load project-specific data here, like timeline, clips, etc.
        self.status_bar.showMessage(f"Project {project_id} loaded")
        
        # Update window title
        # In a real implementation, you'd load the project name from workspace
        self.setWindowTitle(f"PyVideoEditor - Project {project_id[:8]}...")
    
    def show_startup_project_manager(self):
        """Show project manager on startup if no project is loaded"""
        if not self.current_project_id:
            self.open_project_manager()
    
    def on_media_selected(self, file_path: str):
        """Handle media selection from media browser"""
        # Update preview with selected media
        self.load_media_file(file_path)
        
    def on_media_double_clicked(self, file_path: str):
        """Handle media double-click - add to timeline"""
        try:
            # Delegate to timeline widget for adding to timeline
            self.timeline_widget.add_media_file(file_path)
            self.status_bar.showMessage(f"Added {os.path.basename(file_path)} to timeline")
        except Exception as e:
            self.status_bar.showMessage(f"Error adding to timeline: {str(e)}")
    
    def load_media_file(self, file_path: str):
        """Load a media file for preview"""
        if self.video_processor.load_video(file_path):
            self.original_clip = self.video_processor.current_clip
            
            # Update preview with the loaded video clip
            self.preview_widget.set_video_clip(self.video_processor.current_clip)
                
            self.status_bar.showMessage(f"Loaded: {os.path.basename(file_path)}")
        else:
            self.status_bar.showMessage(f"Failed to load: {os.path.basename(file_path)}")
    
    def on_timeline_time_changed(self, time: float):
        """Handle timeline time change"""
        # Prevent recursive time sync
        if self._syncing_time:
            return
            
        self._syncing_time = True
        try:
            # Update preview to show frame at this time
            if hasattr(self.preview_widget, 'seek_to_time'):
                self.preview_widget.seek_to_time(time)
        finally:
            self._syncing_time = False
    
    def on_timeline_clip_selected(self, clip_id: str):
        """Handle timeline clip selection"""
        self.current_clip_id = clip_id
        # Update properties panel with clip properties
        self.status_bar.showMessage(f"Selected clip: {clip_id}")
        
        # Load the selected clip's media file for individual preview if needed
        if hasattr(self, 'timeline_clips') and clip_id in self.timeline_clips:
            file_path = self.timeline_clips[clip_id]
            # Could load individual clip for effects preview here
    
    def on_clip_moved(self, clip_id: str, new_time: float, track_id: int):
        """Handle clip movement on timeline"""
        # Update the timeline composition when clips are moved
        self.update_timeline_composition()
        self.status_bar.showMessage(f"Moved clip {clip_id} to {new_time:.2f}s")
    
    def on_media_added_to_timeline(self, clip_id: str, file_path: str):
        """Handle media added to timeline via drag and drop"""
        # Store the file path for this clip
        self.timeline_clips[clip_id] = file_path
        
        # Generate waveform data for audio/video files
        self.generate_waveform_for_clip(clip_id, file_path)
        
        # Update the timeline composition and preview
        self.update_timeline_composition()
        
        # Reconnect track signals in case new tracks were created
        self.connect_track_signals()
        
        self.status_bar.showMessage(f"Added {os.path.basename(file_path)} to timeline with waveform")
    
    def generate_waveform_for_clip(self, clip_id: str, file_path: str):
        """Generate waveform data for a clip"""
        try:
            # Find the clip in timeline
            clip = None
            for track in self.timeline_widget.tracks:
                for track_clip in track.clips:
                    if track_clip.clip_id == clip_id:
                        clip = track_clip
                        break
                if clip:
                    break
            
            if clip:
                # Generate waveform data
                self.timeline_widget.generate_waveform_data(file_path, clip)
                # Update the timeline display
                self.timeline_widget.update_tracks()
                
        except Exception as e:
            print(f"Error generating waveform for clip {clip_id}: {e}")
    
    def on_preview_time_changed(self, time: float):
        """Handle preview time change"""
        # Prevent recursive time sync
        if self._syncing_time:
            return
            
        self._syncing_time = True
        try:
            # Update timeline playhead
            if hasattr(self.timeline_widget, 'set_playhead_time'):
                self.timeline_widget.set_playhead_time(time)
        finally:
            self._syncing_time = False
    
    def on_preview_frame_changed(self, time: float, frame):
        """Handle preview frame change"""
        # Could update frame-based displays here
        pass
    
    def update_timeline_composition(self):
        """Create a composite video from timeline clips and update preview"""
        if not hasattr(self, 'timeline_clips') or not self.timeline_clips:
            return
            
        try:
            from moviepy import VideoFileClip, CompositeVideoClip
            
            # Get all clips from timeline
            all_clips = []
            for track in self.timeline_widget.tracks:
                for clip in track.clips:
                    if clip.clip_id in self.timeline_clips:
                        file_path = self.timeline_clips[clip.clip_id]
                        
                        # Load the video clip
                        video_clip = VideoFileClip(file_path)
                        
                        # Set start time and duration
                        video_clip = video_clip.with_start(clip.start_time)
                        if clip.duration < video_clip.duration:
                            video_clip = video_clip.with_duration(clip.duration)
                            
                        all_clips.append(video_clip)
            
            if all_clips:
                # Create composite
                if len(all_clips) == 1:
                    composite_clip = all_clips[0]
                else:
                    composite_clip = CompositeVideoClip(all_clips)
                
                # Update preview with composite
                self.preview_widget.set_video_clip(composite_clip)
                
                # Update timeline duration
                total_duration = max(clip.end_time() for track in self.timeline_widget.tracks for clip in track.clips)
                self.timeline_widget.duration = total_duration
                self.timeline_widget.update_timeline_size()
                
                self.status_bar.showMessage("Timeline composition updated")
            
        except Exception as e:
            print(f"Error updating timeline composition: {e}")
            self.status_bar.showMessage(f"Error updating timeline: {str(e)}")
    
    def apply_selected_effect(self):
        """Apply the selected effect to the current clip"""
        if not self.video_processor.current_clip:
            self.status_bar.showMessage("No video loaded to apply effect")
            return
            
        selected_items = self.effects_list.selectedItems()
        if not selected_items:
            self.status_bar.showMessage("No effect selected")
            return
            
        effect_name = selected_items[0].text().lower()
        
        try:
            # Apply effect to current clip
            processed_clip = self.video_processor.apply_effect_to_clip(
                self.video_processor.current_clip, 
                effect_name
            )
            
            # Update current clip
            self.video_processor.current_clip = processed_clip
            
            # Update preview if available
            if hasattr(self.preview_widget, 'refresh_preview'):
                self.preview_widget.refresh_preview()
                
            self.status_bar.showMessage(f"Applied {effect_name.capitalize()} effect")
            
        except Exception as e:
            self.status_bar.showMessage(f"Error applying effect: {str(e)}")
    
    def apply_selected_transition(self):
        """Apply the selected transition between clips"""
        selected_items = self.transitions_list.selectedItems()
        if not selected_items:
            self.status_bar.showMessage("No transition selected")
            return
            
        transition_name = selected_items[0].text().lower().replace(' ', '_')
        
        # For demonstration, we'll apply transition between current clip and a duplicate
        # In a real scenario, this would be between two different clips
        if not self.video_processor.current_clip:
            self.status_bar.showMessage("No video loaded to apply transition")
            return
            
        try:
            # Create a simple transition demonstration
            # This is a placeholder - real implementation would handle timeline clips
            clip1 = self.video_processor.current_clip.subclip(0, 5)
            clip2 = self.video_processor.current_clip.subclip(5, 10)
            
            transitioned_clip = self.video_processor.apply_transition_between_clips(
                clip1, clip2, transition_name, 1.0
            )
            
            # Update current clip
            self.video_processor.current_clip = transitioned_clip
            
            # Update preview if available
            if hasattr(self.preview_widget, 'refresh_preview'):
                self.preview_widget.refresh_preview()
                
            self.status_bar.showMessage(f"Applied {transition_name.replace('_', ' ').capitalize()} transition")
            
        except Exception as e:
            self.status_bar.showMessage(f"Error applying transition: {str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VideoEditor()
    window.show()
    sys.exit(app.exec())

