import os
import sys
import base64
import json
import subprocess
import requests
import instaloader
import re
import shutil
import glob
from dotenv import load_dotenv

# Configuration - Ensure OPENROUTER_API_KEY is set in your environment variables
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "google/gemini-2.5-flash"
TEMP_VIDEO_PATH = "temp_reel.mp4"
TARGET_DIR = "downloaded_content"

if not API_KEY:
    print("Error: OPENROUTER_API_KEY environment variable is not set.")
    sys.exit(1)

def download_instagram_content(url):
    """Downloads content and returns a tuple: (content_type, [list_of_filepaths])"""
    match = re.search(r"/(?:p|reel|reels)/([A-Za-z0-9_-]+)", url)
    if not match:
        print("[-] Error: Could not parse Instagram Shortcode from URL.")
        sys.exit(1)
        
    shortcode = match.group(1)
    
    # Clean up any old download directory to avoid mixing files
    if os.path.exists(TARGET_DIR):
        shutil.rmtree(TARGET_DIR)

    L = instaloader.Instaloader(
        download_pictures=True,       # Needed for text carousels
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False
    )
    
    # Optional: Load your session cookies if Instagram blocks anonymous requests
    cookie_path = "instagram_cookies.txt"
    if os.path.exists(cookie_path):
        try:
            # Replace with your actual username or a dummy string depending on cookie type
            L.load_session_from_file("instagram_session", filename=cookie_path)
        except Exception as e:
            print(f"[!] Cookie warning: {e}. Attempting without session...")

    print(f"[*] Fetching metadata for shortcode: {shortcode}")
    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target=TARGET_DIR)
        
        # Check if it's a carousel (Sidecar) or a single video
        if post.typename == 'GraphSidecar':
            # Collect all downloaded JPEG images for the text carousel
            images = sorted(glob.glob(os.path.join(TARGET_DIR, "*.jpg")))
            print(f"[+] Text Carousel detected. Found {len(images)} slides.")
            return "carousel", images
        else:
            # Collect the single downloaded MP4
            videos = glob.glob(os.path.join(TARGET_DIR, "*.mp4"))
            if videos:
                print("[+] Single video/reel detected.")
                return "video", [videos[0]]
            else:
                # Fallback if a post is just a single static image
                images = glob.glob(os.path.join(TARGET_DIR, "*.jpg"))
                print("[+] Single image detected.")
                return "carousel", [images[0]]
                
    except Exception as e:
        print(f"[-] Instaloader failed: {e}")
        sys.exit(1)

def encode_file_to_base64(path, mime_type):
    """Converts a local file (image or video) to a base64 Data URL."""
    try:
        with open(path, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode('utf-8')
        return f"data:{mime_type};base64,{encoded_string}"
    except FileNotFoundError:
        print(f"[-] Error: File not found at {path}")
        sys.exit(1)

def analyze_content(content_type, file_paths):
    """Constructs the appropriate payload and sends it to OpenRouter."""
    print(f"[*] Preparing OpenRouter payload for {content_type}...")
    
    prompt = (
        "Analyze this technical content and extract information using this exact structure:\n"
        "1. **Main Topic**: (What is this about? e.g., a new AI tool, keyboard shortcut, dev tip)\n"
        "2. **Key Points Explained**: (Bullet points of the concepts or steps shown across the slides/video)\n"
        "3. **Tools Mentioned**: (Exact transcription of any Repo names or URLs visible)\n"
        "Keep it highly technical, objective, and straight to the point."
    )

    # Base structure of the message content
    message_content = [{"type": "text", "text": prompt}]

    # Build payload dynamically based on assumption type
    if content_type == "video":
        base64_video = encode_file_to_base64(file_paths[0], "video/mp4")
        message_content.append({
            "type": "video_url",
            "video_url": {"url": base64_video}
        })
    elif content_type == "carousel":
        for path in file_paths:
            base64_image = encode_file_to_base64(path, "image/jpeg")
            message_content.append({
                "type": "image_url",
                "image_url": {"url": base64_image}
            })

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": message_content}]
    }

    response = None
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"[-] API Error: {e}")
        if response is not None:
            print(f"Response Body: {response.text}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_reel.py <INSTAGRAM_REEL_URL>")
        sys.exit(1)
        
    url = sys.argv[1]
    
    try:
        content_type, files = download_instagram_content(url)
        analysis = analyze_content(content_type, files)
        
        print("\n================ ANALYSIS RESULT ================\n")
        print(analysis)
        print("\n=================================================\n")
        
    finally:
        # Clean up the downloaded file to keep the container/host clean
        if os.path.exists(TARGET_DIR):
            shutil.rmtree(TARGET_DIR)

if __name__ == "__main__":
    main()