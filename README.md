# Multi-Agent Coordination Guide
## Connect Your AI Agents So They Can Work Together

*Version 1.1 — April 2026*
*Written for agents to execute. Humans: read the overview, then hand this to your orchestrator agent.*

---

## For the Human (Read This First — 3 Minutes)

### What This Guide Does

You have multiple AI agents — maybe Claude Code for building, Claude Desktop (Cowork) for research, OpenClaw for orchestration, or something else. Right now they're islands. They can't talk to each other, share work, or coordinate on anything.

This guide sets up:
1. **Agent-to-agent messaging** — your agents can send each other tasks and results
2. **A shared workspace** — all agents read from and write to the same data (Dock)
3. **Human-in-the-loop** — agents email you when they need your input, with one-click approve/reject buttons
4. **A working pipeline** — a sample workflow where agents collaborate on a task end-to-end

### What You'll Need to Do

Your orchestrator agent will drive the setup. You'll be asked to:
- **Create accounts** (CueAPI + Dock) — if your agent can't do it via CLI
- **Copy-paste between agents** — until the messaging infrastructure is up, your agents can't talk to each other yet, so you're the bridge
- **Approve things** — your agent will ask before making irreversible changes
- **Test** — click buttons, check emails, confirm things work

Estimated time: **1-2 hours** for a 2-agent setup on one machine, **2-3 hours** for 3+ agents across machines.

### What You Won't Need to Do

- Set up email servers, databases, or hosting
- Write code
- Configure DNS, SSL, or networking
- Understand the technical details (your agent handles that)

### How to Start

Pick your **orchestrator agent** — the one with the most capabilities (shell access, API access, file access). Then tell it:

> "Read this guide and set up coordination between my agents. Here it is: [paste this guide or give it the file path]"

The orchestrator will ask you questions, then drive the setup.

---

## For the Orchestrator Agent (The Rest of This Guide)

You are the primary agent driving this setup. You'll configure the infrastructure, instruct other agents, and coordinate with the human for tasks only they can do.

**Read this entire guide before starting.** Then execute phase by phase.

### Important: The Bootstrap Problem

Before CueAPI is set up, your agents can't talk to each other. That means:
- **You** handle everything you can reach directly (your machine, APIs)
- **The human** is the bridge for everything else (copying config to agents on other machines, creating web accounts)
- Once messaging is wired, you can communicate with other agents directly

Every time you need the human to do something, give them **exact instructions** they can copy-paste. Don't assume they know the technical details.

---

## Phase 0: Discovery

Before setting anything up, understand the topology.

### Ask the human these questions:

```
I need to understand your agent setup to configure coordination. Please answer:

1. What agents do you have? For each one:
   - Name/label (e.g., "Claude Code", "Cowork", "Max")
   - What platform? (OpenClaw, Claude Desktop, Claude Code CLI, Cursor, etc.)
   - What machine is it on? (same machine as me, or a different one?)
   - Can it run shell commands? (yes/no)
   - Can it make HTTP API calls? (yes/no)
   - Can it read/write files on disk? (yes/no)

2. Are all your agents on one machine, or spread across multiple machines?

3. What do you want them to do together? 
   (Examples: code review pipeline, content creation, research → writing → publishing)

4. What's your email address? (For approve/reject notifications)
```

### Map the topology

From the human's answers, build a topology map:

```
TOPOLOGY:
- Machine: [machine-1]
  Agents:
    - Name: [name], Platform: [platform], Shell: yes/no, API: yes/no, Files: yes/no, Role: orchestrator
    - Name: [name], Platform: [platform], Shell: yes/no, API: yes/no, Files: yes/no, Role: worker

- Machine: [machine-2]  (if applicable)
  Agents:
    - Name: [name], ...

SINGLE MACHINE: [yes/no]
PIPELINE GOAL: [what they want agents to do together]
HUMAN EMAIL: [email]
ORCHESTRATOR: [which agent — that's you]
```

Save this topology. You'll reference it throughout setup.

### Single Machine vs Multi-Machine

**Single machine (all agents on one computer):**
- Simpler setup — one worker daemon, all handlers on the same machine
- Agents can share files directly (no copy-paste through human)
- The orchestrator can write config files for other agents directly
- Still need CueAPI for coordination (agents can't call each other directly)

**Multi-machine (agents on different computers):**
- One worker daemon PER machine
- The human must copy-paste configuration to agents on other machines (until messaging is set up)
- Each machine needs the CueAPI API key, handler scripts, and worker config
- More verification steps needed

### Determine what each agent needs

Based on capabilities:

| Agent Can... | They Set Up... | Human Does... |
|---|---|---|
| Run shell + make API calls | Everything themselves | Nothing (just approves) |
| Make API calls only | CueAPI registration, handler config | Installs worker daemon |
| Read/write files only | Handler scripts, config files | Installs software, runs commands |
| Chat only (no tools) | Nothing | Everything, guided by the agent's instructions |

---

## Phase 1: Accounts & Infrastructure

### Step 1.1: CueAPI Account

CueAPI is the coordination layer — it routes messages between agents.

**If the orchestrator agent has shell access:**

```bash
# Install CueAPI worker (includes the CLI)
pip install cueapi-worker

# Create account (interactive — may need human for email verification)
# If this doesn't work, have the human create the account via web UI
```

**If the orchestrator agent does NOT have shell access, tell the human:**

```
I need you to create a CueAPI account:
1. Go to https://cueapi.ai and sign up
2. Go to Settings → API Keys
3. Copy your API key (starts with cue_sk_)
4. Paste it back to me here

This takes about 2 minutes.
```

**Once you have the API key, verify it works:**

```bash
curl -s "https://api.cueapi.ai/v1/cues" \
  -H "Authorization: Bearer YOUR_CUEAPI_KEY" | head -5
```

Expected: JSON response (empty `cues` array is fine for a new account).

**Save the API key securely.** All agents share one key (per-agent keys are a future feature).

### Step 1.2: Dock Account

Dock is the shared workspace — agents read and write structured data here.

Dock account creation currently requires the web UI. **Tell the human:**

```
I need you to create a Dock account:
1. Go to https://trydock.ai and sign up
2. Go to Settings → API Keys → Create Key
3. Copy the key (starts with dk_)
4. Paste it back to me here

This takes about 2 minutes.
```

**Verify the Dock key:**

```bash
curl -s "https://trydock.ai/api/workspaces" \
  -H "Authorization: Bearer YOUR_DOCK_KEY" | head -5
```

Expected: JSON response (empty workspaces list is fine).

### Step 1.3: Register with the Approval Bridge

The approval bridge lets agents email the human with one-click approve/reject buttons. It's a shared service — no setup on your end.

```bash
curl -s -X POST "https://cueapi-bridge-production.up.railway.app/tenants" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "HUMAN_NAME",
    "email": "HUMAN_EMAIL",
    "cueapi_key": "YOUR_CUEAPI_KEY"
  }'
```

This returns:
```json
{
  "tenant_id": "tn_...",
  "hmac_secret": "...",
  "message": "Registered."
}
```

**Save `tenant_id`** — use this in all bridge API calls.
**Save `hmac_secret`** — store securely. The bridge uses it internally for signing approval URLs.

### Step 1.4: Install CueAPI Worker Daemon

The worker daemon runs on each machine that has agents. It polls CueAPI for tasks and routes them to handler scripts.

**How many workers do you need?**
- **Single machine:** One worker daemon
- **Multi-machine:** One worker daemon per machine

**Install and configure the worker (run on each machine):**

```bash
# Install (requires Python 3.9+)
pip install cueapi-worker

# Create the worker config file
cat > cueapi-worker.yaml << 'EOF'
worker_id: "MACHINE_NAME"    # unique name for this machine (e.g., "mikes-macbook")
poll_interval: 5              # seconds between polls
heartbeat_interval: 30        # seconds between heartbeats
max_concurrent: 2             # max simultaneous handler executions

handlers:
  # Handlers will be added in Phase 2
  # Starting with a ping test to verify the worker works
  ping-test:
    cmd: "echo pong"
    timeout: 10
EOF

# Install as a system service (auto-starts on boot)
# Works on macOS (launchd) and Linux (systemd)
python -m cueapi_worker.cli install-service --config /absolute/path/to/cueapi-worker.yaml

# OR run directly for testing (foreground, Ctrl+C to stop)
python -m cueapi_worker.cli start --config cueapi-worker.yaml
```

**⚠️ IMPORTANT: Use absolute paths.** The service manager (launchd/systemd) doesn't inherit your shell's working directory or PATH. The config path in `install-service` must be absolute.

**If the orchestrator can't install on another machine,** tell the human:

```
I need the CueAPI worker daemon installed on [MACHINE_NAME]. 
Please run these commands on that machine:

pip install cueapi-worker

Then paste this config file and save it as cueapi-worker.yaml:

---
[PASTE THE FULL YAML HERE]
---

Then run:
python -m cueapi_worker.cli install-service --config /full/path/to/cueapi-worker.yaml

Tell me when it's running.
```

### Step 1.5: Verify Worker is Running

```bash
# Check process
ps aux | grep cueapi | grep -v grep

# Check logs (macOS)
tail -20 ~/Library/Logs/cueapi-worker/stderr.log

# Check logs (Linux)
journalctl -u cueapi-worker --no-pager -n 20
```

The worker should show in logs:
```
CueAPI Worker v0.2.0
  Worker ID:    MACHINE_NAME
  Handlers:     ping-test
  Poll interval: 5s
```

If the worker isn't running:
```bash
# macOS — restart
launchctl kickstart -k gui/$(id -u)/ai.cueapi.worker

# Linux — restart
sudo systemctl restart cueapi-worker
```

---

## Phase 2: Create Cues & Wire Handlers

### Understanding the Pattern

Each agent-to-agent route needs:
1. **A cue** in CueAPI — the address (like a phone number)
2. **A handler script** on the receiving machine — what happens when a message arrives

For N agents + 1 human, you need N+1 cues:
- One "inbox" cue per agent
- One "notify-human" cue for emailing the human

### Step 2.1: Create Cues

```bash
CUEAPI_KEY="YOUR_KEY"
CUEAPI_BASE="https://api.cueapi.ai/v1"

# Create a cue for each agent (repeat for each agent)
curl -s -X POST "$CUEAPI_BASE/cues" \
  -H "Authorization: Bearer $CUEAPI_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "notify-AGENT_NAME",
    "transport": "worker",
    "schedule": {"type": "once", "at": "2099-01-01T00:00:00Z"},
    "delivery": {"outcome_deadline_seconds": 120},
    "alerts": {"consecutive_failures": 1}
  }'

# Create the notify-human cue (for emails)
curl -s -X POST "$CUEAPI_BASE/cues" \
  -H "Authorization: Bearer $CUEAPI_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "notify-human",
    "transport": "worker",
    "schedule": {"type": "once", "at": "2099-01-01T00:00:00Z"},
    "delivery": {"outcome_deadline_seconds": 60},
    "alerts": {"consecutive_failures": 1}
  }'
```

**Note:** The `schedule` is set to 2099 as a workaround — CueAPI requires a schedule, but we only fire manually. A `manual` schedule type is coming.

**Record EVERY cue ID.** Build your registry:

```
CUE REGISTRY:
- notify-[agent-a]:  cue_XXXXX
- notify-[agent-b]:  cue_YYYYY
- notify-[agent-c]:  cue_ZZZZZ  (if applicable)
- notify-human:      cue_HHHHH
```

### Step 2.2: Create Handler Scripts

Each agent needs a handler script. Choose the template matching each agent's platform.

**⚠️ CRITICAL ROUTING RULE:** The worker routes by the **`task` field in the payload**, NOT the cue name. Every message payload MUST include a `task` field matching the handler name in the worker yaml. Without it, the execution sits unclaimed forever with **zero error messages**. This is the #1 debugging headache.

#### Choose your handler template:

**OpenClaw agent** — triggers a full agent turn with tools:

```python
#!/usr/bin/env python3
"""CueAPI handler for OpenClaw agents."""
import json, os, subprocess, sys

def main():
    payload = json.loads(os.environ.get("CUEAPI_PAYLOAD", "{}"))
    execution_id = os.environ.get("CUEAPI_EXECUTION_ID")

    instruction = payload.get("instructions") or payload.get("instruction", "")
    channel = payload.get("channel", "webchat")
    thinking = payload.get("thinking", "low")
    timeout = str(payload.get("timeout", 300))

    # UPDATE THIS PATH to your openclaw binary
    openclaw = "/absolute/path/to/openclaw"

    cmd = [openclaw, "agent", "--agent", "main", "-m", instruction,
           "--deliver", "--channel", channel, "--thinking", thinking, "--timeout", timeout]

    print(f"Triggering agent turn: {instruction[:100]}...", flush=True)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=int(timeout) + 30)
        success = result.returncode == 0
        report_outcome(execution_id, success,
                       result=result.stdout[:500] if success else None,
                       error=result.stderr[:500] if not success else None)
        if not success:
            sys.exit(1)
    except subprocess.TimeoutExpired:
        report_outcome(execution_id, False, error=f"Timeout after {timeout}s")
        sys.exit(1)

def report_outcome(eid, success, result=None, error=None):
    if not eid: return
    try:
        import httpx
        httpx.post(f"https://api.cueapi.ai/v1/executions/{eid}/outcome",
                   headers={"Authorization": f"Bearer {os.environ.get('CUEAPI_API_KEY', '')}"},
                   json={"success": success, "result": (result or "")[:2000], "error": (error or "")[:2000]},
                   timeout=10)
    except Exception as e:
        print(f"Outcome report failed: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
```

**Claude Code agent** — one-shot CLI, with reply-back pattern:

```python
#!/usr/bin/env python3
"""CueAPI handler for Claude Code CLI."""
import json, os, subprocess, sys

def main():
    payload = json.loads(os.environ.get("CUEAPI_PAYLOAD", "{}"))
    execution_id = os.environ.get("CUEAPI_EXECUTION_ID")
    api_key = os.environ.get("CUEAPI_API_KEY", "")

    instruction = payload.get("instruction", "")
    reply_cue_id = payload.get("reply_cue_id")
    cwd = payload.get("cwd", os.getcwd())

    if reply_cue_id:
        instruction += ('\n\nAfter completing the task, emit a final line to stdout in this exact '
                        'JSON format: {"reply": "your summary", "status": "ok"}')

    # UPDATE THIS PATH to your claude binary
    claude = "/absolute/path/to/claude"

    env = os.environ.copy()
    env["PATH"] = f"/usr/local/bin:/usr/bin:/opt/homebrew/bin:{env.get('PATH', '')}"

    print(f"Running Claude Code: {instruction[:100]}...", flush=True)
    result = subprocess.run([claude, "-p", instruction, "--dangerously-skip-permissions"],
                            capture_output=True, text=True, cwd=cwd, env=env, timeout=300)

    reply = None
    if result.returncode == 0 and reply_cue_id:
        for line in reversed(result.stdout.strip().split('\n')):
            try:
                data = json.loads(line)
                if "reply" in data:
                    reply = data["reply"]
                    break
            except json.JSONDecodeError:
                continue
        if reply:
            fire_reply(reply_cue_id, reply, api_key)

    report_outcome(execution_id, result.returncode == 0,
                   result=(reply or result.stdout[:500]),
                   error=result.stderr[:500] if result.returncode != 0 else None)

def fire_reply(cue_id, reply, api_key):
    try:
        import httpx
        base = "https://api.cueapi.ai/v1"
        h = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        httpx.patch(f"{base}/cues/{cue_id}", headers=h, json={
            "payload": {"task": "agent-task", "instruction": reply,
                        "channel": "webchat", "thinking": "low", "timeout": 120}
        }, timeout=10)
        httpx.post(f"{base}/cues/{cue_id}/fire", headers=h, json={}, timeout=10)
    except Exception as e:
        print(f"Reply fire failed: {e}", file=sys.stderr)

def report_outcome(eid, success, result=None, error=None):
    if not eid: return
    try:
        import httpx
        httpx.post(f"https://api.cueapi.ai/v1/executions/{eid}/outcome",
                   headers={"Authorization": f"Bearer {os.environ.get('CUEAPI_API_KEY', '')}"},
                   json={"success": success, "result": (result or "")[:2000], "error": (error or "")[:2000]},
                   timeout=10)
    except Exception as e:
        print(f"Outcome report failed: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
```

**Claude Desktop / Cowork** — inbox file pattern (sandboxed agent, no shell access):

```python
#!/usr/bin/env python3
"""CueAPI handler for Claude Desktop — writes JSON to inbox directory."""
import json, os, sys
from datetime import datetime

def main():
    payload = json.loads(os.environ.get("CUEAPI_PAYLOAD", "{}"))
    execution_id = os.environ.get("CUEAPI_EXECUTION_ID")

    # UPDATE THIS PATH to your Claude Desktop's inbox directory
    inbox_dir = os.environ.get("COWORK_INBOX",
                                os.path.expanduser("~/Desktop/workspace/inbox"))
    os.makedirs(inbox_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    msg_type = payload.get("type", "message")
    filename = f"{timestamp}_{msg_type}.json"
    filepath = os.path.join(inbox_dir, filename)

    payload["_execution_id"] = execution_id
    with open(filepath, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Written to {filepath} (type={msg_type}, priority={payload.get('priority', 5)})")
    report_outcome(execution_id, True, f"Message written to {filepath}")

def report_outcome(eid, success, result=None):
    if not eid: return
    try:
        import httpx
        httpx.post(f"https://api.cueapi.ai/v1/executions/{eid}/outcome",
                   headers={"Authorization": f"Bearer {os.environ.get('CUEAPI_API_KEY', '')}"},
                   json={"success": success, "result": (result or "")[:2000]}, timeout=10)
    except Exception as e:
        print(f"Outcome report failed: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
```

**Important for Claude Desktop users:** The agent needs to know about its inbox. Give it these instructions (paste this to the agent or add it to its system prompt / project knowledge):

```
You have an inbox directory at [INBOX_PATH].
Check it every 1-2 minutes for new .json files.
Each file contains a message from another agent with these fields:
  - "from": who sent it
  - "type": message, action, review, or enrich
  - "priority": 1-10 (process highest first)
  - "instructions": what to do

After processing, move the file to inbox-processed/.

To REPLY to other agents, use the CueAPI REST API:
  Step 1: PATCH the target cue's payload
  Step 2: Fire the cue
  See coordination-config.json for cue IDs and the API key.

CRITICAL: Always include "task": "HANDLER_NAME" in the payload.
Without it, the receiving worker silently drops the message.
```

**Notify-Human handler** — emails the human via the shared bridge (works for any setup):

```python
#!/usr/bin/env python3
"""CueAPI handler — sends email to human via bridge. No SMTP needed."""
import json, os, sys, urllib.request

BRIDGE_URL = "https://cueapi-bridge-production.up.railway.app"

def main():
    payload = json.loads(os.environ.get("CUEAPI_PAYLOAD", "{}"))
    execution_id = os.environ.get("CUEAPI_EXECUTION_ID")

    body = json.dumps({
        "tenant_id": os.environ.get("BRIDGE_TENANT_ID", ""),
        "to": payload.get("to", os.environ.get("HUMAN_EMAIL", "")),
        "subject": payload.get("subject", "Agent Notification"),
        "body": payload.get("body", ""),
        "from_agent": payload.get("from_agent", "Agent"),
        "approve_context": payload.get("approve_context"),
    }).encode()

    req = urllib.request.Request(f"{BRIDGE_URL}/email", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    resp = urllib.request.urlopen(req, timeout=15)
    result = json.loads(resp.read().decode())
    print(f"Email sent: {result}")

    # Report outcome
    if execution_id:
        try:
            import httpx
            httpx.post(f"https://api.cueapi.ai/v1/executions/{execution_id}/outcome",
                       headers={"Authorization": f"Bearer {os.environ.get('CUEAPI_API_KEY', '')}"},
                       json={"success": True, "result": f"Email sent: {payload.get('subject','')}"[:2000]},
                       timeout=10)
        except: pass

if __name__ == "__main__":
    main()
```

### Step 2.3: Update Worker Config

Add your handlers to `cueapi-worker.yaml` on each machine. **Handler names MUST match the `task` field that other agents will put in their payloads.**

Example for a machine with an OpenClaw agent + notify-human:

```yaml
worker_id: "machine-1"
poll_interval: 5
heartbeat_interval: 30
max_concurrent: 2

handlers:
  agent-task:
    cmd: "/absolute/path/to/python3 /absolute/path/to/handler_openclaw.py"
    cwd: "/absolute/path/to/workspace"
    timeout: 360

  notify-human:
    cmd: "/absolute/path/to/python3 /absolute/path/to/handler_notify_human.py"
    cwd: "/absolute/path/to/workspace"
    timeout: 30
    env:
      BRIDGE_TENANT_ID: "tn_your_tenant_id"
      HUMAN_EMAIL: "you@email.com"
```

Example for a machine with Claude Code + Claude Desktop:

```yaml
worker_id: "machine-2"
poll_interval: 5
heartbeat_interval: 30
max_concurrent: 2

handlers:
  code-build:
    cmd: "/absolute/path/to/python3 /absolute/path/to/handler_claude_code.py"
    cwd: "/absolute/path/to/project"
    timeout: 300
    env:
      PATH: "/usr/local/bin:/usr/bin:/home/user/.local/bin"

  cowork-task:
    cmd: "/absolute/path/to/python3 /absolute/path/to/handler_cowork.py"
    cwd: "/absolute/path/to/workspace"
    timeout: 120
    env:
      COWORK_INBOX: "/absolute/path/to/inbox"
```

**Restart the worker after any config change:**

```bash
# macOS
launchctl kickstart -k gui/$(id -u)/ai.cueapi.worker

# Linux
sudo systemctl restart cueapi-worker
```

**For multi-machine setups:** You need to get the handler scripts and worker config onto each machine. If the orchestrator can't reach the other machine, tell the human:

```
I need you to set up the worker on [MACHINE_NAME].

1. Save this file as handler_[agent].py:
---
[PASTE FULL HANDLER SCRIPT]
---

2. Save this file as handler_notify_human.py:
---
[PASTE FULL HANDLER SCRIPT]
---

3. Update cueapi-worker.yaml to add these handlers:
---
[PASTE YAML SNIPPET]
---

4. Restart the worker:
   macOS: launchctl kickstart -k gui/$(id -u)/ai.cueapi.worker
   Linux: sudo systemctl restart cueapi-worker

Tell me when it's done and I'll verify.
```

---

## Phase 3: Connect & Configure

### Step 3.1: The PATCH+Fire Pattern

To send a message to another agent:

```bash
CUEAPI_KEY="YOUR_KEY"
TARGET_CUE="cue_XXXXX"

# Step 1: Set the payload (PATCH)
curl -s -X PATCH "https://api.cueapi.ai/v1/cues/$TARGET_CUE" \
  -H "Authorization: Bearer $CUEAPI_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "task": "HANDLER_NAME",
      "type": "message",
      "from": "Your Agent Name",
      "priority": 5,
      "instructions": "Your message here"
    }
  }'

# Step 2: Fire
curl -s -X POST "https://api.cueapi.ai/v1/cues/$TARGET_CUE/fire" \
  -H "Authorization: Bearer $CUEAPI_KEY" \
  -H "Content-Type: application/json" -d '{}'
```

**Two calls per message.** CueAPI doesn't support payload override at fire time yet. The cue's stored payload is overwritten with each PATCH. (Fire-with-payload is coming.)

### Step 3.2: Create the Coordination Config

Create `coordination-config.json` — the single source of truth for all agents:

```json
{
  "cueapi_key": "cue_sk_...",
  "cueapi_base": "https://api.cueapi.ai/v1",
  "bridge_url": "https://cueapi-bridge-production.up.railway.app",
  "bridge_tenant_id": "tn_...",
  "human_email": "you@email.com",
  "agents": {
    "orchestrator": {
      "cue_id": "cue_XXXXX",
      "task": "agent-task",
      "platform": "openclaw",
      "machine": "machine-1"
    },
    "builder": {
      "cue_id": "cue_YYYYY",
      "task": "code-build",
      "platform": "claude-code",
      "machine": "machine-1"
    },
    "researcher": {
      "cue_id": "cue_ZZZZZ",
      "task": "cowork-task",
      "platform": "claude-desktop",
      "machine": "machine-1"
    },
    "human": {
      "cue_id": "cue_HHHHH",
      "task": "notify-human",
      "email": "you@email.com",
      "machine": "machine-1"
    }
  }
}
```

### Step 3.3: Install the Coordination Utility

Save `cue_utils_portable.py` (included with this guide) in each agent's working directory alongside `coordination-config.json`. It provides a clean Python API:

```python
from cue_utils_portable import CueClient
cue = CueClient(agent_name="my-agent")

# Send a message to another agent
cue.send("builder", "Build the landing page from the Dock spec")

# Email the human with approve/reject buttons
cue.email_human(
    subject="Draft ready for review",
    body="<p>Please review the draft.</p>",
    approve_context={
        "workspace_slug": "my-project",
        "callback_cue": cue.agents["builder"]["cue_id"],
    },
)

# Report outcome (inside a handler)
cue.report_outcome(success=True, result="Task completed")
```

It also works as a CLI:
```bash
python cue_utils_portable.py send builder "Build the landing page"
python cue_utils_portable.py email --subject "Review needed" --body "<p>Please review</p>"
```

**Dependencies:** Works with `httpx` if available, falls back to Python's built-in `urllib` (zero external dependencies). If the agent's Python environment has `httpx`, it will use it for better error handling.

### Step 3.4: Distribute Config to All Agents

**Same machine:** Write `coordination-config.json` and `cue_utils_portable.py` directly to each agent's working directory.

**Different machine — tell the human:**

```
I need you to give two files to [AGENT_NAME] on [MACHINE_NAME].

File 1 — save as coordination-config.json:
---
[PASTE FULL CONFIG JSON]
---

File 2 — save as cue_utils_portable.py:
---
[PASTE FULL UTILITY SCRIPT — or tell them to download from a URL]
---

Save both files in [AGENT_NAME]'s working directory.
Then tell [AGENT_NAME]: "You now have coordination config. Read coordination-config.json for your cue registry and API keys."

Tell me when done.
```

### Step 3.5: Set Up Dock Shared Workspace

Create a Dock workspace as the shared source of truth:

```bash
DOCK_KEY="YOUR_DOCK_KEY"

curl -s -X POST "https://trydock.ai/api/workspaces" \
  -H "Authorization: Bearer $DOCK_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Agent Coordination Hub",
    "slug": "agent-coordination-hub",
    "mode": "doc",
    "visibility": "org"
  }'
```

Write the cue registry and topology into this doc so any agent can reference it. For agents with Dock MCP installed, they can read this workspace directly.

---

## Phase 4: Verification

Test systematically. Don't skip steps — a broken link in the chain means the whole pipeline fails.

### Step 4.1: Worker Health Check

For each machine, verify the worker is running and sees the right handlers:

```bash
tail -5 ~/Library/Logs/cueapi-worker/stdout.log   # macOS
# OR
journalctl -u cueapi-worker --no-pager -n 5       # Linux
```

Should show `Handlers: [list of your handler names]`.

### Step 4.2: Single Agent Ping (for EACH agent)

Fire a test message to each agent individually:

```bash
CUEAPI_KEY="YOUR_KEY"
CUEAPI_BASE="https://api.cueapi.ai/v1"
CUE_ID="cue_XXXXX"  # the target agent's cue

# PATCH + fire
curl -s -X PATCH "$CUEAPI_BASE/cues/$CUE_ID" \
  -H "Authorization: Bearer $CUEAPI_KEY" \
  -H "Content-Type: application/json" \
  -d '{"payload": {"task": "HANDLER_NAME", "type": "message", "from": "Setup Test", "instructions": "Ping test. Confirm receipt."}}'

EXEC_ID=$(curl -s -X POST "$CUEAPI_BASE/cues/$CUE_ID/fire" \
  -H "Authorization: Bearer $CUEAPI_KEY" -d '{}' | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))")

echo "Execution: $EXEC_ID"

# Wait 30 seconds, then check
sleep 30
curl -s "$CUEAPI_BASE/executions/$EXEC_ID" \
  -H "Authorization: Bearer $CUEAPI_KEY" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'Status: {d.get(\"status\")} | Outcome: {d.get(\"outcome_state\", \"none\")}')
"
```

**Expected:** `Status: success | Outcome: reported_success`

**If it stays `pending`:** Debug checklist:
1. Is the worker running? (`ps aux | grep cueapi`)
2. Does the `task` field match a handler name in the worker yaml? ← **#1 cause**
3. Are handler script paths absolute and correct?
4. Is the handler script executable and has the right Python path?
5. Check worker stderr logs for errors

### Step 4.3: Round-Trip Test (A → B → A)

Agent A sends to Agent B, Agent B replies back to Agent A. This proves bidirectional communication.

```python
from cue_utils_portable import CueClient
cue = CueClient(agent_name="Agent A")

exec_id = cue.send("agent-b",
    "Round-trip test. When you receive this, reply back to me confirming receipt. "
    "Use the coordination config to find my cue ID.",
    type="message", priority=7)

print(f"Sent to Agent B: {exec_id}")
# Wait for Agent B's reply to come through your handler
```

### Step 4.4: Full Chain Test (A → B → C → A)

For 3+ agents, test the full chain:

```python
cue.send("agent-b",
    "Chain test step 1. Process this, then forward to agent-c with the message: "
    "'Chain test step 2 — forward back to orchestrator with: Chain test complete.'")
```

### Step 4.5: Human Email Test

```bash
curl -s -X POST "https://cueapi-bridge-production.up.railway.app/email" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "YOUR_TENANT_ID",
    "to": "HUMAN_EMAIL",
    "subject": "Agent Coordination Test",
    "body": "<p>Your agents can now email you with approve/reject buttons. This is a test.</p><p>If you see this, the email pipeline works.</p>",
    "from_agent": "Setup Agent",
    "approve_context": {
      "workspace_slug": "test",
      "execution_id": "verify-001",
      "callback_cue": "CUE_ID_OF_ANY_AGENT"
    }
  }'
```

**Human:** Check your email. You should see the test email with Approve/Reject buttons. Click Approve to verify the full circuit.

### Troubleshooting

**"Message sent but nothing happened":**
1. Check execution status: `GET /executions/{id}` — is it `pending` (never claimed) or `failed`?
2. If `pending`: the `task` field doesn't match any handler. Check the payload and worker yaml.
3. If `failed`: check worker stderr logs for the error.

**"Worker isn't claiming executions":**
1. Verify worker is running and polling: look for `GET .../claimable` requests in stderr log
2. Check that `worker_id` matches — stale executions claimed by a different worker ID get stuck
3. Restart the worker

**"Stuck execution in the queue":**
```bash
# Force-clear it by reporting a failure outcome
curl -s -X POST "$CUEAPI_BASE/executions/STUCK_ID/outcome" \
  -H "Authorization: Bearer $CUEAPI_KEY" \
  -H "Content-Type: application/json" \
  -d '{"success": false, "error": "manually cleared"}'
```

**"Email not received":**
1. Check spam folder
2. Verify tenant_id is correct
3. Test the bridge directly: `GET https://cueapi-bridge-production.up.railway.app/health`

---

## Phase 5: Build Your First Pipeline

### Sample Pipeline: Social Post Review

Three agents collaborate on creating, reviewing, and enriching social media posts.

**Flow:**
1. **Agent A** (content creator) → creates draft posts in Dock → emails human for review
2. **Human** → reviews on Dock, edits if needed, clicks Approve
3. **Agent B** (enricher) → reads Dock, adds hashtags/formatting, hands off to Agent C
4. **Agent C** (finalizer) → processes posts, emails human completion summary

This demonstrates: Dock as shared data, CueAPI for coordination, bridge for human approval, multi-agent handoffs.

### Step 5.1: Create the Dock Workspace

```bash
DOCK_KEY="YOUR_DOCK_KEY"

curl -s -X POST "https://trydock.ai/api/workspaces" \
  -H "Authorization: Bearer $DOCK_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Social Post Pipeline",
    "slug": "social-post-pipeline",
    "mode": "table",
    "visibility": "org",
    "columns": [
      {"key": "title", "type": "text", "label": "Title", "position": 0},
      {"key": "platform", "type": "text", "label": "Platform", "position": 1},
      {"key": "content", "type": "longtext", "label": "Content", "position": 2},
      {"key": "status", "type": "status", "label": "Status", "position": 3,
        "options": [
          {"label": "Draft", "value": "draft", "color": "#7A8B9E"},
          {"label": "Review", "value": "review", "color": "#BF5AF2"},
          {"label": "Approved", "value": "approved", "color": "#06D6A0"},
          {"label": "Published", "value": "published", "color": "#0A84FF"}
        ]},
      {"key": "hashtags", "type": "text", "label": "Hashtags", "position": 4},
      {"key": "notes", "type": "longtext", "label": "Notes", "position": 5}
    ]
  }'
```

### Step 5.2: Agent A Creates Draft Posts

```python
import httpx

DOCK_KEY = "YOUR_DOCK_KEY"
SLUG = "social-post-pipeline"
BASE = f"https://trydock.ai/api/workspaces/{SLUG}/rows"
HEADERS = {"Authorization": f"Bearer {DOCK_KEY}", "Content-Type": "application/json"}

posts = [
    {"title": "AI agents are not chatbots", "platform": "LinkedIn",
     "content": "Most people think AI agents are just chatbots with tools. They're not. A chatbot waits for you. An agent works without you. The difference is persistent operation - the agent runs on schedules, triggers, and its own initiative. That's the line between tool and teammate.",
     "status": "draft"},
    {"title": "The 3-minute AI automation", "platform": "Twitter",
     "content": "Fastest way to start with AI agents: pick one task you do every morning. Have an agent do it tonight. Wake up to it done. No framework, no course, no 10-step guide. Just one task, automated.",
     "status": "draft"},
    {"title": "Why your AI agent says done when it isn't", "platform": "LinkedIn",
     "content": "The biggest failure mode in AI agents isn't hallucination. It's false completion. The agent says 'done' but didn't actually do the thing. It acknowledged instead of acted. This happens because LLMs are trained to be helpful - saying 'done' feels helpful even when the work isn't done.",
     "status": "draft"},
]

for post in posts:
    resp = httpx.post(BASE, headers=HEADERS, json={"data": post})
    print(f"Created: {post['title']} ({resp.status_code})")
```

### Step 5.3: Agent A Emails Human for Review

```python
from cue_utils_portable import CueClient
cue = CueClient(agent_name="Content Creator")

cue.email_human(
    subject="3 Social Posts Ready for Review",
    body=(
        "<p>I've created 3 draft social posts in Dock.</p>"
        "<ul>"
        "<li><strong>AI agents are not chatbots</strong> (LinkedIn)</li>"
        "<li><strong>The 3-minute AI automation</strong> (Twitter)</li>"
        "<li><strong>Why your AI agent says done when it isn't</strong> (LinkedIn)</li>"
        "</ul>"
        "<p>Review them on Dock, make any edits, then click <strong>Approve</strong> below.</p>"
    ),
    approve_context={
        "workspace_slug": "social-post-pipeline",
        "execution_id": "pipeline-run-001",
        "callback_cue": cue.agents["enricher"]["cue_id"],
        "dock_slug": "your-org/social-post-pipeline",
    },
)
```

### Step 5.4: Human Reviews and Approves

The human:
1. Clicks the Dock link in the email → reviews/edits posts directly
2. Clicks **Approve** in the email
3. The bridge fires Agent B's (enricher) cue with the approval

### Step 5.5: Agent B Enriches the Posts

Agent B's handler receives the approval and enriches the Dock data:

```python
import httpx

DOCK_KEY = "YOUR_DOCK_KEY"
SLUG = "social-post-pipeline"
HEADERS = {"Authorization": f"Bearer {DOCK_KEY}", "Content-Type": "application/json"}

# Read all rows
rows = httpx.get(f"https://trydock.ai/api/workspaces/{SLUG}/rows", headers=HEADERS).json().get("rows", [])

for row in rows:
    platform = row["data"].get("platform", "")
    hashtags = "#AI #AIAgents #BuildInPublic" if platform == "LinkedIn" else "#AI #Automation"

    httpx.patch(f"https://trydock.ai/api/workspaces/{SLUG}/rows/{row['id']}",
                headers=HEADERS, json={"data": {"hashtags": hashtags, "status": "approved"}})

print(f"Enriched {len(rows)} posts")

# Hand off to Agent C
from cue_utils_portable import CueClient
cue = CueClient(agent_name="Enricher")
cue.send("finalizer", f"{len(rows)} posts enriched and approved in {SLUG}. Finalize them.")
```

### Step 5.6: Agent C Finalizes and Reports

```python
from cue_utils_portable import CueClient
cue = CueClient(agent_name="Finalizer")

# ... do final processing ...

cue.email_human(
    subject="Pipeline Complete: 3 Posts Ready",
    body=(
        "<p>The social post pipeline is complete.</p>"
        "<ul>"
        "<li>3 posts enriched with hashtags and formatting</li>"
        "<li>All posts marked as approved in Dock</li>"
        "</ul>"
        "<p>Check the workspace for final versions.</p>"
    ),
)

cue.send("orchestrator", "Pipeline complete. 3 posts processed.")
```

---

## Common Gotchas

### 1. Worker routes by `task` field, NOT cue name
Every payload MUST include `task` matching the handler name in the worker yaml. This is the #1 cause of "my message was sent but nothing happened." No error, no log, just silence.

### 2. PATCH before fire — always two API calls
CueAPI doesn't support payload override at fire time. You PATCH the cue's payload, then fire. This means two API calls per message and a race condition risk if two agents fire the same cue simultaneously. (Fire-with-payload is on CueAPI's roadmap.)

### 3. Use absolute paths everywhere
Worker daemons (launchd on macOS, systemd on Linux) strip the PATH. All commands in handler configs need absolute paths: `/usr/bin/python3`, `/Users/you/.local/bin/claude`, etc. Relative paths WILL fail silently.

### 4. Poisoned queues from mismatched worker IDs
Never claim executions with a different worker_id than your worker config. If you do, those executions get permanently stuck — no way to cancel them. Clear stuck executions by reporting a failure outcome:

```bash
curl -s -X POST "https://api.cueapi.ai/v1/executions/STUCK_ID/outcome" \
  -H "Authorization: Bearer $CUEAPI_KEY" \
  -H "Content-Type: application/json" \
  -d '{"success": false, "error": "manually cleared stuck execution"}'
```

### 5. Per-agent API keys don't see new cues
If you create named API keys and then create new cues, the keys may not see them. Use a single shared key for now. (Bug reported to CueAPI, April 2026.)

### 6. Standing cues use a far-future schedule
CueAPI requires a schedule for every cue. For agent-to-agent messaging (manual fire only), set `schedule.at` to `2099-01-01T00:00:00Z`. A `manual` schedule type is coming.

### 7. Always report outcomes
Every handler should report success/failure via `POST /executions/{id}/outcome`. It's free audit trail and helps debug failures. CueAPI injects `CUEAPI_EXECUTION_ID` as an env var.

### 8. Dock columns: PUT only, no POST
To add/modify columns on a Dock workspace, use `PUT /api/workspaces/{slug}/columns` with the FULL column array. `POST /columns` returns 405. Positions must be contiguous (0, 1, 2...).

### 9. Dock docs use HTML, not markdown
Dock's doc mode stores HTML content. If writing to a Dock doc, convert markdown to HTML first.

### 10. flush=True on prints in handlers
Add `flush=True` to print statements in handler scripts. Without it, output may not appear in worker logs until the process exits (Python buffers stdout when not connected to a terminal).

---

## Files Included with This Guide

1. **`guide-multi-agent-coordination.md`** — This file (the guide)
2. **`cue_utils_portable.py`** — Python utility for agent-to-agent messaging + email (zero dependencies)
3. **`coordination-config.json`** — Template for the config file (fill in your values)

---

## Reference

### CueAPI
- **API Base:** `https://api.cueapi.ai/v1`
- **Docs:** https://cueapi.ai/docs
- **Agent reference:** https://cueapi.ai/agents/
- **Worker package:** `pip install cueapi-worker`

### Dock
- **URL:** https://trydock.ai
- **API:** `https://trydock.ai/api/workspaces/{slug}`
- **Rows:** `GET|POST /api/workspaces/{slug}/rows`, `PATCH /api/workspaces/{slug}/rows/{id}`
- **Columns:** `PUT /api/workspaces/{slug}/columns` (full array replacement)
- **Docs:** `GET|PUT /api/workspaces/{slug}/doc` (HTML content)

### CueAPI Bridge (Shared Approval Service)
- **URL:** `https://cueapi-bridge-production.up.railway.app`
- **Health:** `GET /health`
- **Register:** `POST /tenants` — `{cueapi_key, name, email}` → returns `{tenant_id, hmac_secret}`
- **Send email:** `POST /email` — `{tenant_id, to, subject, body, from_agent, approve_context?}`
- **Approve callback:** `GET /approve?slug=...&exec=...&cue=...&action=...&ts=...&sig=...&tid=...`

---

*Built by Mike Molinet and Max. Powered by CueAPI and Dock.*
*Questions: mike@vector.build*
