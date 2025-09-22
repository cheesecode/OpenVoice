# ElevenLabs Model Fix Summary

## Issue
The service was failing when using `eleven_v3` model during voice clone creation, returning "Failed to create voice clone" error.

## Root Cause Analysis

### Initial Issue: eleven_multilingual_v3
`eleven_multilingual_v3` does not exist in the ElevenLabs API. This was an incorrect model name being used in the codebase.

### Actual Issues Discovered

#### 1. Voice Limit Reached
After fixing the model names, testing revealed: **Voice limit reached (10/10 on Starter plan)**. 
The service attempts to create a voice clone but fails because the ElevenLabs account has reached its maximum custom voices limit.

#### 2. eleven_v3 Stability Parameter Issue
After fixing the voice limits, `eleven_v3` was still failing with:
**`invalid_ttd_stability`**: "Invalid TTD stability value. Must be one of: [0.0, 0.5, 1.0] (0.0 = Creative, 0.5 = Natural, 1.0 = Robust)"

**Root Cause**: `eleven_v3` has different parameter requirements than other models:
- **Other models**: Accept continuous stability values (0.0 to 1.0)
- **eleven_v3**: Only accepts discrete values: `0.0`, `0.5`, or `1.0`

## Available ElevenLabs Models (as of current API)
✅ **Working Models:**
- `eleven_multilingual_v2` - Eleven Multilingual v2
- `eleven_v3` - Eleven v3 (alpha) 
- `eleven_flash_v2_5` - Eleven Flash v2.5
- `eleven_turbo_v2_5` - Eleven Turbo v2.5
- `eleven_turbo_v2` - Eleven Turbo v2
- `eleven_flash_v2` - Eleven Flash v2
- `eleven_english_sts_v2` - Eleven English v2
- `eleven_monolingual_v1` - Eleven English v1
- `eleven_multilingual_v1` - Eleven Multilingual v1
- `eleven_multilingual_sts_v2` - Eleven Multilingual v2

❌ **Non-existent Model:**
- `eleven_multilingual_v3` - This model does not exist

## Files Updated

### 1. `fastapi_elevenlabs_service/main.py`
- Updated model validation to include all valid ElevenLabs models
- Added appropriate text length limits for different model types
- Improved error messages to show available models

### 2. `fastapi_elevenlabs_service/services/voice_cloning.py`
- Updated text chunking limits for all valid models
- Added chunk size configurations for newer models (Flash/Turbo)

### 3. `fastapi_elevenlabs_service/models/requests.py`
- Updated model field documentation to reflect available options

### 4. Documentation Updates
- Updated `README.md` to mention newer model support
- Updated `WARP.md` with correct chunking limits for all models

## Text Length Limits by Model
- **Multilingual models** (`eleven_multilingual_v2`, `eleven_multilingual_v1`, `eleven_multilingual_sts_v2`): 10,000 chars max
- **V3 model** (`eleven_v3`): 3,000 chars max
- **Flash/Turbo models** (`eleven_flash_v2_5`, `eleven_turbo_v2_5`, etc.): 5,000 chars max

## Chunk Size Limits for Long Text
- **Multilingual models**: 9,500 chars per chunk
- **V3 model**: 2,800 chars per chunk
- **Flash/Turbo models**: 4,500 chars per chunk

## Verification
Testing confirmed:
- ✅ `eleven_multilingual_v2` works (baseline)
- ✅ `eleven_flash_v2_5` works  
- ✅ `eleven_turbo_v2_5` works
- ✅ **`eleven_v3` now works** (short and medium text)
- ❌ `eleven_multilingual_v3` does not exist
- ⚠️ Long text with `eleven_v3` limited by character quota

## Solutions Implemented

### 1. Improved Error Handling
- Enhanced `elevenlabs_client.py` to show specific API errors instead of generic "Failed to create voice clone"
- Added detection for voice limit, quota, and audio quality errors
- Better error messages help diagnose issues faster

### 2. Aggressive Voice Cleanup
- Added `ensure_voice_capacity_aggressive()` method to delete multiple voices when needed
- Improved voice capacity management in the service
- Automatic cleanup before voice creation attempts

### 3. eleven_v3 Parameter Compatibility
- Fixed stability parameter handling for `eleven_v3` model
- Added automatic conversion: input stability → discrete values (0.0, 0.5, 1.0)
- Mapping: < 0.25 → 0.0, < 0.75 → 0.5, ≥ 0.75 → 1.0

### 4. Voice Cleanup Utility
- Created `cleanup_voices.py` script for manual voice management  
- Interactive tool to delete oldest voices or all custom voices
- Shows current usage: `{current}/{limit}` voices

## How to Fix Your Current Issue

### Immediate Solution
```powershell
# Run the voice cleanup utility
python cleanup_voices.py
# Choose 'o' to delete oldest 3 voices, or 'a' to delete all custom voices
```

### Alternative: Use API Endpoint
```bash
# Clean up oldest voices via API
curl -X DELETE "http://localhost:8000/voices/cleanup" \
  -H "Content-Type: application/json" \
  -d '{"cleanup_type": "oldest", "max_voices": 7}'
```

## Long-term Recommendations
1. **Monitor Voice Usage**: Keep track of custom voices to avoid hitting limits
2. **Consider Plan Upgrade**: Creator plan allows 30 custom voices vs 10 on Starter
3. **Regular Cleanup**: Implement periodic cleanup of unused voices
4. **Use `eleven_multilingual_v2`** for multilingual content (most reliable)
5. **Try newer models** like `eleven_flash_v2_5` or `eleven_turbo_v2_5` for faster processing
