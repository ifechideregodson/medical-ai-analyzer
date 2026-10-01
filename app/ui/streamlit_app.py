from __future__ import annotations

import json
from typing import Any

import requests
import streamlit as st
import pandas as pd
from time import sleep

API_BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="Medical AI Analyzer", layout="wide", initial_sidebar_state="expanded")

st.title("🏥 Medical AI Analyzer")
st.caption("Decision-support system for X-ray and skin image analysis")

# Sidebar navigation
page = st.sidebar.radio(
    "Navigate",
    ["Inference", "Training", "Jobs Status"],
    icons=["camera", "graduation-cap", "hourglass"],
)

if page == "Inference":
    st.header("🔍 Image Inference")
    st.write("Upload an image to analyze using trained models.")

    col1, col2 = st.columns(2)
    with col1:
        image_type = st.selectbox("Image type", ["xray", "skin"], key="inference_type")
    with col2:
        uploaded_file = st.file_uploader("Upload image", type=["jpg", "jpeg", "png", "webp"])

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Uploaded image", use_column_width=True)

        if st.button("Run Inference", key="inference_button"):
            with st.spinner("Analyzing image..."):
                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        uploaded_file.type or "application/octet-stream",
                    )
                }
                response = requests.post(
                    f"{API_BASE_URL}/api/v1/predict?image_type={image_type}",
                    files=files,
                    timeout=60,
                )

                if response.status_code == 200:
                    payload = response.json()
                    prediction = payload["prediction"]
                    st.success(f"✅ Prediction: **{prediction['label']}**")
                    st.metric("Confidence", f"{prediction['confidence'] * 100:.2f}%")
                    if prediction["needs_review"]:
                        st.warning("⚠️ Needs human review")
                    st.subheader("Class Scores")
                    scores_df = pd.DataFrame(
                        [
                            {"Class": label, "Score": score}
                            for label, score in prediction["all_scores"].items()
                        ]
                    )
                    st.bar_chart(scores_df.set_index("Class"))
                else:
                    st.error(f"❌ Prediction failed: {response.text}")
    else:
        st.info("📤 Upload an image to run inference.")

elif page == "Training":
    st.header("🎓 Model Training")
    st.write("Create and train new models with your own datasets.")

    with st.form("training_config"):
        st.subheader("Training Configuration")
        col1, col2 = st.columns(2)
        with col1:
            dataset_name = st.text_input("Dataset Name", value="my_dataset_v1")
            image_type = st.selectbox("Image Type", ["xray", "skin"], key="train_type")
            num_classes = st.number_input("Number of Classes", min_value=2, max_value=50, value=4)
        with col2:
            num_epochs = st.number_input("Epochs", min_value=1, max_value=100, value=10)
            batch_size = st.number_input("Batch Size", min_value=4, max_value=128, value=16)
            learning_rate = st.number_input("Learning Rate", min_value=1e-6, max_value=0.1, value=1e-4, format="%e")

        st.subheader("Class Labels")
        labels = []
        label_cols = st.columns(2)
        for i in range(num_classes):
            with label_cols[i % 2]:
                label = st.text_input(f"Class {i + 1}", value=f"Class_{i + 1}")
                labels.append(label)

        create_job = st.form_submit_button("Create Training Job", use_container_width=True)

    if create_job:
        with st.spinner("Creating training job..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/v1/training/jobs",
                    json={
                        "dataset_name": dataset_name,
                        "image_type": image_type,
                        "num_classes": num_classes,
                        "train_size": 100,
                        "val_size": 20,
                        "labels": labels,
                    },
                    timeout=10,
                )
                if response.status_code == 200:
                    job_data = response.json()
                    job_id = job_data["job_id"]
                    st.success(f"✅ Job created! ID: `{job_id}`")
                    st.session_state.current_job_id = job_id
                    st.session_state.show_upload = True
                else:
                    st.error(f"Failed to create job: {response.text}")
            except Exception as e:
                st.error(f"Error: {e}")

    # Upload training data
    if "current_job_id" in st.session_state and st.session_state.get("show_upload"):
        st.divider()
        st.subheader("Upload Training Images")
        job_id = st.session_state.current_job_id
        st.info(f"Job ID: `{job_id}`")

        uploaded_files = st.file_uploader(
            "Upload training images",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="training_files",
        )

        if uploaded_files:
            st.write(f"📊 {len(uploaded_files)} images selected")

            if st.button("Upload Images", key="upload_button"):
                with st.spinner("Uploading images..."):
                    files = [
                        ("files", (f.name, f.getvalue(), f.type))
                        for f in uploaded_files
                    ]
                    response = requests.post(
                        f"{API_BASE_URL}/api/v1/training/jobs/{job_id}/upload",
                        files=files,
                        timeout=120,
                    )
                    if response.status_code == 200:
                        st.success("✅ Images uploaded successfully!")
                        st.session_state.show_labels = True
                    else:
                        st.error(f"Upload failed: {response.text}")

            # Label assignment
            if st.session_state.get("show_labels"):
                st.divider()
                st.subheader("Assign Labels")
                st.info("Assign a class label to each uploaded image")

                assigned_labels = []
                for i in range(len(uploaded_files)):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"📷 {uploaded_files[i].name}")
                    with col2:
                        label_idx = st.selectbox(f"Label for image {i + 1}", range(len(labels)), key=f"label_{i}")
                        assigned_labels.append(label_idx)

                if st.button("Start Training", key="start_training", use_container_width=True):
                    with st.spinner("Starting training..."):
                        response = requests.post(
                            f"{API_BASE_URL}/api/v1/training/jobs/{job_id}/start",
                            json={
                                "labels": assigned_labels,
                                "num_epochs": num_epochs,
                                "batch_size": batch_size,
                                "learning_rate": learning_rate,
                            },
                            timeout=30,
                        )
                        if response.status_code == 200:
                            st.success("✅ Training started!")
                            st.session_state.training_job_id = job_id
                        else:
                            st.error(f"Failed to start training: {response.text}")

elif page == "Jobs Status":
    st.header("📋 Training Jobs Status")
    st.write("Monitor the progress of your training jobs.")

    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/training/jobs", timeout=10)
        if response.status_code == 200:
            jobs = response.json()
            if not jobs:
                st.info("No training jobs yet.")
            else:
                for job in jobs:
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            st.write(f"**{job['dataset_name']}** ({job['image_type']})")
                            st.caption(f"Job ID: `{job['job_id']}`")
                        with col2:
                            status_color = {
                                "pending": "⏳",
                                "running": "🔄",
                                "completed": "✅",
                                "failed": "❌",
                            }
                            st.write(f"{status_color.get(job['status'], '❓')} {job['status'].upper()}")
                        with col3:
                            st.metric("Progress", f"{job['progress']:.1f}%")

                        if job["status"] == "running":
                            st.progress(job["progress"] / 100)
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Epoch", f"{job['epoch']}/{job['total_epochs']}")
                            with col2:
                                st.metric("Loss", f"{job['loss']:.4f}" if job["loss"] else "N/A")
                            with col3:
                                st.metric("Accuracy", f"{job['accuracy']:.2f}%" if job["accuracy"] else "N/A")
                            with col4:
                                if st.button("Refresh", key=f"refresh_{job['job_id']}"):
                                    st.rerun()
                        elif job["status"] == "completed":
                            st.success(f"✅ Completed with {job['accuracy']:.2f}% accuracy")
                        elif job["status"] == "failed":
                            st.error(f"❌ Failed: {job['error_message']}")
        else:
            st.error(f"Failed to fetch jobs: {response.text}")
    except Exception as e:
        st.error(f"Error: {e}")
