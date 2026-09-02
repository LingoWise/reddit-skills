"""DAG-based plan executor with conditionals, retries, and checkpoints."""

import json
import logging
import re
import subprocess
import sys
import time

from .state import save_state


def topological_sort(steps):
    """Sort steps by dependency order. Raises ValueError on cycle."""
    name_to_step = {s["name"]: s for s in steps}
    visited = {}
    result = []

    def visit(name, path):
        if visited.get(name) == "done":
            return
        if visited.get(name) == "visiting":
            raise ValueError(f"Dependency cycle detected: {' -> '.join(path + [name])}")
        visited[name] = "visiting"
        step = name_to_step.get(name)
        if step is None:
            raise ValueError(f"Unknown dependency: {name}")
        for dep in step.get("depends_on", []):
            visit(dep, path + [name])
        visited[name] = "done"
        result.append(step)

    for step in steps:
        visit(step["name"], [])

    return result


def resolve_placeholders(command, step_outputs, params):
    """Replace {step_name.field} and {param_name} placeholders in command args."""
    resolved = []
    for arg in command:
        if not isinstance(arg, str):
            resolved.append(arg)
            continue

        def replace_step_ref(match):
            ref = match.group(1)
            if "." in ref:
                parts = ref.split(".", 1)
                step_name, field = parts[0], parts[1]
                step_out = step_outputs.get(step_name, {})
                value = step_out
                for key in field.split("."):
                    if isinstance(value, dict):
                        value = value.get(key)
                    elif isinstance(value, list) and key.isdigit() and key != "":
                        idx = int(key)
                        if 0 <= idx < len(value):
                            value = value[idx]
                        else:
                            return match.group(0)
                    else:
                        return match.group(0)
                if value is not None:
                    return str(value)
            return match.group(0)

        arg = re.sub(r"\{([\w.]+)\}", replace_step_ref, arg)

        def replace_param_ref(match):
            ref = match.group(1)
            if "." not in ref and ref in params:
                return str(params[ref])
            return match.group(0)

        arg = re.sub(r"\{([\w.]+)\}", replace_param_ref, arg)
        resolved.append(arg)
    return resolved


def evaluate_condition(condition, step_outputs):
    """Evaluate a condition string against step outputs."""
    if condition is None:
        return True

    or_parts = re.split(r"\s+or\s+", condition)
    for or_part in or_parts:
        and_parts = re.split(r"\s+and\s+", or_part)
        all_true = True
        for part in and_parts:
            if not _eval_single_condition(part.strip(), step_outputs):
                all_true = False
                break
        if all_true:
            return True
    return False


def _eval_single_condition(expr, step_outputs):
    """Evaluate a single condition expression."""
    m = re.match(r"(\w+)\.(\w+)\s*(==|!=)\s*(.+)", expr)
    if not m:
        return False

    step_name, field, op, value_str = m.groups()
    step_out = step_outputs.get(step_name)
    if step_out is None:
        return False

    actual = step_out.get(field)
    if actual is None:
        return False

    value_str = value_str.strip()
    if value_str == "true":
        expected = True
    elif value_str == "false":
        expected = False
    else:
        expected = value_str

    if op == "==":
        return actual == expected
    elif op == "!=":
        return actual != expected
    return False


def _coerce_output(output, stdout):
    """Normalize parsed JSON into a result dict with a success flag."""
    if isinstance(output, dict):
        if "success" not in output:
            output["success"] = True
        return output.get("success", True), output
    return True, {"success": True, "stdout": stdout, "json_output": output}


def _run_subprocess(command):
    """Run a subprocess and return (success, output_dict)."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=3600,
            check=False,
        )
        if result.returncode != 0:
            return False, {"error": result.stderr.strip() or f"exit code {result.returncode}"}

        stdout_stripped = result.stdout.strip()
        if not stdout_stripped:
            return True, {"success": True, "stdout": result.stdout}

        try:
            output = json.loads(stdout_stripped)
        except json.JSONDecodeError:
            lines = stdout_stripped.split("\n")
            try:
                output = json.loads(lines[-1])
            except json.JSONDecodeError:
                return True, {"success": True, "stdout": result.stdout}
        return _coerce_output(output, result.stdout)
    except subprocess.TimeoutExpired:
        return False, {"error": "subprocess timed out"}
    except (subprocess.SubprocessError, OSError, ValueError, TypeError) as exc:
        return False, {"error": str(exc)}


def _read_checkpoint_response(stdin_input):
    """Read a checkpoint response from stdin. Returns 'resume', 'skip', or None."""
    if stdin_input is None:
        line = sys.stdin.readline()
    else:
        line = stdin_input.readline()
    if not line:
        return None
    try:
        data = json.loads(line.strip())
        action = data.get("action", "").lower()
        if action in ("resume", "skip"):
            return action
    except (json.JSONDecodeError, AttributeError):
        pass
    return None


def execute(plan, dry_run=False, stdin_input=None, state=None):
    """Execute a plan and yield JSONL events.

    Args:
        plan: Plan dict with plan_id, workflow, request, steps.
        dry_run: If True, print commands without executing.
        stdin_input: File-like object for checkpoint responses. If None, reads from sys.stdin.
        state: Optional saved state dict for resuming a plan.

    Yields:
        Event dicts (plan_started, step_started, step_done, step_skipped,
        step_failed, checkpoint, plan_done).
    """
    plan_id = plan.get("plan_id", "unknown")
    workflow = plan.get("workflow", "unknown")
    steps = plan.get("steps", [])

    yield {"event": "plan_started", "plan_id": plan_id, "workflow": workflow, "step_count": len(steps)}

    ordered_steps = topological_sort(steps)
    step_outputs = {}
    skipped_steps = set()
    if state:
        for k, v in state.get("step_outputs", {}).items():
            if isinstance(v, dict) and v.get("success") is True:
                step_outputs[k] = v
        skipped_steps = set(state.get("skipped_steps", []))
    completed = 0
    skipped = 0
    failed = 0

    for step in ordered_steps:
        name = step["name"]
        output_key = step.get("output_key", name)
        if output_key in step_outputs:
            completed += 1
            yield {"event": "step_done", "step": name, "success": True, "output": step_outputs[output_key], "resumed": True}
            continue
        if name in skipped_steps:
            skipped += 1
            yield {"event": "step_skipped", "step": name, "reason": "resumed"}
            continue
        condition = step.get("condition")
        checkpoint = step.get("checkpoint", False)
        retry = step.get("retry", {"max_attempts": 1, "delay_seconds": 0})
        max_attempts = retry.get("max_attempts", 1)
        delay = retry.get("delay_seconds", 0)

        # Check if any dependency was skipped or failed
        deps = step.get("depends_on", [])
        dep_failed = any(d in skipped_steps or not step_outputs.get(d, {}).get("success") for d in deps)
        if dep_failed:
            yield {"event": "step_skipped", "step": name, "reason": "dependency failed or skipped"}
            skipped += 1
            skipped_steps.add(name)
            continue

        # Evaluate condition
        if not evaluate_condition(condition, step_outputs):
            yield {"event": "step_skipped", "step": name, "reason": "condition not met"}
            skipped += 1
            skipped_steps.add(name)
            continue

        # Checkpoint handling
        if checkpoint:
            yield {"event": "checkpoint", "step": name, "message": f"Review step '{name}' before proceeding. Send 'resume' to continue or 'skip' to skip."}
            action = _read_checkpoint_response(stdin_input)
            if action == "skip":
                yield {"event": "step_skipped", "step": name, "reason": "user skipped at checkpoint"}
                skipped += 1
                skipped_steps.add(name)
                continue
            elif action is None:
                yield {"event": "step_skipped", "step": name, "reason": "checkpoint timeout"}
                skipped += 1
                skipped_steps.add(name)
                continue

        # Resolve placeholders in command
        command = resolve_placeholders(step["command"], step_outputs, plan.get("params", {}))

        yield {"event": "step_started", "step": name, "skill": step.get("skill", "")}

        if dry_run:
            yield {
                "event": "step_done",
                "step": name,
                "success": True,
                "output": {"dry_run": True, "command": command},
            }
            step_outputs[step.get("output_key", name)] = {"success": True, "dry_run": True}
            completed += 1
            continue

        # Execute with retry
        attempts = 0
        success = False
        output = {}
        for attempt in range(max_attempts):
            attempts = attempt + 1
            success, output = _run_subprocess(command)
            if success:
                break
            if attempt < max_attempts - 1 and delay > 0:
                time.sleep(delay)

        if success:
            yield {"event": "step_done", "step": name, "success": True, "output": output}
            step_outputs[step.get("output_key", name)] = output
            completed += 1
        else:
            yield {"event": "step_failed", "step": name, "error": output.get("error", "unknown"), "attempts": attempts}
            step_outputs[step.get("output_key", name)] = {"success": False, "error": output.get("error")}
            failed += 1
            skipped_steps.add(name)

        # Save state after each step
        try:
            save_state(plan_id, {
                "plan_id": plan_id,
                "completed_steps": list(step_outputs.keys()),
                "step_outputs": step_outputs,
                "skipped_steps": list(skipped_steps),
            })
        except (OSError, TypeError, ValueError) as exc:
            logging.getLogger(__name__).warning("Failed to save state for %s: %s", plan_id, exc)

    yield {
        "event": "plan_done",
        "plan_id": plan_id,
        "success": failed == 0,
        "steps_completed": completed,
        "steps_skipped": skipped,
        "steps_failed": failed,
    }
