"""
Audio editing module for PyVideoEditor
Handles audio effects, waveform visualization, and audio processing
"""

try:
    import simpleaudio as sa
except ImportError:
    print("simpleaudio not available, using pygame for audio playback")
    import pygame
    pygame.mixer.init()
    sa = None
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from typing import Optional, List
try:
    from moviepy.editor import VideoFileClip, AudioFileClip
except ImportError:
    from moviepy import VideoFileClip, AudioFileClip
import io
import wave
from scipy.signal import butter, lfilter
import scipy.fft

class AudioProcessor:
    """Class for audio processing and effects"""
    
    def __init__(self):
        self.current_audio = None
        self.sample_rate = 44100
        self.tracks = []  # Hold multiple audio tracks for mixing
        self.filters_chain = []  # New chain for modular filtering

    def add_filter(self, filter_name: str, *args, **kwargs):
        """Add a filter to the chain"""
        if filter_name == 'lowpass':
            self.filters_chain.append((self.lowpass_filter, args, kwargs))
        elif filter_name == 'highpass':
            self.filters_chain.append((self.highpass_filter, args, kwargs))
        print(f"Added {filter_name} filter to chain")

    def apply_filters(self, audio_clip):
        """Apply all filters to the audio clip"""
        for filter_func, args, kwargs in self.filters_chain:
            audio_clip = filter_func(audio_clip, *args, **kwargs)
        return audio_clip

    def lowpass_filter(self, audio_clip, cutoff=1000.0, order=5):
        """Apply lowpass filter to audio clip"""
        def butter_lowpass(cutoff, fs, order=5):
            nyq = 0.5 * fs
            normal_cutoff = cutoff / nyq
            b, a = butter(order, normal_cutoff, btype='low', analog=False)
            return b, a

        def lfilter_process(data, cutoff, fs, order):
            b, a = butter_lowpass(cutoff, fs, order=order)
            y = lfilter(b, a, data)
            return y

        # Process audio clip
        return audio_clip.fl(lambda gf, t: lfilter_process(gf, cutoff, audio_clip.fps, order))

    def highpass_filter(self, audio_clip, cutoff=200.0, order=5):
        """Apply highpass filter to audio clip"""
        def butter_highpass(cutoff, fs, order=5):
            nyq = 0.5 * fs
            normal_cutoff = cutoff / nyq
            b, a = butter(order, normal_cutoff, btype='high', analog=False)
            return b, a

        def lfilter_process(data, cutoff, fs, order):
            b, a = butter_highpass(cutoff, fs, order=order)
            y = lfilter(b, a, data)
            return y

        # Process audio clip
        return audio_clip.fl(lambda gf, t: lfilter_process(gf, cutoff, audio_clip.fps, order))
    def add_track(self, audio_clip):
        """Add an audio clip to the list of tracks for multi-track mixing"""
        self.tracks.append(audio_clip)

    def mix_tracks(self) -> Optional[AudioFileClip]:
        """Mix multiple audio tracks into one"""
        if not self.tracks:
            print("No tracks to mix")
            return None
        
        try:
            from moviepy.editor import CompositeAudioClip
            mixed_audio = CompositeAudioClip(self.tracks)
            return mixed_audio
        except Exception as e:
            print(f"Error mixing tracks: {e}")
            return None
    
    def load_audio_from_clip(self, clip):
        """Extract audio from video clip"""
        if hasattr(clip, 'audio') and clip.audio is not None:
            self.current_audio = clip.audio
            return True
        return False
    
    def load_audio_file(self, file_path: str) -> bool:
        """Load audio file directly"""
        try:
            self.current_audio = AudioFileClip(file_path)
            return True
        except Exception as e:
            print(f"Error loading audio: {e}")
            return False
    
    def get_audio_array(self, clip=None):
        """Get audio as numpy array for processing"""
        audio_clip = clip or self.current_audio
        if not audio_clip:
            return None, None
            
        try:
            # Get audio array from MoviePy
            audio_array = audio_clip.to_soundarray()
            sample_rate = audio_clip.fps
            return audio_array, sample_rate
        except Exception as e:
            print(f"Error getting audio array: {e}")
            return None, None
    
    def apply_volume_adjustment(self, clip, volume_factor: float):
        """Adjust volume of audio clip"""
        if not clip or not hasattr(clip, 'audio') or clip.audio is None:
            return clip
            
        try:
            adjusted_audio = clip.audio.volumex(volume_factor)
            return clip.set_audio(adjusted_audio)
        except Exception as e:
            print(f"Error adjusting volume: {e}")
            return clip
    
    def apply_fade_in(self, clip, duration: float):
        """Apply fade in effect to audio"""
        if not clip or not hasattr(clip, 'audio') or clip.audio is None:
            return clip
            
        try:
            faded_audio = clip.audio.fadein(duration)
            return clip.set_audio(faded_audio)
        except Exception as e:
            print(f"Error applying fade in: {e}")
            return clip
    
    def apply_fade_out(self, clip, duration: float):
        """Apply fade out effect to audio"""
        if not clip or not hasattr(clip, 'audio') or clip.audio is None:
            return clip
            
        try:
            faded_audio = clip.audio.fadeout(duration)
            return clip.set_audio(faded_audio)
        except Exception as e:
            print(f"Error applying fade out: {e}")
            return clip
    
    def normalize_audio(self, clip):
        """Normalize audio levels"""
        if not clip or not hasattr(clip, 'audio') or clip.audio is None:
            return clip
            
        try:
            # Get audio array
            audio_array, sample_rate = self.get_audio_array(clip.audio)
            if audio_array is None:
                return clip
                
            # Normalize to prevent clipping
            max_val = np.max(np.abs(audio_array))
            if max_val > 0:
                normalized_array = audio_array / max_val * 0.95
                
                # Convert back to audio clip
                from moviepy.audio.io.AudioArrayClip import AudioArrayClip
                normalized_audio = AudioArrayClip(normalized_array, fps=sample_rate)
                return clip.set_audio(normalized_audio)
                
        except Exception as e:
            print(f"Error normalizing audio: {e}")
            
        return clip
    
    def apply_echo_effect(self, clip, delay: float = 0.5, decay: float = 0.3):
        """Apply echo effect to audio"""
        if not clip or not hasattr(clip, 'audio') or clip.audio is None:
            return clip
            
        try:
            audio_array, sample_rate = self.get_audio_array(clip.audio)
            if audio_array is None:
                return clip
                
            # Calculate delay in samples
            delay_samples = int(delay * sample_rate)
            
            # Create echo effect
            echo_array = np.zeros_like(audio_array)
            if len(echo_array) > delay_samples:
                echo_array[delay_samples:] = audio_array[:-delay_samples] * decay
                
            # Mix original with echo
            mixed_array = audio_array + echo_array
            
            # Prevent clipping
            max_val = np.max(np.abs(mixed_array))
            if max_val > 1:
                mixed_array = mixed_array / max_val
                
            # Convert back to audio clip
            from moviepy.audio.io.AudioArrayClip import AudioArrayClip
            echo_audio = AudioArrayClip(mixed_array, fps=sample_rate)
            return clip.set_audio(echo_audio)
            
        except Exception as e:
            print(f"Error applying echo: {e}")
            
        return clip
    
    def apply_audio_ducking(self, background_clip, foreground_clip, duck_amount: float = 0.3, 
                          attack_time: float = 0.1, release_time: float = 0.5):
        """Apply audio ducking - lower background when foreground is present"""
        try:
            # Get audio arrays
            bg_array, bg_rate = self.get_audio_array(background_clip.audio if hasattr(background_clip, 'audio') else background_clip)
            fg_array, fg_rate = self.get_audio_array(foreground_clip.audio if hasattr(foreground_clip, 'audio') else foreground_clip)
            
            if bg_array is None or fg_array is None:
                return background_clip
            
            # Ensure same sample rate
            if bg_rate != fg_rate:
                print(f"Warning: Sample rates don't match ({bg_rate} vs {fg_rate})")
                return background_clip
            
            # Calculate RMS of foreground for ducking trigger
            window_size = int(0.1 * bg_rate)  # 100ms window
            fg_rms = np.sqrt(np.convolve(fg_array.flatten()**2, np.ones(window_size)/window_size, mode='same'))
            
            # Create ducking envelope
            threshold = 0.01  # Threshold for ducking trigger
            duck_envelope = np.ones_like(bg_array.flatten())
            
            # Apply ducking where foreground is present
            duck_mask = fg_rms > threshold
            if np.any(duck_mask):
                # Smooth the ducking envelope
                attack_samples = int(attack_time * bg_rate)
                release_samples = int(release_time * bg_rate)
                
                for i in range(len(duck_mask)):
                    if duck_mask[i]:
                        # Attack phase
                        start_idx = max(0, i - attack_samples)
                        for j in range(start_idx, i):
                            duck_envelope[j] = np.interp(j, [start_idx, i], [1.0, duck_amount])
                        duck_envelope[i] = duck_amount
                        
                        # Release phase
                        end_idx = min(len(duck_envelope), i + release_samples)
                        for j in range(i, end_idx):
                            duck_envelope[j] = np.interp(j, [i, end_idx], [duck_amount, 1.0])
            
            # Apply ducking to background
            if len(bg_array.shape) > 1:
                ducked_array = bg_array * duck_envelope.reshape(-1, 1)
            else:
                ducked_array = bg_array * duck_envelope
            
            # Convert back to audio clip
            from moviepy.audio.io.AudioArrayClip import AudioArrayClip
            ducked_audio = AudioArrayClip(ducked_array, fps=bg_rate)
            return background_clip.set_audio(ducked_audio) if hasattr(background_clip, 'set_audio') else ducked_audio
            
        except Exception as e:
            print(f"Error applying audio ducking: {e}")
            return background_clip
    
    def apply_noise_reduction(self, clip, noise_reduction_db: float = 10.0):
        """Apply basic noise reduction using spectral subtraction"""
        try:
            audio_array, sample_rate = self.get_audio_array(clip.audio if hasattr(clip, 'audio') else clip)
            if audio_array is None:
                return clip
            
            # Handle stereo audio
            if len(audio_array.shape) > 1:
                processed_channels = []
                for channel in range(audio_array.shape[1]):
                    processed_channels.append(self._reduce_noise_channel(audio_array[:, channel], sample_rate, noise_reduction_db))
                processed_array = np.column_stack(processed_channels)
            else:
                processed_array = self._reduce_noise_channel(audio_array, sample_rate, noise_reduction_db)
            
            # Convert back to audio clip
            from moviepy.audio.io.AudioArrayClip import AudioArrayClip
            denoised_audio = AudioArrayClip(processed_array, fps=sample_rate)
            return clip.set_audio(denoised_audio) if hasattr(clip, 'set_audio') else denoised_audio
            
        except Exception as e:
            print(f"Error applying noise reduction: {e}")
            return clip
    
    def _reduce_noise_channel(self, audio_channel, sample_rate, noise_reduction_db):
        """Apply noise reduction to a single audio channel"""
        # Use the first 0.5 seconds as noise profile
        noise_sample_length = min(int(0.5 * sample_rate), len(audio_channel))
        noise_profile = audio_channel[:noise_sample_length]
        
        # Compute noise spectrum
        noise_fft = scipy.fft.fft(noise_profile)
        noise_power = np.abs(noise_fft) ** 2
        noise_power_mean = np.mean(noise_power)
        
        # Process audio in chunks
        chunk_size = 2048
        processed_audio = np.zeros_like(audio_channel)
        
        for i in range(0, len(audio_channel), chunk_size):
            chunk = audio_channel[i:i+chunk_size]
            if len(chunk) < chunk_size:
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)), 'constant')
            
            # FFT of chunk
            chunk_fft = scipy.fft.fft(chunk)
            chunk_power = np.abs(chunk_fft) ** 2
            
            # Spectral subtraction
            alpha = 10 ** (-noise_reduction_db / 20)  # Convert dB to linear
            suppression_factor = np.maximum(alpha, 1 - (noise_power_mean / (chunk_power + 1e-10)))
            
            # Apply suppression
            suppressed_fft = chunk_fft * suppression_factor
            suppressed_chunk = np.real(scipy.fft.ifft(suppressed_fft))
            
            # Store result
            end_idx = min(i + chunk_size, len(processed_audio))
            processed_audio[i:end_idx] = suppressed_chunk[:end_idx-i]
        
        return processed_audio

    def real_time_preview(self, clip):
        """Play audio clip in real-time with effects applied"""
        if not clip.audio:
            print("No audio to play for real-time preview.")
            return

        try:
            # Apply filters
            filtered_audio = self.apply_filters(clip.audio)

            # Get audio array for playback
            audio_array, sample_rate = self.get_audio_array(filtered_audio)
            if audio_array is None:
                print("Failed to retrieve audio for playback.")
                return

            # Convert audio array to simpleaudio format
            audio_data = (audio_array * 32767 / np.max(np.abs(audio_array))).astype(np.int16)
            play_obj = sa.play_buffer(audio_data, 2, 2, sample_rate)  # Stereo, 2 bytes per sample
            play_obj.wait_done()

        except Exception as e:
            print(f"Error during real-time preview: {e}")

    def apply_surround_sound(self, clip, channel_layout='5.1'):
        """Apply surround sound processing to audio"""
        try:
            audio_array, sample_rate = self.get_audio_array(clip.audio)
            if audio_array is None:
                return clip

            # Create surround sound channels based on layout
            if channel_layout == '5.1':
                surround_channels = self._create_5_1_channels(audio_array)
            elif channel_layout == '7.1':
                surround_channels = self._create_7_1_channels(audio_array)
            else:
                print(f"Unsupported channel layout: {channel_layout}")
                return clip

            # Convert back to audio clip
            from moviepy.audio.io.AudioArrayClip import AudioArrayClip
            surround_audio = AudioArrayClip(surround_channels, fps=sample_rate)
            return clip.set_audio(surround_audio) if hasattr(clip, 'set_audio') else surround_audio

        except Exception as e:
            print(f"Error applying surround sound: {e}")
            return clip

    def _create_5_1_channels(self, audio_array):
        """Create 5.1 surround sound channels from stereo input"""
        if len(audio_array.shape) == 1:
            # Mono to 5.1
            left = right = audio_array
        else:
            # Stereo to 5.1
            left = audio_array[:, 0]
            right = audio_array[:, 1]

        # Create 6 channels: Left, Right, Center, LFE, Left Surround, Right Surround
        center = (left + right) * 0.5
        lfe = center * 0.3  # Low frequency effects
        left_surround = left * 0.7
        right_surround = right * 0.7

        return np.column_stack([left, right, center, lfe, left_surround, right_surround])

    def _create_7_1_channels(self, audio_array):
        """Create 7.1 surround sound channels from stereo input"""
        if len(audio_array.shape) == 1:
            # Mono to 7.1
            left = right = audio_array
        else:
            # Stereo to 7.1
            left = audio_array[:, 0]
            right = audio_array[:, 1]

        # Create 8 channels: L, R, C, LFE, LS, RS, LB, RB
        center = (left + right) * 0.5
        lfe = center * 0.3
        left_surround = left * 0.6
        right_surround = right * 0.6
        left_back = left * 0.4
        right_back = right * 0.4

        return np.column_stack([left, right, center, lfe, left_surround, right_surround, left_back, right_back])
    
    def apply_parametric_eq(self, clip, eq_bands: List[dict]):
        """Apply parametric EQ with multiple frequency bands
        
        eq_bands: List of dictionaries with keys:
        - 'frequency': center frequency in Hz
        - 'gain': gain in dB
        - 'q_factor': Q factor (bandwidth)
        """
        try:
            audio_array, sample_rate = self.get_audio_array(clip.audio if hasattr(clip, 'audio') else clip)
            if audio_array is None:
                return clip
            
            # Handle stereo audio
            if len(audio_array.shape) > 1:
                processed_channels = []
                for channel in range(audio_array.shape[1]):
                    processed_channels.append(self._apply_eq_to_channel(audio_array[:, channel], sample_rate, eq_bands))
                processed_array = np.column_stack(processed_channels)
            else:
                processed_array = self._apply_eq_to_channel(audio_array, sample_rate, eq_bands)
            
            # Convert back to audio clip
            from moviepy.audio.io.AudioArrayClip import AudioArrayClip
            eq_audio = AudioArrayClip(processed_array, fps=sample_rate)
            return clip.set_audio(eq_audio) if hasattr(clip, 'set_audio') else eq_audio
            
        except Exception as e:
            print(f"Error applying parametric EQ: {e}")
            return clip
    
    def _apply_eq_to_channel(self, audio_channel, sample_rate, eq_bands):
        """Apply EQ bands to a single audio channel"""
        processed_audio = audio_channel.copy()
        
        for band in eq_bands:
            frequency = band.get('frequency', 1000)
            gain_db = band.get('gain', 0)
            q_factor = band.get('q_factor', 1.0)
            
            if gain_db == 0:
                continue  # No change needed
            
            # Design peaking filter
            gain_linear = 10 ** (gain_db / 20)
            omega = 2 * np.pi * frequency / sample_rate
            alpha = np.sin(omega) / (2 * q_factor)
            
            # Peaking EQ coefficients
            A = gain_linear
            b0 = 1 + alpha * A
            b1 = -2 * np.cos(omega)
            b2 = 1 - alpha * A
            a0 = 1 + alpha / A
            a1 = -2 * np.cos(omega)
            a2 = 1 - alpha / A
            
            # Normalize coefficients
            b = [b0/a0, b1/a0, b2/a0]
            a = [1, a1/a0, a2/a0]
            
            # Apply filter
            processed_audio = signal.lfilter(b, a, processed_audio)
        
        return processed_audio

    def apply_pitch_correction(self, clip, pitch_shift=0.0):
        """Apply pitch correction (auto-tune) to audio"""
        try:
            audio_array, sample_rate = self.get_audio_array(clip.audio if hasattr(clip, 'audio') else clip)
            if audio_array is None:
                return clip
            
            # Process each channel separately
            processed_channels = []
            for channel in range(audio_array.shape[1] if len(audio_array.shape) > 1 else 1):
                channel_data = audio_array if len(audio_array.shape) == 1 else audio_array[:, channel]
                # Apply pitch shifting
                shifted = self._shift_pitch(channel_data, pitch_shift, sample_rate)
                processed_channels.append(shifted)

            processed_array = np.column_stack(processed_channels) if len(audio_array.shape) > 1 else processed_channels[0]
            
            from moviepy.audio.io.AudioArrayClip import AudioArrayClip
            pitch_audio = AudioArrayClip(processed_array, fps=sample_rate)
            return clip.set_audio(pitch_audio) if hasattr(clip, 'set_audio') else pitch_audio
            
        except Exception as e:
            print(f"Error applying pitch correction: {e}")
            return clip

    def _shift_pitch(self, data, semitones, sample_rate):
        """Shift pitch of audio data by a number of semitones"""
        # Simple pitch shifting using resampling (basic implementation)
        shift_factor = 2 ** (semitones / 12.0)
        indices = np.arange(0, len(data), shift_factor)
        shifted_data = np.interp(np.arange(len(data)), indices, data[:len(indices)])
        return shifted_data
    
    def apply_compressor(self, clip, threshold_db: float = -20, ratio: float = 4.0, 
                        attack_ms: float = 10, release_ms: float = 100, makeup_gain_db: float = 0):
        """Apply dynamic range compression"""
        try:
            audio_array, sample_rate = self.get_audio_array(clip.audio if hasattr(clip, 'audio') else clip)
            if audio_array is None:
                return clip
            
            # Handle stereo audio
            if len(audio_array.shape) > 1:
                processed_channels = []
                for channel in range(audio_array.shape[1]):
                    processed_channels.append(self._compress_channel(
                        audio_array[:, channel], sample_rate, threshold_db, ratio, attack_ms, release_ms, makeup_gain_db
                    ))
                processed_array = np.column_stack(processed_channels)
            else:
                processed_array = self._compress_channel(
                    audio_array, sample_rate, threshold_db, ratio, attack_ms, release_ms, makeup_gain_db
                )
            
            # Convert back to audio clip
            from moviepy.audio.io.AudioArrayClip import AudioArrayClip
            compressed_audio = AudioArrayClip(processed_array, fps=sample_rate)
            return clip.set_audio(compressed_audio) if hasattr(clip, 'set_audio') else compressed_audio
            
        except Exception as e:
            print(f"Error applying compressor: {e}")
            return clip
    
    def _compress_channel(self, audio_channel, sample_rate, threshold_db, ratio, attack_ms, release_ms, makeup_gain_db):
        """Apply compression to a single audio channel"""
        # Convert parameters
        threshold_linear = 10 ** (threshold_db / 20)
        attack_coeff = np.exp(-1 / (attack_ms * 0.001 * sample_rate))
        release_coeff = np.exp(-1 / (release_ms * 0.001 * sample_rate))
        makeup_gain_linear = 10 ** (makeup_gain_db / 20)
        
        # Initialize envelope follower
        envelope = 0
        compressed_audio = np.zeros_like(audio_channel)
        
        for i, sample in enumerate(audio_channel):
            # Envelope detection
            input_level = abs(sample)
            if input_level > envelope:
                envelope = attack_coeff * envelope + (1 - attack_coeff) * input_level
            else:
                envelope = release_coeff * envelope + (1 - release_coeff) * input_level
            
            # Compression
            if envelope > threshold_linear:
                # Calculate compression ratio
                excess = envelope - threshold_linear
                compressed_excess = excess / ratio
                gain_reduction = (threshold_linear + compressed_excess) / envelope
            else:
                gain_reduction = 1.0
            
            # Apply compression and makeup gain
            compressed_audio[i] = sample * gain_reduction * makeup_gain_linear
        
        return compressed_audio
    
    def apply_limiter(self, clip, ceiling_db: float = -0.1, release_ms: float = 50):
        """Apply hard limiting to prevent clipping"""
        try:
            audio_array, sample_rate = self.get_audio_array(clip.audio if hasattr(clip, 'audio') else clip)
            if audio_array is None:
                return clip
            
            ceiling_linear = 10 ** (ceiling_db / 20)
            release_coeff = np.exp(-1 / (release_ms * 0.001 * sample_rate))
            
            # Handle stereo audio
            if len(audio_array.shape) > 1:
                processed_channels = []
                for channel in range(audio_array.shape[1]):
                    processed_channels.append(self._limit_channel(audio_array[:, channel], ceiling_linear, release_coeff))
                processed_array = np.column_stack(processed_channels)
            else:
                processed_array = self._limit_channel(audio_array, ceiling_linear, release_coeff)
            
            # Convert back to audio clip
            from moviepy.audio.io.AudioArrayClip import AudioArrayClip
            limited_audio = AudioArrayClip(processed_array, fps=sample_rate)
            return clip.set_audio(limited_audio) if hasattr(clip, 'set_audio') else limited_audio
            
        except Exception as e:
            print(f"Error applying limiter: {e}")
            return clip
    
    def _limit_channel(self, audio_channel, ceiling_linear, release_coeff):
        """Apply limiting to a single audio channel"""
        gain_reduction = 1.0
        limited_audio = np.zeros_like(audio_channel)
        
        for i, sample in enumerate(audio_channel):
            # Check if limiting is needed
            if abs(sample) > ceiling_linear:
                required_gain_reduction = ceiling_linear / abs(sample)
                gain_reduction = min(gain_reduction, required_gain_reduction)
            else:
                # Release
                gain_reduction = release_coeff * gain_reduction + (1 - release_coeff) * 1.0
                gain_reduction = min(gain_reduction, 1.0)
            
            # Apply limiting
            limited_audio[i] = sample * gain_reduction
        
        return limited_audio

class WaveformWidget(FigureCanvas):
    """Widget for displaying audio waveforms"""
    
    def __init__(self, parent=None, width=5, height=2, dpi=100):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.figure)
        self.setParent(parent)
        
        self.axes = self.figure.add_subplot(111)
        self.axes.set_facecolor('black')
        self.figure.patch.set_facecolor('black')
        
    def plot_waveform(self, audio_array, sample_rate, duration=None):
        """Plot audio waveform"""
        self.axes.clear()
        
        if audio_array is None or len(audio_array) == 0:
            self.axes.text(0.5, 0.5, 'No Audio', transform=self.axes.transAxes,
                          ha='center', va='center', color='white')
            self.draw()
            return
            
        # Handle stereo audio (take first channel for display)
        if len(audio_array.shape) > 1:
            audio_data = audio_array[:, 0]
        else:
            audio_data = audio_array
            
        # Create time axis
        time_axis = np.linspace(0, len(audio_data) / sample_rate, len(audio_data))
        
        # Plot waveform
        self.axes.plot(time_axis, audio_data, color='cyan', linewidth=0.5)
        self.axes.fill_between(time_axis, audio_data, alpha=0.3, color='cyan')
        
        # Styling
        self.axes.set_facecolor('black')
        self.axes.set_xlabel('Time (s)', color='white')
        self.axes.set_ylabel('Amplitude', color='white')
        self.axes.tick_params(colors='white')
        self.axes.grid(True, alpha=0.3)
        
        # Set limits
        self.axes.set_xlim(0, time_axis[-1] if len(time_axis) > 0 else 1)
        self.axes.set_ylim(-1.1, 1.1)
        
        self.figure.tight_layout()
        self.draw()
    
    def clear_waveform(self):
        """Clear the waveform display"""
        self.axes.clear()
        self.axes.set_facecolor('black')
        self.axes.text(0.5, 0.5, 'No Audio Loaded', transform=self.axes.transAxes,
                      ha='center', va='center', color='white')
        self.draw()

class AudioEffectsManager:
    """Manager for audio effects"""
    
    def __init__(self):
        self.processor = AudioProcessor()
        self.effects = {
            # Basic effects
            'volume': self.processor.apply_volume_adjustment,
            'fade_in': self.processor.apply_fade_in,
            'fade_out': self.processor.apply_fade_out,
            'normalize': self.processor.normalize_audio,
            'echo': self.processor.apply_echo_effect,
            
            # Advanced effects
            'noise_reduction': self.processor.apply_noise_reduction,
            'parametric_eq': self.processor.apply_parametric_eq,
            'compressor': self.processor.apply_compressor,
            'limiter': self.processor.apply_limiter
        }
    
    def list_effects(self):
        """List available audio effects"""
        return list(self.effects.keys())
    
    def apply_effect(self, clip, effect_name: str, **kwargs):
        """Apply an audio effect to a clip"""
        if effect_name in self.effects:
            return self.effects[effect_name](clip, **kwargs)
        else:
            raise ValueError(f"Audio effect '{effect_name}' not found")
    
    def get_waveform_data(self, clip):
        """Get waveform data for visualization"""
        return self.processor.get_audio_array(clip.audio if hasattr(clip, 'audio') else clip)
