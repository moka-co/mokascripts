import os
import re
import time
from datetime import datetime

output_filename = "instagram_cookies.txt"

def parse_cookie_string(cookie_str):
    # Standardize spaces after semicolons for easier splitting
    cookie_str = re.sub(r';\s*', '; ', cookie_str.strip())
    parts = cookie_str.split('; ')
    
    # The first element is always the Name=Value pair
    if '=' not in parts[0]:
        print("[-] Invalid format. Could not find a 'Name=Value' pair.")
        return None
        
    name_value = parts[0].split('=', 1)
    cookie_data = {
        'name': name_value[0],
        'value': name_value[1],
        'domain': '.instagram.com',  # Fallback defaults
        'path': '/',
        'expires': int(time.time() + 86400 * 30), # Default to 30 days if parsing fails
        'secure': 'FALSE'
    }
    
    # Parse the remaining attributes
    for part in parts[1:]:
        if '=' in part:
            key, val = part.split('=', 1)
            key_lower = key.lower()
            
            if key_lower == 'domain':
                cookie_data['domain'] = val if val.startswith('.') else f".{val}"
            elif key_lower == 'path':
                cookie_data['path'] = val
            elif key_lower == 'expires':
                try:
                    # Parse standard HTTP cookie date format (GMT/UTC)
                    dt = datetime.strptime(val, "%a, %d %b %Y %H:%M:%S GMT")
                    cookie_data['expires'] = int(dt.timestamp())
                except ValueError:
                    pass
        else:
            if part.lower() == 'secure':
                cookie_data['secure'] = 'TRUE'
                
    return cookie_data

# 1. Initialize or clear the file with Netscape headers
with open(output_filename, 'w', encoding='utf-8') as f:
    f.write("# Netscape HTTP Cookie File\n")
    f.write("# This file was generated automatically by Python\n\n")

print("=== Instagram Netscape Cookie Generator ===")
print(f"Cookies will be saved to: {os.path.abspath(output_filename)}")
print("------------------------------------------")

# 2. Loop to accept inputs
cookie_count = 0
while True:
    print(f"\n[Cookie #{cookie_count + 1}]")
    user_input = input("Paste cookie string (or press ENTER without typing to finish): ")
    
    if not user_input.strip():
        break
        
    parsed = parse_cookie_string(user_input)
    
    if parsed:
        include_subdomains = 'TRUE' if parsed['domain'].startswith('.') else 'FALSE'
        line = f"{parsed['domain']}\t{include_subdomains}\t{parsed['path']}\t{parsed['secure']}\t{parsed['expires']}\t{parsed['name']}\t{parsed['value']}\n"
        
        # Append the new cookie to the file
        with open(output_filename, 'a', encoding='utf-8') as f:
            f.write(line)
            
        cookie_count += 1
        print(f"[+] Added '{parsed['name']}' successfully.")

print(f"\n[!] Finished! Added {cookie_count} cookie(s) to '{output_filename}'.")
print(f"You can now run: yt-dlp --cookies {output_filename} \"YOUR_URL\"")