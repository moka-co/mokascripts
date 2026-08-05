import win32api
import win32con
import time

EXIT_KEYS = [win32con.VK_CONTROL, win32con.VK_MENU, ord('M')] # Ctrl + Alt + M
last_exit_state = False

def is_key_down(vk_code):
    return win32api.GetAsyncKeyState(vk_code) & 0x8000 != 0

def right_click(): 
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

try:
    last_click_time = 0
    while True:
        # Detect 
        last_exit_state = all(is_key_down(vk) for vk in EXIT_KEYS)
        if last_exit_state:
            break
        
        time.sleep(0.05)

        # Right Click
        if (time.time() - last_click_time) >= 2:
            right_click()
            last_click_time = time.time()


except KeyboardInterrupt:
    print("\nStopped by user.")
