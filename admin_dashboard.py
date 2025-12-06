import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import plotly.express as px
import plotly.graph_objects as go


st.set_page_config(
    page_title="Admin Dashboard",
    page_icon="📊",
    layout="wide"
)


# Data file path
DATA_FILE = "feedback_data.csv"


# MODEL LOADING
@st.cache_resource
def load_model():
    model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None
    )
    
    return tokenizer, model

# Load model
tokenizer, model = load_model()



def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            # Ensure required columns exist
            if 'summary' not in df.columns:
                df['summary'] = ''
            if 'actions' not in df.columns:
                df['actions'] = ''
            return df
        except:
            return pd.DataFrame(columns=['id', 'timestamp', 'rating', 'review', 'ai_response', 'summary', 'actions'])
    return pd.DataFrame(columns=['id', 'timestamp', 'rating', 'review', 'ai_response', 'summary', 'actions'])


def generate_admin_analysis(rating, review):    
    try:
        prompt = f"""<|system|>
You are a business analyst reviewing customer feedback.
</s>
<|user|>
Analyze this feedback:
Rating: {rating}/5 stars
Review: "{review}"

Write one sentence summarizing the key point, then list 3 specific actions.
</s>
<|assistant|>
Summary:"""
        
        # Tokenize
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=400)
        
        if torch.cuda.is_available():
            inputs = inputs.to("cuda")
        
        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=120,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                repetition_penalty=1.2
            )
        
        # Decode
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract assistant response
        if "<|assistant|>" in response:
            response = response.split("<|assistant|>")[-1].strip()
        if "Summary:" in response:
            response = response.split("Summary:")[-1].strip()
        
        response = response.replace("</s>", "").strip()
        
        # Try to extract summary (first sentence)
        sentences = response.split('.')
        summary = sentences[0].strip() if sentences else ""
        
        # Clean up summary
        summary = summary.replace("SUMMARY:", "").replace("Summary:", "").strip()
        
        # Validate AI summary
        use_ai_summary = (
            summary and 
            len(summary) > 15 and 
            len(summary) < 200 and
            not any(placeholder in summary.lower() for placeholder in ['[', ']', 'action 1', 'placeholder'])
        )
        
    except Exception as e:
        print(f"AI Generation Error: {e}")
        use_ai_summary = False
        summary = ""
    
    if not use_ai_summary:
        review_lower = review.lower()
        
        # Analyze review sentiment
        positive_words = ['great', 'excellent', 'amazing', 'love', 'best', 'perfect', 'wonderful', 'fantastic', 'awesome', 'good', 'impressive']
        negative_words = ['bad', 'terrible', 'awful', 'worst', 'disappointed', 'poor', 'horrible', 'useless', 'hate', 'never']
        
        pos_count = sum(1 for word in positive_words if word in review_lower)
        neg_count = sum(1 for word in negative_words if word in review_lower)
        
        if rating >= 4:
            if pos_count > 2:
                summary = f"Customer is highly satisfied and praised multiple aspects of the service (rated {rating}/5)"
            else:
                summary = f"Customer had a positive experience and is satisfied with the service (rated {rating}/5)"
        elif rating == 3:
            if pos_count > neg_count:
                summary = f"Customer had a generally positive but mixed experience with some areas for improvement (rated {rating}/5)"
            else:
                summary = f"Customer found the experience average with both positive and negative aspects (rated {rating}/5)"
        else:
            if neg_count > 2:
                summary = f"Customer expressed significant dissatisfaction with multiple service issues (rated {rating}/5)"
            else:
                summary = f"Customer had a negative experience and was disappointed with the service (rated {rating}/5)"
    
    # Generate smart actions based on rating and review content
    review_lower = review.lower()
    actions = []
    
    if rating >= 4:
        # Positive feedback actions
        actions = [
            "Send personalized thank you message to customer",
            "Request permission to use review as testimonial",
            "Analyze what went well to replicate success"
        ]
        
        if 'recommend' in review_lower or 'refer' in review_lower:
            actions[2] = "Set up referral reward program for satisfied customers"
        
    elif rating == 3:
        # Neutral feedback actions
        actions = [
            "Contact customer to understand specific pain points",
            "Identify service gaps mentioned in the feedback",
            "Implement improvements in areas of concern"
        ]
        
        if 'slow' in review_lower or 'wait' in review_lower:
            actions[1] = "Review and optimize service speed and wait times"
        elif 'price' in review_lower or 'expensive' in review_lower:
            actions[1] = "Evaluate pricing structure and value proposition"
            
    else:
        # Negative feedback actions
        actions = [
            "Reach out immediately to apologize and resolve the issue",
            "Conduct internal investigation into the problems raised",
            "Offer compensation or remedy to recover customer relationship"
        ]
        
        if 'refund' in review_lower or 'money back' in review_lower:
            actions[2] = "Process refund and ensure customer satisfaction"
        elif 'staff' in review_lower or 'service' in review_lower:
            actions[1] = "Provide additional training to staff on customer service"
    
    return summary, actions


def update_analysis(df, idx):
    rating = df.loc[idx, 'rating']
    review = df.loc[idx, 'review']
    
    summary, actions = generate_admin_analysis(rating, review)
    
    df.loc[idx, 'summary'] = summary
    df.loc[idx, 'actions'] = json.dumps(actions)
    df.to_csv(DATA_FILE, index=False)
    
    return summary, actions


def get_rating_color(rating):
    if rating >= 4:
        return "🟢"
    elif rating == 3:
        return "🟡"
    else:
        return "🔴"


def get_border_class(rating):
    if rating >= 4:
        return "positive-border"
    elif rating == 3:
        return "neutral-border"
    else:
        return "negative-border"



# CUSTOM CSS

st.markdown("""
<style>
    /* Main styling */
    .main {
        background: #f8f9fa;
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        text-align: center;
        border-left: 4px solid #667eea;
    }
    
    /* Feedback card */
    .feedback-item {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border-left: 4px solid #e0e0e0;
    }
    
    .positive-border {
        border-left-color: #4caf50 !important;
    }
    
    .neutral-border {
        border-left-color: #ff9800 !important;
    }
    
    .negative-border {
        border-left-color: #f44336 !important;
    }
    
    /* Section headers */
    .section-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
        font-weight: 600;
    }
    
    /* Analysis box */
    .analysis-box {
        background: #f0f4ff;
        padding: 1rem;
        border-radius: 8px;
        border-left: 3px solid #667eea;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ANALYTICS FUNCTIONS

def create_rating_distribution(df):
    if len(df) == 0:
        return None
    
    rating_counts = df['rating'].value_counts().sort_index()
    
    fig = go.Figure(data=[
        go.Bar(
            x=[f"{i} ⭐" for i in rating_counts.index],
            y=rating_counts.values,
            marker_color=['#f44336', '#ff9800', '#ffc107', '#8bc34a', '#4caf50'][:len(rating_counts)],
            text=rating_counts.values,
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title="Rating Distribution",
        xaxis_title="Rating",
        yaxis_title="Count",
        showlegend=False,
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig


def create_timeline_chart(df):
    if len(df) == 0:
        return None
    
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    daily_counts = df.groupby('date').size().reset_index(name='count')
    
    fig = px.line(
        daily_counts,
        x='date',
        y='count',
        title='Feedback Submissions Over Time',
        markers=True
    )
    
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Number of Submissions",
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig



# MAIN APP

def main():
    # Header
    st.title("📊 Admin Dashboard")
    st.markdown("### Customer Feedback Management System")
    
    # Refresh button
    col1, col2, col3 = st.columns([6, 1, 1])
    with col3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    st.markdown("---")
    
    # Load data
    df = load_data()
    
    if len(df) == 0:
        st.info("📭 No feedback submissions yet. Waiting for customer reviews...")
        st.markdown("### 🚀 Getting Started")
        st.markdown("""
        1. Users can submit feedback through the User Dashboard
        2. Feedback will appear here automatically
        3. Click 'Generate Analysis' to get AI insights
        """)
        return
    
    # ANALYTICS SECTION    
    st.markdown("## 📈 Analytics Overview")
    
    # Calculate metrics
    total_reviews = len(df)
    avg_rating = df['rating'].mean()
    positive_count = len(df[df['rating'] >= 4])
    negative_count = len(df[df['rating'] <= 2])
    positive_pct = (positive_count / total_reviews * 100) if total_reviews > 0 else 0
    negative_pct = (negative_count / total_reviews * 100) if total_reviews > 0 else 0
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📊 Total Reviews",
            value=total_reviews,
            delta="Active"
        )
    
    with col2:
        st.metric(
            label="⭐ Average Rating",
            value=f"{avg_rating:.1f}",
            delta=f"{'📈' if avg_rating >= 3.5 else '📉'}"
        )
    
    with col3:
        st.metric(
            label="✅ Positive",
            value=f"{positive_pct:.0f}%",
            delta=f"{positive_count} reviews"
        )
    
    with col4:
        st.metric(
            label="⚠️ Negative",
            value=f"{negative_pct:.0f}%",
            delta=f"{negative_count} reviews"
        )
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        rating_chart = create_rating_distribution(df)
        if rating_chart:
            st.plotly_chart(rating_chart, use_container_width=True)
    
    with col2:
        timeline_chart = create_timeline_chart(df)
        if timeline_chart:
            st.plotly_chart(timeline_chart, use_container_width=True)
    
    st.markdown("---")
    
    # FEEDBACK LIST    
    st.markdown("## 📋 Recent Feedback")
    
    # Sort by timestamp (newest first)
    df = df.sort_values('timestamp', ascending=False).reset_index(drop=True)
    
    # Display each feedback
    for idx in range(len(df)):
        row = df.iloc[idx]
        
        with st.container():
            # Rating and timestamp header
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### {get_rating_color(row['rating'])} {'⭐' * int(row['rating'])} ({row['rating']}/5)")
            
            with col2:
                timestamp = pd.to_datetime(row['timestamp']).strftime("%Y-%m-%d %H:%M")
                st.markdown(f"**🕐 {timestamp}**")
            
            # Create colored border
            border_class = get_border_class(row['rating'])
            
            # Customer Review
            st.markdown("**📝 Customer Review:**")
            st.info(row['review'])
            
            # AI Response sent to customer
            st.markdown("**💬 AI Response Sent:**")
            st.success(f"*\"{row['ai_response']}\"*")
            
            # Check if analysis exists
            has_analysis = row['summary'] and str(row['summary']) != '' and str(row['summary']) != 'nan'
            
            if has_analysis:
                st.markdown("---")
                
                # Summary section
                st.markdown("**🔍 AI Analysis Summary:**")
                st.markdown(f"<div class='analysis-box'><strong>{row['summary']}</strong></div>", unsafe_allow_html=True)
                
                # Actions section
                st.markdown("**✅ Recommended Actions:**")
                try:
                    actions = json.loads(row['actions'])
                    
                    for i, action in enumerate(actions, 1):
                        if i == 1:
                            icon = "🎯"  # High priority
                        elif i == 2:
                            icon = "📋"  # Medium priority
                        else:
                            icon = "💡"  # Suggestion
                        
                        st.markdown(f"{icon} **{i}.** {action}")
                except Exception as e:
                    st.markdown("- Review feedback and take appropriate action")
                
                col1, col2, col3 = st.columns([2, 1, 2])
                with col2:
                    if st.button("🔄 Regenerate", key=f"regen_{idx}"):
                        with st.spinner("🔄 Re-analyzing feedback..."):
                            summary, actions = update_analysis(df, idx)
                            st.success("✅ Analysis updated!")
                            st.rerun()
            else:
                st.markdown("---")
                st.warning("⚠️ AI analysis not generated yet - Click below to analyze this feedback")
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button(f"🤖 Generate AI Analysis", key=f"analyze_{idx}", use_container_width=True):
                        with st.spinner("🔄 Analyzing feedback with AI..."):
                            summary, actions = update_analysis(df, idx)
                            st.success("✅ Analysis generated successfully!")
                            st.rerun()
            
            st.markdown("---")
    
    # Footer
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <p>Powered by TinyLlama 1.1B • Real-time Feedback Analysis</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()