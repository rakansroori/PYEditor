"""
Advanced 3D Effects Plugin System for PyVideoEditor
Provides 3D transformations, depth effects, and perspective manipulation
"""

from abc import ABC, abstractmethod
from moviepy import VideoFileClip, CompositeVideoClip, ColorClip
import numpy as np
import cv2
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass
import math

@dataclass
class Transform3D:
    """3D transformation parameters"""
    rotation_x: float = 0.0      # Rotation around X-axis (degrees)
    rotation_y: float = 0.0      # Rotation around Y-axis (degrees)
    rotation_z: float = 0.0      # Rotation around Z-axis (degrees)
    translation_x: float = 0.0   # Translation along X-axis (pixels)
    translation_y: float = 0.0   # Translation along Y-axis (pixels)
    translation_z: float = 0.0   # Translation along Z-axis (depth)
    scale_x: float = 1.0         # Scale factor X
    scale_y: float = 1.0         # Scale factor Y
    scale_z: float = 1.0         # Scale factor Z (depth)
    perspective: float = 1000.0  # Perspective distance
    center_x: float = 0.5        # Center of transformation (0-1)
    center_y: float = 0.5        # Center of transformation (0-1)

class Effect3D(ABC):
    """Base class for all 3D effects"""
    
    @abstractmethod
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply the 3D effect to a video clip"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the effect"""
        pass

class Matrix3DUtils:
    """Utility class for 3D matrix operations"""
    
    @staticmethod
    def get_rotation_matrix_x(angle_degrees: float) -> np.ndarray:
        """Get rotation matrix for X-axis"""
        angle = np.radians(angle_degrees)
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        return np.array([
            [1, 0, 0],
            [0, cos_a, -sin_a],
            [0, sin_a, cos_a]
        ])
    
    @staticmethod
    def get_rotation_matrix_y(angle_degrees: float) -> np.ndarray:
        """Get rotation matrix for Y-axis"""
        angle = np.radians(angle_degrees)
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        return np.array([
            [cos_a, 0, sin_a],
            [0, 1, 0],
            [-sin_a, 0, cos_a]
        ])
    
    @staticmethod
    def get_rotation_matrix_z(angle_degrees: float) -> np.ndarray:
        """Get rotation matrix for Z-axis"""
        angle = np.radians(angle_degrees)
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        return np.array([
            [cos_a, -sin_a, 0],
            [sin_a, cos_a, 0],
            [0, 0, 1]
        ])
    
    @staticmethod
    def get_combined_rotation_matrix(rx: float, ry: float, rz: float) -> np.ndarray:
        """Get combined rotation matrix for all three axes"""
        rx_mat = Matrix3DUtils.get_rotation_matrix_x(rx)
        ry_mat = Matrix3DUtils.get_rotation_matrix_y(ry)
        rz_mat = Matrix3DUtils.get_rotation_matrix_z(rz)
        return rz_mat @ ry_mat @ rx_mat
    
    @staticmethod
    def apply_perspective_projection(points: np.ndarray, distance: float) -> np.ndarray:
        """Apply perspective projection to 3D points"""
        # Points should be in format [x, y, z, 1] for homogeneous coordinates
        projected = points.copy()
        
        # Avoid division by zero
        z_values = points[:, 2] + distance
        z_values = np.where(z_values == 0, 0.001, z_values)
        
        # Apply perspective projection
        projected[:, 0] = (points[:, 0] * distance) / z_values
        projected[:, 1] = (points[:, 1] * distance) / z_values
        
        return projected

class Rotate3DEffect(Effect3D):
    """3D rotation effect"""
    
    def __init__(self, transform: Transform3D):
        self.transform = transform
    
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply 3D rotation effect"""
        def rotate_3d_frame(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]
            
            # Create corner points of the frame
            corners = np.array([
                [-w/2, -h/2, 0, 1],
                [w/2, -h/2, 0, 1],
                [w/2, h/2, 0, 1],
                [-w/2, h/2, 0, 1]
            ], dtype=np.float32)
            
            # Apply rotation
            rotation_matrix = Matrix3DUtils.get_combined_rotation_matrix(
                self.transform.rotation_x,
                self.transform.rotation_y,
                self.transform.rotation_z
            )
            
            # Apply rotation to corners
            rotated_corners = corners[:, :3] @ rotation_matrix.T
            rotated_corners = np.column_stack([rotated_corners, np.ones(4)])
            
            # Apply perspective projection
            projected_corners = Matrix3DUtils.apply_perspective_projection(
                rotated_corners,
                self.transform.perspective
            )
            
            # Translate to center of frame
            center_x = w * self.transform.center_x
            center_y = h * self.transform.center_y
            
            projected_corners[:, 0] += center_x + self.transform.translation_x
            projected_corners[:, 1] += center_y + self.transform.translation_y
            
            # Apply scale
            projected_corners[:, 0] *= self.transform.scale_x
            projected_corners[:, 1] *= self.transform.scale_y
            
            # Create transformation matrix for perspective transform
            src_corners = np.array([
                [0, 0],
                [w, 0],
                [w, h],
                [0, h]
            ], dtype=np.float32)
            
            dst_corners = projected_corners[:, :2].astype(np.float32)
            
            # Get perspective transformation matrix
            try:
                matrix = cv2.getPerspectiveTransform(src_corners, dst_corners)
                
                # Apply transformation
                transformed = cv2.warpPerspective(frame, matrix, (w, h))
                
                return transformed
            except:
                # Return original frame if transformation fails
                return frame
        
        return clip.fl(rotate_3d_frame)
    
    def get_name(self) -> str:
        return "3D Rotation"

class Cube3DEffect(Effect3D):
    """3D cube effect that maps video onto cube faces"""
    
    def __init__(self, rotation_speed: float = 30.0, cube_size: float = 0.8):
        self.rotation_speed = rotation_speed  # degrees per second
        self.cube_size = cube_size
    
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply 3D cube effect"""
        def cube_3d_frame(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]
            
            # Calculate rotation based on time
            rotation_angle = (t * self.rotation_speed) % 360
            
            # Create cube transformation
            transform = Transform3D(
                rotation_y=rotation_angle,
                rotation_x=rotation_angle * 0.5,
                scale_x=self.cube_size,
                scale_y=self.cube_size,
                perspective=w * 2
            )
            
            # Apply the transformation
            rotator = Rotate3DEffect(transform)
            temp_clip = VideoFileClip(make_frame=get_frame, duration=0.1)
            rotated_clip = rotator.apply(temp_clip)
            
            return rotated_clip.get_frame(0)
        
        return clip.fl(cube_3d_frame)
    
    def get_name(self) -> str:
        return "3D Cube"

class Cylinder3DEffect(Effect3D):
    """3D cylinder effect that wraps video around a cylinder"""
    
    def __init__(self, curvature: float = 0.5, rotation_speed: float = 0.0):
        self.curvature = curvature  # How curved the cylinder is (0-1)
        self.rotation_speed = rotation_speed  # degrees per second
    
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply 3D cylinder effect"""
        def cylinder_3d_frame(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]
            
            # Create output frame
            output = np.zeros_like(frame)
            
            # Calculate rotation offset
            rotation_offset = (t * self.rotation_speed) % (2 * np.pi)
            
            for y in range(h):
                for x in range(w):
                    # Normalize coordinates to [-1, 1]
                    norm_x = (x / w) * 2 - 1
                    norm_y = (y / h) * 2 - 1
                    
                    # Apply cylindrical mapping
                    theta = norm_x * np.pi * self.curvature + rotation_offset
                    radius = 1.0
                    
                    # Calculate 3D position
                    x_3d = radius * np.sin(theta)
                    z_3d = radius * np.cos(theta)
                    y_3d = norm_y
                    
                    # Apply perspective projection
                    perspective_distance = w
                    if z_3d + perspective_distance != 0:
                        proj_x = (x_3d * perspective_distance) / (z_3d + perspective_distance)
                        proj_y = (y_3d * perspective_distance) / (z_3d + perspective_distance)
                        
                        # Convert back to image coordinates
                        src_x = int((proj_x + 1) * w / 2)
                        src_y = int((proj_y + 1) * h / 2)
                        
                        # Check bounds and copy pixel
                        if 0 <= src_x < w and 0 <= src_y < h:
                            output[y, x] = frame[src_y, src_x]
            
            return output
        
        return clip.fl(cylinder_3d_frame)
    
    def get_name(self) -> str:
        return "3D Cylinder"

class Sphere3DEffect(Effect3D):
    """3D sphere effect that maps video onto a sphere"""
    
    def __init__(self, sphere_radius: float = 0.8, rotation_speed: float = 20.0):
        self.sphere_radius = sphere_radius
        self.rotation_speed = rotation_speed  # degrees per second
    
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply 3D sphere effect"""
        def sphere_3d_frame(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]
            
            output = np.zeros_like(frame)
            
            # Calculate rotation
            rotation_angle = np.radians(t * self.rotation_speed)
            
            center_x, center_y = w // 2, h // 2
            max_radius = min(w, h) // 2 * self.sphere_radius
            
            for y in range(h):
                for x in range(w):
                    # Distance from center
                    dx = x - center_x
                    dy = y - center_y
                    distance = np.sqrt(dx*dx + dy*dy)
                    
                    if distance <= max_radius:
                        # Calculate sphere coordinates
                        norm_x = dx / max_radius
                        norm_y = dy / max_radius
                        
                        # Calculate Z coordinate on sphere
                        z_squared = 1 - norm_x*norm_x - norm_y*norm_y
                        if z_squared >= 0:
                            norm_z = np.sqrt(z_squared)
                            
                            # Apply rotation around Y-axis
                            rotated_x = norm_x * np.cos(rotation_angle) - norm_z * np.sin(rotation_angle)
                            rotated_z = norm_x * np.sin(rotation_angle) + norm_z * np.cos(rotation_angle)
                            
                            # Convert to texture coordinates
                            theta = np.arctan2(rotated_x, rotated_z)
                            phi = np.arcsin(norm_y)
                            
                            # Map to image coordinates
                            tex_x = (theta / np.pi + 1) * w / 2
                            tex_y = (phi / (np.pi/2) + 1) * h / 2
                            
                            src_x = int(tex_x) % w
                            src_y = int(tex_y) % h
                            
                            output[y, x] = frame[src_y, src_x]
            
            return output
        
        return clip.fl(sphere_3d_frame)
    
    def get_name(self) -> str:
        return "3D Sphere"

class WaveDeform3DEffect(Effect3D):
    """3D wave deformation effect"""
    
    def __init__(self, amplitude: float = 20.0, frequency: float = 2.0, 
                 wave_speed: float = 5.0, direction: str = "horizontal"):
        self.amplitude = amplitude
        self.frequency = frequency
        self.wave_speed = wave_speed
        self.direction = direction  # "horizontal", "vertical", or "both"
    
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply 3D wave deformation effect"""
        def wave_3d_frame(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]
            
            # Create coordinate grids
            x_coords, y_coords = np.meshgrid(np.arange(w), np.arange(h))
            
            # Calculate wave offset based on time
            time_offset = t * self.wave_speed
            
            # Apply wave deformations
            if self.direction in ["horizontal", "both"]:
                wave_x = self.amplitude * np.sin(
                    (y_coords * self.frequency * 2 * np.pi / h) + time_offset
                )
                x_coords = x_coords + wave_x
            
            if self.direction in ["vertical", "both"]:
                wave_y = self.amplitude * np.sin(
                    (x_coords * self.frequency * 2 * np.pi / w) + time_offset
                )
                y_coords = y_coords + wave_y
            
            # Ensure coordinates are within bounds
            x_coords = np.clip(x_coords, 0, w - 1).astype(int)
            y_coords = np.clip(y_coords, 0, h - 1).astype(int)
            
            # Create output frame by remapping pixels
            output = frame[y_coords, x_coords]
            
            return output
        
        return clip.fl(wave_3d_frame)
    
    def get_name(self) -> str:
        return "3D Wave Deform"

class Ripple3DEffect(Effect3D):
    """3D ripple effect emanating from center"""
    
    def __init__(self, amplitude: float = 30.0, frequency: float = 3.0, 
                 wave_speed: float = 100.0, decay: float = 0.5):
        self.amplitude = amplitude
        self.frequency = frequency
        self.wave_speed = wave_speed
        self.decay = decay
    
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply 3D ripple effect"""
        def ripple_3d_frame(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]
            
            center_x, center_y = w // 2, h // 2
            
            # Create coordinate grids
            x_coords, y_coords = np.meshgrid(np.arange(w), np.arange(h))
            
            # Calculate distance from center
            distances = np.sqrt((x_coords - center_x)**2 + (y_coords - center_y)**2)
            
            # Calculate ripple wave
            wave_phase = distances * self.frequency - t * self.wave_speed
            wave_amplitude = self.amplitude * np.exp(-distances * self.decay / max(w, h))
            
            # Apply ripple deformation
            ripple_offset = wave_amplitude * np.sin(wave_phase * 2 * np.pi / max(w, h))
            
            # Calculate direction vectors for displacement
            norm_x = (x_coords - center_x) / (distances + 1e-6)
            norm_y = (y_coords - center_y) / (distances + 1e-6)
            
            # Apply displacement
            new_x = x_coords + ripple_offset * norm_x
            new_y = y_coords + ripple_offset * norm_y
            
            # Ensure coordinates are within bounds
            new_x = np.clip(new_x, 0, w - 1).astype(int)
            new_y = np.clip(new_y, 0, h - 1).astype(int)
            
            # Create output frame by remapping pixels
            output = frame[new_y, new_x]
            
            return output
        
        return clip.fl(ripple_3d_frame)
    
    def get_name(self) -> str:
        return "3D Ripple"

class DepthOfField3DEffect(Effect3D):
    """3D depth of field effect with blur based on distance"""
    
    def __init__(self, focus_distance: float = 0.5, blur_strength: float = 5.0,
                 depth_map_type: str = "radial"):
        self.focus_distance = focus_distance  # 0-1, where to focus
        self.blur_strength = blur_strength
        self.depth_map_type = depth_map_type  # "radial", "linear", "custom"
    
    def apply(self, clip: VideoFileClip) -> VideoFileClip:
        """Apply 3D depth of field effect"""
        def dof_3d_frame(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]
            
            # Create depth map
            if self.depth_map_type == "radial":
                center_x, center_y = w // 2, h // 2
                x_coords, y_coords = np.meshgrid(np.arange(w), np.arange(h))
                distances = np.sqrt((x_coords - center_x)**2 + (y_coords - center_y)**2)
                depth_map = distances / np.max(distances)
            elif self.depth_map_type == "linear":
                depth_map = np.linspace(0, 1, h)[:, np.newaxis].repeat(w, axis=1)
            else:
                # Default to radial
                center_x, center_y = w // 2, h // 2
                x_coords, y_coords = np.meshgrid(np.arange(w), np.arange(h))
                distances = np.sqrt((x_coords - center_x)**2 + (y_coords - center_y)**2)
                depth_map = distances / np.max(distances)
            
            # Calculate blur amount based on distance from focus
            blur_map = np.abs(depth_map - self.focus_distance) * self.blur_strength
            
            # Apply varying blur
            output = frame.copy()
            
            # Sample different blur levels
            blur_levels = np.unique(np.round(blur_map).astype(int))
            
            for blur_level in blur_levels:
                if blur_level > 0:
                    # Create mask for this blur level
                    mask = (np.round(blur_map).astype(int) == blur_level)
                    
                    if np.any(mask):
                        # Apply Gaussian blur
                        kernel_size = int(blur_level * 2) + 1
                        if kernel_size % 2 == 0:
                            kernel_size += 1
                        
                        blurred_frame = cv2.GaussianBlur(frame, (kernel_size, kernel_size), 0)
                        
                        # Apply mask
                        output[mask] = blurred_frame[mask]
            
            return output
        
        return clip.fl(dof_3d_frame)
    
    def get_name(self) -> str:
        return "3D Depth of Field"

class Effects3DManager:
    """Manager for all 3D effects"""
    
    def __init__(self):
        self.effects = {
            'rotate_3d': Rotate3DEffect,
            'cube_3d': Cube3DEffect,
            'cylinder_3d': Cylinder3DEffect,
            'sphere_3d': Sphere3DEffect,
            'wave_deform_3d': WaveDeform3DEffect,
            'ripple_3d': Ripple3DEffect,
            'depth_of_field_3d': DepthOfField3DEffect
        }
    
    def get_effect(self, effect_name: str, **kwargs) -> Effect3D:
        """Get a 3D effect instance by name"""
        if effect_name in self.effects:
            return self.effects[effect_name](**kwargs)
        else:
            raise ValueError(f"3D Effect '{effect_name}' not found")
    
    def list_effects(self) -> List[str]:
        """List all available 3D effects"""
        return list(self.effects.keys())
    
    def apply_effect(self, clip: VideoFileClip, effect_name: str, **kwargs) -> VideoFileClip:
        """Apply a 3D effect to a clip"""
        effect = self.get_effect(effect_name, **kwargs)
        return effect.apply(clip)
    
    def create_transform_3d(self, **kwargs) -> Transform3D:
        """Create a 3D transform with given parameters"""
        return Transform3D(**kwargs)
    
    def animate_transform_3d(self, clip: VideoFileClip, 
                           start_transform: Transform3D,
                           end_transform: Transform3D,
                           easing: str = "linear") -> VideoFileClip:
        """Animate between two 3D transforms"""
        def animated_3d_frame(get_frame, t):
            frame = get_frame(t)
            duration = clip.duration
            
            # Calculate interpolation factor
            if duration > 0:
                factor = t / duration
            else:
                factor = 0
            
            # Apply easing
            if easing == "ease_in":
                factor = factor * factor
            elif easing == "ease_out":
                factor = 1 - (1 - factor) * (1 - factor)
            elif easing == "ease_in_out":
                if factor < 0.5:
                    factor = 2 * factor * factor
                else:
                    factor = 1 - 2 * (1 - factor) * (1 - factor)
            
            # Interpolate transforms
            interpolated_transform = Transform3D(
                rotation_x=start_transform.rotation_x + (end_transform.rotation_x - start_transform.rotation_x) * factor,
                rotation_y=start_transform.rotation_y + (end_transform.rotation_y - start_transform.rotation_y) * factor,
                rotation_z=start_transform.rotation_z + (end_transform.rotation_z - start_transform.rotation_z) * factor,
                translation_x=start_transform.translation_x + (end_transform.translation_x - start_transform.translation_x) * factor,
                translation_y=start_transform.translation_y + (end_transform.translation_y - start_transform.translation_y) * factor,
                translation_z=start_transform.translation_z + (end_transform.translation_z - start_transform.translation_z) * factor,
                scale_x=start_transform.scale_x + (end_transform.scale_x - start_transform.scale_x) * factor,
                scale_y=start_transform.scale_y + (end_transform.scale_y - start_transform.scale_y) * factor,
                scale_z=start_transform.scale_z + (end_transform.scale_z - start_transform.scale_z) * factor,
                perspective=start_transform.perspective + (end_transform.perspective - start_transform.perspective) * factor,
                center_x=start_transform.center_x + (end_transform.center_x - start_transform.center_x) * factor,
                center_y=start_transform.center_y + (end_transform.center_y - start_transform.center_y) * factor
            )
            
            # Apply the interpolated transform
            effect = Rotate3DEffect(interpolated_transform)
            temp_clip = VideoFileClip(make_frame=get_frame, duration=0.1)
            transformed_clip = effect.apply(temp_clip)
            return transformed_clip.get_frame(0)
        
        return clip.fl(animated_3d_frame)
