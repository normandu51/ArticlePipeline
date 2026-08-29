"""Kokoro synthesis with sentence-level phoneme durations."""

from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np
import soundfile as sf

try:
    from tts.Kokoro.kokoro_local import build_pipeline, resolve_voice
except ImportError:  # run as a plain script
    from tts.Kokoro.kokoro_local import build_pipeline, resolve_voice


SAMPLE_RATE = 24000
PHONEME_DURATION_SCALE = 40.0


def _as_numpy(audio) -> np.ndarray:
    if hasattr(audio, "detach"):
        audio = audio.detach().cpu().numpy()
    return np.asarray(audio, dtype=np.float32).reshape(-1)


def synthesize_sentences(
    sentences: Iterable[Dict],
    output_path: str,
    speaker: str = "am",
    lang: str = "a",
) -> Dict:
    """Synthesize each sentence and concatenate chunks into one WAV file."""
    sentence_list = list(sentences)
    if not sentence_list:
        raise ValueError("No sentences to synthesize")

    pipeline = build_pipeline(lang)
    voice = resolve_voice(speaker)
    audio_chunks: List[np.ndarray] = []
    sentence_results = []
    for sentence in sentence_list:
        result = next(pipeline(sentence["text"], voice=voice, split_pattern=None))
        if result.audio is None or result.pred_dur is None:
            raise RuntimeError(f"Kokoro returned no audio for sentence {sentence['id']}")
        audio = _as_numpy(result.audio)
        pred_dur = result.pred_dur.detach().cpu().numpy()
        audio_length = len(audio)
        # phoneme_duration = float(pred_dur.sum()) / PHONEME_DURATION_SCALE
        duration = audio_length / SAMPLE_RATE
        audio_chunks.append(audio)
        sentence_results.append({
            "id": sentence["id"],
            "phonemes": result.phonemes,
            "phoneme_count": len(result.phonemes),
            "phoneme_duration": duration,
            "audio_samples": audio_length,
        })

    audio_file = Path(output_path)
    audio_file.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(audio_file), np.concatenate(audio_chunks), SAMPLE_RATE)
    return {"audio_file": str(audio_file), "sentences": sentence_results}