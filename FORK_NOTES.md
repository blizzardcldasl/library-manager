# Fork Notes

This document details the changes and enhancements made in this fork of [deucebucket/library-manager](https://github.com/deucebucket/library-manager).

## Original Project

- **Repository:** [deucebucket/library-manager](https://github.com/deucebucket/library-manager)
- **Original Version:** 0.9.0-beta.27
- **License:** MIT
- **Original Author:** deucebucket

## Fork Purpose

This fork maintains compatibility with the original project while adding enhancements for improved file structure detection and validation.

## Changes in This Fork

### Version 0.9.0-beta.27-fork.1

#### Enhanced Structure Detection
- **Improved name pattern matching** - Extracted `looks_like_person_name()` to shared function
  - Now handles 3-word names, initials, prefixes (Le, De, Von, etc.)
  - Better detection of author-like titles and reversed structures
- **Enhanced reversed structure detection** - More comprehensive pattern matching
  - Detects when author folder doesn't look like a person name
  - Better handling of edge cases

#### Empty Folder Management
- **Empty folder detection** - Detects book folders without audio files
  - Treats folders with only metadata/nfo files as empty
  - Ignores metadata files (.nfo, .txt, .json, .xml, cover images) when determining if folder is empty
  - New GUI page: "Empty Folders" for managing empty folders
  - API endpoints for listing and deleting empty folders
  - Safety checks: Verifies folders are still empty before deletion

#### Recursive Structure Scanning
- **Fully recursive folder analysis** - Handles nested structures at any depth
  - Previously only handled 2-level (Author/Title)
  - Now supports Author/Series/Book and deeper nesting
  - Recursively processes all subdirectories
- **File-to-folder matching verification** - Validates files match their folders
  - Reads audio file metadata (ID3 tags)
  - Compares file metadata with folder structure
  - Detects when files are in wrong folders
  - Flags mismatches as issues
- **Cross-validation** - Compares detected structure with actual file metadata
  - Samples audio files to verify they match folder structure
  - Flags `file_folder_mismatch` when 50%+ files don't match
  - Adds `file_title_mismatch` and `file_author_mismatch` issues

#### New Features
- **Empty Folders page** - GUI for managing empty book folders
  - View all empty folders
  - Delete individual or all empty folders
  - Safety confirmations before deletion
- **File verification** - Automatic validation that files match folders
  - Uses ID3 metadata from audio files
  - Word-based similarity matching
  - Confidence scoring

#### Technical Improvements
- **Recursive scanning function** - `scan_folder_recursive()` handles any depth
- **File verification function** - `verify_file_matches_folder()` validates matches
- **Metadata file definitions** - Constants for identifying metadata-only folders
- **Enhanced issue detection** - New issue types for file mismatches

## Compatibility

This fork maintains full compatibility with:
- Original configuration format
- Original database schema
- Original API endpoints (adds new ones, doesn't break existing)
- Original Docker setup

## Migration Notes

No migration required. This fork is a drop-in replacement that:
- Uses the same database schema
- Uses the same configuration format
- Maintains backward compatibility

## Contributing Back

If you find bugs or improvements that would benefit the original project, please consider:
1. Opening an issue in the [original repository](https://github.com/deucebucket/library-manager/issues)
2. Submitting a pull request to the original project
3. Maintaining this fork for features specific to your needs

## License

This fork maintains the original MIT License. See LICENSE file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed version history. Fork-specific changes are marked with `[FORK]` tag.
