import streamlit as st
import requests
import os
import time

st.set_page_config(page_title="Compliance Form Assistant")
st.title("📄 Compliance Form Assistant")

def log(message):
    st.text(f"🪵 {message}")

# ✅ Load secrets
try:
    APIFY_TOKEN = os.environ["APIFY_TOKEN"]
    APIFY_ACTOR_ID = os.environ["APIFY_ACTOR_ID"]
    st.success("✅ Secrets loaded")
except KeyError as e:
    st.error(f"❌ Missing secret: {e}")
    st.stop()

# 📤 Upload DOCX file
uploaded_file = st.file_uploader("Upload DOCX file", type=["docx"])

if uploaded_file:
    with open("temp_upload.docx", "wb") as f:
        f.write(uploaded_file.getbuffer())
    log("✅ File saved locally as temp_upload.docx")

    # ✅ Step 1: Create Key-Value Store
    kv_res = requests.post(
        f"https://api.apify.com/v2/key-value-stores?token={APIFY_TOKEN}",
        json={"name": "form-upload-store"}
    )
    kv_id = kv_res.json()["data"]["id"]
    log(f"📦 Created KV store: {kv_id}")

    # ✅ Step 2: Upload file to INPUT record
    with open("temp_upload.docx", "rb") as f:
        put_res = requests.put(
            f"https://api.apify.com/v2/key-value-stores/{kv_id}/records/INPUT?token={APIFY_TOKEN}",
            files={"value": ("input.docx", f)},
        )
    if put_res.status_code not in [200, 201]:
        st.error(f"❌ Upload to INPUT failed: {put_res.text}")
        st.stop()
    log("✅ File uploaded to INPUT")

    # ✅ Step 3: Run Actor with keyValueStoreId
    run_res = requests.post(
        f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/runs?token={APIFY_TOKEN}",
        json={"keyValueStoreId": kv_id},
        headers={"Content-Type": "application/json"}
    )
    run_id = run_res.json()["data"]["id"]
    log(f"🚀 Actor started: {run_id}")

    # ✅ Step 4: Poll status
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        time.sleep(3)
        status = requests.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        ).json()["data"]["status"]
        log(f"⏳ Status: {status}")

    if status != "SUCCEEDED":
        st.error(f"❌ Actor run failed with status: {status}")
        st.stop()

    st.success("✅ Actor finished!")

    # ✅ Step 5: Read output
    try:
        output = requests.get(
            f"https://api.apify.com/v2/key-value-stores/{kv_id}/records/output.json?token={APIFY_TOKEN}"
        ).json()
        st.json(output)
    except Exception as e:
        st.error(f"❌ Failed to fetch output.json: {e}")
        st.stop()

    # ✅ Step 6: Show unanswered questions
    st.subheader("🤖 Unanswered Questions")
    unanswered = output.get("unknown_questions", {})
    if unanswered:
        responses = {}
        for q in unanswered:
            responses[q] = st.text_input(q)
        if st.button("Submit Answers & Finalize Form"):
            st.warning("This step is not yet wired — it would reprocess the form.")
    else:
        st.success("✅ All questions filled!")

    # ✅ Step 7: Download link for filled file
    st.subheader("📥 Download")
    try:
        file_name = output["filled_file"]
        download_url = f"https://api.apify.com/v2/key-value-stores/{kv_id}/records/{file_name}?token={APIFY_TOKEN}"
        st.markdown(f"[Download Filled Form]({download_url})")
    except KeyError:
        st.error("❌ Filled file not found in output.json.")
