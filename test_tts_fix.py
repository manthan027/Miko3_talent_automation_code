import os
import sys
import asyncio
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from miko3_automation.core.tts_utils import TextToSpeech

logging.basicConfig(level=logging.INFO)

def test_edge_tts():
    print("Testing Edge TTS with float rate...")
    tts = TextToSpeech(output_dir="temp_audio")
    
    # This should now succeed without TypeError
    # Using rate=1.0 which previously caused the crash
    audio_path = tts.edge_tts(
        text="A brave knight named Sir Lancelot.",
        output_path="temp_audio/test_fixed.wav",
        rate=1.0
    )
    
    if audio_path and os.path.exists(audio_path):
        print(f"SUCCESS: Audio generated at {audio_path}")
        # Clean up
        os.remove(audio_path)
    else:
        print("FAILURE: Audio generation failed")

if __name__ == "__main__":
    test_edge_tts()
