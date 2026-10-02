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
