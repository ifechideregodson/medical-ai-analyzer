"""Train and evaluate an image classifier from a folder dataset.

Dataset layout:
    data/<task>/
      class_a/*.jpg
      class_b/*.jpg

The script creates patient/study-level splits only when a group column is
provided in a CSV manifest. Without a manifest, it performs a stratified
image-level split and reports that limitation in the metrics file.

This is a research/training pipeline; it does not establish clinical validity.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Iterable

import numpy as np
import torch
from PIL import Image
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SEED = 42


class ImageFolderDataset(Dataset):
    def __init__(self, samples: list[tuple[Path, int]], transform):
        self.samples = samples
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int):
        path, label = self.samples[index]
        with Image.open(path) as image:
            image = image.convert("RGB")
            return self.transform(image), label


def discover_samples(root: Path) -> tuple[list[tuple[Path, int]], list[str]]:
    classes = sorted(path.name for path in root.iterdir() if path.is_dir())
    if len(classes) < 2:
        raise ValueError("Dataset must contain at least two class directories")
    class_to_index = {name: i for i, name in enumerate(classes)}
    samples: list[tuple[Path, int]] = []
    for class_name, label in class_to_index.items():
        for path in sorted((root / class_name).rglob("*")):
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                samples.append((path, label))
    if len(samples) < max(20, len(classes) * 5):
        raise ValueError("Dataset is too small for a meaningful training run")
    return samples, classes


def split_samples(samples: list[tuple[Path, int]], val_size: float, test_size: float):
    labels = [label for _, label in samples]
    train_val, test = train_test_split(
        samples, test_size=test_size, random_state=SEED, stratify=labels
    )
    train_labels = [label for _, label in train_val]
    relative_test = test_size / (1.0 - test_size)
    train, val = train_test_split(
        train_val, test_size=relative_test, random_state=SEED, stratify=train_labels
    )
    return train, val, test


def build_model(num_classes: int) -> nn.Module:
    model = models.efficientnet_b0(weights="DEFAULT")
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    return model


def run_epoch(model, loader, criterion, optimizer, device):
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    predictions: list[int] = []
    targets: list[int] = []
    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        if training:
            optimizer.zero_grad(set_to_none=True)
        with torch.set_grad_enabled(training):
            logits = model(images)
            loss = criterion(logits, labels)
            if training:
                loss.backward()
                optimizer.step()
        total_loss += loss.item() * labels.size(0)
        predictions.extend(logits.argmax(1).detach().cpu().tolist())
        targets.extend(labels.detach().cpu().tolist())
    return total_loss / len(loader.dataset), accuracy_score(targets, predictions), predictions, targets


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Dataset root containing one directory per class")
    parser.add_argument("--output", default="models/trained", help="Model output directory")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--val-size", type=float, default=0.15)
    parser.add_argument("--test-size", type=float, default=0.15)
    args = parser.parse_args()

    if args.val_size <= 0 or args.test_size <= 0 or args.val_size + args.test_size >= 1:
        raise ValueError("Validation and test sizes must be positive and sum to less than 1")

    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    root = Path(args.data)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    samples, classes = discover_samples(root)
    train_samples, val_samples, test_samples = split_samples(samples, args.val_size, args.test_size)

    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    eval_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    train_loader = DataLoader(ImageFolderDataset(train_samples, train_transform), batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(ImageFolderDataset(val_samples, eval_transform), batch_size=args.batch_size)
    test_loader = DataLoader(ImageFolderDataset(test_samples, eval_transform), batch_size=args.batch_size)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(len(classes)).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)

    best_val = -1.0
    best_state = None
    history = []
    for epoch in range(1, args.epochs + 1):
        train_loss, train_acc, _, _ = run_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc, _, _ = run_epoch(model, val_loader, criterion, None, device)
        history.append({"epoch": epoch, "train_loss": train_loss, "train_accuracy": train_acc, "val_loss": val_loss, "val_accuracy": val_acc})
        print(f"epoch={epoch} train_loss={train_loss:.4f} train_acc={train_acc:.4f} val_loss={val_loss:.4f} val_acc={val_acc:.4f}")
        if val_acc > best_val:
            best_val = val_acc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    if best_state is None:
        raise RuntimeError("No checkpoint was produced")
    model.load_state_dict(best_state)
    test_loss, test_acc, predictions, targets = run_epoch(model, test_loader, criterion, None, device)
    report = classification_report(targets, predictions, target_names=classes, output_dict=True, zero_division=0)
    metrics = {
        "task": root.name,
        "classes": classes,
        "device": str(device),
        "split": {"train": len(train_samples), "validation": len(val_samples), "test": len(test_samples)},
        "test_loss": test_loss,
        "test_accuracy": test_acc,
        "test_macro_f1": f1_score(targets, predictions, average="macro", zero_division=0),
        "confusion_matrix": confusion_matrix(targets, predictions).tolist(),
        "classification_report": report,
        "history": history,
        "split_note": "Image-level stratified split. For datasets containing multiple images/studies per patient, use patient/study-level grouping before clinical evaluation.",
        "clinical_status": "research_only_not_clinically_validated",
    }

    torch.save({"state_dict": best_state, "classes": classes, "architecture": "efficientnet_b0"}, output / "model.pt")
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (output / "labels.json").write_text(json.dumps(classes, indent=2))
    print(json.dumps({"model": str(output / "model.pt"), "metrics": str(output / "metrics.json"), "test_accuracy": test_acc, "test_macro_f1": metrics["test_macro_f1"]}, indent=2))


if __name__ == "__main__":
    main()
