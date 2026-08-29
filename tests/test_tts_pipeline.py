from tts.Kokoro.text_processor import read_and_parse, split_sentences
from tts.Kokoro.timing_extractor import extract_timings


def test_split_sentences_uses_requested_regex():
    text = "First sentence. Second sentence! Third sentence?"
    assert split_sentences(text) == [
        "First sentence.",
        "Second sentence!",
        "Third sentence?",
    ]


def test_read_and_parse_tracks_paragraph_metadata(tmp_path):
    article = tmp_path / "article.txt"
    article.write_text("First paragraph. It has two sentences.\nSecond paragraph.", encoding="utf-8")

    sentences = read_and_parse(str(article))

    assert [item["id"] for item in sentences] == [0, 1, 2]
    assert [item["paragraph_id"] for item in sentences] == [0, 0, 1]
    assert sentences[0]["word_count"] == 2
    assert sentences[1]["start_char"] > sentences[0]["end_char"]


def test_extract_timings_uses_phoneme_durations_directly():
    sentences = [
        {"id": 0, "text": "One.", "paragraph_id": 0, "word_count": 1},
        {"id": 1, "text": "Two.", "paragraph_id": 0, "word_count": 1},
    ]
    synthesis = [
        {"phoneme_duration": 1.125, "phoneme_count": 4},
        {"phoneme_duration": 2.375, "phoneme_count": 8},
    ]

    timings = extract_timings(sentences, synthesis)

    assert timings[0]["start_time"] == 0.0
    assert timings[0]["end_time"] == 1.125
    assert timings[1]["start_time"] == 1.125
    assert timings[1]["end_time"] == 3.5
    assert timings[1]["phoneme_count"] == 8