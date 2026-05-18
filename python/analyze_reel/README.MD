# Analyze Reel

## Requirements
python >=3.11

- yt-dlp
- ffmpeg
- requests

## Prerequisites
**Instagram cookies**: it is required a file called "instagram_cookies.txt" inside the folder, that is in a format compliat with yt-dp (Netscape HTTP Cookie File). This file must contains all the required cookies, personally i manually copied them and converted them to the right format using the script `extract_cookie.py` script. However there may be a better way to do this.

**OpenRouter API Key**: i'm using gemini2.5-flash for extracting information from video and OpenRouter as provider, so an `.env` file with `OPENROUTER_API_KEY` is required

## How to run
```
python analyze_reel.py <url>
```
