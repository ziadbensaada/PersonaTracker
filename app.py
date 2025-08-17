#app.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

# Configure matplotlib to use a font that supports common Unicode characters
mpl.rcParams['font.family'] = 'sans-serif'
mpl.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans', 'Bitstream Vera Sans', 'sans-serif']
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
from bs4 import BeautifulSoup
import os
import logging
import requests
import urllib.parse
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from news_fetcher3 import get_news_about, make_absolute_url_robust, test_image_accessibility  # Import our enhanced RSS fetcher

def is_consent_page(response):
    """Check if the response is a consent page"""
    if not response or not hasattr(response, 'text'):
        return False
        
    consent_indicators = [
        'consent', 'cookies', 'gdpr', 'privacy', 'accept all',
        'cookie consent', 'privacy settings', 'privacy policy',
        'cookie policy', 'privacy preferences'
    ]
    
    # Check URL
    url = response.url.lower()
    if any(indicator in url for indicator in consent_indicators):
        return True
    
    # Check page content
    try:
        text = response.text.lower()
        if any(indicator in text for indicator in consent_indicators):
            return True
    except:
        pass
    
    return False

def handle_consent(session, url):
    """Handle consent pages by accepting all cookies"""
    try:
        logger.info(f"Handling potential consent page: {url}")
        
        # First, try to get the page
        try:
            response = session.get(url, timeout=15)
            response.raise_for_status()
        except Exception as e:
            logger.warning(f"Failed to fetch page for consent handling: {str(e)}")
            return False
        
        # Check if this is a consent page
        if not is_consent_page(response):
            logger.info("No consent page detected")
            return False
            
        logger.info("Consent page detected, attempting to accept all")
        
        # Try to find and submit the consent form
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for common consent form elements
            form = None
            for form_selector in ['form', 'div[class*="consent"]', 'div[class*="cookie"] form', 'form[action*="consent"]', 'form[action*="cookie"]']:
                form = soup.select_one(form_selector)
                if form:
                    break
            
            if form:
                form_data = {}
                # Find all relevant input fields
                for input_tag in form.find_all(['input', 'button']):
                    input_type = input_tag.get('type', '').lower()
                    name = input_tag.get('name', '')
                    value = input_tag.get('value', '1')
                    
                    # Skip file inputs and other non-submittable inputs
                    if input_type in ['file', 'image', 'reset']:
                        continue
                        
                    # Handle different input types
                    if input_type == 'checkbox' and not input_tag.has_attr('checked'):
                        continue
                    elif input_type == 'radio' and not input_tag.has_attr('checked'):
                        continue
                    
                    # Add to form data if it has a name
                    if name:
                        form_data[name] = value
                
                # Try to find form action URL
                action = form.get('action', '')
                if not action or action.startswith('javascript:'):
                    action = url
                elif not action.startswith(('http://', 'https://')):
                    action = urllib.parse.urljoin(url, action)
                
                # Submit the form
                if form_data:
                    logger.info(f"Submitting consent form to {action}")
                    try:
                        session.post(
                            action,
                            data=form_data,
                            headers={
                                'Referer': url,
                                'Content-Type': 'application/x-www-form-urlencoded'
                            },
                            timeout=15,
                            allow_redirects=True
                        )
                        logger.info("Successfully submitted consent form")
                        return True
                    except Exception as e:
                        logger.warning(f"Error submitting consent form: {str(e)}")
            
            # If no form found or form submission failed, try clicking common consent buttons
            for button_text in ['Accept All', 'I Agree', 'Accept', 'Agree', 'Allow All', 'Allow']:
                buttons = soup.find_all(['button', 'a', 'div', 'span'], string=lambda t: t and button_text.lower() in t.lower())
                for button in buttons:
                    try:
                        # Try to get the URL from the button
                        if button.name == 'a' and button.get('href'):
                            button_url = urllib.parse.urljoin(url, button['href'])
                            session.get(button_url, timeout=15)
                            logger.info(f"Clicked consent button: {button_text}")
                            return True
                        # For buttons that submit a form
                        elif button.get('type') == 'submit' and button.find_parent('form'):
                            form = button.find_parent('form')
                            form_data = {}
                            for inp in form.find_all('input'):
                                if inp.get('name'):
                                    form_data[inp['name']] = inp.get('value', '')
                            
                            action = form.get('action', url)
                            if not action.startswith(('http://', 'https://')):
                                action = urllib.parse.urljoin(url, action)
                            
                            session.post(
                                action,
                                data=form_data,
                                headers={'Referer': url},
                                timeout=15
                            )
                            logger.info(f"Submitted consent via button: {button_text}")
                            return True
                    except Exception as e:
                        logger.warning(f"Error clicking consent button {button_text}: {str(e)}")
                        
            logger.warning("Could not find or submit consent form")
            return False
            
        except Exception as e:
            logger.error(f"Error processing consent page: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error in handle_consent: {str(e)}")
        return False
from sentiment_analysis import analyze_sentiment  # Import the sentiment analysis function
from summarizer import generate_overall_summary  # Import the summarizer function
from tts import translate_and_generate_audio  # Import the TTS function
from auth_ui import show_login_form, show_register_form, show_logout_button, get_current_user, require_login, require_admin
from models import log_search  # Import the search logging function
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Professional styling with clean design (keeping the same CSS as before)
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
        max-height: 200px;
        overflow-y: auto;
    }
    
    .content-preview strong {
        color: #374151;
        font-weight: 600;
    }
    
    .content-full {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
        border-left: 3px solid #e2e8f0;
        white-space: pre-wrap;
        word-wrap: break-word;
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
    
    /* Image Status Indicator */
    .image-status {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 0.75rem;
        margin: 0.5rem 0;
        text-align: center;
        color: #64748b;
    }
    
    .image-status.success {
        background: #f0fdf4;
        border-color: #bbf7d0;
        color: #047857;
    }
    
    .image-status.error {
        background: #fef2f2;
        border-color: #fecaca;
        color: #dc2626;
    }
    
    /* Enhanced Image Container */
    .image-container {
        position: relative;
        margin: 1rem 0;
    }
    
    .image-overlay {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(transparent, rgba(0,0,0,0.7));
        color: white;
        padding: 0.5rem;
        border-radius: 0 0 8px 8px;
        font-size: 0.75rem;
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
        
        .article-card {
            padding: 1rem;
        }
        
        .executive-summary {
            padding: 1.5rem;
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

# Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Personalized Feed", "Search Articles"],
    index=0
)

# Professional sidebar with user info and logout
if user:
    st.sidebar.markdown(f"""
    <div class="sidebar-header">
        <h3>Welcome Back</h3>
        <p>{user.get('username', 'User')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show user's interests in sidebar
    if user.get('interests'):
        st.sidebar.markdown("### Your Interests")
        for interest in user.get('interests', []):
            st.sidebar.markdown(f"- {interest}")
    
    # Check if user is admin
    is_admin = user.get('role') == 'admin'
    if is_admin:
        st.sidebar.markdown("---")
        st.sidebar.success("Administrator Access")
        if st.sidebar.button("Admin Dashboard", use_container_width=True):
            st.switch_page("pages/admin_dashboard.py")
    
    # Main content based on navigation
    if page == "Personalized Feed":
        def get_articles_by_domains(domains, date_range="Last 7 days"):
            """
            Fetch articles based on the given domains and date range using enhanced RSS fetcher.
            """
            articles = []
            processed_urls = set()
            
            # Convert date range to start_date and end_date
            end_date = datetime.now()
            if date_range == "Last 24 hours":
                start_date = end_date - timedelta(days=1)
            elif date_range == "Last 7 days":
                start_date = end_date - timedelta(days=7)
            elif date_range == "Last 30 days":
                start_date = end_date - timedelta(days=30)
            else:  # All time
                start_date = None
            
            # Format dates as strings for the API
            start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # Search for articles for each domain using the enhanced RSS fetcher
            for domain in domains:
                try:
                    logger.info(f"Fetching articles for domain: {domain}")
                    domain_articles = get_news_about(
                        query=domain,
                        max_articles=20,  # Limit per domain
                        start_date=start_date_str,
                        end_date=end_date_str
                    )
                    
                    # Add articles to the results, avoiding duplicates
                    for article in domain_articles:
                        if article.get('url') and article['url'] not in processed_urls:
                            # Add domain information to the article
                            article['domain'] = domain
                            articles.append(article)
                            processed_urls.add(article['url'])
                            logger.info(f"Added article: {article.get('title')} with image: {article.get('image_url', 'No image')}")
                    
                except Exception as e:
                    st.error(f"Error fetching articles for {domain}: {str(e)}")
                    logger.error(f"Error fetching articles for {domain}: {str(e)}")
            
            logger.info(f"Total articles fetched: {len(articles)}")
            return articles

        def show_personalized_articles(user):
            """Display articles based on user's interests with enhanced image support."""
            st.title("Your Personalized News Feed")
            
            # Add date range filter
            st.sidebar.subheader("Filter Articles")
            date_range = st.sidebar.selectbox(
                "Date Range",
                ["Last 24 hours", "Last 7 days", "Last 30 days", "All time"],
                index=1
            )
            
            # Get user's interests
            user_interests = user.get('interests', [])
            
            if not user_interests:
                st.warning("You haven't selected any interests yet. Please update your profile to get personalized news.")
                return
            
            # Show user's interests
            st.write(f"### Your Interests: {', '.join(user_interests)}")
            
            # Show overall statistics
            with st.spinner("Loading your personalized feed..."):
                all_articles = get_articles_by_domains(user_interests, date_range)
            
            if not all_articles:
                st.info("No articles found for your interests in the selected time range.")
                return
            
            # Display overall statistics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="stats-card">
                    <div class="stats-number">{len(all_articles)}</div>
                    <div class="stats-label">Articles</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="stats-card">
                    <div class="stats-number">{len(user_interests)}</div>
                    <div class="stats-label">Topics</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                unique_sources = len(set(article.get('source', 'Unknown') for article in all_articles))
                st.markdown(f"""
                <div class="stats-card">
                    <div class="stats-number">{unique_sources}</div>
                    <div class="stats-label">Sources</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Group articles by interest/domain
            articles_by_interest = {}
            for article in all_articles:
                domain = article.get('domain', 'General')
                if domain not in articles_by_interest:
                    articles_by_interest[domain] = []
                articles_by_interest[domain].append(article)
            
            # Display articles grouped by interest
            for interest, articles in articles_by_interest.items():
                st.markdown(f"""
                <div class="section-header">
                    <h2>{interest} News ({len(articles)} articles)</h2>
                </div>
                """, unsafe_allow_html=True)
                
                # Display articles for this interest
                for i, article in enumerate(articles[:10]):  # Limit to 10 articles per interest
                    st.markdown('<div class="article-card">', unsafe_allow_html=True)
                    
                    # Create two columns for image and content
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        image_displayed = False
                        if article.get('url'):
                            try:
                                # Use the enhanced image extractor
                                from enhanced_image_extractor import EnhancedImageExtractor
                                extractor = EnhancedImageExtractor()
                                
                                # Try to get image from article URL
                                image_url = extractor.extract_image(article['url'])
                                
                                # If no image found, try the RSS feed URL if available
                                if not image_url and article.get('rss_feed_url'):
                                    image_url = extractor.extract_image(article['rss_feed_url'], is_rss_feed=True)
                                
                                # If we found an image, display it
                                if image_url:
                                    try:
                                        st.image(
                                            image_url,
                                            width=250,
                                            use_container_width=True,
                                            caption=f"📸 Source: {article.get('source', 'Unknown')}",
                                            output_format='JPEG'
                                        )
                                        # Update the article to indicate it has an image
                                        article['image_url'] = image_url
                                        article['has_image'] = True
                                        image_displayed = True
                                    except Exception as e:
                                        logger.error(f"Error displaying image: {e}")
                                        article['has_image'] = False
                            except Exception as e:
                                logger.error(f"Error extracting image: {e}")
                        
                        if not image_displayed:
                            # Show a placeholder if no image is available
                            st.image(
                                "https://via.placeholder.com/300x200?text=No+Image+Available",
                                width=250,
                                use_container_width=True,
                                caption="No image available for this article"
                            )
                    
                    with col2:
                        # Enhanced article title with link
                        st.markdown(f"""
                        <div class="article-title">
                            <a href="{article.get('url', '#')}" target="_blank" rel="noopener noreferrer" 
                               style="color: #1e293b; text-decoration: none;">
                                {article.get('title', 'No title')}
                            </a>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Enhanced metadata
                        st.markdown(f"""
                        <div class="article-meta">
                            <span class="article-source">{article.get('source', 'Unknown')}</span><br>
                            <strong>Published:</strong> {article.get('publish_date', 'Unknown date')}<br>
                            <strong>Author:</strong> {article.get('author', 'Unknown')}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Enhanced content preview
                        if article.get('content'):
                            content = article['content']
                            preview = content[:300] + "..." if len(content) > 300 else content
                            st.markdown(f"""
                            <div class="content-preview">
                                <strong>Content Preview:</strong><br>
                                <em>{preview}</em>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Add article summary and sentiment analysis in a single section
                        if article.get('content'):
                            try:
                                with st.spinner("🤖 Analyzing article..."):
                                    # Generate summary
                                    from summarizer import generate_overall_summary
                                    summary_article = [{
                                        'summary': article['content'][:500],  # First 500 chars for summarization
                                        'sentiment_score': 0  # Will be updated by sentiment analysis
                                    }]
                                    summary = generate_overall_summary(interest, summary_article)
                                    
                                    # Analyze sentiment
                                    sentiment_result = analyze_sentiment(interest, article['content'])
                                    sentiment_score = sentiment_result.get('sentiment_score', 0) if sentiment_result else 0
                                    sentiment = "Positive" if sentiment_score > 0.1 else "Negative" if sentiment_score < -0.1 else "Neutral"
                                    
                                    # Determine sentiment color
                                    sentiment_color = "#10b981"  # Green for positive
                                    if sentiment == "Negative":
                                        sentiment_color = "#ef4444"  # Red for negative
                                    elif sentiment == "Neutral":
                                        sentiment_color = "#6b7280"  # Gray for neutral
                                    
                                    # Display summary and sentiment in a single card
                                    st.markdown(f"""
                                    <div style="margin-top: 10px; padding: 15px; border-radius: 8px; background-color: #f8fafc; border-left: 4px solid {sentiment_color};">
                                        <div style="margin-bottom: 10px;">
                                            <div style="display: flex; align-items: center; gap: 5px; margin-bottom: 8px;">
                                                <span style="font-weight: 600; color: #1e293b;">Analysis:</span>
                                                <span style="color: {sentiment_color}; font-weight: 500;">{sentiment}</span>
                                                <span style="color: #6b7280; font-size: 0.9em;">({sentiment_score:.2f})</span>
                                            </div>
                                            <div style="font-size: 0.95em; line-height: 1.5; color: #334155;">
                                                {summary if summary else 'No summary available'}
                                            </div>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                            except Exception as e:
                                logger.error(f"Error in article analysis: {e}")
                                st.error("Failed to analyze article content")
                        
                        # Add "Read Full Article" button that redirects to the article
                        article_url = article.get('url', '#')
                        st.markdown(f"""
                        <a href="{article_url}" target="_blank" style="text-decoration: none;">
                            <button style="width: 100%; padding: 0.5rem; background-color: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer;">
                                Read Full Article
                            </button>
                        </a>
                        """, unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)  # Close article card
                
                st.markdown("---")  # Separator between interests
        
        show_personalized_articles(user)
    
    else:  # Search Articles page
        # Main app header for search page
        st.markdown("""
        <div class="main-header">
            <h1 class="main-title">PersonaTracker</h1>
            <p class="main-subtitle">AI-Powered Media Intelligence Platform</p>
        </div>
        """, unsafe_allow_html=True)

        # Professional search form
        st.markdown("""
        <div class="search-container">
            <h2 class="search-title">Enhanced Search Configuration</h2>
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
                
                # Advanced options
                max_articles = st.slider("Maximum Articles", min_value=10, max_value=100, value=30, step=5)
                
                # Ensure end date is after start date
                if start_date > end_date:
                    start_date, end_date = end_date, start_date
            
            # Professional submit button
            submitted = st.form_submit_button("🚀 Start Enhanced Analysis", use_container_width=True)

        # Only show results if form is submitted
        if not submitted:
            # Show professional info section when no search is active
            st.markdown("""
            <div class="search-container">
                <div style="text-align: center; padding: 2rem;">
                    <h3 style="color: #1e293b; margin-bottom: 1rem;">Ready for Enhanced Analysis</h3>
                    <p style="color: #64748b; font-size: 1rem;">Configure your search parameters above to begin comprehensive sentiment analysis with enhanced image extraction</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Enhanced info about data sources
            st.info("**📊 Enhanced Data Sources**: Real-time analysis from premium RSS feeds with advanced image extraction and accessibility testing")
            
            # Professional features section
            with st.expander("**🚀 Enhanced Features**", expanded=False):
                st.markdown("""
                **New Enhanced Capabilities:**
                
                • **🖼️ Advanced Image Extraction**: Multiple fallback strategies for finding article images
                • **✅ Image Validation**: Real-time accessibility testing for all images
                • **🔍 Smart Content Analysis**: Enhanced RSS parsing with full article extraction
                • **📈 Improved Accuracy**: Better name matching with pattern recognition
                • **⚡ Performance Optimized**: Intelligent caching and rate limiting
                • **🎯 Precision Search**: Exact phrase matching for better results
                
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

        # Enhanced search status display
        status_container = st.container()
        with status_container:
            status_text = st.empty()
            status_text.info(f"**🔄 Initializing Enhanced Analysis** | Target: {search_query}")

        # Professional progress bar
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)

        # Fetch news articles with enhanced progress updates
        try:
            # Prepare date range
            start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
            end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None
            
            # Show professional date range info
            if start_date_str and end_date_str:
                status_text.info(f"**📅 Analysis Configuration** | Period: {start_date_str} to {end_date_str} | Max Articles: {max_articles}")
            
            # Enhanced search with progress updates
            progress_bar.progress(20)
            status_text.info(f"**Enhanced Data Collection** | Processing RSS feeds for: {search_query}")
            
            # Use the enhanced RSS fetcher
            articles = get_news_about(
                search_query, 
                max_articles=max_articles,
                start_date=start_date_str,
                end_date=end_date_str
            )
            
            progress_bar.progress(60)
            status_text.info(f"**📊 Processing Results** | Found {len(articles)} articles")
            
            # Process articles and count images
            articles_with_images = 0
            for article in articles:
                # Ensure has_image is set based on whether we could display an image
                if article.get('has_image', False):
                    articles_with_images += 1
                elif article.get('image_url'):
                    # If has_image wasn't set but image_url exists, count it
                    articles_with_images += 1
                    article['has_image'] = True
            
            progress_bar.progress(100)
            status_text.success(f"**✅ Analysis Complete** | {len(articles)} articles found | {articles_with_images} with images")
            
        except Exception as e:
            st.error(f"**❌ Analysis Error**: {str(e)}")
            logger.error(f"Analysis error: {str(e)}")
            articles = []
            
        finally:
            progress_bar.empty()
            time.sleep(2)  # Show success message briefly
            status_text.empty()
                    
        if not articles:
            st.error("**❌ No Results Found** | Please adjust search parameters or date range.")
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

            # Enhanced results header with statistics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="stats-card">
                    <div class="stats-number">{len(articles)}</div>
                    <div class="stats-label">Articles Found</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                unique_sources = len(set(article.get('source', 'Unknown') for article in articles))
                st.markdown(f"""
                <div class="stats-card">
                    <div class="stats-number">{unique_sources}</div>
                    <div class="stats-label">News Sources</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Removed image statistics as requested
            
            with col4:
                date_range_days = (datetime.now() - datetime.strptime(start_date_str, '%Y-%m-%d')).days if start_date_str else 30
                st.markdown(f"""
                <div class="stats-card">
                    <div class="stats-number">{date_range_days}</div>
                    <div class="stats-label">Days Analyzed</div>
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
                        elif ' ' in date_str:
                            # Try to parse YYYY-MM-DD HH:MM:SS format
                            date_obj = datetime.strptime(date_str.split()[0], '%Y-%m-%d')
                            date_str = date_obj.strftime('%Y-%m-%d')
                    except (ValueError, AttributeError):
                        date_str = 'Unknown Date'
                
                if date_str not in articles_by_date:
                    articles_by_date[date_str] = []
                articles_by_date[date_str].append(article)
            
            # Sort dates in descending order (newest first)
            sorted_dates = sorted([d for d in articles_by_date.keys() if d != 'Unknown Date'], reverse=True)
            if 'Unknown Date' in articles_by_date:
                sorted_dates.append('Unknown Date')
            
            # Enhanced section header
            st.markdown("""
            <div class="section-header">
                <h2>📰 Enhanced Article Analysis</h2>
            </div>
            """, unsafe_allow_html=True)
            
            sentiment_results = []  # Store sentiment results for overall analysis
            articles_with_sentiment = []  # Store articles with API-generated summaries and sentiment scores
            
            # Track processed articles for rate limiting
            processed_articles = 0
            
            # Display articles grouped by date with enhanced styling
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
                
                # Date section without image statistics
                articles_in_date = articles_by_date[date]
                
                st.markdown(f"""
                <div class="date-section">
                    📅 {date if date != 'Unknown Date' else 'Date Unknown'} • 
                    {len(articles_in_date)} Articles
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"View articles from {date if date != 'Unknown Date' else 'Unknown Date'}", expanded=True):
                    for i, article in enumerate(articles_in_date):
                        # Enhanced article processing with professional card styling
                        st.markdown('<div class="article-card">', unsafe_allow_html=True)
                        
                        # Enhanced article header
                        st.markdown(f"""
                        <div class="article-title">
                            📄 {article.get('title', 'Untitled Article')}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Create columns for enhanced layout
                        col1, col2 = st.columns([1, 2])
                        
                        # Enhanced image display with robust consent handling and retry logic
                        with col1:
                            image_displayed = False
                            if article.get('url'):
                                try:
                                    # Use the enhanced image extractor
                                    from enhanced_image_extractor import EnhancedImageExtractor
                                    extractor = EnhancedImageExtractor()
                                    
                                    # Try to get image from article URL
                                    image_url = extractor.extract_image(article['url'])
                                    
                                    # If no image found, try the RSS feed URL if available
                                    if not image_url and article.get('rss_feed_url'):
                                        image_url = extractor.extract_image(article['rss_feed_url'], is_rss_feed=True)
                                    
                                    # If we found an image, display it
                                    if image_url:
                                        try:
                                            st.image(
                                                image_url,
                                                width=250,
                                                use_container_width=True,
                                                caption=f"📸 Source: {article.get('source', 'Unknown')}",
                                                output_format='JPEG'
                                            )
                                            st.markdown("""
                                            <div class="image-status success">
                                                <span>🟢 Image loaded</span>
                                            </div>
                                            """, unsafe_allow_html=True)
                                            # Update the article to indicate it has an image
                                            article['image_url'] = image_url
                                            article['has_image'] = True
                                            image_displayed = True
                                        except Exception as e:
                                            logger.error(f"Error displaying image: {e}")
                                            article['has_image'] = False
                                    
                                except Exception as e:
                                    logger.error(f"Error extracting image: {e}")
                            
                            if not image_displayed:
                                # Show a placeholder if no image is available
                                st.image(
                                    "https://via.placeholder.com/300x200?text=No+Image+Available",
                                    width=250,
                                    use_container_width=True,
                                    caption="No image available for this article"
                                )
                        
                        # Enhanced article details
                        with col2:
                            # Enhanced metadata with better error handling
                            try:
                                # Format the publish date if available
                                publish_date = 'Unknown date'
                                if article.get('publish_date'):
                                    try:
                                        if isinstance(article['publish_date'], (int, float)):
                                            # Handle timestamp
                                            publish_date = datetime.fromtimestamp(article['publish_date']).strftime('%Y-%m-%d %H:%M')
                                        elif isinstance(article['publish_date'], str):
                                            # Try to parse the date string
                                            try:
                                                dt = datetime.fromisoformat(article['publish_date'].replace('Z', '+00:00'))
                                                publish_date = dt.strftime('%Y-%m-%d %H:%M')
                                            except ValueError:
                                                publish_date = article['publish_date']
                                    except Exception as e:
                                        logger.warning(f"Error formatting date {article.get('publish_date')}: {e}")
                                
                                # Get source with fallback to domain
                                source = article.get('source', '')
                                if not source and 'url' in article:
                                    try:
                                        domain = urllib.parse.urlparse(article['url']).netloc
                                        source = domain.replace('www.', '') if domain else 'Unknown source'
                                    except Exception as e:
                                        logger.warning(f"Error parsing URL for source: {e}")
                                
                                st.markdown(f"""
                                <div class="article-meta">
                                    <strong>🏢 Source:</strong> <span class="article-source">{source or 'Unknown source'}</span><br>
                                    <strong>📅 Published:</strong> {publish_date}<br>
                                    <strong>🔗 URL:</strong> <a href="{article['url']}" target="_blank" rel="noopener noreferrer" style="color: #3b82f6;">View Original Article</a>
                                    {f'<br><strong>✍️ Author:</strong> {article["author"]}' if article.get('author') and article['author'] != 'Unknown' else ''}
                                    {f'<br><strong>🖼️ Image:</strong> Available' if article.get('image_url') else '<br><strong>🖼️ Image:</strong> Not available'}
                                </div>
                                """, unsafe_allow_html=True)
                                
                            except Exception as meta_error:
                                logger.error(f"Error displaying article metadata: {meta_error}")
                                st.markdown("""
                                <div class="article-meta" style="color: #ef4444;">
                                    ❌ Error loading article metadata
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Enhanced content display
                            content = article.get('content', 'No content available')
                            
                            # Create expandable content section
                            with st.expander("📖 Full Article Content", expanded=False):
                                st.markdown(f"""
                                <div class="content-full">
                                    {content}
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Show enhanced preview
                            preview = content[:400] + "..." if len(content) > 400 else content
                            st.markdown(f"""
                            <div class="content-preview">
                                <strong>📝 Content Preview:</strong><br>
                                <em>{preview}</em>
                            </div>
                            """, unsafe_allow_html=True)
                    
                        # Enhanced sentiment analysis
                        try:
                            with st.spinner("🤖 Analyzing sentiment with AI..."):
                                sentiment_result = analyze_sentiment(search_query, article['content'])
                            
                            if sentiment_result:
                                # Enhanced sentiment display
                                sentiment_class = "positive" if float(sentiment_result['Score']) > 0 else "negative" if float(sentiment_result['Score']) < 0 else "neutral"
                                sentiment_icon = "🟢" if sentiment_class == "positive" else "🔴" if sentiment_class == "negative" else "🟡"
                                
                                st.markdown(f"""
                                <div style="margin: 1rem 0;">
                                    <div class="sentiment-{sentiment_class}">
                                        {sentiment_icon} Sentiment: {sentiment_result['Sentiment']} | Score: {sentiment_result['Score']}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Enhanced summary and keywords
                                st.markdown(f"""
                                <div class="ai-summary">
                                    <strong>🤖 AI Analysis Summary:</strong><br>
                                    {sentiment_result['Summary']}
                                </div>
                                """, unsafe_allow_html=True)
                                
                                if sentiment_result['Keywords']:
                                    keywords_html = ' '.join([f'<span class="keyword-tag">🏷️ {keyword}</span>' for keyword in sentiment_result['Keywords']])
                                    st.markdown(f"""
                                    <div style="margin: 1rem 0;">
                                        <strong>Key Topics Identified:</strong><br>
                                        <div style="margin-top: 0.5rem;">{keywords_html}</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                # Store sentiment results for overall analysis
                                sentiment_results.append(sentiment_result)
                                
                                # Store article with enhanced metadata
                                articles_with_sentiment.append({
                                    "summary": sentiment_result['Summary'],
                                    "sentiment_score": float(sentiment_result['Score']),
                                    "topics": sentiment_result['Keywords'],
                                    "date": date,
                                    "has_image": bool(article.get('image_url')),
                                    "source": article.get('source', 'Unknown')
                                })
                                
                                # Increment the processed articles counter
                                processed_articles += 1
                                
                                # Add a small delay between API calls to avoid rate limits
                                time.sleep(1.5)  # Reduced delay for better UX
                                    
                            else:
                                st.error("❌ Failed to analyze sentiment for this article.")
                        except Exception as e:
                            st.error(f"**⚠️ Processing Error**: {str(e)}")
                            logger.error(f"Sentiment analysis error: {str(e)}")
                            continue  # Continue with the next article if there's an error
                        
                        st.markdown('</div>', unsafe_allow_html=True)  # Close article card

            # Generate enhanced overall summary
            if articles_with_sentiment:
                # Enhanced overall summary section
                st.markdown("""
                <div class="section-header">
                    <h2>📊 Executive Intelligence Summary</h2>
                </div>
                """, unsafe_allow_html=True)
                
                # Validate articles with sentiment analysis
                valid_articles = [
                    a for a in articles_with_sentiment 
                    if isinstance(a, dict) and 'summary' in a and 'sentiment_score' in a
                ]
                
                if not valid_articles:
                    st.warning("⚠️ No valid articles with summaries available for generating an overall summary.")
                else:
                    # Calculate enhanced sentiment metrics
                    overall_score = sum(article['sentiment_score'] for article in valid_articles) / len(valid_articles)
                    overall_sentiment = "Positive" if overall_score > 0 else "Negative" if overall_score < 0 else "Neutral"
                    
                    # Generate enhanced overall summary
                    overall_summary = generate_overall_summary(search_query, valid_articles)
                    if overall_summary:
                        # Enhanced summary container
                        st.markdown(f"""
                        <div class="executive-summary">
                            <h3>Intelligence Report for "{search_query}"</h3>
                            <p>{overall_summary}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Enhanced sentiment overview with more details
                        sentiment_color = "#10b981" if overall_score > 0 else "#ef4444" if overall_score < 0 else "#6b7280"
                        sentiment_icon = "🟢" if overall_score > 0 else "🔴" if overall_score < 0 else "🟡"
                        
                        st.markdown(f"""
                        <div class="sentiment-overview">
                            <h3>📈 Overall Sentiment Assessment</h3>
                            <div class="sentiment-badge-large" style="background: {sentiment_color};">
                                {sentiment_icon} {overall_sentiment} | Score: {overall_score:.2f}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Enhanced analytics dashboard
                        st.markdown("""
                        <div class="section-header">
                            <h2>📊 Enhanced Analytics Dashboard</h2>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Calculate enhanced metrics
                        sentiment_counts = {
                            "Positive": sum(1 for article in valid_articles if article['sentiment_score'] > 0),
                            "Negative": sum(1 for article in valid_articles if article['sentiment_score'] < 0),
                            "Neutral": sum(1 for article in valid_articles if article['sentiment_score'] == 0)
                        }
                        
                        # Enhanced dashboard layout
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            # Enhanced pie chart
                            if any(sentiment_counts.values()):
                                fig, ax = plt.subplots(figsize=(10, 8))
                                
                                # Professional color palette with enhanced styling
                                colors = ['#10b981', '#ef4444', '#6b7280']
                                explode = (0.05, 0.05, 0.05)  # Slight separation
                                
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
                                
                                # Enhanced styling for pie chart
                                for autotext in autotexts:
                                    autotext.set_color('white')
                                    autotext.set_weight('bold')
                                    autotext.set_fontsize(11)
                                
                                for text in texts:
                                    text.set_fontsize(12)
                                    text.set_fontweight('600')
                                    text.set_color('#374151')
                                
                                # Enhanced center circle
                                centre_circle = plt.Circle((0,0), 0.70, fc='white', linewidth=2, edgecolor='#e5e7eb')
                                fig.gca().add_artist(centre_circle)
                                
                                ax.set_title('📊 Enhanced Sentiment Distribution', fontsize=16, fontweight='bold', color='#1e293b', pad=20)
                                ax.axis('equal')
                                
                                # Clean background
                                fig.patch.set_facecolor('white')
                                ax.set_facecolor('white')
                                
                                plt.tight_layout()
                                st.pyplot(fig)
                        
                        with col2:
                            # Enhanced statistics with additional metrics
                            articles_with_images = sum(1 for article in valid_articles if article.get('has_image', False) or article.get('image_url'))
                            unique_sources = len(set(article.get('source', 'Unknown') for article in valid_articles))
                            
                            st.markdown(f"""
                            <div class="statistics-section">
                                <h4>📈 Enhanced Analytics</h4>
                                <div class="stat-item">
                                    <span class="label" style="color: #10b981;">🟢 Positive Articles</span>
                                    <span class="value">{sentiment_counts['Positive']}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="label" style="color: #ef4444;">🔴 Negative Articles</span>
                                    <span class="value">{sentiment_counts['Negative']}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="label" style="color: #6b7280;">🟡 Neutral Articles</span>
                                    <span class="value">{sentiment_counts['Neutral']}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="label">🖼️ Articles with Images</span>
                                    <span class="value">{articles_with_images}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="label">🏢 Unique Sources</span>
                                    <span class="value">{unique_sources}</span>
                                </div>
                                <div class="stat-item" style="border-top: 2px solid #e2e8f0; margin-top: 1rem; padding-top: 1rem;">
                                    <span class="label">📊 Total Analyzed</span>
                                    <span class="value">{len(valid_articles)}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Enhanced topics display
                            if all('topics' in article for article in valid_articles):
                                all_topics = [topic for article in valid_articles for topic in article.get('topics', [])]
                                if all_topics:
                                    topic_counts = {}
                                    for topic in all_topics:
                                        topic_counts[topic] = topic_counts.get(topic, 0) + 1
                                    
                                    # Enhanced topics display
                                    topics_html = ""
                                    for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                                        topics_html += f'<div class="topic-item"><strong>🏷️ {topic}</strong> <span class="count">({count} mentions)</span></div>'
                                    
                                    st.markdown(f"""
                                    <div class="topics-section">
                                        <h4>Top Discussion Topics</h4>
                                        {topics_html}
                                    </div>
                                    """, unsafe_allow_html=True)
                        
                        # Enhanced audio summary generation
                        try:
                            st.markdown("""
                            <div class="section-header">
                                <h2>🎧 Enhanced Audio Summary</h2>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            with st.spinner("🤖 Generating enhanced audio summary..."):
                                enhanced_summary_text = f"""
                                Analysis Results for {search_query}:
                                
                                Overall sentiment score is {overall_score:.2f}, indicating {overall_sentiment.lower()} coverage.
                                
                                We analyzed {len(valid_articles)} articles from {unique_sources} different sources.
                                {articles_with_images} articles included images.
                                
                                {overall_summary}
                                """
                                
                                audio_file = asyncio.run(translate_and_generate_audio(
                                    enhanced_summary_text,
                                    "en"  # Force English language
                                ))
                                if audio_file and os.path.exists(audio_file):
                                    st.markdown("""
                                    <div class="audio-summary">
                                        <h4>🎧 Enhanced Executive Summary Audio</h4>
                                        <p>Listen to the comprehensive analysis results</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    st.audio(audio_file, format="audio/mp3")
                                else:
                                    st.warning("🔇 Audio summary generation currently unavailable.")
                        except Exception as e:
                            st.warning(f"🔇 Audio summary unavailable: {str(e)}")
                            logger.error(f"Audio generation error: {str(e)}")
                    else:
                        st.warning("⚠️ Unable to generate comprehensive summary.")

    # Add logout button at the bottom
    st.sidebar.markdown("---")
    show_logout_button()

# Professional footer with enhanced branding
st.markdown("""
<div class="professional-footer">
    <p>🚀 Powered by Enhanced Ziad Ben Saada | Advanced News Intelligence Platform with Image Recognition</p>
    <p style="font-size: 0.75rem; margin-top: 0.5rem; opacity: 0.7;">
        Enhanced with AI-powered sentiment analysis, advanced image extraction, and real-time validation
    </p>
</div>
""", unsafe_allow_html=True)