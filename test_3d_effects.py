"""
Test script for 3D Effects in PyVideoEditor
Demonstrates various 3D transformations and animations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from plugins.effects_3d import Effects3DManager, Transform3D
from core.video_processor import VideoProcessor
import numpy as np

def test_3d_effects():
    """Test various 3D effects"""
    print("🌀 Testing 3D Effects System...")
    
    # Initialize 3D effects manager
    effects_3d = Effects3DManager()
    
    # List available effects
    available_effects = effects_3d.list_effects()
    print(f"✅ Available 3D Effects: {available_effects}")
    
    # Test Transform3D creation
    transform = effects_3d.create_transform_3d(
        rotation_x=30.0,
        rotation_y=45.0,
        rotation_z=15.0,
        scale_x=0.8,
        scale_y=0.8,
        perspective=1500.0
    )
    print(f"✅ Created 3D Transform: {transform}")
    
    # Test individual effects (without actual video for now)
    try:
        # Test 3D rotation effect creation
        rotation_effect = effects_3d.get_effect('rotate_3d', transform=transform)
        print(f"✅ Created 3D Rotation Effect: {rotation_effect.get_name()}")
        
        # Test 3D cube effect
        cube_effect = effects_3d.get_effect('cube_3d', rotation_speed=45.0, cube_size=0.7)
        print(f"✅ Created 3D Cube Effect: {cube_effect.get_name()}")
        
        # Test 3D cylinder effect
        cylinder_effect = effects_3d.get_effect('cylinder_3d', curvature=0.8, rotation_speed=30.0)
        print(f"✅ Created 3D Cylinder Effect: {cylinder_effect.get_name()}")
        
        # Test 3D sphere effect
        sphere_effect = effects_3d.get_effect('sphere_3d', sphere_radius=0.9, rotation_speed=25.0)
        print(f"✅ Created 3D Sphere Effect: {sphere_effect.get_name()}")
        
        # Test wave deformation
        wave_effect = effects_3d.get_effect('wave_deform_3d', 
                                          amplitude=15.0, 
                                          frequency=3.0, 
                                          wave_speed=8.0, 
                                          direction="both")
        print(f"✅ Created 3D Wave Deform Effect: {wave_effect.get_name()}")
        
        # Test ripple effect
        ripple_effect = effects_3d.get_effect('ripple_3d',
                                            amplitude=25.0,
                                            frequency=4.0,
                                            wave_speed=120.0,
                                            decay=0.3)
        print(f"✅ Created 3D Ripple Effect: {ripple_effect.get_name()}")
        
        # Test depth of field
        dof_effect = effects_3d.get_effect('depth_of_field_3d',
                                         focus_distance=0.6,
                                         blur_strength=8.0,
                                         depth_map_type="radial")
        print(f"✅ Created 3D Depth of Field Effect: {dof_effect.get_name()}")
        
        print("🎉 All 3D effects created successfully!")
        
    except Exception as e:
        print(f"❌ Error testing 3D effects: {e}")
        return False
    
    return True

def test_integration_with_video_processor():
    """Test integration with VideoProcessor"""
    print("\n🎬 Testing 3D Effects Integration with VideoProcessor...")
    
    try:
        # Initialize video processor
        processor = VideoProcessor()
        
        # Check if 3D effects are available
        available_effects = processor.list_available_effects()
        
        # Count 3D effects
        effects_3d_count = sum(1 for effect in available_effects if '3d' in effect.lower())
        print(f"✅ Found {effects_3d_count} 3D effects in VideoProcessor")
        
        if effects_3d_count > 0:
            print("✅ 3D Effects successfully integrated with VideoProcessor!")
            return True
        else:
            print("⚠️ No 3D effects found in VideoProcessor")
            return False
            
    except Exception as e:
        print(f"❌ Error testing integration: {e}")
        return False

def demonstrate_3d_usage():
    """Demonstrate how to use 3D effects"""
    print("\n📖 3D Effects Usage Examples:")
    
    print("""
    # Example 1: Apply 3D rotation to a video clip
    from plugins.effects_3d import Effects3DManager, Transform3D
    
    effects_3d = Effects3DManager()
    transform = Transform3D(
        rotation_x=30.0,    # Rotate 30 degrees around X-axis
        rotation_y=45.0,    # Rotate 45 degrees around Y-axis
        scale_x=0.8,        # Scale to 80% width
        scale_y=0.8         # Scale to 80% height
    )
    
    # Apply to video clip
    rotated_clip = effects_3d.apply_effect(video_clip, 'rotate_3d', transform=transform)
    
    # Example 2: Create animated 3D cube
    cube_clip = effects_3d.apply_effect(video_clip, 'cube_3d', 
                                       rotation_speed=60.0,  # 60 degrees per second
                                       cube_size=0.7)        # 70% of original size
    
    # Example 3: Apply cylinder wrap effect
    cylinder_clip = effects_3d.apply_effect(video_clip, 'cylinder_3d',
                                           curvature=0.8,       # 80% curvature
                                           rotation_speed=20.0) # Slow rotation
    
    # Example 4: Create ripple effect
    ripple_clip = effects_3d.apply_effect(video_clip, 'ripple_3d',
                                         amplitude=30.0,       # Ripple strength
                                         frequency=2.0,        # Wave frequency
                                         wave_speed=100.0)     # Speed of ripples
    
    # Example 5: Apply depth of field blur
    dof_clip = effects_3d.apply_effect(video_clip, 'depth_of_field_3d',
                                      focus_distance=0.5,    # Focus at center
                                      blur_strength=10.0,    # Strong blur
                                      depth_map_type="radial") # Radial depth map
    """)

if __name__ == "__main__":
    print("🚀 Starting 3D Effects Test Suite...")
    
    # Test 3D effects system
    effects_test = test_3d_effects()
    
    # Test integration
    integration_test = test_integration_with_video_processor()
    
    # Show usage examples
    demonstrate_3d_usage()
    
    # Summary
    print(f"\n📊 Test Results:")
    print(f"  3D Effects System: {'✅ PASSED' if effects_test else '❌ FAILED'}")
    print(f"  VideoProcessor Integration: {'✅ PASSED' if integration_test else '❌ FAILED'}")
    
    if effects_test and integration_test:
        print("\n🎉 All 3D Effects tests passed! The system is ready to use.")
    else:
        print("\n⚠️ Some tests failed. Please check the implementation.")
    
    print("\n" + "="*60)
    print("3D Effects Features Added:")
    print("• 3D Rotation with full X, Y, Z axis control")
    print("• 3D Cube mapping and animation")
    print("• Cylindrical video wrapping")
    print("• Spherical video mapping")
    print("• Wave deformation effects")
    print("• Ripple effects from center")
    print("• Depth of field with distance-based blur")
    print("• Animated 3D transformations with easing")
    print("• Integration with existing effects system")
    print("="*60)
