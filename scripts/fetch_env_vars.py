import os
import shutil
import json
import subprocess

def fetch_env():
    print("==========================================================")
    print("   LearnItIn API - Cloud Run Environment Variables Sync   ")
    print("==========================================================")

    # Find gcloud executable or default to 'gcloud'
    gcloud_bin = shutil.which("gcloud") or "gcloud"
    
    service_name = "learnitin-api"
    region = "us-central1"
    
    print(f"Fetching environment variables for service '{service_name}' in region '{region}'...")
    
    # Construct the describe command to get the JSON service spec
    command = [
        gcloud_bin,
        "run",
        "services",
        "describe",
        service_name,
        "--region",
        region,
        "--format",
        "json"
    ]
    
    try:
        # Run gcloud command
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        service_data = json.loads(result.stdout)
        
        # Access the environment variables from the container specification
        try:
            containers = service_data['spec']['template']['spec']['containers']
            env_list = containers[0].get('env', [])
        except (KeyError, IndexError):
            print("\n❌ Error: Could not find container environment variables in the service definition.")
            return

        if not env_list:
            print(f"\n⚠️ Warning: No environment variables found on the Cloud Run service '{service_name}'.")
            return

        # Load existing .env values if it exists and has content
        env_path = ".env"
        existing_vars = {}
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        parts = line.split("=", 1)
                        k = parts[0].strip()
                        v = parts[1].strip().strip("'").strip('"')
                        existing_vars[k] = v

        # Merge Cloud Run variables with existing variables (giving precedence to Cloud Run values)
        updated_count = 0
        new_count = 0
        for item in env_list:
            name = item.get('name')
            value = item.get('value', '')
            if name:
                if name in existing_vars:
                    updated_count += 1
                else:
                    new_count += 1
                existing_vars[name] = value

        # Write merged variables back to .env
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("# Environment variables synced from Google Cloud Run\n")
            f.write(f"# Service: {service_name} | Region: {region}\n\n")
            for k, v in sorted(existing_vars.items()):
                # Wrap values with spaces, hash signs, or quotes in double quotes
                if any(c in v for c in (' ', '#', '"', "'")):
                    # Escape any double quotes in value
                    escaped_val = v.replace('"', '\\"')
                    f.write(f'{k}="{escaped_val}"\n')
                else:
                    f.write(f'{k}={v}\n')

        print(f"\n✅ Success! Successfully synced environment variables to '{env_path}'.")
        print(f"   - Added {new_count} new variables")
        print(f"   - Updated {updated_count} existing variables")
        print(f"   - Total variables now: {len(existing_vars)}")
        
    except subprocess.CalledProcessError as e:
        print("\n❌ Error running 'gcloud' command.")
        if e.stderr:
            print(e.stderr)
        else:
            print("Please ensure that you are authenticated and have access to the service.")
        print("\n💡 Troubleshooting Checklist:")
        print("1. Ensure Google Cloud CLI (gcloud) is installed on your system.")
        print("2. Run 'gcloud auth login' to authenticate in your terminal.")
        print("3. Run 'gcloud config set project YOUR_PROJECT_ID' to select your active project.")
        print(f"4. Verify that you have permissions to describe the Cloud Run service '{service_name}'.")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    fetch_env()
