"""
Motion Tracking System for PyVideoEditor
Provides object tracking, video stabilization, match moving, and 2D planar tracking
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from typing import Optional, Tuple, List, Dict, Any, Union
from dataclasses import dataclass
import json

try:
    from moviepy.editor import VideoFileClip, ImageSequenceClip
except ImportError:
    from moviepy import VideoFileClip, ImageSequenceClip

@dataclass
class TrackingPoint:
    """Represents a tracking point with coordinates and confidence"""
    x: float
    y: float
    confidence: float = 1.0
    frame_number: int = 0

@dataclass
class TrackingData:
    """Container for tracking data across frames"""
    points: List[TrackingPoint]
    roi: Tuple[int, int, int, int]  # x, y, width, height
    tracker_type: str
    is_valid: bool = True

class ObjectTracker:
    """Single object tracking using various OpenCV trackers"""
    
    def __init__(self, tracker_type: str = "CSRT"):
        self.tracker_type = tracker_type
        self.tracker = None
        self.initialized = False
        self.tracking_data = None
        
        # Available tracker types
        self.tracker_types = {
            "BOOSTING": cv2.TrackerBoosting_create,
            "MIL": cv2.TrackerMIL_create,
            "KCF": cv2.TrackerKCF_create,
            "TLD": cv2.TrackerTLD_create,
            "MEDIANFLOW": cv2.TrackerMedianFlow_create,
            "GOTURN": cv2.TrackerGOTURN_create,
            "MOSSE": cv2.TrackerMOSSE_create,
            "CSRT": cv2.TrackerCSRT_create
        }
    
    def initialize_tracker(self, frame: np.ndarray, roi: Tuple[int, int, int, int]) -> bool:
        """Initialize tracker with first frame and ROI"""
        try:
            if self.tracker_type in self.tracker_types:
                self.tracker = self.tracker_types[self.tracker_type]()
            else:
                print(f"Unknown tracker type: {self.tracker_type}")
                return False
            
            # Convert frame to grayscale if needed
            if len(frame.shape) == 3:
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            else:
                gray_frame = frame
            
            success = self.tracker.init(gray_frame, roi)
            
            if success:
                self.initialized = True
                self.tracking_data = TrackingData(
                    points=[TrackingPoint(roi[0] + roi[2]/2, roi[1] + roi[3]/2, 1.0, 0)],
                    roi=roi,
                    tracker_type=self.tracker_type
                )
                return True
            
        except Exception as e:
            print(f"Error initializing tracker: {e}")
        
        return False
    
    def update(self, frame: np.ndarray, frame_number: int) -> Optional[TrackingPoint]:
        """Update tracker with new frame"""
        if not self.initialized or self.tracker is None:
            return None
        
        try:
            # Convert frame to grayscale if needed
            if len(frame.shape) == 3:
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            else:
                gray_frame = frame
            
            success, bbox = self.tracker.update(gray_frame)
            
            if success:
                x, y, w, h = bbox
                center_x = x + w / 2
                center_y = y + h / 2
                
                # Simple confidence measure based on bbox size consistency
                expected_area = self.tracking_data.roi[2] * self.tracking_data.roi[3]
                current_area = w * h
                confidence = min(1.0, expected_area / max(current_area, 1))
                
                point = TrackingPoint(center_x, center_y, confidence, frame_number)
                self.tracking_data.points.append(point)
                self.tracking_data.roi = (int(x), int(y), int(w), int(h))
                
                return point
            else:
                self.tracking_data.is_valid = False
                
        except Exception as e:
            print(f"Error updating tracker: {e}")
            self.tracking_data.is_valid = False
        
        return None

class MultiObjectTracker:
    """Track multiple objects simultaneously"""
    
    def __init__(self):
        self.trackers: Dict[str, ObjectTracker] = {}
        self.next_id = 0
    
    def add_tracker(self, frame: np.ndarray, roi: Tuple[int, int, int, int], 
                   tracker_type: str = "CSRT", track_id: str = None) -> str:
        """Add a new tracker for an object"""
        if track_id is None:
            track_id = f"track_{self.next_id}"
            self.next_id += 1
        
        tracker = ObjectTracker(tracker_type)
        if tracker.initialize_tracker(frame, roi):
            self.trackers[track_id] = tracker
            return track_id
        
        return None
    
    def update_all(self, frame: np.ndarray, frame_number: int) -> Dict[str, TrackingPoint]:
        """Update all trackers with new frame"""
        results = {}
        
        for track_id, tracker in self.trackers.items():
            point = tracker.update(frame, frame_number)
            if point:
                results[track_id] = point
        
        return results
    
    def remove_tracker(self, track_id: str):
        """Remove a tracker"""
        if track_id in self.trackers:
            del self.trackers[track_id]
    
    def get_tracking_data(self, track_id: str) -> Optional[TrackingData]:
        """Get tracking data for a specific tracker"""
        if track_id in self.trackers:
            return self.trackers[track_id].tracking_data
        return None

class VideoStabilizer:
    """Video stabilization using optical flow and homography"""
    
    def __init__(self):
        self.transforms = []
        self.trajectory = []
        self.smoothed_trajectory = []
        self.smoothing_radius = 30
        
        # Feature detection parameters
        self.feature_params = dict(
            maxCorners=200,
            qualityLevel=0.01,
            minDistance=30,
            blockSize=3
        )
        
        # Lucas-Kanade parameters
        self.lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )
    
    def detect_motion(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> Optional[np.ndarray]:
        """Detect motion between two frames using optical flow"""
        try:
            # Convert to grayscale
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_RGB2GRAY) if len(prev_frame.shape) == 3 else prev_frame
            curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_RGB2GRAY) if len(curr_frame.shape) == 3 else curr_frame
            
            # Detect features in previous frame
            prev_pts = cv2.goodFeaturesToTrack(prev_gray, mask=None, **self.feature_params)
            
            if prev_pts is None or len(prev_pts) < 10:
                return None
            
            # Calculate optical flow
            curr_pts, status, error = cv2.calcOpticalFlowPyrLK(
                prev_gray, curr_gray, prev_pts, None, **self.lk_params
            )
            
            # Filter good points
            good_prev = prev_pts[status == 1]
            good_curr = curr_pts[status == 1]
            
            if len(good_prev) < 10:
                return None
            
            # Find transformation matrix
            transform = cv2.estimateAffinePartial2D(good_prev, good_curr)[0]
            
            return transform
            
        except Exception as e:
            print(f"Error detecting motion: {e}")
            return None
    
    def analyze_video(self, frames: List[np.ndarray]) -> bool:
        """Analyze entire video for stabilization"""
        if len(frames) < 2:
            return False
        
        self.transforms = []
        self.trajectory = []
        
        try:
            for i in range(1, len(frames)):
                transform = self.detect_motion(frames[i-1], frames[i])
                
                if transform is not None:
                    # Extract translation and rotation
                    dx = transform[0, 2]
                    dy = transform[1, 2]
                    da = np.arctan2(transform[1, 0], transform[0, 0])
                    
                    self.transforms.append([dx, dy, da])
                    
                    # Calculate trajectory
                    if len(self.trajectory) == 0:
                        self.trajectory.append([dx, dy, da])
                    else:
                        x = self.trajectory[-1][0] + dx
                        y = self.trajectory[-1][1] + dy
                        a = self.trajectory[-1][2] + da
                        self.trajectory.append([x, y, a])
                else:
                    # Use previous transform if detection fails
                    if len(self.transforms) > 0:
                        self.transforms.append(self.transforms[-1])
                        self.trajectory.append(self.trajectory[-1])
                    else:
                        self.transforms.append([0, 0, 0])
                        self.trajectory.append([0, 0, 0])
            
            # Smooth trajectory
            self._smooth_trajectory()
            return True
            
        except Exception as e:
            print(f"Error analyzing video: {e}")
            return False
    
    def _smooth_trajectory(self):
        """Smooth the camera trajectory"""
        self.smoothed_trajectory = []
        
        for i in range(len(self.trajectory)):
            # Calculate smoothing window
            start = max(0, i - self.smoothing_radius)
            end = min(len(self.trajectory), i + self.smoothing_radius + 1)
            
            # Calculate average
            smooth_x = np.mean([self.trajectory[j][0] for j in range(start, end)])
            smooth_y = np.mean([self.trajectory[j][1] for j in range(start, end)])
            smooth_a = np.mean([self.trajectory[j][2] for j in range(start, end)])
            
            self.smoothed_trajectory.append([smooth_x, smooth_y, smooth_a])
    
    def stabilize_frame(self, frame: np.ndarray, frame_index: int) -> np.ndarray:
        """Apply stabilization to a single frame"""
        if frame_index >= len(self.transforms) or frame_index >= len(self.smoothed_trajectory):
            return frame
        
        try:
            h, w = frame.shape[:2]
            
            # Calculate difference between smoothed and original trajectory
            diff_x = self.smoothed_trajectory[frame_index][0] - self.trajectory[frame_index][0]
            diff_y = self.smoothed_trajectory[frame_index][1] - self.trajectory[frame_index][1]
            diff_a = self.smoothed_trajectory[frame_index][2] - self.trajectory[frame_index][2]
            
            # Create transformation matrix
            dx = self.transforms[frame_index][0] + diff_x
            dy = self.transforms[frame_index][1] + diff_y
            da = self.transforms[frame_index][2] + diff_a
            
            # Build transformation matrix
            transform_matrix = np.array([
                [np.cos(da), -np.sin(da), dx],
                [np.sin(da), np.cos(da), dy]
            ], dtype=np.float32)
            
            # Apply transformation
            stabilized_frame = cv2.warpAffine(frame, transform_matrix, (w, h))
            
            # Crop borders to remove black edges
            crop_percent = 0.05
            crop_x = int(w * crop_percent)
            crop_y = int(h * crop_percent)
            
            stabilized_frame = stabilized_frame[
                crop_y:h-crop_y,
                crop_x:w-crop_x
            ]
            
            # Resize back to original dimensions
            stabilized_frame = cv2.resize(stabilized_frame, (w, h))
            
            return stabilized_frame
            
        except Exception as e:
            print(f"Error stabilizing frame: {e}")
            return frame

class PlanarTracker:
    """2D planar tracking for match moving and compositing"""
    
    def __init__(self):
        self.reference_points = None
        self.reference_frame = None
        self.tracked_points = []
        self.homographies = []
        
        # ORB feature detector
        self.detector = cv2.ORB_create(nfeatures=1000)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    
    def set_reference_plane(self, frame: np.ndarray, corners: List[Tuple[int, int]]):
        """Set reference plane using four corner points"""
        self.reference_frame = frame.copy()
        self.reference_points = np.array(corners, dtype=np.float32)
        
        # Detect features in reference frame
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY) if len(frame.shape) == 3 else frame
        keypoints, descriptors = self.detector.detectAndCompute(gray, None)
        
        self.reference_keypoints = keypoints
        self.reference_descriptors = descriptors
    
    def track_plane(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Track the plane in current frame"""
        if self.reference_frame is None:
            return None
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY) if len(frame.shape) == 3 else frame
            
            # Detect features in current frame
            keypoints, descriptors = self.detector.detectAndCompute(gray, None)
            
            if descriptors is None or len(descriptors) < 10:
                return None
            
            # Match features
            matches = self.matcher.match(self.reference_descriptors, descriptors)
            matches = sorted(matches, key=lambda x: x.distance)
            
            if len(matches) < 10:
                return None
            
            # Extract matched points
            src_pts = np.float32([
                self.reference_keypoints[m.queryIdx].pt for m in matches
            ]).reshape(-1, 1, 2)
            
            dst_pts = np.float32([
                keypoints[m.trainIdx].pt for m in matches
            ]).reshape(-1, 1, 2)
            
            # Find homography
            homography, mask = cv2.findHomography(
                src_pts, dst_pts, cv2.RANSAC, 5.0
            )
            
            if homography is not None:
                self.homographies.append(homography)
                return homography
            
        except Exception as e:
            print(f"Error tracking plane: {e}")
        
        return None
    
    def get_tracked_corners(self, homography: np.ndarray) -> Optional[np.ndarray]:
        """Get transformed corner points using homography"""
        if homography is None or self.reference_points is None:
            return None
        
        try:
            # Transform reference points using homography
            tracked_corners = cv2.perspectiveTransform(
                self.reference_points.reshape(-1, 1, 2), homography
            )
            return tracked_corners.reshape(-1, 2)
            
        except Exception as e:
            print(f"Error getting tracked corners: {e}")
            return None

class MatchMover:
    """Match moving for 3D tracking and compositing"""
    
    def __init__(self):
        self.camera_matrix = None
        self.dist_coeffs = None
        self.tracked_points_3d = []
        self.tracked_points_2d = []
        self.camera_poses = []
    
    def set_camera_parameters(self, camera_matrix: np.ndarray, dist_coeffs: np.ndarray):
        """Set camera calibration parameters"""
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
    
    def estimate_camera_pose(self, object_points_3d: np.ndarray, 
                           image_points_2d: np.ndarray) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Estimate camera pose using PnP"""
        if self.camera_matrix is None:
            return None
        
        try:
            success, rvec, tvec = cv2.solvePnP(
                object_points_3d,
                image_points_2d,
                self.camera_matrix,
                self.dist_coeffs
            )
            
            if success:
                return rvec, tvec
            
        except Exception as e:
            print(f"Error estimating camera pose: {e}")
        
        return None
    
    def project_3d_point(self, point_3d: np.ndarray, rvec: np.ndarray, 
                        tvec: np.ndarray) -> Optional[np.ndarray]:
        """Project 3D point to 2D image coordinates"""
        if self.camera_matrix is None:
            return None
        
        try:
            projected_points, _ = cv2.projectPoints(
                point_3d.reshape(-1, 1, 3),
                rvec,
                tvec,
                self.camera_matrix,
                self.dist_coeffs
            )
            
            return projected_points.reshape(-1, 2)
            
        except Exception as e:
            print(f"Error projecting 3D point: {e}")
            return None

class MotionTrackingVisualizer(FigureCanvas):
    """Visualization widget for motion tracking data"""
    
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.figure)
        self.setParent(parent)
        
        self.axes = self.figure.add_subplot(111)
        self.setup_plot()
    
    def setup_plot(self):
        """Setup the plot"""
        self.axes.set_facecolor('black')
        self.figure.patch.set_facecolor('black')
        self.axes.set_title('Motion Tracking', color='white')
        self.axes.set_xlabel('Frame Number', color='white')
        self.axes.set_ylabel('Position', color='white')
        self.axes.tick_params(colors='white')
        self.axes.grid(True, alpha=0.3)
    
    def plot_tracking_data(self, tracking_data: TrackingData):
        """Plot tracking data"""
        self.axes.clear()
        self.setup_plot()
        
        if not tracking_data.points:
            return
        
        # Extract data
        frames = [p.frame_number for p in tracking_data.points]
        x_positions = [p.x for p in tracking_data.points]
        y_positions = [p.y for p in tracking_data.points]
        confidences = [p.confidence for p in tracking_data.points]
        
        # Plot trajectories
        self.axes.plot(frames, x_positions, 'r-', label='X Position', alpha=0.8)
        self.axes.plot(frames, y_positions, 'g-', label='Y Position', alpha=0.8)
        
        # Plot confidence
        ax2 = self.axes.twinx()
        ax2.plot(frames, confidences, 'b--', label='Confidence', alpha=0.6)
        ax2.set_ylabel('Confidence', color='white')
        ax2.tick_params(colors='white')
        
        self.axes.legend(loc='upper left')
        ax2.legend(loc='upper right')
        
        self.draw()
    
    def plot_stabilization_data(self, original_trajectory: List, smoothed_trajectory: List):
        """Plot stabilization data"""
        self.axes.clear()
        self.setup_plot()
        
        if not original_trajectory or not smoothed_trajectory:
            return
        
        frames = list(range(len(original_trajectory)))
        
        # Extract x, y movements
        orig_x = [t[0] for t in original_trajectory]
        orig_y = [t[1] for t in original_trajectory]
        smooth_x = [t[0] for t in smoothed_trajectory]
        smooth_y = [t[1] for t in smoothed_trajectory]
        
        # Plot trajectories
        self.axes.plot(frames, orig_x, 'r-', alpha=0.5, label='Original X')
        self.axes.plot(frames, orig_y, 'g-', alpha=0.5, label='Original Y')
        self.axes.plot(frames, smooth_x, 'r--', linewidth=2, label='Smoothed X')
        self.axes.plot(frames, smooth_y, 'g--', linewidth=2, label='Smoothed Y')
        
        self.axes.legend()
        self.draw()

class MotionTrackingSystem:
    """Main motion tracking system combining all tracking methods"""
    
    def __init__(self):
        self.object_tracker = MultiObjectTracker()
        self.stabilizer = VideoStabilizer()
        self.planar_tracker = PlanarTracker()
        self.match_mover = MatchMover()
        self.visualizer = None
    
    def set_visualizer(self, visualizer: MotionTrackingVisualizer):
        """Set visualization widget"""
        self.visualizer = visualizer
    
    def track_objects_in_video(self, clip: VideoFileClip, tracking_regions: List[Dict]) -> Dict[str, TrackingData]:
        """Track multiple objects throughout a video"""
        results = {}
        
        try:
            # Get frames
            frames = []
            for t in np.arange(0, clip.duration, 1.0/clip.fps):
                frame = clip.get_frame(t)
                frames.append(frame)
            
            # Initialize trackers
            track_ids = []
            for i, region in enumerate(tracking_regions):
                roi = region['roi']  # (x, y, width, height)
                tracker_type = region.get('tracker_type', 'CSRT')
                
                track_id = self.object_tracker.add_tracker(
                    frames[0], roi, tracker_type
                )
                if track_id:
                    track_ids.append(track_id)
            
            # Track through all frames
            for frame_num, frame in enumerate(frames[1:], 1):
                self.object_tracker.update_all(frame, frame_num)
            
            # Collect results
            for track_id in track_ids:
                tracking_data = self.object_tracker.get_tracking_data(track_id)
                if tracking_data:
                    results[track_id] = tracking_data
            
        except Exception as e:
            print(f"Error tracking objects: {e}")
        
        return results
    
    def stabilize_video(self, clip: VideoFileClip) -> Optional[VideoFileClip]:
        """Stabilize a video clip"""
        try:
            # Extract frames
            frames = []
            for t in np.arange(0, clip.duration, 1.0/clip.fps):
                frame = clip.get_frame(t)
                frames.append(frame)
            
            # Analyze for stabilization
            if not self.stabilizer.analyze_video(frames):
                print("Failed to analyze video for stabilization")
                return None
            
            # Apply stabilization
            stabilized_frames = []
            for i, frame in enumerate(frames):
                stabilized_frame = self.stabilizer.stabilize_frame(frame, i)
                stabilized_frames.append(stabilized_frame)
            
            # Create new clip from stabilized frames
            stabilized_clip = ImageSequenceClip(stabilized_frames, fps=clip.fps)
            
            # Copy audio if present
            if clip.audio:
                stabilized_clip = stabilized_clip.set_audio(clip.audio)
            
            return stabilized_clip
            
        except Exception as e:
            print(f"Error stabilizing video: {e}")
            return None
    
    def track_planar_surface(self, clip: VideoFileClip, reference_corners: List[Tuple[int, int]]) -> List[np.ndarray]:
        """Track a planar surface throughout the video"""
        homographies = []
        
        try:
            # Get first frame and set reference
            first_frame = clip.get_frame(0)
            self.planar_tracker.set_reference_plane(first_frame, reference_corners)
            
            # Track through all frames
            for t in np.arange(1.0/clip.fps, clip.duration, 1.0/clip.fps):
                frame = clip.get_frame(t)
                homography = self.planar_tracker.track_plane(frame)
                homographies.append(homography)
            
        except Exception as e:
            print(f"Error tracking planar surface: {e}")
        
        return homographies
    
    def save_tracking_data(self, tracking_data: Dict[str, TrackingData], filepath: str):
        """Save tracking data to file"""
        try:
            data_to_save = {}
            
            for track_id, data in tracking_data.items():
                data_to_save[track_id] = {
                    'points': [
                        {
                            'x': p.x,
                            'y': p.y,
                            'confidence': p.confidence,
                            'frame_number': p.frame_number
                        }
                        for p in data.points
                    ],
                    'roi': data.roi,
                    'tracker_type': data.tracker_type,
                    'is_valid': data.is_valid
                }
            
            with open(filepath, 'w') as f:
                json.dump(data_to_save, f, indent=2)
                
        except Exception as e:
            print(f"Error saving tracking data: {e}")
    
    def load_tracking_data(self, filepath: str) -> Dict[str, TrackingData]:
        """Load tracking data from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            results = {}
            for track_id, track_data in data.items():
                points = []
                for p in track_data['points']:
                    points.append(TrackingPoint(
                        x=p['x'],
                        y=p['y'],
                        confidence=p['confidence'],
                        frame_number=p['frame_number']
                    ))
                
                results[track_id] = TrackingData(
                    points=points,
                    roi=tuple(track_data['roi']),
                    tracker_type=track_data['tracker_type'],
                    is_valid=track_data['is_valid']
                )
            
            return results
            
        except Exception as e:
            print(f"Error loading tracking data: {e}")
            return {}
