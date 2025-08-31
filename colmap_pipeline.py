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
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    NC = '\033[0m'  # No Color

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
        
        if not verbose and hasattr(result, 'stdout') and result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print_error(f"{step_name} failed after {elapsed:.1f}s")
        print_error(f"Return code: {e.returncode}")
        if hasattr(e, 'stderr') and e.stderr:
            print_error(f"Error output: {e.stderr}")
        if hasattr(e, 'stdout') and e.stdout:
            print_error(f"Standard output: {e.stdout}")
        return False

def check_directory(image_dir):
    """Check if directory exists and contains images"""
    if not os.path.isdir(image_dir):
        print_error(f"Directory '{image_dir}' does not exist!")
        return False
    
    # Check for image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.JPG', '.JPEG', '.PNG', '.TIFF', '.TIF'}
    image_files = []
    
    for file_path in Path(image_dir).rglob('*'):
        if file_path.suffix in image_extensions:
            image_files.append(file_path)
    
    if not image_files:
        print_error(f"No image files found in '{image_dir}'")
        return False
    
    print_success(f"Found {len(image_files)} images in '{image_dir}'")
    return True

def create_directory(path):
    """Create directory if it doesn't exist"""
    os.makedirs(path, exist_ok=True)

@click.command()
@click.argument('image_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option('--docker-image', default='roboticsmicrofarms/colmap:3.8', 
              help='Docker image to use', show_default=True)
@click.option('--max-image-size', type=int, default=2000,
              help='Maximum image size for processing', show_default=True)
@click.option('--skip-dense', is_flag=True, default=False,
              help='Skip dense reconstruction (only run sparse reconstruction)')
@click.option('--skip-mesh', is_flag=True, default=False,
              help='Skip mesh generation (run up to dense point cloud)')
@click.option('--verbose', '-v', is_flag=True, default=False,
              help='Enable verbose output from Docker commands')
def main(image_dir, docker_image, max_image_size, skip_dense, skip_mesh, verbose):
    """Run complete COLMAP pipeline on a directory of images.
    
    IMAGE_DIR: Path to directory containing images
    """
    if not check_directory(image_dir):
        sys.exit(1)
    
    # Setup paths
    image_dir_name = image_dir.name
    parent_dir = image_dir.parent
    
    # Change to parent directory
    original_cwd = os.getcwd()
    os.chdir(parent_dir)
    
    print_success(f"Starting COLMAP pipeline for '{image_dir_name}'")
    print_info(f"Working directory: {parent_dir}")
    print_info(f"Docker image: {docker_image}")
    
    if skip_dense:
        print_warning("Dense reconstruction will be skipped")
    elif skip_mesh:
        print_warning("Mesh generation will be skipped")
    
    try:
        # Define all pipeline steps
        all_steps = [
            {
                'name': '1/7 - Feature Extraction',
                'category': 'sparse',
                'command': [
                    'docker', 'run', '--rm', '--gpus', 'all',
                    '-v', f'{os.getcwd()}:/workspace',
                    '-w', '/workspace',
                    docker_image,
                    'colmap', 'feature_extractor',
                    '--database_path', 'database.db',
                    '--image_path', image_dir_name
                ]
            },
            {
                'name': '2/7 - Feature Matching',
                'category': 'sparse',
                'command': [
                    'docker', 'run', '--rm', '--gpus', 'all',
                    '-v', f'{os.getcwd()}:/workspace',
                    '-w', '/workspace',
                    docker_image,
                    'colmap', 'exhaustive_matcher',
                    '--database_path', 'database.db'
                ]
            },
            {
                'name': '3/7 - Sparse Reconstruction',
                'category': 'sparse',
                'command': [
                    'docker', 'run', '--rm', '--gpus', 'all',
                    '-v', f'{os.getcwd()}:/workspace',
                    '-w', '/workspace',
                    docker_image,
                    'colmap', 'mapper',
                    '--database_path', 'database.db',
                    '--image_path', f'{image_dir_name}/',
                    '--output_path', f'{image_dir_name}/sparse/'
                ]
            },
            {
                'name': '4/7 - Image Undistortion',
                'category': 'dense',
                'command': [
                    'docker', 'run', '--rm', '--gpus', 'all',
                    '-v', f'{os.getcwd()}:/workspace',
                    '-w', '/workspace',
                    docker_image,
                    'colmap', 'image_undistorter',
                    '--image_path', f'{image_dir_name}/',
                    '--input_path', f'{image_dir_name}/sparse/0',
                    '--output_path', f'{image_dir_name}/dense',
                    '--output_type', 'COLMAP',
                    '--max_image_size', str(max_image_size)
                ]
            },
            {
                'name': '5/7 - Patch Match Stereo',
                'category': 'dense',
                'command': [
                    'docker', 'run', '--rm', '--gpus', 'all',
                    '-v', f'{os.getcwd()}:/workspace',
                    '-w', '/workspace',
                    docker_image,
                    'colmap', 'patch_match_stereo',
                    '--workspace_path', f'{image_dir_name}/dense',
                    '--workspace_format', 'COLMAP',
                    '--PatchMatchStereo.geom_consistency', 'true'
                ]
            },
            {
                'name': '6/7 - Stereo Fusion',
                'category': 'dense',
                'command': [
                    'docker', 'run', '--rm', '--gpus', 'all',
                    '-v', f'{os.getcwd()}:/workspace',
                    '-w', '/workspace',
                    docker_image,
                    'colmap', 'stereo_fusion',
                    '--workspace_path', f'{image_dir_name}/dense',
                    '--workspace_format', 'COLMAP',
                    '--input_type', 'geometric',
                    '--output_path', f'{image_dir_name}/dense/fused.ply'
                ]
            },
            {
                'name': '7/7 - Poisson Meshing',
                'category': 'mesh',
                'command': [
                    'docker', 'run', '--rm', '--gpus', 'all',
                    '-v', f'{os.getcwd()}:/workspace',
                    '-w', '/workspace',
                    docker_image,
                    'colmap', 'poisson_mesher',
                    '--input_path', f'{image_dir_name}/dense/fused.ply',
                    '--output_path', f'{image_dir_name}/dense/meshed-poisson.ply'
                ]
            }
        ]
        
        # Filter steps based on options
        steps = []
        for step in all_steps:
            if step['category'] == 'sparse':
                steps.append(step)
            elif step['category'] == 'dense' and not skip_dense:
                steps.append(step)
            elif step['category'] == 'mesh' and not skip_dense and not skip_mesh:
                steps.append(step)
        
        # Create necessary directories
        create_directory(f'{image_dir_name}/sparse')
        
        # Execute pipeline
        total_start = time.time()
        
        for i, step in enumerate(steps):
            # Special handling for step 3 - check if sparse reconstruction was successful
            if not run_docker_command(step['command'], step['name'], verbose):
                print_error(f"Pipeline failed at step: {step['name']}")
                sys.exit(1)
            
            # Check if sparse reconstruction created a model
            if step['name'].startswith('3/7'):  # Sparse reconstruction step
                if not os.path.exists(f'{image_dir_name}/sparse/0'):
                    print_error("Sparse reconstruction failed - no model created")
                    sys.exit(1)
        
        total_elapsed = time.time() - total_start
        
        # Success summary
        print("\n" + "="*50)
        print_success(f"COLMAP PIPELINE COMPLETED SUCCESSFULLY!")
        print_success(f"Total processing time: {total_elapsed/60:.1f} minutes")
        print("="*50)
        print("Output files:")
        print(f"  • Sparse reconstruction: {image_dir_name}/sparse/")
        if not skip_dense:
            print(f"  • Dense point cloud:     {image_dir_name}/dense/fused.ply")
            if not skip_mesh:
                print(f"  • Mesh:                  {image_dir_name}/dense/meshed-poisson.ply")
        print(f"  • Database:              database.db")
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