import streamlit as st
import requests
import json
import os

st.set_page_config(page_title="Compliance Form Assistant")
st.title("📄 Compliance Form Assistant")

# Logging helper
def log(message):
    st.text(f"🪵 {message}")

# ✅ Check for secrets
try:
    APIFY_TOKEN = os.environ["APIFY_TOKEN"]
    APIFY_ACTOR_ID = os.environ["APIFY_ACTOR_ID"]
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

    st.info("Uploading to Apify key-value store...")
    store_res = requests.post(
        f"https://api.apify.com/v2/key-value-stores?token={APIFY_TOKEN}",
        json={"name": "form-upload-store"}
    )
    log(f"Store create response: {store_res.status_code}")

    try:
        res_json = store_res.json()
        st.json(res_json)  # Show full response for debug
        store_id = res_json["data"]["id"]
    except Exception as e:
        st.error(f"Failed to extract store ID: {e}")
        st.stop()

    log(f"Using store_id: {store_id}")

    try:
        requests.put(
            f"https://api.apify.com/v2/key-value-stores/{store_id}/records/INPUT_FILE?token={APIFY_TOKEN}",
            files={"value": ("form.docx", open("temp_upload.docx", "rb"))},
            headers={"Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        )
        log("File uploaded to KV store")
    except Exception as e:
        st.error(f"Failed to upload to KV store: {e}")
        st.stop()

    st.info("Running Apify actor...")
    try:
        actor_call = requests.post(
            f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/runs?token={APIFY_TOKEN}",
            json={"input": {"useInputFile": True}, "memory": 2048, "build": "latest", "keyValueStoreId": store_id}
        )
        log("Actor started")
        run_id = actor_call.json()["data"]["id"]
        log(f"Run ID: {run_id}")
    except Exception as e:
        st.error(f"Failed to start actor: {e}")
        st.stop()

    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        status_res = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}")
        status = status_res.json()["data"]["status"]
        log(f"Run status: {status}")

    log("Actor complete")

    try:
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
