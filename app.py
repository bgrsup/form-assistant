# ✅ Streamlit S3 Uploader App

import streamlit as st
import boto3
import os
import uuid

st.set_page_config(page_title="Compliance File Uploader")
st.title("📄 Compliance File Uploader to S3")

def log(msg):
    st.text(f"🪵 {msg}")

# ✅ Load AWS credentials from Streamlit secrets
try:
    AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
    AWS_REGION = os.environ["AWS_REGION"]
    S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
    st.success("✅ AWS secrets loaded")
except KeyError as e:
    st.error(f"❌ Missing AWS env var: {e}")
    st.stop()

# ✅ Initialize S3 client
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

uploaded_file = st.file_uploader("Upload your form file (DOCX, PDF, XLSX etc.)", type=["docx", "pdf", "xlsx"])

if uploaded_file:
    file_id = str(uuid.uuid4())
    file_name = f"{file_id}-{uploaded_file.name}"
    
    # Save temp file
    with open(file_name, "wb") as f:
        f.write(uploaded_file.getbuffer())
    log(f"✅ File saved locally as {file_name}")

    # Upload to S3
    try:
        s3.upload_file(file_name, S3_BUCKET_NAME, file_name)
        file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_name}"
        st.success(f"✅ File uploaded to S3 bucket `{S3_BUCKET_NAME}`")
        st.markdown(f"[📥 Download your file]({file_url})")
    except Exception as e:
        st.error(f"❌ S3 upload failed: {e}")
