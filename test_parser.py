#!/usr/bin/env python3
"""
Simple test script to validate iPhone backup parser functionality.
Creates mock data structures to test the parser components.
"""

import os
import sqlite3
import tempfile
import json
import plistlib
from pathlib import Path
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from iphone_backup_parser import iPhoneBackupParser
from backup_analyzer import BackupAnalyzer


def create_mock_backup():
    """Create a mock iPhone backup structure for testing."""
    backup_dir = Path(tempfile.mkdtemp(prefix="mock_iphone_backup_"))
    
    # Create Info.plist
    info_data = {
        'Device Name': 'Test iPhone',
        'Display Name': 'Test Device',
        'Product Version': '15.0',
        'Serial Number': 'TEST123456789',
        'Phone Number': '+1234567890',
        'Last Backup Date': '2023-01-01 12:00:00'
    }
    
    with open(backup_dir / "Info.plist", 'wb') as f:
        plistlib.dump(info_data, f)
    
    # Create Manifest.db
    manifest_db = sqlite3.connect(backup_dir / "Manifest.db")
    cursor = manifest_db.cursor()
    
    cursor.execute("""
        CREATE TABLE Files (
            fileID TEXT PRIMARY KEY,
            domain TEXT,
            relativePath TEXT,
            flags INTEGER,
            file BLOB
        )
    """)
    
    # Add some mock file entries with correct SHA1 hashes
    import hashlib
    
    mock_files = [
        ('HomeDomain', 'Library/AddressBook/AddressBook.sqlitedb'),
        ('HomeDomain', 'Library/SMS/sms.db'),
        ('WirelessDomain', 'Library/CallHistoryDB/CallHistory.storedata'),
    ]
    
    file_id_map = {}
    for domain, path in mock_files:
        file_id = hashlib.sha1(f"{domain}-{path}".encode()).hexdigest()
        file_id_map[(domain, path)] = file_id
        cursor.execute("INSERT INTO Files (fileID, domain, relativePath, flags) VALUES (?, ?, ?, ?)",
                      (file_id, domain, path, 1))
    
    manifest_db.commit()
    manifest_db.close()
    
    # Create directory structure for backup files based on actual file IDs
    contacts_file_id = file_id_map[('HomeDomain', 'Library/AddressBook/AddressBook.sqlitedb')]
    sms_file_id = file_id_map[('HomeDomain', 'Library/SMS/sms.db')]
    calls_file_id = file_id_map[('WirelessDomain', 'Library/CallHistoryDB/CallHistory.storedata')]
    
    # Create directories based on first 2 chars of file IDs
    (backup_dir / contacts_file_id[:2]).mkdir(exist_ok=True)
    (backup_dir / sms_file_id[:2]).mkdir(exist_ok=True)
    (backup_dir / calls_file_id[:2]).mkdir(exist_ok=True)
    
    # Create mock AddressBook.sqlitedb
    contacts_db = sqlite3.connect(backup_dir / contacts_file_id[:2] / contacts_file_id)
    cursor = contacts_db.cursor()
    
    cursor.execute("""
        CREATE TABLE ABPerson (
            ROWID INTEGER PRIMARY KEY,
            First TEXT,
            Last TEXT,
            Organization TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE ABMultiValue (
            ROWID INTEGER PRIMARY KEY,
            record_id INTEGER,
            property INTEGER,
            value TEXT
        )
    """)
    
    # Add mock contacts
    cursor.execute("INSERT INTO ABPerson (ROWID, First, Last, Organization) VALUES (1, 'John', 'Doe', 'Test Corp')")
    cursor.execute("INSERT INTO ABPerson (ROWID, First, Last, Organization) VALUES (2, 'Jane', 'Smith', 'Example Inc')")
    
    # Add phone numbers (property 3)
    cursor.execute("INSERT INTO ABMultiValue (record_id, property, value) VALUES (1, 3, '+1234567890')")
    cursor.execute("INSERT INTO ABMultiValue (record_id, property, value) VALUES (2, 3, '+0987654321')")
    
    # Add emails (property 4)
    cursor.execute("INSERT INTO ABMultiValue (record_id, property, value) VALUES (1, 4, 'john@test.com')")
    cursor.execute("INSERT INTO ABMultiValue (record_id, property, value) VALUES (2, 4, 'jane@example.com')")
    
    contacts_db.commit()
    contacts_db.close()
    
    # Create mock SMS database
    sms_db = sqlite3.connect(backup_dir / sms_file_id[:2] / sms_file_id)
    cursor = sms_db.cursor()
    
    cursor.execute("""
        CREATE TABLE message (
            ROWID INTEGER PRIMARY KEY,
            text TEXT,
            date INTEGER,
            is_from_me INTEGER,
            service TEXT,
            handle_id INTEGER
        )
    """)
    
    cursor.execute("""
        CREATE TABLE handle (
            ROWID INTEGER PRIMARY KEY,
            id TEXT
        )
    """)
    
    # Add mock handles
    cursor.execute("INSERT INTO handle (ROWID, id) VALUES (1, '+1234567890')")
    cursor.execute("INSERT INTO handle (ROWID, id) VALUES (2, '+0987654321')")
    
    # Add mock messages
    cursor.execute("INSERT INTO message (text, date, is_from_me, service, handle_id) VALUES ('Hello there!', 1640995200, 1, 'iMessage', 1)")
    cursor.execute("INSERT INTO message (text, date, is_from_me, service, handle_id) VALUES ('Hi back!', 1640995260, 0, 'iMessage', 2)")
    
    sms_db.commit()
    sms_db.close()
    
    # Create mock call history
    calls_db = sqlite3.connect(backup_dir / calls_file_id[:2] / calls_file_id)
    cursor = calls_db.cursor()
    
    cursor.execute("""
        CREATE TABLE ZCALLRECORD (
            ROWID INTEGER PRIMARY KEY,
            address TEXT,
            date INTEGER,
            duration INTEGER,
            flags INTEGER,
            name TEXT
        )
    """)
    
    # Add mock call records
    cursor.execute("INSERT INTO ZCALLRECORD (address, date, duration, flags, name) VALUES ('+1234567890', 1640995200, 120, 5, 'John Doe')")
    cursor.execute("INSERT INTO ZCALLRECORD (address, date, duration, flags, name) VALUES ('+0987654321', 1640995400, 300, 5, 'Jane Smith')")
    
    calls_db.commit()
    calls_db.close()
    
    return backup_dir


def test_parser():
    """Test the iPhone backup parser with mock data."""
    print("🧪 Creating mock iPhone backup for testing...")
    backup_dir = create_mock_backup()
    
    try:
        print(f"📁 Mock backup created at: {backup_dir}")
        
        # Test parser initialization
        print("\n🔍 Testing parser initialization...")
        parser = iPhoneBackupParser(str(backup_dir))
        
        # Test backup info extraction
        print("\n📱 Testing backup info extraction...")
        info = parser.get_backup_info()
        print("Backup Info:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        
        # Test contacts extraction
        print("\n📇 Testing contacts extraction...")
        contacts = parser.extract_contacts()
        print(f"Found {len(contacts)} contacts:")
        for contact in contacts:
            print(f"  - {contact['first_name']} {contact['last_name']}: {contact['phone_numbers']}")
        
        # Test messages extraction
        print("\n💬 Testing messages extraction...")
        messages = parser.extract_messages()
        print(f"Found {len(messages)} messages:")
        for msg in messages:
            direction = "→" if msg['is_from_me'] else "←"
            print(f"  {direction} {msg['contact']}: {msg['text']}")
        
        # Test call history extraction
        print("\n📞 Testing call history extraction...")
        calls = parser.extract_call_history()
        print(f"Found {len(calls)} call records:")
        for call in calls:
            print(f"  - {call['contact_name']} ({call['number']}): {call['duration']}s")
        
        # Test analyzer
        print("\n🔬 Testing backup analyzer...")
        analyzer = BackupAnalyzer(parser)
        
        size_info = analyzer.analyze_backup_size()
        print(f"Backup size: {size_info['total_size_mb']} MB, {size_info['file_count']} files")
        
        # Test export functionality
        print("\n💾 Testing data export...")
        export_dir = Path(tempfile.mkdtemp(prefix="exported_data_"))
        parser.export_data(str(export_dir))
        
        # Verify exported files
        exported_files = list(export_dir.glob("*.json"))
        print(f"Exported files: {[f.name for f in exported_files]}")
        
        # Check content of one exported file
        if (export_dir / "contacts.json").exists():
            with open(export_dir / "contacts.json", 'r') as f:
                exported_contacts = json.load(f)
                print(f"Exported contacts file contains {len(exported_contacts)} entries")
        
        print("\n✅ All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        import shutil
        try:
            shutil.rmtree(backup_dir)
            if 'export_dir' in locals():
                shutil.rmtree(export_dir)
        except:
            pass


if __name__ == "__main__":
    test_parser()