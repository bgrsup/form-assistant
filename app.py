import streamlit as st
import requests
import json
import os

st.set_page_config(page_title="Compliance Form Assistant")
st.title("📄 Compliance Form Assistant")

# Logging helper
def log(message):
    st.text(f"🪵 {message}")

# ✅ Load secrets
try:
    APIFY_TOKEN = os.environ["APIFY_TOKEN"]
    APIFY_TASK_ID = os.environ["APIFY_TASK_ID"]  # e.g. "your-username~form-assistant-default"
    st.success("✅ Secrets loaded successfully!")
except KeyError as e:
    st.error(f"❌ Missing environment variable: {e}")
    st.stop()

uploaded_file = st.file_uploader("Upload a DOCX file to auto-fill", type=["docx"])

if uploaded_file:
    st.success("File uploaded! Preparing to send to Apify...")

    with open("temp_upload.docx", "wb") as f:
        f.write(uploaded_file.getbuffer())

    log("Saved uploaded file")

    # Upload to Apify task input
    log("Uploading file to Apify Task input...")
    with open("temp_upload.docx", "rb") as file_data:
        upload_res = requests.put(
            f"https://api.apify.com/v2/actor-tasks/{APIFY_TASK_ID}/input?token={APIFY_TOKEN}",
            files={"value": file_data},
            headers={"Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        )
    log(f"Upload response status: {upload_res.status_code}")
    if upload_res.status_code != 200:
        st.error(f"Upload failed: {upload_res.text}")
        st.stop()

    # Start the Apify task
    st.info("Running Apify task...")
    try:
        task_run = requests.post(
            f"https://api.apify.com/v2/actor-tasks/{APIFY_TASK_ID}/runs?token={APIFY_TOKEN}",
        )
        run_id = task_run.json()["data"]["id"]
        log(f"Task Run ID: {run_id}")
    except Exception as e:
        st.error(f"Failed to start task: {e}")
        st.stop()

    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        status_res = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}")
        status = status_res.json()["data"]["status"]
        log(f"Run status: {status}")

    log("Actor task complete")

    try:
        store_id = status_res.json()["data"]["defaultKeyValueStoreId"]
        output = requests.get(
            f"https://api.apify.com/v2/key-value-stores/{store_id}/records/output.json?token={APIFY_TOKEN}"
        )
        output_json = output.json()
        st.json(output_json)
    except Exception as e:
        st.error(f"Failed to retrieve output: {e}")
        st.stop()

    st.subheader("🤖 Unanswered Questions")
    unanswered = output_json.get("unknown_questions", {})
    if unanswered:
        responses = {}
        for q in unanswered:
            responses[q] = st.text_input(q)

        if st.button("Submit Answers & Finalize Form"):
            st.warning("In a real app, this would update the form with final answers and return the final file.")
    else:
        st.success("No unanswered questions! Your form is ready.")

    st.subheader("📎 Download Partially Filled Form")
    filled_url = f"https://api.apify.com/v2/key-value-stores/{store_id}/records/{output_json['filled_file'].split('/')[-1]}?token={APIFY_TOKEN}"
    st.markdown(f"[Download Filled Form]({filled_url})")
