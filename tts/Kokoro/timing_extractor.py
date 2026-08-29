"""Build sentence timing metadata from per-sentence phoneme durations."""

from typing import Dict, Iterable, List


def extract_timings(sentences: Iterable[Dict], synthesis_sentences: Iterable[Dict]) -> List[Dict]:
    """Return cumulative sentence timings in seconds."""
    sentence_list = list(sentences)
    synthesis_list = list(synthesis_sentences)
    if len(sentence_list) != len(synthesis_list):
        raise ValueError("Sentence and synthesis result counts do not match")

    timings = []
    current_time = 0.0
    for sentence, result in zip(sentence_list, synthesis_list):
        duration = float(result["phoneme_duration"])
        start_time = current_time
        end_time = start_time + duration
        timings.append({
            "id": sentence["id"],
            "sentence": sentence["text"],
            "paragraph_id": sentence["paragraph_id"],
            "word_count": sentence["word_count"],
            "start_time": round(start_time, 3),
            "end_time": round(end_time, 3),
            "duration": round(duration, 3),
            "phoneme_count": result["phoneme_count"],
        })
        current_time = end_time
    return timings