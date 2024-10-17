import streamlit as st
import json
import openai
import time
import random
from utils.session_management import collect_session_data
from utils.firebase_operations import upload_to_firebase

def read_croup_txt():
    croup_info = {}
    with open("croup.txt", "r") as file:
        content = file.read().strip().split("\n\n")  # Split by double newlines (space)
        for block in content:
            lines = block.strip().split("\n")
            if len(lines) >= 2:
                question = lines[0].split("Q: ", 1)[1].strip().lower()  # Get question
                answer = lines[1].split("A: ", 1)[1].strip().lower()    # Get answer
                croup_info[question] = answer
    return croup_info

# Load the document content
croup_info = read_croup_txt()

def get_chatgpt_response(user_input):
    user_input_lower = user_input.lower()
    
    alternative_responses = [
        "I'm not sure about that.",
        "I don't have that information.",
        "That's a good question, but I don't know.",
        "I'm not certain.",
    ]

    if user_input_lower in croup_info:
        answer = croup_info[user_input_lower]
        # Return the answer directly without calling the API
        return answer
    else:
        return random.choice(alternative_responses)


def load_existing_data(db, document_id):
    """Load existing questions and responses from Firebase."""
    collection_name = st.secrets["FIREBASE_COLLECTION_NAME"]
    user_data = db.collection(collection_name).document(document_id).get()
    
    if user_data.exists:
        return user_data.to_dict().get("questions_asked", []), user_data.to_dict().get("responses", [])
    return [], []

def remove_duplicates(questions, responses):
    """Remove duplicates from questions and responses."""
    unique_questions = []
    unique_responses = []
    seen = set()

    for question, response in zip(questions, responses):
        if question not in seen:
            unique_questions.append(question)
            unique_responses.append(response)
            seen.add(question)

    return unique_questions, unique_responses

def run_virtual_patient(db, document_id):
    st.title("Virtual Patient")

    st.info(
        "You will have the opportunity to perform a history and ask for important physical examination details. "
        "You will be limited to 15 minutes. Alternatively, you may end the session and move to the next page."
    )

    if 'start_time' not in st.session_state or st.session_state.start_time is None:
        st.session_state.start_time = time.time()

    if 'session_data' not in st.session_state:
        st.session_state.session_data = {
            'questions_asked': [],
            'responses': []
        }

    # Load existing data from Firebase
    existing_questions, existing_responses = load_existing_data(db, document_id)
    st.session_state.session_data['questions_asked'].extend(existing_questions)
    st.session_state.session_data['responses'].extend(existing_responses)

    # Remove duplicates
    st.session_state.session_data['questions_asked'], st.session_state.session_data['responses'] = remove_duplicates(
        st.session_state.session_data['questions_asked'], 
        st.session_state.session_data['responses']
    )

    # Display existing questions and responses in the sidebar
    with st.sidebar:
        st.header("Questions and Responses")
        for question, response in zip(st.session_state.session_data['questions_asked'], st.session_state.session_data['responses']):
            st.write(f"**Q:** {question}")
            st.write(f"**A:** {response}")

    elapsed_time = (time.time() - st.session_state.start_time) / 60

    if elapsed_time < 15:
        with st.form("question_form", clear_on_submit=True):
            user_input = st.text_input("Ask the virtual patient typical history questions you would want to know for this case:")
            submit_button = st.form_submit_button("Ask")

            if submit_button and user_input:
                # Process the user input
                st.session_state.session_data['questions_asked'].append(user_input)

                virtual_patient_response = get_chatgpt_response(user_input)
                st.session_state.session_data['responses'].append(virtual_patient_response)

                # Clear the input field
                st.rerun()

                # Display the new response
                st.write(f"Virtual Patient: {virtual_patient_response}")

                # Collect session data and prepare for upload to Firebase
                entry = collect_session_data()  # Collect session data
                entry['questions_asked'] = st.session_state.session_data['questions_asked']
                entry['responses'] = st.session_state.session_data['responses']  # Include responses

                # Upload to Firebase
                try:
                    upload_message = upload_to_firebase(db, document_id, entry)
                    st.success("Your questions have been saved successfully.")
                except Exception as e:
                    st.error(f"Error uploading data: {e}")

    else:
        st.warning("Session time is up. Please end the session.")

    if st.button("End History Taking Session", key="end_session_button"):
        entry = collect_session_data()  # Collect session data
        entry['questions_asked'] = st.session_state.session_data['questions_asked']
        entry['responses'] = st.session_state.session_data['responses']
        
        # Upload to Firebase
        try:
            upload_message = upload_to_firebase(db, document_id, entry)
            st.success("Your questions have been saved successfully.")
        except Exception as e:
            st.error(f"Error uploading data: {e}")

        st.session_state.start_time = None
        st.session_state.page = "Focused Physical Examination"
        st.write("Session ended. You can start a new session.")
        st.rerun()

if __name__ == '__main__':
    run_virtual_patient(db, document_id)


