import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch


st.set_page_config(
    page_title="Customer Feedback",
    page_icon="⭐",
    layout="centered"
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
    """Load existing feedback data"""
    if os.path.exists(DATA_FILE):
        try:
            return pd.read_csv(DATA_FILE)
        except:
            return pd.DataFrame(columns=['id', 'timestamp', 'rating', 'review', 'ai_response'])
    return pd.DataFrame(columns=['id', 'timestamp', 'rating', 'review', 'ai_response'])


def save_feedback(rating, review, ai_response):
    df = load_data()
    
    new_entry = {
        'id': int(datetime.now().timestamp() * 1000),
        'timestamp': datetime.now().isoformat(),
        'rating': rating,
        'review': review,
        'ai_response': ai_response,
        'summary': '',  # Will be filled by admin
        'actions': ''   # Will be filled by admin
    }
    
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    return True


def generate_ai_response(rating, review):
    try:
        if rating >= 4:
            system_msg = "You are a friendly customer service representative responding to positive feedback. Be warm and grateful."
        elif rating == 3:
            system_msg = "You are a customer service representative responding to neutral feedback. Be understanding and encouraging."
        else:
            system_msg = "You are an empathetic customer service representative responding to negative feedback. Be apologetic and solution-focused."
        
        prompt = f"""<|system|>
{system_msg}
</s>
<|user|>
A customer gave us {rating} out of 5 stars and wrote: "{review}"

Write a brief, professional response (2-3 sentences).
</s>
<|assistant|>
"""
        
        # Tokenize
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        
        if torch.cuda.is_available():
            inputs = inputs.to("cuda")
        
        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=100,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # Decode
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract only the assistant's response
        if "<|assistant|>" in response:
            response = response.split("<|assistant|>")[-1].strip()
        
        # Clean up
        response = response.replace("</s>", "").strip()
        
        # If response is too short or empty, use fallback
        if len(response) < 10:
            raise Exception("Response too short")
        
        return response
    
    except Exception as e:
        print(f"AI Error: {e}")
        if rating >= 4:
            return "Thank you so much for your wonderful feedback! We're thrilled to hear you had a great experience with us. We look forward to serving you again!"
        elif rating == 3:
            return "Thank you for your feedback. We appreciate you taking the time to share your experience. We're always working to improve and hope to exceed your expectations next time!"
        else:
            return "We sincerely apologize for not meeting your expectations. Your feedback is invaluable to us, and we're committed to making things right. Please reach out to our support team so we can address your concerns directly."


# CUSTOM CSS

st.markdown("""
<style>
    /* Main container */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Card styling */
    .feedback-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        margin: 2rem 0;
    }
    
    /* Success message */
    .success-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
    }
    
    /* Star rating */
    .star-rating {
        font-size: 3rem;
        text-align: center;
        margin: 1rem 0;
    }
    
    /* Button styling */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-size: 1.1rem;
        border-radius: 10px;
        width: 100%;
        font-weight: 600;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    /* Text area */
    .stTextArea textarea {
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        font-size: 1rem;
    }
    
    /* Headers */
    h1 {
        color: white;
        text-align: center;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        color: white;
        text-align: center;
        font-size: 1.2rem;
        margin-bottom: 2rem;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# MAIN APP

def main():
    # Header
    st.markdown("<h1>⭐ Share Your Experience</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>We value your feedback and strive to improve</p>", unsafe_allow_html=True)
    
    # Initialize session state
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False
    if 'ai_response' not in st.session_state:
        st.session_state.ai_response = ""
    
    # Main feedback form
    with st.container():
        st.markdown("<div class='feedback-card'>", unsafe_allow_html=True)
        
        # Star Rating
        st.markdown("### 🌟 Rate Your Experience")
        rating = st.select_slider(
            "Select rating",
            options=[1, 2, 3, 4, 5],
            value=5,
            format_func=lambda x: "⭐" * x,
            label_visibility="collapsed"
        )
        
        # Display selected rating
        st.markdown(f"<div class='star-rating'>{'⭐' * rating}</div>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: #666; margin-top: -1rem;'>You selected {rating} star{'s' if rating != 1 else ''}</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Review Text
        st.markdown("### 📝 Tell Us More")
        review = st.text_area(
            "Share your experience with us...",
            height=150,
            placeholder="Tell us about your experience...",
            label_visibility="collapsed"
        )
        
        # Character count
        st.caption(f"{len(review)} characters")
        
        st.markdown("---")
        
        # Submit button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submit_button = st.button("🚀 Submit Feedback", use_container_width=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Handle submission
    if submit_button:
        if len(review.strip()) < 10:
            st.error("⚠️ Please write at least 10 characters in your review")
        else:
            with st.spinner("✨ Generating AI response..."):
                # Generate AI response
                ai_response = generate_ai_response(rating, review)
                
                # Save to CSV
                save_feedback(rating, review, ai_response)
                
                # Store in session state
                st.session_state.submitted = True
                st.session_state.ai_response = ai_response
    
    # Display success message
    if st.session_state.submitted:
        st.markdown("<div class='success-box'>", unsafe_allow_html=True)
        st.markdown("### ✅ Thank you for your feedback!")
        st.markdown(f"**Our Response:**")
        st.markdown(f"*{st.session_state.ai_response}*")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Reset button
        if st.button("📝 Submit Another Review"):
            st.session_state.submitted = False
            st.session_state.ai_response = ""
            st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: white; padding: 1rem;'>
        <p>Your feedback helps us serve you better</p>
        <p style='font-size: 0.9rem; opacity: 0.8;'>Powered by TinyLlama AI • Secure & Confidential</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()