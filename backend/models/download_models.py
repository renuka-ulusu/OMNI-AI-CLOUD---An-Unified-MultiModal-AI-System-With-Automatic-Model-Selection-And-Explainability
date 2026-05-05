"""
Model Download Script
Downloads and caches large AI models to local storage
Ensures complete downloads with progress tracking
"""

import os
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch


# Define model storage directory
MODELS_DIR = Path(__file__).parent / "downloaded_models"
MODELS_DIR.mkdir(exist_ok=True)

# Model configurations
MODELS = {
    "flan-t5-large": {
        "name": "google/flan-t5-large",
        "size": "~12GB",
        "local_path": MODELS_DIR / "flan-t5-large"
    },
    "flan-t5-base": {
        "name": "google/flan-t5-base",
        "size": "~1GB",
        "local_path": MODELS_DIR / "flan-t5-base"
    }
}


def download_model(model_key: str, force_redownload: bool = False):
    """
    Download a model completely to local storage
    
    Args:
        model_key: Key from MODELS dict (e.g., 'flan-t5-large')
        force_redownload: Force redownload even if model exists
    """
    if model_key not in MODELS:
        print(f"❌ Unknown model: {model_key}")
        print(f"Available models: {list(MODELS.keys())}")
        return False
    
    model_info = MODELS[model_key]
    model_name = model_info["name"]
    local_path = model_info["local_path"]
    
    print(f"\n{'='*60}")
    print(f"📥 Downloading: {model_name}")
    print(f"📦 Size: {model_info['size']}")
    print(f"📂 Local path: {local_path}")
    print(f"{'='*60}\n")
    
    # Check if model already exists
    if local_path.exists() and not force_redownload:
        print(f"✅ Model already exists at {local_path}")
        print("Use force_redownload=True to redownload")
        return True
    
    try:
        # Download tokenizer
        print("⏬ Downloading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=None,
            local_files_only=False
        )
        tokenizer.save_pretrained(local_path)
        print("✅ Tokenizer downloaded")
        
        # Download model with progress
        print("⏬ Downloading model (this may take a while)...")
        print("💡 The model will download completely - don't interrupt!")
        
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            cache_dir=None,
            local_files_only=False,
            torch_dtype=torch.float32,  # Ensure full precision download
            low_cpu_mem_usage=True      # Optimize memory usage
        )
        
        # Save model to local path
        print("💾 Saving model to local storage...")
        model.save_pretrained(local_path)
        
        print(f"\n✅ SUCCESS! Model downloaded completely to:")
        print(f"   {local_path}")
        print(f"\n📊 Folder size:")
        
        # Calculate folder size
        total_size = sum(
            f.stat().st_size 
            for f in local_path.rglob('*') 
            if f.is_file()
        )
        size_gb = total_size / (1024**3)
        print(f"   {size_gb:.2f} GB")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error downloading model: {str(e)}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Check your internet connection")
        print("   2. Ensure you have enough disk space (~15GB free)")
        print("   3. Try running with administrator privileges")
        print("   4. Check if HuggingFace is accessible")
        return False


def get_model_path(model_key: str) -> Path:
    """
    Get the local path for a model
    
    Args:
        model_key: Key from MODELS dict
    
    Returns:
        Path to the local model directory
    """
    if model_key not in MODELS:
        raise ValueError(f"Unknown model: {model_key}")
    return MODELS[model_key]["local_path"]


def check_model_status(model_key: str):
    """
    Check if a model is downloaded and get its status
    """
    if model_key not in MODELS:
        print(f"❌ Unknown model: {model_key}")
        return False
    
    model_info = MODELS[model_key]
    local_path = model_info["local_path"]
    
    print(f"\n{'='*60}")
    print(f"📊 Model Status: {model_info['name']}")
    print(f"{'='*60}")
    print(f"Expected size: {model_info['size']}")
    print(f"Local path: {local_path}")
    
    if local_path.exists():
        # Calculate actual size
        total_size = sum(
            f.stat().st_size 
            for f in local_path.rglob('*') 
            if f.is_file()
        )
        size_gb = total_size / (1024**3)
        
        # Count files
        file_count = len(list(local_path.rglob('*')))
        
        print(f"Status: ✅ Downloaded")
        print(f"Actual size: {size_gb:.2f} GB")
        print(f"Files: {file_count}")
        
        # Check if download seems complete
        if size_gb < 1.0 and model_key == "flan-t5-large":
            print("⚠️  WARNING: Size seems too small! Download may be incomplete.")
            print("   Expected: ~12GB, Found: {:.2f}GB".format(size_gb))
            print("   Consider redownloading with force_redownload=True")
        else:
            print("✅ Download appears complete")
        
        return True
    else:
        print(f"Status: ❌ Not downloaded")
        print(f"Run: download_model('{model_key}') to download")
        return False


if __name__ == "__main__":
    import sys
    
    print("\n🤖 OmniAI Model Downloader")
    print("="*60)
    
    if len(sys.argv) < 2:
        print("\n📋 Available models:")
        for key, info in MODELS.items():
            print(f"\n  {key}:")
            print(f"    Name: {info['name']}")
            print(f"    Size: {info['size']}")
        
        print("\n💡 Usage:")
        print(f"  python {Path(__file__).name} <model_key>")
        print(f"  python {Path(__file__).name} flan-t5-large")
        print(f"\n  Or check status:")
        print(f"  python {Path(__file__).name} status flan-t5-large")
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "status":
        if len(sys.argv) < 3:
            print("❌ Please specify model key")
            sys.exit(1)
        model_key = sys.argv[2]
        check_model_status(model_key)
    
    else:
        model_key = command
        force = "--force" in sys.argv
        download_model(model_key, force_redownload=force)
