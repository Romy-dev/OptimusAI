#!/bin/bash
# Setup ComfyUI + FLUX.1 schnell GGUF for Apple M4 (16GB)
# Run this script from the optimusai root directory

set -e

COMFYUI_DIR="/Users/kerefranck/comfyui"
PYTHON="python3.11"

echo "=== OptimusAI — ComfyUI + FLUX Setup ==="
echo ""

# Check Python
if ! command -v $PYTHON &> /dev/null; then
    PYTHON="python3"
    if ! command -v $PYTHON &> /dev/null; then
        echo "❌ Python 3.11+ not found. Install from https://www.python.org/downloads/"
        exit 1
    fi
fi

PY_VERSION=$($PYTHON --version | cut -d' ' -f2)
echo "✓ Python: $PY_VERSION"

# Clone ComfyUI
if [ ! -d "$COMFYUI_DIR" ]; then
    echo "📦 Cloning ComfyUI..."
    git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFYUI_DIR"
else
    echo "✓ ComfyUI already cloned at $COMFYUI_DIR"
fi

cd "$COMFYUI_DIR"

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    $PYTHON -m venv venv
fi

source venv/bin/activate

# Install deps
echo "📥 Installing PyTorch + ComfyUI dependencies..."
pip install --upgrade pip
pip install torch torchvision torchaudio
pip install -r requirements.txt

# Install GGUF support
if [ ! -d "custom_nodes/ComfyUI-GGUF" ]; then
    echo "📥 Installing ComfyUI-GGUF node..."
    cd custom_nodes
    git clone https://github.com/city96/ComfyUI-GGUF.git
    cd ComfyUI-GGUF
    pip install -r requirements.txt
    cd ../..
else
    echo "✓ ComfyUI-GGUF already installed"
fi

# Create model directories
mkdir -p models/diffusion_models
mkdir -p models/vae
mkdir -p models/clip
mkdir -p models/clip_vision

echo ""
echo "=== Downloading FLUX.1 schnell GGUF models ==="
echo "(This will download ~10 GB total)"
echo ""

# FLUX.1 schnell Q4_K_S (~6.5 GB) — best for 16GB Mac
if [ ! -f "models/diffusion_models/flux1-schnell-Q4_K_S.gguf" ]; then
    echo "📥 Downloading FLUX.1 schnell Q4_K_S (6.5 GB)..."
    curl -L "https://huggingface.co/city96/FLUX.1-schnell-gguf/resolve/main/flux1-schnell-Q4_K_S.gguf" \
        -o "models/diffusion_models/flux1-schnell-Q4_K_S.gguf"
else
    echo "✓ FLUX.1 schnell Q4_K_S already downloaded"
fi

# T5-XXL text encoder Q4 (~5 GB)
if [ ! -f "models/clip/t5xxl_fp8_e4m3fn.safetensors" ]; then
    echo "📥 Downloading T5-XXL FP8 text encoder (4.9 GB)..."
    curl -L "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors" \
        -o "models/clip/t5xxl_fp8_e4m3fn.safetensors"
else
    echo "✓ T5-XXL FP8 already downloaded"
fi

# CLIP-L text encoder (~250 MB)
if [ ! -f "models/clip/clip_l.safetensors" ]; then
    echo "📥 Downloading CLIP-L text encoder (246 MB)..."
    curl -L "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors" \
        -o "models/clip/clip_l.safetensors"
else
    echo "✓ CLIP-L already downloaded"
fi

# FLUX VAE (~335 MB)
if [ ! -f "models/vae/ae.safetensors" ]; then
    echo "📥 Downloading FLUX VAE (335 MB)..."
    curl -L "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/ae.safetensors" \
        -o "models/vae/ae.safetensors"
else
    echo "✓ FLUX VAE already downloaded"
fi

echo ""
echo "=== ✅ Setup complete! ==="
echo ""
echo "To start ComfyUI:"
echo "  cd $COMFYUI_DIR"
echo "  source venv/bin/activate"
echo "  python main.py --force-fp16 --listen 0.0.0.0 --port 8188"
echo ""
echo "ComfyUI will be available at: http://localhost:8188"
echo "OptimusAI will connect to it automatically."
