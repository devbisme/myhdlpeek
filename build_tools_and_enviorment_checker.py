import os
import platform
import sys
from pathlib import Path



######################
#enviorment inspection
######################

#usefull when working with pycharm, windows, wsl, and conda

def get_os():
    system = platform.system()
    if system == 'Linux':
        with open('/proc/version', 'r') as f:
            if 'microsoft' in f.read().lower():
                return 'Windows Subsystem for Linux (WSL)'
        return 'Linux'
    elif system == 'Darwin':
        return 'macOS'
    elif system == 'Windows':
        return 'Windows'
    else:
        return 'Unknown OS'

def in_virtual_env():
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

def get_virtual_env_info():
    if in_virtual_env():
        venv_path = sys.prefix
        return {
            "is_virtual_env": True,
            "path": venv_path,
            "name": os.path.basename(venv_path),
            "is_conda": os.path.exists(os.path.join(venv_path, 'conda-meta'))
        }
    return {"is_virtual_env": False}

def in_docker():
    path = '/proc/self/cgroup'
    return os.path.exists('/.dockerenv') or os.path.isfile(path) and any('docker' in line for line in open(path))

def get_docker_container_id():
    if in_docker():
        with open('/proc/self/cgroup', 'r') as f:
            for line in f:
                if 'docker' in line:
                    return line.split('/')[-1].strip()
    return None

def get_current_path():
    return os.getcwd()

# Print system information
print(f"Operating System: {get_os()}")
print(f"Current Path: {get_current_path()}")

venv_info = get_virtual_env_info()
print(f"Running in Virtual Environment: {'Yes' if venv_info['is_virtual_env'] else 'No'}")
if venv_info['is_virtual_env']:
    print(f"Virtual Environment Path: {venv_info['path']}")
    print(f"Virtual Environment Name: {venv_info['name']}")
    print(f"Virtual Environment Type: {'Conda' if venv_info['is_conda'] else 'Python'}")
    # Instructions for activating the virtual environment
    activation_cmd = "source" if os.name != "nt" else ""
    print(f"To activate this environment, run: `{activation_cmd} {os.path.join(venv_info['path'], 'bin', 'activate')}`" if not venv_info['is_conda'] else f"To activate this Conda environment, run: `conda activate {venv_info['name']}`")

docker_id = get_docker_container_id()
print(f"Running in Docker: {'Yes' if docker_id else 'No'}")
if docker_id:
    print(f"Docker Container ID: {docker_id}")

##########################
#ipython notebooks to html
##########################

#insures that the all notebooks have an HTML equal for viewing if
#a notebook viewer is not available

from nbconvert import HTMLExporter
import nbformat

def convert_notebooks_to_html(notebook_path, output_path):
    notebook_dir = Path(notebook_path)
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    html_exporter = HTMLExporter()
    html_exporter.template_name = 'classic'

    for file in notebook_dir.glob('*.ipynb'):
        print(f"Converting {file.name} to HTML.")
        notebook = nbformat.read(file, as_version=4)
        (body, resources) = html_exporter.from_notebook_node(notebook)

        html_file = output_dir / (file.stem + '.html')
        html_file.write_text(body, encoding='utf-8')
        print(f"Created {html_file}")

# Specify your path here
notebook_directory = Path.cwd()/'examples'
html_output_directory = notebook_directory

convert_notebooks_to_html(notebook_directory, html_output_directory)


