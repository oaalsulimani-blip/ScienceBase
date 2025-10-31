import os
from datetime import time
from dotenv import load_dotenv

load_dotenv('environment.env')

class Config:
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/scholarly_metrics.db')
    
    # Update Schedule
    UPDATE_TIME = os.getenv('UPDATE_TIME', '02:00')
    
    # API Endpoints
    OPENALEX_API = os.getenv('OPENALEX_API', 'https://api.openalex.org')
    CROSSREF_API = os.getenv('CROSSREF_API', 'https://api.crossref.org')
    PUBMED_API = os.getenv('PUBMED_API', 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils')
    SCOPUS_API_URL = os.getenv('SCOPUS_API_URL', 'https://api.elsevier.com/content')
    WOS_API_URL = os.getenv('WOS_API_URL', 'https://api.clarivate.com/apis/wos')
    
    # API Keys
    SCOPUS_API_KEY = os.getenv('SCOPUS_API_KEY', '')
    SCOPUS_INSTTOKEN = os.getenv('SCOPUS_INSTTOKEN', '')
    WOS_API_KEY = os.getenv('WOS_API_KEY', '')
    
    # File Paths
    ORCID_FILE = "data_ORCIDs.xlsx"
    LOG_FILE = os.getenv('LOG_FILE', 'logs/scholarly_metrics.log')
    
    # ULTIMATE SEARCHER SETTINGS
    # ==========================
    
    # API Settings
    RATE_LIMIT_DELAY = int(os.getenv('RATE_LIMIT_DELAY', '2'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
    
    # Search Limits
    MAX_PUBLICATIONS_PER_RESEARCHER = int(os.getenv('MAX_PUBLICATIONS_PER_RESEARCHER', '100'))
    MAX_PUBMED_RESULTS = int(os.getenv('MAX_PUBMED_RESULTS', '50'))
    MAX_CROSSREF_RESULTS = int(os.getenv('MAX_CROSSREF_RESULTS', '100'))
    MAX_OPENALEX_RESULTS = int(os.getenv('MAX_OPENALEX_RESULTS', '200'))
    
    # Years range
    START_YEAR = int(os.getenv('START_YEAR', '1964'))
    END_YEAR = int(os.getenv('END_YEAR', '2026'))
    
    # Dashboard Settings
    DASHBOARD_PORT = int(os.getenv('DASHBOARD_PORT', '8501'))
    DASHBOARD_HOST = os.getenv('DASHBOARD_HOST', 'localhost')
    
    # User Information
    USER_EMAIL = os.getenv('USER_EMAIL', 'your_email@example.com')
    DEVELOPER_NAME = os.getenv('DEVELOPER_NAME', 'Dr. Osamah Alsulimani')
    
    # Performance
    ENABLE_PARALLEL_PROCESSING = os.getenv('ENABLE_PARALLEL_PROCESSING', 'false').lower() == 'true'
    MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', '3'))
    
    # Data Quality - SIMPLE EXACT MATCH ONLY
    ENABLE_DUPLICATE_REMOVAL = os.getenv('ENABLE_DUPLICATE_REMOVAL', 'true').lower() == 'true'
    MIN_PUBLICATION_YEAR = int(os.getenv('MIN_PUBLICATION_YEAR', '1990'))