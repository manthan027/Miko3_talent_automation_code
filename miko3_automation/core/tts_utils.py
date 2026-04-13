"""
Text-to-Speech Utilities Module
================================
Provides TTS conversion using Google TTS and Microsoft Edge TTS.
Generates audio files that can be played on Android devices.
"""

import os
import logging
import asyncio
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class TTSProvider(Enum):
    """Available TTS providers."""

    GOOGLE = "google"
    EDGE = "edge"


class TextToSpeech:
    """
    Multi-provider TTS conversion (Google TTS and Edge TTS).

    Usage:
        tts = TextToSpeech()
        audio_path = tts.convert("Hello, let's create a story")
        
        # Or with specific provider:
        audio_path = tts.google_tts("Hello world", "output.wav")
        audio_path = tts.edge_tts("Hello world", "output.wav")
    """

    def __init__(self, output_dir: str = "audio"):
        """
        Initialize TTS converter.

        Args:
            output_dir: Directory to save generated audio files.
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"✓ TTS output directory: {output_dir}")

    def _ensure_output_path(self, output_path: str) -> str:
        """Ensure output directory exists."""
        os.makedirs(os.path.dirname(output_path) or self.output_dir, exist_ok=True)
        return output_path

    # =========================================================================
    # Google TTS
    # =========================================================================

    def google_tts(
        self,
        text: str,
        output_path: str = "speech.wav",
        language: str = "en",
        slow: bool = False,
    ) -> Optional[str]:
        """
        Convert text to speech using Google TTS (free, no API key needed).

        Google TTS is reliable and free but has limitations:
        - Max ~100-200 characters per request
        - No voice customization
        - Basic quality

        Args:
            text: Text to convert.
            output_path: Where to save the audio file.
            language: Language code (e.g., "en", "es", "fr").
            slow: Slower speech rate if True.

        Returns:
            Path to generated audio file, or None on failure.

        Example:
            tts = TextToSpeech()
            audio = tts.google_tts(
                "Let's create an adventure story",
                "audio/intro.wav"
            )

        Note:
            Requires internet connection and gtts library:
            pip install gtts
        """
        if not text or not text.strip():
            logger.error("Text cannot be empty")
            return None

        if len(text) > 500:
            logger.warning(
                f"Text is {len(text)} chars (max ~500 recommended). "
                "Consider splitting into smaller chunks."
            )

        output_path = self._ensure_output_path(output_path)

        try:
            from gtts import gTTS

            logger.debug(
                f"Generating speech with Google TTS: '{text[:50]}...' → {output_path}"
            )
            tts = gTTS(text=text, lang=language, slow=slow)
            tts.save(output_path)

            size_kb = os.path.getsize(output_path) / 1024
            logger.info(f"✓ Generated audio: {output_path} ({size_kb:.1f} KB)")
            return output_path

        except ImportError:
            logger.error(
                "Google TTS not available. Install: pip install gtts"
            )
            return None
        except Exception as e:
            logger.error(f"✗ Google TTS conversion failed: {e}")
            return None

    def google_tts_split(
        self,
        text: str,
        output_path: str = "speech.wav",
        language: str = "en",
        chunk_size: int = 100,
    ) -> Optional[str]:
        """
        Convert long text by splitting into chunks (overcomes length limits).

        Args:
            text: Long text to convert.
            output_path: Where to save combined audio.
            language: Language code.
            chunk_size: Characters per chunk (max ~100-200).

        Returns:
            Path to combined audio file.

        Example:
            audio = tts.google_tts_split(
                "This is a very long story that needs splitting...",
                "audio/long_story.wav"
            )

        Note:
            Requires ffmpeg for concatenation:
            pip install pydub
        """
        if len(text) <= chunk_size:
            return self.google_tts(text, output_path, language)

        logger.info(f"Splitting text into {chunk_size}-char chunks")
        chunks = [
            text[i : i + chunk_size]
            for i in range(0, len(text), chunk_size)
        ]

        try:
            from pydub import AudioSegment

            combined = AudioSegment.empty()
            chunk_files = []

            for idx, chunk in enumerate(chunks):
                chunk_file = (
                    f"{self.output_dir}/chunk_{idx:03d}.wav"
                )
                if self.google_tts(chunk, chunk_file, language):
                    chunk_files.append(chunk_file)
                    # Add small silence between chunks
                    combined += AudioSegment.from_wav(chunk_file)
                    combined += AudioSegment.silent(duration=200)

            if chunk_files:
                combined.export(output_path, format="wav")
                logger.info(f"✓ Combined {len(chunk_files)} chunks: {output_path}")

                # Cleanup chunk files
                for chunk_file in chunk_files:
                    try:
                        os.remove(chunk_file)
                    except:
                        pass

                return output_path
            else:
                logger.error("Failed to generate any chunks")
                return None

        except ImportError:
            logger.error(
                "Audio concatenation requires pydub: pip install pydub"
            )
            return None
        except Exception as e:
            logger.error(f"✗ Chunk concatenation failed: {e}")
            return None

    # =========================================================================
    # Microsoft Edge TTS
    # =========================================================================

    def edge_tts(
        self,
        text: str,
        output_path: str = "speech.wav",
        voice: str = "en-US-AriaNeural",
        rate: float = 1.0,
    ) -> Optional[str]:
        """
        Convert text to speech using Microsoft Edge TTS (free, high quality).

        Edge TTS offers:
        - Natural-sounding voices
        - Voice customization (male/female/neutral)
        - Speed control
        - No API key required
        - Better quality than Google

        Args:
            text: Text to convert.
            output_path: Where to save the audio file.
            voice: Voice to use (see EDGE_VOICES for options).
            rate: Speech rate (0.5 = slower, 2.0 = faster).

        Returns:
            Path to generated audio file, or None on failure.

        Example:
            tts = TextToSpeech()
            
            # Female voice (natural)
            audio = tts.edge_tts(
                "Let's create an adventure",
                "audio/intro.wav",
                voice="en-US-AriaNeural"
            )
            
            # Male voice
            audio = tts.edge_tts(
                "Hello there",
                "audio/greeting.wav",
                voice="en-US-GuyNeural"
            )

        Note:
            Requires internet connection. Install: pip install edge-tts

            Available voices (English - US):
                Female: AriaNeural, ZiraNeural, JennyNeural
                Male: GuyNeural, AmberNeural, AshleyNeural
                Child: KaiNeural, BrianNeural
        """
        if not text or not text.strip():
            logger.error("Text cannot be empty")
            return None

        output_path = self._ensure_output_path(output_path)

        try:
            import edge_tts

            logger.debug(
                f"Generating speech with Edge TTS ({voice}): "
                f"'{text[:50]}...' → {output_path}"
            )

            async def save_audio():
                # Edge TTS requires rate to be a string (e.g., "+0%", "+10%", "-10%")
                # If rate is float (1.0 = normal), convert to percentage string
                rate_str = f"{rate - 1:+.0%}" if isinstance(rate, (int, float)) else rate
                
                communicate = edge_tts.Communicate(
                    text=text, voice=voice, rate=rate_str
                )
                await communicate.save(output_path)

            asyncio.run(save_audio())

            size_kb = os.path.getsize(output_path) / 1024
            logger.info(
                f"✓ Generated audio ({voice}): {output_path} ({size_kb:.1f} KB)"
            )
            return output_path

        except ImportError:
            logger.error(
                "Edge TTS not available. Install: pip install edge-tts"
            )
            return None
        except Exception as e:
            logger.error(f"✗ Edge TTS conversion failed: {e}")
            return None

    # =========================================================================
    # Voice Lists
    # =========================================================================

    @staticmethod
    def get_edge_voices() -> dict:
        """Get available Edge TTS voices grouped by language/gender."""
        return {
            "en_US_female": [
                "en-US-AriaNeural",  # Default, natural
                "en-US-ZiraNeural",  # Alternative female
                "en-US-JennyNeural",  # Younger female
            ],
            "en_US_male": [
                "en-US-GuyNeural",  # Natural male
                "en-US-AmberNeural",  # Another option
                "en-US-AshleyNeural",  # Neutral
            ],
            "en_US_child": [
                "en-US-KaiNeural",  # Child
            ],
            "en_GB_female": [
                "en-GB-SoniaNeural",  # UK female
            ],
            "en_GB_male": [
                "en-GB-RyanNeural",  # UK male
            ],
        }

    @staticmethod
    def list_edge_voices() -> None:
        """Print available Edge TTS voices."""
        voices = TextToSpeech.get_edge_voices()
        print("\nAvailable Edge TTS Voices:")
        print("=" * 50)
        for category, voice_list in voices.items():
            print(f"\n{category}:")
            for voice in voice_list:
                print(f"  - {voice}")

    # =========================================================================
    # Smart Conversion (Auto-select best provider)
    # =========================================================================

    def convert(
        self,
        text: str,
        output_path: str = "speech.wav",
        provider: str = "edge",
        **kwargs
    ) -> Optional[str]:
        """
        Convert text to speech using specified provider.

        Args:
            text: Text to convert.
            output_path: Where to save audio.
            provider: "google" or "edge" (default: "edge").
            **kwargs: Provider-specific options (voice, language, etc).

        Returns:
            Path to generated audio file.

        Example:
            tts = TextToSpeech()
            
            # Use Edge TTS (recommended)
            audio = tts.convert("Hello", "hello.wav", provider="edge")
            
            # Use Google TTS
            audio = tts.convert("Hello", "hello.wav", provider="google")
        """
        if provider.lower() == "edge":
            return self.edge_tts(text, output_path, **kwargs)
        elif provider.lower() == "google":
            return self.google_tts(text, output_path, **kwargs)
        else:
            logger.error(f"Unknown provider: {provider}")
            return None

    # =========================================================================
    # Batch Processing
    # =========================================================================

    def batch_convert(
        self,
        texts: dict,
        provider: str = "edge",
        **kwargs
    ) -> dict:
        """
        Convert multiple texts to speech.

        Args:
            texts: Dict of {name: text} pairs.
            provider: TTS provider to use.
            **kwargs: Provider-specific options.

        Returns:
            Dict of {name: audio_path} with conversion results.

        Example:
            tts = TextToSpeech()
            texts = {
                "greeting": "Welcome to the adventure",
                "instruction": "Tap the button to start",
                "confirmation": "Great job!"
            }
            audio_files = tts.batch_convert(texts)
            # Result: {
            #   "greeting": "audio/greeting.wav",
            #   "instruction": "audio/instruction.wav",
            #   "confirmation": "audio/confirmation.wav"
            # }
        """
        results = {}
        total = len(texts)

        logger.info(f"Converting {total} texts to speech using {provider} TTS")

        for idx, (name, text) in enumerate(texts.items()):
            logger.debug(f"[{idx+1}/{total}] Converting: {name}")
            output_path = os.path.join(
                self.output_dir, f"{name}.wav"
            )
            result = self.convert(text, output_path, provider, **kwargs)
            results[name] = result

        successful = sum(1 for r in results.values() if r is not None)
        logger.info(f"✓ Converted {successful}/{total} texts successfully")

        return results
