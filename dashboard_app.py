# dashboard_app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import logging
import json
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="ScienceBase - Research Analytics",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
        font-family: 'Arial', sans-serif;
    }
    
    .logo {
        font-size: 2.5rem;
        font-weight: bold;
        color: #ff6b6b;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .subheader {
        font-size: 1.5rem;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        border-left: 5px solid #667eea;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    .footer {
        text-align: center;
        padding: 1rem;
        margin-top: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        font-size: 0.9rem;
    }
    
    .filter-section {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    .chart-container {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1.5rem;
    }
    
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .validation-card {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 5px solid #ffc107;
    }
    
    .data-card {
        background: linear-gradient(135deg, #a5d6a7 0%, #66bb6a 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 5px solid #2e7d32;
        color: white;
    }
    
    .data-filter-card {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 5px solid #2196f3;
    }
    
    .data-badge {
        background: linear-gradient(135deg, #66bb6a 0%, #2e7d32 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin: 0.2rem;
    }
    
    .copyright {
        font-size: 0.8rem;
        color: #e0e0e0;
        margin-top: 0.5rem;
    }
    
    .publication-details {
        background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 5px solid #ff9800;
    }
</style>
""", unsafe_allow_html=True)

def clean_text(text):
    """Clean and normalize text for shared publication detection"""
    if pd.isna(text) or text is None:
        return ""
    
    text = str(text).lower().strip()
    # Remove extra spaces, special characters, and normalize
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    return text

def clean_doi(doi):
    """Clean and normalize DOI for shared publication detection"""
    if pd.isna(doi) or doi is None or doi == '':
        return ""
    
    doi = str(doi).lower().strip()
    # Remove common DOI prefixes and URLs
    doi = re.sub(r'^https?://doi\.org/', '', doi)
    doi = re.sub(r'^doi:', '', doi)
    doi = re.sub(r'^\s*', '', doi)
    doi = re.sub(r'\s*$', '', doi)
    return doi

def count_unique_publications(publication_df):
    """Count unique publications by removing DOI and title shared publications"""
    if publication_df.empty:
        return 0, 0, pd.DataFrame()
    
    try:
        # Create a copy to avoid modifying original data
        df = publication_df.copy()
        
        # Clean the data for shared publication detection
        df['doi_clean'] = df['doi'].apply(clean_doi)
        df['title_clean'] = df['title'].apply(clean_text)
        df['journal_clean'] = df['journal'].apply(clean_text)
        
        # Fill NaN years with empty string
        df['year_clean'] = df['year'].fillna('').astype(str)
        
        # Step 1: Remove shared publications by DOI (most reliable)
        df_no_doi_shared = df.drop_duplicates(subset=['doi_clean'], keep='first')
        doi_shared_removed = len(df) - len(df_no_doi_shared)
        
        # Step 2: From remaining, remove shared publications by title + journal + year
        # Only consider titles that are not empty or too short
        valid_titles = df_no_doi_shared[
            (df_no_doi_shared['title_clean'].str.len() > 10) &
            (df_no_doi_shared['title_clean'] != 'unknown title') &
            (df_no_doi_shared['title_clean'] != '')
        ]
        
        # Remove shared publications based on title + journal + year combination
        unique_publications = valid_titles.drop_duplicates(
            subset=['title_clean', 'journal_clean', 'year_clean'], 
            keep='first'
        )
        
        # Count publications that were removed by title deduplication
        title_shared_removed = len(valid_titles) - len(unique_publications)
        
        # Total unique publications
        total_unique = len(unique_publications)
        total_shared_removed = doi_shared_removed + title_shared_removed
        
        logger.info(f"Unique publications: {total_unique} (DOI shared: {doi_shared_removed}, Title shared: {title_shared_removed})")
        
        return total_unique, total_shared_removed, unique_publications
        
    except Exception as e:
        logger.error(f"Error counting unique publications: {e}")
        # Fallback: simple unique count by DOI only
        try:
            unique_dois = df['doi_clean'][df['doi_clean'] != ''].nunique()
            return unique_dois, len(df) - unique_dois, pd.DataFrame()
        except:
            return len(df), 0, pd.DataFrame()

def get_orcid_data():
    """Load ORCID data ONLY from data_ORCIDs_CORRECTED.xlsx"""
    try:
        orcid_df = pd.read_excel("data_ORCIDs_CORRECTED.xlsx")
        logger.info(f"Successfully loaded data from data_ORCIDs_CORRECTED.xlsx with {len(orcid_df)} records")
        return orcid_df
    except Exception as e:
        logger.error(f"Error loading data_ORCIDs_CORRECTED.xlsx: {e}")
        st.error("❌ data_ORCIDs_CORRECTED.xlsx not found or cannot be loaded. Please ensure the file exists.")
        return pd.DataFrame()

def get_publication_details():
    """Load publication details ONLY from data_ORCIDs_CORRECTED.xlsx"""
    try:
        # Try to load from the Publication_Details sheet
        publication_df = pd.read_excel("data_ORCIDs_CORRECTED.xlsx", sheet_name='Publication_Details')
        logger.info(f"Successfully loaded publication details with {len(publication_df)} records")
        return publication_df
    except Exception as e:
        logger.warning(f"Could not load publication details sheet: {e}")
        # Try to extract from publication_details column in main sheet
        try:
            orcid_df = get_orcid_data()
            if not orcid_df.empty and 'publication_details' in orcid_df.columns:
                all_publications = []
                for index, row in orcid_df.iterrows():
                    if row['orcid_valid'] and pd.notna(row['publication_details']):
                        try:
                            publication_details_str = str(row['publication_details']).strip()
                            if publication_details_str and publication_details_str != 'nan' and publication_details_str != 'None':
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
                        except json.JSONDecodeError:
                            continue
                publication_df = pd.DataFrame(all_publications)
                logger.info(f"Extracted {len(publication_df)} publication details from main sheet")
                return publication_df
        except Exception as e2:
            logger.error(f"Error extracting publication details: {e2}")
    return pd.DataFrame()

def get_filtered_orcid_data(universities, colleges, departments, researchers, data_filter):
    """Get filtered ORCID data from data_ORCIDs_CORRECTED.xlsx with multiple selection support"""
    try:
        orcid_df = get_orcid_data()
        if orcid_df.empty:
            return pd.DataFrame()
        
        # Apply filters
        filtered_df = orcid_df.copy()
        
        # University filter (multiple selection)
        if "All" not in universities and universities:
            filtered_df = filtered_df[filtered_df['university'].isin(universities)]
            
        # College filter (multiple selection)
        if "All" not in colleges and colleges:
            filtered_df = filtered_df[filtered_df['college'].isin(colleges)]
            
        # Department filter (multiple selection)
        if "All" not in departments and departments:
            filtered_df = filtered_df[filtered_df['department'].isin(departments)]
            
        # Researcher filter (multiple selection)
        if "All" not in researchers and researchers:
            filtered_df = filtered_df[filtered_df['name'].isin(researchers)]
        
        # Apply data filter
        if data_filter == "Valid ORCID Only":
            filtered_df = filtered_df[filtered_df['orcid_valid'] == True]
        elif data_filter == "With Publications":
            filtered_df = filtered_df[filtered_df['publications_count'] > 0]
        elif data_filter == "High Publication Count (10+)":
            filtered_df = filtered_df[filtered_df['publications_count'] >= 10]
        
        return filtered_df
        
    except Exception as e:
        logger.error(f"Error filtering ORCID data: {str(e)}")
        return pd.DataFrame()

def get_filtered_publication_details(universities, colleges, departments, researchers, data_filter, year_range):
    """Get filtered publication details from data_ORCIDs_CORRECTED.xlsx with multiple selection support"""
    try:
        publication_df = get_publication_details()
        if publication_df.empty:
            return pd.DataFrame()
        
        # Apply filters
        filtered_df = publication_df.copy()
        
        # University filter (multiple selection)
        if "All" not in universities and universities:
            filtered_df = filtered_df[filtered_df['university'].isin(universities)]
            
        # College filter (multiple selection)
        if "All" not in colleges and colleges:
            filtered_df = filtered_df[filtered_df['college'].isin(colleges)]
            
        # Department filter (multiple selection)
        if "All" not in departments and departments:
            filtered_df = filtered_df[filtered_df['department'].isin(departments)]
            
        # Researcher filter (multiple selection)
        if "All" not in researchers and researchers:
            filtered_df = filtered_df[filtered_df['researcher_name'].isin(researchers)]
        
        # Apply year range filter
        if year_range[0] is not None and year_range[1] is not None:
            # Convert year column to numeric, handling errors
            filtered_df['year_numeric'] = pd.to_numeric(filtered_df['year'], errors='coerce')
            filtered_df = filtered_df[
                (filtered_df['year_numeric'] >= year_range[0]) & 
                (filtered_df['year_numeric'] <= year_range[1])
            ]
        
        # Apply data filter based on researcher data
        orcid_data = get_orcid_data()
        if not orcid_data.empty:
            if data_filter == "Valid ORCID Only":
                valid_researchers = orcid_data[orcid_data['orcid_valid'] == True]['name'].tolist()
                filtered_df = filtered_df[filtered_df['researcher_name'].isin(valid_researchers)]
            elif data_filter == "With Publications":
                researchers_with_pubs = orcid_data[orcid_data['publications_count'] > 0]['name'].tolist()
                filtered_df = filtered_df[filtered_df['researcher_name'].isin(researchers_with_pubs)]
            elif data_filter == "High Publication Count (10+)":
                high_pub_researchers = orcid_data[orcid_data['publications_count'] >= 10]['name'].tolist()
                filtered_df = filtered_df[filtered_df['researcher_name'].isin(high_pub_researchers)]
        
        return filtered_df
        
    except Exception as e:
        logger.error(f"Error filtering publication details: {str(e)}")
        return pd.DataFrame()

def get_researcher_metrics(universities, colleges, departments, researchers, data_filter):
    """Calculate metrics based on filtered data from data_ORCIDs_CORRECTED.xlsx"""
    filtered_df = get_filtered_orcid_data(universities, colleges, departments, researchers, data_filter)
    
    if filtered_df.empty:
        return pd.DataFrame(), {}
    
    # Calculate metrics per researcher
    researcher_metrics = filtered_df[['name', 'department', 'college', 'university', 'publications_count']].copy()
    researcher_metrics = researcher_metrics.rename(columns={
        'publications_count': 'publications'
    })
    
    # Create totals dictionary
    totals = {
        'Total Publications': researcher_metrics['publications'].sum(),
        'Total Researchers': len(researcher_metrics),
        'Average Publications': researcher_metrics['publications'].mean() if len(researcher_metrics) > 0 else 0,
        'Valid ORCIDs': filtered_df['orcid_valid'].sum() if 'orcid_valid' in filtered_df.columns else 0
    }
    
    return researcher_metrics, totals

def get_filtered_performance_metrics(universities, colleges, departments, researchers, data_filter, year_range):
    """Get comprehensive performance metrics for filtered data that respects year range"""
    # Get filtered researcher data
    filtered_researchers = get_filtered_orcid_data(universities, colleges, departments, researchers, data_filter)
    
    # Get filtered publication details with year range
    filtered_publications = get_filtered_publication_details(
        universities, colleges, departments, researchers, data_filter, year_range
    )
    
    if filtered_researchers.empty:
        return {
            'total_publications': 0,
            'unique_publications': 0,
            'total_researchers': 0,
            'researchers_with_publications': 0,
            'average_publications': 0,
            'data_quality': 0,
            'shared_publications_removed': 0,
            'publication_rate': 0
        }
    
    # Calculate unique publications for filtered data
    unique_publications, shared_removed, _ = count_unique_publications(filtered_publications)
    
    # Calculate publications count based on year-filtered publications
    # Group publications by researcher and count
    if not filtered_publications.empty:
        researcher_publication_counts = filtered_publications.groupby('researcher_name').size().reset_index(name='filtered_publications_count')
        # Merge with filtered researchers to get the publication counts based on year range
        filtered_researchers_with_counts = filtered_researchers.merge(
            researcher_publication_counts, 
            left_on='name', 
            right_on='researcher_name', 
            how='left'
        )
        # Fill NaN values with 0 for researchers with no publications in the year range
        filtered_researchers_with_counts['filtered_publications_count'] = filtered_researchers_with_counts['filtered_publications_count'].fillna(0)
        
        # Use the year-filtered publication counts
        total_publications = filtered_researchers_with_counts['filtered_publications_count'].sum()
        total_researchers = len(filtered_researchers_with_counts)
        researchers_with_publications = len(filtered_researchers_with_counts[filtered_researchers_with_counts['filtered_publications_count'] > 0])
        average_publications = total_publications / total_researchers if total_researchers > 0 else 0
        publication_rate = (researchers_with_publications / total_researchers) * 100 if total_researchers > 0 else 0
    else:
        # If no publications in the year range, set all to 0
        total_publications = 0
        total_researchers = len(filtered_researchers)
        researchers_with_publications = 0
        average_publications = 0
        publication_rate = 0
    
    # Calculate data quality (percentage of valid ORCIDs)
    if 'orcid_valid' in filtered_researchers.columns:
        valid_count = filtered_researchers['orcid_valid'].sum()
        data_quality = (valid_count / total_researchers) * 100 if total_researchers > 0 else 0
    else:
        data_quality = 0
    
    return {
        'total_publications': total_publications,
        'unique_publications': unique_publications,
        'total_researchers': total_researchers,
        'researchers_with_publications': researchers_with_publications,
        'average_publications': average_publications,
        'data_quality': data_quality,
        'shared_publications_removed': shared_removed,
        'publication_rate': publication_rate
    }

def get_college_performance_over_years(universities, colleges, departments, researchers, data_filter, year_range):
    """Get college performance data over years"""
    filtered_publications = get_filtered_publication_details(
        universities, colleges, departments, researchers, data_filter, year_range
    )
    
    if filtered_publications.empty:
        return pd.DataFrame()
    
    # Convert year to numeric and filter out invalid years
    filtered_publications['year_numeric'] = pd.to_numeric(filtered_publications['year'], errors='coerce')
    filtered_publications = filtered_publications[filtered_publications['year_numeric'].notna()]
    
    # Group by college and year, count publications
    college_performance = filtered_publications.groupby(['college', 'year_numeric']).size().reset_index(name='publications')
    college_performance = college_performance.sort_values(['college', 'year_numeric'])
    
    return college_performance

def get_department_performance_over_years(universities, colleges, departments, researchers, data_filter, year_range):
    """Get department performance data over years"""
    filtered_publications = get_filtered_publication_details(
        universities, colleges, departments, researchers, data_filter, year_range
    )
    
    if filtered_publications.empty:
        return pd.DataFrame()
    
    # Convert year to numeric and filter out invalid years
    filtered_publications['year_numeric'] = pd.to_numeric(filtered_publications['year'], errors='coerce')
    filtered_publications = filtered_publications[filtered_publications['year_numeric'].notna()]
    
    # Group by department and year, count publications
    department_performance = filtered_publications.groupby(['department', 'year_numeric']).size().reset_index(name='publications')
    department_performance = department_performance.sort_values(['department', 'year_numeric'])
    
    return department_performance

def main():
    # Header Section with Logo and Branding
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="logo">🔬 ScienceBase</div>', unsafe_allow_html=True)
        st.markdown('<div class="main-header">Research Analytics Dashboard</div>', unsafe_allow_html=True)
        st.markdown('<div class="subheader">ORCID Research Profiles & Publication Analytics</div>', unsafe_allow_html=True)
    
    # Data Overview Section
    st.markdown("### 📊 Research Data Overview")
    
    orcid_data = get_orcid_data()
    publication_details = get_publication_details()
    
    if not orcid_data.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="data-card">', unsafe_allow_html=True)
            total_researchers = len(orcid_data)
            st.metric("Total Researchers", f"{total_researchers:,}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="data-card">', unsafe_allow_html=True)
            # Handle case where orcid_valid column might not exist
            if 'orcid_valid' in orcid_data.columns:
                valid_orcids = orcid_data[orcid_data['orcid_valid'] == True]
            else:
                valid_orcids = orcid_data[orcid_data['orcid'].notna()]
            valid_count = len(valid_orcids)
            st.metric("Valid Profiles", f"{valid_count:,}")
            st.metric("Validation Rate", f"{(valid_count/total_researchers)*100:.1f}%")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="data-card">', unsafe_allow_html=True)
            total_publications = orcid_data['publications_count'].sum() if 'publications_count' in orcid_data.columns else 0
            st.metric("Total Publications", f"{total_publications:,}")
            avg_pubs = total_publications / total_researchers if total_researchers > 0 else 0
            st.metric("Avg Publications", f"{avg_pubs:.1f}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="data-card">', unsafe_allow_html=True)
            researchers_with_pubs = len(orcid_data[orcid_data['publications_count'] > 0]) if 'publications_count' in orcid_data.columns else 0
            st.metric("Researchers with Publications", f"{researchers_with_pubs:,}")
            pub_rate = (researchers_with_pubs / total_researchers) * 100 if total_researchers > 0 else 0
            st.metric("Publication Rate", f"{pub_rate:.1f}%")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Publication Details Overview
        if not publication_details.empty:
            total_publication_records = len(publication_details)
            unique_publications, shared_removed, _ = count_unique_publications(publication_details)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="publication-details">', unsafe_allow_html=True)
                st.metric("Total Publication Records", f"{total_publication_records:,}")
                st.metric("Unique Publications", f"{unique_publications:,}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="publication-details">', unsafe_allow_html=True)
                publications_with_doi = len(publication_details[publication_details['doi'].notna() & (publication_details['doi'] != '')])
                doi_percentage = (publications_with_doi / total_publication_records * 100) if total_publication_records > 0 else 0
                
                # Calculate shared publication rate
                shared_rate = (shared_removed / total_publication_records * 100) if total_publication_records > 0 else 0
                
                st.metric("Publications with DOI", f"{publications_with_doi:,}")
                st.metric("DOI Coverage", f"{doi_percentage:.1f}%")
                st.metric("Shared Publications Removed", f"{shared_removed:,}")
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.error("❌ No research data found. Please ensure data_ORCIDs_CORRECTED.xlsx exists in the current directory.")
        return
    
    # Sidebar filters for data
    st.sidebar.markdown("""
    <div style='background: linear-gradient(135deg, #66bb6a 0%, #2e7d32 100%); 
                padding: 1rem; 
                border-radius: 10px; 
                color: white; 
                text-align: center;
                margin-bottom: 1rem;'>
        <h3>🔬 Data Filters</h3>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        # University filter - MULTIPLE SELECTION
        st.sidebar.markdown('<div class="filter-section">', unsafe_allow_html=True)
        university_options = ["All"] + sorted(orcid_data['university'].unique().tolist())
        selected_universities = st.sidebar.multiselect(
            "🏛️ Universities", 
            university_options,
            default=["All"],
            help="Select one or more universities"
        )
        # If "All" is selected with other options, keep only "All"
        if "All" in selected_universities and len(selected_universities) > 1:
            selected_universities = ["All"]
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
        
        # College filter - MULTIPLE SELECTION
        st.sidebar.markdown('<div class="filter-section">', unsafe_allow_html=True)
        if "All" not in selected_universities and selected_universities:
            college_options = ["All"] + sorted(orcid_data[orcid_data['university'].isin(selected_universities)]['college'].unique().tolist())
        else:
            college_options = ["All"] + sorted(orcid_data['college'].unique().tolist())
        
        selected_colleges = st.sidebar.multiselect(
            "🎓 Colleges", 
            college_options,
            default=["All"],
            help="Select one or more colleges"
        )
        # If "All" is selected with other options, keep only "All"
        if "All" in selected_colleges and len(selected_colleges) > 1:
            selected_colleges = ["All"]
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
        
        # Department filter - MULTIPLE SELECTION
        st.sidebar.markdown('<div class="filter-section">', unsafe_allow_html=True)
        if "All" not in selected_colleges and selected_colleges:
            department_options = ["All"] + sorted(orcid_data[orcid_data['college'].isin(selected_colleges)]['department'].unique().tolist())
        else:
            department_options = ["All"] + sorted(orcid_data['department'].unique().tolist())
        
        selected_departments = st.sidebar.multiselect(
            "📚 Departments", 
            department_options,
            default=["All"],
            help="Select one or more departments"
        )
        # If "All" is selected with other options, keep only "All"
        if "All" in selected_departments and len(selected_departments) > 1:
            selected_departments = ["All"]
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
        
        # Researcher filter - MULTIPLE SELECTION
        st.sidebar.markdown('<div class="filter-section">', unsafe_allow_html=True)
        researcher_options = ["All"]
        
        if "All" not in selected_departments and selected_departments:
            filtered_researchers = orcid_data[orcid_data['department'].isin(selected_departments)]
            if "All" not in selected_colleges and selected_colleges:
                filtered_researchers = filtered_researchers[filtered_researchers['college'].isin(selected_colleges)]
            if "All" not in selected_universities and selected_universities:
                filtered_researchers = filtered_researchers[filtered_researchers['university'].isin(selected_universities)]
            researcher_options += sorted(filtered_researchers['name'].unique().tolist())
        else:
            researcher_options += sorted(orcid_data['name'].unique().tolist())
        
        selected_researchers = st.sidebar.multiselect(
            "👨‍🔬 Researchers", 
            researcher_options,
            default=["All"],
            help="Select one or more researchers"
        )
        # If "All" is selected with other options, keep only "All"
        if "All" in selected_researchers and len(selected_researchers) > 1:
            selected_researchers = ["All"]
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
        
        # Year Range filter
        st.sidebar.markdown('<div class="filter-section">', unsafe_allow_html=True)
        st.sidebar.markdown("**📅 Publication Year Range**")
        
        # Get available years from publication data
        publication_df = get_publication_details()
        if not publication_df.empty and 'year' in publication_df.columns:
            # Convert to numeric and remove NaN values
            years = pd.to_numeric(publication_df['year'], errors='coerce')
            years = years.dropna().astype(int)
            if len(years) > 0:
                min_year = int(years.min())
                max_year = int(years.max())
            else:
                min_year = 2000
                max_year = datetime.now().year
        else:
            min_year = 2000
            max_year = datetime.now().year
        
        year_range = st.sidebar.slider(
            "Select year range",
            min_value=min_year,
            max_value=max_year,
            value=(min_year, max_year),
            help="Filter publications by publication year"
        )
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
        
        # Data Status Filter
        st.sidebar.markdown('<div class="data-filter-card">', unsafe_allow_html=True)
        data_filters = ["All Researchers", "Valid ORCID Only", "With Publications", "High Publication Count (10+)"]
        selected_data_filter = st.sidebar.selectbox("📊 Data Status", data_filters)
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
        
    except Exception as e:
        st.sidebar.error(f"Error loading filter data: {str(e)}")
        selected_universities = selected_colleges = selected_departments = selected_researchers = ["All"]
        selected_data_filter = "All Researchers"
        year_range = (2000, datetime.now().year)
    
    # Active filters summary
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📋 Active Filters")
    st.sidebar.write(f"**Universities:** {', '.join(selected_universities) if selected_universities else 'All'}")
    st.sidebar.write(f"**Colleges:** {', '.join(selected_colleges) if selected_colleges else 'All'}")
    st.sidebar.write(f"**Departments:** {', '.join(selected_departments) if selected_departments else 'All'}")
    st.sidebar.write(f"**Researchers:** {', '.join(selected_researchers) if selected_researchers else 'All'}")
    st.sidebar.write(f"**Year Range:** {year_range[0]} - {year_range[1]}")
    st.sidebar.write(f"**Data Status:** {selected_data_filter}")
    
    # Refresh button
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    # Get filtered data
    researcher_metrics, totals = get_researcher_metrics(
        selected_universities, selected_colleges, 
        selected_departments, selected_researchers, 
        selected_data_filter
    )
    
    # Get filtered publication details with year range
    filtered_publications = get_filtered_publication_details(
        selected_universities, selected_colleges,
        selected_departments, selected_researchers,
        selected_data_filter, year_range
    )
    
    # Calculate unique publications for filtered data
    unique_filtered_publications, shared_removed, unique_publications_df = count_unique_publications(filtered_publications)
    
    # Get comprehensive filtered performance metrics (NOW RESPECTS YEAR RANGE)
    performance_metrics = get_filtered_performance_metrics(
        selected_universities, selected_colleges,
        selected_departments, selected_researchers,
        selected_data_filter, year_range
    )
    
    # Get college and department performance data
    college_performance = get_college_performance_over_years(
        selected_universities, selected_colleges,
        selected_departments, selected_researchers,
        selected_data_filter, year_range
    )
    
    department_performance = get_department_performance_over_years(
        selected_universities, selected_colleges,
        selected_departments, selected_researchers,
        selected_data_filter, year_range
    )
    
    # Main dashboard content
    if not researcher_metrics.empty:
        # Top metrics row - NOW ALL METRICS RESPECT YEAR RANGE FILTER
        st.markdown("### 📈 Filtered Research Performance")
        
        # Create 5 columns for the metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Total Publications", f"{performance_metrics['total_publications']:,}")
            st.metric("Unique Publications", f"{performance_metrics['unique_publications']:,}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Total Researchers", f"{performance_metrics['total_researchers']:,}")
            st.metric("Researchers with Publications", f"{performance_metrics['researchers_with_publications']:,}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Avg Publications", f"{performance_metrics['average_publications']:.1f}")
            st.metric("Publication Rate", f"{performance_metrics['publication_rate']:.1f}%")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Data Quality", f"{performance_metrics['data_quality']:.1f}%")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col5:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Shared Publications Removed", f"{performance_metrics['shared_publications_removed']:,}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Show shared publication info if applicable
        if shared_removed > 0:
            st.info(f"🔍 **Shared Publication Detection:** Removed {shared_removed:,} shared publications, showing {unique_filtered_publications:,} unique publications out of {len(filtered_publications):,} total records")
        
        # NEW: College and Department Performance Over Years Charts
        if not college_performance.empty or not department_performance.empty:
            st.markdown("### 📈 Performance Trends Over Years")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                st.markdown("#### 🏫 College Performance Over Years")
                
                if not college_performance.empty:
                    fig = px.line(
                        college_performance,
                        x='year_numeric',
                        y='publications',
                        color='college',
                        title="College Publication Trends Over Years",
                        markers=True
                    )
                    fig.update_layout(
                        height=400,
                        xaxis_title="Year",
                        yaxis_title="Number of Publications",
                        legend_title="College"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No college performance data available for current filters")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                st.markdown("#### 📚 Department Performance Over Years")
                
                if not department_performance.empty:
                    # Limit to top 10 departments for better visualization
                    top_departments = department_performance.groupby('department')['publications'].sum().nlargest(10).index
                    filtered_department_performance = department_performance[department_performance['department'].isin(top_departments)]
                    
                    fig = px.line(
                        filtered_department_performance,
                        x='year_numeric',
                        y='publications',
                        color='department',
                        title="Top 10 Department Publication Trends Over Years",
                        markers=True
                    )
                    fig.update_layout(
                        height=400,
                        xaxis_title="Year",
                        yaxis_title="Number of Publications",
                        legend_title="Department"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No department performance data available for current filters")
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Analytics Visualizations
        st.markdown("### 📊 Research Analytics")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown("#### 📈 Publication Distribution")
            
            # Publication count distribution - use year-filtered data
            if not filtered_publications.empty:
                # Create researcher metrics based on year-filtered publication counts
                year_filtered_researcher_counts = filtered_publications.groupby('researcher_name').size().reset_index(name='year_filtered_publications')
                researcher_metrics_year_filtered = researcher_metrics.merge(
                    year_filtered_researcher_counts, 
                    left_on='name', 
                    right_on='researcher_name', 
                    how='left'
                )
                researcher_metrics_year_filtered['year_filtered_publications'] = researcher_metrics_year_filtered['year_filtered_publications'].fillna(0)
                
                fig = px.histogram(
                    researcher_metrics_year_filtered, 
                    x='year_filtered_publications',
                    nbins=20,
                    title="Distribution of Publication Counts (Year Filtered)",
                    color_discrete_sequence=['#00A36C']
                )
            else:
                fig = px.histogram(
                    researcher_metrics, 
                    x='publications',
                    nbins=20,
                    title="Distribution of Publication Counts",
                    color_discrete_sequence=['#00A36C']
                )
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown("#### 📊 Publications by Department")
            
            # Top departments by publications - use year-filtered data
            if not filtered_publications.empty:
                dept_publications = filtered_publications.groupby('department').size().reset_index(name='publications')
                dept_publications = dept_publications.sort_values('publications', ascending=False).head(10)
                title = "Top Departments by Publications (Year Filtered)"
            else:
                dept_publications = researcher_metrics.groupby('department')['publications'].sum().reset_index()
                dept_publications = dept_publications.sort_values('publications', ascending=False).head(10)
                title = "Top Departments by Publications"
            
            if not dept_publications.empty:
                fig = px.bar(
                    dept_publications,
                    x='publications',
                    y='department',
                    orientation='h',
                    color='publications',
                    color_continuous_scale='viridis',
                    title=title
                )
                fig.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No department data available for current filters")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Validation Status
        st.markdown("### 🎯 Data Validation Status")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown("#### ✅ Profile Validation Overview")
            
            filtered_data = get_filtered_orcid_data(selected_universities, selected_colleges, 
                                                  selected_departments, selected_researchers, 
                                                  selected_data_filter)
            
            if not filtered_data.empty and 'orcid_valid' in filtered_data.columns:
                validation_counts = filtered_data['orcid_valid'].value_counts()
                fig = px.pie(
                    values=validation_counts.values,
                    names=['Valid Profile' if x else 'Invalid Profile' for x in validation_counts.index],
                    title="Profile Validation Status",
                    color_discrete_sequence=['#00A36C', '#FF6B6B']
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No validation data available for current filters")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown("#### 📋 Department-wise Validation")
            
            filtered_data = get_filtered_orcid_data(selected_universities, selected_colleges, 
                                                  selected_departments, selected_researchers, 
                                                  selected_data_filter)
            
            if not filtered_data.empty and 'orcid_valid' in filtered_data.columns:
                dept_validation = filtered_data.groupby('department').agg({
                    'orcid_valid': ['sum', 'count']
                }).reset_index()
                dept_validation.columns = ['department', 'valid_count', 'total_count']
                dept_validation['invalid_count'] = dept_validation['total_count'] - dept_validation['valid_count']
                dept_validation = dept_validation.head(10)  # Top 10 departments
                
                fig = go.Figure(data=[
                    go.Bar(name='Valid Profile', y=dept_validation['department'], 
                          x=dept_validation['valid_count'], orientation='h', marker_color='#00A36C'),
                    go.Bar(name='Invalid Profile', y=dept_validation['department'], 
                          x=dept_validation['invalid_count'], orientation='h', marker_color='#FF6B6B')
                ])
                fig.update_layout(barmode='stack', height=400, title="Profile Validation by Department")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No validation data available for current filters")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Top Researchers Section - use year-filtered data
        st.markdown("### 🏆 Top Researchers by Publication Count")
        
        # Use year-filtered publication counts for rankings
        if not filtered_publications.empty:
            year_filtered_researcher_counts = filtered_publications.groupby('researcher_name').size().reset_index(name='year_filtered_publications')
            top_researchers = year_filtered_researcher_counts.nlargest(10, 'year_filtered_publications')
            chart_title = "Top 10 Researchers by Publication Count (Year Filtered)"
            publications_column = 'year_filtered_publications'
        else:
            top_researchers = researcher_metrics.nlargest(10, 'publications')
            chart_title = "Top 10 Researchers by Publication Count"
            publications_column = 'publications'
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            if not top_researchers.empty:
                fig = px.bar(
                    top_researchers,
                    x=publications_column,
                    y='researcher_name' if 'researcher_name' in top_researchers.columns else 'name',
                    orientation='h',
                    color=publications_column,
                    color_continuous_scale='viridis',
                    title=chart_title
                )
                fig.update_layout(height=500, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No researcher data available for current filters")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown("#### 🥇 Researcher Rankings")
            
            if not top_researchers.empty:
                for i, (_, researcher) in enumerate(top_researchers.iterrows(), 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    researcher_name = researcher['researcher_name'] if 'researcher_name' in researcher else researcher['name']
                    publications_count = researcher[publications_column]
                    
                    st.markdown(f"""
                    <div style='padding: 0.5rem; margin: 0.2rem 0; background: #f8f9fa; border-radius: 8px;'>
                        <strong>{medal} {researcher_name}</strong><br>
                        <span style='color: #2e7d32; font-weight: bold;'>📄 {publications_count} publications</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No researcher rankings available")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Publication Details Table - Show ALL publications (with shared publications)
        if not filtered_publications.empty:
            st.markdown("### 📖 Publication Details")
            
            # Create display dataframe for publication details (ALL records)
            publication_display_df = filtered_publications.copy()
            
            # Select and rename columns for display
            display_columns = ['researcher_name', 'title', 'journal', 'year', 'doi']
            available_columns = [col for col in display_columns if col in publication_display_df.columns]
            
            publication_display_df = publication_display_df[available_columns]
            
            # Rename columns for better display
            column_rename_map = {
                'researcher_name': 'Researcher Name',
                'title': 'Publication Title',
                'journal': 'Journal/Conference',
                'year': 'Year',
                'doi': 'DOI'
            }
            
            # Only rename columns that exist
            final_rename_map = {k: v for k, v in column_rename_map.items() if k in publication_display_df.columns}
            publication_display_df = publication_display_df.rename(columns=final_rename_map)
            
            # Clean up data
            if 'Year' in publication_display_df.columns:
                publication_display_df['Year'] = publication_display_df['Year'].fillna('N/A')
                # Convert to string and clean up
                publication_display_df['Year'] = publication_display_df['Year'].astype(str).str.replace('.0', '', regex=False)
            
            if 'DOI' in publication_display_df.columns:
                publication_display_df['DOI'] = publication_display_df['DOI'].fillna('No DOI')
                # Truncate long DOIs for better display
                publication_display_df['DOI'] = publication_display_df['DOI'].apply(
                    lambda x: x[:50] + '...' if len(str(x)) > 50 and x != 'No DOI' else x
                )
            
            if 'Publication Title' in publication_display_df.columns:
                publication_display_df['Publication Title'] = publication_display_df['Publication Title'].fillna('Unknown Title')
                # Truncate long titles for better display
                publication_display_df['Publication Title'] = publication_display_df['Publication Title'].apply(
                    lambda x: x[:100] + '...' if len(str(x)) > 100 else x
                )
            
            if 'Journal/Conference' in publication_display_df.columns:
                publication_display_df['Journal/Conference'] = publication_display_df['Journal/Conference'].fillna('Unknown')
                # Truncate long journal names
                publication_display_df['Journal/Conference'] = publication_display_df['Journal/Conference'].apply(
                    lambda x: x[:80] + '...' if len(str(x)) > 80 else x
                )
            
            st.markdown(f"**Showing {len(publication_display_df)} publication records ({unique_filtered_publications} unique publications after shared publication removal)**")
            
            st.markdown('<div class="dataframe">', unsafe_allow_html=True)
            st.dataframe(
                publication_display_df.sort_values('Year', ascending=False),
                use_container_width=True,
                height=400
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Export option for publication details (ALL records)
            pub_csv = publication_display_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Publication Details as CSV",
                data=pub_csv,
                file_name=f"publication_details_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("📖 No publication details available for the selected filters.")
        
        # Detailed Researcher Data Table
        st.markdown("### 📋 Detailed Researcher Data")
        
        filtered_data = get_filtered_orcid_data(selected_universities, selected_colleges, 
                                              selected_departments, selected_researchers, 
                                              selected_data_filter)
        
        if not filtered_data.empty:
            try:
                # Create display dataframe
                display_columns = ['name', 'department', 'college', 'orcid', 'publications_count']
                if 'orcid_valid' in filtered_data.columns:
                    display_columns.append('orcid_valid')
                
                display_df = filtered_data[display_columns].copy()
                
                # Rename for clarity
                column_rename_map = {
                    'name': 'Researcher Name',
                    'department': 'Department',
                    'college': 'College', 
                    'orcid': 'Profile ID',
                    'publications_count': 'Publications',
                    'orcid_valid': 'Profile Valid'
                }
                
                # Only rename columns that exist
                final_rename_map = {k: v for k, v in column_rename_map.items() if k in display_df.columns}
                display_df = display_df.rename(columns=final_rename_map)
                
                # Format Profile Valid column if it exists
                if 'Profile Valid' in display_df.columns:
                    display_df['Profile Valid'] = display_df['Profile Valid'].map({True: '✅ Yes', False: '❌ No'})
                
                st.markdown('<div class="dataframe">', unsafe_allow_html=True)
                st.dataframe(
                    display_df.sort_values('Publications', ascending=False),
                    use_container_width=True,
                    height=400
                )
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Export option
                csv = display_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Research Data as CSV",
                    data=csv,
                    file_name=f"research_analytics_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
            except Exception as e:
                st.error(f"Error preparing detailed data: {str(e)}")
        
    else:
        st.warning("""
        ⚠️ No research data available for the selected filters. 
        
        Please try:
        - Selecting different filter combinations
        - Choosing "All Researchers" in Data Status
        - Ensuring your data file is properly formatted
        """)
    
    # Footer
    st.markdown("""
    <div class="footer">
        <p>🔬 ScienceBase Research Analytics Dashboard | Built with Streamlit</p>
        <div class="copyright">© 2025 Dr. Osamah Alsulimani. All rights reserved.</div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
