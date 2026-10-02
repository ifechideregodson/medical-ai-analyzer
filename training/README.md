# Model training

The training pipeline expects a directory containing one folder per class:

```text
data/xray/
  normal/
    image-001.png
  pneumonia/
    image-002.png
```

Run locally with:

```bash
python training/train_classifier.py --data data/xray --output models/xray_v1 --epochs 10
```

The pipeline creates:
- `model.pt`: checkpoint containing the model state and class labels.
- `metrics.json`: validation history, held-out test metrics, confusion matrix, and per-class metrics.
- `labels.json`: class order used by the model.

Do not treat training accuracy as evidence of clinical performance. Before clinical use, the model needs appropriately separated patient/study-level data, external validation, calibration, bias/subgroup analysis, prospective evaluation, and the required clinical/privacy/regulatory review.


## Real public dataset

The repository includes `training/download_medmnist.py`, which downloads real public research data from MedMNIST and exports it into class folders.

### Chest X-ray dataset

Use PneumoniaMNIST:

```bash
python training/download_medmnist.py --dataset pneumonia --output data/pneumonia_mnist
```

This preserves the official `train`, `val`, and `test` splits and writes a `manifest.csv`.

### Skin-image dataset

Use DermaMNIST:

```bash
python training/download_medmnist.py --dataset skin --output data/dermamnist
```

DermaMNIST has a different license from most MedMNIST subsets, so check the dataset terms before redistribution or commercial use.

MedMNIST is a lightweight biomedical-image benchmark and is suitable for developing and testing the training pipeline, but it is **not sufficient by itself to establish clinical performance**. The project should later add appropriately governed, representative clinical data and external validation.

A manual GitHub Actions workflow is also provided to download and package the datasets as workflow artifacts without committing the image files to the repository.
