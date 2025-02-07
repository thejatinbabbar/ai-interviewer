import asyncio
import os
import threading

import httpx
import requests
import streamlit as st

FASTAPI_BASE_URL = os.environ["BACKEND_URL"]
START_URL = f"{FASTAPI_BASE_URL}/start"
CHAT_URL = f"{FASTAPI_BASE_URL}/generate_question"
FINISH_URL = f"{FASTAPI_BASE_URL}/generate_evaluation"


def initialize_session() -> None:
    """Initialize session_state variables if they do not exist."""
    if "phase" not in st.session_state:
        st.session_state.phase = "form"
    if "user_info" not in st.session_state:
        st.session_state.user_info = {}
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "finish_interview" not in st.session_state:
        st.session_state.finish_interview = False


def call_start_endpoint(user_info: dict) -> str:
    """
    Call the start endpoint to get the first interview question.

    Args:
        user_info: Candidate information.

    Returns:
        str: The starting question.
    """
    response = requests.post(START_URL, json=user_info)
    response.raise_for_status()
    data = response.json()
    return data["question"]


async def call_chat_endpoint(user_response: str) -> dict:
    """
    Asynchronously call the chat endpoint to generate the next interview question.

    Args:
        user_response (str): The candidate's text response.

    Returns:
        The response data including the question.
    """
    async with httpx.AsyncClient(timeout=None) as client:
        payload = {"user_input": user_response}
        response = await client.post(CHAT_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        return data


async def call_finish_endpoint() -> dict:
    """
    Asynchronously call the finish endpoint to complete the interview.

    Returns:
        dict: The data returned after finishing the interview.
    """
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(FINISH_URL)
        response.raise_for_status()
        data = response.json()
        return data


def finish_in_background() -> None:
    """Run the finish endpoint call in a background thread."""
    asyncio.run(call_finish_endpoint())


def reset_app() -> None:
    """Reset all session state variables and reload the app."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# Initialize the user session.
initialize_session()

# Render the form if in the initial phase.
if st.session_state.phase == "form":
    st.sidebar.header("Enter Your Information")
    with st.sidebar.form(key="user_info_form"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        role = st.text_input("Role")
        submitted = st.form_submit_button("Submit")
        if submitted:
            if not name or not email or not role:
                st.sidebar.error("All fields are required!")
            else:
                st.session_state.phase = "chat"
                user_info = {"name": name, "email": email, "role": role}
                st.session_state.user_info = user_info
                with st.spinner("Starting the interview..."):
                    start_response = call_start_endpoint(user_info)
                    if start_response:
                        st.session_state.chat_history.append(
                            {
                                "role": "assistant",
                                "content": start_response,
                            }
                        )
                    else:
                        st.sidebar.error("Failed to start the interview. Please try again.")
                st.rerun()

# Render the chat interface.
if st.session_state.phase == "chat":
    st.title("AI Interviewer Chat")
    # Display each message in the chat history.
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    if st.session_state.finish_interview:
        st.info("The interview is complete. Please click 'Finish Interview' to submit your responses.")
        if st.button("Finish Interview"):
            with st.spinner("Finishing the interview..."):
                threading.Thread(target=finish_in_background, daemon=True).start()
                st.session_state.phase = "finished"
            st.rerun()
    else:
        user_input = st.chat_input("Your Response", key="chat_input")
        if user_input:
            with st.spinner("..."):
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                chat_data = asyncio.run(call_chat_endpoint(user_input))
                st.session_state.chat_history.append({"role": "assistant", "content": chat_data["question"]})
                if chat_data.get("finish_interview", False):
                    st.session_state.finish_interview = True
            st.rerun()

if st.session_state.phase == "finished":
    st.title("Thank You for Participating in the Interview!")
    st.write("Your interview has been completed.")
    if st.button("Restart Interview"):
        reset_app()
