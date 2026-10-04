# Model training

The training pipeline is for research/model development and does not establish clinical validity.

## Official MedMNIST splits

The recommended workflow is to use the dataset exported by `download_medmnist.py`:

```bash
python training/download_medmnist.py --dataset pneumonia --output data/pneumonia_mnist
python training/train_classifier.py --data data/pneumonia_mnist --output models/pneumonia_v1 --epochs 10
```

The exporter creates:

```text
data/pneumonia_mnist/
  train/<class>/*.png
  val/<class>/*.png
  test/<class>/*.png
  manifest.csv
```

When these three directories exist, the trainer **uses them directly**. It does not reshuffle official MedMNIST examples between train, validation, and test.

For DermaMNIST:

```bash
python training/download_medmnist.py --dataset skin --output data/dermamnist
python training/train_classifier.py --data data/dermamnist --output models/derma_v1 --epochs 10
```

The trainer also supports the older single-root layout:

```text
data/xray/
  normal/*.png
  pneumonia/*.png
```

In that case it creates a stratified image-level split. Use `--split-mode official` to require official split directories or `--split-mode stratified` to force a new split.

## Outputs

Each training run writes:

- `model.pth` — full PyTorch model artifact compatible with the current model registry loader.
- `model.pt` — portable state-dict checkpoint with architecture and class metadata.
- `metrics.json` — held-out test metrics, confusion matrix, per-class metrics and training history.
- `labels.json` — exact class order used by the model.

Before clinical use, the model needs appropriately separated patient/study-level data, external validation, calibration, bias/subgroup analysis, prospective evaluation, and required clinical/privacy/regulatory review.
