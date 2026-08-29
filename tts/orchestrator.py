"""CLI for generating article audio and sentence timing JSON."""

import argparse
import json
from datetime import datetime
from pathlib import Path

try:
    from tts.Kokoro.text_processor import read_and_parse
    from tts.Kokoro.timing_extractor import extract_timings
    from tts.Kokoro.tts_synthesizer import synthesize_sentences
except ImportError:
    from text_processor import read_and_parse
    from timing_extractor import extract_timings
    from tts_synthesizer import synthesize_sentences


def generate_audio_and_timings(input_file: str, output_dir: str = "tts", speaker: str = "am", lang: str = "a"):
    input_path = Path(input_file)
    sentences = read_and_parse(str(input_path))
    if not sentences:
        raise ValueError(f"No sentences found in {input_path}")

    output_path = Path(output_dir)
    audio_file = output_path / f"{input_path.stem}_kokoro.wav"
    timings_file = output_path / f"{input_path.stem}_timings.json"
    synthesis = synthesize_sentences(sentences, str(audio_file), speaker=speaker, lang=lang)
    timings = extract_timings(sentences, synthesis["sentences"])
    total_duration = timings[-1]["end_time"] if timings else 0.0
    data = {
        "metadata": {
            "source_file": str(input_path),
            "audio_file": str(audio_file),
            "total_duration": total_duration,
            "sentence_count": len(timings),
            "paragraph_count": len({item["paragraph_id"] for item in sentences}),
            "speaker": speaker,
            "language": lang,
            "generated_at": datetime.now().isoformat(),
        },
        "sentences": timings,
    }
    with timings_file.open("w", encoding="utf-8") as timing_file:
        json.dump(data, timing_file, indent=2)
    return str(audio_file), str(timings_file)


def main():
    parser = argparse.ArgumentParser(description="Generate Kokoro audio and sentence timings")
    parser.add_argument("input_file")
    parser.add_argument("output_dir", nargs="?", default="Output")
    parser.add_argument("--speaker", default="am")
    parser.add_argument("--lang", default="a")
    args = parser.parse_args()
    audio_file, timings_file = generate_audio_and_timings(args.input_file, args.output_dir, args.speaker, args.lang)
    print(f"Audio: {audio_file}")
    print(f"Timings: {timings_file}")


if __name__ == "__main__":
    main()