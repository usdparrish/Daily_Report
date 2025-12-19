@echo off
REM Activate the virtual environment
call C:\Path\To\Your\venv\Scripts\activate.bat

REM Run the radiology report CLI command
python -m radiology_reports.cli.manager_pdf --combined --email --cleanup

REM Optional: Deactivate the environment (not required for one-time execution)
deactivate