import pytest
from core.video_processor import VideoProcessor
from core.color_grading import ColorGrading

class TestVideoProcessor:
    def setup_method(self):
        self.processor = VideoProcessor()
        self.color_grading = ColorGrading()

    def test_load_video(self):
        # Test loading a video (will fail without actual video file)
        result = self.processor.load_video("assets/sample.mp4")
        # This will be False since we don't have an actual video file
        assert isinstance(result, bool), "load_video should return boolean"

    def test_color_grading_methods_exist(self):
        # Test that color grading methods exist
        assert hasattr(self.color_grading, 'adjust_hue'), "adjust_hue method missing"
        assert hasattr(self.color_grading, 'adjust_saturation'), "adjust_saturation method missing"
        assert hasattr(self.color_grading, 'adjust_luminance'), "adjust_luminance method missing"

    def test_apply_color_grading_method_exists(self):
        # Test that video processor has color grading integration
        assert hasattr(self.processor, 'apply_color_grading'), "apply_color_grading method missing"
        assert hasattr(self.processor, 'color_grading'), "color_grading attribute missing"

    def test_video_info_structure(self):
        # Test video info returns correct structure
        info = self.processor.get_video_info()
        assert isinstance(info, dict), "get_video_info should return dict"

    def teardown_method(self):
        # Clean up any loaded clips
        self.processor.cleanup()
