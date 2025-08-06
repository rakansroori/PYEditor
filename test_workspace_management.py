#!/usr/bin/env python3
"""
Test script for PyVideoEditor Workspace Management
Demonstrates creating, saving, loading, and managing workspaces
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from ui.project_manager_dialog import ProjectManagerDialog
from core.workspace_manager import WorkspaceManager, MediaAsset, TimelineClipData, TrackData
import uuid

def test_workspace_manager():
    """Test the workspace manager functionality"""
    print("Testing PyVideoEditor Workspace Management...")
    
    # Initialize workspace manager
    workspace_manager = WorkspaceManager()
    
    print(f"Projects directory: {workspace_manager.projects_dir}")
    
    # Test creating a new project
    print("\n1. Creating a new project...")
    project_id = workspace_manager.create_new_project(
        name="Test Project",
        description="A test project for demonstrating workspace management",
        fps=30.0,
        resolution=(1920, 1080)
    )
    print(f"Created project with ID: {project_id}")
    
    # Test loading the project
    print("\n2. Loading the project...")
    workspace_data = workspace_manager.load_workspace(project_id)
    if workspace_data:
        print("Project loaded successfully!")
        print(f"Project name: {workspace_data['settings']['name']}")
        print(f"Resolution: {workspace_data['settings']['resolution']}")
        print(f"FPS: {workspace_data['settings']['fps']}")
    else:
        print("Failed to load project!")
        return False
    
    # Test adding media assets
    print("\n3. Adding media assets...")
    sample_asset = MediaAsset(
        asset_id=str(uuid.uuid4()),
        name="sample_video.mp4",
        file_path="/path/to/sample_video.mp4",
        file_type="video",
        duration=120.0,
        fps=30.0,
        resolution=(1920, 1080),
        file_size=50000000
    )
    
    success = workspace_manager.add_media_asset(project_id, sample_asset)
    if success:
        print(f"Added media asset: {sample_asset.name}")
    else:
        print("Failed to add media asset!")
    
    # Test getting project list
    print("\n4. Getting project list...")
    projects = workspace_manager.get_project_list()
    print(f"Found {len(projects)} projects:")
    for project in projects:
        print(f"  - {project['name']} (ID: {project['project_id'][:8]}...)")
    
    # Test project statistics
    print("\n5. Getting project statistics...")
    stats = workspace_manager.get_project_statistics(project_id)
    if stats:
        print(f"Total size: {stats['total_size_formatted']}")
        print(f"Asset count: {stats['asset_count']}")
        print(f"Clip count: {stats['clip_count']}")
        print(f"Backup count: {stats['backup_count']}")
    
    # Test duplication
    print("\n6. Duplicating project...")
    duplicated_id = workspace_manager.duplicate_project(project_id, "Test Project Copy")
    if duplicated_id:
        print(f"Duplicated project with ID: {duplicated_id}")
    else:
        print("Failed to duplicate project!")
    
    # Test export (without actual media files)
    print("\n7. Testing export functionality...")
    export_path = os.path.join(workspace_manager.projects_dir, "test_export.pvproj")
    success = workspace_manager.export_workspace(project_id, export_path, include_assets=False)
    if success:
        print(f"Exported project to: {export_path}")
    else:
        print("Failed to export project!")
    
    # Test import
    if success and os.path.exists(export_path):
        print("\n8. Testing import functionality...")
        imported_id = workspace_manager.import_workspace(export_path, "Imported Test Project")
        if imported_id:
            print(f"Imported project with ID: {imported_id}")
        else:
            print("Failed to import project!")
    
    # Test search
    print("\n9. Testing project search...")
    search_results = workspace_manager.search_projects("Test")
    print(f"Found {len(search_results)} projects matching 'Test':")
    for project in search_results:
        print(f"  - {project['name']}")
    
    # Clean up test projects (optional - comment out to keep test data)
    print("\n10. Cleaning up test projects...")
    all_projects = workspace_manager.get_project_list()
    for project in all_projects:
        if "Test" in project['name']:
            workspace_manager.delete_project(project['project_id'])
            print(f"Deleted project: {project['name']}")
    
    # Clean up export file
    if os.path.exists(export_path):
        os.remove(export_path)
        print(f"Deleted export file: {export_path}")
    
    print("\nWorkspace management test completed!")
    return True

def test_project_manager_dialog():
    """Test the project manager dialog"""
    print("\nTesting Project Manager Dialog...")
    
    app = QApplication(sys.argv)
    
    # Create and show the dialog
    dialog = ProjectManagerDialog()
    
    def on_project_selected(project_id):
        print(f"Project selected: {project_id}")
        QMessageBox.information(None, "Project Selected", f"Selected project: {project_id}")
        app.quit()
    
    dialog.project_selected.connect(on_project_selected)
    
    # Show dialog
    result = dialog.exec()
    
    if result == dialog.DialogCode.Accepted:
        print("Dialog accepted")
    else:
        print("Dialog cancelled")
    
    return True

def main():
    """Main test function"""
    print("PyVideoEditor Workspace Management Test Suite")
    print("=" * 50)
    
    # Test 1: Workspace Manager functionality
    if not test_workspace_manager():
        print("Workspace manager tests failed!")
        return 1
    
    # Test 2: Project Manager Dialog (interactive)
    print("\n" + "=" * 50)
    choice = input("Do you want to test the Project Manager Dialog? (y/n): ").lower().strip()
    
    if choice == 'y' or choice == 'yes':
        if not test_project_manager_dialog():
            print("Project manager dialog tests failed!")
            return 1
    
    print("\nAll tests completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
