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
        self.excel_file = excel_file or os.getenv('ORCID_EXCEL_FILE', 'data_ORCIDs_CORRECTED.xlsx')
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
            
            # Read all sheets and save to backup
            with pd.ExcelWriter(backup_file, engine='openpyxl') as writer:
                # Read and save all existing sheets
                excel_file = pd.ExcelFile(self.excel_file)
                for sheet_name in excel_file.sheet_names:
                    df_sheet = pd.read_excel(self.excel_file, sheet_name=sheet_name)
                    df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)
            
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
                return True, publication_details
            else:
                df.at[index, 'orcid_valid'] = False
                df.at[index, 'works_checked'] = True
                df.at[index, 'publication_details'] = ''
                logger.warning(f"Invalid ORCID for {df.at[index, 'name']}: {orcid}")
                return False, []
                
        except Exception as e:
            try:
                logger.error(f"Error updating data for {df.at[index, 'name']}: {e}")
            except:
                logger.error(f"Error updating data at index {index}: {e}")
            return False, []
    
    def generate_publication_details_sheet(self, df_main):
        """Generate the Publication_Details sheet from the main dataframe"""
        publication_records = []
        
        for index, row in df_main.iterrows():
            if (pd.notna(row.get('orcid')) and str(row.get('orcid')).strip() and 
                row.get('orcid_valid') and 
                pd.notna(row.get('publication_details')) and 
                row.get('publication_details')):
                
                try:
                    publications = json.loads(row.get('publication_details'))
                    
                    for pub in publications:
                        publication_record = {
                            'researcher_name': row.get('name', ''),
                            'orcid': row.get('orcid', ''),
                            'department': row.get('department', ''),
                            'college': row.get('college', ''),
                            'university': row.get('university', ''),
                            'title': pub.get('title', ''),
                            'doi': pub.get('doi', ''),
                            'year': pub.get('year', ''),
                            'journal': pub.get('journal', ''),
                            'url': pub.get('url', '')
                        }
                        publication_records.append(publication_record)
                        
                except Exception as e:
                    logger.warning(f"Error parsing publication details for {row.get('name')}: {e}")
                    continue
        
        return pd.DataFrame(publication_records)
    
    def save_excel_with_both_sheets(self, df_main, df_publications):
        """Save both main and publication details sheets to Excel"""
        try:
            with pd.ExcelWriter(self.excel_file, engine='openpyxl') as writer:
                # Save main sheet
                df_main.to_excel(writer, sheet_name='Sheet1', index=False)
                
                # Save publication details sheet
                df_publications.to_excel(writer, sheet_name='Publication_Details', index=False)
            
            logger.info(f"Successfully saved both sheets to {self.excel_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving Excel file with both sheets: {e}")
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
            # Load the Excel file with both sheets
            excel_file = pd.ExcelFile(self.excel_file)
            sheet_names = excel_file.sheet_names
            
            # Load main sheet (Sheet1)
            df_main = pd.read_excel(self.excel_file, sheet_name='Sheet1')
            
            # Ensure required columns exist in main sheet
            required_columns = ['name', 'orcid', 'orcid_valid', 'publications_count', 'works_checked', 'publication_details']
            for col in required_columns:
                if col not in df_main.columns:
                    if col == 'orcid_valid':
                        df_main[col] = False
                    elif col == 'publications_count':
                        df_main[col] = 0
                    elif col == 'works_checked':
                        df_main[col] = False
                    elif col == 'publication_details':
                        df_main[col] = ''
            
            updated_count = 0
            total_researchers = len(df_main)
            all_publication_details = []
            
            # Update each researcher's data
            for index, row in df_main.iterrows():
                name = row.get('name', '')
                orcid = row.get('orcid', '')
                
                logger.info(f"Processing {index+1}/{total_researchers}: {name}")
                
                if pd.isna(orcid) or not str(orcid).strip():
                    logger.warning(f"Missing ORCID for {name}")
                    continue
                
                # Update researcher data
                success, publication_details = self.update_researcher_data(df_main, index, str(orcid).strip())
                if success:
                    updated_count += 1
                    # Store publication details for generating the second sheet
                    for pub in publication_details:
                        pub['researcher_name'] = name
                        pub['orcid'] = str(orcid).strip()
                        pub['department'] = row.get('department', '')
                        pub['college'] = row.get('college', '')
                        pub['university'] = row.get('university', '')
                        all_publication_details.append(pub)
                
                # Rate limiting to be respectful to ORCID API
                time.sleep(1)
            
            # Generate publication details sheet
            df_publications = pd.DataFrame(all_publication_details)
            
            # Reorganize columns for publication details sheet
            publication_columns = ['researcher_name', 'orcid', 'department', 'college', 'university', 
                                 'title', 'doi', 'year', 'journal', 'url']
            for col in publication_columns:
                if col not in df_publications.columns:
                    df_publications[col] = ''
            
            df_publications = df_publications[publication_columns]
            
            # Save both sheets to Excel
            self.save_excel_with_both_sheets(df_main, df_publications)
            
            # Update file hash
            current_hash = self.get_file_hash(self.excel_file)
            if current_hash:
                self.save_current_hash(current_hash)
            
            logger.info(f"✅ Update completed: {updated_count}/{total_researchers} researchers updated")
            logger.info(f"📄 Publication details: {len(df_publications)} records")
            
            # Generate update report
            self.generate_update_report(df_main, len(df_publications))
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during update: {e}")
            return False
    
    def update_publication_data_only(self):
        """Update only publication data without checking for file changes"""
        logger.info("🔄 Updating publication data only...")
        
        try:
            # Load both sheets
            df_main = pd.read_excel(self.excel_file, sheet_name='Sheet1')
            
            updated_count = 0
            all_publication_details = []
            
            for index, row in df_main.iterrows():
                if pd.notna(row.get('orcid')) and str(row.get('orcid')).strip():
                    name = row.get('name', '')
                    orcid = str(row.get('orcid')).strip()
                    
                    logger.info(f"Updating publications for {name}")
                    
                    success, publication_details = self.update_researcher_data(df_main, index, orcid)
                    if success:
                        updated_count += 1
                        # Store publication details for generating the second sheet
                        for pub in publication_details:
                            pub['researcher_name'] = name
                            pub['orcid'] = orcid
                            pub['department'] = row.get('department', '')
                            pub['college'] = row.get('college', '')
                            pub['university'] = row.get('university', '')
                            all_publication_details.append(pub)
                    
                    # Rate limiting
                    time.sleep(1)
            
            # Generate publication details sheet
            df_publications = pd.DataFrame(all_publication_details)
            
            # Reorganize columns for publication details sheet
            publication_columns = ['researcher_name', 'orcid', 'department', 'college', 'university', 
                                 'title', 'doi', 'year', 'journal', 'url']
            for col in publication_columns:
                if col not in df_publications.columns:
                    df_publications[col] = ''
            
            df_publications = df_publications[publication_columns]
            
            # Save both sheets to Excel
            self.save_excel_with_both_sheets(df_main, df_publications)
            
            logger.info(f"✅ Publication update completed: {updated_count} researchers updated")
            logger.info(f"📄 Publication details: {len(df_publications)} records")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating publication data: {e}")
            return False
    
    def generate_update_report(self, df_main, publication_count):
        """Generate a summary report of the update"""
        try:
            valid_count = int(df_main['orcid_valid'].sum()) if 'orcid_valid' in df_main.columns else 0
            total_publications = int(df_main['publications_count'].sum()) if 'publications_count' in df_main.columns else 0
            total_researchers = len(df_main)
            
            report = f"""
 📊 ORCID UPDATE REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 ============================================
 👥 Total Researchers: {total_researchers}
 ✅ Valid ORCIDs: {valid_count} ({(valid_count/total_researchers*100) if total_researchers else 0:.1f}%)
 📄 Total Publications: {total_publications}
 📋 Publication Records: {publication_count}
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