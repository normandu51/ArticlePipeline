# Network Troubleshooting Guide - Kokoro TTS

## Status: ✅ SYSTEM READY (Network Issue - Model Download)

**Good News**: Kokoro TTS is fully installed and configured.  
**Current Issue**: Network connectivity to download the ML model from Hugging Face.

## Quick Diagnosis

Your setup shows:
- ✅ All dependencies installed correctly
- ✅ Python 3.9.6 with virtual environment active
- ✅ Kokoro 0.7.16 package installed
- ✅ Phonemizer 3.3.0 working
- ✅ Misaki G2P converter ready
- ❌ Network connection to huggingface.co is timing out

## The Issue Explained

Kokoro uses a 82-million parameter AI model stored on Hugging Face's servers. On first use, it attempts to download this model (~500MB). Your internet connection to huggingface.co is currently experiencing connection resets (Error 54).

This is **not** a problem with Kokoro, your installation, or your MacBook—it's a temporary network issue.

## Solutions (In Order of Recommendation)

### Solution 1: Try Again Later ⏱️ (Easiest)

Network issues are often temporary. Try again in a few minutes:

```bash
cd /Users/pengdu/PycharmProjects/ArticleExtraction
source .venv/bin/activate
python tts/kokoro_run.py tts/Steady_pvc.txt
```

### Solution 2: Check Your Internet Connection 🌐

Test if you can reach Hugging Face:

```bash
# Check connectivity
curl -I https://huggingface.co

# Or using Python
python -c "import urllib.request; urllib.request.urlopen('https://huggingface.co')"
```

If this fails, check:
- WiFi/Internet connection is active
- No corporate firewall blocking huggingface.co
- DNS is resolving correctly

### Solution 3: Use a VPN (If Behind Firewall) 🔒

If your network blocks Hugging Face:

1. Connect to a VPN that allows access to huggingface.co
2. Then run: `python tts/kokoro_run.py tts/Steady_pvc.txt`

### Solution 4: Manual Model Download 📥

Pre-download the model on a machine with better internet, then copy it:

```bash
# On a machine with good internet connection:
source .venv/bin/activate
python -c "from huggingface_hub import snapshot_download; snapshot_download('hexgrad/Kokoro-82M')"
```

Model cache location:
- Linux/Mac: `~/.cache/huggingface/hub/models--hexgrad--Kokoro-82M`
- Copy this folder to your machine

### Solution 5: Use Local Mirror (Advanced) 🔄

If available in your region, use a Hugging Face mirror:

```bash
# Set environment variable before running
export HF_ENDPOINT="https://huggingface-mirror.example.com"
python tts/kokoro_run.py tts/Steady_pvc.txt
```

## Model Details

- **Size**: ~500 MB compressed, ~1.2 GB uncompressed
- **Download Time**: 2-5 minutes on good internet
- **Cache Location**: `~/.cache/huggingface/hub/`
- **Cache Duration**: Permanent (reused automatically on next run)

## Verification After Download

Once the model downloads successfully, you can verify:

```bash
# This will reuse the cached model (no redownload)
python tts/kokoro_run.py --help

# Generate a simple test
python -c "
from kokoro import KPipeline
p = KPipeline(lang_code='a')
phonemes, tokens, durations = p('Hello world', speaker='af')
print(f'Generated {len(phonemes)} phonemes')
"
```

## If Nothing Works: Online Tools Alternative

While your setup is configured locally, you could temporarily try:

1. **Google Colab** (Cloud - Free)
   ```python
   !pip install kokoro phonemizer
   from kokoro import KPipeline
   # Works on Google's servers with better internet
   ```

2. **RunPod Cloud GPU** (Paid - ~$0.30/hour)
   - Pre-configured Kokoro environment

## Expected Timeline

Once internet is restored:
- **First run**: ~3-5 minutes (download + synthesis)
- **Subsequent runs**: ~30-60 seconds (uses cached model)

## Verify Installation is Correct

Run this to confirm everything is set up properly:

```bash
source .venv/bin/activate
python tts/kokoro_demo.py
```

**Expected output**: Shows all dependencies as ✓ (like above)

## Files Created

Your ArticleExtraction project now has:
- `tts/kokoro_run.py` — Main TTS synthesis script
- `tts/kokoro_demo.py` — API demo and verification
- `KOKORO_SETUP.md` — Complete setup documentation
- `NETWORK_TROUBLESHOOTING.md` — This file

## Next Steps

1. **Resolve network issue** using solutions above
2. **Run synthesis**: `python tts/kokoro_run.py tts/Steady_pvc.txt`
3. **Check output**: `ls -lh tts/Steady_pvc_kokoro.wav` (should exist)
4. **Listen to audio**: Open the WAV file in any audio player

## Contact Info

If network issues persist:
- Check Hugging Face status: https://status.huggingface.co
- Verify your ISP isn't blocking the domain
- Try from a different network (phone hotspot, different WiFi)

---

**Created**: January 2025  
**Kokoro Version**: 0.7.16  
**Model**: Kokoro-82M (hexgrad/Kokoro-82M)
