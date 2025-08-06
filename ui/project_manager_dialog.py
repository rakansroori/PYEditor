"""
Project Manager Dialog for PyVideoEditor
Provides UI for managing workspaces, creating new projects, and opening existing ones
"""

import sys
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QListWidget,
    QListWidgetItem, QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox,
    QSpinBox, QGroupBox, QGridLayout, QMessageBox, QFileDialog, QProgressBar,
    QSplitter, QFrame, QScrollArea, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon
from typing import Dict, List, Optional
from datetime import datetime
import json

from core.workspace_manager import WorkspaceManager, ProjectSettings

class ProjectListWidget(QListWidget):
    """Custom list widget for displaying projects with enhanced information"""
    
    def __init__(self):
        super().__init__()
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
        
    def add_project_item(self, project_info: Dict):
        """Add a project item to the list"""
        item = QListWidgetItem()
        
        # Create display text
        name = project_info.get('name', 'Unnamed Project')
        modified = project_info.get('modified_date', '')
        if modified:
            try:
                modified_dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                modified_str = modified_dt.strftime('%Y-%m-%d %H:%M')
            except:
                modified_str = modified
        else:
            modified_str = 'Unknown'
            
        clip_count = project_info.get('clip_count', 0)
        asset_count = project_info.get('asset_count', 0)
        
        display_text = f"{name}\n"
        display_text += f"Modified: {modified_str}\n"
        display_text += f"Clips: {clip_count}, Assets: {asset_count}"
        
        item.setText(display_text)
        item.setData(Qt.ItemDataRole.UserRole, project_info)
        
        self.addItem(item)
        
    def on_item_double_clicked(self, item):
        """Handle double-click on project item"""
        self.parent().open_selected_project()
        
    def get_selected_project(self) -> Optional[Dict]:
        """Get currently selected project info"""
        current_item = self.currentItem()
        if current_item:
            return current_item.data(Qt.ItemDataRole.UserRole)
        return None

class NewProjectDialog(QDialog):
    """Dialog for creating a new project"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setFixedSize(400, 300)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Project name
        name_group = QGroupBox("Project Settings")
        name_layout = QGridLayout(name_group)
        
        name_layout.addWidget(QLabel("Name:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter project name")
        name_layout.addWidget(self.name_edit, 0, 1)
        
        name_layout.addWidget(QLabel("Description:"), 1, 0)
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setPlaceholderText("Optional project description")
        name_layout.addWidget(self.description_edit, 1, 1)
        
        layout.addWidget(name_group)
        
        # Video settings
        video_group = QGroupBox("Video Settings")
        video_layout = QGridLayout(video_group)
        
        video_layout.addWidget(QLabel("Frame Rate:"), 0, 0)
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["23.976", "24", "25", "29.97", "30", "50", "59.94", "60"])
        self.fps_combo.setCurrentText("30")
        video_layout.addWidget(self.fps_combo, 0, 1)
        
        video_layout.addWidget(QLabel("Resolution:"), 1, 0)
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "1920x1080 (Full HD)",
            "1280x720 (HD)",
            "3840x2160 (4K UHD)",
            "2560x1440 (QHD)",
            "1920x1200 (WUXGA)",
            "1024x768 (XGA)"
        ])
        video_layout.addWidget(self.resolution_combo, 1, 1)
        
        layout.addWidget(video_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addStretch()
        
        self.create_button = QPushButton("Create Project")
        self.create_button.clicked.connect(self.accept)
        self.create_button.setDefault(True)
        button_layout.addWidget(self.create_button)
        
        layout.addLayout(button_layout)
        
    def get_project_data(self) -> Dict:
        """Get project data from form"""
        resolution_text = self.resolution_combo.currentText()
        if "1920x1080" in resolution_text:
            resolution = (1920, 1080)
        elif "1280x720" in resolution_text:
            resolution = (1280, 720)
        elif "3840x2160" in resolution_text:
            resolution = (3840, 2160)
        elif "2560x1440" in resolution_text:
            resolution = (2560, 1440)
        elif "1920x1200" in resolution_text:
            resolution = (1920, 1200)
        else:
            resolution = (1024, 768)
            
        return {
            'name': self.name_edit.text().strip() or "Untitled Project",
            'description': self.description_edit.toPlainText().strip(),
            'fps': float(self.fps_combo.currentText()),
            'resolution': resolution
        }

class ProjectManagerDialog(QDialog):
    """Main project manager dialog"""
    
    project_selected = pyqtSignal(str)  # project_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PyVideoEditor - Project Manager")
        self.setMinimumSize(800, 600)
        self.workspace_manager = WorkspaceManager()
        self.setup_ui()
        self.refresh_projects()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Project Manager")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Recent Projects tab
        self.setup_recent_tab()
        
        # All Projects tab
        self.setup_all_projects_tab()
        
        # Import/Export tab
        self.setup_import_export_tab()
        
        layout.addWidget(self.tab_widget)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.new_project_button = QPushButton("New Project")
        self.new_project_button.clicked.connect(self.create_new_project)
        button_layout.addWidget(self.new_project_button)
        
        self.open_project_button = QPushButton("Open Project")
        self.open_project_button.clicked.connect(self.open_selected_project)
        self.open_project_button.setEnabled(False)
        button_layout.addWidget(self.open_project_button)
        
        button_layout.addStretch()
        
        self.delete_project_button = QPushButton("Delete Project")
        self.delete_project_button.clicked.connect(self.delete_selected_project)
        self.delete_project_button.setEnabled(False)
        self.delete_project_button.setStyleSheet("QPushButton { color: red; }")
        button_layout.addWidget(self.delete_project_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
    def setup_recent_tab(self):
        """Setup recent projects tab"""
        recent_widget = QWidget()
        layout = QVBoxLayout(recent_widget)
        
        # Search
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search projects...")
        self.search_edit.textChanged.connect(self.search_projects)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)
        
        # Recent projects list
        self.recent_projects_list = ProjectListWidget()
        self.recent_projects_list.itemSelectionChanged.connect(self.on_project_selection_changed)
        layout.addWidget(self.recent_projects_list)
        
        # Project info panel
        self.setup_project_info_panel(layout)
        
        self.tab_widget.addTab(recent_widget, "Recent Projects")
        
    def setup_all_projects_tab(self):
        """Setup all projects tab"""
        all_widget = QWidget()
        layout = QVBoxLayout(all_widget)
        
        # All projects list
        self.all_projects_list = ProjectListWidget()
        self.all_projects_list.itemSelectionChanged.connect(self.on_project_selection_changed)
        layout.addWidget(self.all_projects_list)
        
        # Project actions
        actions_layout = QHBoxLayout()
        
        duplicate_button = QPushButton("Duplicate Project")
        duplicate_button.clicked.connect(self.duplicate_selected_project)
        actions_layout.addWidget(duplicate_button)
        
        actions_layout.addStretch()
        
        layout.addLayout(actions_layout)
        
        self.tab_widget.addTab(all_widget, "All Projects")
        
    def setup_import_export_tab(self):
        """Setup import/export tab"""
        import_export_widget = QWidget()
        layout = QVBoxLayout(import_export_widget)
        
        # Export section
        export_group = QGroupBox("Export Project")
        export_layout = QVBoxLayout(export_group)
        
        export_info = QLabel("Export a project as a portable package that can be shared or archived.")
        export_info.setWordWrap(True)
        export_layout.addWidget(export_info)
        
        export_options_layout = QHBoxLayout()
        self.include_assets_checkbox = QCheckBox("Include media assets in export")
        self.include_assets_checkbox.setChecked(True)
        export_options_layout.addWidget(self.include_assets_checkbox)
        export_options_layout.addStretch()
        export_layout.addLayout(export_options_layout)
        
        export_button_layout = QHBoxLayout()
        export_button_layout.addStretch()
        export_project_button = QPushButton("Export Selected Project")
        export_project_button.clicked.connect(self.export_selected_project)
        export_button_layout.addWidget(export_project_button)
        export_layout.addLayout(export_button_layout)
        
        layout.addWidget(export_group)
        
        # Import section
        import_group = QGroupBox("Import Project")
        import_layout = QVBoxLayout(import_group)
        
        import_info = QLabel("Import a project package that was previously exported.")
        import_info.setWordWrap(True)
        import_layout.addWidget(import_info)
        
        import_button_layout = QHBoxLayout()
        import_button_layout.addStretch()
        import_project_button = QPushButton("Import Project Package")
        import_project_button.clicked.connect(self.import_project_package)
        import_button_layout.addWidget(import_project_button)
        import_layout.addLayout(import_button_layout)
        
        layout.addWidget(import_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(import_export_widget, "Import/Export")
        
    def setup_project_info_panel(self, parent_layout):
        """Setup project information panel"""
        info_group = QGroupBox("Project Information")
        info_layout = QVBoxLayout(info_group)
        
        self.project_info_label = QLabel("Select a project to view details")
        self.project_info_label.setWordWrap(True)
        self.project_info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        info_layout.addWidget(self.project_info_label)
        
        info_group.setMaximumHeight(120)
        parent_layout.addWidget(info_group)
        
    def refresh_projects(self):
        """Refresh project lists"""
        # Clear existing items
        self.recent_projects_list.clear()
        self.all_projects_list.clear()
        
        # Get projects
        projects = self.workspace_manager.get_project_list()
        recent_projects = projects[:10]  # Show last 10 projects
        
        # Populate recent projects
        for project in recent_projects:
            self.recent_projects_list.add_project_item(project)
            
        # Populate all projects
        for project in projects:
            self.all_projects_list.add_project_item(project)
            
    def search_projects(self, query: str):
        """Search projects and update recent list"""
        self.recent_projects_list.clear()
        
        if query.strip():
            projects = self.workspace_manager.search_projects(query)
        else:
            projects = self.workspace_manager.get_recent_projects(10)
            
        for project in projects:
            self.recent_projects_list.add_project_item(project)
            
    def on_project_selection_changed(self):
        """Handle project selection change"""
        current_tab = self.tab_widget.currentIndex()
        
        if current_tab == 0:  # Recent projects tab
            project = self.recent_projects_list.get_selected_project()
        elif current_tab == 1:  # All projects tab
            project = self.all_projects_list.get_selected_project()
        else:
            project = None
            
        # Update buttons
        has_selection = project is not None
        self.open_project_button.setEnabled(has_selection)
        self.delete_project_button.setEnabled(has_selection)
        
        # Update project info
        if project:
            self.update_project_info(project)
        else:
            self.project_info_label.setText("Select a project to view details")
            
    def update_project_info(self, project: Dict):
        """Update project information display"""
        name = project.get('name', 'Unnamed Project')
        description = project.get('description', 'No description')
        created = project.get('created_date', 'Unknown')
        modified = project.get('modified_date', 'Unknown')
        clip_count = project.get('clip_count', 0)
        asset_count = project.get('asset_count', 0)
        
        # Format dates
        try:
            if created != 'Unknown':
                created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                created = created_dt.strftime('%Y-%m-%d %H:%M')
        except:
            pass
            
        try:
            if modified != 'Unknown':
                modified_dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                modified = modified_dt.strftime('%Y-%m-%d %H:%M')
        except:
            pass
            
        info_text = f"<b>{name}</b><br>"
        info_text += f"Description: {description}<br>"
        info_text += f"Created: {created}<br>"
        info_text += f"Modified: {modified}<br>"
        info_text += f"Clips: {clip_count}, Assets: {asset_count}"
        
        self.project_info_label.setText(info_text)
        
    def create_new_project(self):
        """Create a new project"""
        dialog = NewProjectDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            project_data = dialog.get_project_data()
            
            try:
                project_id = self.workspace_manager.create_new_project(
                    name=project_data['name'],
                    description=project_data['description'],
                    fps=project_data['fps'],
                    resolution=project_data['resolution']
                )
                
                # Emit signal and close dialog
                self.project_selected.emit(project_id)
                self.accept()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create project:\n{str(e)}")
                
    def open_selected_project(self):
        """Open the selected project"""
        current_tab = self.tab_widget.currentIndex()
        
        if current_tab == 0:
            project = self.recent_projects_list.get_selected_project()
        elif current_tab == 1:
            project = self.all_projects_list.get_selected_project()
        else:
            return
            
        if project:
            project_id = project['project_id']
            self.project_selected.emit(project_id)
            self.accept()
            
    def delete_selected_project(self):
        """Delete the selected project"""
        current_tab = self.tab_widget.currentIndex()
        
        if current_tab == 0:
            project = self.recent_projects_list.get_selected_project()
        elif current_tab == 1:
            project = self.all_projects_list.get_selected_project()
        else:
            return
            
        if project:
            project_name = project['name']
            reply = QMessageBox.question(
                self, 
                "Delete Project",
                f"Are you sure you want to delete the project '{project_name}'?\n\nThis action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if self.workspace_manager.delete_project(project['project_id']):
                    self.refresh_projects()
                    QMessageBox.information(self, "Success", f"Project '{project_name}' has been deleted.")
                else:
                    QMessageBox.critical(self, "Error", f"Failed to delete project '{project_name}'.")
                    
    def duplicate_selected_project(self):
        """Duplicate the selected project"""
        project = self.all_projects_list.get_selected_project()
        if not project:
            return
            
        original_name = project['name']
        new_name, ok = QLineEdit().getText(
            self, 
            "Duplicate Project", 
            "Enter name for duplicated project:",
            text=f"{original_name} Copy"
        )
        
        if ok and new_name.strip():
            try:
                new_project_id = self.workspace_manager.duplicate_project(
                    project['project_id'], 
                    new_name.strip()
                )
                
                if new_project_id:
                    self.refresh_projects()
                    QMessageBox.information(self, "Success", f"Project duplicated as '{new_name.strip()}'.")
                else:
                    QMessageBox.critical(self, "Error", "Failed to duplicate project.")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to duplicate project:\n{str(e)}")
                
    def export_selected_project(self):
        """Export the selected project"""
        current_tab = self.tab_widget.currentIndex()
        
        if current_tab == 0:
            project = self.recent_projects_list.get_selected_project()
        elif current_tab == 1:
            project = self.all_projects_list.get_selected_project()
        else:
            QMessageBox.information(self, "No Selection", "Please select a project to export.")
            return
            
        if not project:
            QMessageBox.information(self, "No Selection", "Please select a project to export.")
            return
            
        # Get export path
        project_name = project['name'].replace(' ', '_').replace('/', '_').replace('\\', '_')
        default_filename = f"{project_name}_export.pvproj"
        
        export_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Project",
            default_filename,
            "PyVideoEditor Project (*.pvproj);;All Files (*)"
        )
        
        if export_path:
            include_assets = self.include_assets_checkbox.isChecked()
            
            try:
                if self.workspace_manager.export_workspace(project['project_id'], export_path, include_assets):
                    QMessageBox.information(self, "Success", f"Project exported to:\n{export_path}")
                else:
                    QMessageBox.critical(self, "Error", "Failed to export project.")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export project:\n{str(e)}")
                
    def import_project_package(self):
        """Import a project package"""
        import_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Project Package",
            "",
            "PyVideoEditor Project (*.pvproj);;All Files (*)"
        )
        
        if import_path:
            # Get project name
            project_name, ok = QLineEdit().getText(
                self,
                "Import Project",
                "Enter name for imported project:",
                text=os.path.splitext(os.path.basename(import_path))[0].replace('_export', '')
            )
            
            if ok and project_name.strip():
                try:
                    new_project_id = self.workspace_manager.import_workspace(import_path, project_name.strip())
                    
                    if new_project_id:
                        self.refresh_projects()
                        QMessageBox.information(self, "Success", f"Project imported as '{project_name.strip()}'.")
                    else:
                        QMessageBox.critical(self, "Error", "Failed to import project.")
                        
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to import project:\n{str(e)}")

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = ProjectManagerDialog()
    
    def on_project_selected(project_id):
        print(f"Selected project: {project_id}")
        
    dialog.project_selected.connect(on_project_selected)
    dialog.show()
    sys.exit(app.exec())
