#!/usr/bin/env python3
"""
iPhone Backup Parser
A tool to interpret and extract data from iPhone backup files.

iPhone backups typically contain:
- SQLite databases with contacts, messages, call history
- Property list (plist) files with app data and settings
- Binary files with encrypted data
- Manifest files describing the backup structure
"""

import os
import sqlite3
import plistlib
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse
import sys


class iPhoneBackupParser:
    """Parser for iPhone backup files."""
    
    def __init__(self, backup_path: str):
        """Initialize the parser with backup directory path."""
        self.backup_path = Path(backup_path)
        self.manifest_db = None
        self.info_plist = None
        
        if not self.backup_path.exists():
            raise FileNotFoundError(f"Backup path does not exist: {backup_path}")
            
        self._load_manifest()
        self._load_info()
    
    def _load_manifest(self):
        """Load the Manifest.db file which contains backup file mappings."""
        manifest_path = self.backup_path / "Manifest.db"
        if manifest_path.exists():
            self.manifest_db = sqlite3.connect(str(manifest_path))
            self.manifest_db.row_factory = sqlite3.Row
    
    def _load_info(self):
        """Load the Info.plist file which contains backup metadata."""
        info_path = self.backup_path / "Info.plist"
        if info_path.exists():
            with open(info_path, 'rb') as f:
                self.info_plist = plistlib.load(f)
    
    def get_backup_info(self) -> Dict[str, Any]:
        """Get general information about the backup."""
        info = {}
        if self.info_plist:
            info.update({
                'device_name': self.info_plist.get('Device Name', 'Unknown'),
                'display_name': self.info_plist.get('Display Name', 'Unknown'),
                'last_backup': self.info_plist.get('Last Backup Date', 'Unknown'),
                'ios_version': self.info_plist.get('Product Version', 'Unknown'),
                'serial_number': self.info_plist.get('Serial Number', 'Unknown'),
                'phone_number': self.info_plist.get('Phone Number', 'Unknown'),
            })
        return info
    
    def _get_file_path(self, domain: str, relative_path: str) -> Optional[Path]:
        """Get the actual file path for a domain and relative path."""
        if not self.manifest_db:
            return None
            
        # Create the file ID hash (same method iTunes uses)
        file_id = hashlib.sha1(f"{domain}-{relative_path}".encode()).hexdigest()
        
        cursor = self.manifest_db.cursor()
        cursor.execute("SELECT fileID FROM Files WHERE fileID = ?", (file_id,))
        result = cursor.fetchone()
        
        if result:
            # Files are stored in subdirectories based on first 2 chars of hash
            file_path = self.backup_path / file_id[:2] / file_id
            if file_path.exists():
                return file_path
        return None
    
    def extract_contacts(self) -> List[Dict[str, Any]]:
        """Extract contacts from the backup."""
        contacts_path = self._get_file_path("HomeDomain", "Library/AddressBook/AddressBook.sqlitedb")
        if not contacts_path:
            return []
        
        contacts = []
        try:
            conn = sqlite3.connect(str(contacts_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Query contacts with their details
            cursor.execute("""
                SELECT 
                    ABPerson.ROWID as id,
                    ABPerson.First as first_name,
                    ABPerson.Last as last_name,
                    ABPerson.Organization as organization
                FROM ABPerson
            """)
            
            for row in cursor.fetchall():
                contact = {
                    'id': row['id'],
                    'first_name': row['first_name'] or '',
                    'last_name': row['last_name'] or '',
                    'organization': row['organization'] or '',
                    'phone_numbers': [],
                    'emails': []
                }
                
                # Get phone numbers
                cursor.execute("""
                    SELECT value FROM ABMultiValue 
                    WHERE record_id = ? AND property = 3
                """, (row['id'],))
                contact['phone_numbers'] = [r[0] for r in cursor.fetchall()]
                
                # Get email addresses
                cursor.execute("""
                    SELECT value FROM ABMultiValue 
                    WHERE record_id = ? AND property = 4
                """, (row['id'],))
                contact['emails'] = [r[0] for r in cursor.fetchall()]
                
                contacts.append(contact)
            
            conn.close()
        except Exception as e:
            print(f"Error extracting contacts: {e}")
        
        return contacts
    
    def extract_messages(self) -> List[Dict[str, Any]]:
        """Extract SMS/iMessage data from the backup."""
        messages_path = self._get_file_path("HomeDomain", "Library/SMS/sms.db")
        if not messages_path:
            return []
        
        messages = []
        try:
            conn = sqlite3.connect(str(messages_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    message.ROWID as id,
                    message.text,
                    message.date,
                    message.is_from_me,
                    message.service,
                    handle.id as contact
                FROM message
                LEFT JOIN handle ON message.handle_id = handle.ROWID
                ORDER BY message.date DESC
                LIMIT 1000
            """)
            
            for row in cursor.fetchall():
                messages.append({
                    'id': row['id'],
                    'text': row['text'] or '',
                    'date': row['date'],
                    'is_from_me': bool(row['is_from_me']),
                    'service': row['service'] or '',
                    'contact': row['contact'] or ''
                })
            
            conn.close()
        except Exception as e:
            print(f"Error extracting messages: {e}")
        
        return messages
    
    def extract_call_history(self) -> List[Dict[str, Any]]:
        """Extract call history from the backup."""
        calls_path = self._get_file_path("WirelessDomain", "Library/CallHistoryDB/CallHistory.storedata")
        if not calls_path:
            return []
        
        calls = []
        try:
            conn = sqlite3.connect(str(calls_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    ROWID as id,
                    address,
                    date,
                    duration,
                    flags,
                    name
                FROM ZCALLRECORD
                ORDER BY date DESC
                LIMIT 500
            """)
            
            for row in cursor.fetchall():
                calls.append({
                    'id': row['id'],
                    'number': row['address'] or '',
                    'date': row['date'],
                    'duration': row['duration'],
                    'flags': row['flags'],
                    'contact_name': row['name'] or ''
                })
            
            conn.close()
        except Exception as e:
            print(f"Error extracting call history: {e}")
        
        return calls
    
    def list_installed_apps(self) -> List[Dict[str, Any]]:
        """List installed applications from the backup."""
        apps = []
        
        # Look for app directories in the backup
        for item in self.backup_path.iterdir():
            if item.is_dir() and len(item.name) == 2:  # Backup hash directories
                for file_item in item.iterdir():
                    if file_item.is_file():
                        # Try to identify app-related files
                        try:
                            # This is a simplified approach - real implementation would
                            # need to parse the manifest database properly
                            pass
                        except:
                            continue
        
        return apps
    
    def export_data(self, output_dir: str):
        """Export all extractable data to JSON files."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Export backup info
        info = self.get_backup_info()
        with open(output_path / "backup_info.json", 'w') as f:
            json.dump(info, f, indent=2, default=str)
        
        # Export contacts
        contacts = self.extract_contacts()
        with open(output_path / "contacts.json", 'w') as f:
            json.dump(contacts, f, indent=2, default=str)
        
        # Export messages
        messages = self.extract_messages()
        with open(output_path / "messages.json", 'w') as f:
            json.dump(messages, f, indent=2, default=str)
        
        # Export call history
        calls = self.extract_call_history()
        with open(output_path / "call_history.json", 'w') as f:
            json.dump(calls, f, indent=2, default=str)
        
        print(f"Data exported to: {output_path}")
        print(f"- Backup info: {len(info)} fields")
        print(f"- Contacts: {len(contacts)} entries")
        print(f"- Messages: {len(messages)} entries")
        print(f"- Call history: {len(calls)} entries")


def main():
    """Main command-line interface."""
    parser = argparse.ArgumentParser(description="iPhone Backup Parser - Extract and interpret iPhone backup data")
    parser.add_argument("backup_path", help="Path to iPhone backup directory")
    parser.add_argument("-o", "--output", default="./extracted_data", 
                       help="Output directory for extracted data (default: ./extracted_data)")
    parser.add_argument("-i", "--info", action="store_true", 
                       help="Show backup information only")
    parser.add_argument("-c", "--contacts", action="store_true", 
                       help="Extract contacts only")
    parser.add_argument("-m", "--messages", action="store_true", 
                       help="Extract messages only")
    parser.add_argument("-l", "--calls", action="store_true", 
                       help="Extract call history only")
    
    args = parser.parse_args()
    
    try:
        parser_obj = iPhoneBackupParser(args.backup_path)
        
        if args.info:
            info = parser_obj.get_backup_info()
            print("Backup Information:")
            for key, value in info.items():
                print(f"  {key}: {value}")
        elif args.contacts:
            contacts = parser_obj.extract_contacts()
            print(f"Extracted {len(contacts)} contacts")
            for contact in contacts[:5]:  # Show first 5
                print(f"  {contact['first_name']} {contact['last_name']}: {contact['phone_numbers']}")
        elif args.messages:
            messages = parser_obj.extract_messages()
            print(f"Extracted {len(messages)} messages")
            for msg in messages[:5]:  # Show first 5
                print(f"  From: {msg['contact']}, Text: {msg['text'][:50]}...")
        elif args.calls:
            calls = parser_obj.extract_call_history()
            print(f"Extracted {len(calls)} call records")
            for call in calls[:5]:  # Show first 5
                print(f"  {call['number']}: {call['duration']}s")
        else:
            # Export all data
            parser_obj.export_data(args.output)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()