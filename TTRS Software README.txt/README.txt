QUICK MATHS FOR WINDOWS

Install and first run
1. This app's OCR library currently requires Python 3.12. If you have Python 3.15, install Python 3.12 alongside it from https://www.python.org/downloads/; you do not need to uninstall 3.15. The installer selects Python 3.12 with the Python launcher (`py`).
2. Double-click Install-and-Run.bat. It creates a private app environment and downloads the OCR and keyboard packages the first time. Keep this folder together.
3. Enter your TTRS username and password in Quick Maths, click Start (or press F8), then return to the game.
4. If setup fails, the installer shows the full error and saves it in `setup.log`. Check internet access and try again; if it still fails, share that log so the specific cause can be fixed.

Using it
- Enter your TTRS username and password in the helper's sign-in fields. The password is masked and both values stay in memory only; they are not written to disk or included in the ZIP. Keep the helper open while you want it to recover from sign-out.
- Leave the game tab open and visible. Keep this helper in the upper-left; its narrow window is sized to leave the centered equation visible on common screen layouts.
- The app warms up its OCR reader at launch. Press F8 once to start watching; it reads the screen and selects an explicit equation near the game's centered prompt, then types the answer and presses Enter.
- Press F8 again or Esc to stop; use either key to start again.
- The app ignores the same question until it sees the prompt change or disappear.
- It reads the prompt at two image sizes and sends the answer immediately only when both reads agree on the exact equation. If only one read sees it, it waits for the next screen frame to confirm. Low-confidence or conflicting reads are not typed. Before typing, it clicks the detected prompt to return keyboard focus to the game, then types the digits and presses Enter with no per-key delay.
- When the round ends, it searches the lower game area for the Play Again label, even when Chrome is windowed, and clicks it after confirming the label twice.
- If TTRS shows its daily-rest message over the results screen, the helper detects the message, clicks its close X, and then proceeds to Play Again.
- If TTRS signs out, it follows the shown School -> Student -> Password sign-in route, then opens Single Player -> Garage -> Play. The helper pauses for you to enter either credential if its field is blank.
- The window is larger. Clicking its X minimizes it to the taskbar while auto-answer continues. Press Ctrl+Shift+Q to quit completely.
- Runtime errors are saved to `quick_maths.log` beside the app.
- The app shows the last equation and answer it recognized. Keep the TT Rock Stars browser window open, unminimized, and in front; screen reading cannot continue if the game page is closed or hidden behind another window.

Notes
- OCR works best when the game question is large and unobstructed. It captures the primary display. If the full equation is obscured or OCR confidence is low, it waits instead of typing a guessed answer.
- It supports whole-number multiplication and exact whole-number division. It will not answer if it cannot read a clear equation.
- This package needs internet on first launch to install its dependencies. Keep the app folder in a location you can write to.
