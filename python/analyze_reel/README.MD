# Analyze Reel
A simple stupid script and agentic skill that downloads and resumes instagram posts with Gemini3.1-flash-lite.

## Requirements
python >=3.11

- instaloader
- ffmpeg
- requests

## Prerequisites
**Instagram cookies**: it is required a file called "instagram_cookies.txt" inside the folder in the format Netscape HTTP Cookie File. This file must contains all the required cookies, personally i manually copied them and converted them to the right format using the script `extract_cookie.py` script. However there may be a better way to do this.

**OpenRouter API Key**: i'm using gemini3.1-flash-lite for extracting information from instagram posts and OpenRouter as provider, so an `.env` file with `OPENROUTER_API_KEY` is required..

## How to run
```
python analyze_reel.py <url>
```
