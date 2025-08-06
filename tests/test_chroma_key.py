import pytest
import numpy as np
import cv2
from core.chroma_key import ChromaKeyProcessor, ChromaKeyManager

class TestChromaKeyProcessor:
    def setup_method(self):
        self.processor = ChromaKeyProcessor()

    def test_initialization(self):
        """Test processor initialization"""
        assert self.processor.key_color == (0, 255, 0)  # Default green
        assert self.processor.tolerance == 40
        assert self.processor.edge_softness == 5
        assert self.processor.spill_suppression == 0.5

    def test_set_key_color(self):
        """Test setting key color"""
        blue_color = (0, 0, 255)
        self.processor.set_key_color(blue_color)
        assert self.processor.key_color == blue_color

    def test_set_tolerance(self):
        """Test setting tolerance with bounds checking"""
        self.processor.set_tolerance(50)
        assert self.processor.tolerance == 50
        
        # Test bounds
        self.processor.set_tolerance(-10)
        assert self.processor.tolerance == 0
        
        self.processor.set_tolerance(300)
        assert self.processor.tolerance == 255

    def test_set_edge_softness(self):
        """Test setting edge softness with bounds checking"""
        self.processor.set_edge_softness(10)
        assert self.processor.edge_softness == 10
        
        # Test bounds
        self.processor.set_edge_softness(-5)
        assert self.processor.edge_softness == 0
        
        self.processor.set_edge_softness(25)
        assert self.processor.edge_softness == 20

    def test_set_spill_suppression(self):
        """Test setting spill suppression with bounds checking"""
        self.processor.set_spill_suppression(0.7)
        assert self.processor.spill_suppression == 0.7
        
        # Test bounds
        self.processor.set_spill_suppression(-0.1)
        assert self.processor.spill_suppression == 0.0
        
        self.processor.set_spill_suppression(1.5)
        assert self.processor.spill_suppression == 1.0

    def test_create_mask_with_test_image(self):
        """Test mask creation with synthetic test image"""
        # Create test image: half green, half red
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        test_image[:, :50] = [0, 255, 0]  # Left half green (key color)
        test_image[:, 50:] = [255, 0, 0]  # Right half red (non-key color)
        
        mask = self.processor.create_mask(test_image)
        
        # Check mask properties
        assert mask.shape == (100, 100)
        assert mask.dtype == np.float32
        assert np.all(mask >= 0.0) and np.all(mask <= 1.0)
        
        # Left side (green) should have low values (closer to 0)
        # Right side (red) should have high values (closer to 1)
        left_avg = np.mean(mask[:, :25])  # Sample from left
        right_avg = np.mean(mask[:, 75:])  # Sample from right
        
        assert left_avg < right_avg, "Green areas should be masked out"

    def test_composite_with_background(self):
        """Test compositing with background"""
        # Create test foreground and background
        foreground = np.full((50, 50, 3), [100, 150, 200], dtype=np.uint8)
        background = np.full((50, 50, 3), [200, 100, 50], dtype=np.uint8)
        
        # Create test mask (half transparent)
        mask = np.full((50, 50), 0.5, dtype=np.float32)
        
        result = self.processor.composite_with_background(foreground, background, mask)
        
        # Check result properties
        assert result.shape == foreground.shape
        assert result.dtype == np.uint8
        
        # Result should be blend of foreground and background
        expected = (foreground * 0.5 + background * 0.5).astype(np.uint8)
        np.testing.assert_array_almost_equal(result, expected)

    def test_composite_with_different_sizes(self):
        """Test compositing with different sized background"""
        foreground = np.zeros((100, 100, 3), dtype=np.uint8)
        background = np.ones((50, 50, 3), dtype=np.uint8) * 255
        mask = np.ones((100, 100), dtype=np.float32)
        
        result = self.processor.composite_with_background(foreground, background, mask)
        
        # Background should be resized to match foreground
        assert result.shape == foreground.shape

    def test_process_frame_without_background(self):
        """Test processing frame without background"""
        # Create test frame
        test_frame = np.full((50, 50, 3), [0, 255, 0], dtype=np.uint8)  # All green
        
        result = self.processor.process_frame(test_frame)
        
        # Result should have alpha channel
        assert result.shape == (50, 50, 4)
        assert result.dtype == np.uint8

    def test_process_frame_with_background(self):
        """Test processing frame with background"""
        foreground = np.full((50, 50, 3), [0, 255, 0], dtype=np.uint8)  # All green
        background = np.full((50, 50, 3), [255, 0, 0], dtype=np.uint8)  # All red
        
        result = self.processor.process_frame(foreground, background)
        
        # Result should be RGB (no alpha channel)
        assert result.shape == (50, 50, 3)
        assert result.dtype == np.uint8

class TestChromaKeyManager:
    def setup_method(self):
        self.manager = ChromaKeyManager()

    def test_initialization(self):
        """Test manager initialization"""
        assert self.manager.processor is not None
        assert self.manager.background_image is None
        assert self.manager.background_clip is None

    def test_set_background_image_nonexistent(self):
        """Test setting non-existent background image"""
        result = self.manager.set_background_image("nonexistent.jpg")
        assert result is False

    def test_get_available_presets(self):
        """Test getting available presets"""
        presets = self.manager.get_available_presets()
        
        expected_presets = ['green_screen', 'blue_screen', 'red_screen', 'high_quality', 'fast_processing']
        for preset in expected_presets:
            assert preset in presets
            
        # Check preset structure
        green_preset = presets['green_screen']
        assert 'key_color' in green_preset
        assert 'tolerance' in green_preset
        assert 'edge_softness' in green_preset
        assert 'spill_suppression' in green_preset
        
        assert green_preset['key_color'] == (0, 255, 0)

    def test_apply_preset(self):
        """Test applying presets"""
        # Test valid preset
        result = self.manager.apply_preset('blue_screen')
        assert result is True
        assert self.manager.processor.key_color == (0, 0, 255)
        
        # Test invalid preset
        result = self.manager.apply_preset('nonexistent_preset')
        assert result is False

    def test_apply_preset_high_quality(self):
        """Test applying high quality preset"""
        self.manager.apply_preset('high_quality')
        
        assert self.manager.processor.key_color == (0, 255, 0)
        assert self.manager.processor.tolerance == 30
        assert self.manager.processor.edge_softness == 8
        assert self.manager.processor.spill_suppression == 0.7

    def test_apply_preset_fast_processing(self):
        """Test applying fast processing preset"""
        self.manager.apply_preset('fast_processing')
        
        assert self.manager.processor.key_color == (0, 255, 0)
        assert self.manager.processor.tolerance == 50
        assert self.manager.processor.edge_softness == 2
        assert self.manager.processor.spill_suppression == 0.3

    def test_processor_integration(self):
        """Test that manager properly configures processor"""
        # Test custom parameters
        test_params = {
            'key_color': (255, 0, 255),  # Magenta
            'tolerance': 60,
            'edge_softness': 10,
            'spill_suppression': 0.8
        }
        
        # Apply parameters through manager
        self.manager.processor.set_key_color(test_params['key_color'])
        self.manager.processor.set_tolerance(test_params['tolerance'])
        self.manager.processor.set_edge_softness(test_params['edge_softness'])
        self.manager.processor.set_spill_suppression(test_params['spill_suppression'])
        
        # Verify processor has correct settings
        assert self.manager.processor.key_color == test_params['key_color']
        assert self.manager.processor.tolerance == test_params['tolerance']
        assert self.manager.processor.edge_softness == test_params['edge_softness']
        assert self.manager.processor.spill_suppression == test_params['spill_suppression']

class TestChromaKeyIntegration:
    def setup_method(self):
        self.processor = ChromaKeyProcessor()
        self.manager = ChromaKeyManager()

    def test_end_to_end_processing(self):
        """Test complete chroma key workflow"""
        # Create test image with green screen area
        test_image = np.zeros((100, 200, 3), dtype=np.uint8)
        test_image[:, :100] = [0, 255, 0]    # Left half: green screen
        test_image[:, 100:] = [255, 255, 255]  # Right half: white subject
        
        # Create background
        background = np.full((100, 200, 3), [255, 0, 0], dtype=np.uint8)  # Red background
        
        # Process with chroma key
        result = self.processor.process_frame(test_image, background)
        
        # Verify result
        assert result.shape == (100, 200, 3)
        
        # Left side should be mostly red (background showing through)
        # Right side should be mostly white (original subject)
        left_avg = np.mean(result[:, :50], axis=(0, 1))
        right_avg = np.mean(result[:, 150:], axis=(0, 1))
        
        # Left should be more red, right should be more white
        assert left_avg[0] > left_avg[1]  # More red than green on left
        assert right_avg[0] > 200  # Right side should be bright

    def test_mask_quality(self):
        """Test mask quality with different scenarios"""
        # Test with pure green screen
        pure_green = np.full((50, 50, 3), [0, 255, 0], dtype=np.uint8)
        mask_pure = self.processor.create_mask(pure_green)
        
        # Should be mostly transparent (low values)
        assert np.mean(mask_pure) < 0.3
        
        # Test with non-green content
        non_green = np.full((50, 50, 3), [255, 0, 0], dtype=np.uint8)
        mask_non_green = self.processor.create_mask(non_green)
        
        # Should be mostly opaque (high values)
        assert np.mean(mask_non_green) > 0.7
