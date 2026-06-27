# spfbot

每日下午自動至永豐期貨官網，拉取當日台股籌碼快報，並傳送至Discord 。

## Setup

```bash
pip install -r requirements.txt
python spfbot/main.py
```

## GitHub Actions

The workflow in [.github/workflows/run-spfbot.yml](.github/workflows/run-spfbot.yml) runs the bot on a schedule and can also be triggered manually.
