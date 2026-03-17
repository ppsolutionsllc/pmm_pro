import asyncio
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import make_url


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    pytest.skip("Smoke API tests require TEST_DATABASE_URL (postgresql+...)", allow_module_level=True)
if not str(TEST_DATABASE_URL).startswith("postgresql"):
    pytest.skip("Smoke API tests are PostgreSQL-only", allow_module_level=True)
try:
    db_name = (make_url(TEST_DATABASE_URL).database or "").lower()
except Exception:
    db_name = ""
if "test" not in db_name:
    pytest.skip(
        "Refusing to run destructive smoke tests on non-test DB. Use TEST_DATABASE_URL with *_test DB name.",
        allow_module_level=True,
    )
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["JWT_SECRET"] = "super-secret-jwt-key-with-at-least-32-chars"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["SQL_ECHO"] = "false"

from app import models  # noqa: E402
from app.crud import user as crud_user  # noqa: E402
from app.db.session import async_session, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import RoleEnum as UserRoleEnum, User  # noqa: E402
from app.schemas import user as schema_user  # noqa: E402


async def _reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.drop_all)
        await conn.run_sync(models.Base.metadata.create_all)


async def _bootstrap_first_admin():
    async with async_session() as session:
        exists = (await session.execute(select(User.id).where(User.role == UserRoleEnum.ADMIN))).first()
        if exists:
            return
        await crud_user.create_user(
            session,
            schema_user.UserCreate(
                login="admin",
                password="AdminPass_123",
                full_name="Administrator",
                role=schema_user.RoleEnum.ADMIN,
                is_active=True,
                department_id=None,
            ),
        )


@pytest.fixture()
def client():
    asyncio.run(_reset_db())
    asyncio.run(_bootstrap_first_admin())
    with TestClient(app) as c:
        yield c


def _auth_headers(client: TestClient, login: str, password: str) -> dict[str, str]:
    res = client.post(
        "/api/v1/token",
        data={"username": login, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_department(client: TestClient, headers: dict[str, str], name: str) -> int:
    res = client.post("/api/v1/departments", json={"name": name, "is_active": True}, headers=headers)
    assert res.status_code == 200, res.text
    return int(res.json()["id"])


def _create_user(
    client: TestClient,
    headers: dict[str, str],
    *,
    login: str,
    password: str,
    role: str,
    department_id: int | None,
) -> int:
    payload = {
        "login": login,
        "password": password,
        "full_name": login,
        "phone": "+380000000000",
        "rank": None,
        "position": None,
        "is_active": True,
        "role": role,
        "department_id": department_id,
    }
    res = client.post("/api/v1/users", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    return int(res.json()["id"])


def test_departments_get_by_id_and_access_rules(client: TestClient):
    admin = _auth_headers(client, "admin", "AdminPass_123")

    dept_1 = _create_department(client, admin, "Dept 1")
    dept_2 = _create_department(client, admin, "Dept 2")

    res_admin = client.get(f"/api/v1/departments/{dept_1}", headers=admin)
    assert res_admin.status_code == 200
    assert res_admin.json()["id"] == dept_1

    _create_user(
        client,
        admin,
        login="dept_user_1",
        password="DeptPass_123",
        role="DEPT_USER",
        department_id=dept_1,
    )
    dept_headers = _auth_headers(client, "dept_user_1", "DeptPass_123")

    own = client.get(f"/api/v1/departments/{dept_1}", headers=dept_headers)
    assert own.status_code == 200

    foreign = client.get(f"/api/v1/departments/{dept_2}", headers=dept_headers)
    assert foreign.status_code == 403


def test_request_flow_to_posted_and_backup_endpoint(client: TestClient):
    admin = _auth_headers(client, "admin", "AdminPass_123")
    dept_id = _create_department(client, admin, "Training Dept")

    _create_user(
        client,
        admin,
        login="dept_user_flow",
        password="DeptFlow_123",
        role="DEPT_USER",
        department_id=dept_id,
    )
    _create_user(
        client,
        admin,
        login="operator_flow",
        password="OperFlow_123",
        role="OPERATOR",
        department_id=dept_id,
    )

    vehicle_res = client.post(
        "/api/v1/vehicles",
        json={
            "department_id": dept_id,
            "brand": "KRAZ",
            "identifier": "AA1234BB",
            "fuel_type": "АБ",
            "consumption_l_per_100km": 30.0,
            "is_active": True,
        },
        headers=admin,
    )
    assert vehicle_res.status_code == 200, vehicle_res.text
    vehicle_id = int(vehicle_res.json()["id"])

    pa_res = client.post(
        "/api/v1/settings/planned-activities",
        json={"name": "Навчання", "is_active": True},
        headers=admin,
    )
    assert pa_res.status_code == 200, pa_res.text
    planned_activity_id = int(pa_res.json()["id"])

    dept_headers = _auth_headers(client, "dept_user_flow", "DeptFlow_123")
    req_res = client.post(
        "/api/v1/requests",
        json={"department_id": dept_id, "persons_involved_count": 10, "training_days_count": 2},
        headers=dept_headers,
    )
    assert req_res.status_code == 200, req_res.text
    req_id = int(req_res.json()["id"])

    item_res = client.post(
        f"/api/v1/requests/{req_id}/items",
        json={
            "planned_activity_id": planned_activity_id,
            "vehicle_id": vehicle_id,
            "route_is_manual": True,
            "route_text": "ППД - Полігон - ППД",
            "distance_km_per_trip": 12.5,
            "justification_text": "Smoke test",
            "persons_involved_count": 10,
            "training_days_count": 2,
        },
        headers=dept_headers,
    )
    assert item_res.status_code == 200, item_res.text

    submit_res = client.post(f"/api/v1/requests/{req_id}/submit", headers=dept_headers)
    assert submit_res.status_code == 200, submit_res.text
    assert submit_res.json()["status"] == "SUBMITTED"

    approve_res = client.post(f"/api/v1/requests/{req_id}/approve", headers=admin)
    assert approve_res.status_code == 200, approve_res.text
    assert approve_res.json()["status"] == "APPROVED"

    operator_headers = _auth_headers(client, "operator_flow", "OperFlow_123")
    issue_res = client.post(f"/api/v1/requests/{req_id}/issue", headers=operator_headers)
    assert issue_res.status_code == 200, issue_res.text
    assert issue_res.json()["status"] == "ISSUED_BY_OPERATOR"

    confirm_res = client.post(f"/api/v1/requests/{req_id}/confirm", headers=dept_headers)
    assert confirm_res.status_code == 200, confirm_res.text
    assert confirm_res.json()["status"] == "POSTED"
    assert confirm_res.json()["has_debt"] is True
    assert confirm_res.json()["result"] == "POSTED_WITH_DEBT"
    assert isinstance(confirm_res.json().get("message"), str)
    assert "заборгован" in confirm_res.json().get("message", "").lower()
    first_session_id = confirm_res.json().get("posting_session_id")
    assert first_session_id

    # repeated confirm without explicit key must reuse deterministic idempotency fallback
    confirm_repeat = client.post(f"/api/v1/requests/{req_id}/confirm", headers=dept_headers)
    assert confirm_repeat.status_code == 200, confirm_repeat.text
    assert confirm_repeat.json().get("posting_session_id") == first_session_id

    ledger_res = client.get("/api/v1/stock/ledger", headers=admin)
    assert ledger_res.status_code == 200, ledger_res.text
    # with zero stock, request is posted with debt and does not create negative stock movements
    assert not any(row["ref_type"] == "issue" and row["ref_id"] == req_id for row in ledger_res.json())

    detail_res = client.get(f"/api/v1/requests/{req_id}", headers=admin)
    assert detail_res.status_code == 200, detail_res.text
    detail = detail_res.json()
    assert detail["has_debt"] is True
    assert any(float(row["missing_liters"]) > 0 for row in (detail.get("fuel_summary") or []))

    backup_res = client.get("/api/v1/settings/backup", headers=admin)
    assert backup_res.status_code == 404, backup_res.text

    restore_bad = client.post(
        "/api/v1/settings/backup",
        files={"file": ("bad.json", b"{not-json}", "application/json")},
        headers=admin,
    )
    assert restore_bad.status_code == 404


def test_confirm_idempotent_and_single_active_rule(client: TestClient):
    admin = _auth_headers(client, "admin", "AdminPass_123")
    dept_id = _create_department(client, admin, "Dept Active Rule")

    _create_user(
        client,
        admin,
        login="dept_user_active",
        password="DeptActive_123",
        role="DEPT_USER",
        department_id=dept_id,
    )
    _create_user(
        client,
        admin,
        login="operator_active",
        password="OperActive_123",
        role="OPERATOR",
        department_id=dept_id,
    )

    vehicle_res = client.post(
        "/api/v1/vehicles",
        json={
            "department_id": dept_id,
            "brand": "MАЗ",
            "identifier": "BB1000AA",
            "fuel_type": "АБ",
            "consumption_l_per_100km": 20.0,
            "is_active": True,
        },
        headers=admin,
    )
    assert vehicle_res.status_code == 200, vehicle_res.text
    vehicle_id = int(vehicle_res.json()["id"])

    pa_res = client.post(
        "/api/v1/settings/planned-activities",
        json={"name": "Чергування", "is_active": True},
        headers=admin,
    )
    assert pa_res.status_code == 200, pa_res.text
    planned_activity_id = int(pa_res.json()["id"])

    # add stock so posting creates real issue rows
    rec_res = client.post(
        "/api/v1/stock/receipts",
        json={"fuel_type": "АБ", "input_unit": "L", "input_amount": 1000},
        headers=admin,
    )
    assert rec_res.status_code == 200, rec_res.text

    dept_headers = _auth_headers(client, "dept_user_active", "DeptActive_123")
    req1 = client.post(
        "/api/v1/requests",
        json={"department_id": dept_id, "persons_involved_count": 5, "training_days_count": 1},
        headers=dept_headers,
    )
    assert req1.status_code == 200, req1.text
    req1_id = int(req1.json()["id"])

    item_res = client.post(
        f"/api/v1/requests/{req1_id}/items",
        json={
            "planned_activity_id": planned_activity_id,
            "vehicle_id": vehicle_id,
            "route_is_manual": True,
            "route_text": "База - Район - База",
            "distance_km_per_trip": 10,
        },
        headers=dept_headers,
    )
    assert item_res.status_code == 200, item_res.text

    submit1 = client.post(f"/api/v1/requests/{req1_id}/submit", headers=dept_headers)
    assert submit1.status_code == 200, submit1.text
    assert submit1.json()["status"] == "SUBMITTED"

    # draft creation remains allowed, but submit of second active request must fail
    req2 = client.post(
        "/api/v1/requests",
        json={"department_id": dept_id, "persons_involved_count": 3, "training_days_count": 1},
        headers=dept_headers,
    )
    assert req2.status_code == 200, req2.text
    req2_id = int(req2.json()["id"])
    submit2 = client.post(f"/api/v1/requests/{req2_id}/submit", headers=dept_headers)
    assert submit2.status_code == 409

    approve1 = client.post(f"/api/v1/requests/{req1_id}/approve", headers=admin)
    assert approve1.status_code == 200, approve1.text
    operator_headers = _auth_headers(client, "operator_active", "OperActive_123")
    issue1 = client.post(f"/api/v1/requests/{req1_id}/issue", headers=operator_headers)
    assert issue1.status_code == 200, issue1.text

    idem_headers = {**dept_headers, "Idempotency-Key": "confirm-key-1"}
    confirm1 = client.post(f"/api/v1/requests/{req1_id}/confirm", headers=idem_headers, json={"idempotency_key": "confirm-key-1"})
    assert confirm1.status_code == 200, confirm1.text
    assert confirm1.json()["status"] == "POSTED"
    assert confirm1.json()["result"] in ("POSTED", "POSTED_WITH_DEBT")
    issue_doc_no = confirm1.json().get("issue_doc_no")
    assert issue_doc_no
    posting_session_id = confirm1.json().get("posting_session_id")
    assert posting_session_id
    assert isinstance(confirm1.json().get("breakdown"), dict)
    assert set(confirm1.json().get("breakdown", {}).keys()) == {"AB", "DP"}
    assert confirm1.json().get("request", {}).get("id") == req1_id
    assert confirm1.json().get("posting_session", {}).get("id") == posting_session_id
    assert confirm1.json().get("issue", {}).get("issue_doc_no") == issue_doc_no

    # same idempotency key returns saved successful result without duplicates
    confirm_same_key = client.post(
        f"/api/v1/requests/{req1_id}/confirm",
        headers=idem_headers,
        json={"idempotency_key": "confirm-key-1"},
    )
    assert confirm_same_key.status_code == 200, confirm_same_key.text
    assert confirm_same_key.json().get("issue_doc_no") == issue_doc_no
    assert confirm_same_key.json().get("posting_session_id") == posting_session_id

    # idempotent: second confirm returns already confirmed, no duplicate issue
    confirm2 = client.post(f"/api/v1/requests/{req1_id}/confirm", headers=dept_headers)
    assert confirm2.status_code == 200, confirm2.text
    assert confirm2.json()["result"] == "ALREADY_CONFIRMED"
    assert confirm2.json().get("issue_doc_no") == issue_doc_no


def test_confirm_ab_dp_split_and_debt_without_negative_balance(client: TestClient):
    admin = _auth_headers(client, "admin", "AdminPass_123")
    dept_id = _create_department(client, admin, "Split Fuel Dept")

    _create_user(
        client,
        admin,
        login="dept_user_split",
        password="DeptSplit_123",
        role="DEPT_USER",
        department_id=dept_id,
    )
    _create_user(
        client,
        admin,
        login="operator_split",
        password="OperSplit_123",
        role="OPERATOR",
        department_id=dept_id,
    )

    ab_vehicle = client.post(
        "/api/v1/vehicles",
        json={
            "department_id": dept_id,
            "brand": "AB Truck",
            "identifier": "AB-100",
            "fuel_type": "АБ",
            "consumption_l_per_100km": 100.0,
            "is_active": True,
        },
        headers=admin,
    )
    assert ab_vehicle.status_code == 200, ab_vehicle.text
    ab_vehicle_id = int(ab_vehicle.json()["id"])

    dp_vehicle = client.post(
        "/api/v1/vehicles",
        json={
            "department_id": dept_id,
            "brand": "DP Truck",
            "identifier": "DP-100",
            "fuel_type": "ДП",
            "consumption_l_per_100km": 100.0,
            "is_active": True,
        },
        headers=admin,
    )
    assert dp_vehicle.status_code == 200, dp_vehicle.text
    dp_vehicle_id = int(dp_vehicle.json()["id"])

    pa_res = client.post(
        "/api/v1/settings/planned-activities",
        json={"name": "Марш", "is_active": True},
        headers=admin,
    )
    assert pa_res.status_code == 200, pa_res.text
    planned_activity_id = int(pa_res.json()["id"])

    rec_ab = client.post(
        "/api/v1/stock/receipts",
        json={"fuel_type": "АБ", "input_unit": "L", "input_amount": 25},
        headers=admin,
    )
    assert rec_ab.status_code == 200, rec_ab.text
    rec_dp = client.post(
        "/api/v1/stock/receipts",
        json={"fuel_type": "ДП", "input_unit": "L", "input_amount": 10},
        headers=admin,
    )
    assert rec_dp.status_code == 200, rec_dp.text

    dept_headers = _auth_headers(client, "dept_user_split", "DeptSplit_123")
    req_res = client.post(
        "/api/v1/requests",
        json={"department_id": dept_id, "persons_involved_count": 2, "training_days_count": 1},
        headers=dept_headers,
    )
    assert req_res.status_code == 200, req_res.text
    req_id = int(req_res.json()["id"])

    ab_item = client.post(
        f"/api/v1/requests/{req_id}/items",
        json={
            "planned_activity_id": planned_activity_id,
            "vehicle_id": ab_vehicle_id,
            "route_is_manual": True,
            "route_text": "AB route",
            "distance_km_per_trip": 20,
        },
        headers=dept_headers,
    )
    assert ab_item.status_code == 200, ab_item.text
    dp_item = client.post(
        f"/api/v1/requests/{req_id}/items",
        json={
            "planned_activity_id": planned_activity_id,
            "vehicle_id": dp_vehicle_id,
            "route_is_manual": True,
            "route_text": "DP route",
            "distance_km_per_trip": 30,
        },
        headers=dept_headers,
    )
    assert dp_item.status_code == 200, dp_item.text

    assert client.post(f"/api/v1/requests/{req_id}/submit", headers=dept_headers).status_code == 200
    assert client.post(f"/api/v1/requests/{req_id}/approve", headers=admin).status_code == 200

    operator_headers = _auth_headers(client, "operator_split", "OperSplit_123")
    assert client.post(f"/api/v1/requests/{req_id}/issue", headers=operator_headers).status_code == 200

    idem_headers = {**dept_headers, "Idempotency-Key": "confirm-ab-dp-split"}
    confirm = client.post(
        f"/api/v1/requests/{req_id}/confirm",
        headers=idem_headers,
        json={"idempotency_key": "confirm-ab-dp-split"},
    )
    assert confirm.status_code == 200, confirm.text
    payload = confirm.json()
    assert payload["status"] == "POSTED"
    assert payload["has_debt"] is True
    assert payload["result"] == "POSTED_WITH_DEBT"
    assert payload.get("issue", {}).get("issue_doc_no")
    assert payload.get("breakdown", {}).get("AB", {}).get("posted", {}).get("liters", 0) > 0
    assert payload.get("breakdown", {}).get("DP", {}).get("debt", {}).get("liters", 0) > 0

    balance = client.get("/api/v1/stock/balance", headers=admin)
    assert balance.status_code == 200, balance.text
    for row in balance.json():
        assert float(row.get("balance_liters", 0.0)) >= -1e-6
        assert float(row.get("balance_kg", 0.0)) >= -1e-6
