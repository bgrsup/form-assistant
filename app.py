import streamlit as st
import requests
import os

st.set_page_config(page_title="Compliance Form Assistant")
st.title("📄 Compliance Form Assistant")

def log(message):
    st.text(f"🪵 {message}")

# Load secrets
try:
    APIFY_TOKEN = os.environ["APIFY_TOKEN"]
    APIFY_TASK_ID = os.environ["APIFY_TASK_ID"]
    st.success("✅ Secrets loaded")
except KeyError as e:
    st.error(f"❌ Missing secret: {e}")
    st.stop()

uploaded_file = st.file_uploader("Upload DOCX file", type=["docx"])

if uploaded_file:
    with open("temp_upload.docx", "wb") as f:
        f.write(uploaded_file.getbuffer())
    log("✅ File saved locally")

    # Create KV store
    kv_res = requests.post(
        f"https://api.apify.com/v2/key-value-stores?token={APIFY_TOKEN}",
        json={"name": "form-upload"}
    )
    kv_id = kv_res.json()["data"]["id"]
    log(f"🗂 KV store created: {kv_id}")

    # Upload file to KV store as INPUT
    with open("temp_upload.docx", "rb") as f:
        put_res = requests.put(
            f"https://api.apify.com/v2/key-value-stores/{kv_id}/records/INPUT?token={APIFY_TOKEN}",
            files={"value": ("input.docx", f)}
        )
    if put_res.status_code not in [200, 201]:
        st.error("❌ Upload failed")
        st.stop()

    # Start actor with KV store
    run_res = requests.post(
        f"https://api.apify.com/v2/actor-tasks/{APIFY_TASK_ID}/runs?token={APIFY_TOKEN}",
        json={"keyValueStoreId": kv_id},
        headers={"Content-Type": "application/json"}
    )
    run_id = run_res.json()["data"]["id"]

    # Poll for actor completion
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        status = requests.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        ).json()["data"]["status"]
        log(f"⏳ Actor status: {status}")

    # Get output
    output = requests.get(
        f"https://api.apify.com/v2/key-value-stores/{kv_id}/records/output.json?token={APIFY_TOKEN}"
    ).json()

    # Show unanswered questions
    st.subheader("🤖 Unanswered Questions")
    for q in output.get("unknown_questions", {}):
        st.text_input(q)

    # Download link
    st.subheader("📥 Download")
    file_name = output["filled_file"].split("/")[-1]
    download_url = f"https://api.apify.com/v2/key-value-stores/{kv_id}/records/{file_name}?token={APIFY_TOKEN}"
    st.markdown(f"[Download Filled Form]({download_url})")
