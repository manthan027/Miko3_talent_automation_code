import ctypes
import os
import shutil

def play_audio(audio_path):
    # Edge-TTS outputs MP3 stream, but we saved it as .wav
    # Copy to .mp3 so MCI recognizes the MP3 headers correctly
    mp3_path = audio_path.replace('.wav', '.mp3')
    if not os.path.exists(mp3_path):
        if os.path.exists(audio_path):
            shutil.copy(audio_path, mp3_path)
        else:
            print("File not found")
            return
            
    p = os.path.abspath(mp3_path)
    cmd = f'play "{p}" wait'
    err = ctypes.windll.winmm.mciSendStringW(cmd, None, 0, None)
    print("Return code:", err)

play_audio('speech.wav')
