# ✅ FULL FINAL OPTION A — streamlit + apify-client 2.5 compatible

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

    # ✅ Create KV Store
    kv = requests.post(
        f"https://api.apify.com/v2/key-value-stores?token={APIFY_TOKEN}",
        json={"name": "form-upload-store"}
    ).json()
    kv_id = kv["data"]["id"]
    log(f"📦 KV store created: {kv_id}")

    # ✅ Upload file to INPUT slot
    with open("temp.docx", "rb") as f:
        put = requests.put(
            f"https://api.apify.com/v2/key-value-stores/{kv_id}/records/INPUT?token={APIFY_TOKEN}",
            files={"value": ("input.docx", f)}
        )
    log(f"📥 File uploaded: {put.status_code}")

    if put.status_code not in [200, 201]:
        st.error("❌ Upload to INPUT failed")
        st.stop()

    # ✅ Trigger Actor
    run = requests.post(
        f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/runs?token={APIFY_TOKEN}",
        json={"input": {"keyValueStoreId": kv_id}},
        headers={"Content-Type": "application/json"}
    ).json()
    run_id = run["data"]["id"]
    log(f"🚀 Actor started: {run_id}")

    # ✅ Poll Actor
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        time.sleep(3)
        status = requests.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        ).json()["data"]["status"]
        log(f"⏳ Status: {status}")

    st.success("✅ Actor finished!")

    # ✅ Get results
    out = requests.get(
        f"https://api.apify.com/v2/key-value-stores/{kv_id}/records/output.json?token={APIFY_TOKEN}"
    ).json()

    st.subheader("🤖 Unanswered Questions")
    unanswered = out.get("unknown_questions", {})
    for q in unanswered:
        st.text_input(q)

    st.subheader("📥 Download")
    try:
        file_name = out["filled_file"]
        file_url = f"https://api.apify.com/v2/key-value-stores/{kv_id}/records/{file_name}?token={APIFY_TOKEN}"
        st.markdown(f"[Download Filled Form]({file_url})")
    except KeyError:
        st.error("❌ No filled_file in output.")
