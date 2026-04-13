# Audio and Text-to-Speech Integration Guide

## Overview

This guide shows how to use **Google TTS** and **Microsoft Edge TTS** for audio input/output in your Miko3 Talents Automation framework.

## Features

- **Text-to-Speech (TTS)**: Convert text to natural-sounding audio
- **Multiple Providers**: Google TTS (free, basic) and Edge TTS (free, high quality)
- **Device Audio**: Push audio to Android device and play it
- **Batch Processing**: Generate multiple audio files at once
- **No API Keys Required**: Both providers work without authentication

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This includes:
- `gtts>=2.4.0` - Google TTS
- `edge-tts>=6.1.0` - Microsoft Edge TTS  
- `pydub>=0.25.1` - Audio manipulation

### 2. Use in Your Talent Test

```python
from miko3_automation.talents.base_talent import BaseTalentTest

class StorymakerTalentTest(BaseTalentTest):
    def execute(self):
        self.step("Generate and play instruction")
        
        # Convert text to speech and play on device
        self.play_speech("Welcome to the story maker talent")
        
        self.step("Tap start button")
        self.tap_text("Create Story")
```

## Detailed Usage

### Option 1: Simple Text-to-Speech (Easiest)

**Generate speech once and play immediately:**

```python
def execute(self):
    self.step("Play greeting")
    
    # All-in-one: generate TTS and play on device
    self.play_speech("Let's create an amazing adventure story")
    self.wait(5)  # Wait for audio to finish
```

**Result**: 
- Text converted to speech
- Audio pushed to device
- Audio played through device speaker
- Automatic wait for playback

### Option 2: Generate First, Reuse Multiple Times

**Create audio once, use many times:**

```python
def execute(self):
    # Generate speech and save locally
    audio_path = self.generate_speech(
        "Tap the first story to begin",
        filename="instruction.wav"
    )
    # audio_path = "audio/instruction.wav"
    
    # Use the same audio multiple times
    for i in range(3):
        self.step(f"Replay instruction {i+1}")
        self.play_audio_file(audio_path, wait_seconds=3)
```

### Option 3: Choose TTS Provider

**Use Edge TTS (recommended - better quality):**

```python
def execute(self):
    # Edge TTS produces more natural-sounding speech
    self.play_speech(
        "Start your creative journey",
        provider="edge"  # Default
    )
```

**Use Google TTS (basic quality):**

```python
def execute(self):
    # Faster, but lower quality
    self.play_speech(
        "Ready to create?",
        provider="google"
    )
```

### Option 4: Choose Voice (Edge TTS Only)

**Select different voices:**

```python
def execute(self):
    # Female voice (natural, default)
    self.generate_speech(
        "Choose a character",
        voice="en-US-AriaNeural"
    )
    
    # Male voice
    self.generate_speech(
        "Select the background",
        voice="en-US-GuyNeural"
    )
    
    # Child voice
    self.generate_speech(
        "What happens next?",
        voice="en-US-KaiNeural"
    )
    
    # List all available voices
    self.tts.list_edge_voices()
```

### Option 5: Long Text (Split into Chunks)

**For text longer than 100 characters:**

```python
def execute(self):
    long_text = """
    Once upon a time, in a magical kingdom far away,
    there lived a brave knight who was ready for adventure.
    The knight lived in a tall castle with towers that touched the sky.
    """
    
    # Automatically splits into chunks
    audio_path = self.tts.google_tts_split(long_text, "story.wav")
    self.play_audio_file(audio_path)
```

### Option 6: Batch Generate Multiple Audio Files

**Create many audio files at once:**

```python
def execute(self):
    # Define all dialogue/instructions
    dialogue = {
        "greeting": "Welcome to Adventure Book",
        "select_story": "Tap a story to begin",
        "story_loaded": "Story is now loaded",
        "tap_play": "Press play to start reading",
        "success": "Great job! Story completed!"
    }
    
    # Generate all at once
    audio_files = self.batch_generate_speech(dialogue)
    # Result: {
    #   "greeting": "audio/greeting.wav",
    #   "select_story": "audio/select_story.wav",
    #   ...
    # }
    
    # Use each audio when needed
    self.play_audio_file(audio_files["greeting"])
    self.step("Select story")
    self.wait_for_text("Select")
    self.play_audio_file(audio_files["select_story"])
```

### Option 7: Direct Audio Utilities (Advanced)

**For more control, use audio utilities directly:**

```python
def execute(self):
    # Generate audio
    audio_path = self.tts.edge_tts("Test message", "test.wav")
    
    # Push to device
    device_path = self.audio.push_audio(audio_path, "test_audio.wav")
    # device_path = "/sdcard/Miko3_Audio/test_audio.wav"
    
    # Play on device
    self.audio.play_audio(device_path)
    
    # Wait for audio
    self.wait(3)
    
    # Stop audio (if needed)
    self.audio.stop_audio()
```

## Complete Example: Storymaker Test with Audio

```python
from miko3_automation.talents.base_talent import BaseTalentTest
import logging

logger = logging.getLogger(__name__)

class StorymakerTalentTest(BaseTalentTest):
    """Storymaker test with TTS narration."""
    
    def execute(self):
        """Execute test with audio guidance."""
        
        # --- Step 1: Dismiss Disclaimer ---
        self.step("Dismiss disclaimer")
        self.play_speech("Let me help you create a story")
        
        if not any(self.tap_text(label) for label in ["Close", "X", "OK"]):
            cross_coords = self.coords.get("disclaimer_cross", [1150, 80])
            self.adb.tap(cross_coords[0], cross_coords[1])
        
        self.wait(2)
        
        # --- Step 2: Start Story Creation ---
        self.step("Start story creation")
        self.play_speech("Now let's create your story")
        
        if not self.tap_text("Create Story"):
            self.adb.tap(640, 600)
        
        self.wait(5)
        
        # --- Step 3: Respond to Idea Prompt ---
        self.step("Respond to idea prompt")
        self.play_speech("Should we use your own idea? Let me decide for you")
        
        self.wait_for_text("idea", timeout=15)
        if not self.tap_text("No"):
            self.adb.tap(400, 600)
        
        self.wait(3)
        
        # --- Step 4: Narrate Miko's Questions ---
        self.step("Narrate conversational creation")
        
        for question_num in range(3):
            # Play a question prompt
            self.play_speech(
                f"Miko is asking question number {question_num + 1}"
            )
            
            # Wait for user to respond (in real test, automate the response)
            self.wait(3)
            
            # Tap answer
            self.tap_text("Next")
            self.wait(2)
        
        # --- Step 5: Complete Story ---
        self.step("Complete story creation")
        self.play_speech("Let's finish creating your story")
        
        self.tap_text("Finish")
        self.wait(3)
        
        self.play_speech("Your story has been created successfully!")
    
    def verify(self):
        """Verify test results."""
        self.verify_activity(self.package_name)
        self.verify_no_crash()


# Usage:
# test = StorymakerTalentTest(adb, config)
# result = test.run()
# print(f"Test {'PASSED' if result.passed else 'FAILED'}")
```

## API Reference

### BaseTalentTest Audio Methods

#### `play_speech(text=None, audio_file=None, wait_seconds=5, provider="edge")`
Play speech on device (generates from text or uses existing audio).

```python
# From text
self.play_speech("Hello world")

# From file
self.play_speech(audio_file="audio/intro.wav")
```

#### `generate_speech(text, filename="speech.wav", provider="edge", **kwargs)`
Generate speech audio file locally.

```python
audio_path = self.generate_speech(
    "Create a story",
    voice="en-US-GuyNeural"  # Edge TTS only
)
```

#### `play_audio_file(audio_path, wait_seconds=5)`
Play an existing audio file.

```python
self.play_audio_file("audio/instruction.wav", wait_seconds=3)
```

#### `batch_generate_speech(texts, provider="edge")`
Generate multiple audio files at once.

```python
audios = self.batch_generate_speech({
    "greeting": "Hello",
    "goodbye": "Thank you"
})
```

#### `record_device_audio(output_filename="recording.wav", duration_seconds=5)`
Record device audio.

```python
device_path = self.record_device_audio(duration_seconds=3)
```

### TextToSpeech Methods

#### `convert(text, output_path, provider="edge", **kwargs)`
Convert text to speech with specified provider.

```python
tts = TextToSpeech()
audio = tts.convert("Hello", "hello.wav", provider="edge")
```

#### `edge_tts(text, output_path, voice="en-US-AriaNeural", rate=1.0)`
Generate speech with Microsoft Edge TTS.

```python
audio = tts.edge_tts(
    "Welcome",
    "welcome.wav",
    voice="en-US-AriaNeural",
    rate=1.2  # Faster
)
```

#### `google_tts(text, output_path, language="en", slow=False)`
Generate speech with Google TTS.

```python
audio = tts.google_tts("Hello", "hello.wav")
```

#### `batch_convert(texts, provider="edge", **kwargs)`
Convert multiple texts to speech.

```python
audios = tts.batch_convert({
    "intro": "Let's begin",
    "end": "Thank you"
})
```

### AudioUtils Methods

#### `push_audio(local_path, device_filename="instruction.wav")`
Push audio from local system to device.

```python
device_path = self.audio.push_audio("audio/intro.wav")
```

#### `play_audio(device_path, wait_for_completion=False)`
Play audio on device.

```python
self.audio.play_audio("/sdcard/Miko3_Audio/intro.wav")
```

#### `play_and_wait(device_path, estimated_duration=5.0)`
Play audio and wait for estimated duration.

```python
self.audio.play_and_wait("/sdcard/Miko3_Audio/intro.wav", 3.0)
```

#### `stop_audio()`
Stop audio playback.

```python
self.audio.stop_audio()
```

#### `set_volume(level)`
Set device volume (0-15).

```python
self.audio.set_volume(10)
```

## Available Voices (Edge TTS)

### English - US
```
Female (Natural):
  - en-US-AriaNeural (default, most natural)
  - en-US-ZiraNeural (alternative)
  - en-US-JennyNeural (younger)

Male:
  - en-US-GuyNeural (most natural)
  - en-US-AmberNeural
  - en-US-AshleyNeural

Child:
  - en-US-KaiNeural
```

### English - UK
```
Female:
  - en-GB-SoniaNeural

Male:
  - en-GB-RyanNeural
```

### List all voices:
```python
self.tts.list_edge_voices()
```

## Troubleshooting

### "ImportError: No module named 'gtts'"

**Solution**:
```bash
pip install gtts
```

### "ImportError: No module named 'edge_tts'"

**Solution**:
```bash
pip install edge-tts
```

### Audio file not found

**Cause**: Generated audio not saved properly

**Solution**:
```python
# Check if file exists
audio_path = self.generate_speech("Hello")
if audio_path and os.path.exists(audio_path):
    print(f"✓ Audio exists: {audio_path}")
else:
    print("✗ Audio not generated")
```

### Audio not playing on device

**Possible causes**:
- Device volume too low
- Audio file not pushed to device
- Wrong device path

**Solution**:
```python
# Set volume
self.audio.set_volume(10)

# Verify push
device_path = self.audio.push_audio("audio/test.wav")
if device_path:
    print(f"✓ Pushed to: {device_path}")
    self.audio.play_audio(device_path)
```

### Low audio quality with Google TTS

**Cause**: Google TTS has lower quality than Edge TTS

**Solution**: Use Edge TTS instead
```python
self.play_speech("Better quality", provider="edge")
```

### Text too long for TTS

**Cause**: Text exceeds provider limits

**Solution**: Use chunk splitting for Google TTS
```python
long_text = "Very long text..."
audio = self.tts.google_tts_split(long_text, "output.wav")
```

## Best Practices

1. **Pre-generate common audio** during setup
   ```python
   def __init__(self, adb, config):
       super().__init__(adb, config, ...)
       # Pre-generate all common messages
       self.audio_cache = self.batch_generate_speech({
           "start": "Let's begin",
           "next": "Moving to next step",
           "done": "Task completed"
       })
   ```

2. **Use Edge TTS for better quality**
   ```python
   # Always prefer Edge TTS
   self.play_speech("Message", provider="edge")
   ```

3. **Cache generated audio**
   ```python
   # Reuse audio file multiple times
   audio = self.generate_speech("Instruction")
   for i in range(5):
       self.play_audio_file(audio)
   ```

4. **Set reasonable wait times**
   ```python
   # ~1 second per 10 words
   self.play_speech("Welcome to the adventure", wait_seconds=3)
   ```

5. **Clean up audio after test**
   ```python
   def teardown(self):
       self.audio.clear_audio_cache()
       super().teardown()
   ```

## File Structure

```
audio/
├── greeting.wav        ← Generated TTS
├── instruction.wav
├── question_1.wav
└── ...

miko3_automation/
├── core/
│   ├── audio_utils.py       ← Audio playback/recording
│   └── tts_utils.py         ← Google & Edge TTS
└── talents/
    └── base_talent.py       ← Audio/TTS convenience methods

reports/
└── screenshots/
    ├── test_1.png
    └── ...
```

## Examples in Your Project

See working examples:
- Audio utilities: [audio_utils.py](miko3_automation/core/audio_utils.py)
- TTS converters: [tts_utils.py](miko3_automation/core/tts_utils.py)
- BaseTalentTest methods: [base_talent.py](miko3_automation/talents/base_talent.py#L463-L535)
