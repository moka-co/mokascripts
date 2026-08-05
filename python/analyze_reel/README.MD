# Analyze Reel
A simple stupid script and agentic skill that downloads and resumes instagram posts with Gemini3.1-flash-lite.

## Requirements
python >=3.11

- instaloader
- ffmpeg
- requests

## Prerequisites
**Instagram cookies**:
- Login to instagram from the browser
- use a plugin like Cookie editor and then export in netscape format
- copy+paste the exported content into a file called `instagram_cookies.txt`

**OpenRouter API Key**: i'm using gemini3.1-flash-lite for extracting information from instagram posts and OpenRouter as provider, so an `.env` file with `OPENROUTER_API_KEY` is required..

## How to run
```
python analyze_reel.py <url>
```
