import json
import os
import re
from typing import Any, Dict, List

from dotenv import load_dotenv
from flask import Flask, render_template, request

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - defensive for environment setup
    genai = None

load_dotenv()

app = Flask(__name__)

EXPECTED_KEYS = {
    "project_name",
    "objective",
    "success_criteria",
    "key_deliverables",
    "milestones",
    "high_level_requirements",
    "resource",
    "risks",
    "stakeholders",
    "project_manager",
}


def _normalize_stakeholders(raw_entries: List[Dict[str, str]]) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        role = str(entry.get("role", "")).strip()
        if name or role:
            normalized.append({"name": name, "role": role})
    return normalized


def _parse_json_response(raw_text: str) -> Dict[str, Any]:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = cleaned.strip()
    if not cleaned:
        raise ValueError("Gemini returned an empty response.")
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("Gemini response is not a JSON object.")

    missing = sorted(EXPECTED_KEYS - set(data.keys()))
    if missing:
        raise ValueError(f"Gemini response is missing required fields: {', '.join(missing)}")

    data["milestones"] = data.get("milestones") or []
    data["high_level_requirements"] = data.get("high_level_requirements") or []
    data["risks"] = data.get("risks") or []
    data["stakeholders"] = _normalize_stakeholders(data.get("stakeholders") or [])

    if not isinstance(data["project_name"], str):
        raise ValueError("project_name must be a string.")
    if not isinstance(data["objective"], str):
        raise ValueError("objective must be a string.")
    if not isinstance(data["resource"], dict):
        raise ValueError("resource must be an object.")

    return data


def _extract_stakeholders(form_data) -> List[Dict[str, str]]:
    names = form_data.getlist("stakeholder_name")
    roles = form_data.getlist("stakeholder_role")
    stakeholders: List[Dict[str, str]] = []
    for index, name in enumerate(names):
        role = roles[index] if index < len(roles) else ""
        if name.strip() or role.strip():
            stakeholders.append({"name": name.strip(), "role": role.strip()})
    return stakeholders


def _generate_prompt(project_data: Dict[str, Any]) -> str:
    stakeholders_block = "\n".join(
        f"- {entry['name']} ({entry['role']})" for entry in project_data.get("stakeholders", []) if entry.get("name")
    )
    return f"""
You are an expert project manager and business analyst.
Create a professional project charter for the project described below.
Return ONLY valid JSON with exactly this schema and no extra text or markdown fences:

{{
  "project_name": "string",
  "objective": "string",
  "success_criteria": "string",
  "key_deliverables": "string",
  "milestones": [
    {{"name": "string", "deadline": "string"}}
  ],
  "high_level_requirements": ["string"],
  "resource": {{
    "budget": "string",
    "team_members": "string"
  }},
  "risks": ["string"],
  "stakeholders": [
    {{"name": "string", "role": "string"}}
  ],
  "project_manager": "string"
}}

Project details:
- Project Name: {project_data['project_name']}
- Objective / Goal: {project_data['objective']}
- Budget constraint: {project_data['budget_constraint']}
- Timeline constraint: {project_data['timeline_constraint']}
- Team size / resources: {project_data['team_size_resources']}
- Stakeholders: {stakeholders_block or 'Not provided'}

Write all strings in professional business language. Make sure milestones are realistic for the given timeline constraint and include a clear owner in project_manager.
Return only valid JSON.
""".strip()



def _call_gemini(project_data: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing. Add it to your .env file.")

    if genai is None:
        raise ValueError("google-generativeai is not installed.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-flash-latest")
    response = model.generate_content(_generate_prompt(project_data))


    raw_text = getattr(response, "text", "")
    if not raw_text:
        raise ValueError("Gemini returned an empty response.")
    return _parse_json_response(raw_text)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")

    project_name = request.form.get("project_name", "").strip()
    objective = request.form.get("objective", "").strip()
    budget_constraint = request.form.get("budget_constraint", "").strip()
    timeline_constraint = request.form.get("timeline_constraint", "").strip()
    team_size_resources = request.form.get("team_size_resources", "").strip()
    stakeholders = _extract_stakeholders(request.form)

    form_data = {
        "project_name": project_name,
        "objective": objective,
        "budget_constraint": budget_constraint,
        "timeline_constraint": timeline_constraint,
        "team_size_resources": team_size_resources,
        "stakeholders": stakeholders,
    }

    if not project_name or not objective or not budget_constraint or not timeline_constraint or not team_size_resources:
        return render_template("index.html", error="Please complete all required fields before generating the charter.", form_data=form_data)

    if not stakeholders:
        return render_template("index.html", error="Please provide at least one stakeholder name and role.", form_data=form_data)

    try:
        charter = _call_gemini(form_data)
        return render_template("charter.html", charter=charter)
    except Exception as exc:  # noqa: BLE001
        return render_template(
            "index.html",
            error=f"We could not generate the charter right now: {exc}",
            form_data=form_data,
        )


if __name__ == "__main__":
    app.run(debug=True)
