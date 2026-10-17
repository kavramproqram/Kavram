# Kavram

 Kavram  is a free and open-source archive platform that brings educational and media projects together under a single roof.

It provides different tools such as text, drawing, sound, video, screen recording, and notes within a single system. You can edit the content you create, connect it with other content, and create mind maps through SPHERE to archive them in encrypted form.

Kavram is not limited to ready-made programs. You can also integrate programs that you develop yourself according to your needs. In this respect, Kavram is designed not simply as a collection of applications, but as a platform where you can create your own working environment.

10 integrated programs + extensible program system.**

<img width="3450" height="1880" alt="sh" src="https://github.com/user-attachments/assets/2f3a8157-ee17-4cf0-97b0-be832fb5480b" />

###  Workflow

1. **File Creation:** The required files are created in the main programs.
2. **Mapping:** These files are mapped on the main screen.
3. **Export:** The mind map is exported in encrypted form (`Export`).

>  **Tip:** You can share the file you create directly without a password, or sell its access password.

---

**Important Note:** Please make sure that the `.kitap` files you download come from a trusted source.


###  The platform consists of various integrated programs designed to meet the different needs of users:



| Program       | What does it do?            |
| ------------- | ------------------------ |
| **SPHERE**    | Main screen                |
| **TEXT**      | Text editing          |
| **DRAWING**   | Drawing                    |
| **SOUND**     | Audio editing           |
| **AI**        | Artificial memory             |
| **MEDIA**     | Combined audio + video archive |
| **REC**       | Screen and audio recording       |
| **COPY**      | Notebook              |
| **FILTER**    | Audio filtering           |
| **CONVERTER** | Format conversion        |


---

# Installation

> **Note:** Installation on Linux Mint XFCE is recommended.

<img width="1920" height="1049" alt="3" src="https://github.com/user-attachments/assets/0b8b71af-737a-4387-a516-77c0fa217e6c" />

---

# SPHERE

## Main Screen

The main screen is where mind maps are archived in encrypted form.

<img width="1918" height="1047" alt="s1" src="https://github.com/user-attachments/assets/4e6782df-e53e-4245-a70f-131ed9d720e4" />

<img width="1920" height="1047" alt="sphere" src="https://github.com/user-attachments/assets/bccf70d7-1060-4ec4-a2be-36493d3fe0f6" />

## Button Functions

**1. File** — Used to import content into the archive and add a square (file).

**3 and 4.** — Used to undo performed actions.

**5. +** — Used to add a square.

**6.** — Opens the location list of connections.

**7. Terminal** — Opens the terminal for using terminal commands.

### Terminal Commands

**1. `reset`**

Deletes everything completely.

**2. `ap image location`**

Used to change the wallpaper.

Example:

```text
ap /home/lts/Pictures/resim4.png
```
---

# Adding External Programs to the System
---

**3. `name program location`**

Adds a program to the bottom section of the menu opened with the `Ctrl + Q` shortcut.

This section is used for utility programs.

Example:

```text
Zaman /home/lts/Kavram/Programlar/Zaman/Zaman
```

<img width="1920" height="1049" alt="Z" src="https://github.com/user-attachments/assets/a569dba7-1714-42cd-8502-16d0bd917692" />

**4. `k name program location`**

Adds a program to the top section of the menu opened with the `Ctrl + Q` shortcut.

This section is used for main programs. Adding files is also possible.

Example:

```text
k Blender /home/lts/blender-5.2.0-linux-x64/blender
```

<img width="1920" height="1050" alt="bl" src="https://github.com/user-attachments/assets/2749222e-e76c-43ec-b58f-aa33c5370315" />


> **Important:** Since Kavram works somewhat like an operating system, when the main program is closed, all programs connected to it are automatically closed.
>
> For example, Blender asks you to save the file before it is closed.
>
> If you close the Kavram program, Blender will close without asking anything. Back up your files beforehand to prevent data loss.

**8. `/`**

Used to turn the grid structure created in the background on or off.

**9. Export**

**Left click:** Creates a file in XZ format. The file is smaller, but creation and export take longer.

**Right click:** Saves in GZ format. The file is larger compared to XZ, but it is created faster.

The resulting file is saved in encrypted form with the `.kitap` extension.

**10. Sphere**

This button is located on the far right of the top bar in all programs, with different names.

It is used to open the menu triggered by the `Ctrl + Q` shortcut.

### Commands That Require Attention

There are 3 commands/actions that require particular attention in this program:

**1. Back up your files.**

Although the possibility of data loss is very low, it is not zero.

**2. `reset` command**

When `reset` is entered in the terminal, everything is deleted.

**3. `Ctrl + S`**

The `Ctrl + S` shortcut applies to the 7 main programs outside of Sphere (the main screen).

It closes the currently open program and returns to the main screen. It does not save anything; it only closes the program.

For quick saving, there is an icon next to the **File** button in every editor. This icon does not apply to Sphere.

The function of this icon in Sphere is to make the layout currently being created the default layout. This way, everything opens in the same state when the program is opened again.

---

# TEXT

## Text Editing Program

## Program Purpose

**Text** is a PyQt5-based text editing platform that allows users to create and format rich-text documents, perform basic file operations, and organize notes/code blocks.

---
<img width="1920" height="1049" alt="T1" src="https://github.com/user-attachments/assets/665de852-5ba9-4185-b21a-39a42a75a2bc" />

## Button Functions

| Button  | Function |
| :--- | :--- |
| **File** | Starts the file opening and import dialog. |
| **Save** | Saves changes and updates made to the active text document. |
| **Undo / Redo** | Undoes or redoes steps in the editing history. |
| **Font Selector** | Dynamically changes the text size in the interface. |
| **Terminal** | Allows special deletion commands (such as deleting language or character groups) to be executed. |
| **Auto Scroll / Read Mode** | Activates automatic scrolling (reading) mode at the specified speed. |
| **Search and Match Buttons** | Searches within the text and navigates forward/backward between found results. |
| **Export** | Exports created documents. |
| **Text** | This button exists in all other programs, displays the program name, and triggers the `Ctrl + Q` shortcut. |


---

# DRAWING

## Program Purpose
Drawing and animation.  
---
<img width="1920" height="1050" alt="d1" src="https://github.com/user-attachments/assets/f4d11e07-ac0c-4ff9-b1f0-672a7c87cf5c" />

---
## Button Functions
---

| Button Name | Left Click Function | Right Click Function |
| :--- | :--- | :--- |
| **File** | Import an image or project file. | Add a reference image. |
| **Save** | Saves the project. | — |
| **Page Number** | Opens the page menu. | — |
| **+** | Adds a new page. | — |
| **-** | Deletes the current page. | — |
| **Undo** | Undoes the last action. | — |
| **Redo** | Redoes the undone action. | — |
| **Pen Style** | Changes the brush style. | — |
| **O** | Turns navigation mode on/off. | Opens the canvas size/resolution dialog. |
| **G** | Shows/hides the reference image. | Reference transparency and layer position menu. |
| **Mix Angle** | Opens the mix angle menu. | Opens the blending mode menu. |
| **Color** | Opens the color selection menu. | — |
| **Eraser** | Turns eraser mode on/off. | Changes the background color. |
| **R:** | Opens the brush/eraser size menu. | — |
| **Drawing** | Opens the layer menu. | — |
| **#** | Pins the active layer to the top. | — |
| **lm** | Turns Lazy Mouse mode on/off. | Opens the Lazy Mouse settings menu. |
| **/** | Turns pressure sensitivity on/off. | — |
| **» «** | Turns vertical mirror mode on/off. | Turns horizontal mirror mode on/off. |
| **Export** | Opens the export dialog. | Advanced export (FPS) menu. |
| **Drawing** | This button exists in all other programs, displays the program name, and triggers the `Ctrl + Q` shortcut. | — |


---

# SOUND
## Program Purpose
Audio editing program
---

<img width="1920" height="1047" alt="Ekran görüntüsü_2026-08-28_10-42-08" src="https://github.com/user-attachments/assets/33505066-7391-4be6-a0f7-0f3c17ae7406" />

---

## Button Functions

---


| Button Name | Left Click Function (`Left Click`) | Right Click Function (`Right Click`) |
| :--- | :--- | :--- |
| **File** | Imports audio files (`.wav`) or a `.sound` package. | — |
| **Save (disk icon)** | Saves the current audio or `.sound` package. | — |
| **Undo** | Undoes the last action (`Ctrl+Z`). | — |
| **Redo** | Redoes the undone action (`Ctrl+Shift+Z` or `Ctrl+Y`). | — |
| **Cut** | Adds a cut point at the position of the playback cursor. | — |
| **`::`** | Automatically removes all silent areas within the selected range. | — |
| **Delete** | Deletes selected audio sections. | — |
| **Play** | Starts / pauses playback. | — |
| **Record** | Starts / stops microphone recording. | — |
| **I** | Turns post-recording filters on/off (persistent setting). | — |
| **Waveform Scale (number)** | Adjusts the waveform width (between 1–7). | — |
| **Speed** | Changes playback speed (`0.1x – 3x`). | — |
| **Scroll Step** | Sets the scrolling step with the mouse wheel (`0.1s – 30s`). | — |
| **`/`** | Opens / closes the temporary text panel. | — |
| **O** | Centers / left-aligns the text in the panel. | — |
| **Text Size (number)** | Sets the text size in the panel (also adjustable with the mouse wheel). | — |
| **Export** | Exports audio as a `WAV` file. | Exports audio as a `.sound` package together with text and settings. |
| **Sound** | This button exists in all other programs, displays the program name, and triggers the `Ctrl + Q` shortcut. | — |

---

# AI

## Artificial Memory
## Program Purpose


**AI** is a desktop application that provides SQLite-based dynamic data/question-answer management, multimedia integration (audio, images, video, external files), and a customized AI/Chat interaction interface.

Its main purposes are:
- **Questions and Answers (Package Management):** Creating, editing, and deleting question-answer packages with unique question validation in the database.
- **Multimedia Support:** Attaching multiple audio (`.mp3`, `.wav`), image (`.png`, `.jpg`), video (`.mp4`), and external file attachments to question-answer entries.
- **Chat and Interaction Mode:** Searching through saved question-answer data and navigating through history mode.
- **Lazy Loading and Performance:** Optimizing resource usage through the SQLite database structure and cache management.

---

## Button Functions
---

<img width="1920" height="1043" alt="ai" src="https://github.com/user-attachments/assets/63637946-2309-4697-ba3b-3ac3395fff04" />


| Button / Component | Text / Icon | Function |
| :--- | :--- | :--- |
| **File** | File | Starts the file selection dialog for importing/opening a database or media files. |
| **Save** | Save | Saves current changes, packages, and database updates. |
| **New** | New | Creates a new empty question-answer package in the data management panel and gives it focus. |
| **Chat** | Chat | Activates the chat (interaction and search) panel. |
| **Exit Fullscreen** | _ | Exits the active multimedia overlay or fullscreen mode. |
| **Edit** | Edit | Activates the data management (SQLite question-answer packages) page. |
| **Clear Chat** | X | Clears the current message bubbles and chat history view. |
| **Font Selector** | Numeric Value | Dynamically changes the text size in the interface (through clicking, menu, or mouse wheel). |
| **Clear (AI/Folder)** | S | Clears the temporary `ai` working folder and open data memory. |
| **Export** | Export | Exports created data packages and attached media. |
| **AI Mode** | AI | This button exists in all other programs, displays the program name, and triggers the `Ctrl + Q` shortcut. |



---

# MEDIA

## Combined Audio and Video Archive Program
---
<img width="1920" height="1049" alt="M" src="https://github.com/user-attachments/assets/2aa5206d-dedb-4256-b859-ffb58721ae99" />

---

## Button Functions

---

| Button Name | Left Click Function (`Left Click`) | Right Click Function (`Right Click`) |
| :--- | :--- | :--- |
| **File** | Imports media files (video, audio, `.media` archive). | — |
| **Save (disk icon)** | Quickly saves the current project (overwrites if previously saved, otherwise opens Save As). | — |
| **Undo** | Undoes the last action (`Ctrl+Z`). | — |
| **Redo** | Redoes the undone action (`Ctrl+Shift+Z`). | — |
| **Play** | Starts / pauses playback of the selected media segment. | — |
| **`/`** | Turns sequential playback mode on/off (automatic transition between segments). | — |
| **Cut** | Splits the active segment into two parts at the position of the playback cursor. | — |
| **Delete** | Deletes the selected segment on the timeline. | — |
| **Camera** | Opens the camera (under development). | — |
| **Sound** | Starts / stops audio recording with the microphone. | — |
| **`I`** | Turns noise filtering on/off (persistent setting). | — |
| **`S`** | Clears the `medya_cut` working folder and completely resets the timeline. | — |
| **Seek Interval (Combo Box)** | Sets the forward/backward seeking or skipping step with the mouse wheel (e.g. 2s, 5s, 1min). | — |
| **Playback Speed (Combo Box)** | Changes media playback speed (e.g. 0.5x, 1x, 2x). | — |
| **Export** | Exports all timeline segments as a `.media` archive file (saves as a project). | Exports the entire timeline as a single `.mkv` video file by rendering it. |
| **Media** | Switches to the main application (`Kavram`). | — |


# REC

## Screen and Audio Recording Program

---

## Program Purpose

---

The main purpose of this program is to record screen and audio.
---


<img width="1918" height="1046" alt="r1" src="https://github.com/user-attachments/assets/9e91a992-8da1-4b17-b614-d4e0e4f235fa" />

---

## Button Functions

---

| Symbol / Name | Description / Function |
| :--- | :--- |
| **File** | Opens the file selector window to load an external video (`.rec`, `.mp4`, `.mkv`) or audio (`.wav`) file into the player. |
| **Camera** | Camera module currently under development. |
| **Windows** | Determines whether screen recording should be enabled. The button color changes when active. Can be disabled when recording audio only. |
| **Sound** | Determines whether system/microphone audio should be recorded. Automatically detects EasyEffects and default PulseAudio sources. |
| **I (Noise Filter)** | Activates/deactivates the noise reduction and audio filtering chain. When active, advanced audio cleaning is applied during export. |
| **S (Delete)** | Deletes everything and closes. |
| **Thickness (Number Button)** | Adjusts the thickness (30–50 px) of the floating time/input window. <br>• **Mouse Wheel:** Increases/decreases thickness.<br>• **Left Click:** Resets the floating window to its default position.<br>• **Right Click:** Sets the current position of the floating window as the default. |
| **/** | **Input Overlay Toggle:** Turns the mechanism that displays keyboard key presses and mouse clicks (on a floating black panel over the screen) on/off. |
| **Z** | **Time Overlay Toggle:** Turns the visibility of the floating live recording duration panel at the top of the screen on/off. |
| **Duration Dropdown Menu** | **Recording Limit (e.g. 5 min):** Automatically pauses the recording when the specified duration is reached (between 1 min and 30 min). |
| **Segment Dropdown Menu** | **Segment Duration (e.g. 30 sec):** Determines how often a new segment file (`s1.mkv`, `s2.mkv`...) is created in the background during recording. |
| **Play / Pause** | Starts/pauses recording or media playback. (Global Shortcut: `Ctrl + M`) |
| **X** | Closes the currently open file playback bar and resets the player. |
| **Segment X Menu** | Lists the recording segments currently accumulated in memory/on disk. Allows individual segments to be deleted or all segments to be cleared with the **All** option. |
| **Export** | Combines all recorded segments in sequence, optionally applies audio filtering, and saves the final file as MKV/WAV. |
| **Rec** | This button exists in all other programs, displays the program name, and triggers the `Ctrl + Q` shortcut. |

> **Note:** Designed to work on older computers. Use with caution; there is a time limit.
>
> **It may not be compatible with every computer.** Testing is recommended before creating large files.

<img width="1920" height="1045" alt="R" src="https://github.com/user-attachments/assets/bbb4c6c4-e8c5-41cf-9273-8ffed6543335" />

---

# COPY
## Program Purpose
Notebook program
---
<img width="1920" height="1043" alt="N" src="https://github.com/user-attachments/assets/34d80842-0917-4ae5-8d5c-5f28b30d7e00" />


---
## Button Functions
---

| Button Name | Description / Function |
| :--- | :--- |
| **File** | Opens a `.copya` project file. |
| **Save (disk icon)** | Saves the current project (opens Save As if there is no existing file). |
| **`+`** | Adds a new empty note. |
| **Gallery** | Selects images, `.txt`, and `.txr` text files and adds them as an existing or new gallery note. |
| **Document** | Selects a `PDF` or `PNF` (`Drawing`) file and imports it page by page as a gallery note. |
| **`#` (page number)** | Opens a menu for navigating between items in the expanded gallery. |
| **`I`** | Starts/stops automatic scrolling (reading mode). |
| **Speed (number)** | Opens a menu for adjusting automatic scrolling speed. |
| **Size (number)** | Adjusts the size of the page displayed in document mode. |
| **`X`** | Deletes the currently expanded note. |
| **`_` (underscore)** | Minimizes (closes) the expanded note. |
| **`/` (slash)** | Copies the content of the active note to the clipboard (file paths for images, plain text for text). |
| **Export** | Exports the current project as a `.copya` archive. |
| **Copy** | This button exists in all other programs, displays the program name, and triggers the `Ctrl + Q` shortcut. |


---

# Filter - Audio & Video Filtering System

**Filter** is a professional desktop application that processes audio and video files using advanced spectral noise reduction, intelligent VAD (Voice Activity Detection), and a multi-layer filtering engine.

---

**Filter** provides advanced filtering and editing operations for audio and video files:

- **x1 Filter (Spectral Cleaning):** Improves audio quality with a 2-stage spectral noise reduction algorithm. Sensitivity is controlled with a power setting (1–9).
- **x2 Filter (Smart Low-Frequency Suppression):** Completely silences noise regions below the selected frequency within the 30–200 Hz range. Intelligent VAD-based detection.
- **Noise Profile Management:** Targeted filtering using user-created noise profiles. Maximum of 8 profiles.
- **Video Support:** Extracts audio from video files, filters it, and combines the processed audio with the video (FFmpeg integration).
- **Audio Editing Panel:** Settings for overall volume, background music level, pitch, playback speed, and post-completion music duration.
- **Persistent Music Addition:** Permanently saves background music and automatically adds it each time.
- **5-Second Preview:** Allows the filtered audio to be listened to before processing.
- **Report Panel:** Last 5 processing records in a selectable and copyable text field.
- **External Connection Support:** Processes audio coming from modules such as Media and Camera through the `process_audio_background()` method.

---


<img width="1920" height="1048" alt="F" src="https://github.com/user-attachments/assets/c6763870-86d7-4973-b307-0e94eecca578" />

---
## Button Functions
---

| Button | Label | Left Click | Right Click |
| :--- | :--- | :--- | :--- |
| **File** | `File` | Loads an audio or video file. | *(None)* |
| **:: (Add Profile)** | `::` | Selects an audio file to add a noise profile. Maximum 8 profiles. | *(None)* |
| **/ (Editing)** | `/` | Opens/closes the audio editing panel (overall volume, music level, pitch, speed, extra duration). | *(None)* |
| **Process** | `Process` | Applies the active filters to the selected file and starts processing. | *(None)* |
| **Reset** | `Reset` | Resets the settings if the editing panel is open; if closed, restores all profiles to their defaults (x1 power=5, x2 cutoff=75 Hz). | *(None)* |
| **Play** | `Play` | Plays a 5-second preview of the filtered audio. Clicking again pauses it. | *(None)* |
| **Music** | `Music` | Selects background music (temporary). | Makes the selected music permanent or cancels it. |
| **Export** | `Export` | Saves the filtered audio or video. Audio: WAV, MP3, FLAC; Video: Original format. | *(None)* |

--- 
> **Note:** This program is connected to 3 programs: **Sound, Media and Rec.**
>
> These 3 programs have an **I** icon in their top bar. If you activate this icon, the audio is filtered when you make a recording.
---

# CONVERTER
## Program Purpose
File Format Conversion Program
---
<img width="1920" height="1027" alt="C" src="https://github.com/user-attachments/assets/87a96bb1-d300-48c4-a062-9aaf4cf3e815" />


---
## Button Functions
---


| Control Name | Type | Interaction Function / Description |
| :--- | :--- | :--- |
| **File** | Button | Opens the file dialog to select the source file to be converted (audio, video, PDF, image). |
| **Convert** | Button | Starts the conversion process according to all settings configured below. |
| **Reset** | Button | Resets all conversion settings (format, speed, effects, filters, etc.) to their default values. |
| **Export** | Button | Saves (copies) the converted output file to the location selected by the user. |
| **Format (`Export Format`)** | Dropdown (`ComboBox`) | Determines the extension/format of the file produced after conversion (e.g. `.wav`, `.mp3`, `.mp4`, `.pdf`, `.jpg`). |
| **Change Frequency (`Frequency`)** | Dropdown (`ComboBox`) | Turns the audio sampling frequency conversion feature on (`On`) or off (`Off`). |
| **New Frequency Hz** | Text Input (`LineEdit`) | When frequency conversion is active, sets the target sampling frequency in Hz according to the entered value. |
| **Audio Speed (`Speed`)** | Dropdown (`ComboBox`) | Adjusts audio playback/conversion speed (`0.10x to 4.0x`). |
| **Pitch** | Dropdown (`ComboBox`) | Raises or lowers the pitch (`-6 Tones to +6 Tones`). |
| **Audio Effect** | Dropdown (`ComboBox`) | Selects a special effect to apply to the audio (`Normalize`, `Compress`, `Filter`, `Fade`, `Shift`, etc.). |
| **Select Cover Image** | Button | Opens a dialog to select the cover image to use when converting audio to video (audio+image -> video). |
| **Invert Video Colors** | Dropdown (`ComboBox`) | Inverts the colors of the video output (when `Yes` is selected). |
| **Video Grayscale** | Dropdown (`ComboBox`) | Converts the video output to black and white (grayscale) (when `Yes` is selected). |
| **Completely Remove Video Audio** | Dropdown (`ComboBox`) | Completely removes the original audio channels from the video file (when `Yes` is selected). |
| **Add External Audio (`Sync`)** | Button | Opens a dialog to select an external audio file to be added to the video as the main audio track. |
| **Invert PDF** | Dropdown (`ComboBox`) | Inverts the colors of PDF pages (when `Yes` is selected). |
| **PDF Grayscale** | Dropdown (`ComboBox`) | Converts PDF pages to black and white (grayscale). |
| **Invert Image** | Dropdown (`ComboBox`) | Inverts the colors of the image output (when `Yes` is selected). |
| **Image Grayscale** | Dropdown (`ComboBox`) | Converts the image output to black and white (grayscale). |
| **Image Resolution** | Dropdown (`ComboBox`) | Adjusts the scaling ratio of the image output (`-5 = 25% smaller, 0 = Original, +5 = 250% larger`). |
