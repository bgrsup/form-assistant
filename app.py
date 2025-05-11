# ✅ FINAL Streamlit app.py with full debug + dataset checks

import streamlit as st
import requests
import os
import time

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
    dataset_res = requests.post(
        f"https://api.apify.com/v2/datasets?token={APIFY_TOKEN}",
        json={"name": "form-upload-dataset"}
    )
    dataset = dataset_res.json()
    dataset_id = dataset["data"]["id"]
    log(f"📦 Dataset created: {dataset_id}")

    # ✅ Upload file to dataset
    with open("temp.docx", "rb") as f:
        upload_res = requests.post(
            f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}",
            files={"value": ("input.docx", f)}
        )
    log(f"📥 File uploaded: {upload_res.status_code}")

    # ✅ Validate dataset contents
    items = requests.get(
        f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}"
    ).json()
    if not items:
        st.error("❌ Dataset is empty after upload. Aborting.")
        st.stop()
    log(f"✅ Dataset contains {len(items)} item(s)")

    # ✅ Trigger Actor with datasetId
    actor_payload = {"input": {"datasetId": dataset_id}}
    log(f"📤 Launching Actor with payload: {actor_payload}")

    run = requests.post(
        f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/runs?token={APIFY_TOKEN}",
        json=actor_payload,
        headers={"Content-Type": "application/json"}
    ).json()
    run_id = run["data"]["id"]
    log(f"🚀 Actor started: {run_id}")

    # ✅ Poll Actor
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        time.sleep(3)
        poll = requests.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        ).json()
        status = poll["data"]["status"]
        log(f"⏳ Actor status: {status}")

    st.success("✅ Actor finished!")
    st.info(f"Actor run ID: {run_id}")
    st.info(f"Dataset ID: {dataset_id}")
    st.markdown(f"View dataset in Apify Console: https://console.apify.com/datasets/{dataset_id}")
