# spfbot

This repository contains a Python bot that scrapes the SPF research report page, downloads the latest PDF, splits it into two images, and sends them to Discord.

## Setup

```bash
pip install -r requirements.txt
python spfbot/main.py
```

## GitHub Actions

The workflow in [.github/workflows/run-spfbot.yml](.github/workflows/run-spfbot.yml) runs the bot on a schedule and can also be triggered manually.
