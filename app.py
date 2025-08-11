import streamlit as st
import h2o
import pandas as pd
import re

# --- Initialize H2O and load your model ---
h2o.init(max_mem_size="2G")  # limit memory if needed
model_path = "GBM_grid_1_AutoML_1_20250730_201105_model_4"  # <-- change to your model path
loaded_model = h2o.load_model(model_path)

st.set_page_config(page_title="❤️ Heart Disease Chatbot", page_icon="❤️", layout="wide")

# --- Feature explanations ---
feature_info = {
    "ATA": "**Typical Angina (ATA)** 🫀: Classic chest pain with exertion, relieved by rest.",
    "NAP": "**Non-Anginal Pain (NAP)** 💭: Chest pain not typical of heart disease.",
    "ASY": "**Asymptomatic (ASY)** 😌: No chest pain symptoms.",
    "TA": "**Atypical Angina (TA)** 🤔: Chest pain not classic but may indicate heart issues.",
    "ExerciseAngina": "**Exercise Induced Angina** 🏃‍♀️: Chest pain with exercise.",
    "FastingBS": "**Fasting Blood Sugar** 🍬: >120 mg/dl may signal diabetes.",
    "ChestPainType": "**Types of Chest Pain** 💔: Helps differentiate heart-related pain.",
    "Age": "**Age** 🎂: Risk increases with age.",
    "Sex": "**Biological Sex** ⚧️: Men develop heart disease earlier.",
    "RestingBP": "**Resting Blood Pressure** 🩺: Normal <120/80 mmHg.",
    "Cholesterol": "**Cholesterol** 🧪: High levels clog arteries.",
    "RestingECG": "**Resting ECG** 📈: Heart electrical activity at rest.",
    "MaxHR": "**Max Heart Rate** ❤️‍🔥: Highest during exercise.",
    "Oldpeak": "**ST Depression** 📉: Electrical changes during exercise.",
    "ST_Slope": "**ST Segment Slope** 📊: Up slope usually better."
}

# --- Required fields with prompts and validation ranges ---
required_fields = [
    ("Age", "What's your age? 🎂 (20-100)", (20, 100)),
    ("Sex", "What's your biological sex? 👤 ('M' or 'F')", None),
    ("ChestPainType", "Type of chest pain? 💔 (ATA, NAP, ASY, TA)\n(Type 'what is ATA' for details)", None),
    ("RestingBP", "Resting blood pressure? 🩺 (90-200 mmHg, or 'unknown')", (90, 200)),
    ("Cholesterol", "Cholesterol level? 🧪 (100-400 mg/dl, or 'unknown')", (0, 600)),
    ("FastingBS", "Is fasting blood sugar >120 mg/dl? 🍬 (Yes/No/unknown)", None),
    ("RestingECG", "Resting ECG result? 📈 (Normal, ST, LVH)\n(Default is 'Normal')", None),
    ("MaxHR", "Maximum heart rate during exercise? ❤️‍🔥 (60-220 bpm; estimate 220-age if unknown)", (60, 220)),
    ("ExerciseAngina", "Exercise-induced angina? 🏃‍♀️ (Yes or No)", None),
    ("Oldpeak", "ST depression value? 📉 (0-6; 0 if unknown)", (0, 6)),
    ("ST_Slope", "ST segment slope during exercise? 📊 (Up, Flat, Down)", None)
]

# --- Clean labels for fast fill-all-at-once mode ---
simple_labels = {
    "Age": "What's your age? 🎂",
    "Sex": "What's your biological sex? 👤",
    "ChestPainType": "Type of chest pain? 💔",
    "RestingBP": "Resting blood pressure? 🩺",
    "Cholesterol": "Cholesterol level? 🧪",
    "FastingBS": "Is fasting blood sugar >120 mg/dl? 🍬",
    "RestingECG": "Resting ECG result? 📈",
    "MaxHR": "Maximum heart rate during exercise? ❤️‍🔥",
    "ExerciseAngina": "Exercise-induced angina? 🏃‍♀️",
    "Oldpeak": "ST depression value? 📉",
    "ST_Slope": "ST segment slope during exercise? 📊"
}

# --- Utility functions ---
def build_patient_info(user_dict):
    defaults = {
        'Age': 50, 'Sex': 'M', 'ChestPainType': 'ASY', 'RestingBP': 120,
        'Cholesterol': 200, 'FastingBS': 0, 'RestingECG': 'Normal',
        'MaxHR': 150, 'ExerciseAngina': 'N', 'Oldpeak': 1.0, 'ST_Slope': 'Up'
    }
    info = {}
    for k, default in defaults.items():
        info[k] = user_dict.get(k, default)
    return info

def display_risk(prob_pct):
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"### 🎯 Heart Disease Risk: **{prob_pct:.1f}%**")
        st.progress(min(prob_pct / 100, 1.0))
        if prob_pct > 70:
            st.error("🚨 **HIGH Risk** - Please consult a cardiologist immediately!")
        elif prob_pct > 40:
            st.warning("⚠️ **MODERATE Risk** - Schedule a check-up with your doctor soon.")
        elif prob_pct > 20:
            st.info("💙 **LOW-MODERATE Risk** - Consider a routine health check.")
        else:
            st.success("💚 **LOW Risk** - Keep up the great work with your health!")
    with col2:
        if prob_pct > 70:
            st.markdown("### 🔴")
        elif prob_pct > 40:
            st.markdown("### 🟡")
        else:
            st.markdown("### 🟢")

def show_personalized_tips(info, prob_pct):
    st.markdown("---")
    st.subheader("🎯 Personalized Health Recommendations")
    tips = []
    if info['Cholesterol'] > 240:
        tips.append("🥗 **Cholesterol Management**: Consider a heart-healthy diet low in saturated fats and regular exercise.")
    if info['RestingBP'] > 140:
        tips.append("🩺 **Blood Pressure**: Monitor regularly and discuss management with your doctor.")
    elif info['RestingBP'] > 130:
        tips.append("📊 **Blood Pressure**: Elevated - keep monitoring.")
    if info['FastingBS'] == 1:
        tips.append("🍬 **Blood Sugar**: Manage diabetes risk with your healthcare provider.")
    if info['ExerciseAngina'] == 'Y':
        tips.append("🏃‍♀️ **Exercise**: Discuss safe plans with your doctor.")
    if info['MaxHR'] < 100:
        tips.append("❤️ **Fitness**: Gradually increase cardiovascular fitness (doctor-approved).")
    if info['Oldpeak'] > 2.0:
        tips.append("🔍 **Follow-up**: Discuss stress test results with cardiologist.")
    if not tips:
        tips.append("🌟 **Great Job!** Maintain your healthy lifestyle!")
    if prob_pct > 40:
        tips.append("🚨 **Important**: Elevated risk. Consult healthcare professional promptly.")
    elif prob_pct > 20:
        tips.append("💙 **Note**: Consider discussing with your doctor at next visit.")
    else:
        tips.append("✅ **Note**: Low risk but regular checkups are recommended.")
    for i, tip in enumerate(tips, 1):
        st.markdown(f"**{i}.** {tip}")

def show_progress():
    progress = len(st.session_state.user_data) / len(required_fields)
    st.progress(progress, f"Progress: {len(st.session_state.user_data)}/{len(required_fields)} questions completed")

def validate_input(current_key, user_text, validation_range=None):
    user_lower = user_text.lower().strip()
    try:
        if current_key in ['FastingBS', 'ExerciseAngina']:
            if any(w in user_lower for w in ["yes", "y", "1", "true", "positive"]):
                return (1 if current_key == 'FastingBS' else 'Y'), None
            elif any(w in user_lower for w in ["no", "n", "0", "false", "negative"]):
                return (0 if current_key == 'FastingBS' else 'N'), None
            elif "unknown" in user_lower or "not sure" in user_lower:
                default_val = 0 if current_key == 'FastingBS' else 'N'
                return default_val, f"No worries! Using '{default_val}' as default. 👍"
            else:
                return None, f"Please answer 'Yes', 'No' or 'unknown'."
        elif current_key == 'Sex':
            if user_lower in ['m', 'male']:
                return 'M', None
            elif user_lower in ['f', 'female']:
                return 'F', None
            else:
                return None, "Please enter 'M' or 'F'."
        elif current_key == 'ChestPainType':
            pain_types = {'ata': 'ATA', 'nap': 'NAP', 'asy': 'ASY', 'ta': 'TA'}
            if user_lower in pain_types:
                return pain_types[user_lower], None
            else:
                return None, "Enter one of ATA, NAP, ASY, TA."
        elif current_key == 'RestingECG':
            ecg_types = {'normal': 'Normal', 'st': 'ST', 'lvh': 'LVH'}
            if user_lower in ecg_types:
                return ecg_types[user_lower], None
            else:
                return None, "Enter Normal, ST, or LVH."
        elif current_key == 'ST_Slope':
            slope_types = {'up': 'Up', 'flat': 'Flat', 'down': 'Down'}
            if user_lower in slope_types:
                return slope_types[user_lower], None
            else:
                return None, "Enter Up, Flat, or Down."
        else:  # Numeric
            if "unknown" in user_lower or "not sure" in user_lower:
                defaults_for_unknown = {
                    'Age': 50,
                    'RestingBP': 120,
                    'Cholesterol': 200,
                    'MaxHR': 150,
                    'Oldpeak': 1.0
                }
                default_val = defaults_for_unknown.get(current_key, 0)
                return default_val, f"Using {default_val} as default."
            val_float = float(user_text)
            if validation_range and (val_float < validation_range[0] or val_float > validation_range[1]):
                return None, f"Please enter a value between {validation_range[0]} and {validation_range[1]}."
            if current_key in ['Age', 'RestingBP', 'Cholesterol', 'MaxHR']:
                return int(val_float), None
            else:
                return val_float, None
    except Exception:
        return None, f"Invalid input format."

# --- Main UI ---

st.title("❤️ Heart Disease Risk Chatbot / Quick Form")

# Mode selection
mode = st.radio(
    "Choose how to input your data:",
    ("Step-by-step chat (recommended)", "Fill all at once (fastest)"),
    key="input_mode"
)

# Reset button
if st.button("🔄 Switch input mode / Start Over"):
    keys_to_clear = ['user_data', 'waiting_for', 'conversation_started', 'last_prediction', 'chat_history']
    for k in keys_to_clear:
        if k in st.session_state:
            if k == 'user_data':
                st.session_state[k] = {}
            else:
                del st.session_state[k]
    st.experimental_rerun() if hasattr(st, 'experimental_rerun') else st.rerun()

# ========== FILL ALL AT ONCE ==========
if mode == "Fill all at once (fastest)" and 'last_prediction' not in st.session_state:
    st.markdown("### 🚀 Fast Mode: Fill All Questions")
    with st.form("full_form"):
        form_values = {}
        for key, label, vrange in required_fields:
            clean_label = simple_labels.get(key, label)
            if key == "Sex":
                val = st.selectbox(clean_label, options=["M", "F"])

            elif key == "ChestPainType":
                val = st.selectbox(
                    clean_label,
                    options=["ATA", "NAP", "ASY", "TA"],
                    help="ATA: Typical Angina, NAP: Non-Anginal Pain, ASY: Asymptomatic, TA: Atypical Angina"
                )

            elif key == "RestingECG":
                val = st.selectbox(
                    clean_label,
                    options=["Normal", "ST", "LVH"],
                    help="Normal: Normal ECG, ST: ST-T wave abnormality, LVH: Left Ventricular Hypertrophy"
                )

            elif key == "ExerciseAngina":
                val = st.radio(clean_label, options=["Yes", "No"], horizontal=True)
                val = 'Y' if val == "Yes" else 'N'

            elif key == "FastingBS":
                val = st.radio(
                    clean_label,
                    options=["Yes", "No"],
                    horizontal=True
                )
                val = 1 if val == "Yes" else 0

            elif key == "ST_Slope":
                val = st.selectbox(
                    clean_label,
                    options=["Up", "Flat", "Down"]
                )

            elif vrange:
                minv, maxv = vrange
                input_val = st.text_input(f"{clean_label}")
                try:
                    val = float(input_val)
                    if val < minv or val > maxv:
                        st.warning(f"{clean_label} must be between {minv} and {maxv}")
                    if key in ['Age', 'RestingBP', 'Cholesterol', 'MaxHR']:
                        val = int(val)
                except:
                    val = minv  # fallback
            else:
                val = st.text_input(clean_label)
            form_values[key] = val

        submitted = st.form_submit_button("Calculate Risk")

    if submitted:
        patient_info = build_patient_info(form_values)
        df = pd.DataFrame([patient_info])
        hf = h2o.H2OFrame(df)
        for c in ['Sex', 'ChestPainType', 'RestingECG', 'ExerciseAngina', 'ST_Slope']:
            hf[c] = hf[c].asfactor()
        pred = loaded_model.predict(hf)
        prob_yes = pred['p1'][0, 0]
        prob_pct = prob_yes * 100
        st.session_state['last_prediction'] = (prob_pct, patient_info)
        st.rerun()

# ========== STEP-BY-STEP CHAT MODE ==========
elif mode == "Step-by-step chat (recommended)" or 'last_prediction' in st.session_state:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "bot",
             "content": "Hello! 👋 I'm your Heart Health Assistant! 🫀\n\n"
                        "I'll help assess your heart disease risk by asking about your health. Don't worry - this takes just a few minutes, and I'll explain everything along the way! 😊\n\n"
                        "Type **'help'** anytime for assistance, or **'what is [term]'** for explanations.\n\n"
                        "Ready to start? Just say 'yes' or 'let's go'! 🚀"}
        ]
        st.session_state.user_data = {}
        st.session_state.waiting_for = None
        st.session_state.conversation_started = False
        st.session_state.progress_count = 0

    def add_bot_message(msg):
        st.session_state.chat_history.append({"role": "bot", "content": msg})

    def add_user_message(msg):
        st.session_state.chat_history.append({"role": "user", "content": msg})

    if st.session_state.user_data:
        show_progress()

    st.markdown("### 💬 Chat")
    chat_container = st.container()
    with chat_container:
        for chat in st.session_state.chat_history:
            if chat["role"] == "bot":
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(chat["content"])
            else:
                with st.chat_message("user", avatar="👤"):
                    st.markdown(chat["content"])

    user_message = st.chat_input("Type your message here... 💭", disabled='last_prediction' in st.session_state)
    if user_message:
        add_user_message(user_message)
        user_text = user_message.strip()
        user_lower = user_text.lower()

        # Help command
        if user_lower in ['help', 'h', '?']:
            help_msg = (
                "🆘 **Help Menu:**\n\n"
                "• Type **'what is [term]'** for explanations (e.g., 'what is ATA')\n"
                "• Type **'restart'** to start over\n"
                "• Type **'skip'** to use default values for current question\n"
                "• For yes/no questions: 'yes', 'no', or 'unknown'\n"
                "I'm here to help! 😊"
            )
            add_bot_message(help_msg)
            st.rerun()

        # Restart command
        elif user_lower in ['restart', 'reset', 'start over']:
            st.session_state.user_data = {}
            st.session_state.waiting_for = None
            st.session_state.conversation_started = False
            if 'last_prediction' in st.session_state:
                del st.session_state['last_prediction']
            add_bot_message("🔄 Let's start fresh. Ready? Say 'yes' or 'let's go'.")
            st.rerun()

        # Explanation commands
        else:
            explained = False
            for term, explanation in feature_info.items():
                if re.search(fr"what is {term.lower()}", user_lower) or re.search(fr"explain {term.lower()}", user_lower):
                    add_bot_message(f"📚 **{term} Explanation:**\n\n{explanation}")
                    explained = True
                    break

            if not explained:
                # Start conversation after user says yes
                if not st.session_state.conversation_started and any(w in user_lower for w in ['yes', 'go', 'start', 'let\'s go', 'sure']):
                    st.session_state.conversation_started = True
                    first_key = required_fields[0][0]
                    st.session_state.waiting_for = first_key
                    add_bot_message(f"Great! Let's start.\n\n**Question 1/{len(required_fields)}:** {required_fields[0][1]}")
                    st.rerun()

                # Handle question flow
                elif st.session_state.waiting_for:
                    current_key = st.session_state.waiting_for
                    current_field_info = next((f for f in required_fields if f[0] == current_key), None)
                    validation_range = current_field_info[2] if current_field_info else None

                    if user_lower in ["skip", "pass", "default"]:
                        defaults = {
                            'Age': 50, 'Sex': 'M', 'ChestPainType': 'ASY', 'RestingBP': 120,
                            'Cholesterol': 200, 'FastingBS': 0, 'RestingECG': 'Normal',
                            'MaxHR': 150, 'ExerciseAngina': 'N', 'Oldpeak': 1.0, 'ST_Slope': 'Up'
                        }
                        st.session_state.user_data[current_key] = defaults[current_key]
                        add_bot_message(f"👍 Using default for {current_key}, moving on...")
                    else:
                        validated_value, err_msg = validate_input(current_key, user_text, validation_range)
                        if validated_value is not None:
                            st.session_state.user_data[current_key] = validated_value
                            add_bot_message(f"✅ Recorded {current_key}. {err_msg or ''}".strip())
                        else:
                            add_bot_message(err_msg)
                            st.rerun()

                    # Determine next question or finish
                    if current_key in st.session_state.user_data:
                        current_index = next(i for i, (f, _, _) in enumerate(required_fields) if f == current_key)
                        next_field = None
                        for j in range(current_index + 1, len(required_fields)):
                            if required_fields[j][0] not in st.session_state.user_data:
                                next_field = required_fields[j][0]
                                break
                        if next_field:
                            st.session_state.waiting_for = next_field
                            q_num = len(st.session_state.user_data) + 1
                            # Important: keep full label here!
                            next_label = next((lab for k, lab, _ in required_fields if k == next_field), "")
                            add_bot_message(f"**Question {q_num}/{len(required_fields)}:** {next_label}")
                        else:
                            # All done
                            add_bot_message("🎉 All done! Analyzing your data now...")
                            st.session_state.waiting_for = None
                            try:
                                patient_info = build_patient_info(st.session_state.user_data)
                                df = pd.DataFrame([patient_info])
                                hf = h2o.H2OFrame(df)
                                for c in ['Sex', 'ChestPainType', 'RestingECG', 'ExerciseAngina', 'ST_Slope']:
                                    hf[c] = hf[c].asfactor()
                                pred = loaded_model.predict(hf)
                                prob_yes = pred['p1'][0, 0]
                                prob_pct = prob_yes * 100
                                st.session_state['last_prediction'] = (prob_pct, patient_info)
                                add_bot_message(f"✨ Prediction complete! Your heart disease risk is **{prob_pct:.1f}%**.\n\nSee below for your results.")
                            except Exception as e:
                                add_bot_message(f"⚠️ Prediction error: {str(e)}\nPlease try restarting.")
                    st.rerun()
                else:
                    if not st.session_state.conversation_started:
                        add_bot_message("Hi! Ready to start? Just say 'yes' or 'let's go'!")
                    else:
                        add_bot_message("I didn't understand that. Type 'help' for instructions.")
                    st.rerun()

# --- Result display (shared) ---
if 'last_prediction' in st.session_state:
    st.markdown("---")
    st.markdown("## 📊 Your Heart Health Assessment Results")
    prob_pct, patient_info = st.session_state['last_prediction']
    display_risk(prob_pct)
    show_personalized_tips(patient_info, prob_pct)

    with st.expander("🔍 View Your Input Data", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.json(patient_info)
        with col2:
            st.markdown("### 📈 Quick Summary:")
            st.write(f"• Age: {patient_info['Age']} years")
            st.write(f"• Sex: {patient_info['Sex']}")
            st.write(f"• Chest Pain Type: {patient_info['ChestPainType']}")
            st.write(f"• Blood Pressure: {patient_info['RestingBP']} mmHg")
            st.write(f"• Cholesterol: {patient_info['Cholesterol']} mg/dl")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 New Assessment"):
            keys_to_clear = ['user_data', 'waiting_for', 'conversation_started', 'last_prediction', 'chat_history']
            for k in keys_to_clear:
                if k in st.session_state:
                    if k == 'user_data':
                        st.session_state[k] = {}
                    else:
                        del st.session_state[k]
            st.experimental_rerun() if hasattr(st, 'experimental_rerun') else st.rerun()
    with col2:
        st.download_button(
            "📥 Download Results",
            data=f"Heart Disease Risk Assessment\nRisk: {prob_pct:.1f}%\nData: {patient_info}",
            file_name="heart_risk_assessment.txt",
            mime="text/plain"
        )
    with col3:
        if prob_pct > 40:
            st.markdown("**🏥 Next Steps:** Schedule a doctor visit!")
        elif prob_pct > 20:
            st.markdown("**💙 Next Steps:** Consider routine checkup.")
        else:
            st.markdown("**🌟 Next Steps:** Keep up healthy habits!")