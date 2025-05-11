# ✅ Streamlit app.py for Option C
import streamlit as st
import requests
import os

st.set_page_config(page_title="Compliance Form Assistant")
st.title("📄 Compliance Form Assistant")

def log(msg):
    st.text(f"🪵 {msg}")

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

    # Upload file to INPUT_FILE slot
    upload_url = f"https://api.apify.com/v2/actor-tasks/{APIFY_TASK_ID}/input-file?token={APIFY_TOKEN}"
    with open("temp_upload.docx", "rb") as f:
        up = requests.put(upload_url, files={"value": f})
    if up.status_code not in [200, 201]:
        st.error(f"❌ Upload failed: {up.text}")
        st.stop()

    # Trigger actor task
    run_url = f"https://api.apify.com/v2/actor-tasks/{APIFY_TASK_ID}/runs?token={APIFY_TOKEN}"
    run = requests.post(run_url, json={"input": {"useInputFile": True}})
    run_id = run.json()["data"]["id"]

    # Poll status
    status = "RUNNING"
    while status in ["RUNNING", "READY"]:
        status = requests.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        ).json()["data"]["status"]
        log(f"⏳ Actor status: {status}")

    st.success("✅ Actor completed")

    # Get default key-value-store id
    store_id = requests.get(
        f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
    ).json()["data"]["defaultKeyValueStoreId"]

    # Load output
    output = requests.get(
        f"https://api.apify.com/v2/key-value-stores/{store_id}/records/output.json?token={APIFY_TOKEN}"
    ).json()

    st.subheader("🤖 Unanswered Questions")
    for q in output.get("unknown_questions", {}):
        st.text_input(q)

    # Download link
    st.subheader("📥 Download")
    file_name = output["filled_file"]
    url = f"https://api.apify.com/v2/key-value-stores/{store_id}/records/{file_name}?token={APIFY_TOKEN}"
    st.markdown(f"[Download Filled Form]({url})")


# ✅ Actor main.py for Option C

import os
from apify import Actor
from docx import Document
from docx.opc.exceptions import PackageNotFoundError

KNOWN_ANSWERS = {
    "Company Name": "BGR, Inc.",
    "Company Address": "6392 Gano Road, West Chester, OH 45069",
    "Company Contact": "Mike Willging",
    "Contact Email": "customerservice@packbgr.com",
    "Job Title": "Warehouse Quality Manager",
    "DUNS": "063974430",
    "Tax ID": "31-0841900"
}

def extract_questions(path):
    try:
        doc = Document(path)
    except PackageNotFoundError:
        raise ValueError(f"Not a valid DOCX: {path}")
    return [p.text.strip() for p in doc.paragraphs if p.text.strip().endswith('?')]

def fill_answers(input_path, output_path, answers):
    doc = Document(input_path)
    for para in doc.paragraphs:
        for k, v in answers.items():
            if k in para.text:
                para.text = para.text.replace(k, f"{k} {v}")
    doc.save(output_path)

async def main():
    async with Actor:
        file_path = await Actor.get_input_file()
        questions = extract_questions(file_path)
        known, unknown = {}, {}
        for q in questions:
            for k, v in KNOWN_ANSWERS.items():
                if k.lower() in q.lower():
                    known[q] = v
                    break
            else:
                unknown[q] = ""
        output_file = file_path.replace(".docx", "_filled.docx")
        fill_answers(file_path, output_file, known)

        await Actor.push_data({"filled_file": "filled.docx", "unknown_questions": unknown})
        await Actor.push_file("filled.docx", output_file)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
