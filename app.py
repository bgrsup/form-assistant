# ✅ Streamlit app.py for Dataset model (Option E)

import streamlit as st
import requests
import os

st.set_page_config(page_title="Compliance Form Assistant")
st.title("📄 Compliance Form Assistant")

def log(msg):
    st.text(f"🪵 {msg}")

try:
    APIFY_TOKEN = os.environ["APIFY_TOKEN"]
    APIFY_ACTOR_ID = os.environ["APIFY_ACTOR_ID"]
    st.success("✅ Secrets loaded")
except KeyError as e:
    st.error(f"❌ Missing env var: {e}")
    st.stop()

uploaded_file = st.file_uploader("Upload DOCX file", type=["docx"])

if uploaded_file:
    with open("temp.docx", "wb") as f:
        f.write(uploaded_file.getbuffer())
    log("✅ File saved locally")

    # ✅ Create dataset
    dataset = requests.post(
        f"https://api.apify.com/v2/datasets?token={APIFY_TOKEN}",
        json={"name": "form-upload-dataset"}
    ).json()
    dataset_id = dataset["data"]["id"]
    log(f"📦 Dataset created: {dataset_id}")

    # ✅ Push file URL to dataset (local path for example purposes)
    # Ideally you'd upload to S3 or external storage
    record = {"file_name": "temp.docx"}
    res = requests.post(
        f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}",
        files={"value": ("temp.docx", open("temp.docx", "rb"))}
    )
    log(f"✅ File pushed to dataset: {res.status_code}")

    # ✅ Trigger Actor with datasetId
    run = requests.post(
        f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/runs?token={APIFY_TOKEN}",
        json={"input": {"datasetId": dataset_id}},
        headers={"Content-Type": "application/json"}
    ).json()
    run_id = run["data"]["id"]
    log(f"🚀 Actor started: {run_id}")

    # ✅ Poll Actor until finished
    status = "RUNNING"
    import time
    while status in ["RUNNING", "READY"]:
        time.sleep(3)
        status = requests.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        ).json()["data"]["status"]
        log(f"⏳ Status: {status}")

    st.success("✅ Actor finished!")

    # ✅ Read output dataset from Actor (or Actor output)
    st.info("You can now query the processed dataset.")
