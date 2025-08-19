# app_enhanced.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from datetime import datetime, timedelta
from news_fetcher3 import get_news_about, make_absolute_url_robust, test_image_accessibility
from sentiment_analysis import analyze_sentiment
from summarizer import generate_overall_summary
from tts import translate_and_generate_audio
from auth_ui import show_login_form, show_register_form, show_logout_button, get_current_user, require_login, require_admin
from models import log_search
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page config with modern look
st.set_page_config(
    page_title="PersonaTracker Pro",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern UI
st.markdown("""
<style>
    /* Modern Color Scheme */
    :root {
        --primary: #4f46e5;
        --primary-hover: #4338ca;
        --secondary: #6b7280;
        --success: #10b981;
        --danger: #ef4444;
        --warning: #f59e0b;
        --info: #3b82f6;
        --light: #f9fafb;
        --dark: #111827;
        --gray-100: #f3f4f6;
        --gray-200: #e5e7eb;
        --gray-300: #d1d5db;
        --gray-700: #374151;
    }
    
    /* Base Styles */
    .main {
        padding: 1.5rem 2rem;
        max-width: 1600px;
        margin: 0 auto;
    }
    
    /* Typography */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--dark);
        line-height: 1.6;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-weight: 700;
        color: var(--dark);
        margin-top: 0;
    }
    
    /* Header */
    .main-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 0 2rem;
        border-bottom: 1px solid var(--gray-200);
        margin-bottom: 2rem;
    }
    
    .logo {
        font-size: 1.75rem;
        font-weight: 800;
        color: var(--primary);
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    
    /* Navigation */
    .stSidebar {
        background: #ffffff;
        border-right: 1px solid var(--gray-200);
    }
    
    .sidebar .sidebar-content {
        padding: 2rem 1.5rem;
    }
    
    /* Buttons */
    .stButton>button {
        border-radius: 8px;
        font-weight: 500;
        padding: 0.5rem 1.25rem;
        transition: all 0.2s;
    }
    
    .stButton>button.primary-btn {
        background-color: var(--primary);
        border: 1px solid var(--primary);
    }
    
    .stButton>button.primary-btn:hover {
        background-color: var(--primary-hover);
        border-color: var(--primary-hover);
    }
    
    /* Cards */
    .card {
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid var(--gray-200);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        transition: all 0.2s;
    }
    
    .card:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transform: translateY(-2px);
    }
    
    /* Article Cards */
    .article-card {
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid var(--gray-200);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        transition: all 0.2s;
    }
    
    .article-card:hover {
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        transform: translateY(-2px);
    }
    
    .article-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--dark);
        margin-bottom: 0.75rem;
    }
    
    .article-meta {
        display: flex;
        align-items: center;
        gap: 1rem;
        color: var(--secondary);
        font-size: 0.875rem;
        margin-bottom: 1rem;
    }
    
    .article-source {
        font-weight: 600;
        color: var(--primary);
    }
    
    .article-date {
        color: var(--secondary);
    }
    
    .article-snippet {
        color: var(--gray-700);
        margin-bottom: 1rem;
        line-height: 1.6;
    }
    
    /* Sentiment Badges */
    .sentiment-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: capitalize;
    }
    
    .sentiment-positive {
        background-color: #d1fae5;
        color: #065f46;
    }
    
    .sentiment-negative {
        background-color: #fee2e2;
        color: #991b1b;
    }
    
    .sentiment-neutral {
        background-color: #e0f2fe;
        color: #075985;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        margin-bottom: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--primary);
        color: white !important;
    }
    
    /* Stats Cards */
    .stat-card {
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid var(--gray-200);
        padding: 1.5rem;
        text-align: center;
    }
    
    .stat-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--primary);
        margin: 0.5rem 0;
    }
    
    .stat-label {
        color: var(--secondary);
        font-size: 0.875rem;
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .main {
            padding: 1rem;
        }
        
        .stButton>button {
            width: 100%;
            margin-bottom: 0.5rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Your existing functions and code here...
# [Previous code for get_articles_by_domains, show_personalized_articles, etc.]

def main():
    # Sidebar with user info and navigation
    st.sidebar.markdown("""
    <div style="padding: 1rem 0 2rem;">
        <div class="logo">🔍 PersonaTracker</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation
    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Search", "Saved Searches", "Alerts", "Reports"],
        index=0
    )
    
    # Main content area
    st.markdown("""
    <div class="main">
        <div class="main-header">
            <h1>Social Media Monitoring Dashboard</h1>
            <div style="display: flex; gap: 1rem; align-items: center;">
                <span style="color: var(--secondary);">Last updated: {}</span>
            </div>
        </div>
    """.format(datetime.now().strftime("%b %d, %Y %H:%M")), unsafe_allow_html=True)
    
    # Your existing main content here
    # [Previous main content code]
    
    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
