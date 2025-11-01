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
    """Clean and normalize text for duplicate detection"""
    if pd.isna(text) or text is None:
        return ""
    
    text = str(text).lower().strip()
    # Remove extra spaces, special characters, and normalize
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
    text = re.sub(r'[^
\w\s]', '', text)  # Remove punctuation
    return text

def clean_doi(doi):
    """Clean and normalize DOI for duplicate detection"""
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
    """Count unique publications by removing DOI and title duplicates"""
    if publication_df.empty:
        return 0, 0, pd.DataFrame()
    
    try:
        # Create a copy to avoid modifying original data
        df = publication_df.copy()
        
        # Clean the data for duplicate detection
        df['doi_clean'] = df['doi'].apply(clean_doi)
        df['title_clean'] = df['title'].apply(clean_text)
        df['journal_clean'] = df['journal'].apply(clean_text)
        
        # Fill NaN years with empty string
        df['year_clean'] = df['year'].fillna('').astype(str)
        
        # Step 1: Remove duplicates by DOI (most reliable)
        df_no_doi_duplicates = df.drop_duplicates(subset=['doi_clean'], keep='first')
        doi_duplicates_removed = len(df) - len(df_no_doi_duplicates)
        
        # Step 2: From remaining, remove duplicates by title + journal + year
        # Only consider titles that are not empty or too short
        valid_titles = df_no_doi_duplicates[
            (df_no_doi_duplicates['title_clean'].str.len() > 10) &
            (df_no_doi_duplicates['title_clean'] != 'unknown title') &
            (df_no_doi_duplicates['title_clean'] != '')
        ]
        
        # Remove duplicates based on title + journal + year combination
        unique_publications = valid_titles.drop_duplicates(
            subset=['title_clean', 'journal_clean', 'year_clean'], 
            keep='first'
        )
        
        # Count publications that were removed by title deduplication
        title_duplicates_removed = len(valid_titles) - len(unique_publications)
        
        # Total unique publications
        total_unique = len(unique_publications)
        total_duplicates_removed = doi_duplicates_removed + title_duplicates_removed
        
        logger.info(f"Unique publications: {total_unique} (DOI duplicates: {doi_duplicates_removed}, Title duplicates: {title_duplicates_removed})")
        
        return total_unique, total_duplicates_removed, unique_publications
        
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

def get_filtered_orcid_data(university, college, department, researcher, data_filter):
    """Get filtered ORCID data from data_ORCIDs_CORRECTED.xlsx"""
    try:
        orcid_df = get_orcid_data()
        if orcid_df.empty:
            return pd.DataFrame()
        
        # Apply filters
        filtered_df = orcid_df.copy()
        
        if university != "All":
            filtered_df = filtered_df[filtered_df['university'] == university]
            
        if college != "All":
            filtered_df = filtered_df[filtered_df['college'] == college]
            
        if department != "All":
            filtered_df = filtered_df[filtered_df['department'] == department]
            
        if researcher != "All":
            filtered_df = filtered_df[filtered_df['name'] == researcher]
        
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

def get_filtered_publication_details(university, college, department, researcher, data_filter, year_range):
    """Get filtered publication details from data_ORCIDs_CORRECTED.xlsx"""
    try:
        publication_df = get_publication_details()
        if publication_df.empty:
            return pd.DataFrame()
        
        # Apply filters
        filtered_df = publication_df.copy()
        
        if university != "All":
            filtered_df = filtered_df[filtered_df['university'] == university]
            
        if college != "All":
            filtered_df = filtered_df[filtered_df['college'] == college]
            
        if department != "All":
            filtered_df = filtered_df[filtered_df['department'] == department]
            
        if researcher != "All":
            filtered_df = filtered_df[filtered_df['researcher_name'] == researcher]
        
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

def get_researcher_metrics(university, college, department, researcher, data_filter):
    """Calculate metrics based on filtered data from data_ORCIDs_CORRECTED.xlsx"""
    filtered_df = get_filtered_orcid_data(university, college, department, researcher, data_filter)
    
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
            unique_publications, duplicates_removed, _ = count_unique_publications(publication_details)
            
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
                
                # Calculate duplication rate
                duplication_rate = (duplicates_removed / total_publication_records * 100) if total_publication_records > 0 else 0
                
                st.metric("Publications with DOI", f"{publications_with_doi:,}")
                st.metric("DOI Coverage", f"{doi_percentage:.1f}%")
                st.metric("Duplicates Removed", f"{duplicates_removed:,}")
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
        # University filter
        st.sidebar.markdown('<div class="filter-section">', unsafe_allow_html=True)
        universities = ["All"] + sorted(orcid_data['university'].unique().tolist())
        selected_university = st.sidebar.selectbox("🏛️ University", universities)
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
        
        # College filter
        st.sidebar.markdown('<div class="filter-section">', unsafe_allow_html=True)
        if selected_university != "All":
            colleges = ["All"] + sorted(orcid_data[orcid_data['university'] == selected_university]['college'].unique().tolist())
        else:
            colleges = ["All"] + sorted(orcid_data['college'].unique().tolist())
        selected_college = st.sidebar.selectbox("🎓 College", colleges)
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
        
        # Department filter
        st.sidebar.markdown('<div class="filter-section">', unsafe_allow_html=True)
        if selected_college != "All":
            departments = ["All"] + sorted(orcid_data[orcid_data['college'] == selected_college]['department'].unique().tolist())
        else:
            departments = ["All"] + sorted(orcid_data['department'].unique().tolist())
        selected_department = st.sidebar.selectbox("📚 Department", departments)
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
        
        # Researcher filter
        st.sidebar.markdown('<div class="filter-section">', unsafe_allow_html=True)
        researcher_options = ["All"]
        if selected_department != "All":
            researcher_options += sorted(orcid_data[
                (orcid_data['department'] == selected_department) &
                (orcid_data['college'] == selected_college) &
                (orcid_data['university'] == selected_university)
            ]['name'].unique().tolist())
        else:
            researcher_options += sorted(orcid_data['name'].unique().tolist())
        
        selected_researcher = st.sidebar.selectbox("👨‍🔬 Researcher", researcher_options)
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
        selected_university = selected_college = selected_department = selected_researcher = "All"
        selected_data_filter = "All Researchers"
        year_range = (2000, datetime.now().year)
    
    # Active filters summary
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📋 Active Filters")
    st.sidebar.write(f"**University:** {selected_university}")
    st.sidebar.write(f"**College:** {selected_college}")
    st.sidebar.write(f"**Department:** {selected_department}")
    st.sidebar.write(f"**Researcher:** {selected_researcher}")
    st.sidebar.write(f"**Year Range:** {year_range[0]} - {year_range[1]}")
    st.sidebar.write(f"**Data Status:** {selected_data_filter}")
    
    # Refresh button
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    # Get filtered data
    researcher_metrics, totals = get_researcher_metrics(
        selected_university, selected_college, 
        selected_department, selected_researcher, 
        selected_data_filter
    )
    
    # Get filtered publication details with year range
    filtered_publications = get_filtered_publication_details(
        selected_university, selected_college,
        selected_department, selected_researcher,
        selected_data_filter, year_range
    )
    
    # Calculate unique publications for filtered data
    unique_filtered_publications, duplicates_removed, unique_publications_df = count_unique_publications(filtered_publications)
    
    # Main dashboard content
    if not researcher_metrics.empty:
        # Top metrics row
        st.markdown("### 📈 Research Performance")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Total Publications", f"{totals.get('Total Publications', 0):,}")
            st.metric("Unique Publications", f"{unique_filtered_publications:,}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Total Researchers", f"{totals.get('Total Researchers', 0):,}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            avg_pubs = totals.get('Average Publications', 0)
            st.metric("Avg Publications", f"{avg_pubs:.1f}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            # Calculate data quality metric
            filtered_data = get_filtered_orcid_data(selected_university, selected_college, 
                                                  selected_department, selected_researcher, 
                                                  selected_data_filter)
            if not filtered_data.empty and 'orcid_valid' in filtered_data.columns:
                valid_percentage = (filtered_data['orcid_valid'].sum() / len(filtered_data) * 100) if len(filtered_data) > 0 else 0
                st.metric("Data Quality", f"{valid_percentage:.1f}%")
            else:
                st.metric("Data Quality", "N/A")
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Show duplication info if applicable
        if duplicates_removed > 0:
            st.info(f"🔍 **Duplicate Detection:** Removed {duplicates_removed:,} duplicate publications, showing {unique_filtered_publications:,} unique publications out of {len(filtered_public[...])}
        
        # Analytics Visualizations
        st.markdown("### 📊 Research Analytics")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown("#### 📈 Publication Distribution")
            
            # Publication count distribution
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
            
            # Top departments by publications
            dept_publications = researcher_metrics.groupby('department')['publications'].sum().reset_index()
            dept_publications = dept_publications.sort_values('publications', ascending=False).head(10)
            
            fig = px.bar(
                dept_publications,
                x='publications',
                y='department',
                orientation='h',
                color='publications',
                color_continuous_scale='viridis',
                title="Top Departments by Publications"
            )
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Validation Status
        st.markdown("### 🎯 Data Validation Status")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown("#### ✅ Profile Validation Overview")
            
            filtered_data = get_filtered_orcid_data(selected_university, selected_college, 
                                                  selected_department, selected_researcher, 
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
            
            filtered_data = get_filtered_orcid_data(selected_university, selected_college, 
                                                  selected_department, selected_researcher, 
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
        
        # Top Researchers Section
        st.markdown("### 🏆 Top Researchers by Publication Count")
        
        top_researchers = researcher_metrics.nlargest(10, 'publications')
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            fig = px.bar(
                top_researchers,
                x='publications',
                y='name',
                orientation='h',
                color='publications',
                color_continuous_scale='viridis',
                title="Top 10 Researchers by Publication Count"
            )
            fig.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown("#### 🥇 Researcher Rankings")
            
            for i, (_, researcher) in enumerate(top_researchers.iterrows(), 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                st.markdown(f""
                <div style='padding: 0.5rem; margin: 0.2rem 0; background: #f8f9fa; border-radius: 8px;'>
                    <strong>{medal} {researcher['name']}</strong><br>
                    <small>📚 {researcher['department']}</small><br>
                    <span style='color: #2e7d32; font-weight: bold;'>📄 {researcher['publications']} publications</span>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Publication Details Table - Show ALL publications (with duplicates)
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
            
            st.markdown(f"**Showing {len(publication_display_df)} publication records ({unique_filtered_publications} unique publications after duplicate removal)**")
            
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
        
        filtered_data = get_filtered_orcid_data(selected_university, selected_college, 
                                              selected_department, selected_researcher, 
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
        st.warning(""
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