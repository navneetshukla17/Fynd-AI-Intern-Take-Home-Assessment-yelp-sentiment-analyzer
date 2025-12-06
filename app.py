import streamlit as st

st.set_page_config(
    page_title="Yelp Sentiment Analyzer",
    page_icon="⭐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Multi-page app
pages = {
    "Customer Feedback": "dashboards.customer_feedback_app",
    "Analytics Dashboard": "dashboards.analytics_dashboard"
}

st.sidebar.title("Navigation")
selection = st.sidebar.radio("Go to", list(pages.keys()))

# Import and run selected page
if selection == "Customer Feedback":
    from dashboards import customer_feedback_app
    customer_feedback_app.main()
else:
    from dashboards import analytics_dashboard
    analytics_dashboard.main()