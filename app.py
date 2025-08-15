import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import time
import os
import logging
import requests
import urllib.parse
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from news_fetcher3 import get_news_about  # Import our new RSS fetcher
from sentiment_analysis import analyze_sentiment  # Import the sentiment analysis function
from summarizer import generate_overall_summary  # Import the summarizer function
from tts import translate_and_generate_audio  # Import the TTS function
from auth_ui import show_login_form, show_register_form, show_logout_button, get_current_user, require_login, require_admin
from models import log_search  # Import the search logging function
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Professional styling with clean design
st.markdown("""
<style>
    /* Import Professional Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Global Reset and Base Styles */
    .main {
        padding: 1rem 2rem;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-weight: 400;
        line-height: 1.5;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Professional Header */
    .main-header {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        padding: 3rem 2rem 2rem 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .main-title {
        color: #1a202c;
        font-size: 2.25rem;
        font-weight: 700;
        margin: 0 0 0.5rem 0;
        letter-spacing: -0.025em;
    }
    
    .main-subtitle {
        color: #64748b;
        font-size: 1rem;
        margin: 0;
        font-weight: 400;
    }
    
    /* Clean Search Container */
    .search-container {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
    
    .search-title {
        color: #374151;
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    
    /* Professional Sidebar */
    .css-1d391kg {
        background: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }
    
    .sidebar-header {
        background: #1e293b;
        color: white;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    
    .sidebar-header h3 {
        margin: 0 0 0.5rem 0;
        font-weight: 600;
        font-size: 1.1rem;
    }
    
    .sidebar-header p {
        margin: 0;
        opacity: 0.8;
        font-size: 0.9rem;
    }
    
    /* Clean Article Cards */
    .article-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.2s ease;
    }
    
    .article-card:hover {
        border-color: #cbd5e1;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .article-title {
        color: #1e293b;
        font-size: 1.125rem;
        font-weight: 600;
        line-height: 1.4;
        margin-bottom: 1rem;
    }
    
    .article-meta {
        color: #64748b;
        font-size: 0.875rem;
        margin-bottom: 1rem;
        line-height: 1.6;
    }
    
    .article-source {
        background: #f1f5f9;
        color: #475569;
        padding: 0.25rem 0.75rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 500;
        display: inline-block;
        border: 1px solid #e2e8f0;
    }
    
    /* Professional Sentiment Indicators */
    .sentiment-positive {
        background: #10b981;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.875rem;
        display: inline-block;
        margin: 0.5rem 0;
    }
    
    .sentiment-negative {
        background: #ef4444;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.875rem;
        display: inline-block;
        margin: 0.5rem 0;
    }
    
    .sentiment-neutral {
        background: #6b7280;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.875rem;
        display: inline-block;
        margin: 0.5rem 0;
    }
    
    /* Clean Statistics Cards */
    .stats-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.2s ease;
    }
    
    .stats-card:hover {
        border-color: #cbd5e1;
    }
    
    .stats-number {
        font-size: 2rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.5rem;
        font-family: 'JetBrains Mono', monospace;
    }
    
    .stats-label {
        color: #64748b;
        font-size: 0.875rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Clean Date Sections */
    .date-section {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #3b82f6;
        padding: 1rem 1.5rem;
        border-radius: 0 8px 8px 0;
        margin: 1.5rem 0;
        font-weight: 600;
        color: #374151;
    }
    
    /* Professional Content Sections */
    .content-preview {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
        border-left: 3px solid #e2e8f0;
    }
    
    .content-preview strong {
        color: #374151;
        font-weight: 600;
    }
    
    .ai-summary {
        background: #fefefe;
        border: 1px solid #e5e7eb;
        padding: 1.25rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 3px solid #3b82f6;
    }
    
    .ai-summary strong {
        color: #1f2937;
        font-weight: 600;
    }
    
    /* Clean Keywords */
    .keyword-tag {
        background: #f3f4f6;
        color: #374151;
        padding: 0.25rem 0.75rem;
        border-radius: 16px;
        font-size: 0.75rem;
        font-weight: 500;
        display: inline-block;
        margin: 0.125rem;
        border: 1px solid #e5e7eb;
    }
    
    /* Professional Buttons */
    .stButton > button {
        background: #1e293b;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 500;
        font-size: 0.875rem;
        transition: all 0.2s ease;
        letter-spacing: 0.025em;
    }
    
    .stButton > button:hover {
        background: #334155;
        transform: translateY(-1px);
    }
    
    /* Form Styling */
    .stTextInput > div > div > input,
    .stDateInput > div > div > input {
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 0.75rem;
        font-size: 0.875rem;
        background: #ffffff;
        transition: border-color 0.2s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stDateInput > div > div > input:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        outline: none;
    }
    
    /* Radio Button Styling */
    .stRadio > div {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 1rem;
    }
    
    /* Progress Bar */
    .stProgress > div > div > div > div {
        background: #3b82f6;
        border-radius: 2px;
    }
    
    /* Professional Messages */
    .stInfo {
        background: #f0f9ff;
        border: 1px solid #bfdbfe;
        border-left: 4px solid #3b82f6;
        border-radius: 0 6px 6px 0;
        color: #1e40af;
    }
    
    .stSuccess {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-left: 4px solid #10b981;
        border-radius: 0 6px 6px 0;
        color: #047857;
    }
    
    .stWarning {
        background: #fffbeb;
        border: 1px solid #fed7aa;
        border-left: 4px solid #f59e0b;
        border-radius: 0 6px 6px 0;
        color: #92400e;
    }
    
    .stError {
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-left: 4px solid #ef4444;
        border-radius: 0 6px 6px 0;
        color: #dc2626;
    }
    
    /* Professional Expander */
    .streamlit-expanderHeader {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        font-weight: 500;
        color: #374151;
    }
    
    /* Executive Summary */
    .executive-summary {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        padding: 2rem;
        border-radius: 12px;
        margin: 2rem 0;
    }
    
    .executive-summary h3 {
        color: #1e293b;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    
    .executive-summary p {
        font-size: 1rem;
        line-height: 1.7;
        color: #475569;
        margin: 0;
    }
    
    /* Sentiment Overview */
    .sentiment-overview {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 2rem;
        margin: 2rem 0;
        text-align: center;
    }
    
    .sentiment-overview h3 {
        color: #1e293b;
        margin-bottom: 1.5rem;
        font-weight: 600;
    }
    
    .sentiment-badge-large {
        padding: 1rem 2rem;
        border-radius: 8px;
        display: inline-block;
        margin: 1rem;
        font-weight: 600;
        font-size: 1.125rem;
    }
    
    /* Statistics Section */
    .statistics-section {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1.5rem;
    }
    
    .statistics-section h4 {
        color: #1e293b;
        margin-bottom: 1rem;
        font-weight: 600;
        font-size: 1rem;
    }
    
    .stat-item {
        margin: 0.75rem 0;
        padding: 0.75rem;
        background: #f8fafc;
        border-radius: 6px;
        border-left: 3px solid #e2e8f0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .stat-item .label {
        font-weight: 500;
        color: #374151;
    }
    
    .stat-item .value {
        font-weight: 600;
        color: #1e293b;
        font-family: 'JetBrains Mono', monospace;
    }
    
    /* Topics Section */
    .topics-section {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1.5rem;
        margin-top: 1rem;
    }
    
    .topic-item {
        margin: 0.5rem 0;
        padding: 0.75rem;
        background: #f8fafc;
        border-radius: 6px;
        border-left: 3px solid #3b82f6;
    }
    
    .topic-item strong {
        color: #1e293b;
        font-weight: 600;
    }
    
    .topic-item .count {
        color: #64748b;
        font-size: 0.875rem;
    }
    
    /* Audio Summary */
    .audio-summary {
        background: #1e293b;
        color: white;
        padding: 2rem;
        border-radius: 12px;
        margin: 2rem 0;
    }
    
    .audio-summary h4 {
        margin-bottom: 1rem;
        font-weight: 600;
        color: white;
    }
    
    /* Professional Footer */
    .professional-footer {
        margin-top: 3rem;
        padding: 2rem;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        text-align: center;
    }
    
    .professional-footer p {
        color: #64748b;
        margin: 0;
        font-size: 0.875rem;
    }
    
    /* Section Headers */
    .section-header {
        margin: 3rem 0 1.5rem 0;
    }
    
    .section-header h2 {
        color: #1e293b;
        font-weight: 600;
        font-size: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin: 0;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid #e2e8f0;
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .main {
            padding: 1rem;
        }
        
        .main-title {
            font-size: 1.75rem;
        }
        
        .stats-number {
            font-size: 1.5rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Set up the Streamlit app configuration
st.set_page_config(
    page_title="PersonaTracker | Professional Dashboard", 
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded"
)

# Check authentication
if not st.session_state.get('authenticated'):
    # Create a professional login interface
    st.markdown("""
    <div class="main-header">
        <h1 class="main-title">PersonaTracker</h1>
        <p class="main-subtitle">Professional Intelligence Dashboard</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show login/register tabs with professional styling
    login_tab, register_tab = st.tabs(["Sign In", "Create Account"])
    
    with login_tab:
        st.markdown('<div class="search-container">', unsafe_allow_html=True)
        user = show_login_form()
        if user:
            st.session_state.authenticated = True
            st.session_state.user = user
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with register_tab:
        st.markdown('<div class="search-container">', unsafe_allow_html=True)
        if show_register_form():
            # Switch to login tab after successful registration
            st.session_state.active_tab = "Sign In"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.stop()

# User is authenticated, get user info
user = get_current_user()

# Professional sidebar with user info and logout
if user:
    st.sidebar.markdown(f"""
    <div class="sidebar-header">
        <h3>Welcome Back</h3>
        <p>{user.get('username', 'User')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if user is admin
    is_admin = user.get('role') == 'admin'
    if is_admin:
        st.sidebar.success("Administrator Access")
        # Add admin dashboard link in sidebar for admin users only
        st.sidebar.markdown("---")
        if st.sidebar.button("Admin Dashboard", use_container_width=True):
            st.switch_page("pages/admin_dashboard.py")
        
        # Redirect to admin dashboard if not already there
        if 'admin_redirected' not in st.session_state:
            st.session_state.admin_redirected = True
            st.switch_page("pages/admin_dashboard.py")
    
    # Show logout button
    st.sidebar.markdown("---")
    show_logout_button()

# Main app header (only shown if not redirected to admin)
st.markdown("""
<div class="main-header">
    <h1 class="main-title">PersonaTracker</h1>
    <p class="main-subtitle">AI-Powered Media Intelligence Platform</p>
</div>
""", unsafe_allow_html=True)

# Professional search form
st.markdown("""
<div class="search-container">
    <h2 class="search-title">Search Configuration</h2>
</div>
""", unsafe_allow_html=True)

# Create search form with professional styling
with st.form("search_form"):
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Input field for person or company name
        search_query = st.text_input(
            "Target Entity", 
            placeholder="Enter person or company name (e.g., Elon Musk, Apple Inc.)",
            help="For optimal results, try different name variations and use specific terms"
        )
        
        # Dropdown to select search type
        search_type = st.radio(
            "Entity Type", 
            ["Person", "Company"], 
            horizontal=True,
            help="Select the appropriate category for targeted analysis"
        )
    
    with col2:
        # Date range filter with professional styling
        st.markdown("**Analysis Period**")
        end_date = st.date_input("End Date", value=datetime.now())
        start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=30))
        
        # Ensure end date is after start date
        if start_date > end_date:
            start_date, end_date = end_date, start_date
    
    # Professional submit button
    submitted = st.form_submit_button("Start Analysis", use_container_width=True)

# Only show results if form is submitted
if not submitted:
    # Show professional info section when no search is active
    st.markdown("""
    <div class="search-container">
        <div style="text-align: center; padding: 2rem;">
            <h3 style="color: #1e293b; margin-bottom: 1rem;">Ready for Analysis</h3>
            <p style="color: #64748b; font-size: 1rem;">Configure your search parameters above to begin comprehensive sentiment analysis</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Professional info about RSS feeds
    st.info("**Data Sources**: Real-time analysis from Le Matin, L'Économiste, Morocco World News, and premium news sources")
    
    # Professional tips section
    with st.expander("**Optimization Guidelines**", expanded=False):
        st.markdown("""
        **Search Best Practices:**
        
        • **Person Searches**: Include full names and common variations
        • **Company Analysis**: Use both official names and abbreviations  
        • **Precision**: Quote exact phrases for specific matches
        • **Coverage**: Adjust date ranges for comprehensive analysis
        """)
    st.stop()

if not search_query:
    st.warning("Please specify a search target to proceed with analysis.")
    st.stop()

# Professional search status display
status_container = st.container()
with status_container:
    status_text = st.empty()
    status_text.info(f"**Initializing Analysis** | Target: {search_query}")

# Professional progress bar
progress_container = st.container()
with progress_container:
    progress_bar = st.progress(0)

# Fetch news articles with progress updates
try:
    # Prepare date range
    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None
    
    # Show professional date range info
    if start_date_str and end_date_str:
        status_text.info(f"**Analysis Configuration** | Period: {start_date_str} to {end_date_str}")
    
    # Fetch articles with progress updates
    progress_bar.progress(25)
    
    # Search with the exact query only
    status_text.info(f"**Data Collection** | Processing: {search_query}")
    articles = get_news_about(
        search_query, 
        max_articles=30,
        start_date=start_date_str,
        end_date=end_date_str
    )
    
    # No fallback to last name search - we want exact matches only
    progress_bar.progress(100)
    
except Exception as e:
    st.error(f"**Analysis Error**: {str(e)}")
    articles = []
    
finally:
    progress_bar.empty()
    status_text.empty()
            
if not articles:
    st.error("**No Results Found** | Please adjust search parameters or date range.")
else:
    # Log the search in the database with full article details
    if user and '_id' in user:
        try:
            log_success = log_search(
                user_id=str(user['_id']), 
                query=search_query, 
                results_count=len(articles),
                articles=articles
            )
            if not log_success:
                st.warning("Analysis completed successfully. Search history logging unavailable.")
        except Exception as e:
            st.error(f"**Logging Error**: {str(e)}")

    # Professional results header with statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-number">{len(articles)}</div>
            <div class="stats-label">Articles</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        unique_sources = len(set(article.get('source', 'Unknown') for article in articles))
        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-number">{unique_sources}</div>
            <div class="stats-label">Sources</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        date_range = (datetime.now() - datetime.strptime(start_date_str, '%Y-%m-%d')).days if start_date_str else 30
        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-number">{date_range}</div>
            <div class="stats-label">Days</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-number">AI</div>
            <div class="stats-label">Analysis</div>
        </div>
        """, unsafe_allow_html=True)

    # Group articles by date
    articles_by_date = {}
    for article in articles:
        # Parse the date if available, otherwise use 'Unknown Date'
        date_str = article.get('publish_date', 'Unknown Date')
        if date_str != 'Unknown Date':
            try:
                # Try to parse ISO 8601 format (e.g., 2023-08-10T16:45:00Z)
                if 'T' in date_str:
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    date_str = date_obj.strftime('%Y-%m-%d')
            except (ValueError, AttributeError):
                date_str = 'Unknown Date'
        
        if date_str not in articles_by_date:
            articles_by_date[date_str] = []
        articles_by_date[date_str].append(article)
    
    # Sort dates in descending order (newest first)
    sorted_dates = sorted(articles_by_date.keys(), reverse=True)
    
    # Professional section header
    st.markdown("""
    <div class="section-header">
        <h2>Article Analysis</h2>
    </div>
    """, unsafe_allow_html=True)
    
    sentiment_results = []  # Store sentiment results for overall analysis
    articles_with_sentiment = []  # Store articles with API-generated summaries and sentiment scores
    
    # Track processed articles for rate limiting
    processed_articles = 0
    
    # Display articles grouped by date with professional styling
    for date in sorted_dates:
        # Skip if date filter is set and doesn't match
        if start_date_str and end_date_str and date != 'Unknown Date':
            try:
                article_date = datetime.strptime(date, '%Y-%m-%d').date()
                start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                if article_date < start_date_obj or article_date > end_date_obj:
                    continue
            except (ValueError, TypeError):
                # If date parsing fails, include the article to be safe
                pass
        
        # Professional date section
        st.markdown(f"""
        <div class="date-section">
            {date if date != 'Unknown Date' else 'Date Unknown'} • {len(articles_by_date[date])} Articles
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander(f"Articles from {date if date != 'Unknown Date' else 'Unknown Date'}", expanded=False):
            for article in articles_by_date[date]:
                # Process all articles with professional card styling
                st.markdown('<div class="article-card">', unsafe_allow_html=True)
                
                # Professional article header
                st.markdown(f"""
                <div class="article-title">{article['title']}</div>
                """, unsafe_allow_html=True)
                
                # Always create columns for consistent layout
                col1, col2 = st.columns([1, 2])
                
                # Display image in first column if available
                with col1:
                    image_shown = False
                    
                    # Log all available article keys for debugging
                    logger.info(f"\n{'='*40} ARTICLE DATA {'='*40}")
                    for key, value in article.items():
                        if key not in ['content']:  # Skip content to keep logs clean
                            logger.info(f"{key}: {value}")
                    
                    # Try multiple image sources
                    image_sources = [
                        ('image_url', article.get('image_url')),
                        ('enclosure', article.get('enclosure')),
                        ('media_content', article.get('media_content', [{}])[0].get('url') if isinstance(article.get('media_content'), list) and len(article.get('media_content', [])) > 0 else None),
                        ('media_thumbnail', article.get('media_thumbnail')),
                        ('enclosure_url', article.get('enclosure', {}).get('url') if isinstance(article.get('enclosure'), dict) else None),
                        ('media_content_url', article.get('media_content', [{}])[0].get('url') if isinstance(article.get('media_content'), list) and len(article.get('media_content', [])) > 0 else None)
                    ]
                    
                    logger.info("\nChecking image sources:")
                    for src_name, src_url in image_sources:
                        logger.info(f"{src_name}: {src_url}")
                    
                    for src_name, img_url in image_sources:
                        if not img_url:
                            logger.debug(f"Skipping empty {src_name}")
                            continue
                            
                        try:
                            # Clean up the URL
                            img_url = str(img_url).strip()
                            
                            # Handle relative URLs
                            if img_url.startswith('//'):
                                img_url = f"https:{img_url}"
                            elif img_url.startswith('/'):
                                parsed_uri = urllib.parse.urlparse(article['url'])
                                img_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}{img_url}"
                            
                            # Skip non-image URLs
                            # Check if URL looks like an image
                            is_image_url = any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', 'image/', 'flickr.com', 'img.'])
                            logger.info(f"Checking if URL is an image: {img_url} -> {'Yes' if is_image_url else 'No'}")
                            if not is_image_url:
                                logger.debug(f"Skipping non-image URL: {img_url}")
                                continue
                            
                            # Try to display the image with professional styling
                            st.image(
                                img_url,
                                width=200,
                                use_container_width=True,
                                caption=f"Source: {article.get('source', 'Article Source')}",
                                output_format='JPEG'
                            )
                            
                            logger.info(f"✅ Successfully displayed image: {img_url}")
                            image_shown = True
                            break  # Stop after first successful image
                            
                        except Exception as img_error:
                            logger.debug(f"Skipping image {img_url}: {str(img_error)}")
                            continue
                    
                    # Only show "No image available" if we really couldn't find any image
                    if not image_shown:
                        logger.info(f"ℹ️ No suitable image found in initial sources. Tried {len([x for x in image_sources if x[1]])} potential image sources.")
                        
                        # Try one more time with a direct image from the article URL if available
                        try:
                            if article.get('url'):
                                logger.info(f"Trying to extract image directly from article URL: {article['url']}")
                                response = requests.get(article['url'], timeout=10)
                                soup = BeautifulSoup(response.text, 'html.parser')
                                
                                # Try common image selectors in order of preference
                                for selector in ['meta[property="og:image"]', 'meta[name="twitter:image"]', 'img']:
                                    if image_shown:  # Skip if we've already found an image
                                        break
                                        
                                    for img in soup.select(selector):
                                        if image_shown:  # Skip if we've already found an image
                                            break
                                            
                                        img_src = img.get('content') or img.get('src')
                                        if not img_src:
                                            continue
                                            
                                        # Make URL absolute if it's relative
                                        try:
                                            if img_src.startswith('//'):
                                                img_src = f'https:{img_src}'
                                            elif img_src.startswith('/'):
                                                parsed_uri = urllib.parse.urlparse(article['url'])
                                                img_src = f"{parsed_uri.scheme}://{parsed_uri.netloc}{img_src}"
                                            
                                            # Only proceed if it looks like an image URL
                                            if not any(ext in img_src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', 'image/']):
                                                continue
                                            
                                            # Try to display the image
                                            st.image(
                                                img_src,
                                                width=200,
                                                use_container_width=True,
                                                caption=f"Source: {article.get('source', 'Article Source')}",
                                                output_format='JPEG'
                                            )
                                            logger.info(f"✅ Successfully displayed fallback image: {img_src}")
                                            image_shown = True
                                            break  # Stop after first successful image
                                            
                                        except Exception as e:
                                            logger.debug(f"Couldn't display fallback image {img_src}: {str(e)}")
                                            continue
                        
                        except Exception as e:
                            logger.warning(f"Error in fallback image extraction: {str(e)}")
                        
                        # Only show the message if we still don't have an image
                        if not image_shown:
                            logger.info("ℹ️ No fallback image found either")
                            st.info("No image available")
                
                # Always display details in second column with professional styling
                with col2:
                    # Professional article metadata
                    st.markdown(f"""
                    <div class="article-meta">
                        <strong>Source:</strong> <span class="article-source">{article.get('source', 'Unknown source')}</span><br>
                        <strong>Published:</strong> {article.get('publish_date', 'Unknown date')}<br>
                        <strong>URL:</strong> <a href="{article['url']}" target="_blank" style="color: #3b82f6;">View Original Article</a>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Article preview with professional styling
                    st.markdown(f"""
                    <div class="content-preview">
                        <strong>Content Preview:</strong><br>
                        <em>{article['content'][:200]}...</em>
                    </div>
                    """, unsafe_allow_html=True)
            
                try:
                    with st.spinner("Analyzing sentiment..."):
                        sentiment_result = analyze_sentiment(search_query, article['content'])
                    
                    if sentiment_result:
                        # Professional sentiment display
                        sentiment_class = "positive" if float(sentiment_result['Score']) > 0 else "negative" if float(sentiment_result['Score']) < 0 else "neutral"
                        
                        st.markdown(f"""
                        <div style="margin: 1rem 0;">
                            <div class="sentiment-{sentiment_class}">
                                Sentiment: {sentiment_result['Sentiment']} | Score: {sentiment_result['Score']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Professional summary and keywords
                        st.markdown(f"""
                        <div class="ai-summary">
                            <strong>Analysis Summary:</strong><br>
                            {sentiment_result['Summary']}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if sentiment_result['Keywords']:
                            keywords_html = ' '.join([f'<span class="keyword-tag">{keyword}</span>' for keyword in sentiment_result['Keywords']])
                            st.markdown(f"""
                            <div style="margin: 1rem 0;">
                                <strong>Key Topics:</strong><br>
                                <div style="margin-top: 0.5rem;">{keywords_html}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Store sentiment results for overall analysis
                        sentiment_results.append(sentiment_result)
                        
                        # Store article with API-generated summary and sentiment score
                        articles_with_sentiment.append({
                            "summary": sentiment_result['Summary'],
                            "sentiment_score": float(sentiment_result['Score']),
                            "topics": sentiment_result['Keywords'],
                            "date": date
                        })
                        
                        # Increment the processed articles counter
                        processed_articles += 1
                        
                        # Add a small delay between API calls to avoid rate limits
                        time.sleep(2)  # 2-second delay between API calls
                            
                    else:
                        st.error("Failed to analyze sentiment for this article.")
                except Exception as e:
                    st.error(f"**Processing Error**: {str(e)}")
                    continue  # Continue with the next article if there's an error
                
                st.markdown('</div>', unsafe_allow_html=True)  # Close article card

    # Generate overall summary if we have articles with sentiment analysis
    if articles_with_sentiment:
        # Professional overall summary section
        st.markdown("""
        <div class="section-header">
            <h2>Executive Summary</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Make sure we have valid article data
        valid_articles = [
            a for a in articles_with_sentiment 
            if isinstance(a, dict) and 'summary' in a and 'sentiment_score' in a
        ]
        
        if not valid_articles:
            st.warning("No valid articles with summaries available for generating an overall summary.")
        else:
            # Calculate overall sentiment score
            overall_score = sum(article['sentiment_score'] for article in valid_articles) / len(valid_articles)
            overall_sentiment = "Positive" if overall_score > 0 else "Negative" if overall_score < 0 else "Neutral"
            
            # Generate overall summary
            overall_summary = generate_overall_summary(search_query, valid_articles)
            if overall_summary:
                # Professional summary container
                st.markdown(f"""
                <div class="executive-summary">
                    <h3>Intelligence Report</h3>
                    <p>{overall_summary}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Professional sentiment overview
                sentiment_color = "#10b981" if overall_score > 0 else "#ef4444" if overall_score < 0 else "#6b7280"
                st.markdown(f"""
                <div class="sentiment-overview">
                    <h3>Overall Sentiment Assessment</h3>
                    <div class="sentiment-badge-large" style="background: {sentiment_color};">
                        {overall_sentiment} | Score: {overall_score:.2f}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Professional sentiment distribution section
                st.markdown("""
                <div class="section-header">
                    <h2>Analytics Dashboard</h2>
                </div>
                """, unsafe_allow_html=True)
                
                # Filter articles by date if date filter is applied
                filtered_articles = articles_with_sentiment
                if start_date_str and end_date_str:
                    filtered_articles = [a for a in articles_with_sentiment 
                                      if a.get('date') == 'Unknown Date' or 
                                      (datetime.strptime(a['date'], '%Y-%m-%d').date() >= datetime.strptime(start_date_str, '%Y-%m-%d').date() and
                                       datetime.strptime(a['date'], '%Y-%m-%d').date() <= datetime.strptime(end_date_str, '%Y-%m-%d').date())]
                
                sentiment_counts = {
                    "Positive": sum(1 for article in filtered_articles if article['sentiment_score'] > 0),
                    "Negative": sum(1 for article in filtered_articles if article['sentiment_score'] < 0),
                    "Neutral": sum(1 for article in filtered_articles if article['sentiment_score'] == 0)
                }
                
                # Create professional statistics display
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    # Create pie chart if we have data
                    if any(sentiment_counts.values()):
                        fig, ax = plt.subplots(figsize=(10, 8))
                        
                        # Professional color palette
                        colors = ['#10b981', '#ef4444', '#6b7280']
                        explode = (0.05, 0.05, 0.05)  # Slight separation for modern look
                        
                        wedges, texts, autotexts = ax.pie(
                            sentiment_counts.values(), 
                            labels=sentiment_counts.keys(), 
                            autopct='%1.1f%%',
                            colors=colors,
                            explode=explode,
                            startangle=90,
                            textprops={'fontsize': 12, 'fontweight': 'bold'},
                            pctdistance=0.85
                        )
                        
                        # Professional styling for pie chart
                        for autotext in autotexts:
                            autotext.set_color('white')
                            autotext.set_weight('bold')
                            autotext.set_fontsize(11)
                        
                        for text in texts:
                            text.set_fontsize(12)
                            text.set_fontweight('600')
                            text.set_color('#374151')
                        
                        # Add a circle at the center for modern donut-like appearance
                        centre_circle = plt.Circle((0,0), 0.70, fc='white', linewidth=2, edgecolor='#e5e7eb')
                        fig.gca().add_artist(centre_circle)
                        
                        ax.set_title('Sentiment Distribution Analysis', fontsize=16, fontweight='bold', color='#1e293b', pad=20)
                        
                        # Equal aspect ratio ensures that pie is drawn as a circle
                        ax.axis('equal')  
                        
                        # Clean background
                        fig.patch.set_facecolor('white')
                        ax.set_facecolor('white')
                        
                        plt.tight_layout()
                        st.pyplot(fig)
                
                with col2:
                    # Professional sentiment statistics
                    st.markdown(f"""
                    <div class="statistics-section">
                        <h4>Sentiment Breakdown</h4>
                        <div class="stat-item">
                            <span class="label" style="color: #10b981;">Positive Articles</span>
                            <span class="value">{sentiment_counts['Positive']}</span>
                        </div>
                        <div class="stat-item">
                            <span class="label" style="color: #ef4444;">Negative Articles</span>
                            <span class="value">{sentiment_counts['Negative']}</span>
                        </div>
                        <div class="stat-item">
                            <span class="label" style="color: #6b7280;">Neutral Articles</span>
                            <span class="value">{sentiment_counts['Neutral']}</span>
                        </div>
                        <div class="stat-item" style="border-top: 2px solid #e2e8f0; margin-top: 1rem; padding-top: 1rem;">
                            <span class="label">Total Analyzed</span>
                            <span class="value">{len(filtered_articles)}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show top topics if available
                    if all('topics' in article for article in filtered_articles):
                        all_topics = [topic for article in filtered_articles for topic in article.get('topics', [])]
                        if all_topics:
                            topic_counts = {}
                            for topic in all_topics:
                                topic_counts[topic] = topic_counts.get(topic, 0) + 1
                            
                            # Professional topics display
                            topics_html = ""
                            for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                                topics_html += f'<div class="topic-item"><strong>{topic}</strong> <span class="count">({count} mentions)</span></div>'
                            
                            st.markdown(f"""
                            <div class="topics-section">
                                <h4>Top Discussion Topics</h4>
                                {topics_html}
                            </div>
                            """, unsafe_allow_html=True)
                
                # Generate and display English audio summary with professional styling
                try:
                    st.markdown("""
                    <div class="section-header">
                        <h2>Audio Summary</h2>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.spinner("Generating audio summary..."):
                        audio_file = asyncio.run(translate_and_generate_audio(
                            f"The overall sentiment score is {overall_score:.2f}. {overall_summary}",
                            "en"  # Force English language
                        ))
                        if audio_file and os.path.exists(audio_file):
                            st.markdown("""
                            <div class="audio-summary">
                                <h4>Executive Summary Audio</h4>
                            """, unsafe_allow_html=True)
                            st.audio(audio_file, format="audio/mp3")
                            st.markdown('</div>', unsafe_allow_html=True)
                        else:
                            st.warning("Audio summary generation currently unavailable.")
                except Exception as e:
                    st.warning(f"Audio summary unavailable: {str(e)}")
            else:
                st.warning("Unable to generate comprehensive summary.")

# Professional footer
st.markdown("""
<div class="professional-footer">
    <p>Powered by Advanced AI Analytics | Professional News Intelligence Platform</p>
</div>
""", unsafe_allow_html=True)