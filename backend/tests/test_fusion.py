import sys
sys.path.insert(0, "backend")
from app.services.fusion import fuse_modalities, validate_fusion_input
from unittest.mock import MagicMock

def test_both_available():
    vision = MagicMock()
    vision.available = True
    vision.duration_sec = 300
    vision.tracks = [MagicMock(), MagicMock()]
    audio = MagicMock()
    audio.available = True
    audio.speech_ratio = 0.3
    audio.method = "energy"
    result = fuse_modalities(vision, audio, session_id="sess-1")
    assert result["modalities"]["vision"]["available"] is True
    assert result["modalities"]["audio"]["available"] is True
    assert result["normalized_available"]["vision"] == 1.0
    assert "Both vision and audio available." in result["missing_signals_explained"]
    print("PASS both_available")

def test_vision_only():
    vision = MagicMock()
    vision.available = True
    vision.duration_sec = 120
    vision.tracks = [MagicMock()]
    audio = MagicMock()
    audio.available = False
    result = fuse_modalities(vision, audio, session_id="sess-v")
    assert result["normalized_available"]["vision"] == 1.0
    assert result["normalized_available"]["audio"] == 0.0
    print("PASS vision_only")

def test_audio_only():
    vision = None
    audio = MagicMock()
    audio.available = True
    audio.speech_ratio = 0.2
    audio.method = "silero"
    result = fuse_modalities(vision, audio)
    assert result["normalized_available"]["audio"] == 1.0
    print("PASS audio_only")

def test_both_missing():
    result = fuse_modalities(None, None)
    assert result["normalized_available"] == {}
    assert "Both vision and audio unavailable." in result["missing_signals_explained"]
    print("PASS both_missing")

def test_empty_observations():
    vision = MagicMock()
    vision.available = True
    vision.duration_sec = 0
    vision.tracks = []
    audio = MagicMock()
    audio.available = False
    result = fuse_modalities(vision, audio)
    assert result["modalities"]["vision"]["tracks_detected"] == 0
    print("PASS empty_observations")

def test_invalid_timestamp():
    errors = validate_fusion_input(None, MagicMock(speech_ratio=-0.1))
    assert any("speech ratio" in e for e in errors)
    print("PASS invalid_timestamp")

if __name__ == "__main__":
    test_both_available()
    test_vision_only()
    test_audio_only()
    test_both_missing()
    test_empty_observations()
    test_invalid_timestamp()
    print("All fusion tests passed.")
