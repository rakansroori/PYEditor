"""
Workspace Management for PyVideoEditor
Handles saving and loading of project workspaces including timeline, effects, and settings
"""

import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import uuid

@dataclass
class ProjectSettings:
    """Project settings and metadata"""
    name: str
    description: str
    created_date: str
    modified_date: str
    version: str = "1.0"
    fps: float = 30.0
    resolution: tuple = (1920, 1080)
    audio_sample_rate: int = 48000
    duration: float = 0.0
    
@dataclass
class MediaAsset:
    """Represents a media file in the project"""
    asset_id: str
    name: str
    file_path: str
    file_type: str  # "video", "audio", "image"
    duration: float
    fps: Optional[float] = None
    resolution: Optional[tuple] = None
    file_size: int = 0
    checksum: Optional[str] = None
    thumbnail_path: Optional[str] = None
    
@dataclass
class TimelineClipData:
    """Timeline clip data for serialization"""
    clip_id: str
    name: str
    start_time: float
    duration: float
    track_id: int
    asset_id: str
    in_point: float = 0.0
    out_point: Optional[float] = None
    effects: List[Dict] = None
    transitions: List[Dict] = None
    volume: float = 1.0
    opacity: float = 1.0
    
    def __post_init__(self):
        if self.effects is None:
            self.effects = []
        if self.transitions is None:
            self.transitions = []

@dataclass
class TrackData:
    """Track data for serialization"""
    track_id: int
    name: str
    track_type: str  # "video" or "audio"
    muted: bool = False
    locked: bool = False
    height: int = 60
    volume: float = 1.0

class WorkspaceManager:
    """Manages project workspaces - saving, loading, and organization"""
    
    def __init__(self, projects_dir: str = None):
        self.projects_dir = projects_dir or os.path.join(os.path.expanduser("~"), "PyVideoEditor", "Projects")
        self.ensure_projects_directory()
        
    def ensure_projects_directory(self):
        """Ensure projects directory exists"""
        os.makedirs(self.projects_dir, exist_ok=True)
        
    def create_new_project(self, name: str, description: str = "", 
                          fps: float = 30.0, resolution: tuple = (1920, 1080)) -> str:
        """Create a new project and return its ID"""
        project_id = str(uuid.uuid4())
        project_dir = os.path.join(self.projects_dir, project_id)
        os.makedirs(project_dir, exist_ok=True)
        
        # Create project subdirectories
        os.makedirs(os.path.join(project_dir, "assets"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "thumbnails"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "exports"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "backups"), exist_ok=True)
        
        # Create project settings
        settings = ProjectSettings(
            name=name,
            description=description,
            created_date=datetime.now().isoformat(),
            modified_date=datetime.now().isoformat(),
            fps=fps,
            resolution=resolution
        )
        
        # Initialize empty workspace
        workspace_data = {
            "project_id": project_id,
            "settings": asdict(settings),
            "media_assets": {},
            "tracks": [],
            "timeline_clips": [],
            "effects_presets": [],
            "export_settings": {},
            "markers": [],
            "metadata": {
                "last_opened": datetime.now().isoformat(),
                "total_edits": 0,
                "export_count": 0
            }
        }
        
        self.save_workspace(project_id, workspace_data)
        return project_id
        
    def save_workspace(self, project_id: str, workspace_data: Dict) -> bool:
        """Save workspace data to project file"""
        try:
            project_dir = os.path.join(self.projects_dir, project_id)
            if not os.path.exists(project_dir):
                os.makedirs(project_dir, exist_ok=True)
                
            # Update modification time
            if "settings" in workspace_data:
                workspace_data["settings"]["modified_date"] = datetime.now().isoformat()
                
            # Create backup of existing workspace
            workspace_file = os.path.join(project_dir, "workspace.json")
            if os.path.exists(workspace_file):
                backup_dir = os.path.join(project_dir, "backups")
                backup_file = os.path.join(backup_dir, f"workspace_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                shutil.copy2(workspace_file, backup_file)
                
                # Keep only last 10 backups
                self._cleanup_backups(backup_dir)
                
            # Save workspace
            with open(workspace_file, 'w', encoding='utf-8') as f:
                json.dump(workspace_data, f, indent=2, ensure_ascii=False)
                
            return True
            
        except Exception as e:
            print(f"Error saving workspace: {e}")
            return False
            
    def load_workspace(self, project_id: str) -> Optional[Dict]:
        """Load workspace data from project file"""
        try:
            workspace_file = os.path.join(self.projects_dir, project_id, "workspace.json")
            if not os.path.exists(workspace_file):
                return None
                
            with open(workspace_file, 'r', encoding='utf-8') as f:
                workspace_data = json.load(f)
                
            # Update last opened time
            if "metadata" not in workspace_data:
                workspace_data["metadata"] = {}
            workspace_data["metadata"]["last_opened"] = datetime.now().isoformat()
            
            # Save updated metadata
            self.save_workspace(project_id, workspace_data)
            
            return workspace_data
            
        except Exception as e:
            print(f"Error loading workspace: {e}")
            return None
            
    def get_project_list(self) -> List[Dict]:
        """Get list of all projects with basic info"""
        projects = []
        
        try:
            for item in os.listdir(self.projects_dir):
                project_dir = os.path.join(self.projects_dir, item)
                if os.path.isdir(project_dir):
                    workspace_file = os.path.join(project_dir, "workspace.json")
                    if os.path.exists(workspace_file):
                        try:
                            with open(workspace_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                
                            settings = data.get("settings", {})
                            metadata = data.get("metadata", {})
                            
                            project_info = {
                                "project_id": item,
                                "name": settings.get("name", "Unnamed Project"),
                                "description": settings.get("description", ""),
                                "created_date": settings.get("created_date", ""),
                                "modified_date": settings.get("modified_date", ""),
                                "last_opened": metadata.get("last_opened", ""),
                                "duration": settings.get("duration", 0.0),
                                "clip_count": len(data.get("timeline_clips", [])),
                                "asset_count": len(data.get("media_assets", {}))
                            }
                            
                            projects.append(project_info)
                            
                        except Exception as e:
                            print(f"Error reading project {item}: {e}")
                            
        except Exception as e:
            print(f"Error listing projects: {e}")
            
        # Sort by last modified
        projects.sort(key=lambda x: x.get("modified_date", ""), reverse=True)
        return projects
        
    def delete_project(self, project_id: str) -> bool:
        """Delete a project and all its files"""
        try:
            project_dir = os.path.join(self.projects_dir, project_id)
            if os.path.exists(project_dir):
                shutil.rmtree(project_dir)
                return True
            return False
            
        except Exception as e:
            print(f"Error deleting project: {e}")
            return False
            
    def duplicate_project(self, project_id: str, new_name: str) -> Optional[str]:
        """Duplicate an existing project"""
        try:
            # Load original workspace
            workspace_data = self.load_workspace(project_id)
            if not workspace_data:
                return None
                
            # Create new project
            new_project_id = str(uuid.uuid4())
            new_project_dir = os.path.join(self.projects_dir, new_project_id)
            
            # Copy entire project directory
            original_project_dir = os.path.join(self.projects_dir, project_id)
            shutil.copytree(original_project_dir, new_project_dir)
            
            # Update workspace data
            workspace_data["project_id"] = new_project_id
            workspace_data["settings"]["name"] = new_name
            workspace_data["settings"]["created_date"] = datetime.now().isoformat()
            workspace_data["settings"]["modified_date"] = datetime.now().isoformat()
            
            # Reset metadata
            workspace_data["metadata"] = {
                "last_opened": datetime.now().isoformat(),
                "total_edits": 0,
                "export_count": 0
            }
            
            # Save updated workspace
            self.save_workspace(new_project_id, workspace_data)
            
            return new_project_id
            
        except Exception as e:
            print(f"Error duplicating project: {e}")
            return None
            
    def export_workspace(self, project_id: str, export_path: str, include_assets: bool = True) -> bool:
        """Export workspace as a portable package"""
        try:
            import zipfile
            
            project_dir = os.path.join(self.projects_dir, project_id)
            if not os.path.exists(project_dir):
                return False
                
            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add workspace file
                workspace_file = os.path.join(project_dir, "workspace.json")
                if os.path.exists(workspace_file):
                    zipf.write(workspace_file, "workspace.json")
                    
                # Add thumbnails
                thumbnails_dir = os.path.join(project_dir, "thumbnails")
                if os.path.exists(thumbnails_dir):
                    for root, dirs, files in os.walk(thumbnails_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arc_path = os.path.relpath(file_path, project_dir)
                            zipf.write(file_path, arc_path)
                            
                # Add assets if requested
                if include_assets:
                    assets_dir = os.path.join(project_dir, "assets")
                    if os.path.exists(assets_dir):
                        for root, dirs, files in os.walk(assets_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arc_path = os.path.relpath(file_path, project_dir)
                                zipf.write(file_path, arc_path)
                                
            return True
            
        except Exception as e:
            print(f"Error exporting workspace: {e}")
            return False
            
    def import_workspace(self, import_path: str, project_name: str = None) -> Optional[str]:
        """Import workspace from exported package"""
        try:
            import zipfile
            
            if not os.path.exists(import_path):
                return None
                
            # Create new project ID
            project_id = str(uuid.uuid4())
            project_dir = os.path.join(self.projects_dir, project_id)
            os.makedirs(project_dir, exist_ok=True)
            
            # Extract zip file
            with zipfile.ZipFile(import_path, 'r') as zipf:
                zipf.extractall(project_dir)
                
            # Update workspace data
            workspace_file = os.path.join(project_dir, "workspace.json")
            if os.path.exists(workspace_file):
                with open(workspace_file, 'r', encoding='utf-8') as f:
                    workspace_data = json.load(f)
                    
                workspace_data["project_id"] = project_id
                if project_name:
                    workspace_data["settings"]["name"] = project_name
                workspace_data["settings"]["modified_date"] = datetime.now().isoformat()
                workspace_data["metadata"]["last_opened"] = datetime.now().isoformat()
                
                with open(workspace_file, 'w', encoding='utf-8') as f:
                    json.dump(workspace_data, f, indent=2, ensure_ascii=False)
                    
            return project_id
            
        except Exception as e:
            print(f"Error importing workspace: {e}")
            return None
            
    def add_media_asset(self, project_id: str, asset: MediaAsset) -> bool:
        """Add a media asset to the project"""
        workspace_data = self.load_workspace(project_id)
        if not workspace_data:
            return False
            
        workspace_data["media_assets"][asset.asset_id] = asdict(asset)
        return self.save_workspace(project_id, workspace_data)
        
    def remove_media_asset(self, project_id: str, asset_id: str) -> bool:
        """Remove a media asset from the project"""
        workspace_data = self.load_workspace(project_id)
        if not workspace_data:
            return False
            
        if asset_id in workspace_data["media_assets"]:
            del workspace_data["media_assets"][asset_id]
            
            # Remove from timeline clips that use this asset
            workspace_data["timeline_clips"] = [
                clip for clip in workspace_data["timeline_clips"]
                if clip.get("asset_id") != asset_id
            ]
            
            return self.save_workspace(project_id, workspace_data)
            
        return False
        
    def get_recent_projects(self, limit: int = 10) -> List[Dict]:
        """Get recently opened projects"""
        projects = self.get_project_list()
        return projects[:limit]
        
    def search_projects(self, query: str) -> List[Dict]:
        """Search projects by name or description"""
        projects = self.get_project_list()
        query_lower = query.lower()
        
        return [
            project for project in projects
            if query_lower in project["name"].lower() or 
               query_lower in project["description"].lower()
        ]
        
    def get_project_statistics(self, project_id: str) -> Dict:
        """Get detailed project statistics"""
        workspace_data = self.load_workspace(project_id)
        if not workspace_data:
            return {}
            
        project_dir = os.path.join(self.projects_dir, project_id)
        
        # Calculate directory size
        total_size = 0
        for root, dirs, files in os.walk(project_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
                    
        assets = workspace_data.get("media_assets", {})
        clips = workspace_data.get("timeline_clips", [])
        
        # Calculate total timeline duration
        max_end_time = 0
        for clip in clips:
            end_time = clip.get("start_time", 0) + clip.get("duration", 0)
            max_end_time = max(max_end_time, end_time)
            
        return {
            "total_size_bytes": total_size,
            "total_size_formatted": self._format_file_size(total_size),
            "asset_count": len(assets),
            "clip_count": len(clips),
            "timeline_duration": max_end_time,
            "video_assets": len([a for a in assets.values() if a.get("file_type") == "video"]),
            "audio_assets": len([a for a in assets.values() if a.get("file_type") == "audio"]),
            "image_assets": len([a for a in assets.values() if a.get("file_type") == "image"]),
            "backup_count": self._count_backups(project_id)
        }
        
    def _cleanup_backups(self, backup_dir: str, max_backups: int = 10):
        """Clean up old backup files"""
        try:
            backup_files = []
            for file in os.listdir(backup_dir):
                if file.startswith("workspace_backup_") and file.endswith(".json"):
                    file_path = os.path.join(backup_dir, file)
                    backup_files.append((file_path, os.path.getmtime(file_path)))
                    
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # Remove old backups
            for file_path, _ in backup_files[max_backups:]:
                os.remove(file_path)
                
        except Exception as e:
            print(f"Error cleaning up backups: {e}")
            
    def _count_backups(self, project_id: str) -> int:
        """Count number of backup files for a project"""
        try:
            backup_dir = os.path.join(self.projects_dir, project_id, "backups")
            if not os.path.exists(backup_dir):
                return 0
                
            return len([f for f in os.listdir(backup_dir) 
                       if f.startswith("workspace_backup_") and f.endswith(".json")])
                       
        except Exception:
            return 0
            
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
