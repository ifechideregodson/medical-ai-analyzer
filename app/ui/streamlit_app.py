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
st.caption("Complete workflow: Train → Upload → Activate → Predict")

# Sidebar navigation
page = st.sidebar.radio(
    "Navigate",
    ["Inference", "Full Training Pipeline", "Jobs Status", "Model Registry"],
    icons=["camera", "graduation-cap", "hourglass", "box"],
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

elif page == "Full Training Pipeline":
    st.header("🎓 Complete Training Pipeline")
    st.write("Step 1️⃣ → Create Job | Step 2️⃣ → Upload Images | Step 3️⃣ → Assign Labels | Step 4️⃣ → Train | Step 5️⃣ → Auto-Activate")
    st.divider()

    # Step 1: Create Training Job
    st.subheader("Step 1️⃣: Create Training Job")
    with st.form("training_config"):
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
                label = st.text_input(f"Class {i + 1}", value=f"Class_{i + 1}", key=f"label_input_{i}")
                labels.append(label)

        col1, col2 = st.columns(2)
        with col1:
            auto_register = st.checkbox("Auto-register model after training", value=True)
        with col2:
            activate_after = st.checkbox("Auto-activate model for inference", value=True)

        create_job = st.form_submit_button("✅ Create Training Job", use_container_width=True)

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
                        "auto_register": auto_register,
                        "activate_after_training": activate_after,
                    },
                    timeout=10,
                )
                if response.status_code == 200:
                    job_data = response.json()
                    job_id = job_data["job_id"]
                    st.success(f"✅ Job created!")
                    st.session_state.current_job_id = job_id
                    st.session_state.current_labels = labels
                    st.session_state.current_num_classes = num_classes
                    st.session_state.show_upload = True
                    st.info(f"📋 Job ID: `{job_id}`")
                else:
                    st.error(f"Failed to create job: {response.text}")
            except Exception as e:
                st.error(f"Error: {e}")

    # Step 2 & 3: Upload and Label
    if "current_job_id" in st.session_state and st.session_state.get("show_upload"):
        st.divider()
        st.subheader("Step 2️⃣ & 3️⃣: Upload Images & Assign Labels")
        job_id = st.session_state.current_job_id
        labels = st.session_state.current_labels
        num_classes = st.session_state.current_num_classes

        st.info(f"Job ID: `{job_id}`")

        uploaded_files = st.file_uploader(
            "Upload training images",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="training_files",
        )

        if uploaded_files:
            st.write(f"📊 {len(uploaded_files)} images selected")

            if st.button("📤 Upload Images", key="upload_button", use_container_width=True):
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
                        st.session_state.uploaded_file_count = len(uploaded_files)
                    else:
                        st.error(f"Upload failed: {response.text}")

            # Label assignment
            if st.session_state.get("show_labels"):
                st.divider()
                st.subheader("Assign Labels to Images")
                st.write(f"You have {st.session_state.uploaded_file_count} images to label.")

                assigned_labels = []
                for i in range(len(uploaded_files)):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"{i+1}. 📷 `{uploaded_files[i].name}`")
                    with col2:
                        label_idx = st.selectbox(f"Class", labels, key=f"label_{i}")
                        assigned_labels.append(labels.index(label_idx))

                st.divider()

                # Step 4: Start Training
                st.subheader("Step 4️⃣: Start Training")
                if st.button("🚀 Start Training", key="start_training", use_container_width=True):
                    with st.spinner("Starting training... This may take a few minutes."):
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
                            st.balloons()
                        else:
                            st.error(f"Failed to start training: {response.text}")

elif page == "Jobs Status":
    st.header("📋 Training Jobs Status")
    st.write("Monitor training progress and model registration.")

    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/training/jobs", timeout=10)
        if response.status_code == 200:
            jobs = response.json()
            if not jobs:
                st.info("No training jobs yet.")
            else:
                for job in sorted(jobs, key=lambda x: x['created_at'], reverse=True):
                    with st.container(border=True):
                        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                        with col1:
                            st.write(f"**{job['dataset_name']}** ({job['image_type'].upper()})")
                            st.caption(f"Job: `{job['job_id'][:8]}...`")
                        with col2:
                            status_color = {
                                "pending": "⏳",
                                "running": "🔄",
                                "completed": "✅",
                                "failed": "❌",
                            }
                            st.write(f"{status_color.get(job['status'], '❓')} {job['status'].upper()}")
                        with col3:
                            if job['model_registered']:
                                st.success("✅ Registered")
                            else:
                                st.write("-")
                        with col4:
                            if job['model_activated']:
                                st.success("✅ Active")
                            else:
                                st.write("-")

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
                            col1, col2 = st.columns(2)
                            with col1:
                                st.success(f"✅ Completed")
                                if job["accuracy"]:
                                    st.metric("Final Accuracy", f"{job['accuracy']:.2f}%")
                            with col2:
                                if job['model_registered']:
                                    st.info(f"📦 Model: `{job['model_name']}`")
                                    if job['model_activated']:
                                        st.success("✅ Activated for inference")
                        elif job["status"] == "failed":
                            st.error(f"❌ Failed: {job['error_message']}")
        else:
            st.error(f"Failed to fetch jobs: {response.text}")
    except Exception as e:
        st.error(f"Error: {e}")

elif page == "Model Registry":
    st.header("📦 Registered Models")
    st.write("View all trained and registered models in your system.")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.write("")
    with col2:
        filter_type = st.selectbox("Filter by type", ["All", "xray", "skin"])
    with col3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/models/list", timeout=10)
        if response.status_code == 200:
            result = response.json()
            models = result["models"]

            # Filter
            if filter_type != "All":
                models = [m for m in models if m["image_type"] == filter_type]

            if not models:
                st.info("No models registered yet. Complete a training job to register a model.")
            else:
                for model in models:
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            st.write(f"**{model['model_name']}**")
                            st.caption(f"Type: `{model['image_type']}` | {model['created_at'][:10]}")
                            if model["description"]:
                                st.write(f"📝 {model['description']}")
                        with col2:
                            if model["is_active"]:
                                st.success("✅ ACTIVE")
                            else:
                                st.write("⭕ Inactive")
                            if model["accuracy"] is not None:
                                st.metric("Accuracy", f"{model['accuracy']:.2f}%")
                        with col3:
                            btn_col1, btn_col2 = st.columns(2)
                            with btn_col1:
                                if not model["is_active"]:
                                    if st.button("Activate", key=f"activate_{model['model_name']}"):
                                        resp = requests.post(
                                            f"{API_BASE_URL}/api/v1/models/activate",
                                            json={"model_name": model["model_name"]},
                                            timeout=10,
                                        )
                                        if resp.status_code == 200:
                                            st.success("✅ Activated")
                                            st.rerun()
                                        else:
                                            st.error("Failed")
                            with btn_col2:
                                if st.button("Delete", key=f"delete_{model['model_name']}"):
                                    resp = requests.delete(
                                        f"{API_BASE_URL}/api/v1/models/{model['model_name']}",
                                        timeout=10,
                                    )
                                    if resp.status_code == 200:
                                        st.success("✅ Deleted")
                                        st.rerun()
                                    else:
                                        st.error("Failed")

                        # Show labels
                        with st.expander("🌠 View labels"):
                            st.write(model["labels"])
        else:
            st.error(f"Failed to fetch models: {response.text}")
    except Exception as e:
        st.error(f"Error: {e}")
