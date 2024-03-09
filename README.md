# Streamlining GPU-Enabled VM Creation in Google Cloud Compute

This project automates the process of finding an available zone within Google Cloud Compute Engine (GCE) that supports a specified GPU type and then creates a Virtual Machine (VM) in that zone with the desired configurations. The goal is to streamline the setup of a VM for running AI models that require GPU acceleration.

## General Logic

- Iterates through all zones and checks for GPU type availability.
- If available, attempt to create VM instance with pre-defined configurations - machine type, OS image, GPU type etc.
- If VM creation fails or if VM created with errors, clean up any instance created and continue to next zone.
- If VM created successfully, print the zone and instance name and exit the loop.

## Prerequisites

Before you can run this script, make sure you have the following:

- A Google Cloud project with billing enabled.
- The [Google Cloud SDK](https://cloud.google.com/sdk) installed and initialized.
- The Compute Engine API enabled for your project.
- Appropriate permissions to create and manage Compute Engine resources.
- Python 3.7 or higher installed.
- Access to Google Cloud Shell Editor (Accessible via Google Cloud Platform UI)

## Installation

1. Open `gcp_gpu_search.py` in Google Cloud Shell Editor (Accessible via Google Cloud Platform UI)
2. Install google-cloud-compute library in Google Cloud Editor environment 
```bash
pip3 install --upgrade google-cloud-compute
```

## Configuration
Edit the script (lines 219-225) to set the following configurations as required:
- project_id: Google Cloud project ID.
- instance_name: Desired name for the VM instance.
- machine_type: The machine type for the VM (e.g. n1-standard-1).
- image_project: The project that hosts the image (e.g. ml-images).
- image_family: The image family for the VM's OS disk (e.g. c1-deeplearning-tf-1-15-cu110-v20221107-debian-10).
- gpu_type: The type of GPU to attach to the VM (e.g. nvidia-tesla-p4).
- max_tries: The maximum number of zones to check for GPU availability.

## Usage
Run the script from the command line (Terminal in Editor):
```bash
python gcp_gpu_search.py
```
or click `Run` from Editor itself (Top-right corner)

Depending on availability of GPU in a particular zone and maximum number of tries specified, VM may or may not be created. If not created, try increasing maximum number of tries.

If VM is created successfully, SSH into the VM instance via command line (or Terminal in Cloud Editor):
```bash
gcloud compute ssh <instance_name> --zone <zone name> --project <project_id>
```
Once successfully logged into the VM, install nvidia driver (system will prompt automatically to do so).

Then run:
```bash
nvidia-smi
```
or
```bash
lspci | grep -i nvidia
```
This will confirm the successful installation of nvidia driver and GPU can be used for AI models.

Once done verifying VM instance, `exit` and run the following command in command line (or Terminal in Cloud Editor) to delete the instance and avoid any unnecessary costs:
```bash
gcloud compute instances delete <instance_name> --zone <zone name> --project <project_id>
```
