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
from PIL import Image

# Configuration - Ensure OPENROUTER_API_KEY is set in your environment variables
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "google/gemini-3.1-flash-lite"
TEMP_VIDEO_PATH = "temp_reel.mp4"
TARGET_DIR = "downloaded_content"

if not API_KEY:
    print("Error: OPENROUTER_API_KEY environment variable is not set.")
    sys.exit(1)

def compress_video(input_path, output_path, bitrate="500k", resolution="720x480"):
    """Compress video to reduce file size and token usage"""
    cmd = [
        "ffmpeg", "-i", input_path,
        "-b:v", bitrate,  # Lower bitrate = smaller file
        "-s", resolution,  # Reduce resolution
        "-c:v", "libx264",
        "-preset", "fast",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"[+] Compressed video: {input_path} → {output_path}")

def compress_image(input_path, output_path, quality=60):
    """Reduce JPEG quality to save tokens"""
    img = Image.open(input_path)
    img.save(output_path, "JPEG", quality=quality, optimize=True)
    print(f"[+] Compressed image: {input_path}")

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

    print(f"[*] Fetching metadata for shortcode: {shortcode}\n")
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
        "Analyze this technical content and produce a structured summary in this exact format:\n\n"
        "Main Topic: (One-line description of the core subject)\n\n"
        "Key Points Explained\n\n"
        "(3-5 bullet points. Each bullet must start with a short descriptive label followed by a colon, "
        "then a concise explanation. Example: '* Hot Reload: Saves changes instantly without restarting the server.')\n\n"
        "Tools Mentioned\n\n"
        "(List tools grouped by type. Use these categories only when applicable:\n"
        "- GitHub Repository: https://url \n"
        "- Tools / CLIs: tool1, tool2\n"
        "- Libraries / Frameworks: lib1, lib2\n"
        "- Hardware / Devices: device1\n"
        "- Other: anything that doesn't fit above\n\n"
        "Rules:\n"
        "- No nested bold inside bullet points\n"
        "- Be technical, specific, and concise\n"
        "- Focus on concepts and tools, not on code\n"
        "- Reproduce exact repo names and URLs as markdown hyperlinks\n"
        "- Include version numbers or model sizes when visible (e.g. Python 3.12, Node 20)"
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
        "messages": [{"role": "user", "content": message_content}],
        "temperature" : 0.2
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

        # Compression
        if content_type == "video":
            compressed = os.path.join(TARGET_DIR, "temp_compressed.mp4")
            compress_video(files[0], compressed, bitrate="400k", resolution="720x480")
            files = [compressed]
        elif content_type == "carousel":
            compressed_files = []
            for f in files:
                out = f.replace(".jpg", "_compressed.jpg")
                compress_image(f, out, quality=65)
                compressed_files.append(out)
            files = compressed_files

        analysis = analyze_content(content_type, files)
        
        print("\n================ ANALYSIS RESULT ================\n")
        print(analysis)
        print("\n=================================================\n")
        
    finally:
        # Clean up the downloaded content directory (includes compressed files)
        if os.path.exists(TARGET_DIR):
            shutil.rmtree(TARGET_DIR)


if __name__ == "__main__":
    main()