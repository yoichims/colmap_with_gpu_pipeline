#!/usr/bin/env python3
"""
COLMAP Full Pipeline Script
Usage: python colmap_pipeline.py /path/to/images/directory
"""

import os
import sys
import subprocess
import time
import click
from pathlib import Path


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    NC = "\033[0m"  # No Color


def print_step(message):
    print(f"{Colors.BLUE}[STEP]{Colors.NC} {message}")


def print_success(message):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")


def print_error(message):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")


def print_warning(message):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")


def print_info(message):
    print(f"{Colors.PURPLE}[INFO]{Colors.NC} {message}")


def determine_image_directory(input_path, fps, video_quality, force_extract, verbose):
    """Determine the image directory from input path (video or directory)"""
    input_path = input_path.resolve()

    if input_path.is_file() and is_video_file(input_path):
        # Input is a video file
        print_info(f"Input is a video file: {input_path.name}")

        # Create output directory for frames
        video_name = input_path.stem
        image_dir = input_path.parent / f"{video_name}_frames"

        # Extract frames from video
        if not extract_frames_from_video(
            input_path, image_dir, fps, video_quality, force_extract, verbose
        ):
            print_error("Failed to extract frames from video")
            return None

        return image_dir

    elif input_path.is_dir():
        # Input is a directory
        print_info(f"Input is a directory: {input_path.name}")
        return input_path
    else:
        print_error(
            f"Input path '{input_path}' is neither a valid video file nor a directory"
        )
        return None


def is_video_file(file_path):
    """Check if file is a video file"""
    video_extensions = {
        ".mp4",
        ".avi",
        ".mov",
        ".mkv",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
        ".3gp",
        ".ogv",
    }
    return file_path.suffix.lower() in video_extensions


def extract_frames_from_video(
    video_path,
    output_dir,
    fps=2.0,
    quality="medium",
    force_extract=False,
    verbose=False,
):
    """Extract frames from video using ffmpeg"""
    video_path = Path(video_path)
    output_dir = Path(output_dir)

    # Check if images already exist
    if not force_extract and output_dir.exists():
        existing_images = list(output_dir.glob("*.jpg")) + list(
            output_dir.glob("*.png")
        )
        if existing_images:
            print_success(
                f"Found {len(existing_images)} existing images in {output_dir}"
            )
            print_info(
                "Skipping frame extraction. Use --force-extract to re-extract frames."
            )
            return True

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Quality settings
    quality_settings = {
        "high": ["-q:v", "2"],  # High quality
        "medium": ["-q:v", "5"],  # Medium quality
        "low": ["-q:v", "10"],  # Lower quality, smaller files
    }

    # Build ffmpeg command
    ffmpeg_cmd = [
        "ffmpeg",
        "-i",
        str(video_path),
        "-vf",
        f"fps={fps}",
        *quality_settings[quality],
        "-y",  # Overwrite existing files
        str(output_dir / "frame_%06d.jpg"),
    ]

    print_step(f"Extracting frames from video: {video_path.name}")
    print_info(f"Output directory: {output_dir}")
    print_info(f"Frame rate: {fps} fps, Quality: {quality}")

    # Provide recommendations based on fps
    if fps < 1.0:
        print_warning(
            f"Low frame rate ({fps} fps) - may result in poor 3D reconstruction"
        )
        print_info("💡 Recommendation: Use 1.5-3.0 fps for better results")
    elif fps > 5.0:
        print_warning(
            f"High frame rate ({fps} fps) - will create many frames and slow processing"
        )
        print_info(
            "💡 Recommendation: Use 1.5-3.0 fps unless you need high temporal resolution"
        )

    if verbose:
        print_info(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")

    start_time = time.time()

    try:
        if verbose:
            subprocess.run(ffmpeg_cmd, check=True, text=True)
        else:
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)

        elapsed = time.time() - start_time

        # Count extracted frames
        extracted_frames = list(output_dir.glob("*.jpg"))
        print_success(f"Extracted {len(extracted_frames)} frames in {elapsed:.1f}s")

        # Provide guidance on frame count
        if len(extracted_frames) < 20:
            print_warning(
                "Very few frames extracted - may not be sufficient for 3D reconstruction"
            )
            print_info("💡 Consider increasing --fps or using a longer video")
        elif len(extracted_frames) > 500:
            print_warning(
                f"Many frames extracted ({len(extracted_frames)}) - processing will be slow"
            )
            print_info("💡 Consider reducing --fps for faster processing")

        if len(extracted_frames) == 0:
            print_error("No frames were extracted from the video")
            return False

        return True

    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print_error(f"Frame extraction failed after {elapsed:.1f}s")
        print_error(f"Return code: {e.returncode}")
        if hasattr(e, "stderr") and e.stderr:
            print_error(f"FFmpeg error: {e.stderr}")
        return False
    except FileNotFoundError:
        print_error("FFmpeg not found. Please install ffmpeg:")
        print_info("  Ubuntu/Debian: sudo apt install ffmpeg")
        print_info("  macOS: brew install ffmpeg")
        print_info("  Windows: Download from https://ffmpeg.org/")
        return False


def run_docker_command(command, step_name, verbose=False):
    """Run a docker command and handle errors"""
    print_step(f"Running: {step_name}")
    if verbose:
        print_info(f"Command: {' '.join(command)}")

    start_time = time.time()

    try:
        if verbose:
            # Show output in real-time for verbose mode
            result = subprocess.run(command, check=True, text=True)
        else:
            result = subprocess.run(command, check=True, capture_output=True, text=True)

        elapsed = time.time() - start_time
        print_success(f"{step_name} completed in {elapsed:.1f}s")

        if not verbose and hasattr(result, "stdout") and result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print_error(f"{step_name} failed after {elapsed:.1f}s")
        print_error(f"Return code: {e.returncode}")
        if hasattr(e, "stderr") and e.stderr:
            print_error(f"Error output: {e.stderr}")
        if hasattr(e, "stdout") and e.stdout:
            print_error(f"Standard output: {e.stdout}")
        return False


def check_directory(image_dir):
    """Check if directory exists and contains images"""
    image_dir = Path(image_dir)  # Ensure it's a Path object

    if not image_dir.exists() or not image_dir.is_dir():
        print_error(f"Directory '{image_dir}' does not exist!")
        return False

    # Check for image files
    image_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".tiff",
        ".tif",
        ".JPG",
        ".JPEG",
        ".PNG",
        ".TIFF",
        ".TIF",
    }
    image_files = []

    for file_path in image_dir.rglob("*"):
        if file_path.suffix in image_extensions:
            image_files.append(file_path)

    if not image_files:
        print_error(f"No image files found in '{image_dir}'")
        return False

    print_success(f"Found {len(image_files)} images in '{image_dir}'")
    return True


def clean_generated_files(input_path, verbose=False):
    """Clean all generated COLMAP files and extracted frames before any processing"""
    input_path = input_path.resolve()
    files_cleaned = []

    # Determine what would be the image directory and parent directory
    if input_path.is_file() and is_video_file(input_path):
        # For video files, clean the potential frames directory and database
        video_name = input_path.stem
        image_dir = input_path.parent / f"{video_name}_frames"
        parent_dir = input_path.parent
    else:
        # For image directories, clean from that directory and its parent
        image_dir = input_path
        parent_dir = input_path.parent

    # Change to parent directory for cleaning (same as processing)
    original_cwd = os.getcwd()
    os.chdir(parent_dir)

    try:
        # Clean database files in working directory
        for db_file in ["database.db"]:
            db_path = Path(db_file)
            if db_path.exists():
                db_path.unlink()
                files_cleaned.append(db_file)

        # Clean extracted frames directory (only if it looks like extracted frames)
        image_dir_name = image_dir.name
        if image_dir_name.endswith("_frames") and image_dir.exists():
            frame_files = list(image_dir.glob("frame_*.jpg")) + list(
                image_dir.glob("frame_*.png")
            )
            if frame_files:
                for frame_file in frame_files:
                    frame_file.unlink()
                files_cleaned.append(f"{len(frame_files)} extracted frames")

            # Remove frames directory if it's empty
            try:
                if not any(image_dir.iterdir()):
                    image_dir.rmdir()
                    files_cleaned.append(f"empty {image_dir_name} directory")
            except:
                pass

        # Clean sparse reconstruction
        sparse_path = image_dir / "sparse"
        if sparse_path.exists():
            import shutil

            shutil.rmtree(sparse_path)
            files_cleaned.append(f"{image_dir_name}/sparse/")

        # Clean dense reconstruction
        dense_path = image_dir / "dense"
        if dense_path.exists():
            import shutil

            shutil.rmtree(dense_path)
            files_cleaned.append(f"{image_dir_name}/dense/")

        if verbose and files_cleaned:
            print_info("Cleaned files:")
            for file_item in files_cleaned:
                print_info(f"  • {file_item}")

    finally:
        os.chdir(original_cwd)

    return len(files_cleaned) > 0


def check_step_completed(image_dir_name, step_number, parent_dir):
    """Check if a pipeline step was already completed"""
    original_cwd = os.getcwd()
    os.chdir(parent_dir)

    try:
        if step_number == 1:  # Feature Extraction
            return Path("database.db").exists()
        elif step_number == 2:  # Feature Matching
            # Check if database exists and has reasonable size (matches added)
            db_path = Path("database.db")
            return db_path.exists() and db_path.stat().st_size > 1000
        elif step_number == 3:  # Sparse Reconstruction
            return Path(f"{image_dir_name}/sparse/0").exists()
        elif step_number == 4:  # Image Undistortion
            dense_path = Path(f"{image_dir_name}/dense")
            return dense_path.exists() and any(dense_path.glob("images/*.jpg"))
        elif step_number == 5:  # Patch Match Stereo
            dense_path = Path(f"{image_dir_name}/dense")
            return dense_path.exists() and any(
                dense_path.glob("stereo/depth_maps/*.geometric.bin")
            )
        elif step_number == 6:  # Stereo Fusion
            return Path(f"{image_dir_name}/dense/fused.ply").exists()
        elif step_number == 7:  # Poisson Meshing
            return Path(f"{image_dir_name}/dense/meshed-poisson.ply").exists()
    finally:
        os.chdir(original_cwd)

    return False


def print_step_status(image_dir_name, parent_dir):
    """Print status of all pipeline steps"""
    step_names = [
        "Feature Extraction",
        "Feature Matching",
        "Sparse Reconstruction",
        "Image Undistortion",
        "Patch Match Stereo",
        "Stereo Fusion",
        "Poisson Meshing",
    ]

    print_info("Pipeline step status:")
    for i in range(1, 8):
        completed = check_step_completed(image_dir_name, i, parent_dir)
        status = "✅ COMPLETED" if completed else "❌ NOT DONE"
        print_info(f"  Step {i}/7 - {step_names[i - 1]}: {status}")


def create_directory(path):
    """Create directory if it doesn't exist"""
    os.makedirs(path, exist_ok=True)


@click.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--docker-image",
    default="roboticsmicrofarms/colmap:3.8",
    help="Docker image to use",
    show_default=True,
)
@click.option(
    "--max-image-size",
    type=int,
    default=2000,
    help="Maximum image size for processing",
    show_default=True,
)
@click.option(
    "--skip-dense",
    is_flag=True,
    default=False,
    help="Skip dense reconstruction (only run sparse reconstruction)",
)
@click.option(
    "--skip-mesh",
    is_flag=True,
    default=False,
    help="Skip mesh generation (run up to dense point cloud)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose output from Docker commands",
)
@click.option(
    "--fps",
    type=float,
    default=2.0,
    help="Frames per second to extract from video (default: 1 fps)",
    show_default=True,
)
@click.option(
    "--video-quality",
    type=click.Choice(["high", "medium", "low"]),
    default="medium",
    help="Quality of extracted frames",
    show_default=True,
)
@click.option(
    "--force-extract",
    is_flag=True,
    default=False,
    help="Force re-extraction of frames even if images already exist",
)
@click.option(
    "--clean",
    is_flag=True,
    default=False,
    help="Clean all generated files before processing (database, sparse, dense, frames)",
)
@click.option(
    "--clean-only",
    is_flag=True,
    default=False,
    help="Only clean generated files and exit (no processing)",
)
@click.option(
    "--step",
    type=click.IntRange(1, 7),
    default=None,
    help="Run only a specific step (1-7)",
)
@click.option(
    "--start-from",
    type=click.IntRange(1, 7),
    default=1,
    help="Start processing from a specific step (1-7)",
    show_default=True,
)
@click.option(
    "--stop-at",
    type=click.IntRange(1, 7),
    default=7,
    help="Stop processing at a specific step (1-7)",
    show_default=True,
)
def main(
    input_path,
    docker_image,
    max_image_size,
    skip_dense,
    skip_mesh,
    verbose,
    fps,
    video_quality,
    force_extract,
    clean,
    clean_only,
    step,
    start_from,
    stop_at,
):
    """Run complete COLMAP pipeline on a directory of images or extract frames from video first.

    INPUT_PATH: Path to directory containing images OR path to video file
    """
    # Clean option - remove all generated files BEFORE any processing
    if clean or clean_only:
        print_step("Cleaning generated files...")
        files_were_cleaned = clean_generated_files(input_path, verbose)
        if files_were_cleaned:
            print_success("Clean completed")
        else:
            print_info("No files to clean")

        if clean_only:
            print_info("Clean-only mode: exiting after cleanup")
            sys.exit(0)

    # Determine image directory from input (video or directory)
    image_dir = determine_image_directory(
        input_path, fps, video_quality, force_extract, verbose
    )
    if image_dir is None:
        sys.exit(1)

    # Setup paths
    image_dir_name = image_dir.name
    parent_dir = image_dir.parent

    # Validate step options
    if step and (start_from != 1 or stop_at != 7):
        print_error("Cannot use --step with --start-from or --stop-at")
        sys.exit(1)

    if start_from > stop_at:
        print_error("--start-from cannot be greater than --stop-at")
        sys.exit(1)

    # Validate image directory
    if not check_directory(image_dir):
        sys.exit(1)

    # Change to parent directory
    original_cwd = os.getcwd()
    os.chdir(parent_dir)

    # Show current pipeline status
    if verbose or step or start_from > 1:
        print_step_status(image_dir_name, parent_dir)
        print()

    print_success(f"Starting COLMAP pipeline for '{image_dir_name}'")
    print_info(f"Working directory: {parent_dir}")
    print_info(f"Docker image: {docker_image}")

    # Configure execution mode
    if step:
        print_info(f"Running only step {step}/7")
        start_from = step
        stop_at = step
    elif start_from > 1 or stop_at < 7:
        print_info(f"Running steps {start_from}-{stop_at}")

    if skip_dense:
        print_warning("Dense reconstruction will be skipped")
        stop_at = min(stop_at, 3)  # Can't go beyond sparse if skipping dense
    elif skip_mesh:
        print_warning("Mesh generation will be skipped")
        stop_at = min(stop_at, 6)  # Can't do meshing if skipping mesh

    try:
        # Define all pipeline steps with step numbers
        all_steps = [
            {
                "number": 1,
                "name": "1/7 - Feature Extraction",
                "category": "sparse",
                "command": [
                    "docker",
                    "run",
                    "--rm",
                    "--gpus",
                    "all",
                    "-v",
                    f"{os.getcwd()}:/workspace",
                    "-w",
                    "/workspace",
                    docker_image,
                    "colmap",
                    "feature_extractor",
                    "--database_path",
                    "database.db",
                    "--image_path",
                    image_dir_name,
                ],
            },
            {
                "number": 2,
                "name": "2/7 - Feature Matching",
                "category": "sparse",
                "command": [
                    "docker",
                    "run",
                    "--rm",
                    "--gpus",
                    "all",
                    "-v",
                    f"{os.getcwd()}:/workspace",
                    "-w",
                    "/workspace",
                    docker_image,
                    "colmap",
                    "exhaustive_matcher",
                    "--database_path",
                    "database.db",
                ],
            },
            {
                "number": 3,
                "name": "3/7 - Sparse Reconstruction",
                "category": "sparse",
                "command": [
                    "docker",
                    "run",
                    "--rm",
                    "--gpus",
                    "all",
                    "-v",
                    f"{os.getcwd()}:/workspace",
                    "-w",
                    "/workspace",
                    docker_image,
                    "colmap",
                    "mapper",
                    "--database_path",
                    "database.db",
                    "--image_path",
                    f"{image_dir_name}/",
                    "--output_path",
                    f"{image_dir_name}/sparse/",
                ],
            },
            {
                "number": 4,
                "name": "4/7 - Image Undistortion",
                "category": "dense",
                "command": [
                    "docker",
                    "run",
                    "--rm",
                    "--gpus",
                    "all",
                    "-v",
                    f"{os.getcwd()}:/workspace",
                    "-w",
                    "/workspace",
                    docker_image,
                    "colmap",
                    "image_undistorter",
                    "--image_path",
                    f"{image_dir_name}/",
                    "--input_path",
                    f"{image_dir_name}/sparse/0",
                    "--output_path",
                    f"{image_dir_name}/dense",
                    "--output_type",
                    "COLMAP",
                    "--max_image_size",
                    str(max_image_size),
                ],
            },
            {
                "number": 5,
                "name": "5/7 - Patch Match Stereo",
                "category": "dense",
                "command": [
                    "docker",
                    "run",
                    "--rm",
                    "--gpus",
                    "all",
                    "-v",
                    f"{os.getcwd()}:/workspace",
                    "-w",
                    "/workspace",
                    docker_image,
                    "colmap",
                    "patch_match_stereo",
                    "--workspace_path",
                    f"{image_dir_name}/dense",
                    "--workspace_format",
                    "COLMAP",
                    "--PatchMatchStereo.geom_consistency",
                    "true",
                ],
            },
            {
                "number": 6,
                "name": "6/7 - Stereo Fusion",
                "category": "dense",
                "command": [
                    "docker",
                    "run",
                    "--rm",
                    "--gpus",
                    "all",
                    "-v",
                    f"{os.getcwd()}:/workspace",
                    "-w",
                    "/workspace",
                    docker_image,
                    "colmap",
                    "stereo_fusion",
                    "--workspace_path",
                    f"{image_dir_name}/dense",
                    "--workspace_format",
                    "COLMAP",
                    "--input_type",
                    "geometric",
                    "--output_path",
                    f"{image_dir_name}/dense/fused.ply",
                ],
            },
            {
                "number": 7,
                "name": "7/7 - Poisson Meshing",
                "category": "mesh",
                "command": [
                    "docker",
                    "run",
                    "--rm",
                    "--gpus",
                    "all",
                    "-v",
                    f"{os.getcwd()}:/workspace",
                    "-w",
                    "/workspace",
                    docker_image,
                    "colmap",
                    "poisson_mesher",
                    "--input_path",
                    f"{image_dir_name}/dense/fused.ply",
                    "--output_path",
                    f"{image_dir_name}/dense/meshed-poisson.ply",
                ],
            },
        ]

        # Filter steps based on options and step range
        steps = []
        for step_def in all_steps:
            step_num = step_def["number"]

            # Check if step is in range
            if step_num < start_from or step_num > stop_at:
                continue

            # Check category filters
            if step_def["category"] == "sparse":
                steps.append(step_def)
            elif step_def["category"] == "dense" and not skip_dense:
                steps.append(step_def)
            elif step_def["category"] == "mesh" and not skip_dense and not skip_mesh:
                steps.append(step_def)

        # Create necessary directories
        create_directory(f"{image_dir_name}/sparse")

        # Execute pipeline
        total_start = time.time()

        for step in steps:
            # Run the step
            if not run_docker_command(step["command"], step["name"], verbose):
                print_error(f"Pipeline failed at step: {step['name']}")
                sys.exit(1)

            # Check if sparse reconstruction created a model
            if step["name"].startswith("3/7"):  # Sparse reconstruction step
                if not os.path.exists(f"{image_dir_name}/sparse/0"):
                    print_error("Sparse reconstruction failed - no model created")
                    sys.exit(1)

        total_elapsed = time.time() - total_start

        # Success summary
        print("\n" + "=" * 50)
        print_success("COLMAP PIPELINE COMPLETED SUCCESSFULLY!")
        print_success(f"Total processing time: {total_elapsed / 60:.1f} minutes")
        print("=" * 50)
        print("Output files:")
        print(f"  • Sparse reconstruction: {image_dir_name}/sparse/")
        if not skip_dense:
            print(f"  • Dense point cloud:     {image_dir_name}/dense/fused.ply")
            if not skip_mesh:
                print(
                    f"  • Mesh:                  {image_dir_name}/dense/meshed-poisson.ply"
                )
        print("  • Database:              database.db")
        print()
        print_warning("You can view the results in MeshLab, Blender, or CloudCompare")

    except KeyboardInterrupt:
        print_warning("\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)
    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    main()
