"""
Text-to-Speech output — reads the morning briefing aloud via Daisy's voice,
with a browser-based player for playback control and live text tracking.

Providers:
  edge      — Microsoft Edge TTS (free, no API key needed, recommended)
  openai    — OpenAI TTS API
  elevenlabs — ElevenLabs (most natural-sounding)
  system    — pyttsx3 (fully offline, no player UI)
"""

import asyncio
import json
import logging
import os
import re
import tempfile
import webbrowser
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_SPEEDS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _audio_output_path(config: dict) -> Path:
    """Return the canonical path for today's MP3 file."""
    output_dir = Path(
        config.get("output", {}).get("markdown", {}).get("path", "~/dailyair-briefings/")
    ).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"briefing-{datetime.now().strftime('%Y-%m-%d')}.mp3"


def generate_audio(text: str, config: dict) -> Path | None:
    """
    Generate the MP3 and save it to the briefings folder.
    Returns the Path on success, or None if the provider is system TTS
    (which doesn't produce a file) or TTS is disabled.
    """
    tts_cfg = config.get("tts", {})
    if not tts_cfg.get("enabled", True):
        return None

    provider = tts_cfg.get("provider", "edge").lower()
    speed    = float(tts_cfg.get("speed", 1.0))

    if provider == "system":
        return None  # pyttsx3 speaks directly; no file produced

    audio_path = _audio_output_path(config)

    if provider == "edge":
        _generate_edge(text, tts_cfg, speed, audio_path)
    elif provider == "openai":
        _generate_openai(text, tts_cfg, speed, audio_path)
    elif provider == "elevenlabs":
        _generate_elevenlabs(text, tts_cfg, audio_path)
    else:
        logger.warning(f"Unknown TTS provider '{provider}' — no audio generated.")
        return None

    return audio_path


def play_audio(text: str, audio_path: Path, config: dict) -> None:
    """Open the browser player for an already-generated audio file."""
    speed = float(config.get("tts", {}).get("speed", 1.0))
    _show_player(text, audio_path, speed)


def speak(text: str, config: dict) -> None:
    """
    Generate audio and open the browser player.
    For system TTS, speaks directly without a player UI.
    Kept for backward compatibility; curator now calls generate_audio / play_audio
    separately so Telegram can reuse the file.
    """
    tts_cfg  = config.get("tts", {})
    provider = tts_cfg.get("provider", "edge").lower()
    speed    = float(tts_cfg.get("speed", 1.0))

    if provider == "system":
        _speak_system(text, speed)
        return

    audio_path = generate_audio(text, config)
    if audio_path:
        _show_player(text, audio_path, speed)


# ---------------------------------------------------------------------------
# Provider generators  (write MP3 to audio_path, then return)
# ---------------------------------------------------------------------------

def _make_edge_rate(speed: float) -> str:
    pct = int((speed - 1) * 100)
    return f"+{pct}%" if pct >= 0 else f"{pct}%"


def _generate_edge(text: str, tts_cfg: dict, speed: float, audio_path: Path) -> None:
    try:
        import edge_tts
    except ImportError:
        raise ImportError("Install edge-tts: pip install edge-tts")

    voice = tts_cfg.get("voice", "en-US-GuyNeural")
    rate  = _make_edge_rate(speed)

    async def _run() -> None:
        await edge_tts.Communicate(text, voice, rate=rate).save(str(audio_path))

    asyncio.run(_run())


def _generate_openai(text: str, tts_cfg: dict, speed: float, audio_path: Path) -> None:
    from openai import OpenAI
    client = OpenAI(api_key=tts_cfg.get("api_key") or os.environ.get("OPENAI_API_KEY", ""))
    client.audio.speech.create(
        model="tts-1",
        voice=tts_cfg.get("voice", "alloy"),
        input=text,
        speed=max(0.25, min(4.0, speed)),
    ).stream_to_file(str(audio_path))


def _generate_elevenlabs(text: str, tts_cfg: dict, audio_path: Path) -> None:
    from elevenlabs import ElevenLabs
    client = ElevenLabs(api_key=tts_cfg.get("api_key") or os.environ.get("ELEVENLABS_API_KEY", ""))
    audio_bytes = b"".join(
        client.text_to_speech.convert(
            text=text,
            voice_id=tts_cfg.get("voice", "Rachel"),
            model_id="eleven_turbo_v2",
        )
    )
    audio_path.write_bytes(audio_bytes)


def _speak_system(text: str, speed: float) -> None:
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty("rate", int(engine.getProperty("rate") * speed))
    engine.say(text)
    engine.runAndWait()


# ---------------------------------------------------------------------------
# Browser player
# ---------------------------------------------------------------------------

def _show_player(text: str, audio_path: Path, initial_speed: float = 1.0) -> None:
    """Generate an HTML player and open it in the default browser."""
    audio_uri = audio_path.as_uri()
    html      = _build_html(text, audio_uri, initial_speed)

    # Write to a temp HTML file (lives in /tmp — cleaned up by OS)
    with tempfile.NamedTemporaryFile(
        suffix=".html", delete=False, mode="w", encoding="utf-8"
    ) as f:
        f.write(html)
        html_path = f.name

    logger.info(f"Opening player in browser: {html_path}")
    webbrowser.open(f"file://{html_path}")


def _build_html(text: str, audio_uri: str, initial_speed: float) -> str:
    # Split into sentences for live highlighting
    sentences    = re.split(r"(?<=[.!?])\s+", text.strip())
    sents_json   = json.dumps(sentences, ensure_ascii=False)

    # Snap initial speed to nearest button value for the active highlight
    closest_spd  = min(_SPEEDS, key=lambda s: abs(s - initial_speed))

    speed_buttons = "\n    ".join(
        f'<button class="spd{"" if abs(s - closest_spd) > 0.01 else " active"}" '
        f'id="spd-{s}" onclick="setSpeed({s})">{s}x</button>'
        for s in _SPEEDS
    )

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>☀️ DailyAir Player</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, sans-serif;
    background: #0f0f1a;
    color: #e8e8e8;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}

  /* ── Header ── */
  header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 24px;
    flex-shrink: 0;
  }}
  .title {{ font-size: 16px; font-weight: 700; color: #f0a030; }}
  #timeDisplay {{
    font-family: "Courier New", monospace;
    font-size: 13px;
    color: #666;
  }}

  /* ── Text panel ── */
  #textPanel {{
    flex: 1;
    overflow-y: auto;
    margin: 0 20px;
    padding: 18px 22px;
    background: #1c1c30;
    border-radius: 8px;
    font-size: 15px;
    line-height: 1.8;
    scroll-behavior: smooth;
  }}
  .sentence {{
    border-radius: 3px;
    padding: 1px 3px;
    margin: -1px -3px;
    transition: background 0.25s, color 0.25s;
  }}
  .sentence.active {{
    background: #2b1d00;
    color: #f0a030;
  }}

  /* ── Progress bar ── */
  .progress-wrap {{ padding: 10px 24px 2px; flex-shrink: 0; }}
  input[type=range] {{
    width: 100%;
    height: 4px;
    border-radius: 2px;
    background: #2a2a45;
    outline: none;
    cursor: pointer;
    -webkit-appearance: none;
    appearance: none;
  }}
  input[type=range]::-webkit-slider-thumb {{
    -webkit-appearance: none;
    width: 14px; height: 14px;
    border-radius: 50%;
    background: #f0a030;
    cursor: pointer;
    box-shadow: 0 0 4px rgba(240,160,48,0.5);
  }}
  input[type=range]::-moz-range-thumb {{
    width: 14px; height: 14px;
    border-radius: 50%;
    background: #f0a030;
    cursor: pointer;
    border: none;
  }}

  /* ── Transport controls ── */
  .controls {{
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 10px;
    padding: 8px 24px;
    flex-shrink: 0;
  }}
  .btn {{
    background: #1c1c30;
    color: #e8e8e8;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-size: 14px;
    cursor: pointer;
    transition: background 0.15s;
  }}
  .btn:hover {{ background: #2a2a45; }}
  #playBtn {{
    background: #f0a030;
    color: #111;
    font-size: 16px;
    font-weight: 700;
    padding: 10px 26px;
    border-radius: 6px;
  }}
  #playBtn:hover {{ background: #d48c20; }}

  /* ── Speed row ── */
  .speed-row {{
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 6px;
    padding: 4px 24px 16px;
    flex-shrink: 0;
  }}
  .speed-label {{ color: #666; font-size: 13px; margin-right: 4px; }}
  .spd {{
    background: #1c1c30;
    color: #e8e8e8;
    border: none;
    border-radius: 5px;
    padding: 5px 11px;
    font-size: 12px;
    cursor: pointer;
    transition: background 0.15s;
  }}
  .spd:hover {{ background: #2a2a45; }}
  .spd.active {{ background: #f0a030; color: #111; font-weight: 700; }}
</style>
</head>
<body>

<header>
  <span class="title">☀️&nbsp; DailyAir Player</span>
  <span id="timeDisplay">0:00 / --:--</span>
</header>

<div id="textPanel"></div>

<div class="progress-wrap">
  <input type="range" id="progress" min="0" max="1000" value="0">
</div>

<div class="controls">
  <button class="btn" onclick="seek(-10)">⏪&nbsp; −10s</button>
  <button id="playBtn" onclick="togglePlay()">⏸</button>
  <button class="btn" onclick="seek(10)">+10s &nbsp;⏩</button>
</div>

<div class="speed-row">
  <span class="speed-label">Speed:</span>
  {speed_buttons}
</div>

<!-- Hidden audio element -->
<audio id="audio" src="{audio_uri}" preload="auto"></audio>

<script>
(function () {{
  const audio       = document.getElementById('audio');
  const progressEl  = document.getElementById('progress');
  const playBtn     = document.getElementById('playBtn');
  const timeDisplay = document.getElementById('timeDisplay');
  const textPanel   = document.getElementById('textPanel');

  /* ── Build sentence spans ── */
  const sentences = {sents_json};
  let html = '';
  sentences.forEach((s, i) => {{
    const safe = s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    html += `<span class="sentence" id="s${{i}}">${{safe}}</span> `;
  }});
  textPanel.innerHTML = html;

  let currentIdx = -1;

  /* ── Pre-compute where each sentence starts as a fraction [0,1) of total chars.
     Longer sentences get a proportionally larger slice of the timeline, so
     highlighting stays accurate regardless of playback speed.                    */
  const sentLens   = sentences.map(s => s.length + 1); // +1 for trailing space
  const totalChars = sentLens.reduce((a, b) => a + b, 0);
  const sentStarts = [];
  let cumChars = 0;
  for (const len of sentLens) {{
    sentStarts.push(cumChars / totalChars);
    cumChars += len;
  }}

  function sentIdxAt(ratio) {{
    let lo = 0, hi = sentStarts.length - 1;
    while (lo < hi) {{
      const mid = (lo + hi + 1) >> 1;
      if (sentStarts[mid] <= ratio) lo = mid; else hi = mid - 1;
    }}
    return lo;
  }}

  function fmt(sec) {{
    sec = Math.max(0, Math.floor(sec || 0));
    return `${{Math.floor(sec / 60)}}:${{String(sec % 60).padStart(2, '0')}}`;
  }}

  /* ── Sync UI to audio position ── */
  audio.addEventListener('timeupdate', () => {{
    if (!audio.duration) return;
    const ratio = audio.currentTime / audio.duration;

    // Progress bar
    progressEl.value = ratio * 1000;

    // Time label
    timeDisplay.textContent = `${{fmt(audio.currentTime)}} / ${{fmt(audio.duration)}}`;

    // Sentence highlight (char-weighted — correct at any playback speed)
    const idx = sentIdxAt(ratio);
    if (idx !== currentIdx) {{
      if (currentIdx >= 0) document.getElementById(`s${{currentIdx}}`).classList.remove('active');
      const el = document.getElementById(`s${{idx}}`);
      el.classList.add('active');
      el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
      currentIdx = idx;
    }}
  }});

  audio.addEventListener('ended', () => {{ playBtn.textContent = '▶'; }});

  /* ── Progress bar scrubbing ── */
  progressEl.addEventListener('input', () => {{
    if (audio.duration) audio.currentTime = (progressEl.value / 1000) * audio.duration;
  }});

  /* ── Controls ── */
  window.togglePlay = function () {{
    if (audio.paused) {{ audio.play(); playBtn.textContent = '⏸'; }}
    else              {{ audio.pause(); playBtn.textContent = '▶'; }}
  }};

  window.seek = function (delta) {{
    audio.currentTime = Math.max(0, Math.min(audio.duration || 0, audio.currentTime + delta));
  }};

  window.setSpeed = function (spd) {{
    audio.playbackRate = spd;
    document.querySelectorAll('.spd').forEach(b => b.classList.remove('active'));
    document.getElementById(`spd-${{spd}}`).classList.add('active');
  }};

  /* ── Set initial speed and start playback ── */
  audio.addEventListener('canplay', () => {{
    audio.playbackRate = {initial_speed};
    audio.play().catch(() => {{
      // Autoplay blocked — user can click play
      playBtn.textContent = '▶';
    }});
  }}, {{ once: true }});

}})();
</script>
</body>
</html>
"""
