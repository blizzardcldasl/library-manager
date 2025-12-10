#!/usr/bin/env python3
"""
Library Metadata Manager - Web UI
Automatically fixes book metadata using AI.

Features:
- Web dashboard with stats
- Queue of books needing fixes
- History of all fixes made
- Settings management
- Multi-provider AI (Gemini, OpenRouter, Ollama)
"""

import os
import sys
import json
import time
import sqlite3
import threading
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/deucebucket/library-manager/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'library-manager-secret-key-2024'

# ============== CONFIGURATION ==============

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / 'library.db'
CONFIG_PATH = BASE_DIR / 'config.json'
SECRETS_PATH = BASE_DIR / 'secrets.json'

DEFAULT_CONFIG = {
    "library_paths": [
        "/mnt/rag_data/audiobooks"
    ],
    "openrouter_model": "google/gemma-3n-e4b-it:free",
    "scan_interval_hours": 6,
    "batch_size": 3,
    "max_requests_per_hour": 30,
    "auto_fix": False,
    "enabled": True
}

# ============== DATABASE ==============

def init_db():
    """Initialize SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Books table - tracks all scanned books
    c.execute('''CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY,
        path TEXT UNIQUE,
        current_author TEXT,
        current_title TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Queue table - books needing AI analysis
    c.execute('''CREATE TABLE IF NOT EXISTS queue (
        id INTEGER PRIMARY KEY,
        book_id INTEGER,
        priority INTEGER DEFAULT 5,
        reason TEXT,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (book_id) REFERENCES books(id)
    )''')

    # History table - all fixes made
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY,
        book_id INTEGER,
        old_author TEXT,
        old_title TEXT,
        new_author TEXT,
        new_title TEXT,
        old_path TEXT,
        new_path TEXT,
        fixed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (book_id) REFERENCES books(id)
    )''')

    # Stats table - daily stats
    c.execute('''CREATE TABLE IF NOT EXISTS stats (
        id INTEGER PRIMARY KEY,
        date TEXT UNIQUE,
        scanned INTEGER DEFAULT 0,
        queued INTEGER DEFAULT 0,
        fixed INTEGER DEFAULT 0,
        verified INTEGER DEFAULT 0,
        api_calls INTEGER DEFAULT 0
    )''')

    conn.commit()
    conn.close()

def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ============== CONFIG ==============

def load_config():
    """Load configuration and secrets from files."""
    config = DEFAULT_CONFIG.copy()

    # Load main config
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            logger.warning(f"Error loading config: {e}")

    # Load secrets (API keys)
    if SECRETS_PATH.exists():
        try:
            with open(SECRETS_PATH) as f:
                secrets = json.load(f)
                config.update(secrets)
        except Exception as e:
            logger.warning(f"Error loading secrets: {e}")

    return config

def save_config(config):
    """Save configuration to file."""
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

# ============== AI API ==============

def build_prompt(messy_names):
    """Build the parsing prompt for AI."""
    items = []
    for i, name in enumerate(messy_names):
        items.append(f"ITEM_{i+1}: {name}")
    names_list = "\n".join(items)

    return f"""Parse these book filenames. Extract author and title.

{names_list}

RULES:
- Author names are people (e.g. "Adrian Tchaikovsky", "Dean Koontz", "Cormac McCarthy")
- Titles are book names (e.g. "Service Model", "The Funhouse", "Stella Maris")
- IMPORTANT: Keep series info in the title! "Book 2", "Book 6", "Part 1" etc MUST stay in the title
  - "Trailer Park Elves, Book 2" -> title should be "Trailer Park Elves, Book 2" NOT just "Trailer Park Elves"
  - "The Expanse 3" -> title should include the "3"
- Remove junk: [bitsearch.to], version numbers [r1.1], quality [64k], format suffixes (EPUB, MP3)
- "Author - Title" format: first part is usually author
- "Title by Author" format: author comes after "by"
- Years like 1999 go in year field, not author
- For "LastName, FirstName" format, author is "FirstName LastName"
- Keep ALL co-authors (e.g. "Michael Dalton, Adam Lance" stays as-is)

Return JSON array. Each object MUST have "item" matching the ITEM_N label:
[
  {{"item": "ITEM_1", "author": "Author Name", "title": "Book Title", "series": null, "series_num": null, "year": null}}
]

Return ONLY the JSON array, nothing else."""

def parse_json_response(text):
    """Extract JSON from AI response."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())

def call_ai(messy_names, config):
    """Call AI API to parse book names."""
    prompt = build_prompt(messy_names)

    # Try OpenRouter first
    if config.get('openrouter_api_key'):
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {config['openrouter_api_key']}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://deucebucket.com",
                    "X-Title": "Library Metadata Manager"
                },
                json={
                    "model": config.get('openrouter_model', 'google/gemma-3n-e4b-it:free'),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                },
                timeout=90
            )

            if resp.status_code == 200:
                result = resp.json()
                text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                if text:
                    return parse_json_response(text)
            else:
                logger.warning(f"OpenRouter error: {resp.status_code}")
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")

    return None

# ============== SCANNER ==============

def looks_suspicious(author, title):
    """Check if author/title look potentially wrong."""
    # Year in author name
    if any(str(y) in author for y in range(1950, 2030)):
        return True, "year in author"

    # Common title words in author
    title_indicators = ['the', 'of', 'and', 'a', 'in', 'to', 'for', 'model', 'maris']
    author_lower = author.lower().split()
    if any(w in author_lower for w in title_indicators):
        return True, "title word in author"

    # Title looks like "First Last" name pattern
    title_parts = title.split()
    if len(title_parts) == 2 and all(p and p[0].isupper() for p in title_parts):
        if not any(w in title.lower() for w in ['the', 'of', 'and', 'a']):
            return True, "title looks like author name"

    # Comma in author (LastName, FirstName format)
    if ',' in author and author.count(',') == 1:
        return True, "comma in author name"

    # Format indicators in author
    format_indicators = ['epub', 'pdf', 'mp3', 'm4b', 'r1.', 'r2.', '[', ']']
    if any(ind in author.lower() for ind in format_indicators):
        return True, "format indicator in author"

    return False, None

def scan_library(config):
    """Scan library for books needing attention."""
    conn = get_db()
    c = conn.cursor()

    scanned = 0
    queued = 0

    for lib_path_str in config.get('library_paths', []):
        lib_path = Path(lib_path_str)
        if not lib_path.exists():
            logger.warning(f"Library path not found: {lib_path}")
            continue

        for author_dir in lib_path.iterdir():
            if not author_dir.is_dir():
                continue

            for title_dir in author_dir.iterdir():
                if not title_dir.is_dir():
                    continue

                path = str(title_dir)
                author = author_dir.name
                title = title_dir.name

                # Check if already in database
                c.execute('SELECT id, status FROM books WHERE path = ?', (path,))
                existing = c.fetchone()

                if existing:
                    if existing['status'] in ['verified', 'fixed']:
                        continue
                else:
                    # Add to database
                    c.execute('''INSERT INTO books (path, current_author, current_title, status)
                                 VALUES (?, ?, ?, 'pending')''', (path, author, title))
                    conn.commit()
                    scanned += 1

                # Check if suspicious
                suspicious, reason = looks_suspicious(author, title)
                if suspicious:
                    # Get book ID
                    c.execute('SELECT id FROM books WHERE path = ?', (path,))
                    book = c.fetchone()
                    if book:
                        # Check if already in queue
                        c.execute('SELECT id FROM queue WHERE book_id = ?', (book['id'],))
                        if not c.fetchone():
                            c.execute('''INSERT INTO queue (book_id, reason) VALUES (?, ?)''',
                                     (book['id'], reason))
                            conn.commit()
                            queued += 1

    # Update daily stats
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute('''INSERT OR REPLACE INTO stats (date, scanned, queued)
                 VALUES (?, COALESCE((SELECT scanned FROM stats WHERE date = ?), 0) + ?,
                         COALESCE((SELECT queued FROM stats WHERE date = ?), 0) + ?)''',
              (today, today, scanned, today, queued))
    conn.commit()
    conn.close()

    logger.info(f"Scan complete: {scanned} new books, {queued} added to queue")
    return scanned, queued

def process_queue(config, limit=None):
    """Process items in the queue."""
    conn = get_db()
    c = conn.cursor()

    batch_size = config.get('batch_size', 3)
    if limit:
        batch_size = min(batch_size, limit)

    logger.info(f"[DEBUG] process_queue called with batch_size={batch_size}, limit={limit}")

    # Get batch from queue
    c.execute('''SELECT q.id as queue_id, q.book_id, q.reason,
                        b.path, b.current_author, b.current_title
                 FROM queue q
                 JOIN books b ON q.book_id = b.id
                 ORDER BY q.priority, q.added_at
                 LIMIT ?''', (batch_size,))
    batch = c.fetchall()

    logger.info(f"[DEBUG] Fetched {len(batch)} items from queue")

    if not batch:
        logger.info("[DEBUG] No items in batch, returning 0")
        conn.close()
        return 0, 0  # (processed, fixed)

    # Build messy names for AI
    messy_names = [f"{row['current_author']} - {row['current_title']}" for row in batch]

    logger.info(f"[DEBUG] Processing batch of {len(batch)} items:")
    for i, name in enumerate(messy_names):
        logger.info(f"[DEBUG]   Item {i+1}: {name}")

    results = call_ai(messy_names, config)
    logger.info(f"[DEBUG] AI returned {len(results) if results else 0} results")

    # Update API call stats
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute('''INSERT OR REPLACE INTO stats (date, api_calls)
                 VALUES (?, COALESCE((SELECT api_calls FROM stats WHERE date = ?), 0) + 1)''',
              (today, today))

    if not results:
        logger.warning("No results from AI")
        conn.commit()
        conn.close()
        return 0, 0  # (processed, fixed)

    processed = 0
    fixed = 0
    for row, result in zip(batch, results):
        new_author = (result.get('author') or '').strip()
        new_title = (result.get('title') or '').strip()

        if not new_author or not new_title:
            # Remove from queue, mark as verified
            c.execute('DELETE FROM queue WHERE id = ?', (row['queue_id'],))
            c.execute('UPDATE books SET status = ? WHERE id = ?', ('verified', row['book_id']))
            processed += 1
            logger.info(f"Verified OK (empty result): {row['current_author']}/{row['current_title']}")
            continue

        # Check if fix needed
        if new_author != row['current_author'] or new_title != row['current_title']:
            old_path = Path(row['path'])
            lib_path = old_path.parent.parent
            new_author_dir = lib_path / new_author
            new_path = new_author_dir / new_title

            if config.get('auto_fix', False):
                # Actually rename the folder
                try:
                    if new_path.exists():
                        # Merge into existing
                        for item in old_path.iterdir():
                            dest = new_path / item.name
                            if not dest.exists():
                                item.rename(dest)
                        old_path.rmdir()
                        if not any(old_path.parent.iterdir()):
                            old_path.parent.rmdir()
                    else:
                        new_author_dir.mkdir(parents=True, exist_ok=True)
                        old_path.rename(new_path)
                        if not any(old_path.parent.iterdir()):
                            old_path.parent.rmdir()

                    logger.info(f"Fixed: {row['current_author']}/{row['current_title']} -> {new_author}/{new_title}")

                    # Record in history
                    c.execute('''INSERT INTO history (book_id, old_author, old_title, new_author, new_title, old_path, new_path)
                                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
                             (row['book_id'], row['current_author'], row['current_title'],
                              new_author, new_title, str(old_path), str(new_path)))

                    # Update book record
                    c.execute('''UPDATE books SET path = ?, current_author = ?, current_title = ?, status = ?
                                 WHERE id = ?''',
                             (str(new_path), new_author, new_title, 'fixed', row['book_id']))

                    fixed += 1
                except Exception as e:
                    logger.error(f"Error fixing {row['path']}: {e}")
                    c.execute('UPDATE books SET status = ? WHERE id = ?', ('error', row['book_id']))
            else:
                # Just record the suggested fix
                c.execute('''INSERT INTO history (book_id, old_author, old_title, new_author, new_title, old_path, new_path)
                             VALUES (?, ?, ?, ?, ?, ?, ?)''',
                         (row['book_id'], row['current_author'], row['current_title'],
                          new_author, new_title, str(old_path), str(new_path)))
                c.execute('UPDATE books SET status = ? WHERE id = ?', ('pending_fix', row['book_id']))
                fixed += 1
        else:
            # No fix needed
            c.execute('UPDATE books SET status = ? WHERE id = ?', ('verified', row['book_id']))
            logger.info(f"Verified OK: {row['current_author']}/{row['current_title']}")

        # Remove from queue
        c.execute('DELETE FROM queue WHERE id = ?', (row['queue_id'],))
        processed += 1

    # Update stats
    c.execute('''UPDATE stats SET fixed = COALESCE(fixed, 0) + ? WHERE date = ?''',
              (fixed, today))

    conn.commit()
    conn.close()

    logger.info(f"[DEBUG] Batch complete: {processed} processed, {fixed} fixed")
    return processed, fixed

def apply_fix(history_id):
    """Apply a pending fix from history."""
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT * FROM history WHERE id = ?', (history_id,))
    fix = c.fetchone()

    if not fix:
        conn.close()
        return False, "Fix not found"

    old_path = Path(fix['old_path'])
    new_path = Path(fix['new_path'])

    if not old_path.exists():
        conn.close()
        return False, "Source folder no longer exists"

    try:
        if new_path.exists():
            # Merge
            for item in old_path.iterdir():
                dest = new_path / item.name
                if not dest.exists():
                    item.rename(dest)
            old_path.rmdir()
            if old_path.parent.exists() and not any(old_path.parent.iterdir()):
                old_path.parent.rmdir()
        else:
            new_path.parent.mkdir(parents=True, exist_ok=True)
            old_path.rename(new_path)
            if old_path.parent.exists() and not any(old_path.parent.iterdir()):
                old_path.parent.rmdir()

        # Update book record
        c.execute('''UPDATE books SET path = ?, current_author = ?, current_title = ?, status = ?
                     WHERE id = ?''',
                 (str(new_path), fix['new_author'], fix['new_title'], 'fixed', fix['book_id']))

        conn.commit()
        conn.close()
        return True, "Fix applied successfully"
    except Exception as e:
        conn.close()
        return False, str(e)

# ============== BACKGROUND WORKER ==============

worker_thread = None
worker_running = False
processing_status = {"active": False, "processed": 0, "total": 0, "current": "", "errors": []}

def process_all_queue(config):
    """Process ALL items in the queue in batches."""
    global processing_status

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) as count FROM queue')
    total = c.fetchone()['count']
    conn.close()

    if total == 0:
        logger.info("Queue is empty, nothing to process")
        return 0, 0  # (total_processed, total_fixed)

    processing_status = {"active": True, "processed": 0, "total": total, "current": "", "errors": []}
    logger.info(f"=== STARTING PROCESS ALL: {total} items in queue ===")

    total_processed = 0
    total_fixed = 0
    batch_num = 0

    while True:
        batch_num += 1
        logger.info(f"--- Processing batch {batch_num} ---")

        processed, fixed = process_queue(config)

        if processed == 0:
            # Check if queue is actually empty or if there was an error
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT COUNT(*) as count FROM queue')
            remaining = c.fetchone()['count']
            conn.close()

            if remaining == 0:
                logger.info("Queue is now empty")
                break
            else:
                logger.warning(f"No items processed but {remaining} remain - possible API error")
                processing_status["errors"].append(f"Batch {batch_num}: No items processed, {remaining} remain")
                break

        total_processed += processed
        total_fixed += fixed
        processing_status["processed"] = total_processed
        logger.info(f"Batch {batch_num} complete: {processed} processed, {fixed} fixed, {total_processed}/{total} total")

        # Rate limiting between batches
        time.sleep(2)

    processing_status["active"] = False
    logger.info(f"=== PROCESS ALL COMPLETE: {total_processed} processed, {total_fixed} fixed ===")
    return total_processed, total_fixed

def background_worker():
    """Background worker that periodically scans and processes."""
    global worker_running

    logger.info("Background worker thread started")

    while worker_running:
        config = load_config()

        if config.get('enabled', True):
            try:
                logger.debug("Worker: Starting scan cycle")
                # Scan library
                scan_library(config)

                # Process queue if auto_fix is enabled
                if config.get('auto_fix', False):
                    logger.debug("Worker: Auto-fix enabled, processing queue")
                    process_all_queue(config)
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)

        # Sleep for scan interval
        interval = config.get('scan_interval_hours', 6) * 3600
        logger.debug(f"Worker: Sleeping for {interval} seconds")
        for _ in range(int(interval / 10)):
            if not worker_running:
                break
            time.sleep(10)

    logger.info("Background worker thread stopped")

def start_worker():
    """Start the background worker."""
    global worker_thread, worker_running

    if worker_thread and worker_thread.is_alive():
        logger.info("Worker already running")
        return

    worker_running = True
    worker_thread = threading.Thread(target=background_worker, daemon=True)
    worker_thread.start()
    logger.info("Background worker started")

def stop_worker():
    """Stop the background worker."""
    global worker_running
    worker_running = False
    logger.info("Background worker stop requested")

def is_worker_running():
    """Check if worker is actually running."""
    global worker_thread, worker_running
    return worker_running and worker_thread is not None and worker_thread.is_alive()

# ============== ROUTES ==============

@app.route('/')
def dashboard():
    """Main dashboard."""
    conn = get_db()
    c = conn.cursor()

    # Get counts
    c.execute('SELECT COUNT(*) as count FROM books')
    total_books = c.fetchone()['count']

    c.execute('SELECT COUNT(*) as count FROM queue')
    queue_size = c.fetchone()['count']

    c.execute("SELECT COUNT(*) as count FROM books WHERE status = 'fixed'")
    fixed_count = c.fetchone()['count']

    c.execute("SELECT COUNT(*) as count FROM books WHERE status = 'verified'")
    verified_count = c.fetchone()['count']

    c.execute("SELECT COUNT(*) as count FROM books WHERE status = 'pending_fix'")
    pending_fixes = c.fetchone()['count']

    # Get recent history
    c.execute('''SELECT h.*, b.path FROM history h
                 JOIN books b ON h.book_id = b.id
                 ORDER BY h.fixed_at DESC LIMIT 10''')
    recent_history = c.fetchall()

    # Get stats for last 7 days
    c.execute('''SELECT date, scanned, queued, fixed, api_calls FROM stats
                 ORDER BY date DESC LIMIT 7''')
    daily_stats = c.fetchall()

    conn.close()

    config = load_config()

    return render_template('dashboard.html',
                          total_books=total_books,
                          queue_size=queue_size,
                          fixed_count=fixed_count,
                          verified_count=verified_count,
                          pending_fixes=pending_fixes,
                          recent_history=recent_history,
                          daily_stats=daily_stats,
                          config=config,
                          worker_running=worker_running)

@app.route('/queue')
def queue_page():
    """Queue management page."""
    conn = get_db()
    c = conn.cursor()

    c.execute('''SELECT q.id, q.reason, q.added_at,
                        b.id as book_id, b.path, b.current_author, b.current_title
                 FROM queue q
                 JOIN books b ON q.book_id = b.id
                 ORDER BY q.priority, q.added_at''')
    queue_items = c.fetchall()

    conn.close()

    return render_template('queue.html', queue_items=queue_items)

@app.route('/history')
def history_page():
    """History of all fixes."""
    conn = get_db()
    c = conn.cursor()

    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page

    c.execute('SELECT COUNT(*) as count FROM history')
    total = c.fetchone()['count']

    c.execute('''SELECT h.*, b.status FROM history h
                 JOIN books b ON h.book_id = b.id
                 ORDER BY h.fixed_at DESC
                 LIMIT ? OFFSET ?''', (per_page, offset))
    history_items = c.fetchall()

    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template('history.html',
                          history_items=history_items,
                          page=page,
                          total_pages=total_pages,
                          total=total)

@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    """Settings page."""
    if request.method == 'POST':
        config = load_config()

        config['library_paths'] = [p.strip() for p in request.form.get('library_paths', '').split('\n') if p.strip()]
        config['openrouter_api_key'] = request.form.get('openrouter_api_key', '')
        config['openrouter_model'] = request.form.get('openrouter_model', 'google/gemma-3n-e4b-it:free')
        config['scan_interval_hours'] = int(request.form.get('scan_interval_hours', 6))
        config['batch_size'] = int(request.form.get('batch_size', 3))
        config['max_requests_per_hour'] = int(request.form.get('max_requests_per_hour', 30))
        config['auto_fix'] = 'auto_fix' in request.form
        config['enabled'] = 'enabled' in request.form

        save_config(config)
        return redirect(url_for('settings_page'))

    config = load_config()
    return render_template('settings.html', config=config)

# ============== API ENDPOINTS ==============

@app.route('/api/scan', methods=['POST'])
def api_scan():
    """Trigger a library scan."""
    config = load_config()
    scanned, queued = scan_library(config)
    return jsonify({'success': True, 'scanned': scanned, 'queued': queued})

@app.route('/api/process', methods=['POST'])
def api_process():
    """Process the queue."""
    config = load_config()
    data = request.json if request.is_json else {}
    process_all = data.get('all', False)
    limit = data.get('limit')

    logger.info(f"API process called: all={process_all}, limit={limit}")

    if process_all:
        # Process entire queue in batches
        processed, fixed = process_all_queue(config)
    else:
        processed, fixed = process_queue(config, limit)

    return jsonify({'success': True, 'processed': processed, 'fixed': fixed})

@app.route('/api/process_status')
def api_process_status():
    """Get current processing status."""
    return jsonify(processing_status)

@app.route('/api/apply_fix/<int:history_id>', methods=['POST'])
def api_apply_fix(history_id):
    """Apply a specific fix."""
    success, message = apply_fix(history_id)
    return jsonify({'success': success, 'message': message})

@app.route('/api/remove_from_queue/<int:queue_id>', methods=['POST'])
def api_remove_from_queue(queue_id):
    """Remove an item from the queue."""
    conn = get_db()
    c = conn.cursor()

    # Get book_id first
    c.execute('SELECT book_id FROM queue WHERE id = ?', (queue_id,))
    row = c.fetchone()
    if row:
        c.execute('DELETE FROM queue WHERE id = ?', (queue_id,))
        c.execute('UPDATE books SET status = ? WHERE id = ?', ('verified', row['book_id']))
        conn.commit()

    conn.close()
    return jsonify({'success': True})

@app.route('/api/stats')
def api_stats():
    """Get current stats."""
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT COUNT(*) as count FROM books')
    total = c.fetchone()['count']

    c.execute('SELECT COUNT(*) as count FROM queue')
    queue = c.fetchone()['count']

    c.execute("SELECT COUNT(*) as count FROM books WHERE status = 'fixed'")
    fixed = c.fetchone()['count']

    c.execute("SELECT COUNT(*) as count FROM books WHERE status = 'pending_fix'")
    pending = c.fetchone()['count']

    c.execute("SELECT COUNT(*) as count FROM books WHERE status = 'verified'")
    verified = c.fetchone()['count']

    conn.close()

    return jsonify({
        'total_books': total,
        'queue_size': queue,
        'fixed': fixed,
        'pending_fixes': pending,
        'verified': verified,
        'worker_running': is_worker_running(),
        'processing': processing_status
    })

@app.route('/api/queue')
def api_queue():
    """Get current queue items as JSON."""
    conn = get_db()
    c = conn.cursor()

    c.execute('''SELECT q.id, q.reason, q.added_at,
                        b.id as book_id, b.path, b.current_author, b.current_title
                 FROM queue q
                 JOIN books b ON q.book_id = b.id
                 ORDER BY q.priority, q.added_at''')
    items = [dict(row) for row in c.fetchall()]

    conn.close()
    return jsonify({'items': items, 'count': len(items)})

@app.route('/api/worker/start', methods=['POST'])
def api_start_worker():
    """Start background worker."""
    start_worker()
    return jsonify({'success': True})

@app.route('/api/worker/stop', methods=['POST'])
def api_stop_worker():
    """Stop background worker."""
    stop_worker()
    return jsonify({'success': True})

# ============== MAIN ==============

if __name__ == '__main__':
    init_db()
    start_worker()
    app.run(host='0.0.0.0', port=5060, debug=False)
