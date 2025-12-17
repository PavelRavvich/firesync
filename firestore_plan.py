#!/usr/bin/env python3
import argparse, json, os, pathlib, platform, subprocess, sys
from collections import defaultdict

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

# Activate service account and set project
auth_cmd = [
    GCLOUD, "auth", "activate-service-account", service_account,
    f"--key-file={key_path}",
    f"--project={project_id}"
]
auth_result = subprocess.run(auth_cmd, capture_output=True, text=True)
if auth_result.returncode != 0:
    print(f"[!] Failed to activate service account: {auth_result.stderr.strip()}")
    sys.exit(1)

SCHEMA_DIR = (pathlib.Path(__file__).parent / args.schema_dir).resolve()


def get_gcloud_json(cmd):
    full_cmd = [GCLOUD] + cmd + ["--format=json", "--project", project_id]
    result = subprocess.run(full_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[!] gcloud error: {result.stderr.strip()}")
        sys.exit(1)
    return json.loads(result.stdout)


def normalize_fields(fields):
    return sorted(f"{f['fieldPath']}:{f.get('order', f.get('arrayConfig', '')).lower()}" for f in fields)


print("\n🔍 Comparing Composite Indexes")
try:
    remote = get_gcloud_json(["firestore", "indexes", "composite", "list"])
    remote_set = set()
    for r in remote:
        coll = r.get("collectionGroup")
        if not coll and "name" in r:
            parts = r["name"].split("/collectionGroups/")
            if len(parts) > 1:
                coll = parts[1].split("/")[0]
        remote_set.add((
            coll,
            r.get("queryScope", "COLLECTION"),
            tuple(normalize_fields(r.get("fields", [])))
        ))

    local_path = SCHEMA_DIR / "composite-indexes.json"
    local = json.loads(local_path.read_text(encoding="utf-8"))
    local_set = set()
    for i in local:
        coll = i.get("collectionGroupId") or i.get("collectionGroup")
        if not coll and "name" in i:
            parts = i["name"].split("/collectionGroups/")
            if len(parts) > 1:
                coll = parts[1].split("/")[0]
        local_set.add((
            coll,
            i.get("queryScope", "COLLECTION"),
            tuple(normalize_fields(i.get("fields", [])))
        ))

    for item in local_set - remote_set:
        print(f"[+] WILL CREATE: {item[0]} {item[1]} {' | '.join(item[2])}")
    for item in remote_set - local_set:
        print(f"[-] WILL DELETE: {item[0]} {item[1]} {' | '.join(item[2])}")
except Exception as e:
    print(f"[!] Composite compare failed: {e}")

print("\n🔍 Comparing Single-Field Indexes")
try:
    remote = get_gcloud_json(["firestore", "indexes", "fields", "list"])
    remote_map = defaultdict(set)
    for f in remote:
        if "/fields/" not in f.get("name", ""):
            continue
        coll = f.get("collectionGroup")
        if not coll:
            parts = f["name"].split("/collectionGroups/")
            if len(parts) > 1:
                coll = parts[1].split("/")[0]
        path_field = f.get("fieldPath")
        for idx in f.get("indexes", []):
            val = idx.get("order") or idx.get("arrayConfig")
            if val:
                remote_map[(coll, path_field)].add(val.lower())

    path = SCHEMA_DIR / "field-indexes.json"
    local = json.loads(path.read_text(encoding="utf-8"))
    local_map = defaultdict(set)
    for i in local:
        coll = i.get("collectionGroupId")
        path_field = i.get("fieldPath")
        for idx in i.get("indexes", []):
            val = idx.get("order") or idx.get("arrayConfig")
            if val:
                local_map[(coll, path_field)].add(val.lower())

    for key in local_map.keys() - remote_map.keys():
        for val in local_map[key]:
            print(f"[+] WILL CREATE FIELD INDEX: {key} => {val}")
    for key in remote_map.keys() - local_map.keys():
        for val in remote_map[key]:
            print(f"[-] WILL DELETE FIELD INDEX: {key} => {val}")
    for key in local_map.keys() & remote_map.keys():
        add = local_map[key] - remote_map[key]
        delete = remote_map[key] - local_map[key]
        for val in add:
            print(f"[+] WILL CREATE FIELD INDEX: {key} => {val}")
        for val in delete:
            print(f"[-] WILL DELETE FIELD INDEX: {key} => {val}")
except Exception as e:
    print(f"[!] Single-field compare failed: {e}")


print("\n🔍 Comparing TTL Policies")
try:
    remote = get_gcloud_json(["firestore", "fields", "ttls", "list"])
    remote_set = {}
    for f in remote:
        coll = f.get("collectionGroup")
        if not coll and "name" in f:
            parts = f["name"].split("/collectionGroups/")
            if len(parts) > 1:
                coll = parts[1].split("/")[0]
        field = f.get("field")
        if not field and "name" in f:
            field = f["name"].split("/fields/")[-1]
        remote_set[(coll, field)] = f.get("ttlPeriod", "")

    path = SCHEMA_DIR / "ttl-policies.json"
    local = json.loads(path.read_text(encoding="utf-8"))
    local_set = {}
    for i in local:
        coll = i.get("collectionGroupId") or i.get("collectionGroup")
        if not coll and "name" in i:
            parts = i["name"].split("/collectionGroups/")
            if len(parts) > 1:
                coll = parts[1].split("/")[0]
        field = i.get("field")
        if not field and "name" in i:
            field = i["name"].split("/fields/")[-1]
        local_set[(coll, field)] = i.get("ttlConfig", {}).get("ttlPeriod", "")

    for key in local_set.keys() - remote_set.keys():
        print(f"[+] WILL CREATE TTL: {key} => {local_set[key]}")
    for key in remote_set.keys() - local_set.keys():
        print(f"[-] WILL DELETE TTL: {key} => {remote_set[key]}")
    for key in local_set.keys() & remote_set.keys():
        if local_set[key] != remote_set[key]:
            print(f"[~] WILL UPDATE TTL: {key} {remote_set[key]} -> {local_set[key]}")
except Exception as e:
    print(f"[!] TTL compare failed: {e}")

print("\n✔️ Plan complete.")
