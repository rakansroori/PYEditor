"""
Enhanced Color Grading Suite for PyVideoEditor
Provides professional color correction tools including color wheels, LUTs, 
vectorscope, histogram, secondary color correction, and masking
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from typing import Optional, Tuple, List, Dict, Any
import os
import json
from scipy import interpolate
from scipy.ndimage import gaussian_filter

try:
    from moviepy.editor import VideoFileClip
except ImportError:
    from moviepy import VideoFileClip

class ColorWheels:
    """Professional color wheels for lift, gamma, and gain adjustments"""
    
    def __init__(self):
        self.lift = {'red': 0.0, 'green': 0.0, 'blue': 0.0, 'master': 0.0}
        self.gamma = {'red': 1.0, 'green': 1.0, 'blue': 1.0, 'master': 1.0}
        self.gain = {'red': 1.0, 'green': 1.0, 'blue': 1.0, 'master': 1.0}
    
    def apply_color_wheels(self, frame: np.ndarray) -> np.ndarray:
        """Apply color wheel adjustments to a frame"""
        # Convert to float for processing
        frame_float = frame.astype(np.float32) / 255.0
        
        # Apply lift (shadows)
        lift_adjustment = np.array([
            self.lift['red'] + self.lift['master'],
            self.lift['green'] + self.lift['master'],
            self.lift['blue'] + self.lift['master']
        ]) * 0.01  # Scale to reasonable range
        
        frame_float = frame_float + lift_adjustment
        
        # Apply gamma (midtones)
        gamma_values = np.array([
            self.gamma['red'] * self.gamma['master'],
            self.gamma['green'] * self.gamma['master'],
            self.gamma['blue'] * self.gamma['master']
        ])
        
        # Avoid division by zero
        gamma_values = np.maximum(gamma_values, 0.01)
        frame_float = np.power(frame_float, 1.0 / gamma_values)
        
        # Apply gain (highlights)
        gain_values = np.array([
            self.gain['red'] * self.gain['master'],
            self.gain['green'] * self.gain['master'],
            self.gain['blue'] * self.gain['master']
        ])
        
        frame_float = frame_float * gain_values
        
        # Clamp and convert back to uint8
        frame_float = np.clip(frame_float, 0.0, 1.0)
        return (frame_float * 255).astype(np.uint8)

class LUTManager:
    """Manages Look-Up Tables for color grading"""
    
    def __init__(self):
        self.luts = {}
        self.current_lut = None
    
    def load_lut_from_file(self, filepath: str, name: str = None) -> bool:
        """Load LUT from various file formats (.cube, .3dl, etc.)"""
        try:
            if name is None:
                name = os.path.splitext(os.path.basename(filepath))[0]
            
            if filepath.lower().endswith('.cube'):
                lut = self._load_cube_lut(filepath)
            elif filepath.lower().endswith('.3dl'):
                lut = self._load_3dl_lut(filepath)
            else:
                print(f"Unsupported LUT format: {filepath}")
                return False
            
            self.luts[name] = lut
            return True
            
        except Exception as e:
            print(f"Error loading LUT: {e}")
            return False
    
    def _load_cube_lut(self, filepath: str) -> np.ndarray:
        """Load .cube format LUT"""
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        # Parse header
        size = 32  # Default size
        data_lines = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('LUT_3D_SIZE'):
                size = int(line.split()[-1])
            elif line and not line.startswith('#') and not line.startswith('TITLE'):
                try:
                    values = [float(x) for x in line.split()]
                    if len(values) == 3:
                        data_lines.append(values)
                except ValueError:
                    continue
        
        # Build 3D LUT
        lut = np.array(data_lines).reshape((size, size, size, 3))
        return lut
    
    def _load_3dl_lut(self, filepath: str) -> np.ndarray:
        """Load .3dl format LUT"""
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        data_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                try:
                    values = [float(x) for x in line.split()]
                    if len(values) == 3:
                        data_lines.append(values)
                except ValueError:
                    continue
        
        # Assume 32x32x32 for 3dl files
        size = int(round(len(data_lines) ** (1/3)))
        lut = np.array(data_lines).reshape((size, size, size, 3))
        return lut
    
    def apply_lut(self, frame: np.ndarray, lut_name: str) -> np.ndarray:
        """Apply a loaded LUT to a frame"""
        if lut_name not in self.luts:
            return frame
        
        lut = self.luts[lut_name]
        return self._interpolate_lut(frame, lut)
    
    def _interpolate_lut(self, frame: np.ndarray, lut: np.ndarray) -> np.ndarray:
        """Interpolate LUT values for frame pixels"""
        frame_float = frame.astype(np.float32) / 255.0
        lut_size = lut.shape[0]
        
        # Scale frame values to LUT coordinates
        coords = frame_float * (lut_size - 1)
        
        # Get integer and fractional parts
        coords_int = coords.astype(np.int32)
        coords_frac = coords - coords_int
        
        # Clamp coordinates
        coords_int = np.clip(coords_int, 0, lut_size - 2)
        
        # Trilinear interpolation
        result = np.zeros_like(frame_float)
        
        for r in range(2):
            for g in range(2):
                for b in range(2):
                    # Get LUT values at 8 corners of the cube
                    lut_coords = (
                        coords_int[:, :, 0] + r,
                        coords_int[:, :, 1] + g,
                        coords_int[:, :, 2] + b
                    )
                    
                    # Weights for trilinear interpolation
                    weight = (
                        (1 - r + (2 * r - 1) * coords_frac[:, :, 0]) *
                        (1 - g + (2 * g - 1) * coords_frac[:, :, 1]) *
                        (1 - b + (2 * b - 1) * coords_frac[:, :, 2])
                    )
                    
                    # Add weighted contribution
                    lut_values = lut[lut_coords]
                    result += weight[:, :, np.newaxis] * lut_values
        
        return np.clip(result * 255, 0, 255).astype(np.uint8)

class Vectorscope(FigureCanvas):
    """Vectorscope for analyzing color balance and saturation"""
    
    def __init__(self, parent=None, width=4, height=4, dpi=100):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.figure)
        self.setParent(parent)
        
        self.axes = self.figure.add_subplot(111, projection='polar')
        self.setup_vectorscope()
    
    def setup_vectorscope(self):
        """Setup vectorscope display"""
        self.axes.set_facecolor('black')
        self.figure.patch.set_facecolor('black')
        
        # Add color targets
        targets = {
            'Red': (0, 1),
            'Yellow': (np.pi/3, 1),
            'Green': (2*np.pi/3, 1),
            'Cyan': (np.pi, 1),
            'Blue': (4*np.pi/3, 1),
            'Magenta': (5*np.pi/3, 1)
        }
        
        for name, (angle, radius) in targets.items():
            self.axes.plot(angle, radius, 'o', markersize=8, 
                          color=name.lower() if name.lower() in ['red', 'yellow', 'green', 'cyan', 'blue', 'magenta'] else 'white')
            self.axes.text(angle, radius + 0.1, name, ha='center', va='center', color='white', fontsize=8)
        
        self.axes.set_ylim(0, 1.2)
        self.axes.set_title('Vectorscope', color='white', pad=20)
        self.axes.grid(True, alpha=0.3)
    
    def update_vectorscope(self, frame: np.ndarray):
        """Update vectorscope with frame data"""
        # Clear previous data (keep targets)
        self.axes.clear()
        self.setup_vectorscope()
        
        # Convert to YUV for vectorscope analysis
        yuv = cv2.cvtColor(frame, cv2.COLOR_RGB2YUV)
        u = yuv[:, :, 1].flatten()
        v = yuv[:, :, 2].flatten()
        
        # Convert U,V to polar coordinates
        # Center U,V around 128 (neutral)
        u_centered = (u - 128) / 128.0
        v_centered = (v - 128) / 128.0
        
        # Calculate magnitude and angle
        magnitude = np.sqrt(u_centered**2 + v_centered**2)
        angle = np.arctan2(v_centered, u_centered)
        
        # Sample subset for performance
        sample_size = min(10000, len(magnitude))
        indices = np.random.choice(len(magnitude), sample_size, replace=False)
        
        magnitude_sample = magnitude[indices]
        angle_sample = angle[indices]
        
        # Plot vectorscope data
        self.axes.scatter(angle_sample, magnitude_sample, s=1, alpha=0.6, c='cyan')
        
        self.draw()

class Histogram(FigureCanvas):
    """RGB and Luma histogram for exposure analysis"""
    
    def __init__(self, parent=None, width=6, height=3, dpi=100):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.figure)
        self.setParent(parent)
        
        self.axes = self.figure.add_subplot(111)
        self.setup_histogram()
    
    def setup_histogram(self):
        """Setup histogram display"""
        self.axes.set_facecolor('black')
        self.figure.patch.set_facecolor('black')
        self.axes.set_title('RGB Histogram', color='white')
        self.axes.set_xlabel('Pixel Value', color='white')
        self.axes.set_ylabel('Count', color='white')
        self.axes.tick_params(colors='white')
        self.axes.grid(True, alpha=0.3)
    
    def update_histogram(self, frame: np.ndarray):
        """Update histogram with frame data"""
        self.axes.clear()
        self.setup_histogram()
        
        # Calculate histograms for R, G, B channels
        colors = ['red', 'green', 'blue']
        for i, color in enumerate(colors):
            hist, bins = np.histogram(frame[:, :, i], bins=256, range=(0, 256))
            self.axes.plot(bins[:-1], hist, color=color, alpha=0.7, linewidth=1)
        
        # Calculate and plot luma histogram
        luma = 0.299 * frame[:, :, 0] + 0.587 * frame[:, :, 1] + 0.114 * frame[:, :, 2]
        hist_luma, bins_luma = np.histogram(luma, bins=256, range=(0, 256))
        self.axes.plot(bins_luma[:-1], hist_luma, color='white', alpha=0.8, linewidth=2, label='Luma')
        
        self.axes.legend()
        self.axes.set_xlim(0, 255)
        self.draw()

class SecondaryColorCorrection:
    """Tools for selective color correction"""
    
    def __init__(self):
        self.masks = {}
    
    def create_color_mask(self, frame: np.ndarray, target_color: Tuple[int, int, int], 
                         tolerance: float = 30.0, softness: float = 10.0) -> np.ndarray:
        """Create a mask for a specific color range"""
        # Convert to HSV for better color selection
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        target_hsv = cv2.cvtColor(np.uint8([[target_color]]), cv2.COLOR_RGB2HSV)[0][0]
        
        # Define range around target color
        h_tolerance = tolerance / 2
        lower_bound = np.array([
            max(0, target_hsv[0] - h_tolerance),
            50,  # Minimum saturation
            50   # Minimum value
        ])
        upper_bound = np.array([
            min(179, target_hsv[0] + h_tolerance),
            255,
            255
        ])
        
        # Create mask
        mask = cv2.inRange(hsv, lower_bound, upper_bound)
        
        # Apply softness (blur the mask edges)
        if softness > 0:
            kernel_size = int(softness * 2) + 1
            mask = cv2.GaussianBlur(mask, (kernel_size, kernel_size), softness)
        
        return mask / 255.0  # Normalize to 0-1 range
    
    def create_luma_mask(self, frame: np.ndarray, luma_range: Tuple[float, float], 
                        softness: float = 10.0) -> np.ndarray:
        """Create a mask based on luminance values"""
        # Calculate luma
        luma = 0.299 * frame[:, :, 0] + 0.587 * frame[:, :, 1] + 0.114 * frame[:, :, 2]
        
        # Create mask for luma range
        min_luma, max_luma = luma_range
        mask = np.logical_and(luma >= min_luma, luma <= max_luma).astype(np.float32)
        
        # Apply softness
        if softness > 0:
            mask = gaussian_filter(mask, sigma=softness/3.0)
        
        return mask
    
    def apply_selective_adjustment(self, frame: np.ndarray, mask: np.ndarray, 
                                 adjustment_func, **kwargs) -> np.ndarray:
        """Apply an adjustment only to masked areas"""
        # Apply adjustment to entire frame
        adjusted_frame = adjustment_func(frame, **kwargs)
        
        # Blend original and adjusted based on mask
        mask_3d = np.stack([mask, mask, mask], axis=2)
        result = frame * (1 - mask_3d) + adjusted_frame * mask_3d
        
        return result.astype(np.uint8)

class AdvancedColorGrading:
    """Main class for advanced color grading operations"""
    
    def __init__(self):
        self.color_wheels = ColorWheels()
        self.lut_manager = LUTManager()
        self.secondary_cc = SecondaryColorCorrection()
        
        # Color correction parameters
        self.exposure = 0.0
        self.contrast = 1.0
        self.highlights = 0.0
        self.shadows = 0.0
        self.whites = 0.0
        self.blacks = 0.0
        self.clarity = 0.0
        self.vibrance = 0.0
        self.saturation = 1.0
        
        # Curve adjustments
        self.curves = {
            'master': np.linspace(0, 1, 256),
            'red': np.linspace(0, 1, 256),
            'green': np.linspace(0, 1, 256),
            'blue': np.linspace(0, 1, 256)
        }
    
    def apply_basic_corrections(self, frame: np.ndarray) -> np.ndarray:
        """Apply basic color corrections"""
        frame_float = frame.astype(np.float32) / 255.0
        
        # Exposure adjustment
        if self.exposure != 0:
            exposure_factor = 2 ** self.exposure
            frame_float = frame_float * exposure_factor
        
        # Contrast adjustment
        if self.contrast != 1.0:
            frame_float = (frame_float - 0.5) * self.contrast + 0.5
        
        # Highlights and shadows
        if self.highlights != 0 or self.shadows != 0:
            # Simple tone mapping
            luma = 0.299 * frame_float[:, :, 0] + 0.587 * frame_float[:, :, 1] + 0.114 * frame_float[:, :, 2]
            
            # Highlights (bright areas)
            highlight_mask = np.clip((luma - 0.7) / 0.3, 0, 1)
            highlight_adjustment = self.highlights * 0.01
            
            # Shadows (dark areas)
            shadow_mask = np.clip((0.3 - luma) / 0.3, 0, 1)
            shadow_adjustment = self.shadows * 0.01
            
            # Apply adjustments
            for i in range(3):
                frame_float[:, :, i] += highlight_mask * highlight_adjustment
                frame_float[:, :, i] += shadow_mask * shadow_adjustment
        
        # Whites and blacks (simple implementation)
        if self.whites != 0:
            white_adjustment = self.whites * 0.01
            frame_float = frame_float + white_adjustment
        
        if self.blacks != 0:
            black_adjustment = self.blacks * 0.01
            frame_float = frame_float * (1 + black_adjustment)
        
        # Saturation adjustment
        if self.saturation != 1.0:
            # Convert to HSV for saturation adjustment
            frame_hsv = cv2.cvtColor((frame_float * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
            frame_hsv[:, :, 1] = np.clip(frame_hsv[:, :, 1] * self.saturation, 0, 255)
            frame_float = cv2.cvtColor(frame_hsv, cv2.COLOR_HSV2RGB).astype(np.float32) / 255.0
        
        # Clamp values
        frame_float = np.clip(frame_float, 0.0, 1.0)
        return (frame_float * 255).astype(np.uint8)
    
    def apply_curves(self, frame: np.ndarray) -> np.ndarray:
        """Apply tone curves to frame"""
        frame_float = frame.astype(np.float32) / 255.0
        
        # Apply master curve
        if not np.array_equal(self.curves['master'], np.linspace(0, 1, 256)):
            for i in range(3):
                frame_float[:, :, i] = np.interp(frame_float[:, :, i], 
                                               np.linspace(0, 1, 256), 
                                               self.curves['master'])
        
        # Apply individual color curves
        color_names = ['red', 'green', 'blue']
        for i, color in enumerate(color_names):
            if not np.array_equal(self.curves[color], np.linspace(0, 1, 256)):
                frame_float[:, :, i] = np.interp(frame_float[:, :, i], 
                                               np.linspace(0, 1, 256), 
                                               self.curves[color])
        
        return np.clip(frame_float * 255, 0, 255).astype(np.uint8)
    
    def apply_full_grade(self, clip: VideoFileClip, lut_name: str = None) -> VideoFileClip:
        """Apply complete color grading to a video clip"""
        def grade_frame(frame):
            # Apply basic corrections
            graded_frame = self.apply_basic_corrections(frame)
            
            # Apply color wheels
            graded_frame = self.color_wheels.apply_color_wheels(graded_frame)
            
            # Apply curves
            graded_frame = self.apply_curves(graded_frame)
            
            # Apply LUT if specified
            if lut_name and lut_name in self.lut_manager.luts:
                graded_frame = self.lut_manager.apply_lut(graded_frame, lut_name)
            
            return graded_frame
        
        return clip.fl_image(grade_frame)
    
    def save_grade_preset(self, filepath: str, name: str = "Custom Grade"):
        """Save current grading settings as a preset"""
        preset = {
            'name': name,
            'color_wheels': {
                'lift': self.color_wheels.lift,
                'gamma': self.color_wheels.gamma,
                'gain': self.color_wheels.gain
            },
            'basic_corrections': {
                'exposure': self.exposure,
                'contrast': self.contrast,
                'highlights': self.highlights,
                'shadows': self.shadows,
                'whites': self.whites,
                'blacks': self.blacks,
                'clarity': self.clarity,
                'vibrance': self.vibrance,
                'saturation': self.saturation
            },
            'curves': {
                'master': self.curves['master'].tolist(),
                'red': self.curves['red'].tolist(),
                'green': self.curves['green'].tolist(),
                'blue': self.curves['blue'].tolist()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(preset, f, indent=2)
    
    def load_grade_preset(self, filepath: str) -> bool:
        """Load grading settings from a preset file"""
        try:
            with open(filepath, 'r') as f:
                preset = json.load(f)
            
            # Load color wheels
            if 'color_wheels' in preset:
                cw = preset['color_wheels']
                self.color_wheels.lift = cw.get('lift', self.color_wheels.lift)
                self.color_wheels.gamma = cw.get('gamma', self.color_wheels.gamma)
                self.color_wheels.gain = cw.get('gain', self.color_wheels.gain)
            
            # Load basic corrections
            if 'basic_corrections' in preset:
                bc = preset['basic_corrections']
                self.exposure = bc.get('exposure', 0.0)
                self.contrast = bc.get('contrast', 1.0)
                self.highlights = bc.get('highlights', 0.0)
                self.shadows = bc.get('shadows', 0.0)
                self.whites = bc.get('whites', 0.0)
                self.blacks = bc.get('blacks', 0.0)
                self.clarity = bc.get('clarity', 0.0)
                self.vibrance = bc.get('vibrance', 0.0)
                self.saturation = bc.get('saturation', 1.0)
            
            # Load curves
            if 'curves' in preset:
                curves = preset['curves']
                for curve_name in ['master', 'red', 'green', 'blue']:
                    if curve_name in curves:
                        self.curves[curve_name] = np.array(curves[curve_name])
            
            return True
            
        except Exception as e:
            print(f"Error loading preset: {e}")
            return False

class ColorGradingSuite:
    """Complete color grading suite with all tools"""
    
    def __init__(self):
        self.grading = AdvancedColorGrading()
        self.vectorscope = None
        self.histogram = None
        self.current_frame = None
    
    def set_vectorscope_widget(self, vectorscope_widget: Vectorscope):
        """Set the vectorscope widget for real-time updates"""
        self.vectorscope = vectorscope_widget
    
    def set_histogram_widget(self, histogram_widget: Histogram):
        """Set the histogram widget for real-time updates"""
        self.histogram = histogram_widget
    
    def analyze_frame(self, frame: np.ndarray):
        """Analyze frame and update scopes"""
        self.current_frame = frame
        
        if self.vectorscope:
            self.vectorscope.update_vectorscope(frame)
        
        if self.histogram:
            self.histogram.update_histogram(frame)
    
    def get_frame_statistics(self, frame: np.ndarray) -> Dict[str, Any]:
        """Get comprehensive frame statistics"""
        stats = {}
        
        # Basic statistics
        stats['mean_rgb'] = np.mean(frame, axis=(0, 1))
        stats['std_rgb'] = np.std(frame, axis=(0, 1))
        
        # Luma statistics
        luma = 0.299 * frame[:, :, 0] + 0.587 * frame[:, :, 1] + 0.114 * frame[:, :, 2]
        stats['mean_luma'] = np.mean(luma)
        stats['std_luma'] = np.std(luma)
        
        # Exposure analysis
        stats['underexposed_pixels'] = np.sum(luma < 16) / luma.size * 100
        stats['overexposed_pixels'] = np.sum(luma > 235) / luma.size * 100
        
        # Color balance
        gray_world_balance = stats['mean_rgb'] / np.mean(stats['mean_rgb'])
        stats['color_balance'] = {
            'red_bias': gray_world_balance[0] - 1.0,
            'green_bias': gray_world_balance[1] - 1.0,
            'blue_bias': gray_world_balance[2] - 1.0
        }
        
        return stats
