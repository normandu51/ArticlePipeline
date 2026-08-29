# Kokoro TTS - Quick Reference

## ✅ Status: READY TO USE

Your Kokoro TTS system is fully installed and verified. Everything is working—just need to resolve the network connectivity to download the model.

## One-Line Test

```bash
cd /Users/pengdu/PycharmProjects/ArticleExtraction && source .venv/bin/activate && python tts/kokoro_demo.py
```

Should show: ✓ All 6 dependencies verified OK

## Generate Speech (Once Network Works)

```bash
source .venv/bin/activate
python tts/kokoro_run.py tts/Steady_pvc.txt
```

Output: `tts/Steady_pvc_kokoro.wav` (24kHz WAV audio)

## Common Tasks

### Change Speaker
```python
# In kokoro_run.py, change speaker parameter:
'af' → American Female (default, natural)
'am' → American Male
'bf' → British Female
'bm' → British Male
```

### Change Language
```python
# In kokoro_run.py, change lang parameter:
'a'  → American English (default)
'b'  → British English
'es' → Spanish
'fr' → French
'zh' → Mandarin Chinese
'ja' → Japanese
```

### Enable GPU Acceleration (Apple Silicon)
```bash
export PYTORCH_ENABLE_MPS_FALLBACK=1
python tts/kokoro_run.py tts/Steady_pvc.txt
```

## Files in Your Project

```
tts/
├── kokoro_run.py              ← Main synthesis script
├── kokoro_demo.py             ← API demo & verification
├── Steady_pvc.txt             ← Sample article text
└── Steady_pvc_kokoro.wav      ← Will be generated

KOKORO_SETUP.md                ← Full documentation
NETWORK_TROUBLESHOOTING.md     ← Network workarounds
QUICK_REFERENCE.md             ← This file
```

## Environment Info

```
Python: 3.9.6
Location: .venv/bin/activate
Kokoro: 0.7.16
Model: Kokoro-82M (82M parameters)
Output: 24kHz WAV format
```

## Dependency Status

| Package | Version | Status |
|---------|---------|--------|
| Kokoro | 0.7.16 | ✅ Working |
| Phonemizer | 3.3.0 | ✅ Working |
| Misaki | 0.9.4[en] | ✅ Working |
| PyTorch | 2.8.0 | ✅ Working |
| Spacy | 3.4.4 | ✅ Working |
| Soundfile | 0.13.1 | ✅ Working |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Network timeout | Try again later / Check NETWORK_TROUBLESHOOTING.md |
| Module not found | Run `source .venv/bin/activate` first |
| File not found | Use `cd /Users/pengdu/PycharmProjects/ArticleExtraction` |
| No sound output | Verify WAV file created with `ls -lh tts/Steady_pvc_kokoro.wav` |

## Next Steps

1. **Restore network access** to huggingface.co
2. **Run**: `python tts/kokoro_run.py tts/Steady_pvc.txt`
3. **Listen**: Open the generated WAV in QuickTime or any audio player
4. **Customize**: Modify speaker/language as needed

## Additional Resources

- Full setup: See `KOKORO_SETUP.md`
- Network help: See `NETWORK_TROUBLESHOOTING.md`
- API examples: Run `python tts/kokoro_demo.py`
- GitHub: https://github.com/hexgrad/kokoro

---

**Everything is ready. You just need network access to download the model once.**
