#!/usr/bin/env python3
"""
Command-line interface for iPhone backup analysis.
Provides an easy-to-use interface for extracting and analyzing backup data.
"""

import sys
import os
from pathlib import Path
import argparse
import json

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from iphone_backup_parser import iPhoneBackupParser
from backup_analyzer import BackupAnalyzer, create_summary_report, format_timestamp


def print_contacts_summary(contacts):
    """Print a summary of contacts."""
    print(f"\n📇 Contacts ({len(contacts)} total):")
    if not contacts:
        print("  No contacts found.")
        return
    
    for i, contact in enumerate(contacts[:10]):  # Show first 10
        name = f"{contact['first_name']} {contact['last_name']}".strip()
        if not name:
            name = contact['organization'] or f"Contact {contact['id']}"
        
        phones = ", ".join(contact['phone_numbers'][:2])  # Show first 2 numbers
        emails = ", ".join(contact['emails'][:2])  # Show first 2 emails
        
        print(f"  {i+1:2d}. {name}")
        if phones:
            print(f"      Phone: {phones}")
        if emails:
            print(f"      Email: {emails}")
    
    if len(contacts) > 10:
        print(f"  ... and {len(contacts) - 10} more contacts")


def print_messages_summary(messages):
    """Print a summary of messages."""
    print(f"\n💬 Messages ({len(messages)} total):")
    if not messages:
        print("  No messages found.")
        return
    
    for i, msg in enumerate(messages[:10]):  # Show first 10
        direction = "→" if msg['is_from_me'] else "←"
        contact = msg['contact'] or "Unknown"
        text = (msg['text'] or "")[:50]
        if len(msg['text'] or "") > 50:
            text += "..."
        
        date = format_timestamp(msg['date'])
        
        print(f"  {i+1:2d}. {direction} {contact}")
        print(f"      {text}")
        print(f"      {date}")
    
    if len(messages) > 10:
        print(f"  ... and {len(messages) - 10} more messages")


def print_calls_summary(calls):
    """Print a summary of call history."""
    print(f"\n📞 Call History ({len(calls)} total):")
    if not calls:
        print("  No call history found.")
        return
    
    for i, call in enumerate(calls[:10]):  # Show first 10
        contact = call['contact_name'] or call['number']
        duration = f"{call['duration']}s" if call['duration'] else "Unknown duration"
        date = format_timestamp(call['date'])
        
        print(f"  {i+1:2d}. {contact}")
        print(f"      Duration: {duration}")
        print(f"      Date: {date}")
    
    if len(calls) > 10:
        print(f"  ... and {len(calls) - 10} more calls")


def interactive_mode(parser, analyzer):
    """Run interactive mode for exploring backup data."""
    print("\n🔍 Interactive Backup Explorer")
    print("Commands: info, contacts, messages, calls, photos, safari, notes, size, apps, export, quit")
    
    while True:
        try:
            cmd = input("\n> ").strip().lower()
            
            if cmd in ['quit', 'exit', 'q']:
                break
            elif cmd == 'info':
                info = parser.get_backup_info()
                print("\n📱 Backup Information:")
                for key, value in info.items():
                    print(f"  {key.replace('_', ' ').title()}: {value}")
            
            elif cmd == 'contacts':
                contacts = parser.extract_contacts()
                print_contacts_summary(contacts)
            
            elif cmd == 'messages':
                messages = parser.extract_messages()
                print_messages_summary(messages)
            
            elif cmd == 'calls':
                calls = parser.extract_call_history()
                print_calls_summary(calls)
            
            elif cmd == 'photos':
                photos = analyzer.extract_photos_metadata()
                print(f"\n📸 Photos Metadata ({len(photos)} total):")
                for i, photo in enumerate(photos[:5]):
                    print(f"  {i+1}. {photo}")
            
            elif cmd == 'safari':
                history = analyzer.extract_safari_history()
                print(f"\n🌐 Safari History ({len(history)} total):")
                for i, item in enumerate(history[:10]):
                    print(f"  {i+1:2d}. {item['title'][:50]}")
                    print(f"      {item['url'][:70]}")
            
            elif cmd == 'notes':
                notes = analyzer.extract_notes()
                print(f"\n📝 Notes ({len(notes)} total):")
                for i, note in enumerate(notes[:10]):
                    print(f"  {i+1:2d}. {note['title'][:50]}")
                    print(f"      {note['summary'][:100]}")
            
            elif cmd == 'size':
                size_info = analyzer.analyze_backup_size()
                print(f"\n💾 Backup Size Analysis:")
                print(f"  Total Size: {size_info['total_size_mb']} MB")
                print(f"  Total Files: {size_info['file_count']}")
                print(f"  File Types:")
                for ext, stats in sorted(size_info['file_types'].items()):
                    mb_size = stats['size'] / (1024 * 1024)
                    print(f"    {ext or 'no extension'}: {stats['count']} files, {mb_size:.1f} MB")
            
            elif cmd == 'apps':
                apps = analyzer.find_app_data()
                print(f"\n📱 App Data ({len(apps)} apps):")
                for i, app in enumerate(apps[:10]):
                    print(f"  {i+1:2d}. {app['domain']}: {app['total_files']} files")
            
            elif cmd == 'export':
                output_dir = input("Enter output directory (default: ./extracted_data): ").strip()
                if not output_dir:
                    output_dir = "./extracted_data"
                parser.export_data(output_dir)
            
            elif cmd == 'help':
                print("Available commands:")
                print("  info     - Show backup information")
                print("  contacts - Show contacts summary")
                print("  messages - Show messages summary")
                print("  calls    - Show call history summary")
                print("  photos   - Show photos metadata")
                print("  safari   - Show Safari browsing history")
                print("  notes    - Show notes")
                print("  size     - Show backup size analysis")
                print("  apps     - Show app data")
                print("  export   - Export all data to files")
                print("  quit     - Exit")
            
            else:
                print("Unknown command. Type 'help' for available commands.")
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("\nGoodbye!")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="iPhone Backup Interpreter - Extract and analyze iPhone backup data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python kali_cli.py /path/to/backup                    # Interactive mode
  python kali_cli.py /path/to/backup --summary          # Show summary report
  python kali_cli.py /path/to/backup --export           # Export all data
  python kali_cli.py /path/to/backup --contacts         # Show contacts only
  python kali_cli.py /path/to/backup --messages         # Show messages only
        """
    )
    
    parser.add_argument("backup_path", help="Path to iPhone backup directory")
    parser.add_argument("-s", "--summary", action="store_true", 
                       help="Show comprehensive summary report")
    parser.add_argument("-e", "--export", metavar="DIR", 
                       help="Export all data to specified directory")
    parser.add_argument("-i", "--interactive", action="store_true", 
                       help="Run in interactive mode (default if no other options)")
    parser.add_argument("-c", "--contacts", action="store_true", 
                       help="Show contacts summary")
    parser.add_argument("-m", "--messages", action="store_true", 
                       help="Show messages summary")
    parser.add_argument("-l", "--calls", action="store_true", 
                       help="Show call history summary")
    parser.add_argument("--info", action="store_true", 
                       help="Show backup information only")
    
    args = parser.parse_args()
    
    try:
        # Initialize parser and analyzer
        backup_parser = iPhoneBackupParser(args.backup_path)
        analyzer = BackupAnalyzer(backup_parser)
        
        # Determine what to do based on arguments
        if args.summary:
            report = create_summary_report(backup_parser, analyzer)
            print(report)
        
        elif args.export:
            backup_parser.export_data(args.export)
        
        elif args.info:
            info = backup_parser.get_backup_info()
            print("📱 Backup Information:")
            for key, value in info.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")
        
        elif args.contacts:
            contacts = backup_parser.extract_contacts()
            print_contacts_summary(contacts)
        
        elif args.messages:
            messages = backup_parser.extract_messages()
            print_messages_summary(messages)
        
        elif args.calls:
            calls = backup_parser.extract_call_history()
            print_calls_summary(calls)
        
        else:
            # Default to interactive mode
            interactive_mode(backup_parser, analyzer)
    
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("Make sure the backup path exists and contains iPhone backup files.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()