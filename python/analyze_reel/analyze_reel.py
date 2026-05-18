import os
import sys
import base64
import json
import subprocess
import requests
from dotenv import load_dotenv

# Configuration - Ensure OPENROUTER_API_KEY is set in your environment variables
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "google/gemini-2.5-flash"
TEMP_VIDEO_PATH = "temp_reel.mp4"

if not API_KEY:
    print("Error: OPENROUTER_API_KEY environment variable is not set.")
    sys.exit(1)

def download_reel(url):
    """Downloads the Instagram Reel using yt-dlp."""
    local_appdata = os.getenv("LOCALAPPDATA")
    print(f"[*] Downloading Reel from: {url}")
    # --force-overwrites ensures we don't pile up old videos
    # We restrict quality slightly to save bandwidth/tokens since it's just informational text/code
    cmd = [
        "yt-dlp",
        "-S", "res:480", 
        "-t", "mp4",
        "--force-overwrites",
        #"--cookies-from-browser", f"brave:/C/Users/{win_user}/AppData/Local/BraveSoftware/Brave-Browser/User Data/AutomationProfile",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Chrome/122.0.0.0 Movavi/122.0.0.0 Brave/122.0.0.0",
        "--cookies", "instagram_cookies.txt",
        "-o", TEMP_VIDEO_PATH,
        url
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print("[+] Download complete.")
    except subprocess.CalledProcessError as e:
        print(f"[-] Error downloading video. Instagram might be blocking the request or login is required.")
        print(e.stderr.decode())
        sys.exit(1)

def encode_video_to_base64(path):
    """Converts the local video file to a base64 string."""
    print("[*] Encoding video to Base64...")
    with open(path, "rb") as video_file:
        encoded_string = base64.b64encode(video_file.read()).decode('utf-8')
    return f"data:video/mp4;base64,{encoded_string}"

def analyze_video(base64_data):
    """Sends the base64 video to OpenRouter for structured tech analysis."""
    print(f"[*] Sending to OpenRouter ({MODEL})...")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = (
        "Analyze this short tech reel/video and extract information using this exact structure:\n"
        "1. **Main Topic**: (What is this video about? e.g., a new AI tool, keyboard shortcut, dev tip)\n"
        "2. **Key Points Explained**: (Bullet points of the concepts or steps shown)\n"
        "3. **Code / Commands / Tools Mentioned**: (Exact transcription of any terminal commands, code snippets, repo names, or URLs visible or spoken)\n"
        "4. **Audio/Speech Summary**: (A concise summary of what the creator says)\n"
        "Keep it highly technical, objective, and straight to the point."
    )

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "video_url",
                        "video_url": {
                            "url": base64_data
                        }
                    }
                ]
            }
        ]
    }

    response = None
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        return result['choices'][0]['message']['content']
    except requests.exceptions.HTTPError as http_err:
        print(f"[-] HTTP Error occurred: {http_err}")
        if response is not None:
            print(f"Response Body: {response.text}")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("[-] Error: The request to OpenRouter timed out.")
        sys.exit(1)
    except requests.exceptions.RequestException as req_err:
        print(f"[-] A networking error occurred: {req_err}")
        sys.exit(1)
    except (KeyError, IndexError):
        print("[-] Error: Unexpected JSON response structure from OpenRouter.")
        if response is not None:
            print(f"Raw Response: {response.text}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_reel.py <INSTAGRAM_REEL_URL>")
        sys.exit(1)
        
    reel_url = sys.argv[1]
    
    try:
        download_reel(reel_url)
        base64_video = encode_video_to_base64(TEMP_VIDEO_PATH)
        analysis = analyze_video(base64_video)
        
        print("\n================ ANALYSIS RESULT ================\n")
        print(analysis)
        print("\n=================================================\n")
        
    finally:
        # Clean up the downloaded file to keep the container/host clean
        if os.path.exists(TEMP_VIDEO_PATH):
            os.remove(TEMP_VIDEO_PATH)

if __name__ == "__main__":
    main()