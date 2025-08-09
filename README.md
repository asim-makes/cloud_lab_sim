# Cloud Lab Simulation - Daily Data Downloader

This is my first foundational cloud project, marking the start of my **cloud engineering journey ☁️**.  

---

## Features
- Scheduled execution using `cron`
- Logging to stdout (cloud-friendly logging)
- Python script to download daily data

---

## Local Setup
1. Clone the repository:
    ```bash
    git clone https://github.com/asim-makes/cloud_lab_sim.git
    cd cloud_lab_sim
    ```


2. Create a virtual environment
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```


3. Run the script manually
    ```python
    python download_todays_data.py
    ```

## **Note**
Locally, I can simulate cloud logging with cron:
```bash
* * * * * /home/ubuntu/cloud_lab_sim/.venv/bin/python /home/ubuntu/cloud_lab_sim/download_todays_data.py >> /home/ubuntu/cloud_lab_sim/cron.log 2>&1
```
This will run the script every minute and log output to cron.log. To change the time, I can change * value to run it when I want.

Logging
Cloud style: Logs are written to stdout and stderr using Python's logging module.
Local simulation: Redirect cron output to a file to preserve logs.


---

## **Why this matters for my cloud journey**
Pushing this to GitHub is less about showing off a “complex” project and more about:
- **Documenting the start** of my journey.
- Showing that I understand **cloud logging patterns**.

---
