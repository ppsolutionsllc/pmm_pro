from app.services.pdf_template_service import AVAILABLE_SOURCES, _build_render_rows, _normalize_service_block_json


def _base_column(*, column_id: str, source: str, fmt: str = "text", align: str = "left") -> dict:
    return {
        "id": column_id,
        "title": column_id,
        "source": source,
        "format": fmt,
        "align": align,
        "visible": True,
        "rules": {"visibility_rule": "ALWAYS"},
    }


def test_build_render_rows_uses_single_row_for_non_item_sources() -> None:
    request_ctx = {
        "request": {"status": "SUBMITTED", "has_debt": False, "request_number": "REQ-1"},
        "department": {"name": "Підрозділ 1"},
        "items": [
            {"row_no": 1, "planned_activity_name": "Марш №1"},
            {"row_no": 2, "planned_activity_name": "Марш №2"},
        ],
    }
    columns = [
        _base_column(column_id="request_number", source="request.request_number"),
        _base_column(column_id="department", source="department.name"),
    ]

    render = _build_render_rows(columns, request_ctx)

    assert len(render) == 1
    assert len(render[0]["rows"]) == 1
    assert [cell["value"] for cell in render[0]["rows"][0]["cells"]] == ["REQ-1", "Підрозділ 1"]


def test_build_render_rows_uses_item_rows_for_item_sources() -> None:
    request_ctx = {
        "request": {"status": "SUBMITTED", "has_debt": False, "request_number": "REQ-2"},
        "items": [
            {
                "row_no": 1,
                "planned_activity_name": "Запланований захід",
                "vehicle_name": "КрАЗ",
                "distance_km_per_trip": 14.5,
            },
            {
                "row_no": 2,
                "planned_activity_name": "Другий захід",
                "vehicle_name": "МАЗ",
                "distance_km_per_trip": 8,
            },
        ],
    }
    columns = [
        _base_column(column_id="row_no", source="computed.row_no", fmt="number_0", align="center"),
        _base_column(column_id="planned_activity_name", source="item.planned_activity_name"),
        _base_column(column_id="vehicle_name", source="item.vehicle_name"),
        _base_column(column_id="distance", source="item.distance_km_per_trip", fmt="number_2", align="right"),
        _base_column(column_id="request_number", source="request.request_number"),
    ]

    render = _build_render_rows(columns, request_ctx)

    assert len(render) == 1
    assert len(render[0]["rows"]) == 2
    assert [cell["value"] for cell in render[0]["rows"][0]["cells"]] == ["1", "Запланований захід", "КрАЗ", "14.50", "REQ-2"]
    assert [cell["value"] for cell in render[0]["rows"][1]["cells"]] == ["2", "Другий захід", "МАЗ", "8.00", "REQ-2"]


def test_available_sources_contains_print_form_fields() -> None:
    required = {
        "item.planned_activity_name",
        "item.vehicle_name",
        "item.distance_km_per_trip",
        "computed.row_no",
        "department.name",
    }
    assert required.issubset(set(AVAILABLE_SOURCES))


def test_build_render_rows_normalizes_column_widths_to_100_percent() -> None:
    request_ctx = {"request": {"status": "SUBMITTED", "has_debt": False}, "items": []}
    columns = [
        {**_base_column(column_id="a", source="request.request_number"), "width": 80},
        {**_base_column(column_id="b", source="request.status"), "width": 80},
        {**_base_column(column_id="c", source="request.route_text"), "width": 40},
    ]

    render = _build_render_rows(columns, request_ctx)
    widths = [float(c["width"]) for c in render[0]["columns"]]

    assert abs(sum(widths) - 100.0) <= 0.11
    assert all(w > 0 for w in widths)


def test_normalize_service_block_keeps_only_allowed_flags() -> None:
    normalized = _normalize_service_block_json(
        {
            "show_request_number": True,
            "show_generated_at": True,
            "show_department": True,
            "show_system_version": False,
            "show_qr": True,
            "show_status": True,
            "show_issue_doc_no": True,
            "show_audit_users": True,
            "rules": {"issue_doc_no": "IF_STATUS_IN"},
        }
    )

    assert normalized == {
        "show_request_number": True,
        "show_generated_at": True,
        "show_department": True,
        "show_system_version": False,
        "show_qr": True,
    }
