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
    log("✅ Saved uploaded file")

    # Create new KV store for this run
    log("📦 Creating temp Apify KV store...")
    kv_store_res = requests.post(
        f"https://api.apify.com/v2/key-value-stores?token={APIFY_TOKEN}",
        json={"name": "form-upload-store"}
    )
    kv_store_id = kv_store_res.json()["data"]["id"]
    log(f"📁 Created store ID: {kv_store_id}")

    # Upload DOCX file to INPUT slot
    log("📤 Uploading file to INPUT...")
    put_res = requests.put(
        f"https://api.apify.com/v2/key-value-stores/{kv_store_id}/records/INPUT?token={APIFY_TOKEN}",
        files={"value": ("input.docx", open("temp_upload.docx", "rb"))},
        headers={"Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    )
    log(f"📥 Upload status: {put_res.status_code}")
    if put_res.status_code not in [200, 201]:
        st.error(f"Upload failed: {put_res.text}")
        st.stop()

    # Start Apify Task with this KV store
    st.info("🚀 Running Apify Task...")
    task_run = requests.post(
        f"https://api.apify.com/v2/actor-tasks/{APIFY_TASK_ID}/runs?token={APIFY_TOKEN}",
        json={
            "keyValueStoreId": kv_store_id,
            "memory": 1024
        },
        headers={"Content-Type": "application/json"}
    )
    run_id = task_run.json()["data"]["id"]
    log(f"🔁 Task Run ID: {run_id}")

    # Poll until finished
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        status_res = requests.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        )
        status = status_res.json()["data"]["status"]
        log(f"⏳ Status: {status}")

    st.success("✅ Task complete!")

    # Fetch output
    try:
        output = requests.get(
            f"https://api.apify.com/v2/key-value-stores/{kv_store_id}/records/output.json?token={APIFY_TOKEN}"
        )
        output_json = output.json()
        st.json(output_json)
    except Exception as e:
        st.error(f"❌ Failed to load output.json: {e}")
        st.stop()

    # Show unanswered questions
    st.subheader("🤖 Unanswered Questions")
    unanswered = output_json.get("unknown_questions", {})
    if unanswered:
        responses = {}
        for q in unanswered:
            responses[q] = st.text_input(q)
        if st.button("Submit Answers & Finalize Form"):
            st.warning("In a real app, this would update the form with final answers and return the final file.")
    else:
        st.success("✅ No unanswered questions! Your form is ready.")

    # Provide download link
    st.subheader("📎 Download Partially Filled Form")
    try:
        filled_file = output_json["filled_file"].split("/")[-1]
        filled_url = f"https://api.apify.com/v2/key-value-stores/{kv_store_id}/records/{filled_file}?token={APIFY_TOKEN}"
        st.markdown(f"[Download Filled Form]({filled_url})")
    except KeyError:
        st.error("❌ Could not determine filled file URL.")
