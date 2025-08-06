import pytest
import numpy as np
from core.audio_editing import AudioProcessor, AudioEffectsManager

class TestAudioEditing:
    def setup_method(self):
        self.audio_processor = AudioProcessor()
        self.audio_effects = AudioEffectsManager()

    def test_audio_processor_initialization(self):
        """Test that AudioProcessor initializes correctly"""
        assert self.audio_processor.current_audio is None
        assert self.audio_processor.sample_rate == 44100

    def test_audio_effects_manager_initialization(self):
        """Test that AudioEffectsManager initializes correctly"""
        assert hasattr(self.audio_effects, 'processor')
        assert hasattr(self.audio_effects, 'effects')
        
    def test_list_audio_effects(self):
        """Test that we can list available audio effects"""
        effects = self.audio_effects.list_effects()
        expected_effects = ['volume', 'fade_in', 'fade_out', 'normalize', 'echo']
        
        for effect in expected_effects:
            assert effect in effects, f"Effect '{effect}' not found in effects list"

    def test_audio_processor_methods_exist(self):
        """Test that AudioProcessor has required methods"""
        required_methods = [
            'load_audio_from_clip',
            'load_audio_file',
            'get_audio_array',
            'apply_volume_adjustment',
            'apply_fade_in',
            'apply_fade_out',
            'normalize_audio',
            'apply_echo_effect'
        ]
        
        for method in required_methods:
            assert hasattr(self.audio_processor, method), f"Method '{method}' missing from AudioProcessor"

    def test_audio_effects_manager_methods_exist(self):
        """Test that AudioEffectsManager has required methods"""
        required_methods = [
            'list_effects',
            'apply_effect',
            'get_waveform_data'
        ]
        
        for method in required_methods:
            assert hasattr(self.audio_effects, method), f"Method '{method}' missing from AudioEffectsManager"

    def test_load_nonexistent_audio_file(self):
        """Test loading a non-existent audio file"""
        result = self.audio_processor.load_audio_file("nonexistent.mp3")
        assert result is False, "Loading non-existent file should return False"

    def test_get_audio_array_no_audio(self):
        """Test getting audio array when no audio is loaded"""
        audio_array, sample_rate = self.audio_processor.get_audio_array()
        assert audio_array is None
        assert sample_rate is None

    def teardown_method(self):
        """Clean up after each test"""
        self.audio_processor.current_audio = None
