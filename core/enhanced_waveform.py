"""
Enhanced Waveform Visualization for PyVideoEditor
Provides detailed waveform display with zoom, frequency analysis, and editing capabilities
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
import scipy.fft
from typing import Optional, Tuple

class EnhancedWaveformWidget(QWidget):
    """Enhanced waveform display with interactive features"""
    
    time_selected = pyqtSignal(float, float)  # start_time, end_time
    position_changed = pyqtSignal(float)  # current_position
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio_data = None
        self.sample_rate = 44100
        self.current_position = 0.0
        self.selection_start = None
        self.selection_end = None
        self.zoom_level = 1.0
        self.view_start = 0.0
        self.view_end = 1.0
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the waveform widget UI"""
        layout = QVBoxLayout(self)
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(12, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # Control panel
        controls_layout = QHBoxLayout()
        
        # Zoom controls
        self.zoom_in_btn = QPushButton("Zoom In")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        controls_layout.addWidget(self.zoom_in_btn)
        
        self.zoom_out_btn = QPushButton("Zoom Out")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        controls_layout.addWidget(self.zoom_out_btn)
        
        # Time position slider
        controls_layout.addWidget(QLabel("Position:"))
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setMinimum(0)
        self.position_slider.setMaximum(1000)
        self.position_slider.valueChanged.connect(self.on_position_changed)
        controls_layout.addWidget(self.position_slider)
        
        # View controls
        self.show_frequency_btn = QPushButton("Show Frequency")
        self.show_frequency_btn.setCheckable(True)
        self.show_frequency_btn.clicked.connect(self.toggle_frequency_view)
        controls_layout.addWidget(self.show_frequency_btn)
        
        layout.addLayout(controls_layout)
        
        # Connect canvas events
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)
        self.canvas.mpl_connect('button_release_event', self.on_canvas_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_canvas_motion)
        
    def load_audio_data(self, audio_data: np.ndarray, sample_rate: int):
        """Load audio data for visualization"""
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        self.view_end = len(audio_data) / sample_rate
        self.update_display()
        
    def update_display(self):
        """Update the waveform display"""
        if self.audio_data is None:
            return
            
        self.figure.clear()
        
        if self.show_frequency_btn.isChecked():
            self.draw_frequency_view()
        else:
            self.draw_waveform_view()
            
        self.canvas.draw()
        
    def draw_waveform_view(self):
        """Draw the waveform view"""
        # Calculate view range
        total_samples = len(self.audio_data)
        start_sample = int(self.view_start * self.sample_rate)
        end_sample = int(self.view_end * self.sample_rate)
        start_sample = max(0, min(start_sample, total_samples))
        end_sample = max(start_sample + 1, min(end_sample, total_samples))
        
        # Get data for current view
        view_data = self.audio_data[start_sample:end_sample]
        time_axis = np.linspace(self.view_start, self.view_end, len(view_data))
        
        # Create subplots
        if len(self.audio_data.shape) > 1 and self.audio_data.shape[1] > 1:
            # Stereo
            ax1 = self.figure.add_subplot(2, 1, 1)
            ax2 = self.figure.add_subplot(2, 1, 2)
            
            ax1.plot(time_axis, view_data[:, 0], color='blue', linewidth=0.5)
            ax1.set_title('Left Channel')
            ax1.set_ylabel('Amplitude')
            ax1.grid(True, alpha=0.3)
            
            ax2.plot(time_axis, view_data[:, 1], color='red', linewidth=0.5)
            ax2.set_title('Right Channel')
            ax2.set_ylabel('Amplitude')
            ax2.set_xlabel('Time (s)')
            ax2.grid(True, alpha=0.3)
            
            axes = [ax1, ax2]
        else:
            # Mono
            ax = self.figure.add_subplot(1, 1, 1)
            if len(view_data.shape) > 1:
                view_data = view_data[:, 0]
            ax.plot(time_axis, view_data, color='blue', linewidth=0.5)
            ax.set_title('Waveform')
            ax.set_ylabel('Amplitude')
            ax.set_xlabel('Time (s)')
            ax.grid(True, alpha=0.3)
            axes = [ax]
            
        # Draw position marker
        for ax in axes:
            ax.axvline(x=self.current_position, color='green', linewidth=2, alpha=0.7)
            
        # Draw selection if exists
        if self.selection_start is not None and self.selection_end is not None:
            for ax in axes:
                ax.axvspan(self.selection_start, self.selection_end, alpha=0.3, color='yellow')
                
    def draw_frequency_view(self):
        """Draw frequency domain view (spectrogram)"""
        if len(self.audio_data.shape) > 1:
            # Use left channel for spectrogram
            data = self.audio_data[:, 0]
        else:
            data = self.audio_data
            
        # Calculate view range
        start_sample = int(self.view_start * self.sample_rate)
        end_sample = int(self.view_end * self.sample_rate)
        start_sample = max(0, min(start_sample, len(data)))
        end_sample = max(start_sample + 1, min(end_sample, len(data)))
        
        view_data = data[start_sample:end_sample]
        
        if len(view_data) < 256:  # Minimum size for spectrogram
            return
            
        ax = self.figure.add_subplot(1, 1, 1)
        
        # Create spectrogram
        frequencies, times, Sxx = scipy.signal.spectrogram(
            view_data, 
            fs=self.sample_rate,
            nperseg=min(1024, len(view_data)//4),
            noverlap=None
        )
        
        # Adjust time axis to match view
        times = times + self.view_start
        
        # Plot spectrogram
        im = ax.pcolormesh(times, frequencies, 10 * np.log10(Sxx + 1e-10), 
                          shading='gouraud', cmap='viridis')
        ax.set_ylabel('Frequency (Hz)')
        ax.set_xlabel('Time (s)')
        ax.set_title('Spectrogram')
        
        # Add colorbar
        self.figure.colorbar(im, ax=ax, label='Power (dB)')
        
        # Draw position marker
        ax.axvline(x=self.current_position, color='red', linewidth=2, alpha=0.7)
        
    def zoom_in(self):
        """Zoom in on the waveform"""
        if self.audio_data is None:
            return
            
        center = (self.view_start + self.view_end) / 2
        current_range = self.view_end - self.view_start
        new_range = current_range / 2
        
        self.view_start = max(0, center - new_range / 2)
        self.view_end = min(len(self.audio_data) / self.sample_rate, center + new_range / 2)
        
        self.zoom_level *= 2
        self.update_display()
        
    def zoom_out(self):
        """Zoom out on the waveform"""
        if self.audio_data is None:
            return
            
        center = (self.view_start + self.view_end) / 2
        current_range = self.view_end - self.view_start
        new_range = min(current_range * 2, len(self.audio_data) / self.sample_rate)
        
        self.view_start = max(0, center - new_range / 2)
        self.view_end = min(len(self.audio_data) / self.sample_rate, center + new_range / 2)
        
        self.zoom_level = max(1.0, self.zoom_level / 2)
        self.update_display()
        
    def toggle_frequency_view(self):
        """Toggle between waveform and frequency view"""
        self.update_display()
        
    def on_position_changed(self, value):
        """Handle position slider change"""
        if self.audio_data is None:
            return
            
        max_time = len(self.audio_data) / self.sample_rate
        self.current_position = (value / 1000.0) * max_time
        self.position_changed.emit(self.current_position)
        self.update_display()
        
    def set_position(self, position: float):
        """Set the current position marker"""
        self.current_position = position
        if self.audio_data is not None:
            max_time = len(self.audio_data) / self.sample_rate
            slider_value = int((position / max_time) * 1000)
            self.position_slider.setValue(slider_value)
        self.update_display()
        
    def on_canvas_click(self, event):
        """Handle canvas click events"""
        if event.inaxes is None or self.audio_data is None:
            return
            
        if event.button == 1:  # Left click
            # Start selection
            self.selection_start = event.xdata
            self.selection_end = None
            
        elif event.button == 3:  # Right click
            # Set position
            self.current_position = event.xdata
            self.position_changed.emit(self.current_position)
            self.update_display()
            
    def on_canvas_release(self, event):
        """Handle canvas release events"""
        if event.inaxes is None or self.audio_data is None:
            return
            
        if event.button == 1 and self.selection_start is not None:  # Left click release
            self.selection_end = event.xdata
            if self.selection_start > self.selection_end:
                self.selection_start, self.selection_end = self.selection_end, self.selection_start
            
            self.time_selected.emit(self.selection_start, self.selection_end)
            self.update_display()
            
    def on_canvas_motion(self, event):
        """Handle canvas motion events"""
        if event.inaxes is None or self.audio_data is None:
            return
            
        # Update selection during drag
        if event.button == 1 and self.selection_start is not None:
            self.selection_end = event.xdata
            self.update_display()
            
    def clear_selection(self):
        """Clear the current selection"""
        self.selection_start = None
        self.selection_end = None
        self.update_display()
        
    def get_selection(self) -> Optional[Tuple[float, float]]:
        """Get the current selection as (start_time, end_time)"""
        if self.selection_start is not None and self.selection_end is not None:
            return (min(self.selection_start, self.selection_end), 
                   max(self.selection_start, self.selection_end))
        return None
        
    def analyze_frequency_at_position(self, position: float) -> dict:
        """Analyze frequency content at a specific position"""
        if self.audio_data is None:
            return {}
            
        # Get sample position
        sample_pos = int(position * self.sample_rate)
        window_size = min(2048, len(self.audio_data) - sample_pos)
        
        if window_size < 256:
            return {}
            
        # Extract window around position
        start_pos = max(0, sample_pos - window_size // 2)
        end_pos = min(len(self.audio_data), start_pos + window_size)
        
        if len(self.audio_data.shape) > 1:
            window_data = self.audio_data[start_pos:end_pos, 0]  # Use left channel
        else:
            window_data = self.audio_data[start_pos:end_pos]
            
        # Apply window function
        window_data = window_data * np.hanning(len(window_data))
        
        # Calculate FFT
        fft_data = np.abs(scipy.fft.fft(window_data))
        freqs = scipy.fft.fftfreq(len(window_data), 1/self.sample_rate)
        
        # Get positive frequencies only
        positive_freqs = freqs[:len(freqs)//2]
        positive_fft = fft_data[:len(fft_data)//2]
        
        # Find dominant frequencies
        peak_indices = scipy.signal.find_peaks(positive_fft, height=np.max(positive_fft) * 0.1)[0]
        dominant_freqs = [(positive_freqs[i], positive_fft[i]) for i in peak_indices]
        dominant_freqs.sort(key=lambda x: x[1], reverse=True)  # Sort by amplitude
        
        return {
            'position': position,
            'dominant_frequencies': dominant_freqs[:10],  # Top 10 frequencies
            'rms_level': np.sqrt(np.mean(window_data**2)),
            'peak_level': np.max(np.abs(window_data))
        }
