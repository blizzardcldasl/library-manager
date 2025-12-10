# Library Manager

**AI-powered audiobook/ebook library metadata fixer** - Automatically detects and fixes incorrectly named book folders using LLM intelligence.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-2.0+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

## The Problem

Audiobook and ebook libraries often end up with messy folder names from various sources:

```
Before:
├── Shards of Earth/Adrian Tchaikovsky/        # Author/Title swapped!
├── Christopher Golden, Amber Benson/Slayers/  # Wrong author format
├── The Expanse 2019/Leviathan Wakes/          # Year in wrong place
├── Tchaikovsky, Adrian/Service Model/         # LastName, FirstName format
└── [bitsearch.to] Dean Koontz - Watchers/     # Junk in filename
```

Manually fixing hundreds of these is tedious. Library Manager uses AI to parse messy filenames and automatically reorganize your library.

## The Solution

Library Manager scans your library, identifies problematic folder structures, and uses AI (via OpenRouter or Google Gemini) to intelligently parse and fix them:

```
After:
├── Adrian Tchaikovsky/Shards of Earth/        # ✓ Correct!
├── Christopher Golden/Slayers/                # ✓ Fixed
├── James S.A. Corey/Leviathan Wakes/          # ✓ Proper author
├── Adrian Tchaikovsky/Service Model/          # ✓ Name normalized
└── Dean Koontz/Watchers/                      # ✓ Cleaned up
```

## Features

- **Web Dashboard** - Beautiful dark-themed UI to monitor and control everything
- **Smart Detection** - Automatically flags suspicious folder names (years in author, swapped fields, etc.)
- **AI-Powered Parsing** - Uses LLMs to intelligently extract author/title from messy filenames
- **Batch Processing** - Process multiple books at once with rate limiting
- **Series Preservation** - Keeps "Book 1", "Book 2" etc. in titles
- **Co-Author Support** - Properly handles multiple authors
- **History Tracking** - See every fix made with before/after comparison
- **Auto or Manual Mode** - Let it run automatically or approve each fix
- **Background Worker** - Periodic scanning on configurable schedule

## Screenshots

The dashboard shows your library stats, recent fixes, and quick actions:

| Dashboard | Queue | History |
|-----------|-------|---------|
| Total books, queue size, fixes | Books flagged for review | All fixes with before/after |

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/library-manager.git
cd library-manager
pip install -r requirements.txt
```

### 2. Configure

```bash
# Copy example configs
cp config.example.json config.json
cp secrets.example.json secrets.json

# Edit with your settings
nano config.json    # Set your library path
nano secrets.json   # Add your API key
```

**config.json:**
```json
{
  "library_paths": ["/path/to/your/audiobooks"],
  "openrouter_model": "google/gemma-3n-e4b-it:free",
  "scan_interval_hours": 6,
  "batch_size": 3,
  "auto_fix": false,
  "enabled": true
}
```

**secrets.json:**
```json
{
  "openrouter_api_key": "sk-or-v1-your-key-here"
}
```

### 3. Run

```bash
python app.py
```

Open http://localhost:5060 in your browser.

## AI Providers

Library Manager supports multiple AI providers:

### OpenRouter (Recommended)
- Get a free API key at [openrouter.ai](https://openrouter.ai)
- Uses `google/gemma-3n-e4b-it:free` by default (completely free!)
- Can also use Claude, GPT-4, etc. for better accuracy

### Google Gemini
- Get an API key from [Google AI Studio](https://aistudio.google.com)
- Add `gemini_api_key` to your secrets.json

## Library Structure

Library Manager expects your library to follow this structure:

```
/your/library/path/
├── Author Name/
│   ├── Book Title/
│   │   └── audiobook.m4b
│   └── Another Book/
│       └── audiobook.mp3
└── Another Author/
    └── Their Book/
        └── book.m4b
```

This is the standard structure used by:
- Audiobookshelf
- Plex Audiobooks
- Most audiobook managers

## How It Works

1. **Scan** - Walks through your library finding all Author/Title folders
2. **Detect** - Flags folders that look wrong (year in author, swapped fields, etc.)
3. **Queue** - Adds suspicious books to a processing queue
4. **Parse** - Sends batches to AI for intelligent parsing
5. **Fix** - Renames folders to correct structure (if auto_fix enabled)
6. **Track** - Records all changes in history for review

### Detection Rules

Books are flagged if they have:
- Years (1950-2030) in the author name
- Common title words ("The", "of", "and") in author
- Title that looks like a person's name (swapped fields)
- Comma in author name (LastName, FirstName format)
- Format indicators in author (epub, mp3, [brackets])

## Production Deployment

### Systemd Service

```bash
sudo tee /etc/systemd/system/library-manager.service << EOF
[Unit]
Description=Library Manager
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/library-manager
ExecStart=/usr/bin/python3 app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable --now library-manager
```

### Nginx Reverse Proxy (with SSL)

```nginx
server {
    listen 443 ssl http2;
    server_name library.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/library.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/library.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5060;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/scan` | POST | Trigger library scan |
| `/api/process` | POST | Process queue (supports `{all: true}` or `{limit: N}`) |
| `/api/queue` | GET | Get current queue items |
| `/api/stats` | GET | Get dashboard statistics |
| `/api/worker/start` | POST | Start background worker |
| `/api/worker/stop` | POST | Stop background worker |

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `library_paths` | `[]` | List of library root paths to scan |
| `openrouter_model` | `google/gemma-3n-e4b-it:free` | AI model to use |
| `scan_interval_hours` | `6` | How often to auto-scan |
| `batch_size` | `3` | Books per AI request |
| `max_requests_per_hour` | `30` | Rate limiting |
| `auto_fix` | `false` | Automatically apply fixes |
| `enabled` | `true` | Enable background processing |

## Contributing

Pull requests welcome! Some ideas:
- Support for more AI providers (Ollama, local LLMs)
- Undo/revert functionality
- Dry-run mode with preview
- Integration with Audiobookshelf API
- Support for different library structures

## License

MIT License - do whatever you want with it.

---

Built with Claude Code
