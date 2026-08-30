# TTS Article with Sentence-Level Timing - Design Document

**Date:** 2026-08-13  
**Project:** ArticleExtraction  
**Objective:** Generate audio from article text files with precise sentence-level timing data for UI synchronization  

---

## 1. Overview

Build a modular pipeline system that:
1. Reads article text (line = paragraph)
2. Splits into sentences using regex
3. Generates audio via Kokoro TTS (American Male speaker)
4. Extracts phoneme-level timing data
5. Maps sentences to audio timestamps
6. Outputs WAV audio + JSON timing metadata

**Deliverables:**
- `Steady_pvc.wav` - 24kHz mono WAV audio
- `Steady_pvc_timings.json` - Array of sentence timing entries with metadata

---

## 2. Requirements

### Functional Requirements
- **FR1:** Read text file, parse by paragraph (one line = one paragraph)
- **FR2:** Split paragraphs into sentences using regex (`(?<=[.!?])\s+(?=[A-Z])`)
- **FR3:** Generate speech audio using Kokoro TTS (speaker='am' for American Male)
- **FR4:** Extract phoneme durations from Kokoro pipeline output
- **FR5:** Map sentences to audio timestamps using phoneme-level precision
- **FR6:** Generate JSON output with timing + metadata per sentence
- **FR7:** Graceful error handling with user-friendly messages

### Non-Functional Requirements
- **NFR1:** Modular design - each component usable independently
- **NFR2:** Testable - unit tests for text splitting and timing extraction
- **NFR3:** Scalable - same pipeline works for any article
- **NFR4:** Performance - complete Steady_pvc.txt in < 30 seconds

---

## 3. Architecture

### 3.1 System Components

```
Input: article.txt
         ↓
    [text_processor.py]
    └─ Parse text, split sentences, track metadata
         ↓
    [tts_synthesizer.py]
    └─ Kokoro TTS, extract phoneme data
         ↓
    [timing_extractor.py]
    └─ Map sentences → phoneme ranges → audio timestamps
         ↓
    [orchestrator.py]
    └─ Coordinate all components, write outputs
         ↓
    Output: audio.wav + timings.json
```

### 3.2 Module Responsibilities

**text_processor.py**
- `read_and_parse(file_path)` → list of `Sentence` objects
- Regex-based sentence splitting
- Track character positions, paragraph IDs, word counts
- Return: `List[Sentence]` where `Sentence = {id, text, paragraph_id, start_char, end_char, word_count}`

**tts_synthesizer.py**
- `synthesize(text, speaker='am')` → (phonemes, durations, audio_path)
- Initialize Kokoro KPipeline with speaker parameter
- Join all sentences into single text
- Call `pipeline(text, speaker)` → returns `(phonemes, tokens, durations)`
- Save audio to WAV file
- Return: `{phonemes: List[str], durations: List[float], tokens: List, audio_file: str}`

**timing_extractor.py**
- `extract_timings(sentences, phonemes, durations)` → List of timing entries
- For each sentence: find character span in full text
- Calculate which phonemes fall within that sentence
- Compute: `start_time = sum(durations[0:first_idx])`, `end_time = sum(durations[0:last_idx])`
- Include metadata: id, paragraph_id, word_count, phoneme_count
- Return: `List[TimingEntry]` where `TimingEntry = {id, sentence, paragraph_id, word_count, start_time, end_time, duration, phoneme_count}`

**orchestrator.py**
- `main(input_file, output_dir='tts/')`
- Coordinate: process_text → synthesize → extract_timings
- Write outputs: `{basename}_kokoro.wav` + `{basename}_timings.json`
- CLI interface: `python orchestrator.py tts/Steady_pvc.txt`

---

## 4. Data Structures

### 4.1 Sentence Object (from text_processor)
```python
{
    "id": 0,                    # 0-indexed sentence number
    "text": "It's tempting...",
    "paragraph_id": 0,          # which paragraph (0-indexed)
    "start_char": 0,            # char position in full text
    "end_char": 85,             # char position in full text
    "word_count": 15
}
```

### 4.2 Phoneme Data (from tts_synthesizer)
```python
{
    "phonemes": ["IH", "T", "S", "T", "EH", ...],  # phoneme labels
    "durations": [0.05, 0.02, 0.08, 0.03, ...],    # seconds per phoneme
    "tokens": [...],                                # token indices
    "audio_file": "audio/Steady_pvc_kokoro.wav"
}
```

### 4.3 Timing Entry (in output JSON)
```python
{
    "id": 0,
    "sentence": "It's tempting to believe that physicians are logical...",
    "paragraph_id": 0,
    "word_count": 15,
    "start_time": 0.0,      # seconds (float)
    "end_time": 3.45,       # seconds (float)
    "duration": 3.45,       # end_time - start_time
    "phoneme_count": 42     # phonemes in this sentence
}
```

### 4.4 Output JSON Structure
```json
{
    "metadata": {
        "source_file": "audio/Steady_pvc.txt",
        "audio_file": "audio/Steady_pvc_kokoro.wav",
        "total_duration": 156.34,
        "sentence_count": 18,
        "paragraph_count": 6,
        "speaker": "am",
        "language": "a",
        "generated_at": "2026-08-13T10:30:00Z"
    },
    "sentences": [
        { "id": 0, "sentence": "...", "paragraph_id": 0, ... },
        { "id": 1, "sentence": "...", "paragraph_id": 0, ... },
        ...
    ]
}
```

---

## 5. Algorithms

### 5.1 Text Processing Algorithm
1. Read input file line-by-line
2. For each line (paragraph):
   - Split using regex `(?<=[.!?])\s+(?=[A-Z])`
   - For each sentence:
     - Create Sentence object with metadata
     - Track character positions in accumulated full text
3. Return list of Sentence objects

**Edge cases:**
- Empty lines: skip
- Paragraph with no sentence-ending punctuation: treat as single sentence
- Multiple spaces/newlines: normalize

### 5.2 Synthesis Algorithm
1. Join all sentences with single space: `full_text = " ".join([s.text for s in sentences])`
2. Initialize Kokoro pipeline: `pipeline = KPipeline(lang_code='a')`
3. Run synthesis: `phonemes, tokens, durations = pipeline(full_text, speaker='am')`
4. Save audio: `pipeline.save(output_path)`
5. Return phoneme data

**Note:** Kokoro returns phoneme durations in order of phoneme sequence

### 5.3 Timing Extraction Algorithm (Critical)
**Goal:** Map each sentence's character span to its phoneme indices, then calculate timestamps

1. Recreate character-to-phoneme mapping:
   - Kokoro processes text and assigns phonemes to character positions
   - We need to track: at character position X, which phoneme index starts?
   
2. For each sentence in order:
   - Find `char_start` and `char_end` in full text
   - Determine which phonemes span this range
   - Calculate cumulative time: 
     - `start_time = sum(durations[0:phoneme_start_idx])`
     - `end_time = sum(durations[0:phoneme_end_idx])`
   - Create timing entry

3. Fallback logic:
   - If phoneme-to-char mapping is ambiguous, log warning
   - Use proportional distribution as fallback

**Complexity:** O(n) where n = number of sentences

---

## 6. Error Handling

| Error Scenario | Handling |
|---|---|
| Input file not found | Exit with message: "File not found: {path}" |
| Kokoro model not available | Attempt download, fail gracefully with link to docs |
| Kokoro synthesis timeout | Retry with progress indicator, fail after 3 attempts |
| Empty text after parsing | Exit with message: "No sentences found in {file}" |
| Phoneme/text mismatch | Log warning, use proportional fallback for affected sentences |
| Disk write failure | Exit with message: "Cannot write to {path}: {error}" |

---

## 7. Testing Strategy

### 7.1 Unit Tests
- **test_text_processor.py**
  - Test sentence splitting on sample text with edge cases
  - Verify character positions are accurate
  - Test paragraph tracking

- **test_timing_extractor.py**
  - Test phoneme-to-character mapping
  - Test cumulative duration calculation
  - Test edge cases (single phoneme, boundary conditions)

### 7.2 Integration Tests
- **test_orchestrator.py**
  - End-to-end on Steady_pvc.txt
  - Verify output files exist and are valid
  - Check JSON structure and timing order
  - Spot-check: sentence 0 starts at 0.0, timings increase monotonically

### 7.3 Validation Checks
- Audio file duration ≈ sum of all sentence durations
- All sentences have start_time < end_time
- Sentences are in chronological order
- JSON is valid and parseable

---

## 8. Output Files

**Location:** `/Users/pengdu/PycharmProjects/ArticleExtraction/tts/`

| File | Format | Purpose |
|---|---|---|
| `Steady_pvc_kokoro.wav` | WAV (24kHz, mono) | Audio output from Kokoro |
| `Steady_pvc_timings.json` | JSON | Timing data + metadata |

---

## 9. Future Extensibility

- **Multiple TTS engines:** Swap `tts_synthesizer.py` for different TTS (Google, Azure, etc.)
- **Batch processing:** Add wrapper to process multiple articles
- **VTT export:** Convert JSON to VTT subtitle format
- **Web UI:** Frontend to visualize audio with highlighting
- **Performance optimization:** Cache Kokoro model, parallel processing

---

## 10. Success Criteria

- ✅ Produces valid WAV audio file from Steady_pvc.txt
- ✅ JSON has correct timing for all sentences
- ✅ Audio duration matches sum of sentence durations (within ±2% tolerance)
- ✅ Modular code - each module independently testable
- ✅ Clear error messages for all failure cases
- ✅ README with usage examples

---

## Appendix: Example Usage

```bash
# Activate environment
source .venv/bin/activate

# Generate audio + timings
python tts/DBArticles2Audios.py tts/Steady_pvc.txt

# Outputs:
# - tts/Steady_pvc_kokoro.wav
# - tts/Steady_pvc_timings.json

# View timings
cat tts/Steady_pvc_timings.json | python -m json.tool | head -50
```

**Example JSON output (first 2 entries):**
```json
{
  "metadata": {
    "source_file": "tts/Steady_pvc.txt",
    "total_duration": 156.34,
    "sentence_count": 18
  },
  "sentences": [
    {
      "id": 0,
      "sentence": "It's tempting to believe that physicians are logical, meticulous thinkers who perfectly weigh the pros and cons of treatment options, acting as unbiased surrogates for their patients.",
      "paragraph_id": 0,
      "word_count": 31,
      "start_time": 0.0,
      "end_time": 8.52,
      "duration": 8.52,
      "phoneme_count": 156
    },
    {
      "id": 1,
      "sentence": "In reality, this is often far from the case.",
      "paragraph_id": 1,
      "word_count": 9,
      "start_time": 8.54,
      "end_time": 11.23,
      "duration": 2.69,
      "phoneme_count": 48
    }
  ]
}
```
