# data_backup.py
import pandas as pd
import os
import shutil
from datetime import datetime
import json

def create_data_backup():
    """Create comprehensive backups of ORCID data files"""
    
    print("💾 ORCID DATA BACKUP SCRIPT")
    print("=" * 50)
    
    # Create backup directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"orcid_backups/backup_{timestamp}"
    
    try:
        # Create backup directory
        os.makedirs(backup_dir, exist_ok=True)
        print(f"📁 Created backup directory: {backup_dir}")
        
        # Files to backup
        files_to_backup = [
            "data_ORCIDs.xlsx",
            "data_ORCIDs_CORRECTED.xlsx", 
            "orcid_publication_details.xlsx"
        ]
        
        backed_up_files = []
        
        # Backup each file if it exists
        for file_name in files_to_backup:
            if os.path.exists(file_name):
                # Copy the file
                shutil.copy2(file_name, os.path.join(backup_dir, file_name))
                backed_up_files.append(file_name)
                print(f"✅ Backed up: {file_name}")
            else:
                print(f"⚠️  File not found: {file_name}")
        
        # Create backup info file
        backup_info = {
            "backup_timestamp": timestamp,
            "backup_date": datetime.now().isoformat(),
            "files_backed_up": backed_up_files,
            "total_files": len(backed_up_files)
        }
        
        # Save backup info
        with open(os.path.join(backup_dir, "backup_info.json"), "w") as f:
            json.dump(backup_info, f, indent=2)
        
        print(f"\n📊 BACKUP SUMMARY:")
        print(f"   📁 Backup location: {backup_dir}")
        print(f"   📄 Files backed up: {len(backed_up_files)}")
        print(f"   🕒 Backup timestamp: {timestamp}")
        
        # Clean up old backups (keep last 10)
        cleanup_old_backups()
        
        return backup_dir
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None

def cleanup_old_backups(keep_count=10):
    """Keep only the most recent backups"""
    
    backup_root = "orcid_backups"
    if not os.path.exists(backup_root):
        return
    
    try:
        # Get all backup directories
        backup_dirs = []
        for item in os.listdir(backup_root):
            item_path = os.path.join(backup_root, item)
            if os.path.isdir(item_path) and item.startswith("backup_"):
                backup_dirs.append((item_path, os.path.getctime(item_path)))
        
        # Sort by creation time (newest first)
        backup_dirs.sort(key=lambda x: x[1], reverse=True)
        
        # Remove old backups
        if len(backup_dirs) > keep_count:
            for backup_path, _ in backup_dirs[keep_count:]:
                shutil.rmtree(backup_path)
                print(f"🗑️  Removed old backup: {os.path.basename(backup_path)}")
                
    except Exception as e:
        print(f"⚠️  Error cleaning up old backups: {e}")

def list_available_backups():
    """List all available backups"""
    
    backup_root = "orcid_backups"
    if not os.path.exists(backup_root):
        print("❌ No backup directory found")
        return []
    
    try:
        backups = []
        print("\n📋 AVAILABLE BACKUPS:")
        print("-" * 40)
        
        for item in sorted(os.listdir(backup_root), reverse=True):
            item_path = os.path.join(backup_root, item)
            if os.path.isdir(item_path) and item.startswith("backup_"):
                # Read backup info
                info_file = os.path.join(item_path, "backup_info.json")
                if os.path.exists(info_file):
                    with open(info_file, "r") as f:
                        info = json.load(f)
                    file_count = len(info.get("files_backed_up", []))
                    timestamp = info.get("backup_timestamp", "Unknown")
                    print(f"📁 {item}")
                    print(f"   🕒 {timestamp}")
                    print(f"   📄 {file_count} files")
                else:
                    print(f"📁 {item} (no info file)")
                
                backups.append(item_path)
        
        return backups
        
    except Exception as e:
        print(f"❌ Error listing backups: {e}")
        return []

def restore_from_backup(backup_name=None):
    """Restore data from a backup"""
    
    print("🔄 RESTORE FROM BACKUP")
    print("=" * 40)
    
    if backup_name is None:
        backups = list_available_backups()
        if not backups:
            return
        
        print("\nEnter the backup name to restore (e.g., backup_20241215_143022):")
        backup_name = input("Backup name: ").strip()
    
    backup_path = os.path.join("orcid_backups", backup_name)
    
    if not os.path.exists(backup_path):
        print(f"❌ Backup not found: {backup_path}")
        return
    
    try:
        # Read backup info
        info_file = os.path.join(backup_path, "backup_info.json")
        if os.path.exists(info_file):
            with open(info_file, "r") as f:
                info = json.load(f)
            files_available = info.get("files_backed_up", [])
        else:
            # If no info file, list all .xlsx files in backup
            files_available = [f for f in os.listdir(backup_path) if f.endswith('.xlsx')]
        
        print(f"\n📋 Files available in backup:")
        for file in files_available:
            print(f"   📄 {file}")
        
        print("\nChoose files to restore (comma-separated, or 'all' for all files):")
        file_choice = input("Files: ").strip()
        
        files_to_restore = []
        if file_choice.lower() == 'all':
            files_to_restore = files_available
        else:
            files_to_restore = [f.strip() for f in file_choice.split(',')]
        
        # Restore selected files
        restored_count = 0
        for file_name in files_to_restore:
            source_path = os.path.join(backup_path, file_name)
            if os.path.exists(source_path):
                shutil.copy2(source_path, file_name)
                print(f"✅ Restored: {file_name}")
                restored_count += 1
            else:
                print(f"❌ File not found in backup: {file_name}")
        
        print(f"\n🔄 RESTORE COMPLETE:")
        print(f"   📄 Files restored: {restored_count}")
        print(f"   📁 From backup: {backup_name}")
        
    except Exception as e:
        print(f"❌ Restore failed: {e}")

def export_publication_data():
    """Export publication data to multiple formats for additional backup"""
    
    print("📤 EXPORT PUBLICATION DATA")
    print("=" * 40)
    
    try:
        # Try to load the corrected data
        if os.path.exists("data_ORCIDs_CORRECTED.xlsx"):
            df = pd.read_excel("data_ORCIDs_CORRECTED.xlsx")
            
            # Create export directory
            export_dir = "data_exports"
            os.makedirs(export_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Export to multiple formats
            formats = {
                'csv': f"{export_dir}/orcid_data_{timestamp}.csv",
                'json': f"{export_dir}/orcid_data_{timestamp}.json",
                'xlsx': f"{export_dir}/orcid_data_{timestamp}.xlsx"
            }
            
            # Export main data
            df.to_csv(formats['csv'], index=False)
            df.to_excel(formats['xlsx'], index=False)
            
            # For JSON, handle the publication_details column
            json_data = df.to_dict('records')
            for record in json_data:
                if 'publication_details' in record and pd.notna(record['publication_details']):
                    try:
                        details_str = str(record['publication_details']).strip()
                        if details_str and details_str != 'nan' and details_str != 'None':
                            record['publication_details'] = json.loads(details_str)
                        else:
                            record['publication_details'] = []
                    except:
                        record['publication_details'] = []
            
            with open(formats['json'], 'w') as f:
                json.dump(json_data, f, indent=2)
            
            print("✅ Data exported to multiple formats:")
            for fmt, path in formats.items():
                print(f"   📄 {path}")
            
            return formats
            
        else:
            print("❌ data_ORCIDs_CORRECTED.xlsx not found")
            return None
            
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return None

def backup_menu():
    """Interactive backup menu"""
    
    print("\n💾 ORCID DATA BACKUP MANAGEMENT")
    print("=" * 50)
    print("1. Create new backup")
    print("2. List available backups") 
    print("3. Restore from backup")
    print("4. Export data to multiple formats")
    print("5. Exit")
    
    choice = input("\nChoose option (1-5): ").strip()
    
    if choice == "1":
        create_data_backup()
    elif choice == "2":
        list_available_backups()
    elif choice == "3":
        restore_from_backup()
    elif choice == "4":
        export_publication_data()
    elif choice == "5":
        print("👋 Goodbye!")
        return
    else:
        print("❌ Invalid choice")
    
    # Return to menu
    input("\nPress Enter to continue...")
    backup_menu()

if __name__ == "__main__":
    backup_menu()