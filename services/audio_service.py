import os
import subprocess
import tempfile
from typing import Tuple, Dict, Any
from utils.constants import SAMPLE_RATE

# Disable coverage for this module to prevent interference with audio libraries
os.environ['COVERAGE_PROCESS_START'] = ''

# Handle coverage interference by disabling it for audio processing
import sys
import logging

logger = logging.getLogger(__name__)

if 'coverage' in sys.modules:
    try:
        import coverage
        # Try to stop and disable coverage
        if hasattr(coverage, 'coverage') and coverage.coverage is not None:
            coverage.coverage.stop()
            coverage.coverage.save()
            coverage.coverage.erase()
            coverage.coverage = None
        # Remove coverage from sys.modules to prevent further interference
        modules_to_remove = ['coverage', 'coverage.types', 'coverage.tracer', 'coverage.collector', 'coverage.control']
        for mod in modules_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]
    except Exception as e:
        logger.warning(f"Could not disable coverage: {e}")

# Import audio libraries after handling coverage
try:
    import librosa
    import numpy as np
    import soundfile as sf
    from skimage.transform import resize
    AUDIO_LIBRARIES_AVAILABLE = True
except ImportError as e:
    AUDIO_LIBRARIES_AVAILABLE = False
    print(f"Warning: Audio libraries not available: {e}")

# Try to import sounddevice, but handle gracefully if not available (e.g., in cloud deployments)
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except (ImportError, OSError) as e:
    SOUNDDEVICE_AVAILABLE = False
    print(f"Warning: sounddevice not available: {e}. Microphone recording will not work in this environment.")

def load_audio(file_path: str) -> np.ndarray:
    """Load audio file and return the signal."""
    try:
        # Check if file is WebM and convert if necessary
        if _is_webm_file(file_path):
            print(f"Detected WebM file: {file_path}, converting to WAV...")
            converted_path = _convert_webm_to_wav(file_path)
            # Use the converted file for loading
            temp_file_path = converted_path
            cleanup_converted = True
        else:
            temp_file_path = file_path
            cleanup_converted = False

        # First try to read the file with soundfile to check if it's a valid audio file
        import soundfile as sf
        try:
            info = sf.info(temp_file_path)
            print(f"Audio file info: {info}")
        except Exception as sf_error:
            print(f"Soundfile info failed: {sf_error}")

        signal, _ = librosa.load(temp_file_path, sr=SAMPLE_RATE)
        print(f"Successfully loaded audio: shape={signal.shape}, dtype={signal.dtype}, min={signal.min():.4f}, max={signal.max():.4f}")

        # Clean up converted file if we created one
        if cleanup_converted and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except PermissionError:
                # File is still in use, log warning but don't fail
                print(f"Warning: Could not delete temporary file {temp_file_path} - it may be in use by another process")

        return signal
    except Exception as e:
        # Provide more detailed error information
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            error_msg = f"Failed to load audio file {file_path} (size: {file_size} bytes): {str(e)}"
            # Try to read first few bytes to see if it's a valid file
            try:
                with open(file_path, 'rb') as f:
                    header = f.read(16)
                    error_msg += f" | File header: {header.hex()}"
            except Exception as header_error:
                error_msg += f" | Could not read file header: {header_error}"
        else:
            error_msg = f"Audio file {file_path} does not exist: {str(e)}"
        error_msg += ". Supported formats: WAV, MP3, FLAC, OGG, WebM, etc. Ensure the file is not corrupted and is in a supported format."
        raise ValueError(error_msg)

def extract_mfcc(signal: np.ndarray, n_mfcc: int = 40) -> np.ndarray:
    """Extract MFCC features from audio signal."""
    mfcc = librosa.feature.mfcc(y=signal, sr=SAMPLE_RATE, n_mfcc=n_mfcc)
    mfcc = np.mean(mfcc.T, axis=0)
    return mfcc

def generate_spectrogram(signal: np.ndarray, target_size: tuple = (150, 120)) -> np.ndarray:
    """Generate spectrogram image from audio signal."""
    # Generate mel spectrogram
    mel_spec = librosa.feature.melspectrogram(y=signal, sr=SAMPLE_RATE, n_mels=128, fmax=8000)
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

    # Resize to target size
    from skimage.transform import resize
    mel_spec_resized = resize(mel_spec_db, target_size, mode='constant', anti_aliasing=True)

    # Normalize to 0-1 range
    mel_spec_normalized = (mel_spec_resized - mel_spec_resized.min()) / (mel_spec_resized.max() - mel_spec_resized.min())

    # Add channel dimension for CNN input
    spectrogram = mel_spec_normalized[..., np.newaxis]

    return spectrogram

def generate_waveform_data(signal: np.ndarray, sample_rate: int = SAMPLE_RATE, points: int = 1000) -> Dict[str, Any]:
    """Generate waveform data for visualization."""
    # Downsample the signal for visualization if it's too long
    if len(signal) > points:
        # Take evenly spaced samples
        indices = np.linspace(0, len(signal) - 1, points, dtype=int)
        waveform = signal[indices]
    else:
        waveform = signal

    # Normalize to -1 to 1 range for better visualization
    if waveform.max() > waveform.min():
        waveform = 2 * (waveform - waveform.min()) / (waveform.max() - waveform.min()) - 1

    # Calculate time axis
    duration = len(signal) / sample_rate
    time_points = np.linspace(0, duration, len(waveform))

    return {
        "waveform": waveform.tolist(),
        "time_points": time_points.tolist(),
        "duration": duration,
        "sample_rate": sample_rate,
        "points": len(waveform)
    }

def record_audio(duration: int, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Record audio from microphone for specified duration."""
    if not SOUNDDEVICE_AVAILABLE:
        raise OSError("Microphone recording is not available in this deployment environment. "
                     "PortAudio library is required but not installed. "
                     "Please use the file upload feature instead.")

    print(f"Recording {duration} seconds of audio...")
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
    sd.wait()  # Wait until recording is finished
    return recording.flatten()

def save_audio_temp(signal: np.ndarray, filename: str, sample_rate: int = SAMPLE_RATE) -> str:
    """Save audio signal to temporary file and return the path."""
    sf.write(filename, signal, sample_rate)
    return filename

def cleanup_temp_file(file_path: str):
    """Remove temporary file if it exists."""
    if os.path.exists(file_path):
        os.remove(file_path)

def _is_webm_file(file_path: str) -> bool:
    """Check if file is WebM format by reading header."""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)
            # WebM files start with specific bytes
            return header.startswith(b'\x1a\x45\xdf\xa3')
    except Exception:
        return False

def _convert_webm_to_wav(input_path: str) -> str:
    """Convert WebM file to WAV using ffmpeg."""
    output_fd, output_path = tempfile.mkstemp(suffix='.wav')
    os.close(output_fd)

    try:
        # Use ffmpeg to convert WebM to WAV
        cmd = [
            'ffmpeg',
            '-i', input_path,  # input file
            '-acodec', 'pcm_s16le',  # convert to PCM 16-bit
            '-ar', str(SAMPLE_RATE),  # set sample rate
            '-ac', '1',  # mono channel
            '-y',  # overwrite output
            output_path  # output file
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg conversion failed: {result.stderr}")

        print(f"Successfully converted WebM to WAV: {input_path} -> {output_path}")
        return output_path

    except subprocess.TimeoutExpired:
        raise TimeoutError("Audio conversion timed out")
    except FileNotFoundError:
        raise FileNotFoundError("FFmpeg not found. Please install ffmpeg to handle WebM files")
    except Exception as e:
        raise RuntimeError(f"Failed to convert WebM to WAV: {str(e)}")
