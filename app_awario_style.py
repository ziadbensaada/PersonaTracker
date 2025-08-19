import streamlit as st
import os
from datetime import datetime

# Set page config with Awario-like appearance
st.set_page_config(
    page_title="PersonaTracker Pro",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Awario-inspired CSS
st.markdown("""
<style>
    :root {
        --primary: #5c6bc0;
        --primary-light: #8e99f3;
        --primary-dark: #26418f;
        --secondary: #26a69a;
        --success: #66bb6a;
        --warning: #ffa726;
        --danger: #ef5350;
        --light: #f5f5f5;
        --dark: #263238;
        --gray-100: #f5f5f5;
        --gray-200: #eeeeee;
        --gray-300: #e0e0e0;
        --gray-600: #757575;
        --gray-800: #424242;
    }
    
    /* Base Styles */
    .main {
        padding: 0;
        max-width: 100%;
        margin: 0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Top Navigation */
    .top-nav {
        background: white;
        border-bottom: 1px solid var(--gray-200);
        padding: 0.75rem 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: sticky;
        top: 0;
        z-index: 1000;
    }
    
    .logo {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--primary);
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Layout */
    .app-container {
        display: flex;
        min-height: calc(100vh - 60px);
    }
    
    /* Sidebar */
    .sidebar {
        width: 220px;
        background: white;
        border-right: 1px solid var(--gray-200);
        padding: 1.5rem 0;
    }
    
    .nav-item {
        padding: 0.5rem 1.5rem;
        color: var(--gray-800);
        text-decoration: none;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        font-weight: 500;
    }
    
    .nav-item:hover, .nav-item.active {
        background: var(--gray-100);
        color: var(--primary);
        border-left: 3px solid var(--primary);
    }
    
    /* Content */
    .content {
        flex: 1;
        padding: 1.5rem 2rem;
        background: var(--gray-100);
    }
    
    /* Stats Grid */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .stat-card {
        background: white;
        border-radius: 8px;
        padding: 1.25rem;
        text-align: center;
        border-left: 4px solid var(--primary);
    }
    
    .stat-value {
        font-size: 1.75rem;
        font-weight: 600;
        color: var(--primary);
        margin: 0.5rem 0;
    }
    
    /* Mention Cards */
    .mention-card {
        background: white;
        border-radius: 8px;
        border: 1px solid var(--gray-200);
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    
    .mention-header {
        display: flex;
        align-items: center;
        margin-bottom: 0.75rem;
    }
    
    .mention-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: var(--primary-light);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 600;
        margin-right: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

def create_sidebar():
    st.sidebar.markdown("""
    <div class="sidebar">
        <div class="nav-item active">
            <span>📊 Dashboard</span>
        </div>
        <div class="nav-item">
            <span>🔍 Mentions</span>
        </div>
        <div class="nav-item">
            <span>📈 Analytics</span>
        </div>
        <div class="nav-item">
            <span>📊 Reports</span>
        </div>
        <div class="nav-item">
            <span>🔔 Alerts</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_header():
    st.markdown("""
    <div class="top-nav">
        <div class="logo">
            <span>🔍 PersonaTracker</span>
        </div>
        <div style="display: flex; gap: 1rem; align-items: center;">
            <div style="position: relative;">
                <input type="text" placeholder="Search..." style="padding: 0.5rem 1rem; border: 1px solid #ddd; border-radius: 20px; width: 200px;">
            </div>
            <div style="width: 40px; height: 40px; border-radius: 50%; background: #eee; display: flex; align-items: center; justify-content: center;">
                <span>👤</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_stats_grid():
    st.markdown("""
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">Total Mentions</div>
            <div class="stat-value">1,248</div>
            <div style="color: var(--success); font-size: 0.875rem;">↑ 12% from last week</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Reach</div>
            <div class="stat-value">245K</div>
            <div style="color: var(--success); font-size: 0.875rem;">↑ 8% from last week</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Sentiment</div>
            <div class="stat-value">78%</div>
            <div style="color: var(--success); font-size: 0.875rem;">Positive</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_mention_card():
    st.markdown("""
    <div class="mention-card">
        <div class="mention-header">
            <div class="mention-avatar">JD</div>
            <div style="flex: 1;">
                <div class="mention-author">John Doe</div>
                <div class="mention-handle">@johndoe · 2h ago</div>
            </div>
            <div style="color: var(--success); font-weight: 500;">Positive</div>
        </div>
        <div class="mention-content">
            Just tried out the new PersonaTrackerfeatures and I'm impressed with the sentiment analysis accuracy. Great job team! #customerexperience
        </div>
    </div>
    """, unsafe_allow_html=True)

def main():
    create_header()
    
    # Main app container
    st.markdown('<div class="app-container">', unsafe_allow_html=True)
    
    # Create sidebar
    create_sidebar()
    
    # Main content
    st.markdown('<div class="content">', unsafe_allow_html=True)
    
    # Page title and date filter
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h1>Mentions Dashboard</h1>
        <div style="display: flex; gap: 1rem; align-items: center;">
            <select style="padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px;">
                <option>Last 24 hours</option>
                <option>Last 7 days</option>
                <option>Last 30 days</option>
            </select>
            <button style="background: var(--primary); color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px;">
                Export Data
            </button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Stats grid
    create_stats_grid()
    
    # Mentions section
    st.markdown("<h2 style='margin: 1.5rem 0;'>Recent Mentions</h2>", unsafe_allow_html=True)
    
    # Sample mention cards
    for _ in range(5):
        create_mention_card()
    
    # Close content divs
    st.markdown('</div></div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
