#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
TS = datetime.now().strftime("%Y%m%d_%H%M%S")


@dataclass(frozen=True)
class PatchResult:
    changed: bool
    before_snippet: str | None = None
    after_snippet: str | None = None
    message: str = ""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def backup_file(path: Path) -> Path:
    backup_path = path.with_suffix(path.suffix + f".bak_{TS}")
    backup_path.write_text(read_text(path), encoding="utf-8")
    return backup_path


def apply_patch(path: Path, patch_fn: Callable[[str], PatchResult]) -> PatchResult:
    if not path.exists():
        return PatchResult(False, message=f"SKIP (missing): {path}")

    original = read_text(path)
    result = patch_fn(original)

    if not result.changed:
        return PatchResult(False, message=f"OK (no change): {path}")

    backup_file(path)
    write_text(path, result.after_snippet if result.after_snippet is not None else original)
    return PatchResult(True, message=f"PATCHED: {path}")


# ---------------------------
# Patch functions
# ---------------------------

def patch_routes_task_py(src: str) -> PatchResult:
    """
    Ensure route returns HTML partial for HTMX and JSON otherwise.
    Surgical: only touches get_task_status_route body.
    """
    if "HX-Request" in src and 'render_template("task_status.html"' in src:
        return PatchResult(False, message="routes_task.py already has HTMX+HTML handling")

    # Find function block for get_task_status_route
    m = re.search(r"def\s+get_task_status_route\s*\(\s*task_id:\s*str\s*\).*?:\n", src)
    if not m:
        return PatchResult(False, message="Could not find get_task_status_route() signature")

    # Very conservative: replace the final return render_template("task_status.html", task=task)
    # with a HX-Request conditional + JSON fallback.
    # We rely on your file already importing render_template/jsonify/Response.
    replaced = False

    def repl(match: re.Match) -> str:
        nonlocal replaced
        replaced = True
        indent = match.group(1)
        return (
            f"{indent}# ✅ HTMX requests expect an HTML partial (not JSON)\n"
            f"{indent}if request.headers.get(\"HX-Request\") == \"true\":\n"
            f"{indent}    return render_template(\"task_status.html\", task=task)\n\n"
            f"{indent}# ✅ Non-HTMX (JS/API) callers may expect JSON\n"
            f"{indent}return jsonify({{\n"
            f"{indent}    \"task_id\": getattr(task, \"id\", None) or getattr(task, \"_id\", None),\n"
            f"{indent}    \"status\": str(getattr(task, \"status\", \"\")),\n"
            f"{indent}    \"result_id\": getattr(task, \"result_id\", None),\n"
            f"{indent}    \"error_message\": getattr(task, \"error_message\", None),\n"
            f"{indent}    \"task_type\": getattr(task, \"task_type\", None),\n"
            f"{indent}}})\n"
        )

    # Replace the last "return render_template(...task_status.html...)" inside the route
    new_src = re.sub(
        r"(?m)^(\s*)return\s+render_template\(\s*[\"']task_status\.html[\"']\s*,\s*task\s*=\s*task\s*\)\s*$",
        repl,
        src,
        count=1,
    )

    if not replaced:
        return PatchResult(False, message="Could not locate return render_template('task_status.html', task=task) to patch")

    # Ensure we import request (needed for HX-Request header)
    if "from flask import" in new_src and " request" not in new_src:
        new_src = re.sub(
            r"from flask import ([^\n]+)\n",
            lambda mm: (
                "from flask import "
                + (mm.group(1).strip().rstrip(",") + ", request")
                + "\n"
                if "request" not in mm.group(1)
                else mm.group(0)
            ),
            new_src,
            count=1,
        )

    return PatchResult(True, after_snippet=new_src, message="Patched routes_task.py for HTMX HTML + JSON fallback")


def patch_route_return_partial_for_htmx(src: str, task_fetch_code: str) -> PatchResult:
    """
    Generic patch: insert an HTMX return after task creation/publish, before returning jsonify.
    It looks for 'return jsonify(' and injects block right before it.
    """
    if "HX-Request" in src and 'render_template("task_status.html"' in src:
        return PatchResult(False, message="Route already returns task_status.html for HTMX")

    if "return jsonify" not in src:
        return PatchResult(False, message="No return jsonify(...) found to patch")

    # We insert just before the first `return jsonify(` in the function (surgical).
    insert_block = (
        "\n        # ✅ HTMX expects an HTML partial so it won't render JSON in the page\n"
        "        if request.headers.get(\"HX-Request\") == \"true\":\n"
        f"{task_fetch_code}"
        "            return render_template(\"task_status.html\", task=task), 202\n\n"
    )

    parts = src.split("return jsonify", 1)
    before, after = parts[0], "return jsonify" + parts[1]

    # Add imports if missing
    new_src = before + insert_block + after

    # Ensure imports exist
    if "render_template" not in new_src:
        new_src = re.sub(
            r"from flask import ([^\n]+)\n",
            lambda mm: (
                "from flask import "
                + (mm.group(1).strip().rstrip(",") + ", render_template")
                + "\n"
                if "render_template" not in mm.group(1)
                else mm.group(0)
            ),
            new_src,
            count=1,
        )

    if "request" not in new_src:
        new_src = re.sub(
            r"from flask import ([^\n]+)\n",
            lambda mm: (
                "from flask import "
                + (mm.group(1).strip().rstrip(",") + ", request")
                + "\n"
                if "request" not in mm.group(1)
                else mm.group(0)
            ),
            new_src,
            count=1,
        )

    return PatchResult(True, after_snippet=new_src, message="Inserted HTMX HTML partial return")


def patch_routes_upload_py(src: str) -> PatchResult:
    """
    After creating tasks, if HTMX -> return task_status partial for first task.
    """
    if "HX-Request" in src and 'render_template("task_status.html"' in src:
        return PatchResult(False, message="routes_upload.py already patched")

    # Need access to task_repo and first task id in that scope.
    # Your upload route already has task_repo and tasks_created list.
    task_fetch_code = (
        "            # Show the first task (simple UX); batch UI can be added later\n"
        "            poll_task_id = tasks_created[0] if tasks_created else None\n"
        "            if not poll_task_id:\n"
        "                return jsonify({\"error\": \"No task created\"}), 500\n"
        "            task = task_repo.get_by_id(poll_task_id)\n"
    )

    return patch_route_return_partial_for_htmx(src, task_fetch_code)


def patch_routes_summary_py(src: str) -> PatchResult:
    """
    After creating `task`, if HTMX -> return task_status partial.
    """
    if "HX-Request" in src and 'render_template("task_status.html"' in src:
        return PatchResult(False, message="routes_summary.py already patched")

    task_fetch_code = (
        "            task = task_repo.get_by_id(task.id)\n"
        "            if task is None:\n"
        "                return jsonify({\"error\": \"Task not found\"}), 404\n"
    )
    return patch_route_return_partial_for_htmx(src, task_fetch_code)


def patch_routes_homework_py(src: str) -> PatchResult:
    """
    After create_task() returns task_id, if HTMX -> return task_status partial using get_task(task_id).
    """
    if "HX-Request" in src and 'render_template("task_status.html"' in src:
        return PatchResult(False, message="routes_homework.py already patched")

    # Ensure get_task is importable in this file
    if "from src.services.task_service import" in src and "get_task" not in src:
        src = re.sub(
            r"from src\.services\.task_service import ([^\n]+)\n",
            lambda mm: (
                "from src.services.task_service import " + mm.group(1).strip() + ", get_task\n"
            ),
            src,
            count=1,
        )
    elif "from src.services.task_service import" not in src:
        # If absent, add a new import near the top
        src = src.replace(
            "from sb_utils.logger_utils import logger\n",
            "from sb_utils.logger_utils import logger\nfrom src.services.task_service import get_task\n",
        )

    task_fetch_code = (
        "            task = get_task(task_id)\n"
        "            if task is None:\n"
        "                return jsonify({\"error\": \"Task not found\"}), 404\n"
    )
    return patch_route_return_partial_for_htmx(src, task_fetch_code)


def patch_tool_template_target(src: str) -> PatchResult:
    """
    Replace hx-target="#upload-result" with hx-target="#task-status-container"
    """
    if 'hx-target="#task-status-container"' in src:
        return PatchResult(False, message="Template already points to #task-status-container")

    if 'hx-target="#upload-result"' not in src:
        return PatchResult(False, message="No hx-target=\"#upload-result\" found")

    new_src = src.replace('hx-target="#upload-result"', 'hx-target="#task-status-container"')
    return PatchResult(True, after_snippet=new_src, message="Updated hx-target to #task-status-container")


# ---------------------------
# Main
# ---------------------------

def main() -> int:
    patches: list[tuple[Path, Callable[[str], PatchResult]]] = []

    # A) routes_task.py
    patches.append((ROOT / "src/api/routes_task.py", patch_routes_task_py))

    # B) HTMX partial returns
    patches.append((ROOT / "src/api/routes_upload.py", patch_routes_upload_py))
    patches.append((ROOT / "src/api/routes_summary.py", patch_routes_summary_py))
    patches.append((ROOT / "src/api/routes_homework.py", patch_routes_homework_py))

    # C) Template hx-target fixes
    patches.append((ROOT / "ui/templates/tool_flashcards.html", patch_tool_template_target))
    patches.append((ROOT / "ui/templates/tool_assess.html", patch_tool_template_target))

    changed_any = False
    print(f"\nStudyBuddy one-time HTMX task fixes (root={ROOT})")
    print(f"Backups suffix: .bak_{TS}\n")

    for path, fn in patches:
        if not path.exists():
            print(f"SKIP (missing): {path}")
            continue

        original = read_text(path)
        res = fn(original)
        if not res.changed:
            print(f"OK: {path}  -> {res.message}")
            continue

        backup = backup_file(path)
        write_text(path, res.after_snippet or original)
        changed_any = True
        print(f"PATCHED: {path}")
        print(f"  backup: {backup}")

    print("\nDone.")
    if changed_any:
        print("Next steps:")
        print("  1) Run your app/tests")
        print("  2) Open tool pages (flashcards/assess/homework/summary) and verify the spinner/partial is shown")
        print("  3) Commit changes")
    else:
        print("No changes were needed (already patched).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
