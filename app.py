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

    # Upload file to INPUT_FILE slot of actor task
    with open("temp_upload.docx", "rb") as f:
        upload_res = requests.put(
            f"https://api.apify.com/v2/actor-tasks/{APIFY_TASK_ID}/input?token={APIFY_TOKEN}",
            files={"value": ("input.docx", f)}
        )
    if upload_res.status_code not in [200, 201]:
        st.error(f"❌ Upload to INPUT_FILE failed: {upload_res.text}")
        st.stop()

    # Start actor task
    run_res = requests.post(
        f"https://api.apify.com/v2/actor-tasks/{APIFY_TASK_ID}/runs?token={APIFY_TOKEN}",
        headers={"Content-Type": "application/json"}
    )
    run_id = run_res.json()["data"]["id"]

    # Poll until finished
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        status = requests.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        ).json()["data"]["status"]
        log(f"⏳ Actor status: {status}")

    st.success("✅ Actor task finished!")

    # Get default Key-Value Store ID from run
    run_info = requests.get(
        f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
    ).json()
    store_id = run_info["data"]["defaultKeyValueStoreId"]

    # Get output.json
    try:
        output = requests.get(
            f"https://api.apify.com/v2/key-value-stores/{store_id}/records/output.json?token={APIFY_TOKEN}"
        ).json()
        st.json(output)
    except Exception as e:
        st.error(f"❌ Failed to load output.json: {e}")
        st.stop()

    # Show unanswered questions
    st.subheader("🤖 Unanswered Questions")
    for q in output.get("unknown_questions", {}):
        st.text_input(q)

    # Download link
    st.subheader("📥 Download")
    try:
        file_name = output["filled_file"].split("/")[-1]
        download_url = f"https://api.apify.com/v2/key-value-stores/{store_id}/records/{file_name}?token={APIFY_TOKEN}"
        st.markdown(f"[📄 Download Filled Form]({download_url})")
    except Exception:
        st.error("❌ Could not determine filled file URL from output.")
