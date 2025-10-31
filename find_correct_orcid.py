import pandas as pd
import requests
import re
from difflib import SequenceMatcher
import time
import json

def find_correct_orcid():
    """Find the correct ORCID ID for researchers and get their publication counts with details"""
    
    print("🔍 FINDING CORRECT ORCID IDs WITH PUBLICATION DETAILS")
    print("=" * 60)
    
    # Load your ORCID data
    try:
        df = pd.read_excel("data_ORCIDs.xlsx")
        print(f"📊 Loaded {len(df)} researchers from data_ORCIDs.xlsx")
        
        # Add new columns for enhanced data
        df['publications_count'] = 0
        df['orcid_valid'] = False
        df['works_checked'] = False
        df['publication_details'] = ''  # JSON string with publication details
        
        # Check each researcher's ORCID
        for index, row in df.iterrows():
            name = row['name']
            orcid = row['orcid']
            
            print(f"\n👤 Researcher: {name}")
            print(f"   📝 Current ORCID: {orcid}")
            
            # Test the ORCID and get publication details
            is_valid, pub_count, publication_details = test_orcid_validity_with_works(orcid)
            
            if is_valid:
                df.at[index, 'orcid_valid'] = True
                df.at[index, 'publications_count'] = pub_count
                df.at[index, 'works_checked'] = True
                if publication_details:
                    df.at[index, 'publication_details'] = json.dumps(publication_details)
                print(f"   ✅ ORCID VALID: {orcid} - {pub_count} publications")
                print(f"   📄 Retrieved {len(publication_details)} publication details")
            else:
                print(f"   ❌ ORCID INVALID: {orcid}")
                print(f"   🔍 Searching for correct ORCID...")
                
                # Try to find correct ORCID
                suggested_orcid, suggested_pub_count, suggested_details = search_orcid_by_name_with_works(name)
                if suggested_orcid:
                    print(f"   ✅ SUGGESTED ORCID: {suggested_orcid} - {suggested_pub_count} publications")
                    # Update the dataframe
                    df.at[index, 'orcid'] = suggested_orcid
                    df.at[index, 'orcid_valid'] = True
                    df.at[index, 'publications_count'] = suggested_pub_count
                    df.at[index, 'works_checked'] = True
                    if suggested_details:
                        df.at[index, 'publication_details'] = json.dumps(suggested_details)
                    print(f"   📄 Retrieved {len(suggested_details)} publication details")
                else:
                    print(f"   ⚠️  No ORCID found for {name}")
            
            # Rate limiting to be respectful to ORCID API
            time.sleep(1)
    
        # Save corrected file with publication counts and details
        corrected_file = "data_ORCIDs_CORRECTED.xlsx"
        df.to_excel(corrected_file, index=False)
        print(f"\n💾 Saved corrected ORCIDs with publication details to: {corrected_file}")
        
        # Generate summary
        valid_count = df['orcid_valid'].sum()
        total_publications = df['publications_count'].sum()
        print(f"\n📊 SUMMARY:")
        print(f"   ✅ Valid ORCIDs: {valid_count}/{len(df)}")
        print(f"   📄 Total Publications: {total_publications}")
        print(f"   📈 Average Publications per Researcher: {total_publications/len(df):.1f}")
        
        # Create a separate sheet with publication details
        create_publications_sheet(df, corrected_file)
        
        return df
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_orcid_validity_with_works(orcid_id):
    """Test if an ORCID ID is valid and get publication count with details"""
    if not orcid_id or pd.isna(orcid_id):
        return False, 0, []
    
    # Clean the ORCID ID
    orcid_clean = str(orcid_id).strip()
    
    # Check ORCID format (XXXX-XXXX-XXXX-XXXX)
    orcid_pattern = r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$'
    if not re.match(orcid_pattern, orcid_clean):
        print(f"   ⚠️  Invalid ORCID format: {orcid_clean}")
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
            publication_details = extract_publication_details(work_groups)
            
            print(f"   ✅ ORCID VALID: Found {publication_count} work groups")
            print(f"   📄 Extracted details for {len(publication_details)} publications")
            return True, publication_count, publication_details
            
        elif response.status_code == 404:
            print(f"   ❌ ORCID NOT FOUND: 404 error")
            return False, 0, []
        else:
            print(f"   ⚠️  ORCID API error: {response.status_code}")
            return False, 0, []
            
    except Exception as e:
        print(f"   ❌ ORCID test failed: {e}")
        return False, 0, []

def extract_publication_details(work_groups):
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
            title = extract_title(work)
            
            # Extract DOI
            doi = extract_doi(work)
            
            # Extract year
            year = extract_year(work)
            
            # Extract journal/source
            journal = extract_journal(work)
            
            # Extract URL
            url = extract_url(work)
            
            publication_detail = {
                'title': title,
                'doi': doi,
                'year': year,
                'journal': journal,
                'url': url
            }
            
            publication_details.append(publication_detail)
            
        except Exception as e:
            print(f"      ⚠️ Error extracting work details: {e}")
            continue
    
    return publication_details

def extract_title(work):
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

def extract_doi(work):
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

def extract_year(work):
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

def extract_journal(work):
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

def extract_url(work):
    """Extract URL from work"""
    try:
        url_info = work.get('url', {})
        if url_info:
            return url_info.get('value', '')
    except:
        pass
    return ''

def search_orcid_by_name_with_works(name):
    """Try to find ORCID ID by researcher name and get publication details"""
    # This is a simplified version - in practice, you'd use ORCID's search API
    # For now, we'll return None and rely on manual correction
    return None, 0, []

def create_publications_sheet(df, excel_file_path):
    """Create a separate sheet with all publication details"""
    try:
        all_publications = []
        
        for index, row in df.iterrows():
            if row['orcid_valid'] and 'publication_details' in row and pd.notna(row['publication_details']):
                try:
                    # Check if publication_details is a string (JSON) before parsing
                    publication_details_str = str(row['publication_details']).strip()
                    
                    # Skip if empty or NaN representation
                    if not publication_details_str or publication_details_str == 'nan' or publication_details_str == 'None':
                        continue
                    
                    # Try to parse JSON
                    publications = json.loads(publication_details_str)
                    
                    for pub in publications:
                        pub_detail = {
                            'researcher_name': row['name'],
                            'orcid': row['orcid'],
                            'department': row.get('department', ''),
                            'college': row.get('college', ''),
                            'university': row.get('university', ''),
                            'title': pub.get('title', ''),
                            'doi': pub.get('doi', ''),
                            'year': pub.get('year', ''),
                            'journal': pub.get('journal', ''),
                            'url': pub.get('url', '')
                        }
                        all_publications.append(pub_detail)
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON decode error for {row['name']}: {e}")
                    continue
                except Exception as e:
                    print(f"⚠️ Error processing publications for {row['name']}: {e}")
                    continue
        
        if all_publications:
            publications_df = pd.DataFrame(all_publications)
            
            # Load existing file and add new sheet
            try:
                with pd.ExcelWriter(excel_file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    publications_df.to_excel(writer, sheet_name='Publication_Details', index=False)
                print(f"💾 Added Publication_Details sheet with {len(publications_df)} publications")
            except Exception as e:
                print(f"⚠️ Error writing to Excel file: {e}")
                # Fallback: create a separate file
                separate_file = "orcid_publication_details.xlsx"
                publications_df.to_excel(separate_file, index=False)
                print(f"💾 Saved publication details to separate file: {separate_file}")
        else:
            print("ℹ️ No publication details to add")
            
    except Exception as e:
        print(f"⚠️ Error creating publications sheet: {e}")

def check_all_orcids_in_file():
    """Check all ORCIDs in your data file and get publication counts with details"""
    print("\n" + "=" * 60)
    print("📋 CHECKING ALL ORCIDs IN DATA FILE WITH PUBLICATION DETAILS")
    print("=" * 60)
    
    try:
        df = pd.read_excel("data_ORCIDs.xlsx")
        
        valid_count = 0
        invalid_count = 0
        total_publications = 0
        all_publication_details = []
        
        for index, row in df.iterrows():
            name = row['name']
            orcid = row['orcid']
            
            print(f"\n{index+1}. {name}")
            print(f"   ORCID: {orcid}")
            
            if pd.isna(orcid) or not str(orcid).strip():
                print("   ❌ MISSING ORCID")
                invalid_count += 1
                continue
            
            is_valid, pub_count, pub_details = test_orcid_validity_with_works(str(orcid).strip())
            
            if is_valid:
                valid_count += 1
                total_publications += pub_count
                all_publication_details.extend(pub_details)
                print(f"   ✅ VALID - {pub_count} publications")
                print(f"   📄 Extracted {len(pub_details)} publication details")
            else:
                invalid_count += 1
                print("   ❌ INVALID")
        
        print(f"\n📊 SUMMARY:")
        print(f"   ✅ Valid ORCIDs: {valid_count}")
        print(f"   ❌ Invalid/Missing ORCIDs: {invalid_count}")
        print(f"   📄 Total Publications: {total_publications}")
        print(f"   📋 Total Publication Details: {len(all_publication_details)}")
        print(f"   📈 Success rate: {valid_count/len(df)*100:.1f}%")
        print(f"   📊 Average Publications: {total_publications/len(df):.1f}")
        
        # Save publication details to a separate file
        if all_publication_details:
            pub_df = pd.DataFrame(all_publication_details)
            pub_file = "orcid_publication_details.xlsx"
            pub_df.to_excel(pub_file, index=False)
            print(f"💾 Saved publication details to: {pub_file}")
        
    except Exception as e:
        print(f"❌ Error checking ORCIDs: {e}")

def generate_orcid_report():
    """Generate a comprehensive ORCID report with publication details"""
    print("\n" + "=" * 60)
    print("📊 GENERATING ORCID COMPREHENSIVE REPORT WITH PUBLICATION DETAILS")
    print("=" * 60)
    
    try:
        # Load the corrected data
        df = pd.read_excel("data_ORCIDs_CORRECTED.xlsx")
        
        # Basic statistics
        total_researchers = len(df)
        valid_orcids = df[df['orcid_valid'] == True]
        total_publications = df['publications_count'].sum()
        
        # Extract publication details for additional stats
        publication_years = []
        dois_found = 0
        titles_found = 0
        
        for index, row in df.iterrows():
            if row['orcid_valid'] and 'publication_details' in row and pd.notna(row['publication_details']):
                try:
                    publication_details_str = str(row['publication_details']).strip()
                    if publication_details_str and publication_details_str != 'nan' and publication_details_str != 'None':
                        publications = json.loads(publication_details_str)
                        for pub in publications:
                            if pub.get('year'):
                                publication_years.append(pub['year'])
                            if pub.get('doi'):
                                dois_found += 1
                            if pub.get('title') and pub.get('title') != 'Unknown Title':
                                titles_found += 1
                except:
                    pass
        
        print(f"👥 Total Researchers: {total_researchers}")
        print(f"✅ Valid ORCIDs: {len(valid_orcids)} ({len(valid_orcids)/total_researchers*100:.1f}%)")
        print(f"📄 Total Publications: {total_publications}")
        print(f"📈 Average Publications per Researcher: {total_publications/total_researchers:.1f}")
        print(f"🔗 DOIs Found: {dois_found}")
        print(f"📝 Titles Found: {titles_found}")
        
        if publication_years:
            print(f"📅 Publication Years Range: {min(publication_years)} - {max(publication_years)}")
        
        # Top researchers by publication count
        top_researchers = df.nlargest(10, 'publications_count')[['name', 'publications_count']]
        print(f"\n🏆 TOP 10 RESEARCHERS BY PUBLICATION COUNT:")
        for _, researcher in top_researchers.iterrows():
            print(f"   {researcher['name']}: {researcher['publications_count']} publications")
        
        # Department statistics
        if 'department' in df.columns:
            dept_stats = df.groupby('department').agg({
                'name': 'count',
                'publications_count': 'sum',
                'orcid_valid': 'sum'
            }).rename(columns={
                'name': 'researcher_count',
                'orcid_valid': 'valid_orcids'
            })
            
            dept_stats['avg_publications'] = dept_stats['publications_count'] / dept_stats['researcher_count']
            dept_stats['valid_percentage'] = dept_stats['valid_orcids'] / dept_stats['researcher_count'] * 100
            
            print(f"\n📊 DEPARTMENT STATISTICS:")
            for dept, stats in dept_stats.iterrows():
                print(f"   {dept}:")
                print(f"     👥 Researchers: {stats['researcher_count']}")
                print(f"     ✅ Valid ORCIDs: {stats['valid_orcids']} ({stats['valid_percentage']:.1f}%)")
                print(f"     📄 Total Publications: {stats['publications_count']}")
                print(f"     📈 Avg Publications: {stats['avg_publications']:.1f}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        return None

def clean_publication_details():
    """Clean the publication_details column in the existing file"""
    try:
        df = pd.read_excel("data_ORCIDs_CORRECTED.xlsx")
        
        # Ensure publication_details column exists
        if 'publication_details' not in df.columns:
            df['publication_details'] = ''
        
        # Clean the column
        cleaned_count = 0
        for index, row in df.iterrows():
            if pd.notna(row['publication_details']):
                # Convert to string and check if it's valid JSON
                details_str = str(row['publication_details']).strip()
                if details_str and details_str != 'nan' and details_str != 'None':
                    try:
                        # Test if it's valid JSON
                        json.loads(details_str)
                        # If valid, keep it as is
                    except json.JSONDecodeError:
                        # If invalid JSON, set to empty
                        df.at[index, 'publication_details'] = ''
                        cleaned_count += 1
                else:
                    # If empty or NaN representation, set to empty
                    df.at[index, 'publication_details'] = ''
                    cleaned_count += 1
            else:
                # If NaN, set to empty
                df.at[index, 'publication_details'] = ''
                cleaned_count += 1
        
        # Save cleaned data
        df.to_excel("data_ORCIDs_CORRECTED.xlsx", index=False)
        print(f"✅ Cleaned {cleaned_count} publication_details entries")
        
    except Exception as e:
        print(f"❌ Error cleaning data: {e}")

if __name__ == "__main__":
    print("🆔 ORCID VALIDATION AND CORRECTION TOOL WITH PUBLICATION DETAILS")
    print("=" * 60)
    
    print("1. Check all ORCIDs in data file (with publication details)")
    print("2. Auto-correct all ORCIDs and get publication details")
    print("3. Generate comprehensive ORCID report")
    print("4. Extract publication details only")
    print("5. Clean publication details data")
    
    choice = input("\nChoose option (1-5): ").strip()
    
    if choice == "1":
        check_all_orcids_in_file()
    elif choice == "2":
        find_correct_orcid()
    elif choice == "3":
        generate_orcid_report()
    elif choice == "4":
        # Extract publication details from existing corrected file
        try:
            df = pd.read_excel("data_ORCIDs_CORRECTED.xlsx")
            create_publications_sheet(df, "data_ORCIDs_CORRECTED.xlsx")
            print("✅ Publication details extracted and saved")
        except Exception as e:
            print(f"❌ Error extracting publication details: {e}")
    elif choice == "5":
        clean_publication_details()
    else:
        print("❌ Invalid choice")