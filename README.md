# IDATA2304 Smart House Project

## Initial setup

1. Install UV.

   - Windows (PowerShell):
     ```powershell
     irm https://astral.sh/uv/install.ps1 | iex
     ```

   - macOS:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```

2. After pulling the latest changes, run this in the project root:

   ```bash
   uv sync
   ```

3. Set up VS Code to use the Python virtual environment.

   - Open the Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P`).
   - Select "Python: Select Interpreter".
   - Choose the Python version inside `.venv`.

4. And you can also run the project from the terminal.

   - Run the app:
     ```bash
     uv run idata2304-smart-house-project
     ```

   - Run tests:
     ```bash
     uv run pytest
     ```