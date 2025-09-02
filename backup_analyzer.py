#!/usr/bin/env python3
"""
Additional utilities for iPhone backup analysis.
Includes helper functions and specialized extractors.
"""

import os
import sqlite3
import plistlib
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import datetime


class BackupAnalyzer:
    """Additional analysis tools for iPhone backups."""
    
    def __init__(self, backup_parser):
        """Initialize with a BackupParser instance."""
        self.parser = backup_parser
    
    def analyze_backup_size(self) -> Dict[str, Any]:
        """Analyze the size and structure of the backup."""
        total_size = 0
        file_count = 0
        type_stats = {}
        
        for root, dirs, files in os.walk(self.parser.backup_path):
            for file in files:
                file_path = Path(root) / file
                if file_path.exists():
                    size = file_path.stat().st_size
                    total_size += size
                    file_count += 1
                    
                    # Categorize by extension
                    ext = file_path.suffix.lower()
                    if ext not in type_stats:
                        type_stats[ext] = {'count': 0, 'size': 0}
                    type_stats[ext]['count'] += 1
                    type_stats[ext]['size'] += size
        
        return {
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'file_count': file_count,
            'file_types': type_stats
        }
    
    def find_app_data(self) -> List[Dict[str, Any]]:
        """Find application data within the backup."""
        app_data = []
        
        if not self.parser.manifest_db:
            return app_data
        
        cursor = self.parser.manifest_db.cursor()
        cursor.execute("""
            SELECT domain, relativePath, fileID 
            FROM Files 
            WHERE domain LIKE 'AppDomain%' 
            ORDER BY domain, relativePath
        """)
        
        current_app = None
        app_info = None
        
        for row in cursor.fetchall():
            domain = row['domain']
            if domain != current_app:
                if app_info:
                    app_data.append(app_info)
                
                current_app = domain
                app_info = {
                    'domain': domain,
                    'files': [],
                    'total_files': 0
                }
            
            if app_info:
                app_info['files'].append({
                    'path': row['relativePath'],
                    'file_id': row['fileID']
                })
                app_info['total_files'] += 1
        
        if app_info:
            app_data.append(app_info)
        
        return app_data
    
    def extract_photos_metadata(self) -> List[Dict[str, Any]]:
        """Extract photos metadata from the backup."""
        photos_path = self.parser._get_file_path("CameraRollDomain", "Media/PhotoData/Photos.sqlite")
        if not photos_path:
            return []
        
        photos = []
        try:
            conn = sqlite3.connect(str(photos_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Try different table names that might exist
            tables = ['ZASSET', 'ZGENERICASSET', 'ZPHOTOLIBRARY']
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                    if cursor.fetchone():
                        cursor.execute(f"PRAGMA table_info({table})")
                        columns = [col[1] for col in cursor.fetchall()]
                        
                        # Build a query based on available columns
                        select_cols = []
                        if 'ZFILENAME' in columns:
                            select_cols.append('ZFILENAME as filename')
                        if 'ZDATECREATED' in columns:
                            select_cols.append('ZDATECREATED as date_created')
                        if 'ZLATITUDE' in columns and 'ZLONGITUDE' in columns:
                            select_cols.append('ZLATITUDE as latitude')
                            select_cols.append('ZLONGITUDE as longitude')
                        
                        if select_cols:
                            query = f"SELECT {', '.join(select_cols)} FROM {table} LIMIT 100"
                            cursor.execute(query)
                            
                            for row in cursor.fetchall():
                                photo_data = dict(row)
                                photos.append(photo_data)
                        break
                except sqlite3.Error:
                    continue
            
            conn.close()
        except Exception as e:
            print(f"Error extracting photos metadata: {e}")
        
        return photos
    
    def extract_safari_history(self) -> List[Dict[str, Any]]:
        """Extract Safari browsing history."""
        history_path = self.parser._get_file_path("HomeDomain", "Library/Safari/History.db")
        if not history_path:
            return []
        
        history = []
        try:
            conn = sqlite3.connect(str(history_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    url,
                    title,
                    visit_count,
                    last_visit_time
                FROM history_items
                ORDER BY last_visit_time DESC
                LIMIT 500
            """)
            
            for row in cursor.fetchall():
                history.append({
                    'url': row['url'],
                    'title': row['title'] or '',
                    'visit_count': row['visit_count'],
                    'last_visit': row['last_visit_time']
                })
            
            conn.close()
        except Exception as e:
            print(f"Error extracting Safari history: {e}")
        
        return history
    
    def extract_notes(self) -> List[Dict[str, Any]]:
        """Extract Notes app data."""
        notes_path = self.parser._get_file_path("HomeDomain", "Library/Notes/notes.sqlite")
        if not notes_path:
            return []
        
        notes = []
        try:
            conn = sqlite3.connect(str(notes_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Try different table structures
            try:
                cursor.execute("""
                    SELECT 
                        ROWID as id,
                        title,
                        summary,
                        creation_date,
                        modification_date
                    FROM note
                    ORDER BY modification_date DESC
                """)
                
                for row in cursor.fetchall():
                    notes.append({
                        'id': row['id'],
                        'title': row['title'] or '',
                        'summary': row['summary'] or '',
                        'created': row['creation_date'],
                        'modified': row['modification_date']
                    })
            except sqlite3.Error as e:
                print(f"Note extraction error: {e}")
            
            conn.close()
        except Exception as e:
            print(f"Error extracting notes: {e}")
        
        return notes


def format_timestamp(timestamp):
    """Convert various timestamp formats to readable datetime."""
    if timestamp is None:
        return "Unknown"
    
    try:
        # iOS uses Core Data timestamps (seconds since 2001-01-01)
        if timestamp > 1000000000:  # Looks like Unix timestamp
            dt = datetime.datetime.fromtimestamp(timestamp)
        else:  # Core Data timestamp
            dt = datetime.datetime(2001, 1, 1) + datetime.timedelta(seconds=timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return str(timestamp)


def create_summary_report(backup_parser, analyzer) -> str:
    """Create a comprehensive summary report."""
    report = []
    report.append("=" * 50)
    report.append("iPhone Backup Analysis Report")
    report.append("=" * 50)
    
    # Basic backup info
    info = backup_parser.get_backup_info()
    report.append("\n📱 Device Information:")
    for key, value in info.items():
        report.append(f"  {key.replace('_', ' ').title()}: {value}")
    
    # Size analysis
    size_info = analyzer.analyze_backup_size()
    report.append(f"\n💾 Backup Size:")
    report.append(f"  Total Size: {size_info['total_size_mb']} MB")
    report.append(f"  Total Files: {size_info['file_count']}")
    
    # Data extraction summary
    contacts = backup_parser.extract_contacts()
    messages = backup_parser.extract_messages()
    calls = backup_parser.extract_call_history()
    
    report.append(f"\n📊 Data Summary:")
    report.append(f"  Contacts: {len(contacts)}")
    report.append(f"  Messages: {len(messages)}")
    report.append(f"  Call Records: {len(calls)}")
    
    # Additional data
    photos = analyzer.extract_photos_metadata()
    safari = analyzer.extract_safari_history()
    notes = analyzer.extract_notes()
    
    report.append(f"  Photos: {len(photos)}")
    report.append(f"  Safari History: {len(safari)}")
    report.append(f"  Notes: {len(notes)}")
    
    return "\n".join(report)