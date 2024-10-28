import streamlit as st
from utils.file_operations import read_diagnoses_from_file
from utils.session_management import collect_session_data
from utils.firebase_operations import upload_to_firebase

def display_diagnoses(db, document_id):
    # Initialize the diagnoses session state if not present
    if 'diagnoses' not in st.session_state:
        # Load existing diagnoses from Firebase
        collection_name = st.secrets["FIREBASE_COLLECTION_NAME"]
        user_data = db.collection(collection_name).document(document_id).get()
        if user_data.exists:
            st.session_state.diagnoses = user_data.to_dict().get('diagnoses_s1', [""] * 5)
        else:
            st.session_state.diagnoses = [""] * 5  # Default to empty if no data

    # Check if assessment data exists
    if 'vs_data' not in st.session_state or not st.session_state.vs_data:
        st.error("Please complete the assessment before updating diagnoses.")
        return

    dx_options = read_diagnoses_from_file()

    st.markdown("""## DIFFERENTIAL DIAGNOSIS
    Please search and select 5 possible diagnoses for the condition you think the patient has in order of likelihood. You will be allowed to alter your choices as you go through the case.""")

    cols = st.columns(5)

    for i, col in enumerate(cols):
        with col:
            current_diagnosis = st.session_state.diagnoses[i]
            search_input = st.text_input(f"Diagnosis # {i + 1}", value=current_diagnosis, key=f"diagnosis_search_{i}")
    
            filtered_options = [dx for dx in dx_options if search_input.lower() in dx.lower()] if search_input else []
    
            if filtered_options:
                st.write("**Suggestions:**")
                for option in filtered_options[:5]:
                    button_key = f"select_option_{i}_{option}"
                    if st.button(f"{option}", key=button_key):
                        st.session_state.diagnoses[i] = option
                        st.rerun()
    
            # Handle deletion of a diagnosis
            if search_input == "" and current_diagnosis:
                st.session_state.diagnoses[i] = ""  # Clear the diagnosis in session state
                current_diagnosis = ""  # Update local variable to reflect the cleared state
    
            # Check if current diagnosis is now empty
            if current_diagnosis:
                st.write(f"**Selected:** {current_diagnosis}")

            if not filtered_options and search_input:
                st.warning("Please select a diagnosis from the suggestions. If there are no suggestions, please alter your search and try again.")

            # Handle deletion of a diagnosis
            if search_input == "" and current_diagnosis:
                st.session_state.diagnoses[i] = ""  # Revert to blank if deleted

            # Update the diagnoses in session state for persistence
            if current_diagnosis and current_diagnosis in dx_options:
                st.session_state.diagnoses[i] = current_diagnosis

    if st.button("Submit"):
        diagnoses = [d.strip() for d in st.session_state.diagnoses]
        if all(diagnosis for diagnosis in diagnoses):
            if len(diagnoses) == len(set(diagnoses)):
                session_data = collect_session_data()

                # Create entry with the diagnoses data, including last page
                entry = {
                    "diagnoses_s1": diagnoses,
                    "last_page": "diagnoses"  # Include the last_page in the entry
                }

                # Log the entry before uploading
                st.write("Uploading the following entry to Firebase:")

                try:
                    upload_message = upload_to_firebase(db, document_id, entry)
                    st.success("Diagnoses submitted successfully.")

                    st.session_state.page = "Intervention Entry"  # Set to next page
                    st.rerun()
                except Exception as e:
                    st.error(f"Error uploading data: {e}")
            else:
                st.error("Please do not provide duplicate diagnoses.")
        else:
            st.error("Please select all 5 diagnoses.")
