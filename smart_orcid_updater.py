# smart_orcid_updater.py
import pandas as pd
import requests
import json
import time
import os
import schedule
from datetime import datetime, timedelta
import hashlib
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('orcid_updater.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ORCIDSmartUpdater:
    def __init__(self, excel_file=None):
        # Prefer explicit parameter, else environment variable ORCID_EXCEL_FILE, else fallback
        self.excel_file = excel_file or os.getenv('ORCID_EXCEL_FILE', 'data_orcids_corrected.xlsx')
        self.backup_dir = "backups"
        self.last_hash_file = "last_file_hash.txt"
        
        # Create backup directory if it doesn't exist
        Path(self.backup_dir).mkdir(exist_ok=True)
        
    def get_file_hash(self, file_path):
        """Calculate MD5 hash of file to detect changes"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            return file_hash
        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
            return None
    
    def save_current_hash(self, file_hash):
        """Save current file hash for future comparison"""
        try:
            with open(self.last_hash_file, 'w') as f:
                f.write(file_hash)
        except Exception as e:
            logger.error(f"Error saving file hash: {e}")
    
    def get_last_hash(self):
        """Get last saved file hash"""
        try:
            if os.path.exists(self.last_hash_file):
                with open(self.last_hash_file, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            logger.error(f"Error reading last file hash: {e}")
        return None
    
    def has_file_changed(self):
        """Check if the Excel file has changed since last update"""
        if not os.path.exists(self.excel_file):
            logger.warning(f"File {self.excel_file} does not exist")
            return False
        
        current_hash = self.get_file_hash(self.excel_file)
        last_hash = self.get_last_hash()
        
        if last_hash is None:
            # First run, save current hash
            if current_hash:
                self.save_current_hash(current_hash)
            return True
        
        return current_hash != last_hash
    
    def create_backup(self):
        """Create a backup of the current Excel file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, f"{timestamp}_{os.path.basename(self.excel_file)}")
            
            df = pd.read_excel(self.excel_file)
            df.to_excel(backup_file, index=False)
            logger.info(f"Backup created: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return False
    
    def test_orcid_validity_with_works(self, orcid_id):
        """Test if an ORCID ID is valid and get publication count with details"""
        if not orcid_id or pd.isna(orcid_id):
            return False, 0, []
        
        # Clean the ORCID ID
        orcid_clean = str(orcid_id).strip()
        
        # Check ORCID format (XXXX-XXXX-XXXX-XXXX)
        import re
        orcid_pattern = r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$'
        if not re.match(orcid_pattern, orcid_clean):
            logger.warning(f"Invalid ORCID format: {orcid_clean}")
            return False, 0, []
        
        # Test API access and get works
        url = f"https://pub.orcid.org/v3.0/{orcid_clean}/works"
        headers = {'Accept': 'application/json'}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                work_groups = data.get('group', [])
                publication_count = len(work_groups)
                
                # Extract publication details
                publication_details = self.extract_publication_details(work_groups)
                
                logger.info(f"ORCID {orcid_clean} valid: {publication_count} publications")
                return True, publication_count, publication_details
                
            elif response.status_code == 404:
                logger.warning(f"ORCID not found: {orcid_clean}")
                return False, 0, []
            else:
                logger.warning(f"ORCID API error {response.status_code} for {orcid_clean}")
                return False, 0, []
                
        except Exception as e:
            logger.error(f"ORCID test failed for {orcid_clean}: {e}")
            return False, 0, []
    
    def extract_publication_details(self, work_groups):
        """Extract DOI, title, and year from ORCID work groups"""
        publication_details = []
        
        for group in work_groups:
            try:
                work_summary = group.get('work-summary', [])
                if not work_summary:
                    continue
                    
                # Take the first work summary (most recent)
                work = work_summary[0]
                
                # Extract title
                title = self.extract_title(work)
                
                # Extract DOI
                doi = self.extract_doi(work)
                
                # Extract year
                year = self.extract_year(work)
                
                # Extract journal/source
                journal = self.extract_journal(work)
                
                # Extract URL
                url = self.extract_url(work)
                
                publication_detail = {
                    'title': title,
                    'doi': doi,
                    'year': year,
                    'journal': journal,
                    'url': url
                }
                
                publication_details.append(publication_detail)
                
            except Exception as e:
                logger.warning(f"Error extracting work details: {e}")
                continue
        
        return publication_details
    
    def extract_title(self, work):
        """Extract title from work"""
        try:
            title_info = work.get('title', {})
            if title_info:
                title_value = title_info.get('title', {})
                if title_value:
                    return title_value.get('value', 'Unknown Title')
        except:
            pass
        return 'Unknown Title'
    
    def extract_doi(self, work):
        """Extract DOI from work external IDs"""
        try:
            external_ids = work.get('external-ids', {})
            if external_ids:
                external_id_list = external_ids.get('external-id', [])
                for ext_id in external_id_list:
                    if ext_id.get('external-id-type') == 'doi':
                        doi_value = ext_id.get('external-id-value', '')
                        # Clean DOI
                        if doi_value:
                            return doi_value.lower().replace('https://doi.org/', '').replace('http://doi.org/', '').strip()
        except:
            pass
        return ''
    
    def extract_year(self, work):
        """Extract publication year from work"""
        try:
            pub_date = work.get('publication-date', {})
            if pub_date:
                year_value = pub_date.get('year', {})
                if year_value:
                    return year_value.get('value', '')
        except:
            pass
        
        # Fallback: try to get from created date
        try:
            created_date = work.get('created-date', {})
            if created_date:
                timestamp = created_date.get('value', 0)
                if timestamp:
                    return pd.to_datetime(timestamp, unit='ms').year
        except:
            pass
        
        return ''
    
    def extract_journal(self, work):
        """Extract journal/source information"""
        try:
            journal_title = work.get('journal-title', '')
            if journal_title:
                return journal_title
            
            # Try to get from source
            source = work.get('source', {})
            if source:
                source_name = source.get('source-name', {})
                if source_name:
                    return source_name.get('value', '')
        except:
            pass
        return ''
    
    def extract_url(self, work):
        """Extract URL from work"""
        try:
            url_info = work.get('url', {})
            if url_info:
                return url_info.get('value', '')
        except:
            pass
        return ''
    
    def update_researcher_data(self, df, index, orcid):
        """Update publication data for a single researcher"""
        try:
            is_valid, pub_count, publication_details = self.test_orcid_validity_with_works(orcid)
            
            if is_valid:
                df.at[index, 'orcid_valid'] = True
                df.at[index, 'publications_count'] = pub_count
                df.at[index, 'works_checked'] = True
                if publication_details:
                    df.at[index, 'publication_details'] = json.dumps(publication_details)
                else:
                    df.at[index, 'publication_details'] = ''
                
                logger.info(f"Updated {df.at[index, 'name']}: {pub_count} publications")
                return True
            else:
                df.at[index, 'orcid_valid'] = False
                df.at[index, 'works_checked'] = True
                df.at[index, 'publication_details'] = ''
                logger.warning(f"Invalid ORCID for {df.at[index, 'name']}: {orcid}")
                return False
                
        except Exception as e:
            try:
                logger.error(f"Error updating data for {df.at[index, 'name']}: {e}")
            except:
                logger.error(f"Error updating data at index {index}: {e}")
            return False
    
    def smart_update(self):
        """Main update function that checks for changes and updates data"""
        logger.info("🔍 Starting smart ORCID update check...")
        
        if not os.path.exists(self.excel_file):
            logger.error(f"File {self.excel_file} not found")
            return False
        
        # Check if file has changed
        if not self.has_file_changed():
            logger.info("No changes detected in Excel file. Checking for ORCID updates...")
            # Even if file hasn't changed, we might want to update publication data
            return self.update_publication_data_only()
        
        logger.info("Changes detected in Excel file. Performing full update...")
        
        # Create backup before making changes
        self.create_backup()
        
        try:
            # Load the Excel file
            df = pd.read_excel(self.excel_file)
            
            # Ensure required columns exist
            required_columns = ['name', 'orcid', 'orcid_valid', 'publications_count', 'works_checked', 'publication_details']
            for col in required_columns:
                if col not in df.columns:
                    if col == 'orcid_valid':
                        df[col] = False
                    elif col == 'publications_count':
                        df[col] = 0
                    elif col == 'works_checked':
                        df[col] = False
                    elif col == 'publication_details':
                        df[col] = ''
            
            updated_count = 0
            total_researchers = len(df)
            
            # Update each researcher's data
            for index, row in df.iterrows():
                name = row.get('name', '')
                orcid = row.get('orcid', '')
                
                logger.info(f"Processing {index+1}/{total_researchers}: {name}")
                
                if pd.isna(orcid) or not str(orcid).strip():
                    logger.warning(f"Missing ORCID for {name}")
                    continue
                
                # Update researcher data
                if self.update_researcher_data(df, index, str(orcid).strip()):
                    updated_count += 1
                
                # Rate limiting to be respectful to ORCID API
                time.sleep(1)
            
            # Save updated data
            df.to_excel(self.excel_file, index=False)
            
            # Update file hash
            current_hash = self.get_file_hash(self.excel_file)
            if current_hash:
                self.save_current_hash(current_hash)
            
            logger.info(f"✅ Update completed: {updated_count}/{total_researchers} researchers updated")
            
            # Generate update report
            self.generate_update_report(df)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during update: {e}")
            return False
    
    def update_publication_data_only(self):
        """Update only publication data without checking for file changes"""
        logger.info("🔄 Updating publication data only...")
        
        try:
            df = pd.read_excel(self.excel_file)
            updated_count = 0
            
            for index, row in df.iterrows():
                if pd.notna(row.get('orcid')) and str(row.get('orcid')).strip():
                    name = row.get('name', '')
                    orcid = str(row.get('orcid')).strip()
                    
                    logger.info(f"Updating publications for {name}")
                    
                    if self.update_researcher_data(df, index, orcid):
                        updated_count += 1
                    
                    # Rate limiting
                    time.sleep(1)
            
            # Save updated data
            df.to_excel(self.excel_file, index=False)
            
            logger.info(f"✅ Publication update completed: {updated_count} researchers updated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating publication data: {e}")
            return False
    
    def generate_update_report(self, df):
        """Generate a summary report of the update"""
        try:
            valid_count = int(df['orcid_valid'].sum()) if 'orcid_valid' in df.columns else 0
            total_publications = int(df['publications_count'].sum()) if 'publications_count' in df.columns else 0
            total_researchers = len(df)
            
            report = f"""
 📊 ORCID UPDATE REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 ============================================
 👥 Total Researchers: {total_researchers}
 ✅ Valid ORCIDs: {valid_count} ({(valid_count/total_researchers*100) if total_researchers else 0:.1f}%)
 📄 Total Publications: {total_publications}
 📈 Average Publications: {(total_publications/total_researchers) if total_researchers else 0:.1f}
 🕒 Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            logger.info(report)
            
            # Save report to file
            report_file = "orcid_update_report.txt"
            with open(report_file, 'w') as f:
                f.write(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return None

def run_scheduled_update():
    """Function to run the scheduled update"""
    logger.info("🕒 Running scheduled ORCID update...")
    updater = ORCIDSmartUpdater()
    updater.smart_update()

def main():
    """Main function with menu options"""
    updater = ORCIDSmartUpdater()
    
    print("🔄 SMART ORCID UPDATER")
    print("=" * 50)
    print("1. Run smart update (check changes + update)")
    print("2. Update publication data only")
    print("3. Check for file changes")
    print("4. Start daily scheduler (2:00 AM)")
    print("5. Run once now")
    
    choice = input("\nChoose option (1-5): ").strip()
    
    if choice == "1":
        updater.smart_update()
    elif choice == "2":
        updater.update_publication_data_only()
    elif choice == "3":
        if updater.has_file_changed():
            print("✅ Changes detected in Excel file")
        else:
            print("ℹ️ No changes detected")
    elif choice == "4":
        print("🕒 Starting daily scheduler (runs at 2:00 AM)...")
        print("Press Ctrl+C to stop the scheduler")
        
        # Schedule daily update at 2:00 AM
        schedule.every().day.at("02:00").do(run_scheduled_update)
        
        # Run immediately first time
        run_scheduled_update()
        
        # Keep the script running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    elif choice == "5":
        run_scheduled_update()
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    # Non-interactive run support:
    # If RUN_SCHEDULED=1 (set in CI/workflow), run scheduled updater and exit (no menu).
    if os.getenv('RUN_SCHEDULED') == '1' or os.getenv('GITHUB_ACTIONS') == 'true':
        run_scheduled_update()
    else:
        main()
