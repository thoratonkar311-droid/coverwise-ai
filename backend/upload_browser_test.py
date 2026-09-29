import urllib.request
import json
import os
import uuid

def post_multipart(url, file_path, headers={}):
    boundary = uuid.uuid4().hex
    filename = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    
    parts = []
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: application/pdf\r\n\r\n".encode("utf-8"))
    parts.append(file_bytes)
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)
    
    h = dict(headers)
    h["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    req = urllib.request.Request(url, data=body, headers=h)
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode("utf-8"))

def main():
    reg_req = urllib.request.Request(
        "http://127.0.0.1:8000/auth/register",
        data=json.dumps({
            "email": "gold_silver_tester@example.com",
            "password": "Password123!",
            "full_name": "Gold Silver Tester"
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(reg_req) as res:
            user_data = json.loads(res.read().decode())
            token = user_data["access_token"]
            print("Registered browser_user, token obtained")
    except Exception as e:
        login_req = urllib.request.Request(
            "http://127.0.0.1:8000/auth/login",
            data=json.dumps({
                "email": "browser_user@example.com",
                "password": "Password123!"
            }).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(login_req) as res:
            user_data = json.loads(res.read().decode())
            token = user_data["access_token"]
            print("Logged in browser_user, token obtained")

    auth_headers = {"Authorization": f"Bearer {token}"}

    print("Uploading Policy A...")
    res_a = post_multipart("http://127.0.0.1:8000/policies/upload", "test_policies/Policy_A_Gold.pdf", auth_headers)
    print("Policy A uploaded ID:", res_a["id"], "Plan:", res_a["plan_name"], "SI:", res_a["sum_insured"], "Active:", res_a["is_active"])

    print("Uploading Policy B...")
    res_b = post_multipart("http://127.0.0.1:8000/policies/upload", "test_policies/Policy_B_Silver.pdf", auth_headers)
    print("Policy B uploaded ID:", res_b["id"], "Plan:", res_b["plan_name"], "SI:", res_b["sum_insured"], "Active:", res_b["is_active"])

if __name__ == "__main__":
    main()
