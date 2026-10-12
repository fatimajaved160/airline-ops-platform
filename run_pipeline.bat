@echo off
cd /d D:\airline-ops-platform\airline-ops-platform
call D:\airline-ops-platform\.venv\Scripts\activate.bat
python -m pipeline.run_pipeline --year 2024 --months 1