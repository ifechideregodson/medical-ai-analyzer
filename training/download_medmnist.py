"""Download and export a real public medical research dataset from MedMNIST.

This script downloads PneumoniaMNIST (chest X-ray) or DermaMNIST (dermatoscopy)
and exports the official train/validation/test splits into class folders.

The resulting data is for research/model-development use. It is not a
clinically validated dataset and should not be used for patient diagnosis.

Usage:
    python training/download_medmnist.py --dataset pneumonia --output data/pneumonia_mnist
    python training/download_medmnist.py --dataset skin --output data/dermamnist
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image

DATASETS = {"pneumonia": "PneumoniaMNIST", "skin": "DermaMNIST"}


def load_dataset(name: str, split: str):
    from medmnist import INFO
    from medmnist import DermaMNIST, PneumoniaMNIST

    dataset_cls = {"pneumonia": PneumoniaMNIST, "skin": DermaMNIST}[name]
    info = INFO[dataset_cls.__name__.lower()]
    dataset = dataset_cls(split=split, download=True)
    labels = {int(key): str(value) for key, value in info["label"].items()}
    return dataset, labels


def export_dataset(name: str, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    manifest = output / "manifest.csv"

    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["split", "path", "label_id", "label"])

        for split in ("train", "val", "test"):
            dataset, labels = load_dataset(name, split)
            split_dir = output / split
            split_dir.mkdir(parents=True, exist_ok=True)

            for index in range(len(dataset)):
                image, target = dataset[index]
                label_id = int(np.asarray(target).reshape(-1)[0])
                label = labels[label_id]
                class_dir = split_dir / label
                class_dir.mkdir(parents=True, exist_ok=True)

                image_path = class_dir / f"{name}-{split}-{index:06d}.png"
                if isinstance(image, Image.Image):
                    image.save(image_path)
                else:
                    array = np.asarray(image).astype(np.uint8)
                    if array.ndim == 2:
                        Image.fromarray(array, mode="L").save(image_path)
                    else:
                        Image.fromarray(array).save(image_path)

                writer.writerow([split, str(image_path.relative_to(output)), label_id, label])

    print(f"Exported {name} dataset to {output}")
    print(f"Manifest: {manifest}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=sorted(DATASETS), default="pneumonia")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    export_dataset(args.dataset, Path(args.output))


if __name__ == "__main__":
    main()
