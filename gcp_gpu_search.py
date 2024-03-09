from google.cloud import compute_v1
from google.api_core.exceptions import GoogleAPICallError
import time

def create_vm_instance(compute_client, project_id, zone, instance_name, machine_type, image_project, image_family, gpu_type):
    """
    Creates a Virtual Machine instance with specified configurations including a GPU.

    Parameters:
    - compute_client: The Compute Engine client instance.
    - project_id: The Google Cloud project ID.
    - zone: The name of the zone to create the VM instance in.
    - instance_name: The name of the VM instance.
    - machine_type: The machine type of the VM.
    - image_project: The project that hosts the image family.
    - image_family: The image family for the VM's OS disk.
    - gpu_type: The type of GPU to attach to the VM.

    Returns:
    The operation object for the instance creation.
    """

    # Configure source disk image
    source_disk_image = f"projects/{image_project}/global/images/{image_family}"

    # Configure the machine type
    machine_type = f"zones/{zone}/machineTypes/{machine_type}"

    # Configure the disk
    disk = compute_v1.AttachedDisk()
    disk.initialize_params.source_image = source_disk_image
    disk.initialize_params.disk_size_gb = 100
    disk.auto_delete = True
    disk.boot = True

    # Configure the network interface and access
    access_config = compute_v1.AccessConfig()
    access_config.name = "External NAT"
    access_config.type = "ONE_TO_ONE_NAT"
    access_config.network_tier = "STANDARD"
    network_interface = compute_v1.NetworkInterface()
    network_interface.network = "global/networks/default"
    network_interface.access_configs = [access_config]

    # Configure the GPU
    guest_accelerator = compute_v1.AcceleratorConfig()
    guest_accelerator.accelerator_count = 1
    guest_accelerator.accelerator_type = f"zones/{zone}/acceleratorTypes/{gpu_type}"

    # Configure the instance
    instance = compute_v1.Instance()
    instance.name = instance_name
    instance.machine_type = machine_type
    instance.disks = [disk]
    instance.network_interfaces = [network_interface]
    instance.guest_accelerators = [guest_accelerator]
    instance.scheduling = compute_v1.Scheduling()
    instance.scheduling.on_host_maintenance = "TERMINATE"
    instance.scheduling.automatic_restart = True

    # Create the instance
    operation = compute_client.insert(project=project_id, zone=zone, instance_resource=instance)

    return operation

def is_gpu_available(compute_client, accelerator_client, project_id, zone, gpu_type):
    """
    Checks if the specified GPU type is available in the given zone.

    Parameters:
    - compute_client: The Compute Engine client instance.
    - accelerator_client: The Compute Engine accelerator client instance.
    - project_id: The Google Cloud project ID.
    - zone: The name of the zone to check GPU availability in.
    - gpu_type: The type of GPU to check for.

    Returns:
    True if the GPU type is available, False otherwise.
    """

    accelerator_types = accelerator_client.list(project=project_id, zone=zone)

    for accelerator_type in accelerator_types:
        if gpu_type in accelerator_type.name:
            return True
    return False

def wait_for_operation(operation, project_id, zone):
    """
    Waits for the provided operation to complete.

    Parameters:
    - operation: The operation to wait for.
    - project_id: The Google Cloud project ID.
    - zone: The name of the zone of the operation.

    Returns:
    The result of the operation once it's done.
    """

    operations_client = compute_v1.ZoneOperationsClient()

    while True:
        result = operations_client.get(project=project_id, zone=zone, operation=operation.name)
        if result.status == compute_v1.Operation.Status.DONE:
            if 'error' in result:
                raise GoogleAPICallError(result.error.errors[0].code)
            return result
        time.sleep(5)

def instance_exists(compute_client, project_id, zone, instance_name):
    """
    Checks if the specified instance exists.

    Parameters:
    - compute_client: The Compute Engine client instance.
    - project_id: The Google Cloud project ID.
    - zone: The name of the zone to check the instance in.
    - instance_name: The name of the instance to check.

    Returns:
    True if the instance exists, False otherwise.
    """
    
    try:
        compute_client.get(project=project_id, zone=zone, instance=instance_name)
        return True  
    except GoogleAPICallError:
        return False

def delete_instance(compute_client, project_id, zone, instance_name):
    """
    Deletes the specified Compute Engine instance.

    Parameters:
    - compute_client: The Compute Engine client instance.
    - project_id: The Google Cloud project ID.
    - zone: The name of the zone of the instance to delete.
    - instance_name: The name of the instance to delete.

    Returns:
    None
    """

    try:
        operation = compute_client.delete(project=project_id, zone=zone, instance=instance_name)
        wait_for_operation(operation, project_id, zone)
        print(f"Deleted VM instance {instance_name}.\n")
    except GoogleAPICallError as e:
        print(f"Failed to delete VM instance {instance_name} due to: {e}\n")

def find_gpu_zone_and_create_vm(project_id, instance_name, machine_type, image_family, image_project, gpu_type, max_tries):
    """
    Finds an available zone with the specified GPU type and creates a VM instance there.

    Parameters:
    - project_id: The Google Cloud project ID.
    - instance_name: The name for the new VM instance.
    - machine_type: The machine type for the new VM.
    - image_family: The image family for the VM's OS disk.
    - image_project: The project that hosts the image.
    - gpu_type: The type of GPU to attach to the VM.
    - max_tries: The maximum number of zones to check for GPU availability.

    Returns:
    The zone name and instance name if creation was successful, None otherwise.
    """

    # create required clients
    compute_client = compute_v1.InstancesClient()
    accelerator_client = compute_v1.AcceleratorTypesClient()

    # List available zones
    zones_client = compute_v1.ZonesClient()
    request = compute_v1.ListZonesRequest(project=project_id)
    zones = zones_client.list(request)

    # loop through zones, check for GPU availability and attempt to create VM
    count = 0
    for zone in zones:
        # keep track of number of attempts
        count += 1
        if count > max_tries:
            print(f"Maximum number of tries ({max_tries}) reached.")
            return None, None

        print(f"Checking GPU availability in {zone.name}...\n")

        # check if GPU available in the zone before attempting to create VM
        if not is_gpu_available(compute_client, accelerator_client, project_id, zone.name, gpu_type):
            print(f"GPU {gpu_type} not available in {zone.name}.\n")
            continue

        print(f"GPU {gpu_type} is available in {zone.name}. Trying to create VM...\n")

        try:
            # Attempt to create VM
            operation = create_vm_instance(
                compute_client, project_id, zone.name, instance_name, machine_type, image_project, image_family, gpu_type
            )
            print("Waiting for the operation to finish...\n")
            wait_for_operation(operation, project_id, zone.name)
            print(f"Successfully created VM\n")
            return zone.name, instance_name
        except GoogleAPICallError as e:
            # Handle failure to create VM
            print(f"Failed to create VM in {zone.name} due to: {e}\n")

            # Clean up any instance created with errors
            if instance_exists(compute_client, project_id, zone.name, instance_name):
                delete_instance(compute_client, project_id, zone.name, instance_name)

            continue

    return None, None

if __name__ == "__main__":
    # input variables
    project_id = 'core-verbena-328218'
    instance_name = "ks6964-vm-test"
    machine_type = "n1-standard-1"
    image_project = "ml-images"
    image_family = "c1-deeplearning-tf-1-15-cu110-v20221107-debian-10"
    gpu_type = "nvidia-tesla-p4"
    max_tries = 20

    # find available zone and create VM with specified GPU
    zone, created_instance_name = find_gpu_zone_and_create_vm(project_id, instance_name, machine_type, image_family, image_project, gpu_type, max_tries)

    # print result
    if zone:
        print(f"VM -> '{created_instance_name}' created successfully in zone -> '{zone}' under project -> '{project_id}'\n")
    else:
        print("Failed to create a VM with the specified configuration.\n")
