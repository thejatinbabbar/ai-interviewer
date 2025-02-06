import streamlit as st
import requests

FASTAPI_BASE_URL = "http://llm:8000"
START_URL = f"{FASTAPI_BASE_URL}/start"
CHAT_URL = f"{FASTAPI_BASE_URL}/generate_question"
FINISH_URL = f"{FASTAPI_BASE_URL}/generate_evaluation"
MAX_QUESTIONS = 5

def initialize_session():
    if 'phase' not in st.session_state:
        st.session_state.phase = "form"
    if 'user_info' not in st.session_state:
        st.session_state.user_info = {}
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'question_count' not in st.session_state:
        st.session_state.question_count = 0

def call_start_endpoint(user_info: dict):
    try:
        response = requests.post(START_URL, json=user_info)
        response.raise_for_status()
        data = response.json()["question"]
        return data
    except Exception as e:
        st.error(f"Error calling start endpoint: {e}")
        return None

def call_chat_endpoint(user_response: str):
    try:
        payload = {"user_input": user_response}
        response = requests.post(CHAT_URL, json=payload)
        response.raise_for_status()
        data = response.json()["question"]
        return data
    except Exception as e:
        st.error(f"Error calling chat endpoint: {e}")
        return None

def call_finish_endpoint():
    try:
        response = requests.post(FINISH_URL)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        st.error(f"Error calling finish endpoint: {e}")
        return None

def reset_app():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

initialize_session()

if st.session_state.phase == "form":
    st.sidebar.header("Enter Your Information")
    with st.sidebar.form(key="user_info_form"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        age = st.text_input("Role")
        
        submitted = st.form_submit_button("Submit")
        if submitted:
            if not name or not email or age is None:
                st.sidebar.error("All fields are required!")
            else:
                st.session_state.phase = "chat"
                user_info = {"name": name, "email": email, "role": age}
                st.session_state.user_info = user_info
                with st.spinner("Starting the interview..."):
                    start_response = call_start_endpoint(user_info)
                    if start_response:
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": start_response,
                        })
                        st.session_state.question_count = 1
                    else:
                        st.sidebar.error("Failed to start the interview. Please try again.")

if st.session_state.phase == "chat":
    st.title("AI Interviewer Chat")
    
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    if st.session_state.question_count >= MAX_QUESTIONS:
        if st.button("Finish Interview"):
            with st.spinner("Finishing the interview..."):
                finish_response = call_finish_endpoint()
                st.session_state.phase = "finished"
    else:
        user_input = st.chat_input("Your Response", key="chat_input")
        if user_input:
            with st.spinner("..."):
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_input
                })
                
                chat_response = call_chat_endpoint(user_input)
                if chat_response:
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": chat_response,
                    })
                    st.session_state.question_count += 1
                else:
                    st.error("Failed to get a response from the AI.")

if st.session_state.phase == "finished":
    st.title("Thank You for Participating in the Interview!")
    st.write("Your interview has been completed.")
    if st.button("Restart Interview"):
        reset_app()
