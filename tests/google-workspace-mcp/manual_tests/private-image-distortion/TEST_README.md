# Google Slides Image Distortion Investigation

This directory contains test scripts to investigate image distortion issues when using Google Slides with private Drive images via Apps Script.

## Files

- `test_slides_local.py` - Comprehensive test script for `create_slide_with_elements` function
- `test_image_distortion.py` - Focused investigation of image distortion causes
- `TEST_README.md` - This file

## Setup

### 1. Environment Variables

Set the following environment variables:

```bash
export GOOGLE_WORKSPACE_CLIENT_ID="your-client-id"
export GOOGLE_WORKSPACE_CLIENT_SECRET="your-client-secret"
export GOOGLE_WORKSPACE_REFRESH_TOKEN="your-refresh-token"
export GOOGLE_WORKSPACE_APPS_SCRIPT_ID="your-apps-script-id"  # Optional, for private Drive images
```

### 2. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the following APIs:
   - Google Slides API
   - Google Drive API
   - Google Apps Script API (if using private Drive images)
4. Create OAuth 2.0 credentials
5. Download the credentials and extract the values

### 3. Apps Script Setup (Optional)

If testing private Drive images:

1. Go to [Google Apps Script](https://script.google.com/)
2. Create a new project
3. Copy the Script ID
4. Set the `GOOGLE_WORKSPACE_APPS_SCRIPT_ID` environment variable

## Usage

### Basic Test

Run the comprehensive test script:

```bash
python test_slides_local.py
```

This will:
- Create a test presentation
- Test the `create_slide_with_elements` function with your data
- Test individual image functions
- Investigate image distortion issues

### Focused Investigation

Run the focused distortion investigation:

```bash
python test_image_distortion.py
```

This will:
- Test image sizing logic
- Compare Apps Script vs REST API approaches
- Identify potential distortion sources
- Provide investigation recommendations

## Test Data

The scripts use your provided test data:

```json
[
  {
    "layout": "BLANK",
    "background_color": "#feeef5",
    "elements": [
      {
        "type": "image",
        "content": "https://drive.google.com/file/d/1obxZHk7ioeCn-BogkIJ3aVlTyst0hICv/view?usp=drive_link",
        "position": {
          "x": 0,
          "y": 0
        }
      },
      {
        "type": "image",
        "content": "https://drive.google.com/file/d/1WXUAHHk_0rRsUaze6v5lVTOKafy5JTyr/view?usp=drive_link",
        "position": {
          "x": 207,
          "y": 63,
          "width": 120,
          "height": 40
        }
      },
      {
        "type": "image",
        "content": "https://drive.google.com/file/d/1qPb_RC1ufWn9bzy2XG784lqhbFqn7Lvt/view?usp=drive_link",
        "position": {
          "x": 390,
          "y": 63,
          "width": 120,
          "height": 40
        }
      }
    ]
  }
]
```

## Investigation Points

### 1. Image Sizing Logic

The code uses different sizing logic for different scenarios:

- **Background images** (x=0, y=0, no size): Uses full slide dimensions (720x540 PT)
- **Exact dimensions**: Uses specified width and height
- **Width-only**: Calculates height using 16:9 aspect ratio
- **Height-only**: Calculates width using 16:9 aspect ratio
- **Default**: Uses 200x150 PT

### 2. Apps Script vs REST API

**REST API Approach:**
- Uses `createImage` request
- Direct URL embedding
- Supports public URLs only
- Size specified in request
- Transform includes position and scale

**Apps Script Approach:**
- Uses `embedPrivateImage` function
- Requires Drive file ID
- Handles private Drive files
- Size calculated in Apps Script
- Position passed as parameters

### 3. Potential Distortion Sources

1. **Unit conversion differences** (PT vs EMU)
2. **Size calculation logic differences**
3. **Aspect ratio handling**
4. **Coordinate system differences**
5. **Apps Script vs REST API implementation differences**

## Debugging Steps

### 1. Check Apps Script Logs

If using Apps Script, check the execution logs for detailed error information:

1. Go to [Google Apps Script](https://script.google.com/)
2. Open your project
3. Click "Executions" in the left sidebar
4. Check recent executions for errors

### 2. Compare with Public Images

Test with public image URLs to establish a baseline:

```python
# Test with public image
public_image_url = "https://example.com/public-image.jpg"
```

### 3. Test Different Units

Try different units to see if that affects distortion:

```python
# Test with PT units
result = slides_service.add_image_with_unit(
    presentation_id, slide_id, image_url, 
    position=(100, 100), size=(200, 150), unit="PT"
)

# Test with EMU units
result = slides_service.add_image_with_unit(
    presentation_id, slide_id, image_url,
    position=(100, 100), size=(200, 150), unit="EMU"
)
```

### 4. Check Image Dimensions

Verify the actual dimensions of your test images:

```python
# Extract file ID from Drive URL
file_id = "1obxZHk7ioeCn-BogkIJ3aVlTyst0hICv"
# Check image metadata in Google Drive
```

## Expected Output

The scripts will output detailed information about:

- Environment setup status
- Authentication results
- Image request building process
- Apps Script vs REST API detection
- Size calculation logic
- Unit conversion details
- Potential distortion sources

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Check environment variables
   - Verify OAuth credentials
   - Ensure APIs are enabled

2. **Apps Script Not Working**
   - Verify Apps Script ID
   - Check Apps Script permissions
   - Review execution logs

3. **Image Distortion**
   - Compare with public images
   - Test different units
   - Check size calculations
   - Verify coordinate systems

### Getting Help

If you encounter issues:

1. Check the script output for error messages
2. Review Google Apps Script execution logs
3. Test with simpler image configurations
4. Compare results with public image URLs

## Next Steps

After running the tests:

1. **Review the presentation** in Google Slides to see actual results
2. **Compare different approaches** (REST API vs Apps Script)
3. **Test with known good images** to establish baseline
4. **Check Apps Script logs** for detailed error information
5. **Modify the code** based on findings to fix distortion issues 