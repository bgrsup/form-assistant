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
    APIFY_ACTOR_ID = os.environ["APIFY_ACTOR_ID"]  # e.g. "your-username~actor-name"
    st.success("✅ Secrets loaded")
except KeyError as e:
    st.error(f"❌ Missing secret: {e}")
    st.stop()

uploaded_file = st.file_uploader("Upload DOCX file", type=["docx"])

if uploaded_file:
    with open("temp_upload.docx", "wb") as f:
        f.write(uploaded_file.getbuffer())
    log("✅ File saved locally")

    # Upload file to actor INPUT slot
    with open("temp_upload.docx", "rb") as f:
        put_res = requests.put(
            f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/input?token={APIFY_TOKEN}",
            files={"value": ("input.docx", f)}
        )
    if put_res.status_code not in [200, 201]:
        st.error(f"❌ Upload to INPUT_FILE failed: {put_res.text}")
        st.stop()

    # Start actor run
    run_res = requests.post(
        f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/runs?token={APIFY_TOKEN}",
        json={"memory": 1024},
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

    # Get default KV store
    run_data = requests.get(
        f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
    ).json()["data"]
    kv_id = run_data["defaultKeyValueStoreId"]

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
