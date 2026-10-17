import re
import threading
import time
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk

import keyboard
import pyautogui
from PIL import ImageGrab
from rapidocr_onnxruntime import RapidOCR

LOG_PATH = Path(__file__).with_name("quick_maths.log")


def log_error(message):
    try:
        with LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {message}\n")
    except OSError:
        pass


class QuickMaths:
    def __init__(self, root):
        self.root = root
        root.title("Quick Maths — F8 to answer")
        # Keep the helper narrow so it does not cover the centered TTRS equation.
        # The earlier 700 px window hid the first digit on common 1080p layouts.
        root.geometry("430x500+20+120")
        root.minsize(410, 450)
        self.active = False
        self.last_question = None
        self.last_attempt_at = 0.0
        self.attempt_count = 0
        self.missed_question_frames = 0
        self.pending_signature = None
        self.pending_count = 0
        self.pending_action = None
        self.pending_action_count = 0
        self.last_play_again_at = 0.0
        self.last_break_close_at = 0.0
        self.login_stage = None
        self.navigation_cooldown_until = 0.0
        self.username_value = ""
        self.password_value = ""
        self.engine = None
        self.engine_lock = threading.Lock()

        box = ttk.Frame(root, padding=18)
        box.pack(fill="both", expand=True)
        ttk.Label(box, text="Quick Maths", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(box, text="Press F8 once to answer questions and resume the game after sign-out.", font=("Segoe UI", 12), wraplength=380).pack(anchor="w", pady=(8, 10))
        ttk.Label(box, text="TTRS sign-in (kept only while this app is open)", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.username_var.trace_add("write", lambda *_: setattr(self, "username_value", self.username_var.get()))
        self.password_var.trace_add("write", lambda *_: setattr(self, "password_value", self.password_var.get()))
        ttk.Label(box, text="Username").pack(anchor="w", pady=(4, 0))
        ttk.Entry(box, textvariable=self.username_var, width=36).pack(anchor="w")
        ttk.Label(box, text="Password (masked; never saved)").pack(anchor="w", pady=(4, 0))
        ttk.Entry(box, textvariable=self.password_var, show="*", width=36).pack(anchor="w")
        self.toggle = ttk.Button(box, text="Start auto-answer (F8)", command=self.start)
        self.toggle.pack(anchor="w", pady=(0, 8))
        self.status = tk.StringVar(value="Stopped. Press F8 once to start.")
        ttk.Label(box, textvariable=self.status, font=("Segoe UI", 11), wraplength=380).pack(anchor="w", pady=(10, 6))
        self.last_seen = tk.StringVar(value="Last read: —")
        ttk.Label(box, textvariable=self.last_seen, font=("Segoe UI", 12, "bold"), wraplength=380).pack(anchor="w", pady=(2, 6))
        ttk.Label(box, text="Keep the game visible. F8 toggles; Esc stops. X minimizes; Ctrl+Shift+Q exits.", font=("Segoe UI", 9), foreground="#555", wraplength=380).pack(anchor="w")
        root.protocol("WM_DELETE_WINDOW", self.hide_window)
        keyboard.add_hotkey("F8", self.hotkey, suppress=False)
        keyboard.add_hotkey("esc", self.stop, suppress=False)
        keyboard.add_hotkey("ctrl+shift+q", self.exit_app, suppress=False)
        root.report_callback_exception = self.report_tk_error
        self.set_status("Preparing screen reader…")
        threading.Thread(target=self.prepare_engine, daemon=True).start()

    def prepare_engine(self):
        try:
            with self.engine_lock:
                if self.engine is None:
                    self.engine = RapidOCR()
            if not self.active:
                self.set_status("Ready. Press F8 once to start auto-answer.")
        except Exception as exc:
            self.set_status(f"Screen reader could not start: {exc}")

    def set_status(self, value):
        self.root.after(0, self.status.set, value)

    def start(self):
        if self.active:
            return
        self.active = True
        self.last_question = None
        self.attempt_count = 0
        self.missed_question_frames = 0
        self.pending_signature = None
        self.pending_count = 0
        self.pending_action = None
        self.pending_action_count = 0
        self.login_stage = None
        self.navigation_cooldown_until = 0.0
        self.root.after(0, lambda: self.toggle.configure(text="Stop auto-answer (F8)", command=self.stop))
        self.set_status("Auto-answer is on. Keep the game visible; press F8 or Esc to stop.")
        threading.Thread(target=self.watch_loop, daemon=True).start()

    def stop(self):
        if not self.active:
            return
        self.active = False
        self.root.after(0, lambda: self.toggle.configure(text="Start auto-answer (F8)", command=self.start))
        self.set_status("Auto-answer stopped. Press F8 to start again.")

    @staticmethod
    def parse_question(text):
        # Require an explicit multiplication or division sign; never guess from nearby numbers.
        cleaned = text.lower().replace("∙", "×").replace("·", "×").replace(":", "÷")
        m = re.search(r"(?<!\d)(\d{1,4})\s*([*/×x÷])\s*(\d{1,4})(?:\s*=)?", cleaned)
        if not m:
            return None
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        if op in ("/", "÷"):
            if not b or a % b:
                return None
            answer = str(a // b)
        else:
            answer = str(a * b)
        canonical_op = "/" if op in ("/", "÷", ":") else "*"
        return answer, f"{a}{canonical_op}{b}"

    def hotkey(self):
        if self.active:
            self.stop()
        else:
            self.start()

    def watch_loop(self):
        while self.active:
            try:
                self.scan_and_answer()
            except Exception as exc:
                log_error(traceback.format_exc())
                self.set_status(f"Could not read/answer: {exc}")
                time.sleep(0.8)
            # OCR itself takes most of the cycle; a short pause keeps the app
            # responsive without adding a noticeable delay after a question appears.
            time.sleep(0.05)

    def try_play_again(self, image):
        """Click the TTRS results button only after confirming its label twice."""
        import numpy as np
        width, height = image.size
        # The game may be maximized or in a smaller browser window. Search the
        # lower part of the display across its width instead of assuming a fixed
        # button position; this also excludes browser tabs/address bar and most UI.
        left, top = int(width * 0.22), int(height * 0.48)
        right, bottom = int(width * 0.96), int(height * 0.98)
        crop = image.crop((left, top, right, bottom))
        scale = 2
        crop = crop.resize((crop.width * scale, crop.height * scale))
        result, _ = self.engine(np.asarray(crop))

        recognized = []
        play_again_boxes = []
        for item in (result or []):
            if len(item) < 2:
                continue
            confidence = float(item[2]) if len(item) > 2 else 0.0
            if confidence < 0.30:
                continue
            text = item[1]
            recognized.append(text)
            if "PLAY" in text.upper() or "AGAIN" in text.upper():
                play_again_boxes.append(item[0])
        label = re.sub(r"[^A-Z]", "", " ".join(recognized).upper())
        if "PLAYAGAIN" not in label:
            self.pending_action = None
            self.pending_action_count = 0
            return False

        if self.pending_action == "PLAY_AGAIN":
            self.pending_action_count += 1
        else:
            self.pending_action = "PLAY_AGAIN"
            self.pending_action_count = 1
        if self.pending_action_count < 2:
            self.set_status("Results screen found. Confirming Play Again button…")
            return True

        if time.time() - self.last_play_again_at < 4.0:
            return True

        # Click the recognized words' bounding-box center, safely within the button.
        points = [point for box in play_again_boxes for point in box]
        xs = [left + float(point[0]) / scale for point in points]
        ys = [top + float(point[1]) / scale for point in points]
        screen_w, screen_h = pyautogui.size()
        x = round(((min(xs) + max(xs)) / 2) * screen_w / width)
        y = round(((min(ys) + max(ys)) / 2) * screen_h / height)
        self.set_status("Play Again found. Clicking to start the next round…")
        pyautogui.click(x, y)
        self.last_play_again_at = time.time()
        self.pending_action = None
        self.pending_action_count = 0
        return True

    def try_close_break_message(self, image):
        """Dismiss TTRS's daily-rest message before attempting Play Again."""
        import numpy as np
        width, height = image.size
        # The rest message is a centered modal above the results card. Inspect
        # that area for its message, rather than mistaking other X-shaped graphics.
        left, top = int(width * 0.30), int(height * 0.14)
        right, bottom = int(width * 0.72), int(height * 0.55)
        crop = image.crop((left, top, right, bottom))
        scale = 2
        crop = crop.resize((crop.width * scale, crop.height * scale))
        result, _ = self.engine(np.asarray(crop))

        texts = []
        message_boxes = []
        for item in (result or []):
            if len(item) < 2:
                continue
            confidence = float(item[2]) if len(item) > 2 else 0.0
            if confidence < 0.30:
                continue
            text = item[1]
            texts.append(text)
            upper = text.upper()
            box = item[0]
            xs = [left + float(point[0]) / scale for point in box]
            ys = [top + float(point[1]) / scale for point in box]
            cx = (min(xs) + max(xs)) / (2 * width)
            cy = (min(ys) + max(ys)) / (2 * height)
            if 0.35 <= cx <= 0.67 and 0.19 <= cy <= 0.49 and upper.strip() != "RESULTS":
                message_boxes.append(item[0])

        message = re.sub(r"[^A-Z]", "", " ".join(texts).upper())
        if "BREAK" not in message and not ("PLAYED" in message and "TOMORROW" in message):
            if self.pending_action == "CLOSE_BREAK":
                self.pending_action = None
                self.pending_action_count = 0
            return False

        if self.pending_action == "CLOSE_BREAK":
            self.pending_action_count += 1
        else:
            self.pending_action = "CLOSE_BREAK"
            self.pending_action_count = 1
        if self.pending_action_count < 2:
            self.set_status("Rest-break message found. Confirming its close button…")
            return True
        if time.time() - self.last_break_close_at < 3.0:
            return True
        if not message_boxes:
            return True

        points = [point for box in message_boxes for point in box]
        xs = [left + float(point[0]) / scale for point in points]
        ys = [top + float(point[1]) / scale for point in points]
        text_left, text_right = min(xs), max(xs)
        text_top = min(ys)
        heights = []
        for box in message_boxes:
            box_ys = [top + float(point[1]) / scale for point in box]
            heights.append(max(box_ys) - min(box_ys))
        line_height = sorted(h for h in heights if h > 0 and h < 60)
        line_height = line_height[len(line_height) // 2] if line_height else 24.0

        # The close X sits just above and close to the message panel's upper-right.
        x = text_right - 0.05 * (text_right - text_left)
        y = text_top - 2.1 * line_height
        screen_w, screen_h = pyautogui.size()
        x = round(x * screen_w / width)
        y = round(y * screen_h / height)
        self.set_status("Rest-break message found. Clicking its X before Play Again…")
        pyautogui.click(x, y)
        self.last_break_close_at = time.time()
        self.pending_action = None
        self.pending_action_count = 0
        return True

    def try_signin_and_resume(self, image):
        """Navigate TTRS sign-in and return to the single-player Garage game."""
        if time.time() < self.navigation_cooldown_until:
            return True

        import numpy as np
        width, height = image.size
        left, top = int(width * 0.22), int(height * 0.14)
        right, bottom = int(width * 0.97), int(height * 0.96)
        scale = 1.5
        crop = image.crop((left, top, right, bottom))
        crop = crop.resize((int(crop.width * scale), int(crop.height * scale)))
        result, _ = self.engine(np.asarray(crop))

        entries = []
        for item in (result or []):
            if len(item) < 2 or (len(item) > 2 and float(item[2]) < 0.30):
                continue
            box = item[0]
            xs = [left + float(point[0]) / scale for point in box]
            ys = [top + float(point[1]) / scale for point in box]
            norm = re.sub(r"[^A-Z0-9]", "", item[1].upper())
            entries.append({"norm": norm, "x": (min(xs) + max(xs)) / 2,
                            "y": (min(ys) + max(ys)) / 2})

        labels = {entry["norm"] for entry in entries}

        def has(word):
            return any(word in label for label in labels)

        def matches(word):
            return [entry for entry in entries if word in entry["norm"]]

        def click_entry(entry):
            screen_w, screen_h = pyautogui.size()
            pyautogui.click(round(entry["x"] * screen_w / width),
                            round(entry["y"] * screen_h / height))
            self.navigation_cooldown_until = time.time() + 1.2

        # Public page -> choose Log In.
        if has("REGISTER") and has("LOGIN"):
            target = matches("LOGIN")[0]
            click_entry(target)
            self.set_status("Opening TTRS sign-in…")
            return True

        # Choose the school sign-in route, then the student route.
        if has("SCHOOL") and has("FAMILY") and has("TUTOR"):
            click_entry(matches("SCHOOL")[0])
            self.set_status("Choosing School sign-in…")
            return True
        if has("STUDENT") and has("TEACHER"):
            click_entry(matches("STUDENT")[0])
            self.set_status("Choosing Student sign-in…")
            return True

        # Enter the username, then select the Password option (not the PIN option).
        username_form = has("USERNAME") and has("PASSWORD") and has("PIN")
        if username_form:
            if not self.username_value.strip():
                self.set_status("Sign-in page found. Enter your username in Quick Maths.")
                return True
            if self.login_stage is None:
                field = matches("USERNAME")[0]
                click_entry(field)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.write(self.username_value.strip(), interval=0.02)
                self.login_stage = "username_entered"
                self.navigation_cooldown_until = time.time() + 0.8
                self.set_status("Username entered. Selecting Password sign-in…")
                return True
            if self.login_stage in ("username_entered", "password_selected"):
                password_options = matches("PASSWORD")
                if password_options:
                    option = max(password_options, key=lambda entry: entry["y"])
                    # The Password caption sits below its large selectable tile.
                    # Click inside the tile rather than below it on the caption.
                    option = dict(option)
                    option["y"] -= 0.08 * height
                    click_entry(option)
                    self.login_stage = "password_selected"
                    self.set_status("Password sign-in selected…")
                    return True

        # On the password page, type the masked in-memory password and submit.
        password_page = has("PASSWORD") and has("LOGIN") and has("USERNAME") and not has("PIN")
        if password_page and self.login_stage != "password_submitted":
            if not self.password_value:
                self.set_status("Password page found. Enter your password in Quick Maths.")
                return True
            password_fields = matches("PASSWORD")
            if password_fields:
                field = max(password_fields, key=lambda entry: entry["y"])
                click_entry(field)
                pyautogui.write(self.password_value, interval=0.02)
                time.sleep(0.12)
                pyautogui.press("enter")
                self.login_stage = "password_submitted"
                self.navigation_cooldown_until = time.time() + 2.0
                self.set_status("Submitting sign-in…")
            return True

        # After sign-in, the home page's play icon opens the Single Player list.
        # On that list, choose the Garage card, then its Play button.
        if has("GARAGE") and has("PLAY"):
            click_entry(matches("PLAY")[-1])
            self.set_status("Starting Garage…")
            return True
        if has("GARAGE") and has("JAMMING") and has("GIG"):
            self.login_stage = None
            click_entry(matches("GARAGE")[0])
            self.set_status("Choosing Garage…")
            return True

        # The logged-in home page has a player badge and a play icon button.
        # Use its screen position only when none of the mode/game screens match.
        if has("NEWARTIST") and not any(has(name) for name in
                                         ("SINGLEPLAYER", "GARAGE", "JAMMING", "GIG", "STUDIO", "SOUNDCHECK")):
            badge = matches("NEWARTIST")[0]
            screen_w, screen_h = pyautogui.size()
            x = badge["x"] - 0.227 * width
            y = badge["y"] - 0.014 * height
            pyautogui.click(round(x * screen_w / width), round(y * screen_h / height))
            self.navigation_cooldown_until = time.time() + 1.2
            self.set_status("Opening the game list…")
            return True
        return False

    def scan_and_answer(self):
        if self.engine is None:
            with self.engine_lock:
                if self.engine is None:
                    self.engine = RapidOCR()
        image = ImageGrab.grab().convert("RGB")
        import numpy as np
        width, height = image.size
        # OCR only the centered prompt area. Reading the whole desktop can mix in
        # unrelated text or partially covered digits from the helper window.
        left, top = int(width * 0.30), int(height * 0.27)
        right, bottom = int(width * 0.70), int(height * 0.52)
        crop = image.crop((left, top, right, bottom))

        def read_at_scale(scale):
            """Read the prompt crop at one size and return its best screen box."""
            sized = crop if scale == 1 else crop.resize((crop.width * scale, crop.height * scale))
            result, _ = self.engine(np.asarray(sized))
            ranked = []
            for item in (result or []):
                if len(item) < 2:
                    continue
                parsed = self.parse_question(item[1])
                if parsed is None:
                    continue
                box = item[0]
                xs = [left + float(point[0]) / scale for point in box]
                ys = [top + float(point[1]) / scale for point in box]
                cx = (min(xs) + max(xs)) / (2 * width)
                cy = (min(ys) + max(ys)) / (2 * height)
                if not (0.20 <= cx <= 0.80 and 0.12 <= cy <= 0.58):
                    continue
                distance = ((cx - 0.50) / 0.30) ** 2 + ((cy - 0.34) / 0.22) ** 2
                confidence = float(item[2]) if len(item) > 2 else 0.0
                if confidence < 0.65:
                    continue
                ranked.append((distance - 0.08 * confidence, parsed, item, scale))
            ranked.sort(key=lambda candidate: candidate[0])
            if not ranked:
                return None
            # If equally plausible OCR lines disagree, treat the frame as unclear.
            if len(ranked) > 1 and ranked[1][0] - ranked[0][0] < 0.12 and ranked[1][1][1] != ranked[0][1][1]:
                return None
            return ranked[0]

        native = read_at_scale(1)
        enlarged = read_at_scale(2)
        consensus = bool(native and enlarged and native[1][1] == enlarged[1][1])
        chosen = enlarged or native
        found = None if chosen is None else (chosen[1][0], chosen[1][1], chosen[2], chosen[3], consensus)
        if native and enlarged and not consensus:
            native_text = native[1][1].replace('*', ' × ').replace('/', ' ÷ ')
            enlarged_text = enlarged[1][1].replace('*', ' × ').replace('/', ' ÷ ')
            self.set_status(f"OCR reads disagree ({native_text} vs {enlarged_text}); waiting, not sending.")
            return
        if found is None:
            if self.try_close_break_message(image):
                return
            if self.try_play_again(image):
                return
            if self.try_signin_and_resume(image):
                return
            self.missed_question_frames += 1
            if self.missed_question_frames >= 3:
                self.last_question = None
                self.pending_signature = None
                self.pending_count = 0
            self.set_status("Auto-answer is on. Keep the TT Rock Stars tab open and visible; looking for its equation…")
            return
        answer, signature, equation_item, scale, consensus = found
        self.missed_question_frames = 0
        if signature != self.pending_signature:
            self.pending_signature = signature
            self.pending_count = 1
        else:
            self.pending_count += 1
        # Two independent image sizes agree, so answer immediately. When only
        # one read sees the equation, require the next screen frame to agree.
        if not consensus and self.pending_count < 2:
            self.set_status(f"Reading {signature}; checking once more…")
            return
        if signature == self.last_question:
            if self.attempt_count >= 2 or time.time() - self.last_attempt_at < 1.4:
                return
        else:
            self.attempt_count = 0
        self.last_question = signature
        self.last_attempt_at = time.time()
        self.attempt_count += 1
        self.root.after(0, self.last_seen.set, f"Last read: {signature.replace('*', ' × ').replace('/', ' ÷ ')} = {answer}")
        # A click on the game prompt returns keyboard focus to its canvas/input
        # after the user has clicked Start in this helper window.
        target = equation_item[0]
        xs = [left + float(point[0]) / scale for point in target]
        ys = [top + float(point[1]) / scale for point in target]
        click_x = (min(xs) + max(xs)) / 2
        click_y = (min(ys) + max(ys)) / 2
        screen_w, screen_h = pyautogui.size()
        click_x = round(click_x * screen_w / image.width)
        click_y = round(click_y * screen_h / image.height)
        self.set_status(f"Found: {signature} = {answer}; focusing game, typing, then pressing Enter…")
        pyautogui.click(click_x, click_y)
        time.sleep(0.03)
        pyautogui.write(answer)
        pyautogui.press("enter")
        self.set_status(f"Sent {answer} and Enter. Check that the game advanced; watching for the next question.")

    def hide_window(self):
        self.root.iconify()

    def report_tk_error(self, exc_type, exc_value, exc_traceback):
        log_error("GUI error:\n" + "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        self.set_status(f"App error logged to {LOG_PATH.name}: {exc_value}")

    def exit_app(self):
        self.active = False
        self.root.after(0, self._exit_now)

    def _exit_now(self):
        keyboard.unhook_all_hotkeys()
        self.root.destroy()


if __name__ == "__main__":
    window = tk.Tk()
    QuickMaths(window)
    window.mainloop()
