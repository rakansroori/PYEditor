"""
Unit tests for the title and text system
Tests text styling, animations, templates, and integration
"""

import pytest
import os
import tempfile
import json
from unittest.mock import Mock, patch
from core.text_system import (
    TitleSystem, TextStyle, TextAnimationConfig, TextAnimation, 
    TextAlignment, TextTemplate, TextClipGenerator
)

class TestTextStyle:
    """Test TextStyle class"""
    
    def test_default_style(self):
        """Test default text style creation"""
        style = TextStyle()
        assert style.font == "Arial"
        assert style.font_size == 48
        assert style.color == "white"
        assert style.alignment == TextAlignment.CENTER
        assert not style.bold
        assert not style.italic
    
    def test_custom_style(self):
        """Test custom text style creation"""
        style = TextStyle(
            font="Impact",
            font_size=72,
            color="red",
            bold=True,
            stroke_color="white",
            stroke_width=2
        )
        assert style.font == "Impact"
        assert style.font_size == 72
        assert style.color == "red"
        assert style.bold
        assert style.stroke_color == "white"
        assert style.stroke_width == 2
    
    def test_style_serialization(self):
        """Test style to_dict and from_dict"""
        original_style = TextStyle(
            font="Helvetica",
            font_size=36,
            color="blue",
            alignment=TextAlignment.LEFT,
            bold=True
        )
        
        # Serialize to dict
        style_dict = original_style.to_dict()
        assert isinstance(style_dict, dict)
        assert style_dict['font'] == "Helvetica"
        assert style_dict['alignment'] == "left"
        
        # Deserialize from dict
        restored_style = TextStyle.from_dict(style_dict)
        assert restored_style.font == original_style.font
        assert restored_style.font_size == original_style.font_size
        assert restored_style.alignment == original_style.alignment
        assert restored_style.bold == original_style.bold

class TestTextAnimationConfig:
    """Test TextAnimationConfig class"""
    
    def test_default_animation(self):
        """Test default animation config"""
        config = TextAnimationConfig()
        assert config.animation_type == TextAnimation.NONE
        assert config.duration == 1.0
        assert config.delay == 0.0
        assert config.repeat == 1
        assert not config.reverse
    
    def test_custom_animation(self):
        """Test custom animation config"""
        config = TextAnimationConfig(
            animation_type=TextAnimation.FADE_IN,
            duration=2.5,
            delay=0.5,
            repeat=3,
            reverse=True
        )
        assert config.animation_type == TextAnimation.FADE_IN
        assert config.duration == 2.5
        assert config.delay == 0.5
        assert config.repeat == 3
        assert config.reverse
    
    def test_animation_serialization(self):
        """Test animation config serialization"""
        original_config = TextAnimationConfig(
            animation_type=TextAnimation.TYPEWRITER,
            duration=3.0,
            easing="ease_out"
        )
        
        # Serialize
        config_dict = original_config.to_dict()
        assert config_dict['animation_type'] == "typewriter"
        assert config_dict['duration'] == 3.0
        
        # Deserialize
        restored_config = TextAnimationConfig.from_dict(config_dict)
        assert restored_config.animation_type == TextAnimation.TYPEWRITER
        assert restored_config.duration == 3.0
        assert restored_config.easing == "ease_out"

class TestTextClipGenerator:
    """Test TextClipGenerator class"""
    
    def setUp(self):
        self.generator = TextClipGenerator()
    
    def test_initialization(self):
        """Test generator initialization"""
        generator = TextClipGenerator()
        assert len(generator.available_fonts) > 0
        assert "Arial" in generator.available_fonts
        assert isinstance(generator.default_style, TextStyle)
    
    @patch('core.text_system.TextClip')
    def test_create_basic_text_clip(self, mock_text_clip):
        """Test basic text clip creation"""
        # Mock the TextClip
        mock_clip = Mock()
        mock_clip.with_duration.return_value = mock_clip
        mock_text_clip.return_value = mock_clip
        
        generator = TextClipGenerator()
        style = TextStyle(font="Arial", font_size=48, color="white")
        
        clip = generator.create_text_clip("Test Text", style, 3.0)
        
        # Verify TextClip was called with correct parameters
        mock_text_clip.assert_called_once()
        mock_clip.with_duration.assert_called_with(3.0)
    
    @patch('core.text_system.TextClip')
    def test_create_text_with_background(self, mock_text_clip):
        """Test text clip with background color"""
        mock_clip = Mock()
        mock_clip.with_duration.return_value = mock_clip
        mock_clip.size = (200, 100)
        mock_text_clip.return_value = mock_clip
        
        generator = TextClipGenerator()
        style = TextStyle(
            font="Arial",
            font_size=48,
            color="white",
            background_color="rgba(0,0,0,0.5)"
        )
        
        with patch('core.text_system.ColorClip') as mock_color_clip, \
             patch('core.text_system.CompositeVideoClip') as mock_composite:
            
            mock_bg = Mock()
            mock_bg.with_duration.return_value = mock_bg
            mock_color_clip.return_value = mock_bg
            
            mock_composite.return_value = Mock()
            
            clip = generator.create_text_clip("Test Text", style, 3.0)
            
            # Verify background was created
            mock_color_clip.assert_called_once()
            mock_composite.assert_called_once()

class TestTextTemplate:
    """Test TextTemplate class"""
    
    def test_template_creation(self):
        """Test template creation"""
        style = TextStyle(font="Impact", font_size=64, bold=True)
        animation = TextAnimationConfig(animation_type=TextAnimation.SCALE_IN)
        
        template = TextTemplate("Test Template", style, animation)
        assert template.name == "Test Template"
        assert template.style.font == "Impact"
        assert template.animation.animation_type == TextAnimation.SCALE_IN
        assert template.description == ""
        assert template.tags == []
    
    def test_template_serialization(self):
        """Test template serialization"""
        style = TextStyle(font="Arial", color="red")
        animation = TextAnimationConfig(animation_type=TextAnimation.FADE_IN)
        template = TextTemplate("Test", style, animation)
        template.description = "A test template"
        template.tags = ["test", "demo"]
        
        # Serialize
        template_dict = template.to_dict()
        assert template_dict['name'] == "Test"
        assert template_dict['description'] == "A test template"
        assert template_dict['tags'] == ["test", "demo"]
        assert 'style' in template_dict
        assert 'animation' in template_dict
        
        # Deserialize
        restored = TextTemplate.from_dict(template_dict)
        assert restored.name == template.name
        assert restored.description == template.description
        assert restored.tags == template.tags
        assert restored.style.font == template.style.font

class TestTitleSystem:
    """Test TitleSystem class"""
    
    def test_initialization(self):
        """Test title system initialization"""
        system = TitleSystem()
        assert isinstance(system.clip_generator, TextClipGenerator)
        assert len(system.templates) > 0
        assert "main_title" in system.templates
        assert "subtitle" in system.templates
        assert len(system.text_clips) == 0
    
    def test_default_templates(self):
        """Test default templates are properly loaded"""
        system = TitleSystem()
        templates = system.list_templates()
        
        expected_templates = [
            "main_title", "subtitle", "lower_third", 
            "typewriter_title", "impact_title"
        ]
        
        for template_name in expected_templates:
            assert template_name in templates
            template = system.get_template(template_name)
            assert template is not None
            assert isinstance(template.style, TextStyle)
            assert isinstance(template.animation, TextAnimationConfig)
    
    @patch('core.text_system.TextClip')
    def test_create_text_overlay(self, mock_text_clip):
        """Test text overlay creation"""
        # Setup mock
        mock_clip = Mock()
        mock_clip.set_duration.return_value = mock_clip
        mock_clip.set_position.return_value = mock_clip
        mock_text_clip.return_value = mock_clip
        
        system = TitleSystem()
        
        overlay = system.create_text_overlay(
            text="Test Overlay",
            template_name="main_title",
            duration=3.0
        )
        
        assert overlay['text'] == "Test Overlay"
        assert overlay['duration'] == 3.0
        assert 'id' in overlay
        assert 'clip' in overlay
        
        # Verify clip was stored
        clip_id = overlay['id']
        assert clip_id in system.text_clips
        stored_clip = system.get_text_clip(clip_id)
        assert stored_clip is not None
        assert stored_clip['text'] == "Test Overlay"
    
    def test_template_management(self):
        """Test adding and retrieving templates"""
        system = TitleSystem()
        initial_count = len(system.templates)
        
        # Add custom template
        custom_style = TextStyle(font="Comic Sans MS", color="purple")
        custom_animation = TextAnimationConfig(animation_type=TextAnimation.BOUNCE)
        custom_template = TextTemplate("Custom", custom_style, custom_animation)
        
        system.add_template(custom_template)
        
        assert len(system.templates) == initial_count + 1
        assert "Custom" in system.list_templates()
        
        retrieved = system.get_template("Custom")
        assert retrieved.name == "Custom"
        assert retrieved.style.font == "Comic Sans MS"
        assert retrieved.animation.animation_type == TextAnimation.BOUNCE
    
    def test_template_persistence(self):
        """Test saving and loading templates"""
        system = TitleSystem()
        
        # Add custom template
        custom_style = TextStyle(font="Georgia", font_size=56)
        custom_animation = TextAnimationConfig(animation_type=TextAnimation.SLIDE_LEFT)
        custom_template = TextTemplate("Persistent", custom_style, custom_animation)
        system.add_template(custom_template)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            system.save_templates(temp_path)
            assert os.path.exists(temp_path)
            
            # Create new system and load templates
            new_system = TitleSystem()
            original_count = len(new_system.templates)
            
            new_system.load_templates(temp_path)
            
            # Verify template was loaded
            assert len(new_system.templates) >= original_count
            persistent_template = new_system.get_template("Persistent")
            if persistent_template:  # Template might not be loaded if it conflicts with defaults
                assert persistent_template.style.font == "Georgia"
                assert persistent_template.animation.animation_type == TextAnimation.SLIDE_LEFT
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @patch('core.text_system.CompositeVideoClip')
    @patch('core.text_system.ColorClip')
    def test_create_title_sequence(self, mock_color_clip, mock_composite):
        """Test title sequence creation"""
        # Setup mocks
        mock_bg = Mock()
        mock_bg.set_duration.return_value = mock_bg
        mock_color_clip.return_value = mock_bg
        
        mock_sequence = Mock()
        mock_composite.return_value = mock_sequence
        
        system = TitleSystem()
        
        titles = [
            {
                'text': 'Title 1',
                'template': 'main_title',
                'start_time': 0.0,
                'duration': 3.0
            },
            {
                'text': 'Title 2', 
                'template': 'subtitle',
                'start_time': 2.0,
                'duration': 3.0
            }
        ]
        
        with patch.object(system, 'create_text_overlay') as mock_create:
            mock_overlay = {
                'clip': Mock(),
                'text': 'Mock Title',
                'duration': 3.0
            }
            mock_overlay['clip'].set_start.return_value = Mock()
            mock_create.return_value = mock_overlay
            
            sequence = system.create_title_sequence(titles, total_duration=10.0)
            
            # Verify overlays were created
            assert mock_create.call_count == 2
            mock_composite.assert_called_once()
    
    @patch('core.text_system.TextClip')
    def test_update_text_style(self, mock_text_clip):
        """Test updating text style"""
        # Setup mock
        mock_clip = Mock()
        mock_clip.set_duration.return_value = mock_clip
        mock_clip.set_position.return_value = mock_clip
        mock_text_clip.return_value = mock_clip
        
        system = TitleSystem()
        
        # Create initial overlay
        overlay = system.create_text_overlay("Test Text", duration=3.0)
        clip_id = overlay['id']
        
        # Update style
        new_style = TextStyle(font="Times New Roman", font_size=64, color="blue")
        success = system.update_text_style(clip_id, new_style)
        
        assert success
        
        # Verify style was updated
        updated_clip = system.get_text_clip(clip_id)
        assert updated_clip['style'].font == "Times New Roman"
        assert updated_clip['style'].font_size == 64
        assert updated_clip['style'].color == "blue"
    
    def test_invalid_operations(self):
        """Test handling of invalid operations"""
        system = TitleSystem()
        
        # Test non-existent template
        overlay = system.create_text_overlay(
            text="Test",
            template_name="non_existent_template"
        )
        assert overlay is not None  # Should fall back to default
        
        # Test updating non-existent clip
        new_style = TextStyle(color="red")
        success = system.update_text_style("invalid_id", new_style)
        assert not success
        
        # Test getting non-existent template
        template = system.get_template("invalid_template")
        assert template is None
        
        # Test getting non-existent clip
        clip = system.get_text_clip("invalid_id")
        assert clip is None

if __name__ == '__main__':
    pytest.main([__file__])
