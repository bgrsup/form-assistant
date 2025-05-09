import streamlit as st
import requests
import json
import os

st.set_page_config(page_title="Compliance Form Assistant")
st.title("📄 Compliance Form Assistant")

def log(message):
    st.text(f"🪵 {message}")

# ✅ Load required secrets
try:
    APIFY_TOKEN = os.environ["APIFY_TOKEN"]
    APIFY_TASK_ID = os.environ["APIFY_TASK_ID"]  # e.g. "your-username~form-assistant-default"
    st.success("✅ Secrets loaded successfully!")
except KeyError as e:
    st.error(f"❌ Missing environment variable: {e}")
    st.stop()

# 📤 Upload section
uploaded_file = st.file_uploader("Upload a DOCX file to auto-fill", type=["docx"])

if uploaded_file:
    st.success("File uploaded! Preparing to send to Apify...")

    with open("temp_upload.docx", "wb") as f:
        f.write(uploaded_file.getbuffer())
    log("✅ Saved uploaded file to temp_upload.docx")

    # Create a new KV store
    log("📦 Creating temporary Apify key-value store...")
    kv_store_res = requests.post(
        f"https://api.apify.com/v2/key-value-stores?token={APIFY_TOKEN}",
        json={"name": "form-upload-store"}
    )
    kv_store_id = kv_store_res.json()["data"]["id"]
    log(f"🗂 Created KV store: {kv_store_id}")

    # Upload DOCX file to INPUT
    log("📤 Uploading DOCX to INPUT...")
    with open("temp_upload.docx", "rb") as file_data:
        put_res = requests.put(
            f"https://api.apify.com/v2/key-value-stores/{kv_store_id}/records/INPUT?token={APIFY_TOKEN}",
            files={"value": ("INPUT", file_data)},
            headers={"Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        )
    log(f"📥 Upload status: {put_res.status_code}")
    if put_res.status_code not in [200, 201]:
        st.error(f"❌ Upload failed: {put_res.text}")
        st.stop()

    # Start the task with the uploaded KV store
    st.info("🚀 Starting Apify Task...")
    task_res = requests.post(
        f"https://api.apify.com/v2/actor-tasks/{APIFY_TASK_ID}/runs?token={APIFY_TOKEN}",
        json={
            "keyValueStoreId": kv_store_id,
            "input": { "useInputFile": True }
        },
        headers={"Content-Type": "application/json"}
    )
    run_id = task_res.json()["data"]["id"]
    log(f"🧠 Task Run ID: {run_id}")

    # Poll run status
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        status_res = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}")
        status = status_res.json()["data"]["status"]
        log(f"⏳ Task status: {status}")

    st.success("✅ Task finished!")

    # Get output.json from KV store
    try:
        output_res = requests.get(
            f"https://api.apify.com/v2/key-value-stores/{kv_store_id}/records/output.json?token={APIFY_TOKEN}"
        )
        output_json = output_res.json()
        st.json(output_json)
    except Exception as e:
        st.error(f"❌ Failed to fetch output: {e}")
        st.stop()

    # Show any unanswered questions
    st.subheader("🤖 Unanswered Questions")
    unanswered = output_json.get("unknown_questions", {})
    if unanswered:
        responses = {}
        for q in unanswered:
            responses[q] = st.text_input(q)
        if st.button("Submit Answers & Finalize Form"):
            st.warning("This step is not yet wired — it would reprocess the form.")
    else:
        st.success("✅ All questions filled!")

    # Download link
    st.subheader("📎 Download Partially Filled Form")
    try:
        filled_file = output_json["filled_file"].split("/")[-1]
        filled_url = f"https://api.apify.com/v2/key-value-stores/{kv_store_id}/records/{filled_file}?token={APIFY_TOKEN}"
        st.markdown(f"[📄 Download Filled Form]({filled_url})")
    except KeyError:
        st.error("❌ Filled form not found in output.json.")
