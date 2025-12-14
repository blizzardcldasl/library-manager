# Contributing to Library Manager

Thanks for your interest in contributing! Here's how to get started.

## Getting Started

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Test thoroughly (see below)
5. Submit a PR

## Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/library-manager.git
cd library-manager
pip install -r requirements.txt
python app.py
```

## Testing

Before submitting:
```bash
# Run integration tests
./test-env/run-integration-tests.sh

# Manual testing
# 1. Web UI loads at http://localhost:5757
# 2. Settings page saves correctly
# 3. Library scan finds audiobooks
# 4. Apply fix moves files correctly
# 5. Undo restores original location
```

## PR Guidelines

- Keep PRs focused - one feature/fix per PR
- Update CHANGELOG.md with your changes
- If adding new config options, update config.example.json
- Test with Docker: `docker build -t library-manager .`

## Code Style

- Python 3.8+ compatible
- Use existing patterns in the codebase
- Comments for non-obvious logic
- Meaningful variable names

---

## Security Review

All PRs are reviewed for security before merge.

### We Check For:

**Malware/Exploits:**
- Path traversal (file ops outside library paths)
- Unauthorized network calls
- Command injection
- Credential exposure
- Destructive operations without confirmation
- Obfuscated code (base64, eval, exec)

**Sabotage:**
- Logic that fails in edge cases
- Data scrambling (swapping author/title)
- Bad default values
- Fake error messages
- Subtle data corruption

### File Operation Rules:
- All file writes MUST stay within configured `library_paths`
- Metadata changes MUST preserve originals in backup
- Rollback MUST actually restore original state
- Never trust paths without validation

This isn't about distrust - it's about protecting users' libraries. Open source means anyone can contribute, which is great, but it also means we verify everything.

---

## Questions?

Open an issue or start a discussion on GitHub.
