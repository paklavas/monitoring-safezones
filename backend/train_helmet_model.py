"""
Training Script for Helmet Detection Model using YOLOv11

DUAL-MODEL APPROACH:
  This script trains a model to detect 'safetyhelmet' ONLY.
  Person detection is handled separately by a COCO model at runtime.
  See app/helmet_detector.py for how both models are combined.
"""

from ultralytics import YOLO
import os

# Configuration – paths relative to project root so it works from any working directory
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
DATASET_PATH = os.path.join(_PROJECT_ROOT, "Safetyhelmet-detection.v3-bounding-box-noise.yolov11", "data.yaml")

# ---------------------------------------------------------------------------
# CPU-OPTIMIZED SETTINGS (Intel i7-1355U)
# ---------------------------------------------------------------------------
MODEL_SIZE = "n"        # "n" (nano) is fastest; don't use larger for CPU training
EPOCHS = 50             # 50 is enough with early stopping
BATCH_SIZE = 32         # Higher batch = faster training; 32 works for 16GB+ RAM
IMAGE_SIZE = 416        # 416 instead of 640 (35% faster per epoch, still accurate)
PATIENCE = 15           # Early stopping after 15 epochs without improvement
WORKERS = 8             # CPU data loading threads (i7-1355U has 12 threads, use 8)
CACHE = "ram"           # Cache images in RAM for faster loading (needs ~2-3 GB)

OUTPUT_MODEL_NAME = os.path.join(_PROJECT_ROOT, "helmet_detection_yolov11.pt")

# Even faster preset (uncomment to reduce to 3-6h):
# EPOCHS = 30
# IMAGE_SIZE = 384
# PATIENCE = 10


def train_model():
    """Train YOLOv11 model on helmet detection dataset"""

    # Run from project root so dataset and runs/ are in the project folder
    os.chdir(_PROJECT_ROOT)

    # Check if dataset exists
    if not os.path.exists(DATASET_PATH):
        print(f"❌ Error: Dataset file not found at {DATASET_PATH}")
        print("Please make sure your Roboflow dataset is extracted in the project directory.")
        return

    print("=" * 60)
    print("🚀 Starting YOLOv11 Helmet Detection Training")
    print("=" * 60)
    print(f"📁 Dataset: {DATASET_PATH}")
    print(f"🤖 Model: YOLOv11{MODEL_SIZE}")
    print(f"📊 Epochs: {EPOCHS}")
    print(f"📦 Batch Size: {BATCH_SIZE}")
    print(f"🖼️  Image Size: {IMAGE_SIZE}")
    print()
    print("ℹ️  This model trains HELMET detection only (1 class: safetyhelmet).")
    print("   Person detection uses a separate COCO model at runtime.")
    print("=" * 60)

    try:
        model_name = f"yolo11{MODEL_SIZE}.pt"
        print(f"\n📥 Loading COCO pre-trained base: {model_name} (warm start)")
        model = YOLO(model_name)  # Downloads automatically if not present

        print(f"\n🎯 Starting training...")
        print("⏳ This may take 6-12 hours on CPU...")
        print("💡 Progress saved in runs/detect/helmet_detection/\n")

        results = model.train(
            data=DATASET_PATH,
            epochs=EPOCHS,
            imgsz=IMAGE_SIZE,
            batch=BATCH_SIZE,
            name="helmet_detection",
            patience=PATIENCE,
            save=True,
            plots=True,
            val=True,
            workers=WORKERS,
            cache=CACHE,
            amp=False,
            device="cpu",
            close_mosaic=10,
        )

        # Save the best model with a friendly name
        best_model_path = results.save_dir / "weights" / "best.pt"
        if os.path.exists(best_model_path):
            import shutil
            shutil.copy(best_model_path, OUTPUT_MODEL_NAME)
            print(f"\n✅ Training completed!")
            print(f"📦 Best helmet model saved as: {OUTPUT_MODEL_NAME}")
            print(f"📊 Training results saved in: {results.save_dir}")
            print(f"\n🎉 Ready to use! The backend combines this with COCO for person+helmet detection.")
        else:
            print(f"\n⚠️  Training completed, but best model not found at expected location.")
            print(f"📊 Check training results in: {results.save_dir}")

    except Exception as e:
        print(f"\n❌ Error during training: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Make sure ultralytics is installed: pip install ultralytics")
        print("   2. Check that data.yaml path is correct")
        print("   3. Verify dataset structure (train/images, train/labels)")
        print("   4. Reduce BATCH_SIZE if you get memory errors")
        return


if __name__ == "__main__":
    try:
        import ultralytics
        print(f"✅ Ultralytics version: {ultralytics.__version__}")
    except ImportError:
        print("❌ Error: ultralytics not installed!")
        print("📦 Install it with: pip install ultralytics")
        exit(1)

    train_model()
