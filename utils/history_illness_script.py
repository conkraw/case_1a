import streamlit as st
from utils.session_management import collect_session_data  # Need this
from utils.firebase_operations import upload_to_firebase  

# Function to read diagnoses from a file
def read_diagnoses_from_file():
    try:
        with open('dx_list.txt', 'r') as file:
            diagnoses = [line.strip() for line in file.readlines() if line.strip()]
        return diagnoses
    except Exception as e:
        st.error(f"Error reading dx_list.txt: {e}")
        return []

# Function to read historical features from a file
def read_historical_features_from_file():
    try:
        with open('hx_f.txt', 'r') as file:
            features = [line.strip() for line in file.readlines() if line.strip()]
        return features
    except Exception as e:
        st.error(f"Error reading hx_f.txt: {e}")
        return []

def load_historical_features(db, document_id):
    """Load existing historical features from Firebase."""
    collection_name = st.secrets["FIREBASE_COLLECTION_NAME"]
    user_data = db.collection(collection_name).document(document_id).get()
    if user_data.exists:
        hxfeatures = user_data.to_dict().get('hxfeatures', {})
        historical_features = [""] * 5  # Default to empty for 5 features
        dropdown_defaults = {diagnosis: [""] * 5 for diagnosis in hxfeatures}  # Prepare default dropdowns
        
        # Populate historical features based on your structure
        for diagnosis, features in hxfeatures.items():
            for i, feature in enumerate(features):
                if i < len(historical_features):  # Ensure we stay within bounds
                    historical_features[i] = feature['historical_feature']
                    dropdown_defaults[diagnosis][i] = feature['hxfeature']  # Set dropdown default values
        
        return historical_features, dropdown_defaults
    else:
        return [""] * 5, {}  # Default to empty if no data

def main(db, document_id):
    # Initialize session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "historical_features"
    if 'diagnoses' not in st.session_state:
        st.session_state.diagnoses = [""] * 5
    if 'historical_features' not in st.session_state:
        st.session_state.historical_features, st.session_state.dropdown_defaults = load_historical_features(db, document_id)

    # Title of the app
    st.title("Historical Features Illness Script")

    # Historical Features Page
    if st.session_state.current_page == "historical_features":
        st.markdown("""
            ### Historical Features
            Please provide up to 5 historical features that influence the differential diagnosis.
        """)

        # Load diagnoses
        st.subheader("Diagnoses")
        st.session_state.diagnoses = read_diagnoses_from_file()
        for diagnosis in st.session_state.diagnoses:
            st.markdown(f"- {diagnosis}")

        # Display historical features with input and buttons
        for i in range(5):
            cols = st.columns(len(st.session_state.diagnoses) + 1)
            with cols[0]:
                # Input for partial matching
                partial_input = st.text_input(f"Feature {i + 1} (type to search)", key=f"hist_row_{i}")

                # Load available historical features based on the input
                available_features = read_historical_features_from_file()

                if partial_input:
                    filtered_options = [feature for feature in available_features if partial_input.lower() in feature.lower()]
                    if filtered_options:
                        st.write("**Available Options:**")
                        for option in filtered_options:
                            if st.button(option, key=f"btn_{i}_{option}"):
                                st.session_state.historical_features[i] = option
                                st.rerun()  # Refresh the input field

            for diagnosis, col in zip(st.session_state.diagnoses, cols[1:]):
                with col:
                    # Render dropdown for hxfeatures
                    dropdown_value = st.session_state.dropdown_defaults.get(diagnosis, [""] * 5)[i]
                    st.selectbox(
                        f"hxfeatures for {diagnosis}",
                        options=["", "Supports", "Does not support"],
                        index=0 if dropdown_value not in ["Supports", "Does not support"] else ["", "Supports", "Does not support"].index(dropdown_value),
                        key=f"select_{i}_{diagnosis}_hist",
                        label_visibility="collapsed"
                    )

        # Submit button for historical features
        if st.button("Submit", key="hx_features_submit_button"):
            if not any(st.session_state.historical_features):
                st.error("Please enter at least one historical feature.")
            else:
                entry = {
                    'hxfeatures': {},
                    'diagnoses': st.session_state.diagnoses
                }

                for i in range(5):
                    for diagnosis in st.session_state.diagnoses:
                        hxfeature = st.session_state[f"select_{i}_{diagnosis}_hist"]
                        if diagnosis not in entry['hxfeatures']:
                            entry['hxfeatures'][diagnosis] = []
                        entry['hxfeatures'][diagnosis].append({
                            'historical_feature': st.session_state.historical_features[i],
                            'hxfeature': hxfeature
                        })
                
                # Upload to Firebase
                upload_message = upload_to_firebase(db, document_id, entry)
                st.success("Historical features submitted successfully.")
                st.rerun()  # Rerun to refresh the app

