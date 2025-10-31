# simple_stats.py
import pandas as pd
import json
import os

def simple_orcid_stats():
    """Super simple statistics display using only data_ORCIDs_CORRECTED.xlsx"""
    try:
        # Load only the corrected database
        df = pd.read_excel("data_ORCIDs_CORRECTED.xlsx")
        
        print("📊 ORCID STATISTICS - data_ORCIDs_CORRECTED.xlsx")
        print("=" * 50)
        
        # Basic counts
        total_researchers = len(df)
        valid_orcids = df['orcid_valid'].sum()
        total_publications = df['publications_count'].sum()
        
        # Count unique publications using DOI
        unique_dois = set()
        for idx, row in df.iterrows():
            if row['orcid_valid'] and pd.notna(row.get('publication_details', '')):
                try:
                    pubs_str = str(row['publication_details']).strip()
                    if pubs_str and pubs_str != 'nan' and pubs_str != 'None':
                        pubs = json.loads(pubs_str)
                        for pub in pubs:
                            doi = pub.get('doi', '')
                            if doi and doi.strip():
                                unique_dois.add(doi.lower().strip())
                except:
                    pass
        
        # Display results
        print(f"👥 Total Researchers: {total_researchers}")
        print(f"✅ Researchers with Valid ORCID: {valid_orcids}")
        print(f"📄 Total Publications Count: {total_publications}")
        print(f"🔍 Unique Publications: {len(unique_dois)}")
        
        # Show file info
        file_size = os.path.getsize("data_ORCIDs_CORRECTED.xlsx") / 1024
        print(f"\n📁 Database: data_ORCIDs_CORRECTED.xlsx ({file_size:.1f} KB)")
        
    except FileNotFoundError:
        print("❌ data_ORCIDs_CORRECTED.xlsx not found")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    simple_orcid_stats()