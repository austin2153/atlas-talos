import kratix_sdk as ks
import os


def main():
    sdk = ks.KratixSDK()
    resource = sdk.read_resource_input()

    name = resource.get_name()
    namespace = resource.get_namespace()
    cores = resource.get_value("spec.cores")
    memory = resource.get_value("spec.memory")

    api_token = os.environ.get("PROXMOX_API_TOKEN")
    if not api_token:
        raise RuntimeError("PROXMOX_API_TOKEN environment variable not set")

    print(f"Creating VM: name={name} cores={cores} memory={memory}")


if __name__ == "__main__":
    main()