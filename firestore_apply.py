#!/usr/bin/env python3
import argparse, json, os, pathlib, platform, subprocess, sys

GCLOUD = "gcloud.cmd" if platform.system() == "Windows" else "gcloud"

parser = argparse.ArgumentParser()
parser.add_argument("--env", choices=["dev", "staging", "production"], help="Target environment")
parser.add_argument("--schema-dir", default="firestore_schema", help="Directory with schema JSON files")
args = parser.parse_args()

env = args.env or os.getenv("ENV")
if not env:
    print("[!] Please provide --env flag or set ENV environment variable.")
    sys.exit(1)

key_path = pathlib.Path(f"secrets/gcp-key-{env}.json")
if not key_path.exists():
    print(f"[!] Key file not found: {key_path}")
    sys.exit(1)

try:
    key_data = json.loads(key_path.read_text(encoding="utf-8"))
    project_id = key_data["project_id"]
    service_account = key_data["client_email"]
except Exception as e:
    print(f"[!] Failed to parse key file: {e}")
    sys.exit(1)

print(f"[~] Environment: {env}")
print(f"[~] Project: {project_id}")

subprocess.run([
    GCLOUD, "auth", "activate-service-account", service_account,
    f"--key-file={key_path}", f"--project={project_id}"
], check=True)

SCHEMA_DIR = (pathlib.Path(__file__).parent / args.schema_dir).resolve()


def run_gcloud(cmd_list):
    full_cmd = [GCLOUD] + cmd_list + ["--quiet", "--project", project_id]
    print(f"[~] {' '.join(full_cmd)}")
    result = subprocess.run(full_cmd, capture_output=True, text=True)
    stderr = result.stderr.strip().lower()
    if result.returncode != 0:
        if "already exists" in stderr or "already_exists" in stderr:
            print(f"[~] Skipped (already exists): {stderr}")
        elif "permission denied" in stderr or "permission" in stderr:
            print(f"[!] Permission denied: {stderr}")
        else:
            print(f"[!] Failed: {stderr}")
    else:
        print("[+] Success")


print("\n🔹 Applying Composite Indexes")
try:
    path = SCHEMA_DIR / "composite-indexes.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Expected a list in composite-indexes.json")

    for idx in data:
        coll = idx.get("collectionGroupId") or idx.get("collectionGroup")
        if not coll and "name" in idx:
            parts = idx["name"].split("/collectionGroups/")
            if len(parts) > 1:
                coll = parts[1].split("/")[0]

        scope = idx.get("queryScope", "COLLECTION")
        fields = idx.get("fields", [])
        if not coll or not fields:
            print(f"[!] Skipping invalid composite index: {idx}")
            continue

        cmd = [
            "firestore", "indexes", "composite", "create",
            f"--collection-group={coll}",
            f"--query-scope={scope}"
        ]
        for f in fields:
            if "fieldPath" in f and ("order" in f or "arrayConfig" in f):
                kv = f"field-path={f['fieldPath']}"
                if "order" in f:
                    kv += f",order={f['order'].lower()}"
                elif "arrayConfig" in f:
                    kv += f",array-config={f['arrayConfig'].lower()}"
                cmd.append(f"--field-config={kv}")
        run_gcloud(cmd)
except Exception as e:
    print(f"[!] Error applying composite indexes: {e}")

print("\n🔹 Applying Single-Field Indexes")
try:
    path = SCHEMA_DIR / "field-indexes.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Expected a list in field-indexes.json")

    for entry in data:
        coll = entry.get("collectionGroupId")
        path_field = entry.get("fieldPath")
        idx_cfg = entry.get("indexes", [])
        for cfg in idx_cfg:
            val = cfg.get("order") or cfg.get("arrayConfig")
            if not val:
                continue
            prefix = "order=" if "order" in cfg else "array-config="
            run_gcloud([
                "firestore", "indexes", "fields", "update",
                path_field,
                f"--collection-group={coll}",
                f"--index={prefix}{val.lower()}"
            ])
except Exception as e:
    print(f"[!] Error applying single-field indexes: {e}")

print("\n🔹 Applying TTL Policies")
try:
    path = SCHEMA_DIR / "ttl-policies.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Expected a list in ttl-policies.json")

    for row in data:
        coll = row.get("collectionGroupId") or row.get("collectionGroup")
        if not coll and "name" in row:
            parts = row["name"].split("/collectionGroups/")
            if len(parts) > 1:
                coll = parts[1].split("/")[0]

        field = row.get("field") or row.get("name").split("/fields/")[-1]
        ttl_state = row.get("ttlConfig", {}).get("state")
        if not (coll and field and ttl_state):
            continue

        cmd = [
            "firestore", "fields", "ttls", "update",
            field,
            f"--collection-group={coll}",
            "--enable-ttl" if ttl_state.upper() == "ACTIVE" else "--disable-ttl"
        ]
        run_gcloud(cmd)
except Exception as e:
    print(f"[!] Error applying TTL: {e}")

print("\n✔️ Firestore schema applied.")
