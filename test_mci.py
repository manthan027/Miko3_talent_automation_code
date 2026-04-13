import ctypes
import os

def play_audio(audio_path):
    p = os.path.abspath(audio_path)
    cmd = f'play "{p}" wait'
    err = ctypes.windll.winmm.mciSendStringW(cmd, None, 0, None)
    print("Return code:", err)

play_audio('speech.wav')
