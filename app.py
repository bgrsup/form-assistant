import streamlit as st
import requests
import json
import os

st.set_page_config(page_title="Compliance Form Assistant")
st.title("📄 Compliance Form Assistant")

def log(message):
    st.text(f"🪵 {message}")

# ✅ Load secrets
try:
    APIFY_TOKEN = os.environ["APIFY_TOKEN"]
    APIFY_TASK_ID = os.environ["APIFY_TASK_ID"]  # Format: username~task-name
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

    # Create a new key-value store
    store_res = requests.post(
        f"https://api.apify.com/v2/key-value-stores?token={APIFY_TOKEN}",
        json={"name": "streamlit-form-upload"}
    )
    store_id = store_res.json()["data"]["id"]
    log(f"Created store ID: {store_id}")

    # Upload file as INPUT
    with open("temp_upload.docx", "rb") as file_data:
        put_res = requests.put(
            f"https://api.apify.com/v2/key-value-stores/{store_id}/records/INPUT?token={APIFY_TOKEN}",
            files={"value": ("form.docx", file_data)},
            headers={"Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        )
    log(f"File upload status: {put_res.status_code}")
    if put_res.status_code != 200:
        st.error(f"Upload failed: {put_res.text}")
        st.stop()

    # Run the Apify task using this store
    run_res = requests.post(
        f"https://api.apify.com/v2/actor-tasks/{APIFY_TASK_ID}/runs?token={APIFY_TOKEN}",
        json={"keyValueStoreId": store_id}
    )
    run_id = run_res.json()["data"]["id"]
    log(f"Run ID: {run_id}")

    # Poll status
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        status_res = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}")
        status = status_res.json()["data"]["status"]
        log(f"Run status: {status}")

    log("Actor task complete")

    # Retrieve output
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

    # Display results
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
