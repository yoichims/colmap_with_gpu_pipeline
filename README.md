# COLMAP Pipeline Script

A complete automated pipeline for 3D reconstruction using COLMAP with Docker. This script can extract frames from videos and process them through the entire COLMAP pipeline to generate sparse reconstructions, dense point clouds, and 3D meshes.

## Features

- 🎥 **Video Frame Extraction** - Extract frames from videos using FFmpeg
- 📸 **Image Processing** - Process existing image directories
- 🏗️ **Complete COLMAP Pipeline** - From feature extraction to final mesh
- 🐳 **Docker-based** - No complex COLMAP installation required
- 🎯 **GPU Acceleration** - Full CUDA support for faster processing
- ⚙️ **Flexible Options** - Skip steps, adjust quality, verbose output
- 🔄 **Smart Resume** - Skip frame extraction if images already exist

## Prerequisites

### System Requirements
- Docker with GPU support (NVIDIA Container Toolkit)
- NVIDIA GPU with CUDA drivers
- FFmpeg (for video processing)
- Python 3.6+

### Installation

1. **Install Docker and NVIDIA Container Toolkit:**
   ```bash
   # Install Docker
   sudo apt update
   sudo apt install docker.io
   
   # Install NVIDIA Container Toolkit
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
   curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
     sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
   
   sudo apt update
   sudo apt install nvidia-container-toolkit
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```

2. **Install FFmpeg:**
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # Windows
   # Download from https://ffmpeg.org/
   ```

3. **Install Python dependencies:**
   ```bash
   pip install click
   ```

4. **Download the script:**
   ```bash
   curl -O https://raw.githubusercontent.com/your-repo/colmap-pipeline/main/colmap_pipeline.py
   chmod +x colmap_pipeline.py
   ```

## Usage

### Basic Usage

```bash
# Process a video file
python colmap_pipeline.py /path/to/video.mp4

# Process an image directory
python colmap_pipeline.py /path/to/images/
```

### Advanced Options

```bash
# Custom frame extraction rate
python colmap_pipeline.py video.mp4 --fps 2.0

# High quality frame extraction
python colmap_pipeline.py video.mp4 --video-quality high

# Skip dense reconstruction (sparse only)
python colmap_pipeline.py video.mp4 --skip-dense

# Skip mesh generation (up to dense point cloud)
python colmap_pipeline.py video.mp4 --skip-mesh

# Verbose output
python colmap_pipeline.py video.mp4 --verbose

# Force re-extraction of frames
python colmap_pipeline.py video.mp4 --force-extract

# Custom Docker image
python colmap_pipeline.py video.mp4 --docker-image colmap/colmap:3.9

# Smaller image processing
python colmap_pipeline.py video.mp4 --max-image-size 1500
```

### Complete Example

```bash
# Process a drone video with optimal settings
python colmap_pipeline.py drone_flight.mp4 \
    --fps 1.0 \
    --video-quality high \
    --max-image-size 2000 \
    --verbose
```

## Command Line Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `INPUT_PATH` | Path | Required | Video file or image directory |
| `--fps` | Float | 1.0 | Frames per second to extract from video |
| `--video-quality` | Choice | medium | Quality of extracted frames (high/medium/low) |
| `--force-extract` | Flag | False | Force re-extraction even if frames exist |
| `--skip-dense` | Flag | False | Skip dense reconstruction |
| `--skip-mesh` | Flag | False | Skip mesh generation |
| `--max-image-size` | Integer | 2000 | Maximum image size for processing |
| `--docker-image` | String | roboticsmicrofarms/colmap:3.8 | Docker image to use |
| `--verbose` | Flag | False | Enable verbose output |

## Pipeline Steps

The script executes the following COLMAP pipeline:

1. **Frame Extraction** (if video input)
   - Extract frames at specified fps
   - Save as high-quality JPEG images
   - Skip if frames already exist

2. **Feature Extraction**
   - Detect and describe image features
   - SIFT features by default

3. **Feature Matching** 
   - Match features between images
   - Exhaustive matching for best results

4. **Sparse Reconstruction**
   - Structure-from-Motion (SfM)
   - Camera pose estimation
   - Sparse 3D point cloud

5. **Image Undistortion** (dense pipeline)
   - Rectify images for stereo processing
   - Generate depth maps

6. **Patch Match Stereo** (dense pipeline)
   - Dense stereo matching
   - Per-pixel depth estimation

7. **Stereo Fusion** (dense pipeline)
   - Fuse depth maps into point cloud
   - Generate dense 3D reconstruction

8. **Poisson Meshing** (mesh generation)
   - Create watertight mesh from point cloud
   - Surface reconstruction

## Output Structure

### For Video Input (`video.mp4`)
```
video.mp4
video_frames/                    # Auto-created frame directory
├── frame_000001.jpg            # Extracted frames
├── frame_000002.jpg
├── ...
├── database.db                 # COLMAP database
├── sparse/                     # Sparse reconstruction
│   └── 0/
│       ├── cameras.bin
│       ├── images.bin
│       └── points3D.bin
└── dense/                      # Dense reconstruction
    ├── fused.ply              # Dense point cloud
    ├── meshed-poisson.ply     # Final mesh
    └── ...
```

### For Image Directory
```
images/
├── img001.jpg                 # Input images
├── img002.jpg
├── ...
├── database.db               # COLMAP database  
├── sparse/                   # Sparse reconstruction
└── dense/                    # Dense reconstruction
    ├── fused.ply            # Dense point cloud
    └── meshed-poisson.ply   # Final mesh
```

## Supported Formats

### Video Formats
- MP4, AVI, MOV, MKV, WMV
- FLV, WebM, M4V, 3GP, OGV

### Image Formats  
- JPEG, PNG, TIFF, TIF
- Both lowercase and uppercase extensions

## Viewing Results

The output files can be viewed in various 3D applications:

- **MeshLab** - Free, cross-platform mesh viewer
- **Blender** - Full 3D modeling suite  
- **CloudCompare** - Point cloud processing
- **Open3D** - Python-based 3D library

```bash
# Install MeshLab for viewing results
sudo apt install meshlab

# Open the mesh
meshlab video_frames/dense/meshed-poisson.ply
```

## Troubleshooting

### Common Issues

**GPU not detected:**
```bash
# Test GPU access
docker run --rm --gpus all nvidia/cuda:11.8-runtime-ubuntu22.04 nvidia-smi
```

**FFmpeg not found:**
```bash
# Install FFmpeg
sudo apt install ffmpeg
```

**Permission denied:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in
```

**Out of memory:**
```bash
# Reduce image size
python colmap_pipeline.py video.mp4 --max-image-size 1000
```

**Video extraction fails:**
```bash
# Check video format
ffmpeg -i your_video.mp4

# Try different quality
python colmap_pipeline.py video.mp4 --video-quality low
```

### Performance Tips

1. **Frame Rate**: Use 0.5-2.0 fps for most scenes
2. **Image Size**: 1500-2000px is usually sufficient  
3. **Quality**: Use 'medium' quality for most cases
4. **GPU Memory**: Monitor with `nvidia-smi`

## Examples

### Drone Footage Processing
```bash
# High-quality processing of drone video
python colmap_pipeline.py drone_flight.mp4 \
    --fps 1.0 \
    --video-quality high \
    --max-image-size 2000
```

### Quick Preview  
```bash
# Fast preview (sparse only)
python colmap_pipeline.py video.mp4 \
    --fps 0.5 \
    --video-quality low \
    --skip-dense
```

### Existing Images
```bash
# Process existing image directory
python colmap_pipeline.py ./photos/ \
    --max-image-size 1500
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [COLMAP](https://colmap.github.io/) - Structure-from-Motion and Multi-View Stereo
- [roboticsmicrofarms/colmap](https://hub.docker.com/r/roboticsmicrofarms/colmap) - Docker image
- [FFmpeg](https://ffmpeg.org/) - Video processing

## Citation

If you use this pipeline in your research, please cite the original COLMAP paper:

```bibtex
@inproceedings{schoenberger2016sfm,
    author={Sch\"{o}nberger, Johannes Lutz and Frahm, Jan-Michael},
    title={Structure-from-Motion Revisited},
    booktitle={Conference on Computer Vision and Pattern Recognition (CVPR)},
    year={2016},
}
```