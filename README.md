# ☀️ DailyAir — Your AI Morning Briefing Agent

> *"Every morning, Daisy reads the internet so you don't have to."*

DailyAir is an open-source, self-hosted AI agent that:

1. **Fetches** content from your favorite newsletters, Substacks, writers, YouTube channels, and podcasts
2. **Summarizes** everything using an LLM of your choice (OpenAI, Claude, Ollama, Groq — bring your own key)
3. **Has Daisy read it to you** while you brush your teeth and get ready for the day

No subscriptions. No lock-in. Runs locally on your machine or a VM. Yours forever.

---

## Demo

```
$ dailyair run

☀️ Starting DailyAir...

[06:30] Fetching 12 sources...
  [Andrej Karpathy] 1 item
  [Ben Thompson] 2 items
  [Email] 7 newsletters
  [YouTube] 3 videos

[06:31] Summarizing 13 items...
[06:32] Generating briefing script...
[06:32] Daisy is reading your briefing...

─────────────────────────────────────────────────────────
Good morning! Here's your DailyAir briefing for today.

Andrej Karpathy dropped a fascinating post this morning about
the future of software as a new kind of living organism...

Ben Thompson at Stratechery is calling OpenAI's latest move
the most important pivot in AI history...

Your newsletters are buzzing — TLDR AI has a roundup of
seven new model releases this week alone...
─────────────────────────────────────────────────────────

📄 Saved to: ~/dailyair-briefings/briefing-2026-04-01.md
```

---

## Features

- **Bring any source** — add anyone by name, handle, or RSS URL
- **Provider-agnostic LLM** — OpenAI, Claude, Gemini, Groq, or run Llama3 locally with Ollama (free)
- **Daisy reads it aloud** — Microsoft Edge TTS (free), OpenAI, ElevenLabs, or offline system voice
- **Multiple output formats** — Markdown file, email digest, or Google Doc
- **Daily scheduling** — set it and forget it with cron or Windows Task Scheduler
- **Privacy-first** — runs entirely on your machine; your data never leaves your environment
- **One config file** — `config.yaml` controls everything

---

## Supported Sources

| Type | How it works |
|------|--------------|
| **Substack** | Auto-discovers RSS feed from publication URL |
| **Personal blogs** | Auto-discovers RSS; falls back to web scraping |
| **Email newsletters** | Connects to a dedicated inbox via IMAP |
| **RSS/Atom feeds** | Direct feed URL support |
| **YouTube channels** | Fetches recent videos + auto-transcripts |
| **Podcasts** | RSS feed + episode descriptions |

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/yourusername/dailyair.git
cd dailyair
pip install -e .
```

### 2. Initialize your config

```bash
dailyair init
```

Opens `config.yaml`. Fill in your LLM API key and add your sources.

### 3. (Optional) Set up email newsletters

Create a **dedicated email address** just for newsletters — keep it separate from your personal inbox. Subscribe to your newsletters there, then enable it in `config.yaml`:

```yaml
email:
  enabled: true
  imap_server: imap.gmail.com
  username: your-newsletter-email@gmail.com
  password: YOUR_APP_PASSWORD
```

For Gmail: enable IMAP in Settings, then generate an App Password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

### 4. Test your setup

```bash
dailyair test
```

### 5. Run your first briefing

```bash
dailyair run --no-tts   # read in terminal first
dailyair run            # let Daisy read it to you
```

### 6. Schedule daily runs

```bash
bash scripts/setup_cron.sh   # Mac/Linux
dailyair schedule            # shows instructions for your OS
```

---

## Configuration

### Adding sources

```yaml
sources:
  people:
    - name: Andrej Karpathy
      handles:
        substack: karpathy.substack.com
        youtube: "@AndrejKarpathy"

    - name: Ben Thompson
      handles:
        substack: stratechery.com

  email_newsletters:
    - The Rundown AI
    - TLDR AI

  rss_feeds:
    - https://techcrunch.com/category/artificial-intelligence/feed/

  youtube_channels:
    - "@TwoMinutePapers"

  podcasts:
    - name: Lex Fridman Podcast
      rss: https://lexfridman.com/feed/podcast/
```

### Quick-add from CLI

```bash
dailyair add "Lenny Rachitsky" --type person
dailyair add "https://simonwillison.net/atom/everything/" --type rss
dailyair add "@lexfridman" --type youtube
```

### Choosing your LLM

```yaml
llm:
  provider: openai        # openai | anthropic | ollama | gemini
  model: gpt-4o-mini
  api_key: YOUR_KEY
```

**Run free and offline with Ollama:**
```yaml
llm:
  provider: ollama
  model: llama3
  base_url: http://localhost:11434
```
Install at [ollama.com](https://ollama.com), then `ollama pull llama3`.

### Daisy's Voice

```yaml
tts:
  provider: edge            # edge (free) | openai | elevenlabs | system
  voice: en-US-GuyNeural
  speed: 1.15
```

Free Edge TTS voice options:
- `en-US-GuyNeural` — American male
- `en-US-JennyNeural` — American female
- `en-GB-RyanNeural` — British male
- `en-AU-NatashaNeural` — Australian female

---

## Output Options

**Markdown** (default) — saves a daily `.md` file, great for Obsidian or archiving.

**Email digest** — sends a formatted HTML email to yourself each morning.

**Google Docs** — creates a new Doc per briefing in a Drive folder.
```bash
pip install "dailyair[google]"
```

---

## Running on a VM (Fully Automated, No Mac Required)

The ideal setup: a cheap cloud VM runs DailyAir every morning, generates your briefing, and sends the MP3 straight to your Telegram. Your phone gets a notification, you tap play, done — no computer needed.

### 1. Provision a VM

Any small instance works. Recommended options:

| Provider | Size | Cost | Notes |
|---|---|---|---|
| DigitalOcean | Basic Droplet (1 GB) | ~$6/mo | Easiest for beginners |
| Hetzner | CX11 | ~$4/mo | Cheapest in Europe |
| AWS | t3.micro | ~$8/mo | Free tier eligible |

Create a Ubuntu 22.04 LTS instance and SSH in:

```bash
ssh root@YOUR_DROPLET_IP
```

### 2. Install system dependencies

```bash
apt update && apt install -y python3.12 python3.12-venv python3-pip git
```

### 3. Clone and install DailyAir

```bash
git clone https://github.com/yourusername/dailyair.git
cd dailyair
python3.12 -m venv venv
source venv/bin/activate
pip install -e .
pip install edge-tts   # free TTS, works headlessly — just generates the MP3
```

### 4. Create your config

```bash
dailyair init        # creates config.yaml from the example
nano config.yaml     # fill in your LLM key, sources, and Telegram credentials
```

For a VM, your `output.formats` should include `telegram`. The browser player is automatically skipped on headless servers since there's no display — the MP3 goes straight to your phone instead.

```yaml
output:
  formats:
    - markdown    # saves a local archive of each briefing
    - telegram    # sends text + MP3 to your phone every morning

telegram:
  bot_token: YOUR_BOT_TOKEN
  chat_id: YOUR_CHAT_ID
  send_text: true
  send_audio: true

tts:
  enabled: true
  provider: edge   # free, no API key, works perfectly on a VM
  speed: 1.15
```

**Getting your Telegram bot token and chat ID** (takes ~2 minutes):

1. Open Telegram → search **@BotFather** → send `/newbot` → follow the prompts
2. Copy the token it gives you (looks like `7123456789:AAFxxx...`)
3. Search for your new bot in Telegram and press **Start**
4. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser
5. Send any message to your bot, refresh the page — copy the numeric `id` inside `"chat"`. That's your `chat_id`.

### 5. Test it end-to-end

```bash
source venv/bin/activate
dailyair test        # verifies LLM connection and source config
dailyair run         # generates a full briefing and sends it to Telegram
```

Check your Telegram — you should receive the briefing text followed by the MP3 audio file.

### 6. Automate with systemd (recommended)

systemd is more robust than cron: it restarts on failure, logs to journald, and handles boot timing correctly.

Create the service file:

```bash
nano /etc/systemd/system/dailyair.service
```

```ini
[Unit]
Description=DailyAir Morning Briefing
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=root
WorkingDirectory=/root/dailyair
EnvironmentFile=/root/dailyair/.env
ExecStart=/root/dailyair/venv/bin/dailyair run
StandardOutput=journal
StandardError=journal
```

Create the timer (runs at 6:30 AM every day):

```bash
nano /etc/systemd/system/dailyair.timer
```

```ini
[Unit]
Description=Run DailyAir every morning at 6:30 AM

[Timer]
OnCalendar=*-*-* 06:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable --now dailyair.timer
systemctl list-timers dailyair.timer   # confirm next run time
```

Check logs at any time:

```bash
journalctl -u dailyair.service -f
```

### 7. Store secrets safely

Never put API keys directly in `config.yaml` if the repo is public. Use an `.env` file instead (already in `.gitignore`):

```bash
# /root/dailyair/.env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

Then reference them in `config.yaml`:

```yaml
llm:
  api_key:   # leave blank — DailyAir reads ANTHROPIC_API_KEY / OPENAI_API_KEY automatically
```

### 8. Quick-fix: if the timer fires but nothing arrives on Telegram

```bash
# Run manually and watch the output
journalctl -u dailyair.service --since "10 minutes ago"

# Or run directly
cd /root/dailyair && source venv/bin/activate && dailyair run
```

Common causes: VM timezone differs from your local time (adjust `OnCalendar` in the timer), network not ready at boot (the `After=network-online.target` line handles this), or a missing API key in `.env`.

---

## Privacy & Security

- Your data stays on your machine — DailyAir doesn't phone home
- Use a dedicated email for newsletters, not your personal inbox
- Store API keys in `.env` (never commit this file — it's in `.gitignore`)

---

## Roadmap

- [ ] Web UI dashboard
- [ ] Smart deduplication across sources
- [ ] Topic filtering
- [ ] Twitter/X integration
- [ ] Spotify podcast integration
- [ ] Mobile companion app
- [ ] Slack/Discord delivery

---

## Contributing

PRs welcome! Open an issue first for major changes.

---

## License

MIT

---

*Built by someone who wanted their AI agent to actually read the internet for them every morning. Daisy does the reading. You do the living.*
