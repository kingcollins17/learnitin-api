import os
import subprocess
import yaml
from dotenv import dotenv_values


def deploy():
    # Load environment variables from .env
    env_vars = dotenv_values(".env")

    # Filter out empty values and clean them
    filtered_vars = {}
    for key, value in env_vars.items():
        if value is not None and value != "":
            # Remove any existing quotes from the value
            clean_value = value.strip("'").strip('"')
            filtered_vars[key] = clean_value

    # Write to a temporary yaml file
    env_file_path = "env_vars.yaml"
    with open(env_file_path, "w") as f:
        yaml.dump(filtered_vars, f, default_flow_style=False)

    # Construct the gcloud command
    command = [
        "/Users/zidepeople/google-cloud-sdk/google-cloud-sdk/bin/gcloud",
        "run",
        "deploy",
        "learnitin-api",
        "--source",
        ".",
        "--region",
        "us-central1",
        "--platform",
        "managed",
        "--allow-unauthenticated",
        f"--env-vars-file={env_file_path}",
        "--port",
        "8080",
    ]

    print("Executing deployment command...")
    try:
        subprocess.run(command, check=True)
        print("\nDeployment successful!")
    except subprocess.CalledProcessError as e:
        print(f"\nDeployment failed with exit code: {e.returncode}")
    finally:
        # Optionally remove the temp file
        if os.path.exists(env_file_path):
            os.remove(env_file_path)


if __name__ == "__main__":
    deploy()
