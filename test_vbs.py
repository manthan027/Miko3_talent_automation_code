import os
import subprocess
import time

def play_audio_hidden(audio_path):
    p = os.path.abspath(audio_path)
    vbs = f"""
Set wmp = CreateObject("WMPlayer.OCX")
wmp.URL = "{p}"
wmp.controls.play
WScript.Sleep 500
While wmp.playState = 3
    WScript.Sleep 100
Wend
"""
    vbs_path = "temp_play.vbs"
    with open(vbs_path, "w") as f:
        f.write(vbs)
    
    subprocess.call(["cscript", "//nologo", vbs_path])
    os.remove(vbs_path)

play_audio_hidden("speech.wav")
