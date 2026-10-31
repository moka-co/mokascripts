import os
import io
import sys
import base64
import json
import subprocess
import requests
import instaloader
import re
import shutil
import glob
import http.cookiejar
from dotenv import load_dotenv
from PIL import Image
from typing import Any 

if sys.platform == "win32" and isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Configuration - Ensure OPENROUTER_API_KEY is set in your environment variables
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "google/gemini-3.1-flash-lite"
TARGET_DIR = "downloaded_content"
MAX_FRAMES = 20

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
    print(f"[+] Compressed video: {input_path} -> {output_path}")

def compress_image(input_path, output_path, quality=60):
    """Reduce JPEG quality to save tokens"""
    img = Image.open(input_path)
    img.save(output_path, "JPEG", quality=quality, optimize=True)
    print(f"[+] Compressed image: {input_path}")

def download_facebook_content(url, target_dir=TARGET_DIR):
    """Downloads Facebook content using yt-dlp and returns a tuple: (content_type, [list_of_filepaths])"""
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)

    output_template = os.path.join(target_dir, "%(id)s.%(ext)s")
    print(f"[*] Fetching Facebook content from: {url}\n")
    try:
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "-f", "b/bestvideo+bestaudio/best",
            "--merge-output-format", "mp4",
            "--write-description",
            "-o", output_template,
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[-] yt-dlp failed: {result.stderr or result.stdout}")
            sys.exit(1)

        description = glob.glob(os.path.join(target_dir, "*.description"))
        if description:
            shutil.move(description[0], os.path.join(target_dir, "caption.txt"))

        videos = glob.glob(os.path.join(target_dir, "*.mp4"))
        if not videos:
            videos = [f for f in glob.glob(os.path.join(target_dir, "*.*"))
                      if not f.endswith(".txt")]
        if videos:
            print("[+] Facebook video/reel detected.")
            return "video", [videos[0]]
        else:
            print("[-] Error: No video files found after download.")
            sys.exit(1)
    except Exception as e:
        print(f"[-] Facebook download failed: {e}")
        sys.exit(1)


def download_instagram_content(url, target_dir=TARGET_DIR):
    """Downloads content and returns a tuple: (content_type, [list_of_filepaths])"""
    match = re.search(r"/(?:p|reel|reels)/([A-Za-z0-9_-]+)", url)
    if not match:
        print("[-] Error: Could not parse Instagram Shortcode from URL.")
        sys.exit(1)
        
    shortcode = match.group(1)
    
    # Clean up any old download directory to avoid mixing files
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)

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
            #L.load_session_from_file("instagram_session", filename=cookie_path)
            cj = http.cookiejar.MozillaCookieJar(cookie_path)
            cj.load(ignore_discard=True, ignore_expires=True)
            L.context._session.cookies.update(cj)

        except Exception as e:
            print(f"[!] Cookie warning: {e}. Attempting without session...")

    print(f"[*] Fetching metadata for shortcode: {shortcode}\n")
    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target=target_dir)
        if post.caption:
            with open(os.path.join(target_dir, "caption.txt"), "w", encoding="utf-8") as f:
                f.write(post.caption)
        
        # Check if it's a carousel (Sidecar) or a single video
        if post.typename == 'GraphSidecar':
            # Collect all downloaded JPEG images for the text carousel
            images = sorted(glob.glob(os.path.join(target_dir, "*.jpg")))
            print(f"[+] Text Carousel detected. Found {len(images)} slides.")
            return "carousel", images
        else:
            # Collect the single downloaded MP4
            videos = glob.glob(os.path.join(target_dir, "*.mp4"))
            if videos:
                print("[+] Single video/reel detected.")
                return "video", [videos[0]]
            else:
                # Fallback if a post is just a single static image
                images = glob.glob(os.path.join(target_dir, "*.jpg"))
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

def download_content(url, target_dir=TARGET_DIR):
    """Dispatches to the right downloader based on the URL host."""
    if re.search(r"(facebook\.com|fb\.watch)", url):
        return download_facebook_content(url, target_dir)
    return download_instagram_content(url, target_dir)

def get_video_duration(path):
    """Returns the video duration in seconds using ffprobe (0 if unknown)."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0

def extract_frames(video_path, frames_dir, max_frames=MAX_FRAMES):
    """Extracts evenly spaced frames (at most max_frames) so they can be inspected as images."""
    os.makedirs(frames_dir, exist_ok=True)
    duration = get_video_duration(video_path)
    interval = max(duration / max_frames, 1) if duration else 2
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"fps=1/{interval:.2f},scale=720:-2",
        "-frames:v", str(max_frames),
        "-q:v", "4",
        os.path.join(frames_dir, "frame_%03d.jpg")
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    frames = sorted(glob.glob(os.path.join(frames_dir, "frame_*.jpg")))
    print(f"[+] Extracted {len(frames)} frames (one every {interval:.1f}s)")
    return frames, interval

def transcribe_audio(video_path, output_path):
    """Transcribes the audio track if faster-whisper is installed. Returns the transcript path or None."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("[!] faster-whisper not installed, skipping audio transcription")
        return None

    print("[*] Transcribing audio...")
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(video_path)
    with open(output_path, "w", encoding="utf-8") as f:
        for seg in segments:
            f.write(f"[{seg.start:6.1f}s] {seg.text.strip()}\n")
    print(f"[+] Transcript saved: {output_path}")
    return output_path

def prepare_local(url, out_dir):
    """Downloads the content and prepares frames/caption/transcript for local analysis.
    Nothing is sent to OpenRouter and the files are kept in out_dir."""
    content_type, files = download_content(url, out_dir)

    manifest: dict[str, Any] = {
        "url": url,
        "content_type": content_type,
        "dir": os.path.abspath(out_dir),
        "media": [os.path.abspath(f) for f in files],
    }

    caption = os.path.join(out_dir, "caption.txt")
    manifest["caption"] = os.path.abspath(caption) if os.path.exists(caption) else None

    if content_type == "video":
        frames, interval = extract_frames(files[0], os.path.join(out_dir, "frames"))
        manifest["frames"] = [os.path.abspath(f) for f in frames]
        manifest["frame_interval_s"] = round(interval, 2)
        transcript = transcribe_audio(files[0], os.path.join(out_dir, "transcript.txt"))
        manifest["transcript"] = os.path.abspath(transcript) if transcript else None
    else:
        manifest["frames"] = manifest["media"]
        manifest["transcript"] = None

    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("\n================ LOCAL CONTENT ================\n")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    print("\n===============================================\n")

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
        "- GitHub Repository: https://url\n"
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
    message_content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

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
    args = sys.argv[1:]
    local = "--local" in args
    out_dir = "local_content"
    if "--out" in args:
        i = args.index("--out")
        out_dir = args[i + 1]
        del args[i:i + 2]
    args = [a for a in args if a != "--local"]

    if not args:
        print("Usage: python analyze_reel.py <REEL_URL> [--local [--out DIR]]")
        print("  --local  download and extract frames/caption/transcript only, no OpenRouter call")
        sys.exit(1)

    url = args[0]

    if local:
        prepare_local(url, out_dir)
        return

    if not API_KEY:
        print("Error: OPENROUTER_API_KEY environment variable is not set.")
        sys.exit(1)

    try:
        content_type, files = download_content(url)

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