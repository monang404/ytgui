import pytest
from core.state import AudioOutput

def test_audio_output_enum():
    assert issubclass(AudioOutput, str)
    assert AudioOutput.DEVICE == "device"
    assert AudioOutput.BROWSER == "browser"
    
    # Test equality with standard strings
    assert AudioOutput.DEVICE == "device"
    assert AudioOutput.BROWSER == "browser"
    
    # Test assignment / serialization behavior implicitly
    val: str = AudioOutput.DEVICE
    assert isinstance(val, str)
