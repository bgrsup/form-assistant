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
    APIFY_ACTOR_ID = os.environ["APIFY_ACTOR_ID"]  # format: username~actor-name
    st.success("✅ Secrets loaded")
except KeyError as e:
    st.error(f"❌ Missing secret: {e}")
    st.stop()

uploaded_file = st.file_uploader("Upload DOCX file", type=["docx"])

if uploaded_file:
    with open("temp_upload.docx", "wb") as f:
        f.write(uploaded_file.getbuffer())
    log("✅ File saved locally as temp_upload.docx")

    # Start Actor with INPUT file
    st.info("🚀 Starting Actor on Apify...")

    # Upload file to INPUT file
    with open("temp_upload.docx", "rb") as f:
        files = {'value': f}
        input_file_res = requests.put(
            f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/input?token={APIFY_TOKEN}",
            files=files
        )

    if input_file_res.status_code not in [200, 201]:
        st.error(f"❌ Upload to INPUT_FILE failed: {input_file_res.text}")
        st.stop()

    log("📤 INPUT file uploaded successfully")

    # Run the Actor
    run_res = requests.post(
        f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/runs?token={APIFY_TOKEN}",
        headers={"Content-Type": "application/json"}
    )
    run_id = run_res.json()["data"]["id"]
    log(f"🎬 Actor run started: {run_id}")

    # Poll status
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        run_status = requests.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        ).json()["data"]
        status = run_status["status"]
        log(f"⏳ Status: {status}")
        time.sleep(2)

    st.success("✅ Actor run finished!")

    # Get default key-value store ID
    store_id = run_status["defaultKeyValueStoreId"]

    # Get output
    output = requests.get(
        f"https://api.apify.com/v2/key-value-stores/{store_id}/records/output.json?token={APIFY_TOKEN}"
    )
    if output.status_code != 200:
        st.error("❌ Could not fetch output.json")
        st.stop()

    output_json = output.json()
    st.json(output_json)

    # Unanswered Questions
    st.subheader("🤖 Unanswered Questions")
    unanswered = output_json.get("unknown_questions", {})
    if unanswered:
        for q in unanswered:
            st.text_input(q)
    else:
        st.success("✅ No unanswered questions!")

    # Download link
    st.subheader("📥 Download Filled Form")
    try:
        file_name = output_json["filled_file"].split("/")[-1]
        download_url = f"https://api.apify.com/v2/key-value-stores/{store_id}/records/{file_name}?token={APIFY_TOKEN}"
        st.markdown(f"[📄 Download Filled Form]({download_url})")
    except KeyError:
        st.error("❌ Filled file not found in output.json")
