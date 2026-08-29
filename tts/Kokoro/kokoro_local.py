"""Load Kokoro entirely from the local tts/Kokoro-82M checkout (no network).

The pre-downloaded model lives in tts/Kokoro-82M/:
  - config.json
  - kokoro-v1_0.pth
  - voices/*.pt

These helpers build a KModel/KPipeline from those local files so no
HuggingFace Hub download is attempted, which is required when the
machine has no (or flaky) network access.
"""

import os
from pathlib import Path

import espeakng_loader
import torch
from kokoro import KModel, KPipeline

# The bundled libespeak-ng is compiled with a data path baked in from its CI
# build machine (e.g. /Users/runner/work/.../espeak-ng-data), which does not
# exist locally. Point it at the installed espeak-ng-data so English G2P works
# offline. Must be set before the first phonemizer backend is created.
os.environ.setdefault("ESPEAK_DATA_PATH", espeakng_loader.get_data_path())

# Directory holding the pre-downloaded Kokoro-82M model files.
KOKORO_DIR = Path(__file__).resolve().parent / "Kokoro-82M"
CONFIG_PATH = KOKORO_DIR / "config.json"
MODEL_PATH = KOKORO_DIR / "kokoro-v1_0.pth"
VOICES_DIR = KOKORO_DIR / "voices"

# When the requested speaker is just a gender/prefix code (e.g. "am"), use a
# concrete default voice from the local voices/ folder.
PREFIX_DEFAULT_VOICE = {
    "af": "af_bella",
    "am": "am_michael",
    "bf": "bf_alice",
    "bm": "bm_george",
    "ef": "ef_dora",
    "em": "em_alex",
    "ff": "ff_siwis",
    "hf": "hf_alpha",
    "hm": "hm_omega",
    "if": "if_sara",
    "im": "im_nicola",
    "jf": "jf_alpha",
    "jm": "jm_kumo",
    "pf": "pf_dora",
    "pm": "pm_alex",
    "zf": "zf_xiaoxiao",
    "zm": "zm_yunyang",
}


def build_pipeline(lang: str = "a") -> KPipeline:
    """Create a KPipeline backed by the local model, without any network access."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = KModel(config=str(CONFIG_PATH), model=str(MODEL_PATH)).to(device).eval()
    return KPipeline(lang_code=lang, model=model)


def resolve_voice(speaker: str) -> str:
    """Resolve a speaker name to a local voices/*.pt path (no HF download).

    Accepts a full voice name (e.g. "af_bella"), a path ending in ".pt", or a
    gender/prefix code (e.g. "am") which is mapped to a concrete default voice.
    """
    if speaker.endswith(".pt"):
        candidate = Path(speaker)
        if not candidate.is_absolute():
            candidate = VOICES_DIR / candidate.name
        if candidate.is_file():
            return str(candidate)
    candidate = VOICES_DIR / f"{speaker}.pt"
    if candidate.is_file():
        return str(candidate)
    default = PREFIX_DEFAULT_VOICE.get(speaker)
    if default:
        candidate = VOICES_DIR / f"{default}.pt"
        if candidate.is_file():
            return str(candidate)
    available = ", ".join(sorted(p.stem for p in VOICES_DIR.glob("*.pt")))
    raise FileNotFoundError(
        f"Voice '{speaker}' not found locally under {VOICES_DIR}. "
        f"Available voices: {available}"
    )
