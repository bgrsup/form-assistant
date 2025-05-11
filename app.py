# app.py - Streamlit S3 handoff model (FINAL VERSION)

import streamlit as st
import boto3
import requests
import os
import time

st.set_page_config(page_title="Compliance Form Assistant")
st.title("📄 Compliance Form Assistant")

def log(msg):
    st.text(f"🪵 {msg}")

# ✅ Load secrets
try:
    AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
    AWS_REGION = os.environ["AWS_REGION"]
    S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
    APIFY_TOKEN = os.environ["APIFY_TOKEN"]
    APIFY_ACTOR_ID = os.environ["APIFY_ACTOR_ID"]
    st.success("✅ All secrets loaded")
except KeyError as e:
    st.error(f"❌ Missing env var: {e}")
    st.stop()

uploaded_file = st.file_uploader("Upload compliance file (DOCX, XLSX, PDF)", type=["docx", "xlsx", "pdf"])

if uploaded_file:
    file_name = uploaded_file.name
    local_file = f"temp_{file_name}"

    # ✅ Save file locally
    with open(local_file, "wb") as f:
        f.write(uploaded_file.getbuffer())
    log(f"✅ File saved locally as {local_file}")

    # ✅ Upload to S3
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

    s3_key = f"compliance-uploads/{file_name}"
    s3.upload_file(local_file, S3_BUCKET_NAME, s3_key)
    log(f"📤 Uploaded to S3 → {S3_BUCKET_NAME}/{s3_key}")

    # ✅ Trigger Apify actor with S3 info
    run = requests.post(
        f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/runs?token={APIFY_TOKEN}",
        json={"input": {
            "S3_BUCKET_NAME": S3_BUCKET_NAME,       # ✅ CORRECTED
            "S3_OBJECT_KEY": s3_key
        }},
        headers={"Content-Type": "application/json"}
    ).json()
    run_id = run["data"]["id"]
    log(f"🚀 Apify actor started → Run ID: {run_id}")

    # ✅ Poll actor status
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        time.sleep(3)
        status = requests.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        ).json()["data"]["status"]
        log(f"⏳ Actor status: {status}")

    st.success("✅ Actor completed!")
