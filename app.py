import streamlit as st
import sys
import os

st.set_page_config(
    page_title="FYND AI Internship",
    page_icon="🚀",
    layout="wide"
)

st.sidebar.title("🚀 FYND AI Project")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Select Page",
    ["📊 Task 1: Rating Prediction", "⭐ Task 2: User Feedback", "📈 Task 2: Admin Dashboard"]
)

st.sidebar.markdown("---")
st.sidebar.info("Built for FYND AI Internship Assessment")

if page == "📊 Task 1: Rating Prediction":
    st.title("📊 Task 1: Yelp Rating Prediction")
    st.markdown("### Analyze Yelp reviews and predict star ratings")
    
    st.info("⚠️ Task 1 requires running locally with the dataset. This is a demo placeholder.")
    
    st.markdown("""
    **What this does:**
    - Tests 3 different prompting approaches
    - Predicts 1-5 star ratings from reviews
    - Compares accuracy, MAE, and JSON validity
    
    **To run locally:**
    ```bash
    cd task1
    python assessment_task_1.py
    ```
    """)
    
    with st.expander("📖 View Sample Results"):
        st.markdown("""
        **Approach 1 (Basic):** 29% accuracy, 88.5% JSON validity
        
        **Approach 2 (Keywords):** Better for sentiment mapping
        
        **Approach 3 (CoT + Examples):** Best for complex reviews
        """)

elif page == "⭐ Task 2: User Feedback":
    import importlib.util
    
    user_path = os.path.join(os.path.dirname(__file__), 'task2', 'user_dashboard.py')
    
    if os.path.exists(user_path):
        spec = importlib.util.spec_from_file_location("user_dashboard", user_path)
        user_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(user_module)
        user_module.main()
    else:
        st.error("user_dashboard.py not found in task2 folder")

elif page == "📈 Task 2: Admin Dashboard":
    import importlib.util
    
    admin_path = os.path.join(os.path.dirname(__file__), 'task2', 'admin_dashboard.py')
    
    if os.path.exists(admin_path):
        spec = importlib.util.spec_from_file_location("admin_dashboard", admin_path)
        admin_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(admin_module)
        admin_module.main()
    else:
        st.error("admin_dashboard.py not found in task2 folder")