import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import time
import os
from datetime import datetime, timedelta
from news_fetcher3 import get_news_about  # Import our new RSS fetcher
from sentiment_analysis import analyze_sentiment  # Import the sentiment analysis function
from summarizer import generate_overall_summary  # Import the summarizer function
from tts import translate_and_generate_audio  # Import the TTS function
from auth_ui import show_login_form, show_register_form, show_logout_button, get_current_user, require_login, require_admin
from models import log_search  # Import the search logging function
import asyncio

# Set up the Streamlit app title
st.set_page_config(page_title="News Sentiment Analysis", layout="wide")

# Check authentication
if not st.session_state.get('authenticated'):
    # Show login/register tabs
    login_tab, register_tab = st.tabs(["Login", "Register"])
    
    with login_tab:
        user = show_login_form()
        if user:
            st.session_state.authenticated = True
            st.session_state.user = user
            st.rerun()
    
    with register_tab:
        if show_register_form():
            # Switch to login tab after successful registration
            st.session_state.active_tab = "Login"
            st.rerun()
    
    st.stop()

# User is authenticated, get user info
user = get_current_user()

# Sidebar with user info and logout
if user:
    st.sidebar.title(f"Welcome, {user.get('username', 'User')}")
    
        # Check if user is admin
    is_admin = user.get('role') == 'admin'
    if is_admin:
        st.sidebar.success("Admin Mode")
        # Add admin dashboard link in sidebar for admin users only
        st.sidebar.markdown("---")
        if st.sidebar.button("🔒 Admin Dashboard"):
            st.switch_page("pages/admin_dashboard.py")
        
        # Redirect to admin dashboard if not already there
        if 'admin_redirected' not in st.session_state:
            st.session_state.admin_redirected = True
            st.switch_page("pages/admin_dashboard.py")
    
    # Show logout button
    show_logout_button()

# Main app title (only shown if not redirected to admin)
st.title("News Sentiment Analysis")

# Create search form
with st.form("search_form"):
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Input field for person or company name
        search_query = st.text_input("Enter a Person or Company Name", 
                                   placeholder="e.g., Hakimi or Achraf Hakimi",
                                   help="For better results, try different name variations")
        
        # Dropdown to select search type
        search_type = st.radio("Search Type", ["Person", "Company"], horizontal=True,
                              help="Select 'Person' for people and 'Company' for organizations")
    
    with col2:
        # Date range filter
        st.write("Date Range (Optional)")
        end_date = st.date_input("To", value=datetime.now())
        start_date = st.date_input("From", value=datetime.now() - timedelta(days=30))
        
        # Ensure end date is after start date
        if start_date > end_date:
            start_date, end_date = end_date, start_date
    
    # Submit button
    submitted = st.form_submit_button("Search")

# Only show results if form is submitted
if not submitted:
    st.stop()

# Add a note about the RSS feeds
st.caption("ℹ️ Searching news from multiple sources including Le Matin, L'Économiste, Morocco World News, and more")

# Add some tips for better search results
with st.expander("💡 Search Tips"):
    st.markdown("""
    - For people, try both full name and just the last name
    - For companies, try both full name and abbreviations
    - Use quotes for exact matches (e.g., "Elon Musk")
    - Try different name variations if you don't get enough results
    """)

if not search_query:
    st.warning("Please enter a name to search for.")
    st.stop()

# Show search status
status_text = st.empty()
status_text.info(f"🔍 Searching for news about: {search_query}")

# Add a progress bar
progress_bar = st.progress(0)

# Fetch news articles with progress updates
try:
    # Prepare date range
    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None
    
    # Show date range being searched
    if start_date_str and end_date_str:
        status_text.info(f"📅 Searching from {start_date_str} to {end_date_str}")
    
    # Fetch articles with progress updates
    progress_bar.progress(25)
    
    # Search with the exact query only
    status_text.info(f"🔍 Searching for: {search_query}")
    articles = get_news_about(
        search_query, 
        max_articles=30,
        start_date=start_date_str,
        end_date=end_date_str
    )
    
    # No fallback to last name search - we want exact matches only
    progress_bar.progress(100)
    
except Exception as e:
    st.error(f"An error occurred during search: {str(e)}")
    articles = []
    
finally:
    progress_bar.empty()
            
if not articles:
    st.error("No articles found. Please try again with a different name or date range.")
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
                st.warning("Search was successful, but there was an issue saving the search history.")
        except Exception as e:
            st.error(f"Error logging search: {str(e)}")

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
    
    # Display article summaries and sentiment analysis
    st.subheader(f"Article Summaries and Sentiment Analysis")
    st.write(f"Found {len(articles)} articles")
    
    sentiment_results = []  # Store sentiment results for overall analysis
    articles_with_sentiment = []  # Store articles with API-generated summaries and sentiment scores
    
    # Track processed articles for rate limiting
    processed_articles = 0
    
    # Display articles grouped by date
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
        
        with st.expander(f"📅 {date if date != 'Unknown Date' else 'Unknown Date'}"):
            for article in articles_by_date[date]:
                # Process all articles
                with st.expander(f"📰 {article['title']}"):
                    st.write(f"**URL:** {article['url']}")
                    st.write(f"**Published Date:** {article.get('publish_date', 'Unknown date')}")
                    st.write(f"**Source:** {article.get('source', 'Unknown source')}")
                    st.write(f"**Content Preview:** {article['content'][:200]}...")  # Show first 200 chars of content
                
                    try:
                        with st.spinner("Analyzing sentiment..."):
                            sentiment_result = analyze_sentiment(search_query, article['content'])
                        
                        if sentiment_result:
                            st.write(f"**Sentiment Score:** {sentiment_result['Score']}")
                            st.write(f"**Sentiment:** {sentiment_result['Sentiment']}")
                            st.write(f"**Summary:** {sentiment_result['Summary']}")
                            st.write(f"**Keywords:** {', '.join(sentiment_result['Keywords'])}")
                            
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
                        st.error(f"Error processing article: {str(e)}")
                        continue  # Continue with the next article if there's an error
    
    # Generate overall summary if we have articles with sentiment analysis
    if articles_with_sentiment:
        st.subheader("Overall News Summary and Sentiment")
        
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
                st.write(overall_summary)
                
                # Display sentiment information
                st.write(f"**Overall Sentiment Score:** {overall_score:.2f}")
                st.write(f"**Overall Sentiment:** {overall_sentiment}")
                
                # Sentiment distribution by date
                st.subheader("Sentiment Distribution")
                
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
                
                # Create pie chart if we have data
                if any(sentiment_counts.values()):
                    fig, ax = plt.subplots()
                    ax.pie(sentiment_counts.values(), 
                          labels=sentiment_counts.keys(), 
                          autopct='%1.1f%%',
                          colors=['green', 'red', 'gray'])
                    st.pyplot(fig)
                    
                    # Show sentiment statistics
                    st.write("**Sentiment Statistics:**")
                    st.write(f"- Positive: {sentiment_counts['Positive']}")
                    st.write(f"- Negative: {sentiment_counts['Negative']}")
                    st.write(f"- Neutral: {sentiment_counts['Neutral']}")
                    
                    # Show top topics if available
                    if all('topics' in article for article in filtered_articles):
                        all_topics = [topic for article in filtered_articles for topic in article.get('topics', [])]
                        if all_topics:
                            topic_counts = {}
                            for topic in all_topics:
                                topic_counts[topic] = topic_counts.get(topic, 0) + 1
                            
                            st.write("\n**Top Topics:**")
                            for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                                st.write(f"- {topic} ({count} mentions)")
                
                # Generate and display English audio summary
                try:
                    st.subheader("Audio Summary")
                    with st.spinner("Generating audio summary..."):
                        audio_file = asyncio.run(translate_and_generate_audio(
                            f"The overall sentiment score is {overall_score:.2f}. {overall_summary}",
                            "en"  # Force English language
                        ))
                        if audio_file and os.path.exists(audio_file):
                            st.audio(audio_file, format="audio/mp3")
                        else:
                            st.warning("Could not generate audio summary.")
                except Exception as e:
                    st.warning(f"Could not generate audio summary: {str(e)}")
            else:
                st.warning("Could not generate overall summary.")
                    


# Display a message if no search query is entered
if not search_query:
    st.warning("Please enter a person or company name to generate the report.")