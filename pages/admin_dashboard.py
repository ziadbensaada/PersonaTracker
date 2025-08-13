import streamlit as st
from datetime import datetime, timedelta
import sys
import os
from bson import ObjectId

# Add the parent directory to path so we can import from the main app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import users_collection, search_history_collection
from auth_ui import get_current_user

# Set page config
st.set_page_config(page_title="Admin Dashboard", layout="wide")

# Check if user is authenticated and is admin
user = get_current_user()
if not user or user.get('role') != 'admin':
    # Instead of showing an error, immediately redirect to the main app
    st.switch_page("app.py")
    st.stop()

# Add a button to go back to the main app in the sidebar
if st.sidebar.button("Back to App"):
    st.switch_page("app.py")

# Admin dashboard title
st.title("Admin Dashboard")
st.write(f"Welcome, {user['username']} (Admin)")

# Sidebar with navigation
st.sidebar.title("Admin Menu")
menu = st.sidebar.radio(
    "Navigation",
    ["User Management", "Search Analytics", "System Status"]
)

# User Management Tab
if menu == "User Management":
    st.header("User Management")
    
    # Get all users
    users = list(users_collection.find({}, {"password": 0}))  # Exclude passwords
    
    # Display users in a table
    if users:
        # Convert to DataFrame for better display
        user_data = []
        for user in users:
            user_data.append({
                "Username": user['username'],
                "Email": user.get('email', ''),
                "Role": user.get('role', 'user'),
                "Active": user.get('is_active', True),
                "Created At": user.get('created_at', '').strftime('%Y-%m-%d %H:%M') 
                                if user.get('created_at') else 'N/A',
                "Last Login": user.get('last_login', '').strftime('%Y-%m-%d %H:%M') 
                              if user.get('last_login') else 'Never'
            })
        
        st.dataframe(
            user_data,
            column_config={
                "Active": st.column_config.CheckboxColumn(
                    "Active",
                    help="User account status",
                    default=True,
                )
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No users found in the database.")
    
    # Add new user form
    with st.expander("Add New User", expanded=False):
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("Username")
                new_email = st.text_input("Email")
            
            with col2:
                new_password = st.text_input("Password", type="password")
                new_role = st.selectbox("Role", ["user", "admin"])
            
            submitted = st.form_submit_button("Add User")
            
            if submitted:
                if not all([new_username, new_email, new_password]):
                    st.error("All fields are required")
                else:
                    # Check if username or email already exists
                    if users_collection.find_one({"$or": [
                        {"username": new_username},
                        {"email": new_email}
                    ]}):
                        st.error("Username or email already exists")
                    else:
                        # Create the user
                        from models import create_user
                        user_id, error = create_user(
                            username=new_username,
                            email=new_email,
                            password=new_password,
                            role=new_role
                        )
                        
                        if user_id:
                            st.success(f"User '{new_username}' created successfully!")
                            st.rerun()
                        else:
                            st.error(f"Error creating user: {error}")

# Search Analytics Tab
elif menu == "Search Analytics":
    st.header("Search Analytics")
    
    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", value=datetime.now())
    
    # Get search history
    search_history = list(search_history_collection.find({
        "timestamp": {
            "$gte": datetime.combine(start_date, datetime.min.time()),
            "$lte": datetime.combine(end_date, datetime.max.time())
        }
    }).sort("timestamp", -1))
    
    # Display search statistics
    st.subheader("Search Statistics")
    
    if search_history:
        # Basic stats
        total_searches = len(search_history)
        unique_users = len({s['user_id'] for s in search_history if 'user_id' in s})
        avg_results = sum(s.get('results_count', 0) for s in search_history) / total_searches
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Searches", total_searches)
        with col2:
            st.metric("Unique Users", unique_users)
        with col3:
            st.metric("Avg Results per Search", f"{avg_results:.1f}")
        
        # Popular searches
        st.subheader("Popular Searches")
        
        # Group by query
        from collections import Counter
        search_counts = Counter(s['query'] for s in search_history)
        
        # Convert to DataFrame for display
        import pandas as pd
        df_popular = pd.DataFrame(
            [{"Query": query, "Count": count} for query, count in search_counts.most_common(10)],
            columns=["Query", "Count"]
        )
        
        if not df_popular.empty:
            st.bar_chart(df_popular.set_index("Query"))
            st.dataframe(df_popular, hide_index=True, use_container_width=True)
        else:
            st.info("No search data available for the selected date range.")
        
        # Function to get username from user_id
        def get_username(user_id):
            try:
                if not user_id or user_id == 'Anonymous':
                    return 'Anonymous'
                user = users_collection.find_one({"_id": ObjectId(user_id)})
                return user.get('username', f'User ({user_id[:6]}...)') if user else f'Deleted User ({user_id[:6]}...)'
            except Exception as e:
                print(f"Error getting username for {user_id}: {str(e)}")
                return f'Error: {str(e)}'
        
        # Get unique user IDs from search history
        user_ids = list({s['user_id'] for s in search_history if s.get('user_id')})
        
        # Create a mapping of user_id to username
        user_map = {}
        for user_id in user_ids:
            user_map[user_id] = get_username(user_id)
        
        # Recent searches with expandable article details
        st.subheader("Recent Searches")
        
        if not search_history:
            st.info("No recent searches to display.")
        else:
            # Display a table of recent searches
            recent_searches = []
            for s in search_history[:20]:  # Show most recent 20 searches
                user_id = s.get('user_id', 'Anonymous')
                username = user_map.get(user_id, 'Anonymous')
                
                search_entry = {
                    "Query": s['query'],
                    "User": f"{username}",
                    "Results": s.get('results_count', 0),
                    "Timestamp": s['timestamp'].strftime('%Y-%m-%d %H:%M')
                }
                recent_searches.append(search_entry)
                
                # Add expandable section for article details
                with st.expander(f"🔍 {s['query']} - {username} - {search_entry['Timestamp']}", expanded=False):
                    st.write(f"**User:** {username}")
                    if user_id != 'Anonymous':
                        st.write(f"**User ID:** {user_id}")
                    st.write(f"**Date/Time:** {search_entry['Timestamp']}")
                    st.write(f"**Number of Results:** {search_entry['Results']}")
                    
                    # Display articles if available
                    if 'articles' in s and s['articles']:
                        st.subheader("Articles")
                        for i, article in enumerate(s['articles'], 1):
                            with st.container():
                                st.markdown(f"### {i}. {article.get('title', 'No title')}")
                                st.write(f"**Source:** {article.get('source', 'Unknown')}")
                                st.write(f"**Date:** {article.get('publish_date', 'Unknown')}")
                                
                                # Display sentiment if available
                                if 'sentiment' in article and article['sentiment']:
                                    sentiment = article['sentiment']
                                    st.write(f"**Sentiment:** {sentiment.get('label', 'N/A')} (Score: {sentiment.get('score', 0):.2f})")
                                
                                # Display summary if available
                                if article.get('summary'):
                                    with st.expander("View Summary", expanded=False):
                                        st.write(article['summary'])
                                
                                # Add a link to the original article
                                if article.get('url'):
                                    st.markdown(f"[Read full article]({article['url']})")
                                
                                st.markdown("---")  # Separator between articles
                    else:
                        st.info("No article details available for this search.")
            
            # Display the search history table
            st.dataframe(
                recent_searches,
                column_config={
                    "Timestamp": st.column_config.DatetimeColumn("Time")
                },
                hide_index=True,
                use_container_width=True
            )
    else:
        st.info("No search history found for the selected date range.")

# System Status Tab
else:
    st.header("System Status")
    
    # Basic system info
    import platform
    import psutil
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("System Information")
        st.write(f"**OS:** {platform.system()} {platform.release()}")
        st.write(f"**Python Version:** {platform.python_version()}")
        st.write(f"**CPU Cores:** {psutil.cpu_count(logical=True)}")
        
        # Memory usage
        memory = psutil.virtual_memory()
        st.write(f"**Memory Usage:** {memory.percent}%")
        st.progress(memory.percent / 100)
        
    with col2:
        st.subheader("Database Status")
        
        # MongoDB stats
        try:
            from models import client
            db = client['news_scraper_db']
            
            # Get collection stats
            users_count = db.users.count_documents({})
            searches_count = db.search_history.count_documents({})
            
            st.write(f"**Users:** {users_count}")
            st.write(f"**Searches:** {searches_count}")
            
            # Database size
            db_stats = db.command('dbstats')
            db_size_mb = db_stats['dataSize'] / (1024 * 1024)
            st.write(f"**Database Size:** {db_size_mb:.2f} MB")
            
        except Exception as e:
            st.error(f"Error connecting to database: {str(e)}")
    
    # Recent logs
    st.subheader("Recent Logs")
    # Note: In a production environment, you would connect to your logging system here
    st.info("Log viewer would be connected here in a production environment.")

# Add a logout button in the sidebar
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()
