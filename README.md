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
   - Now you can run things normally via VSCode (F5/ Ctrl F5/ Run tests) without even a python installation on your PC

4. Run the project from VSCode
   - Press F5 to run the Server + Client in separate terminal windows automatically
   - If the above does not work, go to Run and debug and select "Smart House: Server + Client" and click Start.

5. Run the project from the terminal.

   - Run the server:
     ```bash
     uv run server
     ```

  - Run the client:
     ```bash
     uv run client
     ```

   - Run tests:
     ```bash
     uv run pytest
     ```

References:
1) https://dev.to/lifeportal20002010/mastering-uv-in-vs-code-the-ultra-fast-python-setup-guide-2n56
2) https://pydevtools.com/handbook/how-to/how-to-configure-vs-code-for-a-uv-project/

3) https://www.youtube.com/watch?v=AMdG7IjgSPM&t=398s