import streamlit as st
import requests
import json
import pandas as pd
from pathlib import Path

API_BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="Medical AI Model Manager", layout="wide")

st.title("📦 Model Management")
st.caption("Upload, manage, and activate trained models")

tab1, tab2, tab3 = st.tabs(["Upload Model", "Model Registry", "Active Models"])

with tab1:
    st.header("Upload Trained Model")
    st.write("Upload a .pth file from your training process to the model registry.")

    with st.form("model_upload"):
        col1, col2 = st.columns(2)
        with col1:
            model_name = st.text_input("Model Name", value="my_model_v1", help="Unique identifier for this model")
            image_type = st.selectbox("Image Type", ["xray", "skin"])
        with col2:
            accuracy = st.number_input(
                "Model Accuracy (%)",
                min_value=0.0,
                max_value=100.0,
                value=85.0,
                step=0.1,
                help="Validation accuracy of the model"
            )

        description = st.text_area("Model Description", help="Notes about this model version")

        st.subheader("Class Labels")
        st.info("Enter the class labels that this model can predict")
        labels_input = st.text_area(
            "Labels (one per line or comma-separated)",
            value="Class_1\nClass_2\nClass_3\nClass_4",
            height=100
        )

        model_file = st.file_uploader("Select .pth model file", type=["pth"])

        submitted = st.form_submit_button("Upload Model", use_container_width=True)

    if submitted:
        if not model_file:
            st.error("❌ Please select a model file")
        elif not model_name:
            st.error("❌ Please enter a model name")
        elif not labels_input.strip():
            st.error("❌ Please enter at least one label")
        else:
            # Parse labels
            labels_text = labels_input.strip()
            if "," in labels_text:
                labels = [l.strip() for l in labels_text.split(",")]
            else:
                labels = [l.strip() for l in labels_text.split("\n")]
            labels = [l for l in labels if l]  # Remove empty strings

            if len(labels) < 2:
                st.error("❌ At least 2 labels are required")
            else:
                with st.spinner("Uploading model..."):
                    try:
                        files = {
                            "file": (model_file.name, model_file.getvalue(), "application/octet-stream")
                        }
                        data = {
                            "model_name": model_name,
                            "image_type": image_type,
                            "labels": json.dumps(labels),
                            "description": description,
                            "accuracy": accuracy if accuracy > 0 else None,
                        }
                        response = requests.post(
                            f"{API_BASE_URL}/api/v1/models/upload",
                            files=files,
                            data=data,
                            timeout=120,
                        )
                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"✅ Model uploaded successfully!")
                            st.json(result)
                            st.info(f"📁 Saved to: `models/{model_name}/model.pth`")
                        else:
                            st.error(f"❌ Upload failed: {response.text}")
                    except Exception as e:
                        st.error(f"Error: {e}")

with tab2:
    st.header("Model Registry")
    st.write("All registered models in the system.")

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
                st.info("No models in registry yet. Upload one to get started!")
            else:
                for model in models:
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            st.write(f"**{model['model_name']}**")
                            st.caption(f"Type: `{model['image_type']}` | Created: {model['created_at'][:10]}")
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
                        with st.expander("View labels"):
                            st.write(model["labels"])
        else:
            st.error(f"Failed to fetch models: {response.text}")
    except Exception as e:
        st.error(f"Error: {e}")

with tab3:
    st.header("Active Models")
    st.write("Currently active models used for inference.")

    col1, col2 = st.columns(2)
    for i, image_type in enumerate(["xray", "skin"]):
        with [col1, col2][i]:
            try:
                response = requests.get(f"{API_BASE_URL}/api/v1/models/active/{image_type}", timeout=10)
                if response.status_code == 200:
                    model = response.json()
                    with st.container(border=True):
                        st.write(f"**{image_type.upper()} Model**")
                        st.write(f"Name: `{model['model_name']}`")
                        st.write(f"Accuracy: {model['accuracy']:.2f}%" if model.get("accuracy") else "Accuracy: N/A")
                        st.write(f"Classes: {len(model['labels'])}")
                        st.write("Labels:")
                        st.write(model["labels"])
                else:
                    st.warning(f"No active model for {image_type}")
            except Exception as e:
                st.error(f"Error fetching {image_type} model: {e}")
