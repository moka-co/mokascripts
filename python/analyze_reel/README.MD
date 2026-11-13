# Analyze Reel
A simple stupid script and agentic skill that downloads and resumes instagram posts (technical or not) with Gemini3.1-flash-lite.

## Requirements
python >=3.11

- instaloader
- ffmpeg
- requests

## Prerequisites
**Instagram cookies**:
- Login to instagram from the browser
- use a plugin like Cookie editor and then export in netscape format
- copy+paste the exported content into a file called `instagram_cookies.txt` (next to `analyze_reel.py`; it is gitignored)
- alternatively run `python extract_cookie.py` and paste the cookie strings one by one

For Instagram URLs the script refuses to run (exit code 3, `COOKIES_MISSING`) if the file is not found. The path can be overridden with the `INSTAGRAM_COOKIES_PATH` environment variable. Facebook URLs do not need cookies. Pass `--no-cookie` to skip the check and download anonymously (the cookie file is then not used at all, and Instagram may block the request). When used as an agent skill, you can also paste the exported cookies in the chat and the agent will save them to `instagram_cookies.txt`.

**OpenRouter API Key**: i'm using gemini3.1-flash-lite for extracting information from instagram posts and OpenRouter as provider, so an `.env` file with `OPENROUTER_API_KEY` is required..

## How to run
```
python analyze_reel.py <url>
```

### Local mode
Downloads the post and prepares it for analysis by an agent (e.g. Claude) without calling OpenRouter:
```
python analyze_reel.py <url> --local --out <dir>
```

It saves the media, the caption (`caption.txt`), up to 20 frames (`frames/`) and a `manifest.json`.
If `faster-whisper` is installed (`pip install faster-whisper`) the audio is also transcribed into `transcript.txt`.

### Options
| Option | Description |
| --- | --- |
| `--local` | download and prepare the content only, no OpenRouter call |
| `--out <dir>` | output directory for `--local` (default `local_content`) |
| `--no-cookie` | skip the `instagram_cookies.txt` check and download anonymously |

Exit code `3` (`COOKIES_MISSING`) means the Instagram cookie file was not found.
