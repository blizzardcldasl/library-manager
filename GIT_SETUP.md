# Git Repository Setup Guide

## Current Status

Your repository is currently configured with:
- **Remote:** `origin` → `https://github.com/deucebucket/library-manager.git` (original project)

## Setting Up Your Fork Repository

### Option 1: Change Remote to Your Fork (Recommended)

If you've already created a fork on GitHub:

```bash
# Remove current origin (or rename it to 'upstream')
git remote rename origin upstream

# Add your fork as the new origin
git remote add origin https://github.com/YOUR_USERNAME/library-manager.git

# Verify
git remote -v
```

### Option 2: Keep Original as Upstream, Add Your Fork

If you want to keep the original as a reference:

```bash
# Rename current origin to upstream
git remote rename origin upstream

# Add your fork as origin
git remote add origin https://github.com/YOUR_USERNAME/library-manager.git

# Verify both remotes
git remote -v
# Should show:
# origin    https://github.com/YOUR_USERNAME/library-manager.git (fetch)
# origin    https://github.com/YOUR_USERNAME/library-manager.git (push)
# upstream  https://github.com/deucebucket/library-manager.git (fetch)
# upstream  https://github.com/deucebucket/library-manager.git (push)
```

### Option 3: Create New Repository on GitHub

If you haven't created your fork yet:

1. Go to https://github.com/deucebucket/library-manager
2. Click "Fork" button (top right)
3. Or create a new repository on GitHub
4. Then follow Option 1 or 2 above

## Committing Your Changes

Once your remote is set up:

```bash
# Stage all changes
git add .

# Or stage specific files:
git add CHANGELOG.md FORK_NOTES.md FORK_PROTOCOL.md README.md CONTRIBUTING.md app.py templates/empty_folders.html templates/base.html

# Commit with descriptive message
git commit -m "Add fork documentation and enhancements

- Add recursive structure scanning for nested folders
- Add file-to-folder matching verification
- Add empty folder detection and management
- Improve name pattern matching
- Add FORK_NOTES.md and FORK_PROTOCOL.md
- Update version to 0.9.0-beta.27-fork.1"

# Push to your repository
git push origin main
```

## If You Need to Create a New Branch

```bash
# Create and switch to new branch
git checkout -b fork-enhancements

# Make your commits
git add .
git commit -m "Your commit message"

# Push to your fork
git push origin fork-enhancements
```

## Keeping Up with Original Project

If you kept upstream remote:

```bash
# Fetch updates from original
git fetch upstream

# Merge updates into your fork
git checkout main
git merge upstream/main

# Resolve any conflicts if needed
# Then push your updated fork
git push origin main
```

## Making It Public

If your repository is private and you want to make it public:

1. Go to your GitHub repository page
2. Click "Settings" tab
3. Scroll down to "Danger Zone"
4. Click "Change visibility"
5. Select "Make public"
6. Confirm

## Quick Commands Summary

```bash
# Check status
git status

# See what changed
git diff

# Stage all changes
git add .

# Commit
git commit -m "Your message"

# Push to your fork
git push origin main

# If first time pushing, you might need:
git push -u origin main
```
