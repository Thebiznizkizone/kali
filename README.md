# Kali - iPhone Backup Interpreter

A powerful Python tool for interpreting and extracting data from iPhone backup files. This tool helps you analyze iTunes/Finder backup files and extract various types of data including contacts, messages, call history, photos metadata, Safari history, and more.

## Features

- **Comprehensive Data Extraction**: Extract contacts, SMS/iMessages, call history, photos metadata, Safari browsing history, notes, and app data
- **Backup Analysis**: Analyze backup size, file structure, and get detailed backup information
- **Multiple Interfaces**: Command-line interface and interactive mode for easy exploration
- **Export Functionality**: Export extracted data to JSON files for further analysis
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

1. Clone this repository:
```bash
git clone https://github.com/Thebiznizkizone/kali.git
cd kali
```

2. Ensure you have Python 3.6+ installed

3. The tool uses only standard library modules, so no additional installation is required.

## Usage

### Quick Start

```bash
# Interactive mode (recommended for exploration)
python kali_cli.py /path/to/iphone/backup

# Show comprehensive summary report
python kali_cli.py /path/to/iphone/backup --summary

# Export all data to JSON files
python kali_cli.py /path/to/iphone/backup --export ./extracted_data

# Show specific data types
python kali_cli.py /path/to/iphone/backup --contacts
python kali_cli.py /path/to/iphone/backup --messages
python kali_cli.py /path/to/iphone/backup --calls
```

### Interactive Mode

The interactive mode provides a command-line interface for exploring backup data:

```
🔍 Interactive Backup Explorer
Commands: info, contacts, messages, calls, photos, safari, notes, size, apps, export, quit

> info          # Show device and backup information
> contacts      # Display contacts summary
> messages      # Show recent messages
> calls         # Display call history
> photos        # Show photos metadata
> safari        # Display browsing history
> notes         # Show notes
> size          # Analyze backup size and structure
> apps          # List app data
> export        # Export all data to files
> quit          # Exit
```

### Finding iPhone Backup Location

**macOS:**
- `~/Library/Application Support/MobileSync/Backup/`

**Windows:**
- `%APPDATA%\Apple Computer\MobileSync\Backup\`

**Each device backup is stored in a folder with a unique identifier (UUID).**

## Supported Data Types

### Core Data
- **Contacts**: Names, phone numbers, email addresses, organizations
- **Messages**: SMS and iMessage conversations with timestamps
- **Call History**: Incoming/outgoing calls with duration and contact info
- **Device Info**: Device name, iOS version, serial number, backup date

### Additional Data
- **Photos Metadata**: Photo information and location data (when available)
- **Safari History**: Browsing history with URLs and visit counts
- **Notes**: Notes app content and timestamps
- **App Data**: Information about installed applications

## Examples

### Basic Usage
```bash
# Analyze a backup and show summary
python kali_cli.py "/Users/username/Library/Application Support/MobileSync/Backup/00008030-001234567890002E" --summary

# Extract contacts only
python kali_cli.py "/path/to/backup" --contacts
```

### Programmatic Usage
```python
from iphone_backup_parser import iPhoneBackupParser
from backup_analyzer import BackupAnalyzer

# Initialize parser
parser = iPhoneBackupParser("/path/to/backup")
analyzer = BackupAnalyzer(parser)

# Extract data
contacts = parser.extract_contacts()
messages = parser.extract_messages()
backup_info = parser.get_backup_info()

# Analyze backup
size_info = analyzer.analyze_backup_size()
```

## Testing

Run the test suite to verify functionality:

```bash
python test_parser.py
```

This creates mock backup data and tests all extraction functions.

## File Structure

- `iphone_backup_parser.py` - Core parsing functionality
- `backup_analyzer.py` - Advanced analysis tools
- `kali_cli.py` - Command-line interface
- `test_parser.py` - Test suite with mock data

## Technical Details

iPhone backups store data in SQLite databases and property list (plist) files. This tool:

1. Reads the `Manifest.db` file to understand backup structure
2. Locates specific data files using domain and path mappings
3. Extracts data from SQLite databases (contacts, messages, calls)
4. Parses plist files for configuration and metadata
5. Provides structured access to the extracted information

## Privacy and Security

- This tool only reads local backup files
- No data is transmitted over the network
- All processing happens locally on your machine
- Exported data is saved as plain JSON files

## Limitations

- Encrypted backups require the backup password (not currently supported)
- Some app-specific data may require additional parsing logic
- Backup format may vary between iOS versions
- Some data types may not be available in all backup versions

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is open source. Please ensure you have the legal right to access and analyze any backup files you use with this tool.

## Disclaimer

This tool is for legitimate backup analysis purposes only. Users are responsible for ensuring they have the legal right to access and analyze the backup files they process.