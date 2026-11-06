"""Seed a demo database with fictional leads so the dashboard has data to show.

All companies, people and domains are made up (`.example` domains).
Writes to `demo.db` by default and never touches your real `leads.db`.

Usage:
    python seed_demo.py              # create / refresh demo.db
    python api.py --demo             # serve the dashboard on demo.db
"""
import os
import random
import sys

DEMO_DB = sys.argv[1] if len(sys.argv) > 1 else "demo.db"

COMPANIES = [
    ("Lumenstack", "AI observability", "Seed", "EU"),
    ("Northwind Labs", "Dev tooling", "Series A", "US"),
    ("Parcelpoint", "Logistics API", "Seed", "India"),
    ("Quillmate", "AI writing for sales", "Pre-Seed", "UK"),
    ("Orbitly", "Product analytics", "Series A", "US"),
    ("Fernway", "Climate data", "Seed", "Germany"),
    ("Tessellate AI", "Vector search", "Series B", "US"),
    ("Kitebase", "Backend-as-a-service", "Seed", "Singapore"),
    ("Mosaic Health", "Clinical workflows", "Series A", "US"),
    ("Brightloop", "Customer onboarding", "Seed", "Canada"),
    ("Cartograph", "Geospatial AI", "Series A", "Netherlands"),
    ("Driftwell", "Support automation", "Pre-Seed", "Remote"),
    ("Helio Ledger", "Fintech infra", "Series A", "UK"),
    ("Juniper Ops", "Incident response", "Seed", "Israel"),
    ("Lattice Learn", "Edtech", "Seed", "India"),
    ("Meridian Voice", "Voice agents", "Series A", "US"),
    ("Nimbus Forms", "No-code forms", "Seed", "France"),
    ("Outpost CRM", "CRM for SMBs", "Series B", "Australia"),
    ("Pinecrest Data", "Data pipelines", "Seed", "US"),
    ("Relay Commerce", "Checkout APIs", "Series A", "Dubai"),
    ("Sable Security", "Cloud security", "Series A", "US"),
    ("Tidewater AI", "AI for ports", "Seed", "Japan"),
    ("Umbra Studio", "3D design tools", "Pre-Seed", "EU"),
    ("Vantage Hire", "Recruiting AI", "Seed", "India"),
    ("Willow Pay", "Payroll", "Series A", "Southeast Asia"),
    ("Xenial Docs", "Docs platform", "Seed", "Remote"),
    ("Yarrow Bio", "Lab automation", "Series A", "US"),
    ("Zephyr Edge", "Edge compute", "Seed", "Germany"),
    ("Aster Agents", "Agent platform", "Seed", "US"),
    ("Basalt Cloud", "GPU cloud", "Series B", "US"),
    ("Cinder Labs", "LLM evals", "Pre-Seed", "UK"),
    ("Dovetail Ops", "RevOps tooling", "Seed", "Canada"),
    ("Ember Robotics", "Warehouse robots", "Series A", "Japan"),
    ("Flint Analytics", "BI for startups", "Seed", "India"),
    ("Granite Legal", "Legal AI", "Series A", "US"),
    ("Harbor Health", "Telehealth", "Seed", "Australia"),
]

ROLES = [
    "Developer Advocate", "DevRel Engineer", "GTM Engineer",
    "Solutions Architect", "Technical Growth Engineer", "Founding GTM Lead",
]
SOURCES = [
    "Wellfound", "YC directory", "EU-Startups", "Inc42",
    "Himalayas", "Antler portfolio", "LinkedIn dork",
]
FIRST = ["Maya", "Arjun", "Lena", "Tom", "Priya", "Jonas", "Aisha", "Leo", "Sara", "Ravi"]
LAST = ["Chen", "Mehta", "Novak", "Reyes", "Iyer", "Berg", "Khan", "Rossi", "Okafor", "Das"]
TITLES = ["Founder & CEO", "Co-founder & CTO", "Head of Growth", "Head of People"]

# Funnel shape: how many leads end in each status.
PLAN = (
    ["new"] * 9 + ["rejected"] * 5 + ["needs_review"] * 2 + ["qualified"] * 6
    + ["enriched"] * 5 + ["drafted"] * 4 + ["sent"] * 3 + ["replied"] * 2
)


def score_for(status: str, rng: random.Random) -> int | None:
    if status == "new":
        return None
    if status == "rejected":
        return rng.randint(18, 49)
    if status == "needs_review":
        return rng.randint(50, 69)
    return rng.randint(70, 97)


def main() -> None:
    if os.path.abspath(DEMO_DB) == os.path.abspath("leads.db"):
        sys.exit("Refusing to seed demo data into leads.db. Pick another path.")

    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(DEMO_DB + suffix):
            os.remove(DEMO_DB + suffix)

    from db import get_conn, insert_lead, update_lead

    rng = random.Random(7)
    plan = PLAN[:]
    rng.shuffle(plan)
    conn = get_conn(DEMO_DB)
    try:
        for (company, niche, stage, region), status in zip(COMPANIES, plan):
            slug = company.lower().replace(" ", "")
            domain = f"{slug}.example"
            role = rng.choice(ROLES)
            insert_lead(
                conn,
                company,
                f"https://{domain}/careers/{role.lower().replace(' ', '-')}",
                rng.choice(SOURCES),
                role_title=role,
                company_domain=domain,
                funding_stage=stage,
                funding_info=f"Raised {stage} round ({niche})",
                region=region,
                employee_count=str(rng.choice([8, 14, 22, 35, 60, 120, 240])),
                posting_text=f"{company} builds {niche.lower()} and is hiring a {role}.",
                status="new",
            )
            lead_id = conn.execute(
                "SELECT id FROM leads WHERE company = ?", (company,)
            ).fetchone()["id"]

            score = score_for(status, rng)
            updates = {"status": status, "fit_score": score}
            if score is not None:
                updates["fit_reason"] = (
                    f"{stage} {niche.lower()} company in {region}; "
                    f"{role} role {'matches' if score >= 70 else 'is a weak match for'} the GTM/DevRel profile."
                )
            if status in ("enriched", "drafted", "sent", "replied"):
                first, last = rng.choice(FIRST), rng.choice(LAST)
                updates.update(
                    contact_name=f"{first} {last}",
                    contact_title=rng.choice(TITLES),
                    email=f"{first.lower()}@{domain}",
                    email_confidence=rng.choice(["verified", "verified", "pattern"]),
                    linkedin_url=f"https://www.linkedin.com/company/{slug}",
                )
            update_lead(conn, lead_id, **updates)
        total = conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]
    finally:
        conn.close()

    print(f"Seeded {total} fictional leads into {DEMO_DB}")
    print("Start the dashboard with:  python api.py --demo")


if __name__ == "__main__":
    main()
