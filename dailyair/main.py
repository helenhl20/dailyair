"""DailyAir CLI — Your AI Morning Briefing Agent"""

import click
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")


@click.group()
@click.version_option("1.0.0", prog_name="DailyAir")
def cli():
    """
    ☀️ DailyAir — Your AI Morning Briefing Agent

    Curates newsletters, Substacks, YouTube, and podcasts into a
    personalized briefing that Daisy reads to you every morning.
    """
    pass


@cli.command()
@click.option("--config", "-c", default="config.yaml", help="Path to config file.")
@click.option("--no-tts", is_flag=True, default=False, help="Skip text-to-speech playback.")
@click.option("--dry-run", is_flag=True, default=False, help="Fetch and summarize only — no output or TTS.")
@click.option("--output", "-o", type=click.Choice(["markdown", "email", "google_docs"]), multiple=True)
def run(config, no_tts, dry_run, output):
    """Run DailyAir now and generate today's briefing."""
    from .curator import Curator
    click.echo("☀️ Starting DailyAir...\n")
    try:
        curator = Curator(config_path=config)
        if output:
            curator.config.setdefault("output", {})["formats"] = list(output)
        result = curator.run(dry_run=dry_run, read_aloud=not no_tts)

        if result.get("briefing"):
            click.echo("\n" + "─" * 60)
            click.echo(result["briefing"])
            click.echo("─" * 60)

        if result.get("outputs"):
            click.echo("\n📄 Saved to:")
            for o in result["outputs"]:
                click.echo(f"  {o}")
    except FileNotFoundError as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n❌ Unexpected error: {e}", err=True)
        raise


@cli.command()
@click.option("--config", "-c", default="config.yaml", help="Path to config file.")
@click.option("--date", "-d", default=None, help="Date to replay (YYYY-MM-DD). Defaults to today.")
@click.option("--file", "-f", "filepath", default=None, help="Path to a specific briefing .md file.")
def replay(config, date, filepath):
    """Re-read a saved briefing aloud without hitting the internet or using any tokens."""
    import re
    from pathlib import Path
    from datetime import datetime
    from .config import load_config
    from .outputs import speak

    cfg = load_config(config)

    if filepath:
        md_path = Path(filepath).expanduser()
    else:
        date_str = date or datetime.now().strftime("%Y-%m-%d")
        output_dir = Path(cfg.get("output", {}).get("markdown", {}).get("path", "~/dailyair-briefings/")).expanduser()
        md_path = output_dir / f"briefing-{date_str}.md"

    if not md_path.exists():
        click.echo(f"❌ No briefing found at: {md_path}", err=True)
        click.echo("   Run 'dailyair run' first to generate one, or pass --date / --file.")
        raise SystemExit(1)

    raw = md_path.read_text(encoding="utf-8")

    # Extract just the briefing script (between "## Today's Briefing" and the next "---" or "##")
    match = re.search(r"## Today's Briefing\s*\n+(.*?)(?=\n---|\n## |\Z)", raw, re.DOTALL)
    if not match:
        click.echo("❌ Could not find a briefing script in that file.", err=True)
        raise SystemExit(1)

    briefing_script = match.group(1).strip()
    click.echo(f"▶️  Replaying briefing from {md_path.name} …\n")
    speak(briefing_script, cfg)


@cli.command()
@click.option("--config", "-c", default="config.yaml")
def schedule(config):
    """Set up DailyAir to run automatically every morning."""
    import platform
    cfg_path = Path(config).resolve()
    click.echo("⏰ Setting up daily schedule...\n")
    if platform.system() in ("Darwin", "Linux"):
        cron_line = f"30 6 * * * cd {cfg_path.parent} && {sys.executable} -m dailyair run --config {cfg_path}"
        click.echo("Add this line to your crontab (run 'crontab -e'):\n")
        click.echo(f"  {cron_line}\n")
        click.echo("Or run: bash scripts/setup_cron.sh")
    elif platform.system() == "Windows":
        click.echo(f"Use Task Scheduler with:\n  Program: {sys.executable}\n  Arguments: -m dailyair run --config {cfg_path}\n  Trigger: Daily at 6:30 AM")


@cli.command()
def init():
    """Create a starter config.yaml in the current directory."""
    import shutil
    dest = Path("config.yaml")
    if dest.exists():
        click.confirm("config.yaml already exists. Overwrite?", abort=True)
    src = Path(__file__).parent.parent / "config.example.yaml"
    if src.exists():
        shutil.copy(src, dest)
        click.echo("✅ Created config.yaml\n   Edit it to add your sources, API key, and preferences.")
    else:
        click.echo("❌ Could not find config.example.yaml. Please copy it manually.")


@cli.command()
@click.argument("name")
@click.option("--config", "-c", default="config.yaml")
@click.option("--type", "source_type", type=click.Choice(["person", "rss", "podcast", "youtube"]), default="person")
def add(name, config, source_type):
    """Add a new source to your config.yaml."""
    import yaml
    cfg_path = Path(config)
    if not cfg_path.exists():
        click.echo("Run 'dailyair init' first to create a config.yaml.")
        return
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)
    sources = cfg.setdefault("sources", {})
    if source_type == "person":
        sources.setdefault("people", []).append({"name": name, "handles": {}})
        click.echo(f"✅ Added person: {name}\n   Open config.yaml and fill in their handles.")
    elif source_type == "rss":
        sources.setdefault("rss_feeds", []).append(name)
        click.echo(f"✅ Added RSS feed: {name}")
    elif source_type == "youtube":
        sources.setdefault("youtube_channels", []).append(name)
        click.echo(f"✅ Added YouTube channel: {name}")
    elif source_type == "podcast":
        sources.setdefault("podcasts", []).append({"name": name, "rss": ""})
        click.echo(f"✅ Added podcast: {name}\n   Open config.yaml and add the RSS feed URL.")
    with open(cfg_path, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)


@cli.command()
@click.option("--config", "-c", default="config.yaml")
def test(config):
    """Test your config: check sources and API connectivity."""
    from .config import load_config
    from .llm import get_provider
    click.echo("🔍 Testing DailyAir configuration...\n")
    try:
        cfg = load_config(config)
        click.echo("✅ Config loaded successfully")
    except Exception as e:
        click.echo(f"❌ Config error: {e}")
        return
    try:
        llm = get_provider(cfg)
        response = llm.complete("You are a test assistant.", "Reply with just: 'DailyAir LLM connection OK'")
        click.echo(f"✅ LLM connection: {response.strip()}")
    except Exception as e:
        click.echo(f"❌ LLM error: {e}")
    sources = cfg.get("sources", {})
    click.echo(f"\n📋 Sources configured:")
    click.echo(f"  People/Writers:    {len(sources.get('people', []))}")
    click.echo(f"  RSS feeds:         {len(sources.get('rss_feeds', []))}")
    click.echo(f"  YouTube channels:  {len(sources.get('youtube_channels', []))}")
    click.echo(f"  Podcasts:          {len(sources.get('podcasts', []))}")
    click.echo(f"  Email newsletters: {len(sources.get('email_newsletters', []))}")
    click.echo(f"  Email enabled:     {cfg.get('email', {}).get('enabled', False)}")
    click.echo(f"\n✅ Run 'dailyair run' to generate your first briefing!")


def main():
    cli()


if __name__ == "__main__":
    main()
