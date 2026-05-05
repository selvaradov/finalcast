Important instructions:

- Never run install per-project pip packages unless you're in the right venv.
  - There's NO REASON to use --break-system-packages
  - You can generally assume the venv is already active
- Check whether you're in the venv if packages you expect to be available are not.
- Prefer to create temporary Python files and run those for debugging, rather than Bash commands directly executing
  Python scripts inline in the terminal.