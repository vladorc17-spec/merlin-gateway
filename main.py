from flask import Flask, jsonify, request
import requests
import os

app = Flask(__name__)

MOODLE_TOKEN = os.environ.get("MOODLE_TOKEN", "46d3cd2f1c90e7a292e4f5b1ff51124a")
MOODLE_BASE = "https://moodle.srce.hr/2025-2026/webservice/rest/server.php"
SECRET = os.environ.get("GATEWAY_SECRET", "merlin2526")

def check_secret():
    return request.args.get("secret") == SECRET or request.headers.get("X-Secret") == SECRET

def moodle(fn, **params):
    r = requests.post(MOODLE_BASE, data={
        "wstoken": MOODLE_TOKEN,
        "wsfunction": fn,
        "moodlewsrestformat": "json",
        **params
    }, timeout=15)
    data = r.json()
    if isinstance(data, dict) and "exception" in data:
        raise Exception(data.get("message", data["exception"]))
    return data

def get_user_id():
    info = moodle("core_webservice_get_site_info")
    return info["userid"], info["fullname"]

@app.route("/robots.txt")
def robots():
    return "User-agent: *\nAllow: /\n", 200, {"Content-Type": "text/plain"}

@app.route("/")
def index():
    return jsonify({"status": "Merlin Gateway running", "endpoints": [
        "/info", "/courses", "/assignments", "/files?course=NAME", "/grades?course_id=ID"
    ]})

@app.route("/info")
def info():
    if not check_secret(): return jsonify({"error": "unauthorized"}), 401
    data = moodle("core_webservice_get_site_info")
    return jsonify({"name": data["fullname"], "userid": data["userid"], "site": data["sitename"]})

@app.route("/courses")
def courses():
    if not check_secret(): return jsonify({"error": "unauthorized"}), 401
    uid, name = get_user_id()
    data = moodle("core_enrol_get_users_courses", userid=uid)
    result = [{"id": c["id"], "name": c["fullname"], "short": c["shortname"]} 
              for c in data if not c.get("hidden")]
    return jsonify({"user": name, "courses": result})

@app.route("/assignments")
def assignments():
    if not check_secret(): return jsonify({"error": "unauthorized"}), 401
    uid, _ = get_user_id()
    courses = [c for c in moodle("core_enrol_get_users_courses", userid=uid) if not c.get("hidden")]
    
    ids = {f"courseids[{i}]": c["id"] for i, c in enumerate(courses)}
    course_map = {c["id"]: c["fullname"] for c in courses}
    
    data = moodle("mod_assign_get_assignments", **ids)
    result = []
    for c in data.get("courses", []):
        for a in c.get("assignments", []):
            result.append({
                "name": a["name"],
                "course": course_map.get(c["id"], ""),
                "duedate": a.get("duedate", 0),
                "id": a["id"]
            })
    result.sort(key=lambda x: x["duedate"] or 0)
    return jsonify({"assignments": result})

@app.route("/files")
def files():
    if not check_secret(): return jsonify({"error": "unauthorized"}), 401
    course_query = request.args.get("course", "").lower()
    uid, _ = get_user_id()
    courses = [c for c in moodle("core_enrol_get_users_courses", userid=uid) if not c.get("hidden")]
    
    # Fuzzy match course name
    course = None
    for c in courses:
        if course_query in c["fullname"].lower() or course_query in c["shortname"].lower():
            course = c
            break
    if not course:
        words = [w for w in course_query.split() if len(w) > 3]
        for c in courses:
            if any(w in c["fullname"].lower() for w in words):
                course = c
                break
    if not course:
        return jsonify({"error": "course not found", "available": [c["fullname"] for c in courses]}), 404

    sections = moodle("core_course_get_contents", courseid=course["id"])
    result = []
    for sec in sections:
        for mod in sec.get("modules", []):
            for content in mod.get("contents", []):
                if content["type"] == "file":
                    url = content["fileurl"]
                    url += ("&" if "?" in url else "?") + f"token={MOODLE_TOKEN}"
                    result.append({
                        "name": content["filename"],
                        "section": sec["name"],
                        "type": content.get("mimetype", ""),
                        "url": url
                    })
    return jsonify({"course": course["fullname"], "files": result})

@app.route("/grades")
def grades():
    if not check_secret(): return jsonify({"error": "unauthorized"}), 401
    course_id = request.args.get("course_id")
    if not course_id:
        return jsonify({"error": "course_id required"}), 400
    uid, _ = get_user_id()
    data = moodle("gradereport_user_get_grades_table", courseid=int(course_id), userid=uid)
    rows = (data.get("tables") or [{}])[0].get("tabledata", [])
    result = []
    for r in rows:
        if r.get("itemname") and r["itemname"].get("content"):
            import re
            name = re.sub(r"<[^>]+>", "", r["itemname"]["content"]).strip()
            grade = re.sub(r"<[^>]+>", "", (r.get("grade") or {}).get("content", "—")).strip()
            if name:
                result.append({"item": name, "grade": grade})
    return jsonify({"grades": result})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
