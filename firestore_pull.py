#!/usr/bin/env python3
import argparse, subprocess, pathlib, json, sys, platform, os


parser = argparse.ArgumentParser()
parser.add_argument("--env", choices=["dev", "staging", "production"], help="Target environment")
args = parser.parse_args()

env = args.env or os.environ.get("ENV")
if env not in {"dev", "staging", "production"}:
    print("[!] You must specify param --env=dev|staging|production or set environment variable ENV=dev|staging|production")
    sys.exit(1)


GCLOUD_BIN = "gcloud.cmd" if platform.system() == "Windows" else "gcloud"

KEY_PATH = pathlib.Path(f"secrets/gcp-key-{env}.json")
OUT_DIR = pathlib.Path(__file__).parent / "firestore_schema"
OUT_DIR.mkdir(parents=True, exist_ok=True)

try:
    with open(KEY_PATH) as f:
        key_data = json.load(f)
        PROJECT_ID = key_data["project_id"]
        SERVICE_ACCOUNT = key_data["client_email"]
except Exception as e:
    print(f"[!] Failed to read {KEY_PATH}: {e}")
    sys.exit(1)


print(f"[~] Activating {SERVICE_ACCOUNT} for project {PROJECT_ID}")
subprocess.run([
    GCLOUD_BIN, "auth", "activate-service-account", SERVICE_ACCOUNT,
    f"--key-file={KEY_PATH}", f"--project={PROJECT_ID}"
], check=True)


def export(cmd, filename):
    print(f"[+] Exporting {filename}")
    with open(OUT_DIR / filename, "w", encoding="utf-8") as f:
        subprocess.run([GCLOUD_BIN] + cmd + ["--format=json", f"--project={PROJECT_ID}"], check=True, stdout=f)


export(["firestore", "indexes", "composite", "list"], "composite-indexes.json")
export(["firestore", "indexes", "fields", "list"], "field-indexes.json")
export(["firestore", "fields", "ttls", "list"], "ttl-policies.json")

print(f"\n✔️ Firestore schema exported to: {OUT_DIR.resolve()}")
