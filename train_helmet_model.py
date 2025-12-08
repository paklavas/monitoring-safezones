"""
Training Script for Helmet Detection Model using YOLOv11
This script trains a YOLOv11 model on your Roboflow dataset.
"""

from ultralytics import YOLO
import os

# Configuration
DATASET_PATH = "Safetyhelmet-detection.v3-bounding-box-noise.yolov11/data.yaml"
MODEL_SIZE = "n"  # Options: n (nano), s (small), m (medium), l (large), x (xlarge)
EPOCHS = 100  # Number of training epochs (increase for better accuracy, but takes longer)
BATCH_SIZE = 16  # Adjust based on your GPU memory (8, 16, 32, 64)
IMAGE_SIZE = 640  # Input image size (640 is standard, can use 1280 for better accuracy)
OUTPUT_MODEL_NAME = "helmet_detection_yolov11.pt"

# Note: YOLO will automatically split train/val if validation folder doesn't exist

def train_model():
    """Train YOLOv11 model on helmet detection dataset"""
    
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
    print("=" * 60)
    
    try:
        # Load YOLOv11 model (nano version for faster training)
        # For YOLOv11, use 'yolo11n.pt', 'yolo11s.pt', etc.
        model_name = f"yolo11{MODEL_SIZE}.pt"
        print(f"\n📥 Loading base model: {model_name}")
        model = YOLO(model_name)  # This will download automatically if not present
        
        print(f"\n🎯 Starting training...")
        print("⏳ This may take a while depending on your hardware...")
        print("💡 Training progress will be saved in 'runs/detect/train/' folder\n")
        
        # Train the model
        results = model.train(
            data=DATASET_PATH,           # Path to dataset.yaml
            epochs=EPOCHS,              # Number of training epochs
            imgsz=IMAGE_SIZE,            # Input image size
            batch=BATCH_SIZE,            # Batch size
            name="helmet_detection",    # Project name
            patience=50,                 # Early stopping patience
            save=True,                   # Save checkpoints
            plots=True,                  # Generate training plots
            val=True,                    # Validate during training
        )
        
        # Save the best model
        best_model_path = results.save_dir / "weights" / "best.pt"
        if os.path.exists(best_model_path):
            # Copy to project root with a friendly name
            import shutil
            shutil.copy(best_model_path, OUTPUT_MODEL_NAME)
            print(f"\n✅ Training completed!")
            print(f"📦 Best model saved as: {OUTPUT_MODEL_NAME}")
            print(f"📊 Training results saved in: {results.save_dir}")
            print(f"\n🎉 Your trained model is ready to use!")
            print(f"💡 Update app/camera.py to use: model_path='{OUTPUT_MODEL_NAME}'")
        else:
            print(f"\n⚠️  Training completed, but best model not found at expected location.")
            print(f"📊 Check training results in: {results.save_dir}")
        
    except Exception as e:
        print(f"\n❌ Error during training: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Make sure ultralytics is installed: pip install ultralytics")
        print("   2. Check that data.yaml path is correct")
        print("   3. Verify dataset structure (train/images, train/labels)")
        print("   4. Reduce batch_size if you get memory errors")
        return

if __name__ == "__main__":
    # Check if ultralytics is installed
    try:
        import ultralytics
        print(f"✅ Ultralytics version: {ultralytics.__version__}")
    except ImportError:
        print("❌ Error: ultralytics not installed!")
        print("📦 Install it with: pip install ultralytics")
        exit(1)
    
    # Start training
    train_model()

