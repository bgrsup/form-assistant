import streamlit as st
import requests
import json
import os

st.set_page_config(page_title="Compliance Form Assistant")
st.title("📄 Compliance Form Assistant")

# ✅ DEBUG: Check for missing secrets or token issues
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

    st.info("Uploading to Apify key-value store...")
store_res = requests.post(
    f"https://api.apify.com/v2/key-value-stores?token={APIFY_TOKEN}",
    json={"name": "form-upload-store"}
)

res_json = store_res.json()

try:
    store_id = res_json["data"]["id"]
except KeyError:
    st.error("Apify response missing expected 'data._id'. Full response:")
    st.json(res_json)
    st.stop()

    requests.put(
        f"https://api.apify.com/v2/key-value-stores/{store_id}/records/INPUT_FILE?token={APIFY_TOKEN}",
        files={"value": ("form.docx", open("temp_upload.docx", "rb"))},
        headers={"Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    )

    st.info("Running Apify actor...")
    actor_call = requests.post(
        f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/runs?token={APIFY_TOKEN}",
        json={"input": {"useInputFile": True}, "memory": 2048, "build": "latest", "keyValueStoreId": store_id}
    )

    run_id = actor_call.json()["data"]["id"]
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        status_res = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}")
        status = status_res.json()["data"]["status"]

    output = requests.get(
        f"https://api.apify.com/v2/key-value-stores/{store_id}/records/output.json?token={APIFY_TOKEN}"
    )
    output_json = output.json()

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
