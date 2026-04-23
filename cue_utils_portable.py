#!/usr/bin/env python3
"""
CueAPI Coordination Utility — Portable version for any agent setup.

Drop this file into any agent's working directory. It handles:
- Agent-to-agent messaging (PATCH+fire pattern)
- Email to human (via shared bridge)
- Outcome reporting
- Execution heartbeats

Setup:
    1. Set CUEAPI_API_KEY env var (or pass to constructor)
    2. Load your coordination config (cue registry, tenant ID)
    3. Use the client

Usage:
    from cue_utils_portable import CueClient

    cue = CueClient(
        agent_name="my-agent",
        config={
            "cueapi_key": "cue_sk_...",
            "bridge_url": "https://cueapi-bridge-production.up.railway.app",
            "bridge_tenant_id": "tn_...",
            "agents": {
                "agent-a": {"cue_id": "cue_XXX", "task": "notify-agent-a"},
                "agent-b": {"cue_id": "cue_YYY", "task": "notify-agent-b"},
                "human":   {"cue_id": "cue_ZZZ", "task": "notify-human", "email": "you@email.com"},
            }
        }
    )

    # Send message to another agent
    cue.send("agent-b", "Please review the draft in the Dock workspace")

    # Send message with custom payload fields
    cue.send("agent-b", "Enrich this workspace", type="action", priority=8,
             workspace_slug="my-workspace")

    # Email the human
    cue.email_human(
        subject="Draft ready for review",
        body="<p>The draft is ready. Please review on Dock.</p>",
        approve_context={
            "workspace_slug": "my-workspace",
            "callback_cue": "cue_YYY",  # fires agent-b on approve
        }
    )

    # Report outcome (in a handler)
    cue.report_outcome(success=True, result="Task completed")
"""

import json
import os
import sys
import time

try:
    import httpx
    _http = "httpx"
except ImportError:
    import urllib.request
    import urllib.error
    _http = "urllib"


class CueError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class CueClient:
    def __init__(self, agent_name="agent", config=None, config_path=None):
        self.agent_name = agent_name

        # Load config
        if config:
            self._config = config
        elif config_path:
            with open(config_path) as f:
                self._config = json.load(f)
        elif os.path.exists("coordination-config.json"):
            with open("coordination-config.json") as f:
                self._config = json.load(f)
        else:
            self._config = {}

        self.api_key = (
            self._config.get("cueapi_key")
            or os.environ.get("CUEAPI_API_KEY")
            or os.environ.get("CUEAPI_KEY")
        )
        if not self.api_key:
            raise CueError("No CueAPI key. Set CUEAPI_API_KEY or include cueapi_key in config.")

        self.base_url = self._config.get("cueapi_base", "https://api.cueapi.ai/v1")
        self.bridge_url = self._config.get("bridge_url", "https://cueapi-bridge-production.up.railway.app")
        self.bridge_tenant_id = self._config.get("bridge_tenant_id")
        self.agents = self._config.get("agents", {})

    # --- HTTP helpers (works with httpx or stdlib) ---

    def _request(self, method, url, json_data=None, headers=None):
        hdrs = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if headers:
            hdrs.update(headers)

        if _http == "httpx":
            resp = httpx.request(method, url, json=json_data, headers=hdrs, timeout=30)
            return resp.status_code, resp.text, resp.json() if resp.headers.get("content-type", "").startswith("application/json") else None
        else:
            data = json.dumps(json_data).encode() if json_data else None
            req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
            try:
                resp = urllib.request.urlopen(req, timeout=30)
                body = resp.read().decode()
                try:
                    return resp.status, body, json.loads(body)
                except json.JSONDecodeError:
                    return resp.status, body, None
            except urllib.error.HTTPError as e:
                body = e.read().decode() if e.fp else ""
                return e.code, body, None

    def _api(self, method, path, json_data=None):
        return self._request(method, f"{self.base_url}{path}", json_data)

    # --- Core: Send message to an agent ---

    def send(self, target, instructions, **extra):
        """
        Send a message to another agent.

        Args:
            target: Agent name from the config (e.g., "agent-b") or a raw cue ID
            instructions: The message/instructions to send
            **extra: Additional payload fields (type, priority, workspace_slug, etc.)
        """
        # Resolve target
        if target in self.agents:
            agent_info = self.agents[target]
            cue_id = agent_info["cue_id"]
            task = agent_info.get("task", f"notify-{target}")
        elif target.startswith("cue_"):
            cue_id = target
            task = extra.pop("task", "agent-task")
        else:
            raise CueError(f"Unknown target: '{target}'. Known agents: {list(self.agents.keys())}")

        payload = {
            "task": task,
            "type": extra.pop("type", "message"),
            "from": self.agent_name,
            "priority": extra.pop("priority", 5),
            "instructions": instructions,
        }
        payload.update(extra)

        return self._fire(cue_id, payload)

    def _fire(self, cue_id, payload):
        """PATCH+fire pattern."""
        # Step 1: PATCH
        status, body, data = self._api("PATCH", f"/cues/{cue_id}", {"payload": payload})
        if status != 200:
            raise CueError(f"PATCH failed ({status}): {body[:300]}", status)

        # Step 2: Fire
        status, body, data = self._api("POST", f"/cues/{cue_id}/fire", {})
        if status != 200:
            raise CueError(f"Fire failed ({status}): {body[:300]}", status)

        exec_id = data.get("id") if data else None
        return exec_id

    # --- Email the human ---

    def email_human(self, subject, body, to=None, approve_context=None):
        """
        Send an email to the human via the bridge.
        No SMTP, no Resend key needed — the bridge handles everything.
        """
        # Resolve email
        if not to:
            human_config = self.agents.get("human", {})
            to = human_config.get("email")
        if not to:
            raise CueError("No email address. Set 'email' in agents.human config or pass 'to'.")

        payload = {
            "tenant_id": self.bridge_tenant_id or "_legacy",
            "to": to,
            "subject": subject,
            "body": body,
            "from_agent": self.agent_name,
        }
        if approve_context:
            payload["approve_context"] = approve_context

        status, resp_body, data = self._request(
            "POST", f"{self.bridge_url}/email", payload,
            headers={"Authorization": ""}  # bridge doesn't need CueAPI auth
        )

        if status != 200:
            raise CueError(f"Email failed ({status}): {resp_body[:300]}", status)

        return data

    # --- Outcome reporting ---

    def report_outcome(self, execution_id=None, success=True, result=None, error=None):
        """Report outcome for the current execution."""
        execution_id = execution_id or os.environ.get("CUEAPI_EXECUTION_ID")
        if not execution_id:
            return  # Not in a handler context, skip silently

        outcome = {"success": success}
        if result:
            outcome["result"] = str(result)[:2000]
        if error:
            outcome["error"] = str(error)[:2000]

        # Write to outcome file if available
        outcome_file = os.environ.get("CUEAPI_OUTCOME_FILE")
        if outcome_file:
            try:
                with open(outcome_file, "w") as f:
                    json.dump(outcome, f)
            except Exception:
                pass

        # Report via API
        try:
            self._api("POST", f"/executions/{execution_id}/outcome", outcome)
        except Exception as e:
            print(f"[cue_utils] outcome report failed: {e}", file=sys.stderr)

    # --- Heartbeat ---

    def heartbeat(self, execution_id=None):
        """Send heartbeat to extend claim lease during long work."""
        execution_id = execution_id or os.environ.get("CUEAPI_EXECUTION_ID")
        if not execution_id:
            return False
        status, _, _ = self._api("POST", f"/executions/{execution_id}/heartbeat", {})
        return status in (200, 204)

    # --- Execution status ---

    def get_execution(self, execution_id):
        """Check execution status."""
        status, body, data = self._api("GET", f"/executions/{execution_id}")
        if status != 200:
            raise CueError(f"Get execution failed ({status})", status)
        return data

    def wait_for(self, execution_id, timeout=120, poll_interval=5):
        """Poll until execution completes."""
        start = time.time()
        while time.time() - start < timeout:
            ex = self.get_execution(execution_id)
            if ex.get("status") in ("success", "failed", "timeout"):
                return ex
            time.sleep(poll_interval)
        raise CueError(f"Execution did not complete in {timeout}s")


# --- CLI ---

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CueAPI coordination utility")
    sub = parser.add_subparsers(dest="cmd")

    s = sub.add_parser("send", help="Send message to agent")
    s.add_argument("target", help="Agent name or cue ID")
    s.add_argument("message", help="Message text")

    e = sub.add_parser("email", help="Email the human")
    e.add_argument("--to", help="Email address")
    e.add_argument("--subject", required=True)
    e.add_argument("--body", required=True)

    sub.add_parser("config", help="Show loaded config")

    args = parser.parse_args()
    cue = CueClient(agent_name="cli")

    if args.cmd == "send":
        eid = cue.send(args.target, args.message)
        print(f"Sent: {eid}")
    elif args.cmd == "email":
        r = cue.email_human(args.subject, args.body, to=args.to)
        print(f"Email sent: {r}")
    elif args.cmd == "config":
        print(json.dumps(cue._config, indent=2))
    else:
        parser.print_help()
