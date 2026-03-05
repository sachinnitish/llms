# llms.txt Generator

A single-page structural link extractor and `llms.txt` generator designed for modern AI indexing.

## 🚀 Quick Start

The project includes convenience scripts for automated setup and execution.

### Windows
1. **Setup**: Edit properties and tick the unblock option on `.\windows\setup.bat`, then double click to create a virtual environment and install dependencies.
2. **Run**: Edit properties and tick the unblock option on `.\windows\run.bat` then double click to launch the application.
3. **Reset**: Edit properties and tick the unblock option on `.\windows\teardown.bat` then double click if you need to clear the environment and cache.

### Unix / macOS
1. **Open Terminal** in the project directory.
2. **Setup**: Run `chmod +x ./unix-macos/*.sh` then `source ./unix-macos/setup.sh` to install dependencies.
3. **Run**: Run `./unix-macos/run.sh` to launch the application.
4. **Reset**: Run `./unix-macos/teardown.sh` to clear the environment and cache.

---

## 🛠️ How to Use

### Step 1: Configuration
- Enter your **Website Name**, **Project Purpose**, and **Category** in the sidebar. These will be used to generate the header metadata for your `llms.txt`.

### Step 2: Extraction
- Enter the **Root Domain** (e.g., `https://www.example.com`).
- Click **Start Extraction**. The tool will crawl the page structure, including:
    - Headers & Footers
    - Dropdown Menus
    - Main Content Body (Articles, Sections)
- All URLs are automatically cleaned of tracking parameters while preserving important section fragments (`#`).

### Step 3: AI Synthesis
- A **Master AI Prompt** is generated containing a JSON map of your site structure.
- Copy the prompt and paste it into your preferred LLM (Gemini, Claude, GPT-4).
- The prompt is strictly tuned to return **raw Markdown** without conversational filler.

### Step 4: Export
- Paste the AI's response back into the **AI Result** box.
- Click **Generate Final llms.txt** to preview and download your standard-compliant file.

---

## 🎨 UI Features
- **Zinc-Dark Theme**: A sleek, high-contrast dark mode aesthetic.
- **Inter Typography**: Clean, modern font across the entire app.
- **Collapsible Navigation Map**: View hundreds of discovered links in a stable, scrollable container.
- **Image-Based Icons**: High-fidelity icons sourced from SVGRepo.
