#!/usr/bin/env python3
from __future__ import annotations

import ast
import html
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENDPOINTS_DIR = ROOT / "backend" / "app" / "api" / "v1" / "endpoints"
OUT_DIR = ROOT / "docs"
OUT_DIR_BACKEND = ROOT / "backend" / "docs"


@dataclass
class EndpointRow:
    module: str
    method: str
    path: str
    function_name: str
    access: str
    checks: str


def _extract_methods_and_paths(node: ast.AST) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for dec in getattr(node, "decorator_list", []):
        if not isinstance(dec, ast.Call):
            continue
        if not isinstance(dec.func, ast.Attribute):
            continue
        if not isinstance(dec.func.value, ast.Name) or dec.func.value.id != "router":
            continue
        method = dec.func.attr.upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            continue
        path = ""
        if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
            path = dec.args[0].value
        out.append((method, path))
    return out


def _extract_access(src: str) -> str:
    m_role = re.search(r'deps\.require_role\("([^"]+)"\)', src)
    if m_role:
        return m_role.group(1)
    m_any = re.search(r"deps\.require_any_role\(\[([^\]]+)\]\)", src)
    if m_any:
        roles = re.findall(r'"([^"]+)"', m_any.group(1))
        if roles:
            return ", ".join(roles)
    if "deps.get_current_active_user" in src:
        return "AUTHENTICATED"
    return "PUBLIC"


def _extract_checks(src: str) -> str:
    checks: list[str] = []
    patterns = [
        (r"req\.department_id != current_user\.department_id", "DEPT_USER: тільки власний підрозділ"),
        (r"Request belongs to another department", "Перевірка належності заявки підрозділу"),
        (r"job\.created_by != current_user\.id", "DEPT_USER: лише власні export jobs"),
        (r"req\.status not in \[RequestStatus\.APPROVED, RequestStatus\.ISSUED_BY_OPERATOR\]", "OPERATOR: лише заявки APPROVED/ISSUED_BY_OPERATOR"),
        (r"if req\.status != RequestStatus\.DRAFT", "Редагування лише чернеток"),
        (r"if req\.status not in \[RequestStatus\.APPROVED, RequestStatus\.ISSUED_BY_OPERATOR\]", "Видача оператором лише APPROVED/ISSUED_BY_OPERATOR"),
        (r"if current_user\.role\.value == \"DEPT_USER\"", "Є окрема логіка/скоуп для DEPT_USER"),
        (r"if current_user\.role\.value == \"OPERATOR\"", "Є окрема логіка/скоуп для OPERATOR"),
    ]
    for pattern, label in patterns:
        if re.search(pattern, src):
            checks.append(label)
    # Deduplicate while preserving order
    seen: set[str] = set()
    uniq = [c for c in checks if not (c in seen or seen.add(c))]
    return "; ".join(uniq)


def collect_endpoints() -> list[EndpointRow]:
    rows: list[EndpointRow] = []
    for path in sorted(ENDPOINTS_DIR.glob("*.py")):
        if path.name.startswith("__"):
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        module = path.stem
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            method_paths = _extract_methods_and_paths(node)
            if not method_paths:
                continue
            segment = ast.get_source_segment(source, node) or ""
            access = _extract_access(segment)
            checks = _extract_checks(segment)
            for method, route in method_paths:
                rows.append(
                    EndpointRow(
                        module=module,
                        method=method,
                        path=f"/api/v1{route}",
                        function_name=node.name,
                        access=access,
                        checks=checks or "—",
                    )
                )
    rows.sort(key=lambda r: (r.module, r.path, r.method, r.function_name))
    return rows


def render_markdown(rows: list[EndpointRow]) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []
    lines.append("# PMM Online: Детальна Матриця Прав Доступу")
    lines.append("")
    lines.append(f"_Згенеровано: {generated}_")
    lines.append("")
    lines.append("## 1. Ролі системи")
    lines.append("")
    lines.append("- `ADMIN`: повний контроль системи, довідників, складу, користувачів, звітів, оновлень, backup/restore, шаблонів друку.")
    lines.append("- `OPERATOR`: операційна роль видачі ПММ, перегляд погоджених заявок, проведення етапу видачі.")
    lines.append("- `DEPT_USER`: роль підрозділу, створення/редагування своїх заявок (до подання), підтвердження отримання, робота зі своїм ТЗ/маршрутами.")
    lines.append("")
    lines.append("## 2. Що хто бачить у UI")
    lines.append("")
    lines.append("### ADMIN")
    lines.append("- Дашборд, Заявки, Склад (прихід/баланс/журнал/коригування/перевірка), Інциденти.")
    lines.append("- Звіти: `Звіт ТЗ`, `Звіт по підрозділах`.")
    lines.append("- Довідники: підрозділи, транспорт, маршрути, густина, оператори, налаштування заявок.")
    lines.append("- Система, PDF шаблони, Підтримка, Профіль.")
    lines.append("")
    lines.append("### OPERATOR")
    lines.append("- `Готово до видачі`, `Видано`, Профіль, Підтримка.")
    lines.append("- У заявках оператор працює тільки зі статусами, допустимими для видачі.")
    lines.append("")
    lines.append("### DEPT_USER")
    lines.append("- `Мої заявки`, `Створити заявку`, `Транспорт`, `Маршрути`, Профіль, Підтримка.")
    lines.append("- Доступ обмежений тільки власним підрозділом.")
    lines.append("")
    lines.append("## 3. Бізнес-обмеження (критичні)")
    lines.append("")
    lines.append("- Підрозділ не може працювати із заявками іншого підрозділу.")
    lines.append("- OPERATOR не має адмінських доступів; видача робиться лише в допустимому життєвому циклі заявки.")
    lines.append("- Підтвердження підрозділом формує акт видачі (`issue_doc_no`) і проводить рух по складу.")
    lines.append("- Експортні jobs для `DEPT_USER` обмежені лише власними jobs.")
    lines.append("- Більшість системних/конфігураційних endpoint-ів доступні тільки `ADMIN`.")
    lines.append("")
    lines.append("## 4. Повна API-матриця доступу")
    lines.append("")
    lines.append("| Module | Method | Path | Access | Function | Додаткові перевірки |")
    lines.append("|---|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| `{r.module}` | `{r.method}` | `{r.path}` | `{r.access}` | `{r.function_name}` | {r.checks} |"
        )
    lines.append("")
    lines.append("## 5. Пояснення Access")
    lines.append("")
    lines.append("- `PUBLIC`: endpoint без role-checker (може мати інші перевірки).")
    lines.append("- `AUTHENTICATED`: будь-який активний користувач з валідним токеном.")
    lines.append("- `ADMIN`, `OPERATOR`, `DEPT_USER`: строго рольовий доступ.")
    lines.append("- `ADMIN, DEPT_USER` (та інші комбінації): доступний набір ролей, додаткові обмеження див. у колонці перевірок.")
    lines.append("")
    lines.append("## 6. Рекомендації експлуатації")
    lines.append("")
    lines.append("- Ревізію цього документа робити після кожного релізу зі зміною endpoint-ів або role logic.")
    lines.append("- Для audit trail зберігати версію цього PDF разом з релізом.")
    lines.append("- Для критичних дій (`approve/issue/confirm/restore/update`) залишати додатковий операційний контроль через журнал дій.")
    lines.append("")
    return "\n".join(lines)


def render_html(md_text: str) -> str:
    # Lightweight markdown-to-html for our controlled format.
    lines = md_text.splitlines()
    out: list[str] = []
    out.append("<!doctype html><html lang='uk'><head><meta charset='utf-8' />")
    out.append(
        "<style>"
        "body{font-family:'Times New Roman',serif;color:#111;font-size:12px;line-height:1.35;margin:16mm;}"
        "h1{font-size:24px;margin:0 0 10px;}h2{font-size:18px;margin:18px 0 8px;}h3{font-size:15px;margin:12px 0 6px;}"
        "p,li{font-size:12px;}table{width:100%;border-collapse:collapse;table-layout:fixed;}"
        "th,td{border:1px solid #555;padding:4px 6px;vertical-align:top;word-break:break-word;overflow-wrap:anywhere;}"
        "th{background:#eee;font-weight:700;}code{background:#f4f4f4;padding:1px 3px;border-radius:3px;}"
        "@page{size:A4 landscape;margin:10mm;}"
        "</style>"
    )
    out.append("</head><body>")

    in_list = False
    in_table = False

    for ln in lines:
        if ln.startswith("# "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h1>{html.escape(ln[2:])}</h1>")
            continue
        if ln.startswith("## "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h2>{html.escape(ln[3:])}</h2>")
            continue
        if ln.startswith("### "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h3>{html.escape(ln[4:])}</h3>")
            continue
        if ln.startswith("|") and ln.endswith("|"):
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if not in_table:
                out.append("<table>")
                in_table = True
            if set(cells) == {"---"} or all(set(c) <= {"-"} for c in cells):
                continue
            tag = "th" if "Module" in cells[0] and "Path" in " ".join(cells) else "td"
            out.append("<tr>" + "".join(f"<{tag}>{html.escape(c)}</{tag}>" for c in cells) + "</tr>")
            continue
        else:
            if in_table:
                out.append("</table>")
                in_table = False

        if ln.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{html.escape(ln[2:])}</li>")
            continue
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
        if ln.strip():
            txt = re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(ln))
            txt = re.sub(r"_(.+)_", r"<em>\1</em>", txt)
            out.append(f"<p>{txt}</p>")

    if in_list:
        out.append("</ul>")
    if in_table:
        out.append("</table>")

    out.append("</body></html>")
    return "\n".join(out)


def main() -> None:
    rows = collect_endpoints()
    md = render_markdown(rows)
    html_text = render_html(md)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR_BACKEND.mkdir(parents=True, exist_ok=True)

    (OUT_DIR / "ROLE_PERMISSIONS_DETAILED.md").write_text(md, encoding="utf-8")
    (OUT_DIR / "ROLE_PERMISSIONS_DETAILED.html").write_text(html_text, encoding="utf-8")

    # duplicate for backend container (mounted as /app)
    (OUT_DIR_BACKEND / "ROLE_PERMISSIONS_DETAILED.md").write_text(md, encoding="utf-8")
    (OUT_DIR_BACKEND / "ROLE_PERMISSIONS_DETAILED.html").write_text(html_text, encoding="utf-8")

    print(f"Generated rows: {len(rows)}")
    print(f"Wrote: {OUT_DIR / 'ROLE_PERMISSIONS_DETAILED.md'}")
    print(f"Wrote: {OUT_DIR / 'ROLE_PERMISSIONS_DETAILED.html'}")
    print(f"Wrote: {OUT_DIR_BACKEND / 'ROLE_PERMISSIONS_DETAILED.html'}")


if __name__ == "__main__":
    main()
