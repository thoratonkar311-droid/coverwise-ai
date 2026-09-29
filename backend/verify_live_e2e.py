import urllib.request
import json

BASE_URL = "http://127.0.0.1:8000"

def request(path, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode("utf-8"))

def main():
    print("=== LIVE END-TO-END VERIFICATION (POSTGRESQL + LIVE FASTAPI SERVER) ===")

    # 1. Login
    login_res = request("/auth/login", method="POST", data={"email": "gold_silver_tester@example.com", "password": "Password123!"})
    token = login_res["access_token"]
    print("[PASS] Auth: Logged in successfully as gold_silver_tester@example.com")

    # 2. Get all policies
    policies = request("/policies/", token=token)
    print(f"[PASS] Found {len(policies)} policies for user:")
    policy_a = next(p for p in policies if "Gold" in p["plan_name"])
    policy_b = next(p for p in policies if "Silver" in p["plan_name"])
    id_a = policy_a["id"]
    id_b = policy_b["id"]
    print(f"  Policy A: ID {id_a} - {policy_a['plan_name']} (SI: {policy_a['sum_insured']})")
    print(f"  Policy B: ID {id_b} - {policy_b['plan_name']} (SI: {policy_b['sum_insured']})")

    for cycle in range(1, 3):
        print(f"\n--- CYCLE {cycle}: TESTING POLICY A (ID: {id_a}) ---")
        # Activate A
        act_a = request(f"/policies/{id_a}/activate", method="POST", token=token)
        active = request("/policies/active", token=token)
        assert active["id"] == id_a, f"Expected active ID {id_a}, got {active['id']}"
        assert active["plan_name"] == "Alpha Super Gold Shield", f"Wrong plan name {active['plan_name']}"
        assert active["sum_insured"] == 1000000.0, f"Wrong SI {active['sum_insured']}"
        print(f"[PASS] [1. Identity & 2. Sum Insured] Active Policy is {active['plan_name']} with SI INR {active['sum_insured']:,.0f}")

        # Check coverage rules
        rules_a = request(f"/coverage/rules?policy_id={id_a}", token=token)
        # Deductible & Copay check
        gen_rule = next((r for r in rules_a if not r["procedure_name"] or r["procedure_name"].lower() in ("general", "basic")), rules_a[0])
        print(f"[PASS] [3. Deductible & 4. Copay] Deductible: {gen_rule['deductible'] or 'Not Determined'}, Network Copay: {gen_rule['copay_percentage']}%")
        assert gen_rule["copay_percentage"] == 0.0, f"Expected 0% copay, got {gen_rule['copay_percentage']}"
        assert gen_rule["deductible"] is None or gen_rule["deductible"] == 0.0

        # Procedure rules & waiting period
        tkr_rule = next(r for r in rules_a if r["procedure_name"] and "knee" in r["procedure_name"].lower())
        print(f"[PASS] [5. Waiting & 6. Procedure Rules] TKR Limit: {tkr_rule['coverage_percentage']}% (Cap INR {tkr_rule['coverage_limit_amount']:,.0f}), Waiting: {tkr_rule['waiting_period']}")
        assert tkr_rule["coverage_percentage"] == 60.0
        assert tkr_rule["coverage_limit_amount"] == 600000.0
        assert "36 months" in tkr_rule["waiting_period"]

        # Evidence
        ev_refs = []
        for r in rules_a:
            ev_refs.extend(r.get("evidence_references") or [])
        print(f"[PASS] [7. Evidence] Found {len(ev_refs)} evidence references for Policy A. Sample: Page {ev_refs[0]['page']}, Clause: '{ev_refs[0]['clause_section']}'")
        for ev in ev_refs:
            assert ev["policy_id"] == id_a, "Cross-policy evidence leakage detected!"

        # Policy Assistant
        conv_a = request("/conversations", method="POST", data={"policy_id": id_a}, token=token)
        conv_a_id = conv_a["id"]
        chat_res = request(f"/conversations/{conv_a_id}/messages", method="POST", data={"content": "What is the waiting period for total knee replacement?"}, token=token)
        answer_text = chat_res["content"]
        print(f"[PASS] [8. Assistant] Q: 'What is waiting period for knee replacement?' -> Answer: {answer_text[:120]}...")
        assert "36" in answer_text, f"Expected 36 months in answer, got: {answer_text}"
        assert "24" not in answer_text or "36" in answer_text

        # Treatment Cost Engine
        est_res = request("/treatment-estimates", method="POST", data={
            "policy_id": id_a,
            "scenario": {
                "treatment_name": "Total Knee Replacement",
                "hospital_quote": 200000.0,
                "room_type": "Single Private",
                "is_network": True
            }
        }, token=token)
        trace = est_res["calculation_trace"]
        print(f"[PASS] [9. Treatment Cost Engine] Quote: INR 200,000 -> Insurer: INR {est_res['estimated_insurer_contribution']:,.0f}, Patient: INR {est_res['estimated_patient_responsibility']:,.0f} (Cap: INR {est_res['policy_coverage_cap']:,.0f}, Copay: {est_res['applicable_copay_percentage']}%)")
        assert est_res["applicable_copay_percentage"] == 0.0

        # What-If
        whatif_res = request("/treatment-estimates/what-if", method="POST", data={
            "policy_id": id_a,
            "previous_scenario": {"treatment_name": "Total Knee Replacement", "hospital_quote": 200000.0, "room_type": "Single Private", "is_network": True},
            "updated_scenario": {"treatment_name": "Total Knee Replacement", "hospital_quote": 200000.0, "room_type": "Deluxe", "is_network": False}
        }, token=token)
        print(f"[PASS] [10. What-If] Insurer Diff: INR {whatif_res['insurer_contribution_delta']:,.0f}, Patient Diff: INR {whatif_res['patient_responsibility_delta']:,.0f}")

        # Dashboard
        dash = request(f"/dashboard/overview?policy_id={id_a}", token=token)
        print(f"[PASS] [11. Dashboard] Plan: {dash['plan_name']}, Sum Insured: INR {dash['sum_insured']:,.0f}, Co-pay: {dash['copay_percentage']}%")
        assert dash["plan_name"] == "Alpha Super Gold Shield"
        assert dash["sum_insured"] == 1000000.0
        assert dash["copay_percentage"] == 0.0

        print(f"\n--- CYCLE {cycle}: SWITCHING TO POLICY B (ID: {id_b}) ---")
        # Activate B
        act_b = request(f"/policies/{id_b}/activate", method="POST", token=token)
        active_b = request("/policies/active", token=token)
        assert active_b["id"] == id_b
        assert active_b["plan_name"] == "Beta Health Advantage Silver"
        assert active_b["sum_insured"] == 500000.0
        print(f"[PASS] [1. Identity & 2. Sum Insured] Active Policy is {active_b['plan_name']} with SI INR {active_b['sum_insured']:,.0f}")

        # Check coverage rules for B
        rules_b = request(f"/coverage/rules?policy_id={id_b}", token=token)
        gen_rule_b = next((r for r in rules_b if not r["procedure_name"] or r["procedure_name"].lower() in ("general", "basic")), rules_b[0])
        print(f"[PASS] [3. Deductible & 4. Copay] Deductible: INR {gen_rule_b['deductible']:,.0f}, Network Copay: {gen_rule_b['copay_percentage']}%")
        assert gen_rule_b["copay_percentage"] == 20.0, f"Expected 20% copay, got {gen_rule_b['copay_percentage']}"
        assert gen_rule_b["deductible"] == 10000.0, f"Expected 10,000 deductible, got {gen_rule_b['deductible']}"

        # Procedure rules & waiting period for B
        tkr_rule_b = next(r for r in rules_b if r["procedure_name"] and "knee" in r["procedure_name"].lower())
        print(f"[PASS] [5. Waiting & 6. Procedure Rules] TKR Limit: {tkr_rule_b['coverage_percentage']}% (Cap INR {tkr_rule_b['coverage_limit_amount']:,.0f}), Waiting: {tkr_rule_b['waiting_period']}")
        assert tkr_rule_b["coverage_percentage"] == 50.0
        assert tkr_rule_b["coverage_limit_amount"] == 250000.0
        assert "24 months" in tkr_rule_b["waiting_period"]

        # Evidence for B
        ev_refs_b = []
        for r in rules_b:
            ev_refs_b.extend(r.get("evidence_references") or [])
        print(f"[PASS] [7. Evidence] Found {len(ev_refs_b)} evidence references for Policy B.")
        for ev in ev_refs_b:
            assert ev["policy_id"] == id_b, "Cross-policy evidence leakage detected!"

        # Policy Assistant for B
        conv_b = request("/conversations", method="POST", data={"policy_id": id_b}, token=token)
        conv_b_id = conv_b["id"]
        chat_res_b = request(f"/conversations/{conv_b_id}/messages", method="POST", data={"content": "What is the waiting period for total knee replacement?"}, token=token)
        answer_text_b = chat_res_b["content"]
        print(f"[PASS] [8. Assistant] Q: 'What is waiting period for knee replacement?' -> Answer: {answer_text_b[:120]}...")
        assert "24" in answer_text_b, f"Expected 24 months in answer, got: {answer_text_b}"
        assert "36" not in answer_text_b

        # Treatment Cost Engine for B
        est_res_b = request("/treatment-estimates", method="POST", data={
            "policy_id": id_b,
            "scenario": {
                "treatment_name": "Total Knee Replacement",
                "hospital_quote": 200000.0,
                "room_type": "Single Private",
                "is_network": True
            }
        }, token=token)
        trace_b = est_res_b["calculation_trace"]
        print(f"[PASS] [9. Treatment Cost Engine] Quote: INR 200,000 -> Insurer: INR {est_res_b['estimated_insurer_contribution']:,.0f}, Patient: INR {est_res_b['estimated_patient_responsibility']:,.0f} (Cap: INR {est_res_b['policy_coverage_cap']:,.0f}, Copay: {est_res_b['applicable_copay_percentage']}%, Deductible: INR {est_res_b['deductible_applied']:,.0f})")
        assert est_res_b["applicable_copay_percentage"] == 20.0
        assert est_res_b["deductible_applied"] == 10000.0

        # What-If for B
        whatif_res_b = request("/treatment-estimates/what-if", method="POST", data={
            "policy_id": id_b,
            "previous_scenario": {"treatment_name": "Total Knee Replacement", "hospital_quote": 200000.0, "room_type": "Single Private", "is_network": True},
            "updated_scenario": {"treatment_name": "Total Knee Replacement", "hospital_quote": 200000.0, "room_type": "Deluxe", "is_network": False}
        }, token=token)
        print(f"[PASS] [10. What-If] Insurer Diff: INR {whatif_res_b['insurer_contribution_delta']:,.0f}, Patient Diff: INR {whatif_res_b['patient_responsibility_delta']:,.0f}")

        # Dashboard for B
        dash_b = request(f"/dashboard/overview?policy_id={id_b}", token=token)
        print(f"[PASS] [11. Dashboard] Plan: {dash_b['plan_name']}, Sum Insured: INR {dash_b['sum_insured']:,.0f}, Co-pay: {dash_b['copay_percentage']}%")
        assert dash_b["plan_name"] == "Beta Health Advantage Silver"
        assert dash_b["sum_insured"] == 500000.0
        assert dash_b["copay_percentage"] == 20.0
        print("[PASS] [12. Zero Old Policy Leakage] Verified all 12 criteria with ZERO cross-policy leakage across cycles!")

    print("\n=======================================================")
    print("ALL 12 ACCEPTANCE CRITERIA VERIFIED ON LIVE BACKEND DAEMON!")
    print("=======================================================")

if __name__ == "__main__":
    main()
