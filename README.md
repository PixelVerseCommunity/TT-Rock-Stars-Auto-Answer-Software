# TT-Rock-Stars-Auto-Answer-Software
Made for TTRS AKA Times Tables Rock stars it is a maths software made for that. It will answer your questions.

# Quick Maths for Windows

A small Windows helper that reads multiplication and division questions from the visible game screen, types the answer, and presses Enter. It can also try to resume the game after a round or sign-out.

## Download and run

1. On this GitHub page, click **Code** → **Download ZIP**.
2. In Downloads, right-click the ZIP and choose **Extract All**.
3. Open the extracted folder. Keep these files together in one folder: `Install-and-Run.bat`, `quick_maths.py`, `requirements.txt`, and `README.md`. You can move that folder and rename the folder to anything you like; do not rename the files inside it.
4. Install Python 3.12 for Windows from [python.org](https://www.python.org/downloads/). Python 3.15 is not supported by the OCR package used here. The installer needs the Python Launcher (`py`) and internet access on first run.
5. Double-click `Install-and-Run.bat`. Keep the command window open while setup runs. On first launch, it creates a private `.venv312` folder and downloads the required packages; this can take a few minutes. The Quick Maths window then opens.
6. Enter your TTRS username and password in Quick Maths if you want it to resume after sign-out. The password is masked and kept in memory only while the app is open.
7. Leave the TTRS game tab visible, press **F8** to start, and return to the game. The helper types an answer and presses Enter when its two OCR reads agree. Press **F8** or **Esc** to stop.

## Keep the download small

Only the source files and installer belong in the GitHub repository. Do not upload `.venv`, `.venv312`, `setup.log`, `quick_maths.log`, or `__pycache__`. Dependencies are downloaded by the batch file on the first run. The included `.gitignore` excludes generated files and virtual environments.

To make a small ZIP yourself, select the four files listed in step 3 (and optionally `.gitignore`) and compress only those. Do not compress the whole folder after running the app, because its `.venv312` contains the downloaded OCR libraries and makes the archive much larger.

## Notes

- Keep the browser game visible and unminimized on the primary display; this helper reads the screen.
- The helper ignores unclear or conflicting equation reads rather than guessing. OCR can still misread a clear-looking question, so check the displayed **Last read** line.
- If setup fails, keep the command window open to read the error. `setup.log` is created in the app folder; you can share the error text when asking for help, but do not publish logs that may contain personal computer paths.
- This is an unofficial helper and is not affiliated with Times Tables Rock Stars.
