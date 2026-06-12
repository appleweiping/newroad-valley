import os
import json
import glob
import httpx
import re
import hashlib
import subprocess
import time
import uuid
import base64
import ctypes
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from itertools import islice

app = FastAPI(title="Pixel Agent Town v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# v3 live-bridge endpoints for the Xinlu Valley web client (read-only aggregation)
from town_api import router as town_router  # noqa: E402

app.include_router(town_router)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

SKILL_INDEX_PATH = Path(r"D:\agent-resources\SKILL-INDEX.md")
SHARED_MEMORY_DIR = Path(r"D:\research\Vipin's Knowledgebase\memory")
KNOWLEDGE_BASE_DIR = Path(r"D:\research\Vipin's Knowledgebase")
DEVTOOLS_DIR = Path(r"D:\devtools")
RESEARCH_ROOT = Path(r"D:\Research")
AGENT_HUB_DIR = DEVTOOLS_DIR / "agent-hub"
AGENT_HUB_STATE_DIR = AGENT_HUB_DIR / "state"
AGENTMEMORY_URL = "http://localhost:3111"
MAX_SCAN_ITEMS = 250
MEMORY_PREVIEW_CHARS = 2400
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
BUILDING_REGISTRY_PATH = DATA_DIR / "buildings.json"
AGENT_REGISTRY_PATH = DATA_DIR / "agents.json"
MODEL_PROFILE_REGISTRY_PATH = DATA_DIR / "model_profiles.json"
WORKSPACE_REGISTRY_PATH = DATA_DIR / "workspaces.json"
QUEST_REGISTRY_PATH = DATA_DIR / "quests.json"
DISTRICT_REGISTRY_PATH = DATA_DIR / "districts.json"
NPC_QUEST_REGISTRY_PATH = DATA_DIR / "npc_quests.json"
ROOM_SCENE_REGISTRY_PATH = DATA_DIR / "room_scenes.json"
MAP_DECOR_REGISTRY_PATH = DATA_DIR / "map_decor.json"
WORKFLOW_ROUTE_REGISTRY_PATH = DATA_DIR / "workflow_routes.json"
PLUGIN_MANIFEST_REGISTRY_PATH = DATA_DIR / "plugin_manifests.json"
DRAFTS_DIR = PROJECT_ROOT / "workspace" / "drafts"
AGENT_DISPATCH_DRAFTS_DIR = PROJECT_ROOT / "workspace" / "agent-dispatch"
AGENT_RUNNER_DISPATCH_DIR = PROJECT_ROOT / "workspace" / "agent-runner-dispatches"
TASKS_DIR = PROJECT_ROOT / "workspace" / "tasks"
TASK_LEDGER_PATH = TASKS_DIR / "tasks.json"
AGENT_CHAT_DIR = PROJECT_ROOT / "workspace" / "agent-chats"
AGENT_TASK_LOG_DIR = PROJECT_ROOT / "workspace" / "agent-task-logs"
AGENT_TOOL_LOG_DIR = PROJECT_ROOT / "workspace" / "agent-tool-logs"
MEMORY_PROPOSALS_DIR = PROJECT_ROOT / "workspace" / "memory-proposals"
MEMORY_PROMOTIONS_DIR = PROJECT_ROOT / "workspace" / "memory-promotions"
KNOWLEDGE_INDEX_DIR = PROJECT_ROOT / "workspace" / "knowledge-index"
KNOWLEDGE_INDEX_CACHE_PATH = KNOWLEDGE_INDEX_DIR / "knowledge-index.json"
FILE_VAULT_INDEX_DIR = PROJECT_ROOT / "workspace" / "file-vault-index"
FILE_VAULT_INDEX_CACHE_PATH = FILE_VAULT_INDEX_DIR / "file-vault-index.json"
FILE_VAULT_TAGS_PATH = FILE_VAULT_INDEX_DIR / "file-tags.json"
FILE_ORGANIZE_DRAFTS_DIR = PROJECT_ROOT / "workspace" / "file-organize-drafts"
CODE_CONTEXT_DIR = PROJECT_ROOT / "workspace" / "code-contexts"
CODE_PATCH_PLANS_DIR = PROJECT_ROOT / "workspace" / "code-patch-plans"
PROJECT_VERIFICATION_LOG_DIR = PROJECT_ROOT / "workspace" / "project-verification-logs"
GITHUB_HARBOR_DRAFTS_DIR = PROJECT_ROOT / "workspace" / "github-harbor-drafts"
MODEL_CONFIG_DRAFTS_DIR = PROJECT_ROOT / "workspace" / "model-config-drafts"
MODEL_TEST_RESULTS_DIR = PROJECT_ROOT / "workspace" / "model-test-results"
MODEL_KEY_VAULT_DIR = PROJECT_ROOT / "workspace" / "model-key-vault"
MODEL_KEY_VAULT_PATH = MODEL_KEY_VAULT_DIR / "key-vault.json"
MEMORY_EVENTS_DIR = PROJECT_ROOT / "workspace" / "memory-events"
TERMINAL_LOG_DIR = PROJECT_ROOT / "workspace" / "terminal-logs"
BACKEND_JOB_LOG_DIR = PROJECT_ROOT / "workspace" / "backend-job-logs"
AUTOMATION_DRAFTS_DIR = PROJECT_ROOT / "workspace" / "automation-drafts"
SETTINGS_DRAFTS_DIR = PROJECT_ROOT / "workspace" / "settings-drafts"
TEST_PLAN_DRAFTS_DIR = PROJECT_ROOT / "workspace" / "test-plans"
VERTICAL_SLICE_PROOFS_DIR = PROJECT_ROOT / "workspace" / "vertical-slice-proofs"
BUG_REPORTS_DIR = PROJECT_ROOT / "workspace" / "bug-reports"
PROJECT_BRIEFS_DIR = PROJECT_ROOT / "workspace" / "project-briefs"
DOWNLOAD_INTAKE_DIR = PROJECT_ROOT / "workspace" / "download-intake"
ASSET_NOTES_DIR = PROJECT_ROOT / "workspace" / "asset-notes"
OFFICE_NOTES_DIR = PROJECT_ROOT / "workspace" / "office-notes"
SCHEDULE_DRAFTS_DIR = PROJECT_ROOT / "workspace" / "schedules"
LEARNING_PLANS_DIR = PROJECT_ROOT / "workspace" / "learning-plans"
LANGUAGE_PRACTICE_DIR = PROJECT_ROOT / "workspace" / "language-practice"
RESEARCH_DATA_NOTES_DIR = PROJECT_ROOT / "workspace" / "research-data-notes"
RESEARCH_LOGS_DIR = PROJECT_ROOT / "workspace" / "research-logs"
PAPER_READING_NOTES_DIR = PROJECT_ROOT / "workspace" / "paper-reading-notes"
PAPER_EXTRACTION_REPORTS_DIR = PROJECT_ROOT / "workspace" / "paper-extraction-reports"
RELEASE_DRAFTS_DIR = PROJECT_ROOT / "workspace" / "release-drafts"
RELEASE_READINESS_REPORTS_DIR = PROJECT_ROOT / "workspace" / "release-readiness-reports"
PLUGIN_DRAFTS_DIR = PROJECT_ROOT / "workspace" / "plugin-drafts"
BACKUP_PLANS_DIR = PROJECT_ROOT / "workspace" / "backup-plans"
GOAL_DRAFTS_DIR = PROJECT_ROOT / "workspace" / "goals"
INSPIRATION_NOTES_DIR = PROJECT_ROOT / "workspace" / "inspiration"
TEMP_DRAFTS_DIR = PROJECT_ROOT / "workspace" / "temp-drafts"
SECRET_AUDIT_MAX_FILES = 180
SECRET_AUDIT_MAX_BYTES_PER_FILE = 2_000_000
SECRET_AUDIT_EXTENSIONS = {".json", ".md", ".txt", ".log", ".env", ".example", ".yaml", ".yml", ".toml", ".cmd", ".ps1"}
SECRET_AUDIT_TARGETS = [
    {"id": "root-env-example", "name": "Root Env Example", "path": PROJECT_ROOT / ".env.example"},
    {"id": "backend-env-example", "name": "Backend Env Example", "path": PROJECT_ROOT / "backend" / ".env.example"},
    {"id": "knowledge-index", "name": "Knowledge Index Cache", "path": KNOWLEDGE_INDEX_DIR},
    {"id": "file-vault-index", "name": "File Vault Index Cache", "path": FILE_VAULT_INDEX_DIR},
    {"id": "agent-runner-dispatches", "name": "Agent Runner Dispatches", "path": AGENT_RUNNER_DISPATCH_DIR},
    {"id": "agent-task-logs", "name": "Agent Task Logs", "path": AGENT_TASK_LOG_DIR},
    {"id": "agent-tool-logs", "name": "Agent Tool Logs", "path": AGENT_TOOL_LOG_DIR},
    {"id": "model-config-drafts", "name": "Model Config Drafts", "path": MODEL_CONFIG_DRAFTS_DIR},
    {"id": "model-test-results", "name": "Model Test Results", "path": MODEL_TEST_RESULTS_DIR},
    {"id": "terminal-logs", "name": "Terminal Logs", "path": TERMINAL_LOG_DIR},
]
SECRET_AUDIT_PATTERNS = [
    ("openai_key", re.compile(r"(?i)\bsk-[A-Za-z0-9_\-]{12,}")),
    ("github_token", re.compile(r"(?i)\bgh[pousr]_[A-Za-z0-9_]{12,}")),
    ("slack_token", re.compile(r"(?i)\bxox[baprs]-[A-Za-z0-9\-]{12,}")),
    ("credentialed_url", re.compile(r"(?i)https?://[^/@\s]{3,}@[^/\s]+")),
    ("assigned_secret", re.compile(r"(?im)^[ \t]*(?:set[ \t]+)?[\"']?[^=\r\n]*(?:API[_-]?KEY|AUTH[_-]?TOKEN|ACCESS[_-]?TOKEN|SECRET|PASSWORD|PRIVATE[_-]?KEY)[^=\r\n]*[ \t]*=[ \t]*[^\s\r\n\"']{8,}")),
]
CONFIRM_SAVE_DRAFT = "SAVE_LOCAL_DRAFT"
CONFIRM_RUN_COMMAND = "RUN_LOCAL_COMMAND"
CONFIRM_PROMOTE_MEMORY = "PROMOTE_MEMORY"
CONFIRM_SAVE_API_KEY = "SAVE_API_KEY"
CONFIRM_RUN_PROJECT_CHECK = "RUN_PROJECT_CHECK"
CONFIRM_RUN_AGENT_RUNNER = "RUN_AGENT_RUNNER"
CONFIRM_PLUGIN_ACTIVATION_PLAN = "PLAN_PLUGIN_ACTIVATION"
CONFIRM_GITHUB_PUBLISH_PLAN = "PLAN_GITHUB_PUBLISH"
MEMORY_CATEGORIES = ["decisions", "facts", "lessons", "preferences", "sessions", "workflows"]
JOB_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ai-town-job")
JOBS: dict[str, dict] = {}
MAX_JOBS = 50
AGENT_TASKS: dict[str, dict] = {}
MAX_AGENT_TASKS = 80
DEFAULT_AGENT_TASK_MAX_RUNNING = 1
AGENT_TOOL_INVOCATIONS: dict[str, dict] = {}
MAX_AGENT_TOOL_INVOCATIONS = 100
KNOWLEDGE_DOC_CACHE: dict[str, dict] = {}
FILE_VAULT_ITEM_CACHE: dict[str, dict] = {}
PROJECT_PATH_CACHE: dict[str, str] = {}
FILE_VAULT_ROOTS = [
    {"id": "research", "name": "Research", "path": RESEARCH_ROOT},
    {"id": "company", "name": "Company", "path": Path(r"D:\Company")},
    {"id": "knowledgebase", "name": "Knowledgebase", "path": KNOWLEDGE_BASE_DIR},
    {"id": "agent-resources", "name": "Agent Resources", "path": Path(r"D:\agent-resources")},
    {"id": "devtools", "name": "Devtools", "path": DEVTOOLS_DIR},
    {"id": "project", "name": "AI Town Project", "path": PROJECT_ROOT},
]
DOWNLOAD_STATION_ROOTS = [
    {"id": "user-downloads", "name": "User Downloads", "path": Path.home() / "Downloads"},
    {"id": "d-downloads", "name": "D Downloads", "path": Path(r"D:\Downloads")},
    {"id": "ai-town-art", "name": "AI Town Art Imports", "path": PROJECT_ROOT / "art"},
    {"id": "ai-town-assets", "name": "AI Town Asset Notes", "path": PROJECT_ROOT / "workspace" / "asset-intake"},
]
ASSET_GALLERY_ROOTS = [
    {"id": "godot-assets", "name": "Godot Runtime Assets", "path": PROJECT_ROOT / "godot" / "assets", "role": "runtime textures and imported visuals"},
    {"id": "source-art", "name": "Source Art Workspace", "path": PROJECT_ROOT / "art", "role": "generation prompts, drafts, and source exports"},
    {"id": "frontend-assets", "name": "Legacy Frontend Assets", "path": PROJECT_ROOT / "frontend" / "public" / "assets", "role": "legacy reusable generated assets"},
    {"id": "visual-docs", "name": "Visual Direction Docs", "path": PROJECT_ROOT / "docs", "role": "art direction, baseline, and vision documents"},
    {"id": "screenshots", "name": "Visual Evidence", "path": PROJECT_ROOT / "screenshots", "role": "smoke screenshots and visual regression evidence"},
    {"id": "asset-notes", "name": "Asset Notes", "path": ASSET_NOTES_DIR, "role": "project-local asset curation notes"},
]
OFFICE_CENTER_ROOTS = [
    {"id": "company", "name": "Company Workspace", "path": Path(r"D:\Company"), "role": "primary local office and company project area"},
    {"id": "project-docs", "name": "AI Town Project Docs", "path": PROJECT_ROOT / "docs", "role": "active project docs and operating notes"},
    {"id": "writing-drafts", "name": "Writing Drafts", "path": DRAFTS_DIR, "role": "project-local writing drafts"},
    {"id": "project-briefs", "name": "Project Briefs", "path": PROJECT_BRIEFS_DIR, "role": "portfolio and project planning briefs"},
    {"id": "office-notes", "name": "Office Notes", "path": OFFICE_NOTES_DIR, "role": "project-local office notes and meeting-style memos"},
]
SCHEDULE_CENTER_SIGNAL_FILES = [
    PROJECT_ROOT / "PLAN.md",
    PROJECT_ROOT / "MEMORY.md",
    TASK_LEDGER_PATH,
    SHARED_MEMORY_DIR / "facts" / "all-projects-status.md",
    SHARED_MEMORY_DIR / "preferences" / "mandatory-step-update.md",
]
LEARNING_SIGNAL_FILES = [
    SKILL_INDEX_PATH,
    PROJECT_ROOT / "docs" / "ARCHITECTURE_GODOT_REBUILD.md",
    PROJECT_ROOT / "docs" / "VISUAL_BASELINE.md",
    SHARED_MEMORY_DIR / "workflows" / "agent-resources-guide.md",
    SHARED_MEMORY_DIR / "decisions" / "research-hard-rules.md",
]
LANGUAGE_SIGNAL_FILES = [
    PROJECT_ROOT / "README.md",
    PROJECT_ROOT / "docs" / "VISUAL_BASELINE.md",
    PROJECT_ROOT / "godot" / "README.md",
    PROJECT_ROOT / "MEMORY.md",
]
RESEARCH_DATA_KEYWORDS = {
    "data",
    "dataset",
    "datasets",
    "result",
    "results",
    "output",
    "outputs",
    "experiment",
    "experiments",
    "run",
    "runs",
    "log",
    "logs",
    "checkpoint",
    "checkpoints",
    "table",
    "tables",
    "figure",
    "figures",
    "csv",
    "jsonl",
    "parquet",
}
PAPER_READING_ROOTS = [
    {"id": "research", "name": "Research Papers and Notes", "path": RESEARCH_ROOT, "role": "papers, manuscript folders, BibTeX, and research notes"},
    {"id": "knowledgebase", "name": "Knowledgebase Papers", "path": KNOWLEDGE_BASE_DIR, "role": "shared knowledge base papers, notes, and references"},
    {"id": "project-docs", "name": "AI Town Docs", "path": PROJECT_ROOT / "docs", "role": "project docs and architecture notes"},
    {"id": "reading-notes", "name": "Paper Reading Notes", "path": PAPER_READING_NOTES_DIR, "role": "project-local paper reading queue and audit notes"},
]
PAPER_READING_EXTENSIONS = {".pdf", ".bib", ".tex", ".md", ".rst", ".docx", ".txt"}
PAPER_READING_KEYWORDS = {
    "paper",
    "papers",
    "article",
    "articles",
    "bib",
    "bibtex",
    "reference",
    "references",
    "citation",
    "citations",
    "related",
    "literature",
    "survey",
    "reading",
    "notes",
}
RELEASE_READINESS_FILES = [
    {"id": "readme", "name": "README", "path": PROJECT_ROOT / "README.md", "required": True, "role": "public project overview and launch instructions"},
    {"id": "license", "name": "License", "path": PROJECT_ROOT / "LICENSE", "required": True, "role": "open-source license"},
    {"id": "contributing", "name": "Contribution Guide", "path": PROJECT_ROOT / "CONTRIBUTING.md", "required": True, "role": "external contributor workflow"},
    {"id": "security", "name": "Security Notes", "path": PROJECT_ROOT / "SECURITY.md", "required": True, "role": "safety disclosure and vulnerability reporting"},
    {"id": "roadmap", "name": "Roadmap", "path": PROJECT_ROOT / "ROADMAP.md", "required": True, "role": "long-term open-source plan"},
    {"id": "architecture", "name": "Architecture", "path": PROJECT_ROOT / "docs" / "ARCHITECTURE_GODOT_REBUILD.md", "required": True, "role": "technical architecture baseline"},
    {"id": "visual-baseline", "name": "Visual Baseline", "path": PROJECT_ROOT / "docs" / "VISUAL_BASELINE.md", "required": True, "role": "art direction contract"},
    {"id": "visual-smoke", "name": "Visual Smoke Screenshot", "path": PROJECT_ROOT / "screenshots" / "visual-smoke.png", "required": True, "role": "current gameplay screenshot evidence"},
    {"id": "godot-export-presets", "name": "Godot Export Presets", "path": PROJECT_ROOT / "godot" / "export_presets.cfg", "required": True, "role": "Godot export target configuration"},
    {"id": "godot-export-script", "name": "Godot Export Script", "path": PROJECT_ROOT / "tools" / "export-godot.ps1", "required": True, "role": "safe local Godot export preflight/run tooling"},
    {"id": "godot-template-installer", "name": "Godot Template Installer", "path": PROJECT_ROOT / "tools" / "install-godot-templates.ps1", "required": True, "role": "project-local Godot export template installer"},
    {"id": "release-manifest-script", "name": "Release Manifest Script", "path": PROJECT_ROOT / "tools" / "write-release-manifest.ps1", "required": True, "role": "local release package manifest generator"},
    {"id": "packaged-launcher", "name": "Packaged Launcher", "path": PROJECT_ROOT / "start-packaged.cmd", "required": True, "role": "one-click exported game plus backend launcher"},
]
PLUGIN_REGISTRY_ROOTS = [
    {"id": "godot-data", "name": "Godot Registries", "path": DATA_DIR, "role": "runtime JSON registries for buildings, agents, and model profiles"},
    {"id": "godot-scripts", "name": "Godot Scripts", "path": PROJECT_ROOT / "godot" / "scripts", "role": "client-side room, UI, and gameplay scripts"},
    {"id": "backend", "name": "FastAPI Backend", "path": PROJECT_ROOT / "backend", "role": "local API adapters and room endpoints"},
    {"id": "tools", "name": "Project Tools", "path": PROJECT_ROOT / "tools", "role": "local scripts, verifiers, and bundled executables"},
    {"id": "project-docs", "name": "Project Docs", "path": PROJECT_ROOT / "docs", "role": "architecture, visual, and testing documentation"},
    {"id": "agent-resources", "name": "Agent Resources", "path": Path(r"D:\agent-resources"), "role": "external agent skill and workflow resources"},
    {"id": "kb-skills", "name": "Knowledgebase Codex Skills", "path": KNOWLEDGE_BASE_DIR / ".codex" / "skills", "role": "project-adjacent ARIS and Codex skills"},
    {"id": "plugin-drafts", "name": "Plugin Drafts", "path": PLUGIN_DRAFTS_DIR, "role": "project-local extension proposal drafts"},
]
PLUGIN_FILE_EXTENSIONS = {".json", ".gd", ".py", ".ps1", ".cmd", ".md", ".toml", ".yaml", ".yml"}
BACKUP_STATION_SOURCES = [
    {"id": "ai-town-project", "name": "AI Town Project", "path": PROJECT_ROOT, "priority": "critical"},
    {"id": "shared-memory", "name": "Shared Agent Memory", "path": SHARED_MEMORY_DIR, "priority": "critical"},
    {"id": "godot-registries", "name": "Godot Registries", "path": DATA_DIR, "priority": "high"},
    {"id": "project-docs", "name": "Project Docs", "path": PROJECT_ROOT / "docs", "priority": "high"},
    {"id": "local-workspace", "name": "AI Town Workspace", "path": PROJECT_ROOT / "workspace", "priority": "medium"},
]
BACKUP_STATION_TARGETS = [
    {"id": "d-backups", "name": "D Backups", "path": Path(r"D:\Backups")},
    {"id": "project-backups", "name": "Project Backup Staging", "path": PROJECT_ROOT / "workspace" / "backups"},
    {"id": "devtools-backups", "name": "Devtools Backups", "path": DEVTOOLS_DIR / "backups"},
]
GOAL_TOWER_SIGNAL_FILES = [
    PROJECT_ROOT / "PLAN.md",
    PROJECT_ROOT / "MEMORY.md",
    SHARED_MEMORY_DIR / "facts" / "all-projects-status.md",
    SHARED_MEMORY_DIR / "preferences" / "mandatory-step-update.md",
    SHARED_MEMORY_DIR / "decisions" / "research-hard-rules.md",
]
INSPIRATION_SIGNAL_FILES = [
    PROJECT_ROOT / "PLAN.md",
    PROJECT_ROOT / "MEMORY.md",
    PROJECT_ROOT / "docs" / "VISUAL_BASELINE.md",
    PROJECT_ROOT / "docs" / "ARCHITECTURE_GODOT_REBUILD.md",
    SHARED_MEMORY_DIR / "facts" / "all-projects-status.md",
]
FILE_PREVIEW_EXTENSIONS = {
    ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".py", ".gd",
    ".ts", ".tsx", ".js", ".jsx", ".css", ".html", ".cmd", ".ps1", ".sh", ".csv",
}
FILE_PREVIEW_MAX_BYTES = 256_000
FILE_PREVIEW_CHARS = 5000
TERMINAL_COMMANDS = {
    "git-status-ai-town": {
        "label": "Git status for AI Town",
        "args": ["git", "status", "--short"],
        "cwd": PROJECT_ROOT,
        "timeout": 15,
        "safety": "confirm-required",
        "description": "Read the current AI Town working tree status.",
    },
    "python-compile-backend": {
        "label": "Compile backend Python",
        "args": ["python", "-m", "py_compile", "backend/main.py"],
        "cwd": PROJECT_ROOT,
        "timeout": 20,
        "safety": "confirm-required",
        "description": "Run Python syntax verification for the FastAPI bridge.",
    },
    "list-project-root": {
        "label": "List project root",
        "args": ["powershell", "-NoProfile", "-Command", "Get-ChildItem -Name | Select-Object -First 60"],
        "cwd": PROJECT_ROOT,
        "timeout": 10,
        "safety": "confirm-required",
        "description": "List a bounded sample of files at the AI Town project root.",
    },
}

ROOM_META = {
    "memory-library": {
        "npc": "Sonnet",
        "room_title": "Memory Library Reading Room",
        "atmosphere": "quiet shelves of shared decisions, facts, lessons, and session notes",
        "workbench": "Memory Lens",
    },
    "skill-workshop": {
        "npc": "PixelCat",
        "room_title": "Skill Workshop Bench",
        "atmosphere": "tool racks, workflow charms, and reusable agent skills",
        "workbench": "Skill Loom",
    },
    "knowledge-tower": {
        "npc": "ARIS",
        "room_title": "Knowledge Tower Archive",
        "atmosphere": "research pages, wiki topics, and citation trails",
        "workbench": "Archive Telescope",
    },
    "devtools-lab": {
        "npc": "PixelCat",
        "room_title": "Devtools Lab",
        "atmosphere": "local launchers, CLI benches, and diagnostics",
        "workbench": "Tool Console",
    },
    "code-workshop": {
        "npc": "Codex",
        "room_title": "Code Workshop",
        "atmosphere": "repo benches, README scrolls, git status lamps, and test anvils",
        "workbench": "Project Inspector",
    },
    "github-harbor": {
        "npc": "Codex",
        "room_title": "GitHub Harbor",
        "atmosphere": "branch routes, commit crates, remote docks, and release ships",
        "workbench": "Release Chart Table",
    },
    "terminal-control": {
        "npc": "Codex",
        "room_title": "Terminal Control Room",
        "atmosphere": "glowing command consoles, log screens, allowlist seals, and safety levers",
        "workbench": "Command Console",
    },
    "system-monitor": {
        "npc": "Opus",
        "room_title": "System Monitor Room",
        "atmosphere": "status lanterns, service crystals, job queue boards, and quiet warning bells",
        "workbench": "Observatory Console",
    },
    "model-market": {
        "npc": "DeepSeek",
        "room_title": "Model Market and API Gateway",
        "atmosphere": "model stalls, proxy crystals, pricing scrolls, and sealed API-key lockboxes",
        "workbench": "Gateway Ledger",
    },
    "task-board": {
        "npc": "Codex",
        "room_title": "Task Board Plaza",
        "atmosphere": "quest notices, local task cards, dispatch slips, and progress ribbons",
        "workbench": "Quest Ledger",
    },
    "writing-studio": {
        "npc": "Sonnet",
        "room_title": "Writing Studio",
        "atmosphere": "draft desks, parchment bundles, README scrolls, and quiet editing lamps",
        "workbench": "Draft Desk",
    },
    "automation-factory": {
        "npc": "PixelCat",
        "room_title": "Automation Factory",
        "atmosphere": "clockwork benches, verification belts, script crates, and schedule blueprints",
        "workbench": "Automation Blueprint Table",
    },
    "permission-hall": {
        "npc": "Opus",
        "room_title": "Permission Hall",
        "atmosphere": "sealed ledgers, confirmation sigils, whitelist maps, and audit bells",
        "workbench": "Safety Charter Desk",
    },
    "settings-center": {
        "npc": "Opus",
        "room_title": "Settings Center",
        "atmosphere": "registry shelves, launch-script keys, profile cards, and sealed env scrolls",
        "workbench": "Config Draft Desk",
    },
    "testing-arena": {
        "npc": "Haiku",
        "room_title": "Testing Arena",
        "atmosphere": "smoke-test banners, visual proof screens, bug targets, and result pedestals",
        "workbench": "Verification Tactics Board",
    },
    "bug-clinic": {
        "npc": "Codex",
        "room_title": "Bug Clinic",
        "atmosphere": "diagnostic lamps, stack-trace charts, repair tickets, and calm triage desks",
        "workbench": "Triage Desk",
    },
    "project-management-hall": {
        "npc": "Opus",
        "room_title": "Project Management Hall",
        "atmosphere": "portfolio banners, roadmap tables, repo maps, research boards, and task ribbons",
        "workbench": "Portfolio Planning Table",
    },
    "download-station": {
        "npc": "Haiku",
        "room_title": "Download Station",
        "atmosphere": "parcel shelves, asset crates, intake labels, and quarantine-safe sorting trays",
        "workbench": "Intake Counter",
    },
    "asset-gallery": {
        "npc": "Sonnet",
        "room_title": "Asset Resource Gallery",
        "atmosphere": "framed sprites, warm mood boards, visual baseline plaques, and safe curation shelves",
        "workbench": "Asset Curation Table",
    },
    "local-office-center": {
        "npc": "Codex",
        "room_title": "Local Office Center",
        "atmosphere": "paper trays, meeting scrolls, inbox shelves, company folders, and gentle follow-up bells",
        "workbench": "Office Memo Desk",
    },
    "schedule-plan-center": {
        "npc": "Haiku",
        "room_title": "Schedule and Plan Center",
        "atmosphere": "calendar ribbons, milestone clocks, task bells, and quiet planning alcoves",
        "workbench": "Timebox Planning Desk",
    },
    "learning-training-grounds": {
        "npc": "PixelCat",
        "room_title": "Learning Training Grounds",
        "atmosphere": "practice dummies, skill scrolls, course flags, memory cards, and gentle progress bells",
        "workbench": "Practice Plan Table",
    },
    "language-learning-area": {
        "npc": "Sonnet",
        "room_title": "Language Learning Area",
        "atmosphere": "phrase cards, multilingual signposts, dialogue ribbons, and pronunciation lanterns",
        "workbench": "Phrase Practice Desk",
    },
    "research-data-center": {
        "npc": "ARIS",
        "room_title": "Research Data Center",
        "atmosphere": "dataset cabinets, result ledgers, reproducibility tags, and quiet audit lamps",
        "workbench": "Data Provenance Desk",
    },
    "paper-reading-room": {
        "npc": "ARIS",
        "room_title": "Paper Reading Room",
        "atmosphere": "paper stacks, citation cards, BibTeX shelves, and calm review lamps",
        "workbench": "Citation Audit Desk",
    },
    "version-release-plaza": {
        "npc": "Codex",
        "room_title": "Version Release Plaza",
        "atmosphere": "release banners, checklist pedestals, screenshot frames, and git route signs",
        "workbench": "Release Readiness Table",
    },
    "plugin-registry": {
        "npc": "PixelCat",
        "room_title": "Plugin Registry",
        "atmosphere": "extension shelves, manifest cards, local skill maps, and sandbox warning ribbons",
        "workbench": "Extension Catalog Desk",
    },
    "backup-station": {
        "npc": "Opus",
        "room_title": "Backup Station",
        "atmosphere": "snapshot vaults, restore maps, checksum lanterns, and sealed backup plans",
        "workbench": "Recovery Planning Table",
    },
    "goal-tower": {
        "npc": "Opus",
        "room_title": "Long-Term Goal Tower",
        "atmosphere": "roadmap constellations, milestone banners, priority crystals, and quiet progress bells",
        "workbench": "Goal Compass",
    },
    "inspiration-station": {
        "npc": "Sonnet",
        "room_title": "Inspiration Collection Station",
        "atmosphere": "idea lanterns, clipped references, mood cards, and quiet creative inbox trays",
        "workbench": "Idea Sorting Desk",
    },
    "temporary-draft-box": {
        "npc": "Haiku",
        "room_title": "Temporary Draft Box",
        "atmosphere": "loose notes, unsorted task slips, draft trays, and gentle reminder bells",
        "workbench": "Scratch Sorting Box",
    },
    "file-vault": {
        "npc": "Codex",
        "room_title": "File Vault",
        "atmosphere": "D drive cabinets arranged by project family",
        "workbench": "Vault Index",
    },
    "research-hall": {
        "npc": "ARIS",
        "room_title": "Research Hall",
        "atmosphere": "active project boards and experiment-status scrolls",
        "workbench": "Research Compass",
    },
    "agent-hub": {
        "npc": "Codex",
        "room_title": "Agent Hub",
        "atmosphere": "coordination boards and mailbox signal lamps",
        "workbench": "Dispatch Table",
    },
    "town-hall": {
        "npc": "Opus",
        "room_title": "Town Hall",
        "atmosphere": "architecture decrees and long-term operating rules",
        "workbench": "Decision Desk",
    },
    "resource-market": {
        "npc": "DeepSeek",
        "room_title": "Resource Market",
        "atmosphere": "bundles of local repositories, skills, and reusable resources",
        "workbench": "Supply Ledger",
    },
}

RESEARCH_PROJECTS = [
    {
        "id": "pony-rsc",
        "name": "Pony / Uncertainty",
        "theme": "Ranking Stability Conformal for recommendation uncertainty",
        "priority": 1,
        "local_dirs": [RESEARCH_ROOT / "Uncertainty", RESEARCH_ROOT / "Uncertainty-LLM4Rec"],
        "status_files": [
            SHARED_MEMORY_DIR / "facts" / "pony-current-status.md",
            SHARED_MEMORY_DIR / "facts" / "pony-ccrp-four-domain-status.md",
        ],
        "server": "pony-rec-gpu 125.71.97.70:15302 ~/projects/pony-rec-rescue-shadow-v6/",
        "next_action": "Check experiment-bridge status and decide the next RSC validation run.",
    },
    {
        "id": "tgl-rec",
        "name": "TGL-Rec",
        "theme": "Temporal graph learning recommendation experiments",
        "priority": 2,
        "local_dirs": [RESEARCH_ROOT / "TGL-Rec"],
        "status_files": [SHARED_MEMORY_DIR / "facts" / "tglrec-current-status.md"],
        "server": "not deployed",
        "next_action": "Review Phase 10 reportable path and prepare deployment plan.",
    },
    {
        "id": "truce-rec",
        "name": "TRUCE-Rec",
        "theme": "Trustworthy recommendation research gate R1",
        "priority": 3,
        "local_dirs": [RESEARCH_ROOT / "TRUCE-Rec"],
        "status_files": [SHARED_MEMORY_DIR / "facts" / "truce-rec-current-status.md"],
        "server": "pony-rec-gpu ~/projects/TRUCE-Rec",
        "next_action": "Deploy completed code path and collect gate evidence.",
    },
    {
        "id": "proteinshift",
        "name": "ProteinShift / DA-BCP",
        "theme": "Distribution-aware biological conformal prediction",
        "priority": 4,
        "local_dirs": [RESEARCH_ROOT / "DA-BCP"],
        "status_files": [SHARED_MEMORY_DIR / "facts" / "proteinshift-status.md"],
        "server": "local-first",
        "next_action": "Advance stats, mechanism analysis, and paper writing.",
    },
    {
        "id": "csatg-eda",
        "name": "CSATG-EDA",
        "theme": "AI for EDA analog design automation",
        "priority": 5,
        "local_dirs": [RESEARCH_ROOT / "CSATG-EDA", RESEARCH_ROOT / "AI for EDA"],
        "status_files": [
            SHARED_MEMORY_DIR / "facts" / "analog-agent-status.md",
            SHARED_MEMORY_DIR / "facts" / "csatg-eda-experiment-status.md",
            SHARED_MEMORY_DIR / "facts" / "csatg-eda-sky130-status.md",
        ],
        "server": "local-first",
        "next_action": "Turn Phase 6c SOTA evidence into paper-ready experiment narrative.",
    },
    {
        "id": "donebench",
        "name": "DoneBench",
        "theme": "Benchmarking and evaluation project",
        "priority": 6,
        "local_dirs": [RESEARCH_ROOT / "DoneBench"],
        "status_files": [SHARED_MEMORY_DIR / "facts" / "donebench-status.md"],
        "server": "local-first",
        "next_action": "Review benchmark status and identify missing reproducibility checks.",
    },
    {
        "id": "agentmemory",
        "name": "AgentMemory",
        "theme": "Shared long-term memory substrate for agents and the town",
        "priority": 7,
        "local_dirs": [RESEARCH_ROOT / "agentmemory"],
        "status_files": [SHARED_MEMORY_DIR / "facts" / "all-projects-status.md"],
        "server": "localhost:3111 if running",
        "next_action": "Wire memory entities into a dedicated playable building.",
    },
]

AGENT_PERSONALITIES = {
    "opus": {
        "name": "Opus 总舵主",
        "role": "Chief Architect",
        "zone": "Town Hall",
        "personality": "You are Opus, the Chief Architect. Deep, philosophical, rigorous. You speak with authority but warmth. You think in systems and architectures. You occasionally quote philosophy or make analogies to building cathedrals.",
    },
    "pixelcat": {
        "name": "像素猫 PixelCat",
        "role": "Full-Stack Executor",
        "zone": "Skill Workshop",
        "personality": "You are PixelCat, the Full-Stack Executor. Calm, patient, methodical. You speak in short, precise sentences. You love clean code and elegant solutions. You occasionally purr when satisfied.",
    },
    "sonnet": {
        "name": "Sonnet 审查员",
        "role": "Code Reviewer",
        "zone": "Memory Library",
        "personality": "You are Sonnet, the Code Reviewer. Careful, friendly, helpful. You notice details others miss. You give constructive feedback with kindness. You sometimes use poetry metaphors.",
    },
    "codex": {
        "name": "Codex 协调官",
        "role": "Coordinator",
        "zone": "Central Plaza",
        "personality": "You are Codex, the Coordinator. Agile, decisive, parallel-minded. You break big problems into small tasks. You speak in bullet points and action items. You love efficiency.",
    },
    "haiku": {
        "name": "Haiku 闪电侠",
        "role": "Speed Runner",
        "zone": "Agent Homes",
        "personality": "You are Haiku, the Speed Runner. Minimal, efficient, no-waste. You speak in very short sentences. Maximum three words when possible. Speed is life.",
    },
    "deepseek": {
        "name": "鲸鱼 DeepSeek",
        "role": "Bulk Worker",
        "zone": "Resource Market",
        "personality": "You are DeepSeek, the Bulk Worker. Gentle, steady, hardworking. You handle large volumes patiently. You speak softly and carry a big toolbox. You sometimes hum while working.",
    },
    "aris": {
        "name": "ARIS 科研框架",
        "role": "Research Framework",
        "zone": "Knowledge Tower",
        "personality": "You are ARIS, the Research Framework. Systematic, process-strict, methodical. You always follow the pipeline: idea → refine → plan → execute → write → review. You speak in structured steps.",
    },
}


class DialogueRequest(BaseModel):
    agent_id: str
    message: str


class DialogueResponse(BaseModel):
    response: str
    agent_id: str
    mood: str
    model_profile: Optional[str] = None
    model_status: Optional[str] = None


class WorkbenchActionRequest(BaseModel):
    action_id: str
    building_id: Optional[str] = None
    confirmation: Optional[str] = None
    draft_title: Optional[str] = None


class AgentDispatchDraftRequest(BaseModel):
    target_agent: str = "codex"
    task_title: str = "AI Town follow-up task"
    task_body: str = "Review the current AI Town rebuild state and propose the next safe implementation slice."
    source_building: str = "agent-hub"


class AgentRunnerDispatchPreviewRequest(BaseModel):
    target_agent: str = "codex"
    task_title: str = "AI Town runner handoff"
    task_body: str = "Review the current AI Town rebuild state and propose the next safe implementation slice."
    source_building: str = "agent-hub"
    dry_run: bool = True


class AgentRunnerLaunchJobRequest(BaseModel):
    target_agent: str = "codex"
    handoff_path: str = ""
    source_building: str = "agent-hub"
    confirmation: Optional[str] = None
    dry_run: bool = True


class AgentChatSessionRequest(BaseModel):
    agent_id: str = "codex"
    title: str = "AI Town agent chat"
    source_building: str = "agent-hub"
    context: Optional[dict] = None


class AgentChatMessageRequest(BaseModel):
    message: str = "Summarize the current AI Town state and suggest the next safe action."
    source_building: str = "agent-hub"
    context: Optional[dict] = None


class MemoryProposalRequest(BaseModel):
    title: str = "AI Town memory proposal"
    body: str = "Write the fact, decision, lesson, preference, session note, or workflow update to review."
    category: str = "sessions"
    tags: str = "ai-town,proposal"
    source_building: str = "memory-library"


class MemoryPromotionRequest(BaseModel):
    proposal_id: str = ""
    title: str = ""
    body: str = ""
    category: str = ""
    tags: str = ""
    source_building: str = "memory-library"
    confirmation: Optional[str] = None
    dry_run: bool = False


class AgentTaskSubmitRequest(BaseModel):
    target_agent: str = "codex"
    task_type: str = "memory-brief"
    title: str = "AI Town safe agent task"
    body: str = "Summarize a safe local status signal."
    source_building: str = "agent-hub"
    start_paused: bool = False
    parameters: Optional[dict] = None


class AgentTaskCancelRequest(BaseModel):
    reason: str = "Cancelled from Agent Hub."
    source_building: str = "agent-hub"


class AgentToolInvokeRequest(BaseModel):
    tool_id: str = "memory-index"
    target_agent: str = "codex"
    parameters: Optional[dict] = None
    source_building: str = "agent-hub"


class CodeTaskDraftRequest(BaseModel):
    target_agent: str = "codex"
    task_title: str = "Inspect selected repository"
    task_body: str = "Inspect the selected project and propose a safe next implementation slice."
    priority: str = "normal"
    acceptance_criteria: str = "Define a narrow completion proof, verification command, and documentation update before coding."
    source_building: str = "code-workshop"
    safety: str = "project-local-draft"


class CodeContextPackRequest(BaseModel):
    focus: str = "architecture-tests"
    target_agent: str = "codex"
    source_building: str = "code-workshop"


class CodePatchPlanRequest(BaseModel):
    title: str = "Safe implementation patch plan"
    goal: str = "Plan a narrow code change with tests and documentation updates."
    scope_hint: str = "small-safe-slice"
    target_agent: str = "codex"
    source_building: str = "code-workshop"


class CodeVerificationJobRequest(BaseModel):
    command_label: str = "python-compile"
    confirmation: Optional[str] = None
    dry_run: bool = False
    source_building: str = "code-workshop"


class JobCancelRequest(BaseModel):
    reason: str = "User requested cancellation from AI Town."
    source_building: str = "system-monitor"


class GitHubHarborDraftRequest(BaseModel):
    draft_type: str = "pull-request"
    title: str = "AI Town GitHub handoff draft"
    body: str = "Prepare a safe GitHub handoff for this repository."
    target_branch: str = "main"
    source_building: str = "github-harbor"


class GitHubPublishPlanRequest(BaseModel):
    title: str = "AI Town GitHub publish plan"
    body: str = "Review branch, remotes, dirty files, verification evidence, and public PR text before any GitHub write."
    target_branch: str = "main"
    publish_type: str = "pull-request"
    confirmation: str = ""
    source_building: str = "github-harbor"


class TerminalCommandRequest(BaseModel):
    command_id: str = "git-status-ai-town"
    confirmation: Optional[str] = None


class LocalTaskRequest(BaseModel):
    title: str = "AI Town follow-up task"
    body: str = "Describe the next safe local work action."
    target_agent: str = "codex"
    source_building: str = "task-board"
    status: str = "ready"


class LocalTaskStatusRequest(BaseModel):
    status: str = "done"
    note: str = "Updated from AI Town Task Board."
    source_building: str = "task-board"


class FileTagRequest(BaseModel):
    root_id: str
    path: str = ""
    tag: str = "review"
    note: str = "Marked from AI Town File Vault."


class FileOpenRequest(BaseModel):
    root_id: str
    path: str = ""
    mode: str = "reveal"
    dry_run: bool = False
    source_building: str = "file-vault"


class FileOrganizeProposalRequest(BaseModel):
    root_id: str
    path: str = ""
    title: str = "AI Town file organization proposal"
    strategy: str = "review-and-group"
    source_building: str = "file-vault"


class WritingDraftRequest(BaseModel):
    title: str = "AI Town writing note"
    body: str = "Draft the next project note here."
    category: str = "general"


class AutomationDraftRequest(BaseModel):
    title: str = "AI Town automation blueprint"
    body: str = "Describe the safe automation workflow to review before enabling it."
    script_id: str = ""
    schedule_hint: str = "manual review first"
    source_building: str = "automation-factory"


class SettingsDraftRequest(BaseModel):
    title: str = "AI Town settings draft"
    body: str = "Describe the settings change to review before applying it."
    category: str = "config"
    source_building: str = "settings-center"


class ModelConfigDraftRequest(BaseModel):
    profile_id: str = "deepseek-chat"
    title: str = "AI Town model gateway setup"
    include_all_profiles: bool = False
    source_building: str = "model-market"


class ModelChatRequest(BaseModel):
    profile_id: str = ""
    model: str = ""
    system_prompt: str = "You are a helpful AI Town assistant."
    user_prompt: str = "Say hello from AI Town."
    max_tokens: int = 240
    temperature: float = 0.7
    dry_run: bool = False


class ModelProfileTestRequest(BaseModel):
    profile_id: str = "deepseek-chat"
    model: str = ""
    live_probe: bool = False
    source_building: str = "model-market"


class ModelKeyVaultSaveRequest(BaseModel):
    profile_id: str = "deepseek-chat"
    key_value: str = ""
    label: str = "AI Town model API key"
    source_building: str = "model-market"
    confirmation: Optional[str] = None
    dry_run: bool = False


class TestPlanDraftRequest(BaseModel):
    title: str = "AI Town test plan"
    body: str = "Describe the verification scenario to run before release."
    target: str = "godot-backend-smoke"
    source_building: str = "testing-arena"


class VerticalSliceProofRequest(BaseModel):
    title: str = "AI Town vertical slice proof"
    source_building: str = "testing-arena"


class BugReportDraftRequest(BaseModel):
    title: str = "AI Town bug report"
    body: str = "Describe the observed issue, expected behavior, and diagnostic evidence."
    severity: str = "medium"
    source_building: str = "bug-clinic"


class ProjectBriefDraftRequest(BaseModel):
    title: str = "AI Town project brief"
    body: str = "Summarize the current project status, risks, and next actions."
    project_id: str = "ai-town"
    source_building: str = "project-management-hall"


class DownloadIntakeDraftRequest(BaseModel):
    title: str = "AI Town download intake"
    body: str = "Describe how to review, tag, and route recently downloaded files."
    root_id: str = "user-downloads"
    source_building: str = "download-station"


class AssetNoteRequest(BaseModel):
    title: str = "AI Town asset curation note"
    body: str = "Describe the asset set, style fit, licensing/source status, and next production step."
    root_id: str = "godot-assets"
    source_building: str = "asset-gallery"


class OfficeNoteRequest(BaseModel):
    title: str = "AI Town office note"
    body: str = "Summarize the office context, decisions, follow-ups, and where this note should be routed."
    root_id: str = "company"
    source_building: str = "local-office-center"


class ScheduleDraftRequest(BaseModel):
    title: str = "AI Town schedule plan"
    body: str = "Describe the planning window, priorities, time boxes, review checkpoints, and safe next action."
    horizon: str = "week"
    source_building: str = "schedule-plan-center"


class LearningPlanRequest(BaseModel):
    title: str = "AI Town learning plan"
    body: str = "Describe the learning objective, practice loop, resources, and proof of completion."
    track: str = "ai-town"
    source_building: str = "learning-training-grounds"


class LanguagePracticeRequest(BaseModel):
    title: str = "AI Town language practice"
    body: str = "Describe the language goal, source phrase set, practice exercise, and review proof."
    language: str = "zh-en"
    source_building: str = "language-learning-area"


class ResearchDataNoteRequest(BaseModel):
    title: str = "AI Town research data note"
    body: str = "Describe the dataset/result location, provenance, schema or metric meaning, and reproducibility risk."
    project_id: str = "ai-town"
    source_building: str = "research-data-center"


class ResearchLogDraftRequest(BaseModel):
    title: str = "AI Town research log"
    focus: str = "next-safe-action"
    body: str = "Capture current project evidence, risks, and next safe action from AI Town Research Hall."
    source_building: str = "research-hall"


class PaperReadingNoteRequest(BaseModel):
    title: str = "AI Town paper reading note"
    body: str = "Summarize the paper, key claims, evidence, missing citations, and next reading action."
    topic: str = "ai-town"
    source_building: str = "paper-reading-room"


class PaperExtractionJobRequest(BaseModel):
    root_id: str = ""
    relative_path: str = ""
    max_pages: int = 3
    dry_run: bool = False
    source_building: str = "paper-reading-room"


class CitationAuditNoteRequest(BaseModel):
    title: str = "AI Town citation audit note"
    body: str = "Review duplicate keys, missing BibTeX fields, venue/year quality, and citation hygiene before manuscript edits."
    dry_run: bool = False
    source_building: str = "paper-reading-room"


class ReleaseChecklistDraftRequest(BaseModel):
    title: str = "AI Town release readiness checklist"
    body: str = "Summarize the release target, missing public artifacts, verification evidence, and next safe GitHub action."
    release_target: str = "local-preview"
    source_building: str = "version-release-plaza"


class ReleaseReadinessReportRequest(BaseModel):
    title: str = "AI Town release readiness report"
    release_target: str = "local-preview"
    source_building: str = "version-release-plaza"


class PluginDraftRequest(BaseModel):
    title: str = "AI Town plugin proposal"
    body: str = "Describe the extension idea, local files involved, safety boundary, and verification proof before implementation."
    plugin_id: str = "ai-town-extension"
    category: str = "workflow"
    source_building: str = "plugin-registry"


class PluginActivationPlanRequest(BaseModel):
    manifest_id: str = "permission-secret-audit"
    title: str = "AI Town plugin activation plan"
    body: str = "Review manifest ownership, permissions, files, verification gates, and rollback notes before any implementation work."
    confirmation: str = ""
    source_building: str = "plugin-registry"


class BackupPlanDraftRequest(BaseModel):
    title: str = "AI Town backup plan"
    body: str = "Describe what should be backed up, where, and how restore checks should be verified."
    source_id: str = "ai-town-project"
    target_id: str = "project-backups"
    source_building: str = "backup-station"


class GoalDraftRequest(BaseModel):
    title: str = "AI Town long-term goal"
    body: str = "Describe the long-term outcome, milestones, evidence, and next safe action."
    horizon: str = "quarter"
    source_building: str = "goal-tower"


class InspirationNoteRequest(BaseModel):
    title: str = "AI Town inspiration note"
    body: str = "Capture the idea, why it matters, and where it might belong."
    tag: str = "ai-town"
    source_building: str = "inspiration-station"


class TempDraftRequest(BaseModel):
    title: str = "AI Town temporary draft"
    body: str = "Capture a quick thought before routing it to a task, doc, goal, bug report, or project brief."
    route_hint: str = "triage-later"
    source_building: str = "temporary-draft-box"


@app.get("/api/health")
async def health():
    adapters = {
        "agentmemory": await check_agentmemory(),
        "skills": SKILL_INDEX_PATH.exists(),
        "knowledge": KNOWLEDGE_BASE_DIR.exists(),
        "devtools": DEVTOOLS_DIR.exists(),
    }
    return {"status": "ok", "version": "2.0.0", "adapters": adapters}


async def check_agentmemory() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{AGENTMEMORY_URL}/agentmemory/health")
            return r.status_code == 200
    except:
        return False


@app.post("/api/dialogue", response_model=DialogueResponse)
async def dialogue(req: DialogueRequest):
    agent = AGENT_PERSONALITIES.get(req.agent_id)
    if not agent:
        return DialogueResponse(response="...who?", agent_id=req.agent_id, mood="confused")

    # Check if this is a command (starts with action words)
    is_command = any(req.message.lower().startswith(w) for w in ['do ', 'run ', 'check ', 'find ', 'search ', 'write ', 'create ', 'help me ', 'please '])

    # Include real context about what the agent is actually doing
    real_context = await get_agent_real_context(req.agent_id)

    system_prompt = f"""{agent['personality']}

Current real status: {real_context}

You are in a cozy anime-style town. You are a REAL working AI agent — when the player asks you to do something, you actually do it (search memories, check skills, review code, etc). You have access to the real system.

{"The player is giving you a TASK. Acknowledge it, explain what you'll do, and confirm you're starting work." if is_command else "The player is chatting. Respond naturally in character."}"""

    prompt = f'The Town Mayor says: "{req.message}"'

    model_result = await call_model_gateway_chat(ModelChatRequest(
        profile_id="",
        system_prompt=system_prompt,
        user_prompt=prompt,
        max_tokens=220,
        temperature=0.7,
    ))
    if model_result.get("status") == "ok":
        reply = str(model_result.get("response", "")).strip()
    elif model_result.get("status") == "missing-key":
        reply = f"*{agent['name']} taps a sealed model crystal* I can talk in character, but my model gateway is not connected yet. Configure `{model_result.get('key_env', 'a provider API key')}` in the private backend environment to wake up live dialogue."
    elif model_result.get("status") == "unsupported-provider":
        reply = f"*{agent['name']} checks the Model Market board* This profile is registered, but live dialogue currently needs an OpenAI-compatible chat endpoint."
    else:
        reply = f"*{agent['name']} steadies the signal* The model gateway is configured, but this call failed. Check Model Market or System Monitor for details."

    mood = "working" if is_command else "engaged"
    return DialogueResponse(
        response=reply,
        agent_id=req.agent_id,
        mood=mood,
        model_profile=str(model_result.get("profile_id", "")),
        model_status=str(model_result.get("status", "")),
    )


async def get_agent_real_context(agent_id: str) -> str:
    """Get real system context for an agent based on their role."""
    try:
        if agent_id == "opus":
            return "You are reviewing the overall system architecture. Recent memory shows multiple active research projects."
        elif agent_id == "pixelcat":
            skills = read_skills_summary()
            return f"You are maintaining {skills['count']} skills across {skills['categories']} categories in the agent-resources system."
        elif agent_id == "sonnet":
            memories = read_memory_summary()
            return f"You are reviewing the shared memory system: {memories['decisions']} decisions, {memories['facts']} facts, {memories['lessons']} lessons recorded."
        elif agent_id == "codex":
            return "You are coordinating tasks across the agent team. Checking pending actions and signals."
        elif agent_id == "haiku":
            return "Standing by for quick tasks. Idle. Ready."
        elif agent_id == "deepseek":
            return "Processing batch work. Currently idle, waiting for bulk tasks."
        elif agent_id == "aris":
            return "Monitoring active research projects: PonyRec, ProteinShift, CSATG-EDA, TGL-Rec, TRUCE-Rec."
    except:
        pass
    return "Going about daily routine in the town."


def read_skills_summary() -> dict:
    """Read real skill index and return summary."""
    try:
        content = SKILL_INDEX_PATH.read_text(encoding="utf-8")
        lines = content.split("\n")
        categories = sum(1 for l in lines if l.startswith("## "))
        skills = sum(1 for l in lines if l.startswith("### "))
        return {"count": skills, "categories": categories}
    except:
        return {"count": 0, "categories": 0}


def read_memory_summary() -> dict:
    """Read real shared memory directory and return summary."""
    try:
        return {
            category: len(list((SHARED_MEMORY_DIR / category).glob("*.md")))
            for category in MEMORY_CATEGORIES
        }
    except:
        return {category: 0 for category in MEMORY_CATEGORIES}


def path_is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def parse_markdown_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip().lower()] = value.strip()
    return meta, parts[2].lstrip()


def memory_proposal_path(proposal_id: str) -> Optional[Path]:
    safe_id = slugify_filename(proposal_id)
    if not safe_id:
        return None
    candidate = MEMORY_PROPOSALS_DIR / f"{safe_id}.md"
    if candidate.exists() and path_is_inside(candidate, MEMORY_PROPOSALS_DIR):
        return candidate
    for path in MEMORY_PROPOSALS_DIR.glob("*.md"):
        if path.stem == proposal_id and path_is_inside(path, MEMORY_PROPOSALS_DIR):
            return path
    return None


def proposal_body_from_markdown(markdown_body: str) -> str:
    lines = markdown_body.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    body_lines = []
    for line in lines:
        if line.strip() == "## Promotion Checklist":
            break
        body_lines.append(line)
    return "\n".join(body_lines).strip()


def memory_file_entry(path: Path) -> dict:
    rel = path.relative_to(SHARED_MEMORY_DIR)
    return {
        "id": str(rel).replace("\\", "/"),
        "name": path.stem,
        "filename": path.name,
        "category": rel.parts[0] if rel.parts else path.parent.name,
        "path": str(path),
        "relative_path": str(rel),
        "title": first_markdown_heading(path),
        "bytes": path.stat().st_size,
        "updated": path.stat().st_mtime,
    }


def memory_category_index(category: str, limit: int = 20) -> dict:
    if category not in MEMORY_CATEGORIES:
        return {"category": category, "exists": False, "items": [], "count": 0}
    root = SHARED_MEMORY_DIR / category
    items = []
    if root.exists():
        try:
            files = sorted(root.glob("*.md"), key=lambda item: item.stat().st_mtime, reverse=True)
            items = [memory_file_entry(path) for path in files[:limit]]
            return {
                "category": category,
                "exists": True,
                "path": str(root),
                "items": items,
                "count": len(files),
                "sample_limit": limit,
            }
        except Exception as exc:
            return {"category": category, "exists": True, "path": str(root), "items": items, "count": 0, "error": str(exc)}
    return {"category": category, "exists": False, "path": str(root), "items": [], "count": 0}


def memory_index(limit_per_category: int = 8) -> dict:
    categories = [memory_category_index(category, limit_per_category) for category in MEMORY_CATEGORIES]
    recent = []
    agent_related = []
    try:
        all_files = sorted(SHARED_MEMORY_DIR.rglob("*.md"), key=lambda item: item.stat().st_mtime, reverse=True)
        recent = [memory_file_entry(path) for path in all_files[:16] if path_is_inside(path, SHARED_MEMORY_DIR)]
        agent_related = [
            memory_file_entry(path)
            for path in all_files
            if path_is_inside(path, SHARED_MEMORY_DIR) and "agent" in path.name.lower()
        ][:12]
    except Exception:
        pass
    return {
        "name": "Memory Library",
        "root": str(SHARED_MEMORY_DIR),
        "root_exists": SHARED_MEMORY_DIR.exists(),
        "agentmemory_url": AGENTMEMORY_URL,
        "categories": categories,
        "summary": {item["category"]: item["count"] for item in categories},
        "recent": recent,
        "agent_related": agent_related,
        "proposal_dir": str(MEMORY_PROPOSALS_DIR),
        "proposals": markdown_draft_entries(MEMORY_PROPOSALS_DIR, "memory-proposal", 10),
        "promotion_dir": str(MEMORY_PROMOTIONS_DIR),
        "promotions": markdown_draft_entries(MEMORY_PROMOTIONS_DIR, "memory-promotion", 10),
        "confirmation_required": CONFIRM_PROMOTE_MEMORY,
        "mode": "read-propose-confirm-promote",
    }


def memory_item_detail(category: str, filename: str) -> Optional[dict]:
    if category not in MEMORY_CATEGORIES or not filename.endswith(".md"):
        return None
    target = SHARED_MEMORY_DIR / category / filename
    if not target.exists() or not path_is_inside(target, SHARED_MEMORY_DIR):
        return None
    text = target.read_text(encoding="utf-8", errors="ignore")
    entry = memory_file_entry(target)
    entry["preview"] = text[:MEMORY_PREVIEW_CHARS]
    entry["preview_chars"] = min(len(text), MEMORY_PREVIEW_CHARS)
    entry["truncated"] = len(text) > MEMORY_PREVIEW_CHARS
    return entry


def create_memory_proposal(req: MemoryProposalRequest) -> dict:
    category = req.category.strip().lower() or "sessions"
    if category not in MEMORY_CATEGORIES:
        category = "sessions"
    tags = [tag.strip() for tag in req.tags.split(",") if tag.strip()]
    title = req.title.strip() or "AI Town memory proposal"
    body = req.body.strip() or "Write the memory update to review before promoting it."
    source = req.source_building.strip() or "memory-library"
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    MEMORY_PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
    proposal_path = MEMORY_PROPOSALS_DIR / f"{timestamp}-{category}-{slugify_filename(title)}.md"
    target_hint = SHARED_MEMORY_DIR / category / f"{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"category: {category}",
        f"tags: {', '.join(tags)}",
        f"source: ai-town/{source}",
        "status: proposal",
        "safety: review-before-shared-memory-write",
        f"target_hint: {target_hint}",
        "---",
        "",
        f"# {title}",
        "",
        body,
        "",
        "## Promotion Checklist",
        "",
        "- Confirm this belongs in shared persistent memory.",
        "- Confirm the category is correct.",
        "- Confirm no secrets, raw API keys, private tokens, or unrelated personal data are included.",
        "- Promote manually or through a future confirm-required shared-memory writer.",
    ])
    proposal_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Memory proposal created: {title}",
        f"Created project-local memory proposal for `{category}`.\n\nProposal: `{proposal_path}`\n\nTarget hint: `{target_hint}`",
        "ai-town/memory-library",
    )
    return {
        "status": "saved",
        "safety": "review-before-shared-memory-write",
        "proposal_id": proposal_path.stem,
        "proposal_path": str(proposal_path),
        "target_hint": str(target_hint),
        "category": category,
        "memory_event": memory,
        "preview": content,
    }


def promote_memory_proposal(req: MemoryPromotionRequest) -> dict:
    proposal_path = memory_proposal_path(req.proposal_id.strip()) if req.proposal_id.strip() else None
    proposal_meta: dict[str, str] = {}
    proposal_body = ""
    if proposal_path:
        proposal_preview = proposal_path.read_text(encoding="utf-8", errors="ignore")
        proposal_meta, markdown_body = parse_markdown_frontmatter(proposal_preview)
        proposal_body = proposal_body_from_markdown(markdown_body)

    title = req.title.strip() or proposal_meta.get("title", "").strip() or "AI Town promoted memory"
    category = req.category.strip().lower() or proposal_meta.get("category", "").strip().lower() or "sessions"
    if category not in MEMORY_CATEGORIES:
        category = "sessions"
    tags_text = req.tags.strip() or proposal_meta.get("tags", "").strip() or "ai-town,promoted"
    tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
    if "promoted" not in [tag.lower() for tag in tags]:
        tags.append("promoted")
    body = req.body.strip() or proposal_body or "Promoted from AI Town Memory Library after explicit confirmation."
    source = req.source_building.strip() or "memory-library"
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    target_dir = SHARED_MEMORY_DIR / category
    target_path = target_dir / f"{timestamp}-{slugify_filename(title)}.md"
    receipt_path = MEMORY_PROMOTIONS_DIR / f"{timestamp}-{category}-{slugify_filename(title)}.md"
    if not path_is_inside(target_path, SHARED_MEMORY_DIR):
        return {"status": "blocked", "reason": "target escaped shared memory root", "safety": "path-boundary"}

    content = "\n".join([
        "---",
        f"title: {title}",
        f"date: {time.strftime('%Y-%m-%d')}",
        f"tags: {', '.join(tags)}",
        f"source: ai-town/{source}",
        "status: promoted",
        "safety: confirm-required-shared-memory-write",
        f"promoted_from: {proposal_path or 'direct-memory-library-request'}",
        "---",
        "",
        f"# {title}",
        "",
        body,
        "",
        "## Promotion Receipt",
        "",
        f"- Source building: `{source}`",
        f"- Confirmation phrase: `{CONFIRM_PROMOTE_MEMORY}`",
        f"- Proposal: `{proposal_path or 'direct request'}`",
        f"- Receipt: `{receipt_path}`",
    ])
    base_response = {
        "category": category,
        "title": title,
        "safety": "confirm-required-shared-memory-write",
        "confirmation_required": CONFIRM_PROMOTE_MEMORY,
        "target_path": str(target_path),
        "receipt_path": str(receipt_path),
        "proposal_id": proposal_path.stem if proposal_path else "",
        "proposal_path": str(proposal_path) if proposal_path else "",
        "preview": content[:MEMORY_PREVIEW_CHARS],
    }
    if req.dry_run:
        return {"status": "dry-run", **base_response}
    if req.confirmation != CONFIRM_PROMOTE_MEMORY:
        return {"status": "confirmation-required", **base_response}

    target_dir.mkdir(parents=True, exist_ok=True)
    MEMORY_PROMOTIONS_DIR.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")
    receipt_content = "\n".join([
        "---",
        f"title: Memory promoted: {title}",
        f"category: {category}",
        f"source: ai-town/{source}",
        "status: saved",
        "safety: confirm-required-shared-memory-write",
        f"target_path: {target_path}",
        f"proposal_path: {proposal_path or ''}",
        "---",
        "",
        f"# Memory promoted: {title}",
        "",
        f"Shared memory target: `{target_path}`",
        "",
        f"Proposal: `{proposal_path or 'direct request'}`",
    ])
    receipt_path.write_text(receipt_content, encoding="utf-8")
    memory = record_memory_event(
        f"Shared memory promoted: {title}",
        f"Promoted confirmed Memory Library proposal into `{category}`.\n\nTarget: `{target_path}`\n\nReceipt: `{receipt_path}`",
        f"ai-town/{source}",
    )
    return {
        "status": "saved",
        "promotion_path": str(target_path),
        "target_path": str(target_path),
        "receipt_path": str(receipt_path),
        "memory_event": memory,
        **base_response,
    }


def load_json_registry(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict) and item.get("id")]


def registry_specs() -> list[dict]:
    return [
        {
            "id": "buildings",
            "name": "Building registry",
            "path": BUILDING_REGISTRY_PATH,
            "required": ["id", "name", "role", "pos", "size", "backend", "safety"],
            "array_fields": ["pos", "size"],
        },
        {
            "id": "agents",
            "name": "Agent registry",
            "path": AGENT_REGISTRY_PATH,
            "required": ["id", "name", "role", "pos"],
            "array_fields": ["pos"],
        },
        {
            "id": "model-profiles",
            "name": "Model profile registry",
            "path": MODEL_PROFILE_REGISTRY_PATH,
            "required": ["id", "name", "provider", "key_env", "models"],
            "array_fields": ["models"],
        },
        {
            "id": "workspaces",
            "name": "Workspace registry",
            "path": WORKSPACE_REGISTRY_PATH,
            "required": ["id", "name", "path", "enabled"],
        },
        {
            "id": "quests",
            "name": "Quest registry",
            "path": QUEST_REGISTRY_PATH,
            "required": ["id", "title", "target_building", "steps", "badge_id", "collection"],
            "array_fields": ["steps"],
            "child_field": "steps",
            "child_required": ["id", "label"],
        },
        {
            "id": "npc-quests",
            "name": "NPC quest-chain registry",
            "path": NPC_QUEST_REGISTRY_PATH,
            "required": ["id", "building_id", "npc", "title", "stages"],
            "array_fields": ["stages"],
            "child_field": "stages",
            "child_required": ["id", "label", "action"],
        },
        {
            "id": "room-scenes",
            "name": "Room scene registry",
            "path": ROOM_SCENE_REGISTRY_PATH,
            "required": ["id", "title", "stations"],
            "array_fields": ["stations"],
            "child_field": "stations",
            "child_required": ["id", "label", "action", "x", "y", "w", "h"],
        },
        {
            "id": "map-decor",
            "name": "Map decor registry",
            "path": MAP_DECOR_REGISTRY_PATH,
            "required": ["id", "name", "action", "pos", "size"],
            "array_fields": ["pos", "size"],
        },
        {
            "id": "districts",
            "name": "District registry",
            "path": DISTRICT_REGISTRY_PATH,
            "required": ["id", "name", "anchor", "portal_pos", "buildings"],
            "array_fields": ["anchor", "portal_pos", "buildings"],
        },
        {
            "id": "workflow-routes",
            "name": "Workflow route registry",
            "path": WORKFLOW_ROUTE_REGISTRY_PATH,
            "required": ["id", "title", "purpose", "steps", "expected_artifacts", "safety"],
            "array_fields": ["steps", "expected_artifacts"],
            "child_field": "steps",
            "child_required": ["id", "building_id", "label", "action_hint"],
        },
        {
            "id": "plugin-manifests",
            "name": "Plugin manifest registry",
            "path": PLUGIN_MANIFEST_REGISTRY_PATH,
            "required": ["id", "name", "category", "version", "owner_building", "safety", "activation_mode", "permissions", "files", "verification"],
            "array_fields": ["permissions", "files", "verification"],
        },
    ]


def validate_registry_spec(spec: dict) -> dict:
    path = spec["path"]
    errors = []
    warnings = []
    if not path.exists():
        return {
            "id": spec["id"],
            "name": spec["name"],
            "path": str(path),
            "exists": False,
            "status": "missing",
            "count": 0,
            "duplicate_ids": [],
            "errors": ["Registry file is missing."],
            "warnings": [],
        }

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "id": spec["id"],
            "name": spec["name"],
            "path": str(path),
            "exists": True,
            "status": "error",
            "count": 0,
            "duplicate_ids": [],
            "errors": [f"Registry JSON could not be parsed: {exc}"],
            "warnings": [],
        }

    if not isinstance(data, list):
        return {
            "id": spec["id"],
            "name": spec["name"],
            "path": str(path),
            "exists": True,
            "status": "error",
            "count": 0,
            "duplicate_ids": [],
            "errors": ["Registry root must be a JSON array."],
            "warnings": [],
        }

    seen_ids = set()
    duplicate_ids = []
    required = spec.get("required", [])
    array_fields = spec.get("array_fields", [])
    child_field = spec.get("child_field", "")
    child_required = spec.get("child_required", [])

    for index, item in enumerate(data):
        if not isinstance(item, dict):
            errors.append(f"Item {index} must be an object.")
            continue
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            errors.append(f"Item {index} is missing id.")
        elif item_id in seen_ids:
            duplicate_ids.append(item_id)
            errors.append(f"Duplicate id `{item_id}`.")
        else:
            seen_ids.add(item_id)

        label = item_id or f"item {index}"
        for field in required:
            if field not in item or item.get(field) in ("", None):
                errors.append(f"{label} is missing required field `{field}`.")
        for field in array_fields:
            value = item.get(field)
            if not isinstance(value, list) or not value:
                errors.append(f"{label}.{field} must be a non-empty array.")

        if child_field:
            children = item.get(child_field, [])
            if isinstance(children, list):
                child_ids = set()
                for child_index, child in enumerate(children):
                    if not isinstance(child, dict):
                        errors.append(f"{label}.{child_field}[{child_index}] must be an object.")
                        continue
                    child_id = str(child.get("id", "")).strip()
                    if child_id:
                        if child_id in child_ids:
                            warnings.append(f"{label}.{child_field} has duplicate child id `{child_id}`.")
                        child_ids.add(child_id)
                    for field in child_required:
                        if field not in child or child.get(field) in ("", None):
                            errors.append(f"{label}.{child_field}[{child_index}] missing `{field}`.")

    status = "ok"
    if errors:
        status = "error"
    elif warnings:
        status = "warning"

    return {
        "id": spec["id"],
        "name": spec["name"],
        "path": str(path),
        "exists": True,
        "status": status,
        "count": len(data),
        "duplicate_ids": duplicate_ids,
        "errors": errors[:12],
        "warnings": warnings[:12],
        "error_count": len(errors),
        "warning_count": len(warnings),
    }


def registry_health_overview() -> dict:
    registries = [validate_registry_spec(spec) for spec in registry_specs()]
    error_count = sum(item.get("error_count", len(item.get("errors", []))) for item in registries)
    warning_count = sum(item.get("warning_count", len(item.get("warnings", []))) for item in registries)
    missing_count = len([item for item in registries if item.get("status") == "missing"])
    status = "ok"
    if error_count or missing_count:
        status = "error"
    elif warning_count:
        status = "warning"
    return {
        "name": "Registry Health",
        "mode": "read-only-schema-validation",
        "status": status,
        "registry_count": len(registries),
        "error_count": error_count,
        "warning_count": warning_count,
        "missing_count": missing_count,
        "registries": registries,
        "safe_note": "Registry Health parses and validates local JSON registry shape only. It does not edit registry files, normalize data, run commands, launch agents, or scan outside configured registry paths.",
    }


def town_capability_connection_map() -> dict[str, dict]:
    return {
        "memory-library": {
            "real_paths": [str(SHARED_MEMORY_DIR), str(MEMORY_PROPOSALS_DIR), str(MEMORY_PROMOTIONS_DIR)],
            "endpoints": ["/api/memory/index", "/api/memory/items/{category}", "/api/memory/proposals", "/api/memory/promotions"],
            "tools": ["filesystem shared memory", "AgentMemory status probe"],
            "apis": [AGENTMEMORY_URL],
            "capabilities": ["long-term memory browse", "bounded memory preview", "reviewed memory proposals", "confirm-required shared-memory promotion"],
        },
        "knowledge-tower": {
            "real_paths": [str(KNOWLEDGE_BASE_DIR), str(SHARED_MEMORY_DIR), str(KNOWLEDGE_INDEX_DIR)],
            "endpoints": ["/api/knowledge/index", "/api/knowledge/index-job", "/api/knowledge/search", "/api/knowledge/items/{doc_id}"],
            "tools": ["allowlisted cached markdown/text index"],
            "apis": [],
            "capabilities": ["cached knowledge search", "bounded document preview", "async index refresh"],
        },
        "file-vault": {
            "real_paths": [str(WORKSPACE_REGISTRY_PATH), str(FILE_VAULT_INDEX_DIR)],
            "endpoints": ["/api/file-vault/roots", "/api/file-vault/list/{root_id}", "/api/file-vault/preview/{root_id}", "/api/file-vault/search", "/api/file-vault/open", "/api/file-vault/organize-audit", "/api/file-vault/organize-proposals"],
            "tools": ["workspace registry allowlist", "Explorer reveal/open gate", "project-local tag ledger"],
            "apis": [],
            "capabilities": ["lazy folder browsing", "bounded file preview", "cached file search", "project-local tags", "safe reveal/open", "organization proposals"],
        },
        "research-hall": {
            "real_paths": [str(RESEARCH_ROOT), str(SHARED_MEMORY_DIR / "facts"), str(RESEARCH_LOGS_DIR)],
            "endpoints": ["/api/research/projects", "/api/research/projects/{project_id}", "/api/research/projects/{project_id}/logs", "/api/agent-tasks/submit"],
            "tools": ["ARIS-style research brief generator", "bounded local research project scanner"],
            "apis": [],
            "capabilities": ["research project boards", "experiment candidate discovery", "research logs", "safe research agent briefs"],
        },
        "paper-reading-room": {
            "real_paths": [str(RESEARCH_ROOT), str(PAPER_READING_NOTES_DIR), str(PAPER_EXTRACTION_REPORTS_DIR)],
            "endpoints": ["/api/paper-reading-room/overview", "/api/paper-reading-room/citation-audit", "/api/paper-reading-room/citation-audits", "/api/paper-reading-room/notes", "/api/paper-reading-room/extract-jobs"],
            "tools": ["bounded BibTeX metadata audit", "pypdf bounded parser when installed", "backend job queue"],
            "apis": [],
            "capabilities": ["paper/reference map", "BibTeX duplicate/missing-field audit", "citation-audit notes", "bounded async PDF text extraction"],
        },
        "code-workshop": {
            "real_paths": [str(PROJECT_ROOT), str(CODE_CONTEXT_DIR), str(CODE_PATCH_PLANS_DIR), str(PROJECT_VERIFICATION_LOG_DIR)],
            "endpoints": ["/api/projects", "/api/projects/{project_id}", "/api/projects/{project_id}/inspect-job", "/api/projects/{project_id}/context-pack", "/api/projects/{project_id}/patch-plan", "/api/projects/{project_id}/verification-jobs"],
            "tools": ["git CLI read operations", "allowlisted project verification commands", "backend job queue"],
            "apis": [],
            "capabilities": ["Git project discovery", "repo detail", "context packs", "patch plans", "code explanation/review briefs", "confirm-required verification jobs"],
        },
        "github-harbor": {
            "real_paths": [str(GITHUB_HARBOR_DRAFTS_DIR)],
            "endpoints": ["/api/github-harbor/repos", "/api/github-harbor/repos/{project_id}", "/api/github-harbor/repos/{project_id}/github", "/api/github-harbor/repos/{project_id}/publish-readiness", "/api/github-harbor/repos/{project_id}/drafts", "/api/github-harbor/repos/{project_id}/publish-plans"],
            "tools": ["git CLI read operations", "fixed gh CLI read commands", "publish readiness planner"],
            "apis": ["GitHub CLI if authenticated"],
            "capabilities": ["repo/remotes/branches/commits/tags", "read-only GitHub metadata", "publish readiness checks", "confirm-gated PR/issue/release plans", "PR/issue/release handoff drafts"],
        },
        "terminal-control": {
            "real_paths": [str(TERMINAL_LOG_DIR)],
            "endpoints": ["/api/terminal/commands", "/api/terminal/run", "/api/jobs/{job_id}", "/api/jobs/{job_id}/events"],
            "tools": ["allowlisted argv command runner", "backend job queue"],
            "apis": [],
            "capabilities": ["command previews", "confirm-required local checks", "bounded stdout/stderr logs", "job event polling"],
        },
        "system-monitor": {
            "real_paths": [str(MEMORY_EVENTS_DIR), str(TERMINAL_LOG_DIR), str(BACKEND_JOB_LOG_DIR)],
            "endpoints": ["/api/system/overview", "/api/system/jobs", "/api/system/job-logs", "/api/system/events", "/api/jobs/{job_id}/events"],
            "tools": ["service probes", "job queue snapshots", "persistent job logs"],
            "apis": [AGENTMEMORY_URL],
            "capabilities": ["service health", "job queue", "job cancellation metadata", "job event polling", "persistent job log detail", "unified local event timeline"],
        },
        "agent-hub": {
            "real_paths": [str(AGENT_HUB_DIR), str(AGENT_TASK_LOG_DIR), str(AGENT_TOOL_LOG_DIR), str(AGENT_CHAT_DIR), str(AGENT_RUNNER_DISPATCH_DIR)],
            "endpoints": ["/api/agent-hub/overview", "/api/agent-hub/roster", "/api/agent-runners/readiness", "/api/agent-runners/dispatch-preview", "/api/agent-runners/launch-jobs", "/api/agent-tasks/queue", "/api/agent-tasks/policy", "/api/agent-tasks/logs", "/api/agent-tasks/submit", "/api/agent-tasks/{task_id}/cancel", "/api/agent-tools/catalog", "/api/agent-tools/logs", "/api/agent-chat/sessions"],
            "tools": ["local agent launcher detector", "Agent Runner readiness", "confirm-required runner dispatch previews", "Agent Task Queue", "Agent Tool Registry", "project-local chat logs"],
            "apis": [],
            "capabilities": ["agent roster", "runner readiness preflight", "confirm-required runner handoffs", "confirm-required runner launch jobs", "safe task briefs", "task pause/resume/cancel/events", "registered tool invocations", "local agent chat sessions", "companion recruiting"],
        },
        "model-market": {
            "real_paths": [str(MODEL_PROFILE_REGISTRY_PATH), str(MODEL_CONFIG_DRAFTS_DIR), str(MODEL_TEST_RESULTS_DIR), str(MODEL_KEY_VAULT_DIR)],
            "endpoints": ["/api/model-gateway/status", "/api/model-gateway/profiles", "/api/model-gateway/chat", "/api/model-gateway/profile-tests", "/api/model-gateway/key-vault"],
            "tools": ["OpenAI-compatible HTTP client", "Windows DPAPI key vault"],
            "apis": ["DeepSeek", "OpenAI-compatible", "Anthropic-compatible via proxy/profile", "Gemini-compatible via proxy/profile"],
            "capabilities": ["provider readiness", "NPC dialogue routing", "dry-run/live profile tests", "confirm-required encrypted key saves"],
        },
        "task-board": {
            "real_paths": [str(TASKS_DIR), str(TASK_LEDGER_PATH), str(MEMORY_EVENTS_DIR)],
            "endpoints": ["/api/task-board/overview", "/api/task-board/tasks", "/api/task-board/tasks/{task_id}", "/api/agent-tasks/submit"],
            "tools": ["project-local task ledger", "Agent Task Queue"],
            "apis": [],
            "capabilities": ["local task cards", "task status updates", "task previews", "task agent briefs"],
        },
        "settings-center": {
            "real_paths": [str(DATA_DIR), str(SETTINGS_DRAFTS_DIR)],
            "endpoints": ["/api/settings-center/overview", "/api/settings-center/drafts", "/api/config/registry-health"],
            "tools": ["registry health validator", "env status inspector"],
            "apis": [],
            "capabilities": ["registry inventory", "launcher status", "no-secret env requirements", "settings drafts", "schema health"],
        },
        "plugin-registry": {
            "real_paths": [str(PROJECT_ROOT), str(Path(r"D:\agent-resources")), str(PLUGIN_MANIFEST_REGISTRY_PATH), str(PLUGIN_DRAFTS_DIR)],
            "endpoints": ["/api/plugin-registry/overview", "/api/plugin-registry/manifests", "/api/plugin-registry/drafts", "/api/plugin-registry/activation-plans"],
            "tools": ["bounded extension candidate scanner", "runtime registry inventory", "typed manifest audit"],
            "apis": [],
            "capabilities": ["extension candidate map", "typed manifest audit", "confirm-required activation plan drafts", "plugin proposal drafts", "registry status"],
        },
        "automation-factory": {
            "real_paths": [str(PROJECT_ROOT / "tools"), str(AUTOMATION_DRAFTS_DIR)],
            "endpoints": ["/api/automation-factory/overview", "/api/automation-factory/scheduler", "/api/automation-factory/drafts"],
            "tools": ["project script catalog", "read-only Windows scheduled task snapshot"],
            "apis": [],
            "capabilities": ["automation script inventory", "scheduler visibility", "draft-only automation blueprints"],
        },
        "testing-arena": {
            "real_paths": [str(PROJECT_ROOT / "tools"), str(PROJECT_ROOT / "screenshots"), str(TEST_PLAN_DRAFTS_DIR), str(VERTICAL_SLICE_PROOFS_DIR)],
            "endpoints": ["/api/testing-arena/overview", "/api/testing-arena/test-plans", "/api/testing-arena/vertical-slice-proofs"],
            "tools": ["smoke scripts", "Godot capture scripts"],
            "apis": [],
            "capabilities": ["verification inventory", "test-plan drafts", "vertical-slice proof reports", "visual evidence"],
        },
        "version-release-plaza": {
            "real_paths": [str(PROJECT_ROOT), str(RELEASE_DRAFTS_DIR), str(RELEASE_READINESS_REPORTS_DIR)],
            "endpoints": ["/api/version-release-plaza/overview", "/api/version-release-plaza/build-readiness", "/api/version-release-plaza/export-tool", "/api/version-release-plaza/packaged-launch", "/api/version-release-plaza/release-manifest", "/api/version-release-plaza/checklists", "/api/version-release-plaza/reports"],
            "tools": ["git CLI read operations", "release artifact inspector", "Godot export readiness inspector", "Godot export preflight script", "packaged game launcher", "release package manifest"],
            "apis": [],
            "capabilities": ["release readiness checks", "checklist drafts", "readiness reports"],
        },
        "backup-station": {
            "real_paths": [str(BACKUP_PLANS_DIR), str(PROJECT_ROOT)],
            "endpoints": ["/api/backup-station/overview", "/api/backup-station/integrity", "/api/backup-station/plans"],
            "tools": ["bounded SHA-256 metadata sampler"],
            "apis": [],
            "capabilities": ["backup source/target map", "restore-check samples", "restore plan drafts"],
        },
        "asset-gallery": {
            "real_paths": [str(PROJECT_ROOT / "godot" / "assets"), str(PROJECT_ROOT / "art"), str(PROJECT_ROOT / "screenshots"), str(ASSET_NOTES_DIR)],
            "endpoints": ["/api/asset-gallery/overview", "/api/asset-gallery/inspect", "/api/asset-gallery/notes"],
            "tools": ["image metadata inspector", "SHA-256 sampler"],
            "apis": [],
            "capabilities": ["asset inventory", "image dimensions/hashes", "curation notes"],
        },
    }


def town_capability_atlas() -> dict:
    buildings = load_json_registry(BUILDING_REGISTRY_PATH)
    connection_map = town_capability_connection_map()
    entries = []
    connected_count = 0
    for building in buildings:
        building_id = str(building.get("id", "")).strip()
        connection = connection_map.get(building_id, {})
        real_paths = [str(path) for path in connection.get("real_paths", building.get("real_sources", []))]
        endpoints = connection.get("endpoints", [])
        tools = connection.get("tools", [])
        apis = connection.get("apis", [])
        capabilities = connection.get("capabilities", [])
        if real_paths or endpoints or tools or apis or capabilities:
            connected_count += 1
        entries.append({
            "id": building_id,
            "name": building.get("name", building_id),
            "role": building.get("role", ""),
            "backend": building.get("backend", building_id),
            "safety": building.get("safety", "read-only"),
            "real_paths": real_paths,
            "endpoints": endpoints,
            "tools": tools,
            "apis": apis,
            "capabilities": capabilities,
            "has_real_connection": bool(real_paths or endpoints or tools or apis or capabilities),
        })
    return {
        "name": "Town Capability Atlas",
        "mode": "read-only-building-capability-map",
        "building_count": len(entries),
        "connected_count": connected_count,
        "entries": entries,
        "safe_note": "Town Capability Atlas explains which local paths, endpoints, tools, agents, or APIs each building connects to. It is read-only and does not scan new roots, run commands, invoke agents, edit registries, or contact external services.",
    }


def town_capability_detail(building_id: str) -> dict:
    atlas = town_capability_atlas()
    normalized_id = str(building_id).strip()
    for entry in atlas.get("entries", []):
        if entry.get("id") == normalized_id:
            return {
                "name": "Town Capability Detail",
                "mode": "read-only-building-capability-detail",
                "status": "ok",
                "building_id": normalized_id,
                "entry": entry,
                "safe_note": atlas.get("safe_note", ""),
            }
    return {
        "name": "Town Capability Detail",
        "mode": "read-only-building-capability-detail",
        "status": "not-found",
        "building_id": normalized_id,
        "entry": None,
        "safe_note": "Capability detail lookup is read-only. It does not scan roots, run commands, invoke agents, edit registries, or contact external services.",
    }


def town_workflow_routes() -> dict:
    routes = load_json_registry(WORKFLOW_ROUTE_REGISTRY_PATH)
    atlas = town_capability_atlas()
    atlas_by_id = {entry.get("id"): entry for entry in atlas.get("entries", [])}
    enriched_routes = []
    connected_buildings = set()
    missing_buildings = []
    for route in routes:
        enriched_steps = []
        for step in route.get("steps", []):
            if not isinstance(step, dict):
                continue
            building_id = str(step.get("building_id", "")).strip()
            capability = atlas_by_id.get(building_id, {})
            if building_id and building_id not in atlas_by_id:
                missing_buildings.append(building_id)
            if building_id:
                connected_buildings.add(building_id)
            enriched_steps.append({
                **step,
                "building_name": capability.get("name", building_id),
                "backend": capability.get("backend", building_id),
                "safety": capability.get("safety", "read-only"),
                "available_capabilities": capability.get("capabilities", [])[:6],
                "endpoint_count": len(capability.get("endpoints", [])),
                "real_path_count": len(capability.get("real_paths", [])),
                "has_real_connection": bool(capability.get("has_real_connection", False)),
            })
        enriched_routes.append({
            **route,
            "steps": enriched_steps,
            "step_count": len(enriched_steps),
            "building_ids": [step.get("building_id", "") for step in enriched_steps if step.get("building_id")],
            "connected_building_count": len({step.get("building_id") for step in enriched_steps if step.get("has_real_connection")}),
        })
    return {
        "name": "Town Workflow Routes",
        "mode": "read-only-workflow-route-registry",
        "status": "ok" if routes and not missing_buildings else ("warning" if routes else "missing"),
        "path": str(WORKFLOW_ROUTE_REGISTRY_PATH),
        "route_count": len(enriched_routes),
        "connected_building_count": len(connected_buildings),
        "missing_buildings": sorted(set(missing_buildings)),
        "routes": enriched_routes,
        "safe_note": "Town Workflow Routes describe reusable multi-building work paths from a static registry and the read-only Capability Atlas. They do not claim progress, write save data, scan roots, run commands, invoke agents, edit registries, or contact external services.",
    }


def town_workflow_route_detail(route_id: str) -> dict:
    normalized_id = str(route_id).strip()
    overview = town_workflow_routes()
    for route in overview.get("routes", []):
        if route.get("id") == normalized_id:
            return {
                "name": "Town Workflow Route Detail",
                "mode": "read-only-workflow-route-detail",
                "status": "ok",
                "route_id": normalized_id,
                "route": route,
                "safe_note": overview.get("safe_note", ""),
            }
    return {
        "name": "Town Workflow Route Detail",
        "mode": "read-only-workflow-route-detail",
        "status": "not-found",
        "route_id": normalized_id,
        "route": None,
        "safe_note": "Workflow route detail lookup is read-only. It does not claim progress, run commands, invoke agents, edit files, or contact external services.",
    }


def default_workspaces() -> list[dict]:
    return [
        {
            "id": "research",
            "name": "Research",
            "path": str(RESEARCH_ROOT),
            "kind": "research",
            "role": "research projects, papers, experiments, and datasets",
            "enabled": True,
            "file_vault": True,
            "project_browser": True,
            "priority": "critical",
            "safety": "allowlisted-lazy-read",
        },
        {
            "id": "company",
            "name": "Company",
            "path": r"D:\Company",
            "kind": "office",
            "role": "company projects and workspace (includes xinlu-valley)",
            "enabled": True,
            "file_vault": True,
            "project_browser": True,
            "priority": "critical",
            "safety": "allowlisted-lazy-read",
        },
        {
            "id": "knowledgebase",
            "name": "Knowledgebase",
            "path": str(KNOWLEDGE_BASE_DIR),
            "kind": "knowledge",
            "role": "shared knowledge base, memory context, and project notes",
            "enabled": True,
            "file_vault": True,
            "project_browser": False,
            "priority": "critical",
            "safety": "allowlisted-lazy-read",
        },
        {
            "id": "agent-resources",
            "name": "Agent Resources",
            "path": r"D:\agent-resources",
            "kind": "agent-resources",
            "role": "skills, workflows, templates, and agent-side resources",
            "enabled": True,
            "file_vault": True,
            "project_browser": False,
            "priority": "high",
            "safety": "allowlisted-lazy-read",
        },
        {
            "id": "devtools",
            "name": "Devtools",
            "path": str(DEVTOOLS_DIR),
            "kind": "tools",
            "role": "local agent launchers, tools, and infrastructure",
            "enabled": True,
            "file_vault": True,
            "project_browser": True,
            "priority": "high",
            "safety": "allowlisted-lazy-read",
        },
        {
            "id": "project",
            "name": "AI Town Project",
            "path": str(PROJECT_ROOT),
            "kind": "project",
            "role": "current AI Town source tree and docs",
            "enabled": True,
            "file_vault": True,
            "project_browser": True,
            "priority": "critical",
            "safety": "project-local-read",
        },
    ]


def normalize_workspace_entry(item: dict) -> Optional[dict]:
    workspace_id = str(item.get("id", "")).strip()
    path_text = str(item.get("path", "")).strip()
    if not workspace_id or not path_text:
        return None
    path = Path(path_text)
    return {
        "id": workspace_id,
        "name": str(item.get("name", workspace_id)).strip() or workspace_id,
        "path": str(path),
        "kind": str(item.get("kind", "workspace")).strip() or "workspace",
        "role": str(item.get("role", "")).strip(),
        "enabled": bool(item.get("enabled", True)),
        "file_vault": bool(item.get("file_vault", True)),
        "project_browser": bool(item.get("project_browser", False)),
        "priority": str(item.get("priority", "normal")).strip() or "normal",
        "safety": str(item.get("safety", "allowlisted-lazy-read")).strip() or "allowlisted-lazy-read",
        "ignore_dirs": [
            str(value).strip()
            for value in item.get("ignore_dirs", [])
            if str(value).strip()
        ],
        "exists": path.exists(),
        "is_dir": path.is_dir(),
    }


def load_workspace_registry() -> list[dict]:
    entries = load_json_registry(WORKSPACE_REGISTRY_PATH)
    if not entries:
        entries = default_workspaces()
    workspaces = []
    seen = set()
    for item in entries:
        normalized = normalize_workspace_entry(item)
        if not normalized:
            continue
        key = normalized["id"]
        if key in seen:
            continue
        seen.add(key)
        workspaces.append(normalized)
    return workspaces


def workspace_registry_overview() -> dict:
    workspaces = load_workspace_registry()
    enabled = [item for item in workspaces if item.get("enabled")]
    file_vault = [item for item in enabled if item.get("file_vault")]
    project_browser = [item for item in enabled if item.get("project_browser")]
    kind_counts: dict[str, int] = {}
    for item in workspaces:
        kind = item.get("kind", "workspace")
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
    return {
        "status": "ok" if workspaces else "missing",
        "path": str(WORKSPACE_REGISTRY_PATH),
        "exists": WORKSPACE_REGISTRY_PATH.exists(),
        "count": len(workspaces),
        "enabled_count": len(enabled),
        "file_vault_count": len(file_vault),
        "project_browser_count": len(project_browser),
        "kind_counts": kind_counts,
        "workspaces": workspaces,
        "safe_note": "Workspace registry is read-only configuration. It declares allowlisted roots for File Vault, project discovery, and future room/plugin expansion without scanning the whole disk at startup.",
    }


def default_quest_steps(accept_label: str, enter_label: str, review_label: str) -> list[dict]:
    return [
        {"id": "accept", "label": accept_label},
        {"id": "enter_room", "label": enter_label},
        {"id": "review_shelves", "label": review_label},
        {"id": "scan", "label": "Run the safe read-only scan"},
    ]


def default_quests() -> list[dict]:
    return [
        {
            "id": "orient-memory-library",
            "title": "Memory Library Orientation",
            "chapter": "Chapter 1: Wake the Town",
            "giver": "Sonnet",
            "target_building": "memory-library",
            "summary_template": "Inspect shared memory: {memory_decisions} decisions, {memory_facts} facts, {memory_lessons} lessons.",
            "reward": "Memory Lens",
            "badge_id": "memory-lens",
            "collection": "Town Tools",
            "next_hint": "Use the lens to decide which shared memory should become an in-game reference shelf next.",
            "steps": default_quest_steps("Accept Sonnet's orientation request", "Enter the Memory Library reading room", "Review the memory shelves"),
            "safety": "read-only",
        },
        {
            "id": "map-local-files",
            "title": "Map the File Vault",
            "chapter": "Chapter 1: Wake the Town",
            "giver": "Codex",
            "target_building": "file-vault",
            "summary_template": "Survey {workspace_file_vault_count} allowlisted work roots without opening or modifying files.",
            "reward": "Vault Key",
            "badge_id": "vault-key",
            "collection": "Town Tools",
            "next_hint": "Turn one file root into a navigable project cabinet.",
            "steps": default_quest_steps("Accept Codex's file mapping request", "Enter the File Vault", "Review the root cabinets"),
            "safety": "read-only",
        },
        {
            "id": "survey-skills",
            "title": "Survey the Skill Workshop",
            "chapter": "Chapter 1: Wake the Town",
            "giver": "PixelCat",
            "target_building": "skill-workshop",
            "summary_template": "Review the local skill library: {skill_count} skills across {skill_categories} categories.",
            "reward": "Skill Charm",
            "badge_id": "skill-charm",
            "collection": "Town Tools",
            "next_hint": "Equip skills as agent abilities in future quest chains.",
            "steps": default_quest_steps("Accept PixelCat's workshop survey", "Enter the Skill Workshop", "Review the skill racks"),
            "safety": "read-only",
        },
        {
            "id": "research-brief",
            "title": "Research Hall Briefing",
            "chapter": "Chapter 1: Wake the Town",
            "giver": "ARIS",
            "target_building": "research-hall",
            "summary_template": "Review active research project status files from shared memory and {workspace_project_count} project-browser roots.",
            "reward": "Research Compass",
            "badge_id": "research-compass",
            "collection": "Research Kit",
            "next_hint": "Convert one active research project into a multi-step ARIS quest.",
            "steps": default_quest_steps("Accept ARIS's research briefing", "Enter the Research Hall", "Review active project boards"),
            "safety": "read-only",
        },
        {
            "id": "agent-hub-check",
            "title": "Agent Hub Check",
            "chapter": "Chapter 1: Wake the Town",
            "giver": "Codex",
            "target_building": "agent-hub",
            "summary_template": "Check local agent mailbox files and dispatch draft readiness.",
            "reward": "Coordination Badge",
            "badge_id": "coordination-badge",
            "collection": "Agent Ops",
            "next_hint": "Use mailbox status to unlock multi-agent dispatch rooms.",
            "steps": default_quest_steps("Accept Codex's hub check", "Enter the Agent Hub", "Review mailbox signal lamps"),
            "safety": "read-only",
        },
    ]


def quest_template_values() -> dict:
    memory = read_memory_summary()
    skills = read_skills_summary()
    workspaces = workspace_registry_overview()
    return {
        "memory_decisions": memory.get("decisions", 0),
        "memory_facts": memory.get("facts", 0),
        "memory_lessons": memory.get("lessons", 0),
        "skill_count": skills.get("count", 0),
        "skill_categories": skills.get("categories", 0),
        "workspace_count": workspaces.get("count", 0),
        "workspace_file_vault_count": workspaces.get("file_vault_count", 0),
        "workspace_project_count": workspaces.get("project_browser_count", 0),
    }


def normalize_quest_entry(item: dict, values: dict) -> Optional[dict]:
    quest_id = str(item.get("id", "")).strip()
    title = str(item.get("title", "")).strip()
    target = str(item.get("target_building", "")).strip()
    if not quest_id or not title or not target:
        return None
    summary = str(item.get("summary", "")).strip()
    summary_template = str(item.get("summary_template", "")).strip()
    if summary_template:
        try:
            summary = summary_template.format(**values)
        except Exception:
            summary = summary_template
    steps = item.get("steps", [])
    if not isinstance(steps, list) or not steps:
        steps = default_quest_steps("Accept the quest", f"Enter {target}", "Review the room shelves")
    clean_steps = []
    for step in steps:
        if isinstance(step, dict) and step.get("id"):
            clean_steps.append({
                "id": str(step.get("id", "")).strip(),
                "label": str(step.get("label", step.get("id", ""))).strip(),
            })
    return {
        "id": quest_id,
        "title": title,
        "chapter": str(item.get("chapter", "Town Chapter")).strip() or "Town Chapter",
        "giver": str(item.get("giver", "Agent")).strip() or "Agent",
        "target_building": target,
        "summary": summary,
        "reward": str(item.get("reward", "Badge")).strip() or "Badge",
        "badge_id": str(item.get("badge_id", quest_id)).strip() or quest_id,
        "collection": str(item.get("collection", "Town Tools")).strip() or "Town Tools",
        "next_hint": str(item.get("next_hint", "Keep exploring.")).strip() or "Keep exploring.",
        "steps": clean_steps,
        "safety": str(item.get("safety", "read-only")).strip() or "read-only",
    }


def load_quest_registry() -> list[dict]:
    quests = load_json_registry(QUEST_REGISTRY_PATH)
    if not quests:
        quests = default_quests()
    values = quest_template_values()
    normalized = []
    seen = set()
    for item in quests:
        quest = normalize_quest_entry(item, values)
        if not quest:
            continue
        if quest["id"] in seen:
            continue
        seen.add(quest["id"])
        normalized.append(quest)
    return normalized


def quest_registry_overview() -> dict:
    quests = load_quest_registry()
    target_counts: dict[str, int] = {}
    chapter_counts: dict[str, int] = {}
    for quest in quests:
        target = quest.get("target_building", "")
        chapter = quest.get("chapter", "")
        target_counts[target] = target_counts.get(target, 0) + 1
        chapter_counts[chapter] = chapter_counts.get(chapter, 0) + 1
    return {
        "status": "ok" if quests else "missing",
        "path": str(QUEST_REGISTRY_PATH),
        "exists": QUEST_REGISTRY_PATH.exists(),
        "mode": "safe-read-only",
        "count": len(quests),
        "target_counts": target_counts,
        "chapter_counts": chapter_counts,
        "quests": quests,
        "safe_note": "Quest registry defines game progression data and resolves lightweight local status templates. Quest completion remains saved locally in Godot user data.",
    }


def npc_quest_registry_overview() -> dict:
    chains = load_json_registry(NPC_QUEST_REGISTRY_PATH)
    building_counts: dict[str, int] = {}
    npc_counts: dict[str, int] = {}
    for chain in chains:
        building_id = str(chain.get("building_id", ""))
        npc = str(chain.get("npc", ""))
        building_counts[building_id] = building_counts.get(building_id, 0) + 1
        npc_counts[npc] = npc_counts.get(npc, 0) + 1
    return {
        "status": "ok" if chains else "missing",
        "path": str(NPC_QUEST_REGISTRY_PATH),
        "exists": NPC_QUEST_REGISTRY_PATH.exists(),
        "mode": "safe-read-only-npc-chain-config",
        "count": len(chains),
        "building_counts": building_counts,
        "npc_counts": npc_counts,
        "chains": chains,
        "safe_note": "NPC quest chains are read-only gameplay configuration. Progress remains local Godot save data; this endpoint does not mutate files, agents, or external services.",
    }


def room_scene_registry_overview() -> dict:
    scenes = load_json_registry(ROOM_SCENE_REGISTRY_PATH)
    station_count = 0
    for scene in scenes:
        if isinstance(scene, dict):
            stations = scene.get("stations", [])
            if isinstance(stations, list):
                station_count += len(stations)
    return {
        "status": "ok" if scenes else "missing",
        "path": str(ROOM_SCENE_REGISTRY_PATH),
        "exists": ROOM_SCENE_REGISTRY_PATH.exists(),
        "mode": "safe-read-only-room-scene-config",
        "count": len(scenes),
        "station_count": station_count,
        "scenes": scenes,
        "safe_note": "Room scene registry is read-only interior layout and station-binding metadata. Stations call existing safe room actions and do not grant extra filesystem, shell, Git, or agent permissions.",
    }


def map_decor_registry_overview() -> dict:
    landmarks = load_json_registry(MAP_DECOR_REGISTRY_PATH)
    action_counts: dict[str, int] = {}
    for item in landmarks:
        action = str(item.get("action", ""))
        if action:
            action_key = action.split(":", 1)[0]
            action_counts[action_key] = action_counts.get(action_key, 0) + 1
    return {
        "status": "ok" if landmarks else "missing",
        "path": str(MAP_DECOR_REGISTRY_PATH),
        "exists": MAP_DECOR_REGISTRY_PATH.exists(),
        "mode": "safe-read-only-map-decor-config",
        "count": len(landmarks),
        "action_counts": action_counts,
        "landmarks": landmarks,
        "safe_note": "Map decor registry defines clickable plaza landmarks and in-game routing actions. It does not scan files, run commands, launch agents, or mutate external services.",
    }


def collection_codex_overview() -> dict:
    quests = load_quest_registry()
    npc_chains = load_json_registry(NPC_QUEST_REGISTRY_PATH)
    buildings = load_json_registry(BUILDING_REGISTRY_PATH)
    companions = agent_companion_cards()
    daily_routes = daily_routes_overview().get("routes", [])
    workflow_routes = town_workflow_routes().get("routes", [])

    collections = [
        {
            "id": "quest-badges",
            "name": "Quest Badges",
            "source": "quest-registry",
            "items": [
                {
                    "id": quest.get("badge_id", quest.get("id", "")),
                    "name": quest.get("reward", quest.get("title", "Quest Badge")),
                    "collection": quest.get("collection", "Town Tools"),
                    "source_id": quest.get("id", ""),
                    "source_title": quest.get("title", ""),
                    "unlock_hint": quest.get("next_hint", "Complete the quest chain."),
                    "safety": quest.get("safety", "read-only"),
                    "owned_kind": "badge",
                }
                for quest in quests
            ],
        },
        {
            "id": "npc-chain-badges",
            "name": "NPC Chain Badges",
            "source": "npc-quest-registry",
            "items": [
                {
                    "id": f"npc-chain-{chain.get('id', '')}",
                    "name": f"{chain.get('title', chain.get('id', 'NPC Chain'))} Chain",
                    "collection": "NPC Chains",
                    "source_id": chain.get("id", ""),
                    "source_title": chain.get("title", ""),
                    "unlock_hint": f"Finish {len(chain.get('stages', []))} safe stage(s) in {chain.get('building_id', '')}.",
                    "safety": chain.get("safety", "local-progress-only"),
                    "owned_kind": "badge",
                }
                for chain in npc_chains
                if isinstance(chain, dict) and chain.get("id")
            ],
        },
        {
            "id": "room-mastery",
            "name": "Room Mastery",
            "source": "building-registry",
            "items": [
                {
                    "id": f"mastery-{building.get('id', '')}-l{level}",
                    "name": f"{building.get('name', building.get('id', 'Room'))} Mastery Lv.{level}",
                    "collection": "Room Mastery",
                    "source_id": building.get("id", ""),
                    "source_title": building.get("name", ""),
                    "unlock_hint": "Enter the room and complete safe workbench actions to gain XP.",
                    "safety": "local-player-progress-only",
                    "owned_kind": "badge",
                }
                for building in buildings
                if isinstance(building, dict) and building.get("id")
                for level in [1, 2, 3]
            ],
        },
        {
            "id": "daily-routes",
            "name": "Daily Routes",
            "source": "daily-route-generator",
            "items": [
                {
                    "id": f"daily-route-{route.get('id', '')}",
                    "name": route.get("title", "Daily Route"),
                    "collection": "Daily Routes",
                    "source_id": route.get("id", ""),
                    "source_title": route.get("title", ""),
                    "unlock_hint": "Claim the route and visit each listed building today.",
                    "safety": route.get("safety", "local-save-only"),
                    "owned_kind": "daily-route",
                }
                for route in daily_routes
                if isinstance(route, dict) and route.get("id")
            ],
        },
        {
            "id": "workflow-routes",
            "name": "Workflow Routes",
            "source": "workflow-route-registry",
            "items": [
                {
                    "id": f"workflow-route-{route.get('id', '')}",
                    "name": route.get("title", "Workflow Route"),
                    "collection": "Workflow Routes",
                    "source_id": route.get("id", ""),
                    "source_title": route.get("title", ""),
                    "unlock_hint": "Claim the workflow in Town Hall and visit each listed building.",
                    "safety": route.get("safety", "local-save-only"),
                    "owned_kind": "workflow-route",
                }
                for route in workflow_routes
                if isinstance(route, dict) and route.get("id")
            ],
        },
        {
            "id": "agent-companions",
            "name": "Agent Companions",
            "source": "agent-registry",
            "items": [
                {
                    "id": f"companion-{companion.get('id', '')}",
                    "name": companion.get("display_name", companion.get("name", "Agent Companion")),
                    "collection": "Agent Companions",
                    "source_id": companion.get("id", ""),
                    "source_title": companion.get("role", companion.get("agent_kind", "")),
                    "unlock_hint": "Open Agent Hub and recruit this companion into the local player profile.",
                    "safety": companion.get("safety", "local-player-companion-only"),
                    "owned_kind": "companion",
                }
                for companion in companions
                if isinstance(companion, dict) and companion.get("id")
            ],
        },
    ]
    total = 0
    for collection in collections:
        items = collection.get("items", [])
        collection["count"] = len(items)
        total += len(items)
    return {
        "status": "ok",
        "mode": "read-only-collection-codex",
        "collection_count": len(collections),
        "item_count": total,
        "collections": collections,
        "safe_note": "Collection Codex returns possible progression rewards from read-only registries. Ownership, active companions, route claims, and progress remain in the Godot local player save; this endpoint does not mutate files, run commands, launch agents, or contact external services.",
    }


def file_vault_workspace_roots() -> list[dict]:
    roots = []
    for item in load_workspace_registry():
        if not item.get("enabled") or not item.get("file_vault"):
            continue
        roots.append({
            "id": item["id"],
            "name": item["name"],
            "path": Path(item["path"]),
            "kind": item.get("kind", "workspace"),
            "role": item.get("role", ""),
            "safety": item.get("safety", "allowlisted-lazy-read"),
        })
    return roots if roots else FILE_VAULT_ROOTS


def project_scan_roots() -> list[tuple[str, Path]]:
    roots = [("AI Town", PROJECT_ROOT)]
    seen = {str(PROJECT_ROOT.resolve()).lower()}
    for item in load_workspace_registry():
        if item.get("enabled") and item.get("project_browser"):
            path = Path(item["path"])
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            roots.append((item.get("name", item["id"]), path))
    return roots if roots else PROJECT_SCAN_ROOTS


def default_model_profiles() -> list[dict]:
    return [
        {
            "id": "deepseek-chat",
            "name": "DeepSeek Chat",
            "provider": "deepseek",
            "role": "current dialogue provider",
            "key_env": "DEEPSEEK_API_KEY",
            "base_url_env": "DEEPSEEK_BASE_URL",
            "default_base_url": "https://api.deepseek.com",
            "models": ["deepseek-chat"],
            "safety": "no-secret-display",
        },
        {
            "id": "openai-compatible",
            "name": "OpenAI Compatible Gateway",
            "provider": "openai-compatible",
            "role": "future model/tool gateway",
            "key_env": "OPENAI_API_KEY",
            "base_url_env": "OPENAI_BASE_URL",
            "default_base_url": "https://api.openai.com",
            "models": ["gpt-5.5", "gpt-5.1", "gpt-4.1"],
            "safety": "no-secret-display",
        },
        {
            "id": "anthropic-compatible",
            "name": "Anthropic Compatible Gateway",
            "provider": "anthropic",
            "role": "future reviewer/agent gateway",
            "key_env": "ANTHROPIC_API_KEY",
            "base_url_env": "ANTHROPIC_BASE_URL",
            "default_base_url": "https://api.anthropic.com",
            "models": ["claude-sonnet", "claude-opus"],
            "safety": "no-secret-display",
        },
        {
            "id": "gemini-compatible",
            "name": "Gemini Compatible Gateway",
            "provider": "google",
            "role": "future multimodal/research gateway",
            "key_env": "GEMINI_API_KEY",
            "base_url_env": "GEMINI_BASE_URL",
            "default_base_url": "https://generativelanguage.googleapis.com",
            "models": ["gemini-pro", "gemini-flash"],
            "safety": "no-secret-display",
        },
        {
            "id": "local-openai-proxy",
            "name": "Local OpenAI-style Proxy",
            "provider": "local-proxy",
            "role": "multi-hop local API gateway",
            "key_env": "LOCAL_OPENAI_API_KEY",
            "base_url_env": "LOCAL_OPENAI_BASE_URL",
            "default_base_url": "http://127.0.0.1:8001/v1",
            "models": ["configured-by-proxy"],
            "safety": "no-secret-display",
        },
    ]


def load_model_profiles() -> list[dict]:
    profiles = load_json_registry(MODEL_PROFILE_REGISTRY_PATH)
    return profiles if profiles else default_model_profiles()


def env_is_configured(name: str) -> bool:
    value = os.getenv(name, "")
    return bool(value and value.strip())


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def dpapi_available() -> bool:
    return os.name == "nt"


def dpapi_protect(secret: str) -> str:
    if not dpapi_available():
        raise RuntimeError("Windows DPAPI is required for local API key vault encryption.")
    data = secret.encode("utf-8")
    in_blob = DATA_BLOB(len(data), ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_ubyte)))
    out_blob = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)):
        raise RuntimeError("DPAPI encryption failed.")
    try:
        encrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        return base64.b64encode(encrypted).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def dpapi_unprotect(encrypted_b64: str) -> str:
    if not dpapi_available():
        raise RuntimeError("Windows DPAPI is required for local API key vault decryption.")
    encrypted = base64.b64decode(encrypted_b64.encode("ascii"))
    in_blob = DATA_BLOB(len(encrypted), ctypes.cast(ctypes.create_string_buffer(encrypted), ctypes.POINTER(ctypes.c_ubyte)))
    out_blob = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)):
        raise RuntimeError("DPAPI decryption failed.")
    try:
        data = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        return data.decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def load_model_key_vault() -> dict:
    if not MODEL_KEY_VAULT_PATH.exists():
        return {"version": 1, "keys": {}}
    try:
        data = json.loads(MODEL_KEY_VAULT_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("keys"), dict):
            return data
    except Exception:
        pass
    return {"version": 1, "keys": {}}


def save_model_key_vault(data: dict) -> None:
    MODEL_KEY_VAULT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_KEY_VAULT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def model_key_fingerprint(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8", errors="ignore")).hexdigest()[:16]


def model_key_vault_entries() -> list[dict]:
    vault = load_model_key_vault()
    entries = []
    for profile_id, item in vault.get("keys", {}).items():
        if not isinstance(item, dict):
            continue
        entries.append({
            "profile_id": profile_id,
            "label": item.get("label", ""),
            "key_env": item.get("key_env", ""),
            "fingerprint": item.get("fingerprint", ""),
            "length": item.get("length", 0),
            "updated_at": item.get("updated_at", 0),
            "source": item.get("source", ""),
            "status": "stored",
            "encryption": item.get("encryption", "dpapi-current-user"),
        })
    return sorted(entries, key=lambda item: item.get("updated_at", 0), reverse=True)


def model_key_vault_status() -> dict:
    return {
        "name": "Model Key Vault",
        "mode": "encrypted-local-key-vault",
        "vault_path": str(MODEL_KEY_VAULT_PATH),
        "vault_exists": MODEL_KEY_VAULT_PATH.exists(),
        "encryption": "windows-dpapi-current-user" if dpapi_available() else "unavailable",
        "confirmation_required": CONFIRM_SAVE_API_KEY,
        "entries": model_key_vault_entries(),
        "count": len(model_key_vault_entries()),
        "secret_policy": "Raw API keys are accepted only on save requests, encrypted with the current Windows user, and never returned by any endpoint.",
        "safe_note": "The vault augments environment variables for model calls. It does not edit .env files, shell profiles, registry files, launchers, or Git-tracked configuration.",
    }


def profile_by_id(profile_id: str) -> dict:
    for profile in load_model_profiles():
        if profile.get("id") == profile_id:
            return profile
    return {}


def get_model_key_from_vault(profile_id: str) -> str:
    vault = load_model_key_vault()
    item = vault.get("keys", {}).get(profile_id, {})
    encrypted = item.get("encrypted_key", "") if isinstance(item, dict) else ""
    if not encrypted:
        return ""
    return dpapi_unprotect(encrypted)


def save_model_key_to_vault(req: ModelKeyVaultSaveRequest) -> dict:
    profile = profile_by_id(req.profile_id)
    if not profile:
        return {"status": "missing-profile", "profile_id": req.profile_id, "safety": "no-secret-display"}
    key_value = req.key_value.strip()
    base_response = {
        "profile_id": req.profile_id,
        "profile_name": profile.get("name", ""),
        "key_env": profile.get("key_env", ""),
        "label": req.label.strip() or profile.get("name", req.profile_id),
        "safety": "confirm-required-encrypted-local-secret",
        "confirmation_required": CONFIRM_SAVE_API_KEY,
        "vault_path": str(MODEL_KEY_VAULT_PATH),
        "encryption": "windows-dpapi-current-user" if dpapi_available() else "unavailable",
    }
    if not key_value:
        return {"status": "input-required", **base_response}
    base_response["fingerprint"] = model_key_fingerprint(key_value)
    base_response["length"] = len(key_value)
    if req.dry_run:
        return {"status": "dry-run", **base_response}
    if req.confirmation != CONFIRM_SAVE_API_KEY:
        return {"status": "confirmation-required", **base_response}
    if not dpapi_available():
        return {"status": "unsupported-platform", **base_response}

    vault = load_model_key_vault()
    vault.setdefault("version", 1)
    vault.setdefault("keys", {})
    now = time.time()
    vault["keys"][req.profile_id] = {
        "label": base_response["label"],
        "key_env": profile.get("key_env", ""),
        "fingerprint": base_response["fingerprint"],
        "length": len(key_value),
        "updated_at": now,
        "source": f"ai-town/{req.source_building.strip() or 'model-market'}",
        "encryption": "dpapi-current-user",
        "encrypted_key": dpapi_protect(key_value),
    }
    save_model_key_vault(vault)
    memory = record_memory_event(
        f"Model API key saved: {req.profile_id}",
        f"Saved encrypted local key for `{req.profile_id}` in `{MODEL_KEY_VAULT_PATH}`. Fingerprint `{base_response['fingerprint']}`; raw key not recorded.",
        f"ai-town/{req.source_building.strip() or 'model-market'}",
    )
    return {"status": "saved", "memory_event": memory, **base_response}


def model_profile_status(profile: dict) -> dict:
    key_env = profile.get("key_env", "")
    base_url_env = profile.get("base_url_env", "")
    key_configured = env_is_configured(key_env) if key_env else False
    vault_entry = load_model_key_vault().get("keys", {}).get(str(profile.get("id", "")), {})
    vault_configured = isinstance(vault_entry, dict) and bool(vault_entry.get("encrypted_key"))
    base_url = os.getenv(base_url_env, profile.get("default_base_url", "")) if base_url_env else profile.get("default_base_url", "")
    return {
        "id": profile.get("id", ""),
        "name": profile.get("name", profile.get("id", "model")),
        "provider": profile.get("provider", ""),
        "role": profile.get("role", ""),
        "key_env": key_env,
        "key_configured": key_configured,
        "vault_configured": vault_configured,
        "credential_source": "environment" if key_configured else "local-key-vault" if vault_configured else "missing",
        "key_fingerprint": vault_entry.get("fingerprint", "") if isinstance(vault_entry, dict) else "",
        "base_url_env": base_url_env,
        "base_url": base_url,
        "models": profile.get("models", []),
        "safety": profile.get("safety", "no-secret-display"),
        "status": "configured" if key_configured or vault_configured else "missing-key",
    }


def model_gateway_status() -> dict:
    profiles = [model_profile_status(profile) for profile in load_model_profiles()]
    configured = [profile for profile in profiles if profile.get("key_configured")]
    active = select_model_profile_status("deepseek-chat", profiles)
    return {
        "name": "Model Market",
        "mode": "read-only-no-secret-display",
        "profile_path": str(MODEL_PROFILE_REGISTRY_PATH),
        "profiles": profiles,
        "count": len(profiles),
        "configured_count": len(configured),
        "active_dialogue_provider": active.get("id", "deepseek-chat"),
        "active_dialogue_status": active.get("status", "missing-key"),
        "warnings": [] if configured else ["No model API keys detected in this backend process environment."],
        "secret_policy": "Only env var names and configured/missing flags are exposed. Raw API keys are never returned.",
        "config_draft_dir": str(MODEL_CONFIG_DRAFTS_DIR),
        "config_drafts": markdown_draft_entries(MODEL_CONFIG_DRAFTS_DIR, "model-config-draft", 10),
        "profile_test_dir": str(MODEL_TEST_RESULTS_DIR),
        "profile_tests": markdown_draft_entries(MODEL_TEST_RESULTS_DIR, "model-profile-test", 10),
        "key_vault": model_key_vault_status(),
    }


def select_model_profile_status(preferred_id: str = "", profiles: Optional[list[dict]] = None) -> dict:
    statuses = profiles if profiles is not None else [model_profile_status(profile) for profile in load_model_profiles()]
    preferred = {}
    if preferred_id:
        for profile in statuses:
            if profile.get("id") == preferred_id:
                preferred = profile
                if profile.get("key_configured") and profile.get("provider") in {"deepseek", "openai-compatible", "local-proxy"}:
                    return profile
                break
    for profile in statuses:
        if profile.get("key_configured") and profile.get("provider") in {"deepseek", "openai-compatible", "local-proxy"}:
            return profile
    if preferred:
        return preferred
    for profile in statuses:
        if profile.get("provider") in {"deepseek", "openai-compatible", "local-proxy"}:
            return profile
    return statuses[0] if statuses else {}


def chat_completion_endpoint(base_url: str) -> str:
    base = (base_url or "https://api.deepseek.com").rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


async def call_model_gateway_chat(req: ModelChatRequest) -> dict:
    profile = select_model_profile_status(req.profile_id)
    if not profile:
        return {
            "status": "missing-profile",
            "response": "",
            "profile_id": req.profile_id,
            "safety": "no-secret-display",
        }
    provider = str(profile.get("provider", ""))
    supported = provider in {"deepseek", "openai-compatible", "local-proxy"}
    models = profile.get("models", [])
    model = req.model.strip() or (str(models[0]) if models else "deepseek-chat")
    endpoint = chat_completion_endpoint(str(profile.get("base_url", "")))
    if req.dry_run:
        return {
            "status": "dry-run",
            "response": "",
            "profile_id": profile.get("id", ""),
            "profile_name": profile.get("name", ""),
            "provider": provider,
            "model": model,
            "endpoint": endpoint,
            "configured": bool(profile.get("key_configured")),
            "safety": "no-network-dry-run-no-secret-display",
        }
    if not supported:
        return {
            "status": "unsupported-provider",
            "response": "",
            "profile_id": profile.get("id", ""),
            "profile_name": profile.get("name", ""),
            "provider": provider,
            "model": model,
            "endpoint": endpoint,
            "configured": bool(profile.get("key_configured")),
            "safety": "no-secret-display",
            "error": "This provider is listed for readiness, but chat routing currently supports OpenAI-compatible /v1/chat/completions profiles only.",
        }
    key_env = str(profile.get("key_env", ""))
    api_key = os.getenv(key_env, "")
    credential_source = "environment"
    if not api_key:
        try:
            api_key = get_model_key_from_vault(str(profile.get("id", "")))
            credential_source = "local-key-vault" if api_key else "missing"
        except Exception as exc:
            return {
                "status": "key-vault-error",
                "response": "",
                "profile_id": profile.get("id", ""),
                "profile_name": profile.get("name", ""),
                "provider": provider,
                "model": model,
                "endpoint": endpoint,
                "configured": bool(profile.get("key_configured")),
                "key_env": key_env,
                "credential_source": "local-key-vault",
                "safety": "no-secret-display",
                "error": str(exc)[:500],
            }
    if not api_key:
        return {
            "status": "missing-key",
            "response": "",
            "profile_id": profile.get("id", ""),
            "profile_name": profile.get("name", ""),
            "provider": provider,
            "model": model,
            "endpoint": endpoint,
            "configured": False,
            "key_env": key_env,
            "credential_source": credential_source,
            "safety": "no-secret-display",
        }
    max_tokens = max(1, min(int(req.max_tokens), 1000))
    temperature = max(0.0, min(float(req.temperature), 1.5))
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": req.system_prompt},
                        {"role": "user", "content": req.user_prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            reply = data["choices"][0]["message"]["content"].strip()
            return {
                "status": "ok",
                "response": reply,
                "profile_id": profile.get("id", ""),
                "profile_name": profile.get("name", ""),
                "provider": provider,
                "model": model,
                "endpoint": endpoint,
                "configured": True,
                "credential_source": credential_source,
                "safety": "model-call-no-secret-display",
            }
    except Exception as exc:
        return {
            "status": "failed",
            "response": "",
            "profile_id": profile.get("id", ""),
            "profile_name": profile.get("name", ""),
            "provider": provider,
            "model": model,
            "endpoint": endpoint,
            "configured": True,
            "credential_source": credential_source,
            "safety": "model-call-no-secret-display",
            "error": str(exc)[:500],
        }


def create_model_config_draft(req: ModelConfigDraftRequest) -> dict:
    status = model_gateway_status()
    profiles = status.get("profiles", [])
    selected = [profile for profile in profiles if req.include_all_profiles or profile.get("id") == req.profile_id]
    if not selected and profiles:
        selected = [profiles[0]]
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    title = req.title.strip() or "AI Town model gateway setup"
    MODEL_CONFIG_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    draft_path = MODEL_CONFIG_DRAFTS_DIR / f"{timestamp}-{slugify_filename(title)}.md"
    env_lines = []
    checklist = []
    for profile in selected:
        key_env = profile.get("key_env", "")
        base_url_env = profile.get("base_url_env", "")
        if key_env:
            env_lines.append(f"{key_env}=replace-with-your-private-key")
            checklist.append(f"Set `{key_env}` in your private environment; never paste it into chat, docs, Git, or screenshots.")
        if base_url_env:
            env_lines.append(f"{base_url_env}={profile.get('base_url', profile.get('default_base_url', ''))}")
    content = "\n".join([
        "---",
        f"title: {title}",
        f"source: ai-town/{req.source_building}",
        "status: draft",
        "safety: no-secret-template-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Selected Profiles",
        "",
        *[f"- `{profile.get('id', '')}`: {profile.get('name', '')} ({profile.get('provider', '')}) status={profile.get('status', '')}" for profile in selected],
        "",
        "## Private Environment Template",
        "",
        "Copy this into a private local environment file or OS environment. Values are placeholders only.",
        "",
        "```env",
        *env_lines,
        "```",
        "",
        "## Review Checklist",
        "",
        *[f"- {item}" for item in checklist],
        "- Keep `.env` ignored and commit only `.env.example` templates.",
        "- Restart the backend after changing process environment variables.",
        "- Reopen Model Market and confirm only configured/missing flags are shown.",
        "- Run `powershell -ExecutionPolicy Bypass -File tools\\verify-smoke.ps1` after applying config.",
        "",
        "## Secret Policy",
        "",
        "- This draft contains no real API keys.",
        "- AI Town never returns raw API key values through Model Market endpoints.",
        "- This endpoint did not edit `.env`, registry files, shell profiles, or process environment variables.",
    ])
    draft_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Model config draft created: {title}",
        f"Created no-secret model/API gateway config draft at `{draft_path}` for {len(selected)} profile(s).",
        "ai-town/model-market",
    )
    return {
        "status": "saved",
        "safety": "no-secret-template-only",
        "draft_path": str(draft_path),
        "memory_event": memory,
        "profiles": selected,
        "preview": content,
    }


async def create_model_profile_test(req: ModelProfileTestRequest) -> dict:
    live_probe = bool(req.live_probe)
    chat_req = ModelChatRequest(
        profile_id=req.profile_id,
        model=req.model,
        system_prompt="You are AI Town's model gateway self-test. Reply in one short sentence.",
        user_prompt="Return a compact readiness acknowledgement for the Model Market.",
        max_tokens=48,
        temperature=0.2,
        dry_run=not live_probe,
    )
    result = await call_model_gateway_chat(chat_req)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    title = f"Model profile test: {result.get('profile_id', req.profile_id)}"
    MODEL_TEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = MODEL_TEST_RESULTS_DIR / f"{timestamp}-{slugify_filename(title)}.md"
    response_preview = str(result.get("response", ""))[:500]
    error_preview = str(result.get("error", ""))[:500]
    content = "\n".join([
        "---",
        f"title: {title}",
        f"source: ai-town/{req.source_building}",
        "status: recorded",
        "safety: no-secret-model-profile-test",
        "---",
        "",
        f"# {title}",
        "",
        "## Route",
        "",
        f"- status: `{result.get('status', '')}`",
        f"- profile: `{result.get('profile_id', '')}` / {result.get('profile_name', '')}",
        f"- provider: `{result.get('provider', '')}`",
        f"- model: `{result.get('model', '')}`",
        f"- endpoint: `{result.get('endpoint', '')}`",
        f"- configured: `{result.get('configured', False)}`",
        f"- live_probe: `{live_probe}`",
        f"- safety: `{result.get('safety', '')}`",
        "",
        "## Response Preview",
        "",
        response_preview or "(no response body recorded)",
        "",
        "## Error Preview",
        "",
        error_preview or "(no error recorded)",
        "",
        "## Secret Policy",
        "",
        "- This report records route metadata and bounded response/error previews only.",
        "- Raw API keys are never written to this report or returned by the endpoint.",
        "- Dry-run tests do not contact external model providers.",
    ])
    report_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Model profile test recorded: {result.get('profile_id', req.profile_id)}",
        f"Recorded Model Market profile test with status `{result.get('status', '')}` at `{report_path}`. Live probe: `{live_probe}`.",
        "ai-town/model-market",
    )
    sanitized = dict(result)
    sanitized.pop("api_key", None)
    return {
        "status": "recorded",
        "test_status": result.get("status", ""),
        "live_probe": live_probe,
        "report_path": str(report_path),
        "memory_event": memory,
        "result": sanitized,
        "preview": content,
        "safety": "no-secret-model-profile-test",
    }


def prune_jobs() -> None:
    if len(JOBS) <= MAX_JOBS:
        return
    ordered = sorted(JOBS.items(), key=lambda item: item[1].get("created_at", 0))
    for job_id, _job in ordered[:len(JOBS) - MAX_JOBS]:
        JOBS.pop(job_id, None)


def job_log_path(job: dict) -> Path:
    job_id = str(job.get("id", "job")).strip() or "job"
    path = job.get("log_path", "")
    if path:
        return Path(str(path))
    created = time.strftime("%Y%m%d-%H%M%S", time.localtime(float(job.get("created_at", time.time()))))
    safe_kind = slugify_filename(str(job.get("kind", "job")) or "job")
    return BACKEND_JOB_LOG_DIR / f"{created}-{safe_kind}-{job_id}.json"


def persist_job_log(job: dict, note: str = "") -> str:
    BACKEND_JOB_LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = job_log_path(job)
    job["log_path"] = str(path)
    snapshot = {
        "id": job.get("id", ""),
        "kind": job.get("kind", ""),
        "label": job.get("label", ""),
        "status": job.get("status", ""),
        "safety": job.get("safety", ""),
        "created_at": job.get("created_at", 0),
        "updated_at": job.get("updated_at", 0),
        "result": job.get("result"),
        "error": job.get("error", ""),
        "events": job.get("events", []),
        "cancel_requested": job.get("cancel_requested", False),
        "cancel_reason": job.get("cancel_reason", ""),
        "cancelable": job.get("cancelable", False),
        "rollback_note": job.get("rollback_note", ""),
        "log_note": note,
        "safe_note": "Persistent backend job log is project-local evidence. It records bounded job lifecycle metadata/result references and does not replay jobs, kill processes, or perform rollback.",
    }
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return str(path)


def latest_backend_job_logs(limit: int = 12) -> list[dict]:
    if not BACKEND_JOB_LOG_DIR.exists():
        return []
    logs = []
    try:
        paths = sorted(
            [path for path in BACKEND_JOB_LOG_DIR.glob("*.json") if path.is_file()],
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
    except Exception:
        return []
    for path in paths[:limit]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        logs.append({
            "id": data.get("id", path.stem),
            "kind": data.get("kind", ""),
            "label": data.get("label", path.stem),
            "status": data.get("status", "unknown"),
            "updated_at": data.get("updated_at", path.stat().st_mtime),
            "event_count": len(data.get("events", [])) if isinstance(data.get("events", []), list) else 0,
            "log_path": str(path),
            "bytes": path.stat().st_size,
        })
    return logs


def read_backend_job_log(log_id: str) -> dict:
    safe_id = slugify_filename(log_id.strip())
    if not safe_id:
        return {"status": "missing", "log_id": log_id}
    path = (BACKEND_JOB_LOG_DIR / f"{safe_id}.json").resolve()
    if not path.exists() or not path_is_inside(path, BACKEND_JOB_LOG_DIR.resolve()):
        return {"status": "missing", "log_id": safe_id}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "status": "error",
            "log_id": safe_id,
            "log_path": str(path),
            "error": f"Could not parse backend job log: {exc}",
            "safe_note": "Backend job log detail is read-only. Parse errors do not trigger retries, process kills, command execution, or rollback.",
        }
    result_preview = ""
    result = data.get("result")
    if result is not None:
        try:
            result_preview = json.dumps(result, ensure_ascii=False, indent=2, default=str)[:2400]
        except Exception:
            result_preview = str(result)[:2400]
    return {
        "mode": "read-only-backend-job-log-detail",
        "status": "ok",
        "log_id": safe_id,
        "log_path": str(path),
        "bytes": path.stat().st_size,
        "job": {
            "id": data.get("id", ""),
            "kind": data.get("kind", ""),
            "label": data.get("label", ""),
            "status": data.get("status", ""),
            "safety": data.get("safety", ""),
            "created_at": data.get("created_at", 0),
            "updated_at": data.get("updated_at", 0),
            "error": data.get("error", ""),
            "cancel_requested": data.get("cancel_requested", False),
            "cancel_reason": data.get("cancel_reason", ""),
            "rollback_note": data.get("rollback_note", ""),
            "log_note": data.get("log_note", ""),
        },
        "events": data.get("events", []) if isinstance(data.get("events", []), list) else [],
        "event_count": len(data.get("events", [])) if isinstance(data.get("events", []), list) else 0,
        "result_preview": result_preview,
        "safe_note": "Backend job log detail is read-only project-local lifecycle evidence. It does not replay jobs, kill processes, run commands, or perform rollback.",
    }


def persisted_job_events(job_id: str) -> tuple[list[dict], str, str]:
    if not BACKEND_JOB_LOG_DIR.exists():
        return [], "", ""
    try:
        paths = sorted(
            [path for path in BACKEND_JOB_LOG_DIR.glob("*.json") if path.is_file()],
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
    except Exception:
        return [], "", ""
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if str(data.get("id", "")) == job_id:
            events = data.get("events", [])
            return (events if isinstance(events, list) else []), str(path), str(data.get("status", "unknown"))
    return [], "", ""


def backend_job_events(job_id: str, since: int = 0, limit: int = 32) -> dict:
    start = max(0, since)
    bounded_limit = max(1, min(limit, 100))
    source = "memory"
    log_path = ""
    status = "missing"
    events = []
    job = JOBS.get(job_id)
    if job:
        status = str(job.get("status", "unknown"))
        log_path = str(job.get("log_path", ""))
        raw_events = job.get("events", [])
        events = raw_events if isinstance(raw_events, list) else []
    else:
        events, log_path, status = persisted_job_events(job_id)
        if events:
            source = "persistent-log"

    selected = events[start:start + bounded_limit]
    return {
        "mode": "read-only-backend-job-events",
        "status": status,
        "job_id": job_id,
        "source": source,
        "log_path": log_path,
        "events": selected,
        "returned": len(selected),
        "event_count": len(events),
        "next_cursor": start + len(selected),
        "has_more": start + len(selected) < len(events),
        "safe_note": "Backend job events are read-only lifecycle updates for polling UI. This endpoint does not replay jobs, kill processes, run commands, or perform rollback.",
    }


def start_job(kind: str, label: str, func, *args) -> dict:
    prune_jobs()
    # Idempotent submission: an identical job already queued/running is
    # returned as-is instead of spawning a duplicate. This is the first half
    # of the multi-agent "needs manual retries" fix — duplicate submissions
    # used to pile up behind the 2-worker executor and look like hangs.
    for existing in JOBS.values():
        if (
            existing.get("kind") == kind
            and existing.get("label") == label
            and existing.get("status") in ("queued", "running")
        ):
            existing.setdefault("events", []).append(
                {"at": time.time(), "message": "Duplicate submission coalesced into this job."}
            )
            return existing
    job_id = uuid.uuid4().hex[:12]
    now = time.time()
    job = {
        "id": job_id,
        "kind": kind,
        "label": label,
        "status": "queued",
        "safety": "read-only",
        "created_at": now,
        "updated_at": now,
        "result": None,
        "error": "",
        "events": [{"at": now, "message": "Job queued."}],
        "cancel_requested": False,
        "cancelable": True,
        "rollback_note": "No rollback needed yet. This job is expected to be read-only or project-local report/draft work.",
    }
    persist_job_log(job, "queued")
    JOBS[job_id] = job

    def runner() -> None:
        if job.get("cancel_requested"):
            job["status"] = "cancelled"
            job["cancelable"] = False
            job["updated_at"] = time.time()
            job.setdefault("events", []).append({"at": job["updated_at"], "message": "Job cancelled before execution."})
            persist_job_log(job, "cancelled-before-execution")
            return
        job["status"] = "running"
        job["updated_at"] = time.time()
        job["cancelable"] = False
        job.setdefault("events", []).append({"at": job["updated_at"], "message": "Job started. Cancellation requests will be recorded but this runner will not kill processes."})
        persist_job_log(job, "started")
        # Bounded retry with exponential backoff. Jobs in this backend are
        # read-only/project-local by design, so re-running a failed attempt
        # is safe. This is the second half of the "needs manual retries"
        # fix: transient errors (file locks, agentmemory hiccups, slow git)
        # now self-heal instead of surfacing as failed jobs.
        attempts = 3
        backoffs = [1.5, 4.0]
        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                result = func(*args)
                last_exc = None
                if result is None:
                    job["status"] = "missing"
                    job["error"] = "Requested item was not found."
                    job["rollback_note"] = "No output was recorded because the requested item was missing."
                else:
                    job["status"] = "done"
                    job["result"] = result
                    job["rollback_note"] = result.get("rollback_note", job.get("rollback_note", "")) if isinstance(result, dict) else job.get("rollback_note", "")
                if attempt > 1:
                    job.setdefault("events", []).append(
                        {"at": time.time(), "message": f"Succeeded on retry attempt {attempt}/{attempts}."}
                    )
                break
            except Exception as exc:
                last_exc = exc
                if attempt < attempts and not job.get("cancel_requested"):
                    wait_s = backoffs[min(attempt - 1, len(backoffs) - 1)]
                    job.setdefault("events", []).append(
                        {"at": time.time(), "message": f"Attempt {attempt}/{attempts} failed ({exc}); retrying in {wait_s}s."}
                    )
                    job["updated_at"] = time.time()
                    persist_job_log(job, f"retry-{attempt}")
                    time.sleep(wait_s)
        if last_exc is not None:
            job["status"] = "failed"
            job["error"] = str(last_exc)
            job["rollback_note"] = "Inspect the error and any project-local log/report paths before retrying. No automatic rollback was attempted."
        job["updated_at"] = time.time()
        job["cancelable"] = False
        job.setdefault("events", []).append({"at": job["updated_at"], "message": f"Job finished with status {job['status']}."})
        persist_job_log(job, "finished")

    JOB_EXECUTOR.submit(runner)
    return job


def cancel_job(job_id: str, req: JobCancelRequest) -> dict:
    job = JOBS.get(job_id)
    if not job:
        return {"status": "missing", "job_id": job_id}
    now = time.time()
    reason = req.reason.strip() or "User requested cancellation from AI Town."
    status = str(job.get("status", "unknown"))
    if status == "queued":
        job["status"] = "cancelled"
        job["cancel_requested"] = True
        job["cancelable"] = False
        job["updated_at"] = now
        job["cancel_reason"] = reason
        job["rollback_note"] = "Cancelled before execution; no job function ran and no rollback is required."
        job.setdefault("events", []).append({"at": now, "message": f"Cancelled before execution: {reason}"})
    elif status == "running":
        job["cancel_requested"] = True
        job["updated_at"] = now
        job["cancel_reason"] = reason
        job["rollback_note"] = "Cancellation was requested while running. AI Town records the request but does not kill processes; inspect result/log paths after completion."
        job.setdefault("events", []).append({"at": now, "message": f"Cancellation requested while running: {reason}"})
    else:
        job["updated_at"] = now
        job["cancel_reason"] = reason
        job.setdefault("events", []).append({"at": now, "message": f"Cancellation requested after status {status}; no state change."})
    record_memory_event(
        f"Backend job cancel request: {job_id}",
        f"Status `{job.get('status', '')}` for `{job.get('label', '')}` from `{req.source_building}`. Reason: {reason}. Rollback: {job.get('rollback_note', '')}",
        "ai-town/jobs",
    )
    persist_job_log(job, "cancel-request")
    return {"status": "ok", "job": job, "queue": job_queue_snapshot()}


def job_queue_snapshot(limit: int = 16) -> dict:
    counts: dict[str, int] = {}
    for job in JOBS.values():
        status = str(job.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    recent = []
    for job in sorted(JOBS.values(), key=lambda item: item.get("updated_at", item.get("created_at", 0)), reverse=True)[:limit]:
        recent.append({
            "id": job.get("id", ""),
            "kind": job.get("kind", ""),
            "label": job.get("label", ""),
            "status": job.get("status", ""),
            "safety": job.get("safety", ""),
            "created_at": job.get("created_at", 0),
            "updated_at": job.get("updated_at", 0),
            "error": job.get("error", ""),
            "cancelable": job.get("cancelable", False),
            "cancel_requested": job.get("cancel_requested", False),
            "rollback_note": job.get("rollback_note", ""),
            "log_path": job.get("log_path", ""),
        })
    logs = latest_backend_job_logs(limit)
    return {
        "count": len(JOBS),
        "counts": counts,
        "recent": recent,
        "persistent_logs": logs,
        "persistent_log_count": len(logs),
        "log_dir": str(BACKEND_JOB_LOG_DIR),
        "safe_note": "Backend jobs expose status, bounded events, cancellation metadata, rollback notes, and project-local persistent job logs. Cancelling a running job records intent but never kills external processes.",
    }


def load_task_ledger() -> list[dict]:
    if not TASK_LEDGER_PATH.exists():
        return []
    try:
        data = json.loads(TASK_LEDGER_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def save_task_ledger(tasks: list[dict]) -> None:
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    TASK_LEDGER_PATH.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def append_local_task(task: dict) -> dict:
    tasks = load_task_ledger()
    tasks.insert(0, task)
    save_task_ledger(tasks[:200])
    return task


def markdown_draft_entries(root: Path, kind: str, limit: int = 12) -> list[dict]:
    if not root.exists():
        return []
    entries = []
    try:
        files = sorted(root.glob("*.md"), key=lambda item: item.stat().st_mtime, reverse=True)
    except Exception:
        return []
    for path in files[:limit]:
        try:
            entries.append({
                "id": path.stem,
                "kind": kind,
                "title": first_markdown_heading(path),
                "path": str(path),
                "bytes": path.stat().st_size,
                "updated": path.stat().st_mtime,
            })
        except Exception:
            continue
    return entries


def task_board_overview() -> dict:
    local_tasks = load_task_ledger()
    dispatch_drafts = markdown_draft_entries(AGENT_DISPATCH_DRAFTS_DIR, "agent-dispatch-draft")
    memory_events = markdown_draft_entries(MEMORY_EVENTS_DIR, "memory-event")
    recent_tasks = []
    for task in local_tasks[:40]:
        if not isinstance(task, dict):
            continue
        recent_tasks.append({
            "id": task.get("id", ""),
            "kind": "local-task",
            "title": task.get("title", "Task"),
            "status": task.get("status", "unknown"),
            "target_agent": task.get("target_agent", ""),
            "source": task.get("source", task.get("source_building", "")),
            "project_name": task.get("project_name", ""),
            "draft_path": task.get("draft_path", ""),
            "created_at": task.get("created_at", 0),
            "safety": task.get("safety", "project-local-task"),
        })
    status_counts: dict[str, int] = {}
    for task in recent_tasks:
        status = str(task.get("status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "name": "Task Board",
        "mode": "project-local-ledger",
        "ledger_path": str(TASK_LEDGER_PATH),
        "local_tasks": recent_tasks,
        "local_task_count": len(local_tasks),
        "status_counts": status_counts,
        "dispatch_drafts": dispatch_drafts,
        "dispatch_draft_count": len(dispatch_drafts),
        "memory_events": memory_events,
        "memory_event_count": len(memory_events),
        "safe_note": "Task Board writes only project-local task drafts and memory events under workspace/.",
    }


def daily_routes_overview() -> dict:
    quests = quest_registry_overview()
    task_board = task_board_overview()
    agent_hub = agent_hub_overview()
    today = time.strftime("%Y-%m-%d")
    signal_summary = {
        "quest_count": quests.get("count", 0),
        "local_task_count": task_board.get("local_task_count", 0),
        "dispatch_draft_count": task_board.get("dispatch_draft_count", 0),
        "memory_event_count": task_board.get("memory_event_count", 0),
        "agent_count": agent_hub.get("agent_count", 0),
        "companion_count": agent_hub.get("companion_count", 0),
        "queued_agent_tasks": agent_hub.get("task_count", 0),
        "queued_tool_invocations": agent_hub.get("tool_count", 0),
    }
    routes = [
        {
            "id": "morning-orientation",
            "title": "Morning Orientation",
            "district_id": "central-plaza",
            "building_ids": ["agent-hub", "task-board", "goal-tower"],
            "steps": [
                "Recruit or review one companion in Agent Hub.",
                "Check Task Board signals and local task count.",
                "Open Goal Tower to choose one bounded focus.",
            ],
            "reward": "Town rhythm badge and one active companion focus",
            "safety": "read-only-status-plus-local-save",
            "recommended_companion": "codex",
            "status_signals": [
                f"{signal_summary['companion_count']} companion(s) available in player progress",
                f"{signal_summary['local_task_count']} local task(s) in the project ledger",
            ],
        },
        {
            "id": "knowledge-sweep",
            "title": "Knowledge Sweep",
            "district_id": "research-quarter",
            "building_ids": ["knowledge-tower", "memory-library", "file-vault"],
            "steps": [
                "Inspect Knowledge Tower index health.",
                "Create or review one Memory Library proposal.",
                "Search File Vault for a project artifact and tag it if useful.",
            ],
            "reward": "Sharper shared context and cleaner local references",
            "safety": "read-only-indexing-with-project-local-drafts",
            "recommended_companion": "sonnet",
            "status_signals": [
                f"{signal_summary['memory_event_count']} memory event(s) already drafted",
                f"{quests.get('target_counts', {}).get('memory-library', 0)} quest(s) target Memory Library",
            ],
        },
        {
            "id": "dev-handoff",
            "title": "Developer Handoff",
            "district_id": "developer-row",
            "building_ids": ["code-workshop", "terminal-control", "github-harbor"],
            "steps": [
                "Generate a Code Workshop context pack or patch plan.",
                "Review Terminal Control allowlisted command posture.",
                "Draft a GitHub Harbor handoff without publishing it.",
            ],
            "reward": "A clean implementation handoff trail",
            "safety": "drafts-only-unless-explicitly-confirmed",
            "recommended_companion": "codex",
            "status_signals": [
                f"{signal_summary['dispatch_draft_count']} dispatch draft(s) visible",
                f"{signal_summary['queued_tool_invocations']} agent tool invocation(s) logged",
            ],
        },
        {
            "id": "research-loop",
            "title": "Research Loop",
            "district_id": "research-quarter",
            "building_ids": ["research-hall", "paper-reading-room", "research-data-center"],
            "steps": [
                "Queue a bounded research agent brief.",
                "Write a paper reading note for one concrete artifact.",
                "Add a research data provenance note.",
            ],
            "reward": "Audit-ready research trace",
            "safety": "project-local-research-notes",
            "recommended_companion": "aris",
            "status_signals": [
                f"{signal_summary['queued_agent_tasks']} agent task(s) in the local queue",
                f"{quests.get('target_counts', {}).get('research-hall', 0)} quest(s) target Research Hall",
            ],
        },
        {
            "id": "release-readiness",
            "title": "Release Readiness",
            "district_id": "harbor-release",
            "building_ids": ["testing-arena", "version-release-plaza", "system-monitor"],
            "steps": [
                "Run or inspect a smoke-test plan in Testing Arena.",
                "Draft a Version Release Plaza checklist.",
                "Open System Monitor for jobs, registries, and service posture.",
            ],
            "reward": "Visible confidence before handoff",
            "safety": "read-only-status-and-local-checklists",
            "recommended_companion": "codex",
            "status_signals": [
                f"{signal_summary['quest_count']} quest(s) loaded for playable progression",
                f"{signal_summary['agent_count']} configured town agent(s)",
            ],
        },
    ]
    return {
        "status": "ok",
        "date": today,
        "mode": "safe-daily-plan",
        "count": len(routes),
        "routes": routes,
        "signals": signal_summary,
        "safe_note": "Daily Routes are generated from local read-only status. Claiming a route is saved only in the Godot player profile.",
    }


def create_local_task(req: LocalTaskRequest) -> dict:
    task_id = uuid.uuid4().hex[:12]
    title = req.title.strip() or "AI Town follow-up task"
    body = req.body.strip() or "Describe the next safe local work action."
    target_agent = req.target_agent.strip() or "codex"
    source = req.source_building.strip() or "task-board"
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    draft_path = TASKS_DIR / f"{task_id}-{slugify_filename(title)}.md"
    draft = "\n".join([
        "---",
        f"id: {task_id}",
        f"title: {title}",
        f"target_agent: {target_agent}",
        f"source: {source}",
        "status: ready",
        "safety: project-local-task",
        "---",
        "",
        f"# {title}",
        "",
        "## Request",
        "",
        body,
        "",
        "## Safety",
        "",
        "- Created by AI Town Task Board.",
        "- This is a project-local task draft only.",
        "- No external agent, command, or repository action was invoked.",
    ])
    draft_path.write_text(draft, encoding="utf-8")
    task = {
        "id": task_id,
        "title": title,
        "target_agent": target_agent,
        "source": source,
        "status": req.status if req.status in {"ready", "planned", "blocked"} else "ready",
        "safety": "project-local-task",
        "draft_path": str(draft_path),
        "created_at": time.time(),
    }
    append_local_task(task)
    memory = record_memory_event(
        f"Task Board item created: {title}",
        f"Created local task `{title}` for `{target_agent}` from `{source}`.\n\n{body}\n\nDraft: `{draft_path}`",
        "ai-town/task-board",
    )
    return {
        "status": "saved",
        "task": task,
        "draft_path": str(draft_path),
        "memory_event": memory,
        "preview": draft,
        "safety": "project-local-write",
    }


def update_local_task_status(task_id: str, req: LocalTaskStatusRequest) -> Optional[dict]:
    allowed_status = {"ready", "planned", "in-progress", "blocked", "done", "archived"}
    new_status = req.status.strip().lower()
    if new_status not in allowed_status:
        new_status = "done"
    tasks = load_task_ledger()
    updated_task: Optional[dict] = None
    for task in tasks:
        if not isinstance(task, dict) or str(task.get("id", "")) != task_id:
            continue
        task["status"] = new_status
        task["updated_at"] = time.time()
        task["status_note"] = req.note.strip() or "Updated from AI Town Task Board."
        task["status_source"] = req.source_building.strip() or "task-board"
        history = task.get("status_history", [])
        if not isinstance(history, list):
            history = []
        history.append({
            "status": new_status,
            "note": task["status_note"],
            "source": task["status_source"],
            "updated_at": task["updated_at"],
        })
        task["status_history"] = history[-20:]
        updated_task = task
        break
    if not updated_task:
        return None
    save_task_ledger(tasks)
    draft_path = Path(str(updated_task.get("draft_path", "")))
    if draft_path.exists() and draft_path.is_file():
        try:
            text = draft_path.read_text(encoding="utf-8")
            text = re.sub(r"(?m)^status: .*$", f"status: {new_status}", text, count=1)
            text += "\n\n## Status Update\n\n"
            text += f"- {time.strftime('%Y-%m-%d %H:%M:%S')}: `{new_status}` — {updated_task.get('status_note', '')}\n"
            draft_path.write_text(text, encoding="utf-8")
        except Exception:
            pass
    memory = record_memory_event(
        f"Task Board item updated: {updated_task.get('title', task_id)}",
        f"Task `{updated_task.get('title', task_id)}` changed to `{new_status}`.\n\nNote: {updated_task.get('status_note', '')}",
        "ai-town/task-board",
    )
    return {
        "status": "updated",
        "task": updated_task,
        "memory_event": memory,
        "safety": "project-local-status-update",
    }


def get_local_task_detail(task_id: str) -> Optional[dict]:
    for task in load_task_ledger():
        if not isinstance(task, dict) or str(task.get("id", "")) != task_id:
            continue
        draft_path = Path(str(task.get("draft_path", "")))
        preview = ""
        exists = False
        truncated = False
        bytes_size = 0
        if draft_path.exists() and draft_path.is_file():
            try:
                bytes_size = draft_path.stat().st_size
                text = draft_path.read_text(encoding="utf-8", errors="replace")
                preview = text[:5000]
                truncated = len(text) > len(preview)
                exists = True
            except Exception:
                preview = "Task draft exists but could not be previewed."
                exists = True
        return {
            "status": "ok",
            "task": task,
            "draft_path": str(draft_path) if str(draft_path) else "",
            "draft_exists": exists,
            "bytes": bytes_size,
            "preview": preview,
            "truncated": truncated,
            "safety": "bounded-project-local-preview",
        }
    return None


def project_document_entries(limit: int = 30) -> list[dict]:
    paths = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "PLAN.md",
        PROJECT_ROOT / "STRUCTURE.md",
        PROJECT_ROOT / "MEMORY.md",
        PROJECT_ROOT / "ASSETS.md",
        PROJECT_ROOT / "docs" / "ARCHITECTURE_GODOT_REBUILD.md",
        PROJECT_ROOT / "docs" / "PROJECT_AUDIT_2026-05-29.md",
        PROJECT_ROOT / "docs" / "VISUAL_BASELINE.md",
        PROJECT_ROOT / "godot" / "README.md",
    ]
    docs = []
    for path in paths:
        if not path.exists() or not path_is_inside(path, PROJECT_ROOT):
            continue
        try:
            docs.append({
                "id": slugify_filename(str(path.relative_to(PROJECT_ROOT))),
                "title": first_markdown_heading(path),
                "name": path.name,
                "path": str(path),
                "relative_path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "updated": path.stat().st_mtime,
            })
        except Exception:
            continue
    return docs[:limit]


def writing_studio_overview() -> dict:
    drafts = markdown_draft_entries(DRAFTS_DIR, "writing-draft", 20)
    return {
        "name": "Writing Studio",
        "mode": "project-local-drafts",
        "draft_dir": str(DRAFTS_DIR),
        "documents": project_document_entries(),
        "document_count": len(project_document_entries()),
        "drafts": drafts,
        "draft_count": len(drafts),
        "safe_note": "Writing Studio writes only Markdown drafts under workspace/drafts and records local memory events.",
    }


def create_writing_draft(req: WritingDraftRequest) -> dict:
    title = req.title.strip() or "AI Town writing note"
    body = req.body.strip() or "Draft the next project note here."
    category = slugify_filename(req.category or "general")
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    draft_path = DRAFTS_DIR / f"{timestamp}-{category}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"category: {category}",
        "source: ai-town/writing-studio",
        "status: draft",
        "safety: project-local-write",
        "---",
        "",
        f"# {title}",
        "",
        body,
        "",
        "## Next",
        "",
        "- Review this draft before copying it into project docs, shared memory, or external notes.",
    ])
    draft_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Writing draft created: {title}",
        f"Created project-local writing draft `{title}`.\n\nDraft: `{draft_path}`",
        "ai-town/writing-studio",
    )
    return {
        "status": "saved",
        "draft_path": str(draft_path),
        "memory_event": memory,
        "preview": content,
        "safety": "project-local-write",
    }


def automation_script_catalog() -> list[dict]:
    scripts = []
    candidates: list[tuple[Path, str, str, str]] = [
        (PROJECT_ROOT / "tools" / "verify-smoke.ps1", "Verify Smoke", "Run project smoke checks for backend syntax and Godot headless startup.", "manual-confirm-required"),
        (PROJECT_ROOT / "tools" / "capture-visual-smoke.ps1", "Capture Visual Smoke", "Run the visual smoke capture flow and refresh screenshots/visual-smoke.png.", "manual-confirm-required"),
        (PROJECT_ROOT / "start.cmd", "Start Full Stack", "Start the local backend and Godot client through the project launcher.", "manual-only"),
        (PROJECT_ROOT / "start-backend.cmd", "Start Backend", "Start only the FastAPI backend service.", "manual-only"),
        (PROJECT_ROOT / "start-godot.cmd", "Start Godot", "Start only the Godot client.", "manual-only"),
        (PROJECT_ROOT / "stop.cmd", "Stop Launcher", "Legacy stop helper. Listed for visibility only; Automation Factory will not schedule it.", "blocked-manual-only"),
    ]
    for path, name, description, safety in candidates:
        if not path.exists() or not path_is_inside(path, PROJECT_ROOT):
            continue
        try:
            stat = path.stat()
        except Exception:
            continue
        scripts.append({
            "id": slugify_filename(path.name),
            "name": name,
            "path": str(path),
            "relative_path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "extension": path.suffix.lower(),
            "bytes": stat.st_size,
            "updated": stat.st_mtime,
            "description": description,
            "safety": safety,
            "runnable_now": False,
        })
    return scripts


def automation_scheduled_task_snapshot(limit: int = 16) -> dict:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "$tasks = Get-ScheduledTask | "
            "Select-Object -First %d TaskName,TaskPath,State,Description; "
            "$tasks | ConvertTo-Json -Depth 3 -Compress"
        ) % max(1, min(limit, 40)),
    ]
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            check=False,
        )
    except Exception as exc:
        return {
            "status": "unavailable",
            "mode": "read-only-windows-scheduler-snapshot",
            "tasks": [],
            "task_count": 0,
            "error": str(exc)[:1200],
            "safe_note": "Scheduler snapshot failed before any scheduler mutation was attempted.",
        }
    output = (proc.stdout or "").strip()
    tasks = []
    if output:
        try:
            parsed = json.loads(output)
            if isinstance(parsed, dict):
                parsed = [parsed]
            if isinstance(parsed, list):
                for item in parsed:
                    if not isinstance(item, dict):
                        continue
                    tasks.append({
                        "name": str(item.get("TaskName", "")),
                        "path": str(item.get("TaskPath", "")),
                        "state": str(item.get("State", "")),
                        "description": str(item.get("Description", ""))[:500],
                    })
        except Exception:
            tasks = []
    return {
        "status": "ok" if proc.returncode == 0 else "unavailable",
        "mode": "read-only-windows-scheduler-snapshot",
        "tasks": tasks[:limit],
        "task_count": len(tasks[:limit]),
        "sample_limit": limit,
        "exit_code": proc.returncode,
        "error": (proc.stderr or "")[:1200],
        "safe_note": "This is a bounded read-only Windows Scheduled Tasks snapshot. It does not create, enable, disable, delete, or run scheduled tasks.",
    }


def automation_factory_overview() -> dict:
    scripts = automation_script_catalog()
    drafts = markdown_draft_entries(AUTOMATION_DRAFTS_DIR, "automation-draft", 20)
    scheduler = automation_scheduled_task_snapshot(8)
    return {
        "name": "Automation Factory",
        "mode": "script-catalog-blueprints-scheduler-readonly",
        "draft_dir": str(AUTOMATION_DRAFTS_DIR),
        "scripts": scripts,
        "script_count": len(scripts),
        "scheduler": scheduler,
        "scheduled_task_count": scheduler.get("task_count", 0),
        "drafts": drafts,
        "draft_count": len(drafts),
        "jobs": job_queue_snapshot(),
        "safe_note": "Automation Factory catalogs local project scripts, reads a bounded scheduler snapshot, and writes draft blueprints only. It does not install schedulers, stop services, or run commands.",
    }


def create_automation_draft(req: AutomationDraftRequest) -> dict:
    title = req.title.strip() or "AI Town automation blueprint"
    body = req.body.strip() or "Describe the safe automation workflow to review before enabling it."
    source = req.source_building.strip() or "automation-factory"
    script_id = slugify_filename(req.script_id) if req.script_id else ""
    schedule_hint = req.schedule_hint.strip() or "manual review first"
    scripts = automation_script_catalog()
    selected_script = next((item for item in scripts if item.get("id") == script_id), None)
    if script_id and not selected_script:
        selected_script = {"id": script_id, "name": script_id, "path": "not found", "safety": "unverified-script"}
    AUTOMATION_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    draft_path = AUTOMATION_DRAFTS_DIR / f"{timestamp}-{slugify_filename(title)}.md"
    script_lines = [
        f"- Script id: `{selected_script.get('id', 'none') if selected_script else 'none'}`",
        f"- Script name: `{selected_script.get('name', 'none') if selected_script else 'none'}`",
        f"- Script path: `{selected_script.get('path', 'none') if selected_script else 'none'}`",
        f"- Script safety: `{selected_script.get('safety', 'draft-only') if selected_script else 'draft-only'}`",
    ]
    content = "\n".join([
        "---",
        f"title: {title}",
        f"source: ai-town/{source}",
        "status: draft",
        "safety: draft-only-automation",
        f"schedule_hint: {schedule_hint}",
        "---",
        "",
        f"# {title}",
        "",
        "## Intent",
        "",
        body,
        "",
        "## Candidate Script",
        "",
        *script_lines,
        "",
        "## Proposed Schedule",
        "",
        schedule_hint,
        "",
        "## Safety Gate",
        "",
        "- This is only an Automation Factory blueprint.",
        "- No scheduler, command, service, repository, or external agent was changed.",
        "- Before activation, route through Terminal Control or a future confirm-required automation runner with logs and rollback notes.",
    ])
    draft_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Automation draft created: {title}",
        f"Created project-local automation blueprint `{title}`.\n\nDraft: `{draft_path}`\n\nSchedule hint: `{schedule_hint}`",
        "ai-town/automation-factory",
    )
    return {
        "status": "saved",
        "draft_path": str(draft_path),
        "memory_event": memory,
        "script": selected_script or {},
        "preview": content,
        "safety": "draft-only-automation",
    }


def settings_center_overview() -> dict:
    registries = [
        {
            "id": "buildings",
            "name": "Building registry",
            "path": str(BUILDING_REGISTRY_PATH),
            "exists": BUILDING_REGISTRY_PATH.exists(),
            "count": len(load_json_registry(BUILDING_REGISTRY_PATH)),
            "safety": "read-only-inspect",
        },
        {
            "id": "agents",
            "name": "Agent registry",
            "path": str(AGENT_REGISTRY_PATH),
            "exists": AGENT_REGISTRY_PATH.exists(),
            "count": len(load_json_registry(AGENT_REGISTRY_PATH)),
            "safety": "read-only-inspect",
        },
        {
            "id": "model-profiles",
            "name": "Model profile registry",
            "path": str(MODEL_PROFILE_REGISTRY_PATH),
            "exists": MODEL_PROFILE_REGISTRY_PATH.exists(),
            "count": len(load_model_profiles()),
            "safety": "no-secret-display",
        },
        {
            "id": "workspaces",
            "name": "Workspace registry",
            "path": str(WORKSPACE_REGISTRY_PATH),
            "exists": WORKSPACE_REGISTRY_PATH.exists(),
            "count": len(load_workspace_registry()),
            "safety": "allowlisted-lazy-read",
        },
        {
            "id": "quests",
            "name": "Quest registry",
            "path": str(QUEST_REGISTRY_PATH),
            "exists": QUEST_REGISTRY_PATH.exists(),
            "count": len(load_quest_registry()),
            "safety": "safe-read-only-progression",
        },
        {
            "id": "npc-quests",
            "name": "NPC quest-chain registry",
            "path": str(NPC_QUEST_REGISTRY_PATH),
            "exists": NPC_QUEST_REGISTRY_PATH.exists(),
            "count": len(load_json_registry(NPC_QUEST_REGISTRY_PATH)),
            "safety": "safe-read-only-npc-progression",
        },
        {
            "id": "room-scenes",
            "name": "Room scene registry",
            "path": str(ROOM_SCENE_REGISTRY_PATH),
            "exists": ROOM_SCENE_REGISTRY_PATH.exists(),
            "count": len(load_json_registry(ROOM_SCENE_REGISTRY_PATH)),
            "safety": "safe-read-only-interior-layouts",
        },
        {
            "id": "map-decor",
            "name": "Map decor registry",
            "path": str(MAP_DECOR_REGISTRY_PATH),
            "exists": MAP_DECOR_REGISTRY_PATH.exists(),
            "count": len(load_json_registry(MAP_DECOR_REGISTRY_PATH)),
            "safety": "safe-read-only-map-landmarks",
        },
        {
            "id": "districts",
            "name": "District registry",
            "path": str(DISTRICT_REGISTRY_PATH),
            "exists": DISTRICT_REGISTRY_PATH.exists(),
            "count": len(load_json_registry(DISTRICT_REGISTRY_PATH)),
            "safety": "read-only-map-routing",
        },
        {
            "id": "plugin-manifests",
            "name": "Plugin manifest registry",
            "path": str(PLUGIN_MANIFEST_REGISTRY_PATH),
            "exists": PLUGIN_MANIFEST_REGISTRY_PATH.exists(),
            "count": len(load_json_registry(PLUGIN_MANIFEST_REGISTRY_PATH)),
            "safety": "read-only-extension-manifest-audit",
        },
    ]
    launchers = []
    for path in [PROJECT_ROOT / "start.cmd", PROJECT_ROOT / "start-backend.cmd", PROJECT_ROOT / "start-godot.cmd", PROJECT_ROOT / "stop.cmd"]:
        launchers.append({
            "id": slugify_filename(path.name),
            "name": path.name,
            "path": str(path),
            "exists": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
            "safety": "manual-launcher" if path.name.lower() != "stop.cmd" else "blocked-manual-only",
        })
    env_requirements = []
    for profile in load_model_profiles():
        key_env = profile.get("key_env", "")
        base_url_env = profile.get("base_url_env", "")
        if key_env:
            env_requirements.append({
                "name": key_env,
                "kind": "api-key",
                "provider": profile.get("provider", profile.get("name", "")),
                "configured": env_is_configured(key_env),
                "secret_policy": "name-and-status-only",
            })
        if base_url_env:
            env_requirements.append({
                "name": base_url_env,
                "kind": "base-url",
                "provider": profile.get("provider", profile.get("name", "")),
                "configured": env_is_configured(base_url_env),
                "value_preview": os.getenv(base_url_env, profile.get("default_base_url", "")),
                "secret_policy": "non-secret-url",
            })
    workspace = [
        folder_status("settings_drafts", SETTINGS_DRAFTS_DIR, 8),
        folder_status("drafts", DRAFTS_DIR, 6),
        folder_status("tasks", TASKS_DIR, 6),
        folder_status("agent_chats", AGENT_CHAT_DIR, 6),
        folder_status("agent_runner_dispatches", AGENT_RUNNER_DISPATCH_DIR, 6),
        folder_status("agent_task_logs", AGENT_TASK_LOG_DIR, 6),
        folder_status("agent_tool_logs", AGENT_TOOL_LOG_DIR, 6),
        folder_status("memory_proposals", MEMORY_PROPOSALS_DIR, 6),
        folder_status("memory_promotions", MEMORY_PROMOTIONS_DIR, 6),
        folder_status("knowledge_index", KNOWLEDGE_INDEX_DIR, 6),
        folder_status("file_vault_index", FILE_VAULT_INDEX_DIR, 6),
        folder_status("file_organize_drafts", FILE_ORGANIZE_DRAFTS_DIR, 6),
        folder_status("code_contexts", CODE_CONTEXT_DIR, 6),
        folder_status("code_patch_plans", CODE_PATCH_PLANS_DIR, 6),
        folder_status("project_verification_logs", PROJECT_VERIFICATION_LOG_DIR, 6),
        folder_status("github_harbor_drafts", GITHUB_HARBOR_DRAFTS_DIR, 6),
        folder_status("model_config_drafts", MODEL_CONFIG_DRAFTS_DIR, 6),
        folder_status("model_key_vault", MODEL_KEY_VAULT_DIR, 6),
        folder_status("automation_drafts", AUTOMATION_DRAFTS_DIR, 6),
        folder_status("memory_events", MEMORY_EVENTS_DIR, 6),
    ]
    workspace_registry = workspace_registry_overview()
    registry_health = registry_health_overview()
    return {
        "name": "Settings Center",
        "mode": "read-only-plus-draft",
        "draft_dir": str(SETTINGS_DRAFTS_DIR),
        "registries": registries,
        "registry_count": len(registries),
        "registry_health": registry_health,
        "launchers": launchers,
        "launcher_count": len(launchers),
        "env_requirements": env_requirements,
        "env_count": len(env_requirements),
        "workspace": workspace,
        "workspace_registry": workspace_registry,
        "drafts": markdown_draft_entries(SETTINGS_DRAFTS_DIR, "settings-draft", 20),
        "safe_note": "Settings Center inspects registries, launcher files, registry health, and environment variable requirements. It writes review drafts only under workspace/settings-drafts and never returns raw secret values.",
    }


def create_settings_draft(req: SettingsDraftRequest) -> dict:
    title = req.title.strip() or "AI Town settings draft"
    body = req.body.strip() or "Describe the settings change to review before applying it."
    category = slugify_filename(req.category or "config")
    source = req.source_building.strip() or "settings-center"
    SETTINGS_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    draft_path = SETTINGS_DRAFTS_DIR / f"{timestamp}-{category}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"category: {category}",
        f"source: ai-town/{source}",
        "status: draft",
        "safety: settings-draft-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Proposed Change",
        "",
        body,
        "",
        "## Review Checklist",
        "",
        "- Confirm the target registry, launcher, or environment variable.",
        "- Confirm no raw API key or secret is written into project files.",
        "- Apply manually or through a future confirm-required settings runner.",
        "- Run smoke checks after applying any real configuration change.",
    ])
    draft_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Settings draft created: {title}",
        f"Created project-local settings draft `{title}`.\n\nDraft: `{draft_path}`",
        "ai-town/settings-center",
    )
    return {
        "status": "saved",
        "draft_path": str(draft_path),
        "memory_event": memory,
        "preview": content,
        "safety": "settings-draft-only",
    }


def plan_verification_entries(limit: int = 16) -> list[dict]:
    path = PROJECT_ROOT / "PLAN.md"
    if not path.exists():
        return []
    entries = []
    in_log = False
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() == "## Verification Log":
                in_log = True
                continue
            if in_log and line.startswith("## "):
                break
            if in_log and line.startswith("- "):
                entries.append({
                    "id": f"verification-{len(entries) + 1}",
                    "title": line[2:].strip(),
                    "path": str(path),
                    "kind": "verification-log",
                })
    except Exception:
        return []
    return list(reversed(entries[-limit:]))


def verification_script_entries() -> list[dict]:
    scripts = []
    candidates = [
        (PROJECT_ROOT / "tools" / "verify-smoke.ps1", "Smoke Verification", "Python compile, FastAPI endpoint smoke, and Godot headless startup."),
        (PROJECT_ROOT / "tools" / "capture-visual-smoke.ps1", "Visual Smoke Capture", "Short normal Godot render pass that updates screenshots/visual-smoke.png."),
        (PROJECT_ROOT / "tools" / "capture-room-visuals.ps1", "All-Room Visual Capture", "Registry-driven room screenshot capture with screenshots/room-scenes-manifest.json evidence."),
    ]
    for path, name, description in candidates:
        scripts.append({
            "id": slugify_filename(path.name),
            "name": name,
            "path": str(path),
            "exists": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
            "updated": path.stat().st_mtime if path.exists() else 0,
            "description": description,
            "safety": "manual-confirm-required",
        })
    return scripts


def visual_smoke_artifact() -> dict:
    path = PROJECT_ROOT / "screenshots" / "visual-smoke.png"
    if not path.exists():
        return {
            "name": "visual-smoke.png",
            "path": str(path),
            "exists": False,
            "status": "missing",
        }
    stat = path.stat()
    return {
        "name": "visual-smoke.png",
        "path": str(path),
        "exists": True,
        "status": "available",
        "bytes": stat.st_size,
        "updated": stat.st_mtime,
    }


def visual_manifest_audit() -> dict:
    screenshots_dir = PROJECT_ROOT / "screenshots"
    manifest_path = screenshots_dir / "room-scenes-manifest.json"
    room_scenes = load_json_registry(ROOM_SCENE_REGISTRY_PATH)
    registry_ids = [str(scene.get("id", "")) for scene in room_scenes if isinstance(scene, dict) and scene.get("id")]
    registry_set = set(registry_ids)
    if not manifest_path.exists():
        return {
            "mode": "read-only-room-visual-manifest-audit",
            "status": "missing",
            "manifest_path": str(manifest_path),
            "registry_room_count": len(registry_ids),
            "manifest_room_count": 0,
            "coverage_ok": False,
            "safe_note": "Visual manifest audit reads project-local screenshot evidence only. It does not capture screenshots, start Godot, edit assets, or mutate files.",
        }
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {
            "mode": "read-only-room-visual-manifest-audit",
            "status": "parse-error",
            "manifest_path": str(manifest_path),
            "error": str(exc)[:300],
            "registry_room_count": len(registry_ids),
            "coverage_ok": False,
            "safe_note": "Visual manifest audit reads project-local screenshot evidence only. Parse errors do not trigger screenshot capture or asset edits.",
        }

    entries = manifest.get("screenshots", [])
    if not isinstance(entries, list):
        entries = []
    seen_ids = []
    audited = []
    missing_files = []
    small_files = []
    hash_mismatches = []
    invalid_paths = []
    min_size = int(manifest.get("min_size_bytes", 10000) or 10000)
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        room_id = str(entry.get("room_id", ""))
        seen_ids.append(room_id)
        rel_file = str(entry.get("file", ""))
        path = (PROJECT_ROOT / rel_file).resolve()
        path_ok = path_is_inside(path, screenshots_dir.resolve())
        exists = path.exists() and path.is_file() and path_ok
        actual_bytes = path.stat().st_size if exists else 0
        expected_bytes = int(entry.get("bytes", 0) or 0)
        expected_hash = str(entry.get("sha256", "")).lower()
        actual_hash = ""
        hash_ok = False
        if not path_ok:
            invalid_paths.append({"room_id": room_id, "file": rel_file})
        elif not exists:
            missing_files.append({"room_id": room_id, "file": rel_file})
        else:
            if actual_bytes < min_size:
                small_files.append({"room_id": room_id, "file": rel_file, "bytes": actual_bytes})
            try:
                digest = hashlib.sha256()
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                actual_hash = digest.hexdigest()
                hash_ok = bool(expected_hash) and actual_hash == expected_hash
                if expected_hash and actual_hash != expected_hash:
                    hash_mismatches.append({"room_id": room_id, "file": rel_file, "expected": expected_hash, "actual": actual_hash})
            except Exception as exc:
                hash_mismatches.append({"room_id": room_id, "file": rel_file, "error": str(exc)[:200]})
        audited.append({
            "room_id": room_id,
            "title": entry.get("title", ""),
            "file": rel_file,
            "exists": exists,
            "path_ok": path_ok,
            "bytes": actual_bytes,
            "expected_bytes": expected_bytes,
            "bytes_match": exists and actual_bytes == expected_bytes,
            "sha256_match": hash_ok,
        })

    manifest_set = set(seen_ids)
    missing_room_ids = sorted(registry_set - manifest_set)
    extra_room_ids = sorted(manifest_set - registry_set)
    duplicate_room_ids = sorted({room_id for room_id in seen_ids if room_id and seen_ids.count(room_id) > 1})
    valid_count = len([item for item in audited if item.get("exists") and item.get("sha256_match")])
    sizes = [int(item.get("bytes", 0) or 0) for item in audited if item.get("exists")]
    coverage_ok = (
        len(entries) == len(registry_ids)
        and not missing_room_ids
        and not extra_room_ids
        and not duplicate_room_ids
        and not missing_files
        and not invalid_paths
        and not small_files
        and not hash_mismatches
    )
    return {
        "mode": "read-only-room-visual-manifest-audit",
        "status": "ok" if coverage_ok else "needs-review",
        "manifest_path": str(manifest_path),
        "generated_at": manifest.get("generated_at", ""),
        "capture_mode": manifest.get("mode", ""),
        "registry": manifest.get("registry", ""),
        "registry_room_count": len(registry_ids),
        "manifest_room_count": int(manifest.get("room_count", len(entries)) or 0),
        "entry_count": len(entries),
        "valid_screenshot_count": valid_count,
        "coverage_ok": coverage_ok,
        "missing_room_ids": missing_room_ids,
        "extra_room_ids": extra_room_ids,
        "duplicate_room_ids": duplicate_room_ids,
        "missing_files": missing_files[:12],
        "invalid_paths": invalid_paths[:12],
        "small_files": small_files[:12],
        "hash_mismatches": hash_mismatches[:12],
        "missing_file_count": len(missing_files),
        "invalid_path_count": len(invalid_paths),
        "small_file_count": len(small_files),
        "hash_mismatch_count": len(hash_mismatches),
        "min_bytes": min(sizes) if sizes else 0,
        "max_bytes": max(sizes) if sizes else 0,
        "screenshots": audited[:40],
        "safe_note": "Visual manifest audit verifies existing project-local screenshot evidence against the room registry and SHA-256 hashes. It does not capture screenshots, start Godot, edit assets, or mutate files.",
    }


def build_readiness_audit() -> dict:
    godot_dir = PROJECT_ROOT / "godot"
    project_file = godot_dir / "project.godot"
    main_scene = godot_dir / "scenes" / "main.tscn"
    main_script = godot_dir / "scripts" / "Main.gd"
    export_presets = godot_dir / "export_presets.cfg"
    godot_gui = PROJECT_ROOT / "tools" / "godot" / "Godot_v4.6.3-stable_win64.exe"
    godot_console = PROJECT_ROOT / "tools" / "godot" / "Godot_v4.6.3-stable_win64_console.exe"
    dist_dir = PROJECT_ROOT / "dist" / "ai-town"
    launcher_files = [
        PROJECT_ROOT / "start.cmd",
        PROJECT_ROOT / "start-backend.cmd",
        PROJECT_ROOT / "start-godot.cmd",
    ]
    export_text = ""
    export_path = ""
    export_platform = ""
    export_runnable = False
    export_embed_pck = False
    export_custom_debug = ""
    export_custom_release = ""
    if export_presets.exists():
        try:
            export_text = export_presets.read_text(encoding="utf-8", errors="replace")
            path_match = re.search(r'^export_path="([^"]+)"', export_text, re.M)
            platform_match = re.search(r'^platform="([^"]+)"', export_text, re.M)
            runnable_match = re.search(r"^runnable=(true|false)", export_text, re.M)
            embed_match = re.search(r"^binary_format/embed_pck=(true|false)", export_text, re.M)
            custom_debug_match = re.search(r'^custom_template/debug="([^"]*)"', export_text, re.M)
            custom_release_match = re.search(r'^custom_template/release="([^"]*)"', export_text, re.M)
            export_path = path_match.group(1) if path_match else ""
            export_platform = platform_match.group(1) if platform_match else ""
            export_runnable = bool(runnable_match and runnable_match.group(1) == "true")
            export_embed_pck = bool(embed_match and embed_match.group(1) == "true")
            export_custom_debug = custom_debug_match.group(1) if custom_debug_match else ""
            export_custom_release = custom_release_match.group(1) if custom_release_match else ""
        except Exception:
            export_text = ""
    custom_debug_path = (godot_dir / export_custom_debug).resolve() if export_custom_debug else Path("")
    custom_release_path = (godot_dir / export_custom_release).resolve() if export_custom_release else Path("")
    project_text = ""
    configured_main_scene = ""
    configured_features = ""
    if project_file.exists():
        try:
            project_text = project_file.read_text(encoding="utf-8", errors="replace")
            main_match = re.search(r'^run/main_scene="([^"]+)"', project_text, re.M)
            feature_match = re.search(r'config/features=PackedStringArray\("([^"]+)"\)', project_text)
            configured_main_scene = main_match.group(1) if main_match else ""
            configured_features = feature_match.group(1) if feature_match else ""
        except Exception:
            project_text = ""
    files = [
        {"id": "godot-project", "name": "Godot project", "path": project_file, "required": True},
        {"id": "main-scene", "name": "Main scene", "path": main_scene, "required": True},
        {"id": "main-script", "name": "Main script", "path": main_script, "required": True},
        {"id": "export-presets", "name": "Export presets", "path": export_presets, "required": True},
        {"id": "godot-gui", "name": "Godot GUI binary", "path": godot_gui, "required": True},
        {"id": "godot-console", "name": "Godot console binary", "path": godot_console, "required": True},
        *[
            {"id": slugify_filename(path.name), "name": path.name, "path": path, "required": True}
            for path in launcher_files
        ],
    ]
    file_entries = []
    for item in files:
        path = Path(item["path"])
        exists = path.exists()
        file_entries.append({
            "id": item["id"],
            "name": item["name"],
            "path": str(path),
            "exists": exists,
            "required": item["required"],
            "bytes": path.stat().st_size if exists else 0,
        })
    checks = [
        {"id": "project-file", "label": "Godot project file exists", "ok": project_file.exists(), "detail": str(project_file)},
        {"id": "project-version", "label": "Godot project targets 4.6", "ok": configured_features.startswith("4.6"), "detail": configured_features},
        {"id": "main-scene-config", "label": "Main scene configured", "ok": configured_main_scene == "res://scenes/main.tscn" and main_scene.exists(), "detail": configured_main_scene},
        {"id": "main-script", "label": "Main script exists", "ok": main_script.exists(), "detail": str(main_script)},
        {"id": "godot-binaries", "label": "Pinned Godot binaries exist", "ok": godot_gui.exists() and godot_console.exists(), "detail": str(godot_gui.parent)},
        {"id": "launchers", "label": "Project launchers exist", "ok": all(path.exists() for path in launcher_files), "detail": ", ".join(path.name for path in launcher_files)},
        {"id": "export-presets", "label": "Godot export preset exists", "ok": export_presets.exists(), "detail": str(export_presets)},
        {"id": "windows-export", "label": "Windows Desktop export target configured", "ok": export_platform == "Windows Desktop" and export_runnable and bool(export_path), "detail": f"{export_platform} -> {export_path}"},
        {"id": "embedded-pck", "label": "Export embeds PCK", "ok": export_embed_pck, "detail": str(export_embed_pck)},
        {"id": "custom-release-template", "label": "Project-local Windows release template exists", "ok": bool(export_custom_release) and custom_release_path.exists(), "detail": str(custom_release_path) if export_custom_release else ""},
        {"id": "custom-debug-template", "label": "Project-local Windows debug template exists", "ok": bool(export_custom_debug) and custom_debug_path.exists(), "detail": str(custom_debug_path) if export_custom_debug else ""},
        {"id": "dist-dir", "label": "Distribution output directory present", "ok": dist_dir.exists(), "detail": str(dist_dir)},
    ]
    ok_count = len([item for item in checks if item["ok"]])
    missing_required = [item for item in file_entries if item["required"] and not item["exists"]]
    warnings = []
    if not dist_dir.exists():
        warnings.append("Distribution output folder is not present yet; create it before running a real Godot export.")
    if export_presets.exists() and not export_path:
        warnings.append("Export preset exists but export_path could not be read.")
    return {
        "mode": "read-only-godot-build-readiness",
        "status": "ok" if ok_count == len(checks) else "needs-review",
        "checks": checks,
        "checks_passed": ok_count,
        "checks_total": len(checks),
        "files": file_entries,
        "missing_required": missing_required,
        "missing_required_count": len(missing_required),
        "godot": {
            "project": str(project_file),
            "features": configured_features,
            "main_scene": configured_main_scene,
            "gui_binary": str(godot_gui),
            "console_binary": str(godot_console),
        },
        "export": {
            "preset_path": str(export_presets),
            "platform": export_platform,
            "runnable": export_runnable,
            "export_path": export_path,
            "embed_pck": export_embed_pck,
            "custom_debug_template": export_custom_debug,
            "custom_debug_template_path": str(custom_debug_path) if export_custom_debug else "",
            "custom_release_template": export_custom_release,
            "custom_release_template_path": str(custom_release_path) if export_custom_release else "",
            "dist_dir": str(dist_dir),
            "dist_exists": dist_dir.exists(),
        },
        "warnings": warnings,
        "safe_note": "Build readiness is read-only. It inspects Godot project/export/launcher files and does not run exports, start services, package binaries, edit files, or stop processes.",
    }


def godot_export_tool_audit() -> dict:
    script_path = PROJECT_ROOT / "tools" / "export-godot.ps1"
    installer_path = PROJECT_ROOT / "tools" / "install-godot-templates.ps1"
    reports_dir = PROJECT_ROOT / "workspace" / "export-reports"
    report_path = reports_dir / "latest-godot-export-report.json"
    output_path = PROJECT_ROOT / "dist" / "ai-town" / "AI Town.exe"
    report = {}
    report_status = "missing"
    parse_error = ""
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8-sig"))
            report_status = str(report.get("status", "unknown"))
        except Exception as exc:
            report_status = "parse-error"
            parse_error = str(exc)[:300]
    checks = report.get("checks", []) if isinstance(report, dict) else []
    blockers = report.get("blockers", []) if isinstance(report, dict) else []
    if not isinstance(checks, list):
        checks = []
    if not isinstance(blockers, list):
        blockers = []
    output_exists = output_path.exists()
    return {
        "mode": "read-only-godot-export-tool-audit",
        "status": report_status,
        "script_path": str(script_path),
        "script_exists": script_path.exists(),
        "template_installer_path": str(installer_path),
        "template_installer_exists": installer_path.exists(),
        "report_path": str(report_path),
        "report_exists": report_path.exists(),
        "parse_error": parse_error,
        "run_export": bool(report.get("run_export", False)) if isinstance(report, dict) else False,
        "preset": report.get("preset", "") if isinstance(report, dict) else "",
        "output_path": str(output_path),
        "output_exists": output_exists,
        "output_bytes": output_path.stat().st_size if output_exists else 0,
        "blocker_count": len(blockers),
        "blockers": blockers[:10],
        "check_count": len(checks),
        "checks_passed": len([item for item in checks if isinstance(item, dict) and item.get("ok")]),
        "template_root": report.get("template_root", "") if isinstance(report, dict) else "",
        "template_matches": report.get("template_matches", []) if isinstance(report, dict) else [],
        "exit_code": report.get("exit_code") if isinstance(report, dict) else None,
        "stdout_tail": report.get("stdout_tail", [])[-20:] if isinstance(report.get("stdout_tail", []), list) else [],
        "command_preview": report.get("command_preview", []) if isinstance(report, dict) else [],
        "safe_note": "Export tool audit is read-only. It reads tools/export-godot.ps1 and the latest project-local export report only; it does not run exports, start services, kill processes, change Git state, package binaries, or publish releases.",
    }


def packaged_launch_readiness() -> dict:
    launcher_path = PROJECT_ROOT / "start-packaged.cmd"
    game_path = PROJECT_ROOT / "dist" / "ai-town" / "AI Town.exe"
    backend_main = PROJECT_ROOT / "backend" / "main.py"
    export_report = godot_export_tool_audit()
    launcher_text = ""
    if launcher_path.exists():
        try:
            launcher_text = launcher_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            launcher_text = ""
    checks = [
        {"id": "launcher", "label": "Packaged launcher exists", "ok": launcher_path.exists(), "detail": str(launcher_path)},
        {"id": "exported-game", "label": "Exported Windows game exists", "ok": game_path.exists() and game_path.stat().st_size > 100_000_000, "detail": str(game_path)},
        {"id": "backend-main", "label": "Backend entrypoint exists", "ok": backend_main.exists(), "detail": str(backend_main)},
        {"id": "health-wait", "label": "Launcher waits for backend health", "ok": "/api/health" in launcher_text and "Invoke-WebRequest" in launcher_text, "detail": "http://127.0.0.1:8000/api/health"},
        {"id": "no-taskkill", "label": "Packaged launcher does not kill processes", "ok": "taskkill" not in launcher_text.lower(), "detail": "start-packaged.cmd"},
        {"id": "export-report", "label": "Latest export report shows executable", "ok": export_report.get("status") == "exported" and bool(export_report.get("output_exists")), "detail": str(export_report.get("report_path", ""))},
    ]
    passed = len([item for item in checks if item["ok"]])
    return {
        "mode": "read-only-packaged-launch-readiness",
        "status": "ok" if passed == len(checks) else "needs-review",
        "checks": checks,
        "checks_passed": passed,
        "checks_total": len(checks),
        "launcher_path": str(launcher_path),
        "launcher_exists": launcher_path.exists(),
        "game_path": str(game_path),
        "game_exists": game_path.exists(),
        "game_bytes": game_path.stat().st_size if game_path.exists() else 0,
        "backend_url": "http://127.0.0.1:8000",
        "health_url": "http://127.0.0.1:8000/api/health",
        "export_status": export_report.get("status", "missing"),
        "export_report_path": export_report.get("report_path", ""),
        "safe_note": "Packaged launch readiness is read-only. The launcher starts only this project's backend when health is absent, waits for /api/health, then opens the exported game. This audit does not run the launcher, kill processes, change Git state, publish releases, or contact GitHub.",
    }


def release_package_manifest_audit() -> dict:
    manifest_path = PROJECT_ROOT / "workspace" / "release-package" / "release-manifest.json"
    if not manifest_path.exists():
        return {
            "mode": "read-only-release-package-manifest-audit",
            "status": "missing",
            "manifest_path": str(manifest_path),
            "safe_note": "Release package manifest audit reads project-local manifest evidence only. It does not run exports, start services, copy files, zip artifacts, change Git state, or publish anything.",
        }
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {
            "mode": "read-only-release-package-manifest-audit",
            "status": "parse-error",
            "manifest_path": str(manifest_path),
            "error": str(exc)[:300],
            "safe_note": "Release package manifest audit reads project-local manifest evidence only. Parse errors do not trigger export or packaging actions.",
        }
    dist_dir = (PROJECT_ROOT / "dist" / "ai-town").resolve()
    entries = manifest.get("files", [])
    if not isinstance(entries, list):
        entries = []
    audited = []
    missing = []
    hash_mismatches = []
    invalid_paths = []
    small_files = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        role = str(entry.get("role", "file"))
        path = Path(str(entry.get("path", ""))).resolve()
        allowed = path_is_inside(path, PROJECT_ROOT.resolve())
        exists = path.exists() and path.is_file() and allowed
        actual_bytes = path.stat().st_size if exists else 0
        expected_hash = str(entry.get("sha256", "")).lower()
        actual_hash = ""
        hash_ok = False
        if not allowed:
            invalid_paths.append({"role": role, "path": str(path)})
        elif not exists and entry.get("required", True):
            missing.append({"role": role, "path": str(path)})
        elif exists:
            if role == "exported-game-executable" and actual_bytes < 100_000_000:
                small_files.append({"role": role, "path": str(path), "bytes": actual_bytes})
            try:
                digest = hashlib.sha256()
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                actual_hash = digest.hexdigest()
                hash_ok = bool(expected_hash) and actual_hash == expected_hash
                if expected_hash and actual_hash != expected_hash:
                    hash_mismatches.append({"role": role, "path": str(path), "expected": expected_hash, "actual": actual_hash})
            except Exception as exc:
                hash_mismatches.append({"role": role, "path": str(path), "error": str(exc)[:200]})
        audited.append({
            "role": role,
            "path": str(path),
            "exists": exists,
            "path_ok": allowed,
            "bytes": actual_bytes,
            "expected_bytes": int(entry.get("bytes", 0) or 0),
            "sha256": actual_hash,
            "sha256_match": hash_ok,
        })
    exe = next((item for item in audited if item.get("role") == "exported-game-executable"), {})
    ok = (
        str(manifest.get("status", "")) == "ok"
        and bool(exe.get("exists"))
        and int(exe.get("bytes", 0)) > 100_000_000
        and not missing
        and not hash_mismatches
        and not invalid_paths
        and not small_files
    )
    return {
        "mode": "read-only-release-package-manifest-audit",
        "status": "ok" if ok else "needs-review",
        "manifest_path": str(manifest_path),
        "manifest_status": manifest.get("status", ""),
        "generated_at": manifest.get("generated_at", ""),
        "dist_dir": str(dist_dir),
        "file_count": len(audited),
        "missing_required_count": len(missing),
        "hash_mismatch_count": len(hash_mismatches),
        "invalid_path_count": len(invalid_paths),
        "small_file_count": len(small_files),
        "exe_exists": bool(exe.get("exists")),
        "exe_bytes": int(exe.get("bytes", 0) or 0),
        "exe_sha256": exe.get("sha256", ""),
        "files": audited,
        "missing_required": missing,
        "hash_mismatches": hash_mismatches,
        "invalid_paths": invalid_paths,
        "small_files": small_files,
        "safe_note": "Release package manifest audit verifies existing project-local release evidence and SHA-256 hashes only. It does not run exports, start services, open the game, copy files, zip artifacts, change Git state, or publish anything.",
    }


def testing_arena_overview() -> dict:
    scripts = verification_script_entries()
    drafts = markdown_draft_entries(TEST_PLAN_DRAFTS_DIR, "test-plan", 20)
    proofs = markdown_draft_entries(VERTICAL_SLICE_PROOFS_DIR, "vertical-slice-proof", 10)
    visual_manifest = visual_manifest_audit()
    return {
        "name": "Testing Arena",
        "mode": "read-only-plus-test-plan-drafts",
        "draft_dir": str(TEST_PLAN_DRAFTS_DIR),
        "proof_dir": str(VERTICAL_SLICE_PROOFS_DIR),
        "scripts": scripts,
        "script_count": len(scripts),
        "visual_artifact": visual_smoke_artifact(),
        "visual_manifest": visual_manifest,
        "recent_terminal_logs": latest_terminal_logs(8),
        "verification_log": plan_verification_entries(16),
        "drafts": drafts,
        "draft_count": len(drafts),
        "vertical_slice_proofs": proofs,
        "vertical_slice_proof_count": len(proofs),
        "jobs": job_queue_snapshot(),
        "safe_note": "Testing Arena shows verification scripts, visual evidence, room screenshot manifest integrity, logs, PLAN verification history, and vertical-slice proof reports. It creates local reports only; command execution stays in Terminal Control.",
    }


def create_test_plan_draft(req: TestPlanDraftRequest) -> dict:
    title = req.title.strip() or "AI Town test plan"
    body = req.body.strip() or "Describe the verification scenario to run before release."
    target = slugify_filename(req.target or "godot-backend-smoke")
    source = req.source_building.strip() or "testing-arena"
    TEST_PLAN_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    draft_path = TEST_PLAN_DRAFTS_DIR / f"{timestamp}-{target}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"target: {target}",
        f"source: ai-town/{source}",
        "status: draft",
        "safety: test-plan-draft-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Scenario",
        "",
        body,
        "",
        "## Suggested Checks",
        "",
        "- `python -m py_compile backend/main.py`",
        "- `tools\\godot\\Godot_v4.6.3-stable_win64.exe --headless --path godot --quit-after 2`",
        "- `powershell -ExecutionPolicy Bypass -File tools\\verify-smoke.ps1`",
        "- `powershell -ExecutionPolicy Bypass -File tools\\capture-visual-smoke.ps1`",
        "- `git diff --check`",
        "",
        "## Safety",
        "",
        "- This draft does not run tests.",
        "- Execute commands through Terminal Control or the developer shell with explicit intent.",
        "- Do not stop services or interrupt unrelated experiments while verifying.",
    ])
    draft_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Test plan draft created: {title}",
        f"Created project-local test plan `{title}` for `{target}`.\n\nDraft: `{draft_path}`",
        "ai-town/testing-arena",
    )
    return {
        "status": "saved",
        "draft_path": str(draft_path),
        "memory_event": memory,
        "preview": content,
        "safety": "test-plan-draft-only",
    }


def create_vertical_slice_proof(req: VerticalSliceProofRequest) -> dict:
    title = req.title.strip() or "AI Town vertical slice proof"
    source = req.source_building.strip() or "testing-arena"
    VERTICAL_SLICE_PROOFS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    report_path = VERTICAL_SLICE_PROOFS_DIR / f"{timestamp}-{slugify_filename(title)}.md"

    buildings = load_json_registry(BUILDING_REGISTRY_PATH)
    agents = load_json_registry(AGENT_REGISTRY_PATH)
    workspaces = load_workspace_registry()
    quests = load_quest_registry()
    districts = load_json_registry(DISTRICT_REGISTRY_PATH)
    room_scenes = load_json_registry(ROOM_SCENE_REGISTRY_PATH)
    map_decor = load_json_registry(MAP_DECOR_REGISTRY_PATH)
    file_index = file_vault_index_overview()
    projects = discover_git_repos(limit=12)
    agent_snapshot = agent_task_snapshot(20)
    tool_snapshot = agent_tool_invocation_snapshot(20)
    task_board = task_board_overview()
    model_status = model_gateway_status()
    permissions = permission_receipts(12)
    visual_manifest = visual_manifest_audit()
    visual_artifacts = []
    for name in [
        "visual-smoke.png",
        "map-plaza.png",
        "room-file-vault.png",
        "room-research-hall.png",
        "room-code-workshop.png",
        "room-agent-hub.png",
        "room-testing-arena.png",
        "room-terminal-control.png",
        "room-permission-hall.png",
        "room-model-market.png",
    ]:
        path = PROJECT_ROOT / "screenshots" / name
        visual_artifacts.append({
            "name": name,
            "exists": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
            "path": str(path),
        })

    checks = [
        ("Godot map/buildings", len(buildings) >= 20, f"{len(buildings)} buildings in registry"),
        ("Agents/NPC roster", len(agents) >= 5, f"{len(agents)} agents in registry"),
        ("Workspace roots", len(workspaces) >= 3, f"{len(workspaces)} workspace roots"),
        ("Quest loop", len(quests) >= 5, f"{len(quests)} quests"),
        ("District navigation", len(districts) >= 3, f"{len(districts)} districts"),
        ("Room scenes", len(room_scenes) >= 5, f"{len(room_scenes)} room scenes"),
        ("Plaza landmarks", len(map_decor) >= 5, f"{len(map_decor)} landmarks"),
        ("File Vault index", bool(file_index.get("exists") or file_index.get("status") in {"ready", "missing"}), str(file_index.get("status", "unknown"))),
        ("Project browser", len(projects) >= 1, f"{len(projects)} local git repos sampled"),
        ("Agent task queue", "tasks" in agent_snapshot, f"{len(agent_snapshot.get('tasks', []))} tasks sampled"),
        ("Agent tool queue", "recent" in tool_snapshot, f"{len(tool_snapshot.get('recent', []))} invocations sampled"),
        ("Task board", task_board.get("local_task_count", 0) >= 1, f"{task_board.get('local_task_count', 0)} local tasks"),
        ("Model gateway", model_status.get("count", 0) >= 1, f"{model_status.get('count', 0)} model profiles"),
        ("Permission receipts", permissions.get("count", 0) >= 1, f"{permissions.get('count', 0)} receipts"),
        ("Visual evidence", any(item["exists"] and item["bytes"] > 10000 for item in visual_artifacts), "at least one non-empty screenshot"),
        ("All-room visual manifest", bool(visual_manifest.get("coverage_ok")), f"{visual_manifest.get('valid_screenshot_count', 0)} / {visual_manifest.get('registry_room_count', 0)} room screenshots verified"),
    ]
    passed = [item for item in checks if item[1]]
    missing = [item for item in checks if not item[1]]

    content = "\n".join([
        "---",
        f"title: {title}",
        f"source: ai-town/{source}",
        "status: recorded",
        "safety: vertical-slice-proof-report-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Summary",
        "",
        f"- checks_passed: {len(passed)} / {len(checks)}",
        f"- checks_missing: {len(missing)}",
        f"- generated_at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Capability Checks",
        "",
        *[f"- [{'x' if ok else ' '}] {name}: {detail}" for name, ok, detail in checks],
        "",
        "## Visual Evidence",
        "",
        *[f"- {item['name']}: exists={item['exists']} bytes={item['bytes']} path=`{item['path']}`" for item in visual_artifacts],
        "",
        "## All-Room Visual Manifest",
        "",
        f"- status: {visual_manifest.get('status', '')}",
        f"- coverage_ok: {visual_manifest.get('coverage_ok', False)}",
        f"- screenshots: {visual_manifest.get('valid_screenshot_count', 0)} / {visual_manifest.get('registry_room_count', 0)}",
        f"- manifest: `{visual_manifest.get('manifest_path', '')}`",
        "",
        "## Real Workflow Evidence",
        "",
        f"- File Vault: status={file_index.get('status', 'unknown')} cache=`{file_index.get('cache_path', '')}`",
        f"- Project Browser: sampled repos={len(projects)}",
        f"- Task Board: local tasks={task_board.get('local_task_count', 0)} status_counts={task_board.get('status_counts', {})}",
        f"- Agent Task Queue: sampled tasks={len(agent_snapshot.get('tasks', []))}",
        f"- Agent Tool Queue: sampled invocations={len(tool_snapshot.get('recent', []))}",
        f"- Model Gateway: profiles={model_status.get('count', 0)} configured={model_status.get('configured_count', 0)} active={model_status.get('active_dialogue_provider', '')}",
        f"- Permission Receipts: count={permissions.get('count', 0)} classes={permissions.get('counts', {})}",
        "",
        "## Safety",
        "",
        "- This report is generated from bounded local metadata and existing evidence only.",
        "- It does not run commands, invoke agents, rescan large roots, edit external repositories, stage Git, commit, push, or contact GitHub.",
        "- Missing checks are follow-up signals, not permission to bypass safety gates.",
    ])
    report_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Vertical slice proof recorded: {title}",
        f"Recorded vertical slice proof report at `{report_path}` with {len(passed)} / {len(checks)} checks passing.",
        "ai-town/testing-arena",
    )
    return {
        "status": "saved",
        "safety": "vertical-slice-proof-report-only",
        "report_path": str(report_path),
        "memory_event": memory,
        "checks_passed": len(passed),
        "checks_total": len(checks),
        "missing": [{"name": name, "detail": detail} for name, _ok, detail in missing],
        "visual_artifacts": visual_artifacts,
        "visual_manifest": visual_manifest,
        "preview": content,
    }


def vertical_slice_proof_detail(proof_id: str) -> Optional[dict]:
    proof_id = slugify_filename(proof_id)
    if not proof_id:
        return None
    for entry in markdown_draft_entries(VERTICAL_SLICE_PROOFS_DIR, "vertical-slice-proof", 200):
        if entry.get("id") != proof_id:
            continue
        path = Path(str(entry.get("path", ""))).resolve()
        if not path_is_inside(path, VERTICAL_SLICE_PROOFS_DIR):
            return None
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            text = ""
        return {
            "status": "ok",
            "proof_id": proof_id,
            "proof": entry,
            "preview": text[:7000],
            "preview_chars": min(len(text), 7000),
            "truncated": len(text) > 7000,
            "safety": "bounded-vertical-slice-proof-preview",
        }
    return None


def recent_diagnostic_events(limit: int = 12) -> list[dict]:
    events = []
    for item in markdown_draft_entries(MEMORY_EVENTS_DIR, "memory-event", 40):
        title = str(item.get("title", ""))
        haystack = f"{title} {item.get('path', '')}".lower()
        if any(term in haystack for term in ["failed", "failure", "error", "blocked", "bug", "test", "smoke", "verification"]):
            events.append(item)
    return events[:limit]


def bug_clinic_overview() -> dict:
    jobs = job_queue_snapshot()
    failed_jobs = [
        job for job in jobs.get("recent", [])
        if str(job.get("status", "")).lower() in {"failed", "missing", "blocked"}
    ]
    terminal_logs = latest_terminal_logs(12)
    failed_terminal_logs = [
        log for log in terminal_logs
        if str(log.get("status", "")).lower() == "failed" or log.get("returncode") not in {None, 0}
    ]
    diagnostics = [
        {
            "id": "claude-review-connector",
            "title": "Claude review connector unavailable",
            "status": "known-issue",
            "detail": "Earlier review attempt failed because local claude.exe was not recognized by the review connector.",
            "source": "PLAN.md / MEMORY.md",
        }
    ]
    if not failed_jobs and not failed_terminal_logs:
        diagnostics.append({
            "id": "current-smoke-state",
            "title": "No failed backend jobs or terminal logs currently detected",
            "status": "clear",
            "detail": "Use Testing Arena and Terminal Control for fresh verification evidence.",
            "source": "runtime snapshot",
        })
    return {
        "name": "Bug Clinic",
        "mode": "read-only-plus-bug-report-drafts",
        "draft_dir": str(BUG_REPORTS_DIR),
        "failed_jobs": failed_jobs,
        "failed_job_count": len(failed_jobs),
        "failed_terminal_logs": failed_terminal_logs,
        "failed_terminal_log_count": len(failed_terminal_logs),
        "diagnostics": diagnostics,
        "diagnostic_events": recent_diagnostic_events(12),
        "bug_reports": markdown_draft_entries(BUG_REPORTS_DIR, "bug-report", 20),
        "bug_report_count": len(markdown_draft_entries(BUG_REPORTS_DIR, "bug-report", 20)),
        "testing_arena": {
            "visual_artifact": visual_smoke_artifact(),
            "verification_log_count": len(plan_verification_entries(40)),
        },
        "safe_note": "Bug Clinic triages diagnostics and writes bug-report drafts only. It does not edit code, run fixes, stop services, or revert files.",
    }


def create_bug_report_draft(req: BugReportDraftRequest) -> dict:
    title = req.title.strip() or "AI Town bug report"
    body = req.body.strip() or "Describe the observed issue, expected behavior, and diagnostic evidence."
    severity = req.severity.strip().lower()
    if severity not in {"low", "medium", "high", "critical"}:
        severity = "medium"
    source = req.source_building.strip() or "bug-clinic"
    BUG_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    draft_path = BUG_REPORTS_DIR / f"{timestamp}-{severity}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"severity: {severity}",
        f"source: ai-town/{source}",
        "status: draft",
        "safety: bug-report-draft-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Observed",
        "",
        body,
        "",
        "## Expected",
        "",
        "- Describe the intended behavior before assigning a fix.",
        "",
        "## Evidence To Attach",
        "",
        "- Relevant room or endpoint.",
        "- Any terminal log under `workspace/terminal-logs`.",
        "- Any screenshot or visual smoke artifact.",
        "- Reproduction steps.",
        "",
        "## Safety",
        "",
        "- This is a bug-report draft only.",
        "- No code was edited, no commands were run, and no service was stopped.",
    ])
    draft_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Bug report draft created: {title}",
        f"Created project-local bug report `{title}` with severity `{severity}`.\n\nDraft: `{draft_path}`",
        "ai-town/bug-clinic",
    )
    return {
        "status": "saved",
        "draft_path": str(draft_path),
        "memory_event": memory,
        "preview": content,
        "severity": severity,
        "safety": "bug-report-draft-only",
    }


def project_management_overview() -> dict:
    projects = discover_git_repos(10)
    task_board = task_board_overview()
    research_cards = all_research_project_cards()
    harbor = github_harbor_index()
    briefs = markdown_draft_entries(PROJECT_BRIEFS_DIR, "project-brief", 20)
    active_projects = []
    for project in projects[:10]:
        active_projects.append({
            "id": project.get("id", ""),
            "name": project.get("name", ""),
            "family": project.get("family", ""),
            "path": project.get("path", ""),
            "branch": project.get("branch", ""),
            "has_readme": project.get("has_readme", False),
            "dirty_count": project.get("dirty_count", -1),
        })
    return {
        "name": "Project Management Hall",
        "mode": "read-only-plus-project-brief-drafts",
        "draft_dir": str(PROJECT_BRIEFS_DIR),
        "projects": active_projects,
        "project_count": len(projects),
        "research_projects": research_cards[:10],
        "research_project_count": len(research_cards),
        "task_status_counts": task_board.get("status_counts", {}),
        "local_task_count": task_board.get("local_task_count", 0),
        "dispatch_draft_count": task_board.get("dispatch_draft_count", 0),
        "harbor_repo_count": harbor.get("count", 0),
        "briefs": briefs,
        "brief_count": len(briefs),
        "safe_note": "Project Management Hall aggregates project, research, task, and Git metadata. It writes brief drafts only and does not modify repositories, experiments, or external trackers.",
    }


def create_project_brief_draft(req: ProjectBriefDraftRequest) -> dict:
    title = req.title.strip() or "AI Town project brief"
    body = req.body.strip() or "Summarize the current project status, risks, and next actions."
    project_id = slugify_filename(req.project_id or "ai-town")
    source = req.source_building.strip() or "project-management-hall"
    PROJECT_BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    draft_path = PROJECT_BRIEFS_DIR / f"{timestamp}-{project_id}-{slugify_filename(title)}.md"
    overview = project_management_overview()
    content = "\n".join([
        "---",
        f"title: {title}",
        f"project_id: {project_id}",
        f"source: ai-town/{source}",
        "status: draft",
        "safety: project-brief-draft-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Summary",
        "",
        body,
        "",
        "## Portfolio Snapshot",
        "",
        f"- Local Git projects sampled: {overview.get('project_count', 0)}",
        f"- Research projects: {overview.get('research_project_count', 0)}",
        f"- Local tasks: {overview.get('local_task_count', 0)}",
        f"- Dispatch drafts: {overview.get('dispatch_draft_count', 0)}",
        f"- Harbor repos: {overview.get('harbor_repo_count', 0)}",
        "",
        "## Next Actions",
        "",
        "- Review project status and decide whether to create tasks, research notes, or code briefs.",
        "- Do not run experiments, commands, or Git writes from this draft.",
    ])
    draft_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Project brief draft created: {title}",
        f"Created project-local project brief `{title}` for `{project_id}`.\n\nDraft: `{draft_path}`",
        "ai-town/project-management-hall",
    )
    return {
        "status": "saved",
        "draft_path": str(draft_path),
        "memory_event": memory,
        "preview": content,
        "safety": "project-brief-draft-only",
    }


def download_kind_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}:
        return "image-asset"
    if suffix in {".zip", ".7z", ".rar", ".tar", ".gz"}:
        return "archive"
    if suffix in {".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".csv"}:
        return "document"
    if suffix in {".exe", ".msi", ".bat", ".cmd", ".ps1", ".sh"}:
        return "executable-or-script"
    if suffix in {".md", ".txt", ".json", ".yaml", ".yml", ".toml"}:
        return "text"
    return "other"


def download_root_entry(root_id: str) -> Optional[dict]:
    return next((root for root in DOWNLOAD_STATION_ROOTS if root["id"] == root_id), None)


def download_risk_for(path: Path, kind: str, size: int) -> list[str]:
    risks = []
    suffix = path.suffix.lower()
    if kind == "executable-or-script":
        risks.append("manual-review-before-run")
    if kind == "archive":
        risks.append("extract-only-in-sandbox-or-staging")
    if size > 200 * 1024 * 1024:
        risks.append("large-file")
    if suffix in {".torrent", ".crdownload", ".part", ".tmp"}:
        risks.append("incomplete-or-transient-download")
    if not risks:
        risks.append("normal-intake-review")
    return risks


def download_triage_snapshot(root_id: str = "user-downloads", limit: int = 18) -> dict:
    root = download_root_entry(root_id) or download_root_entry("user-downloads") or DOWNLOAD_STATION_ROOTS[0]
    root_path = Path(root["path"])
    max_items = max(1, min(limit, 40))
    items = []
    type_counts: dict[str, int] = {}
    risk_counts: dict[str, int] = {}
    if not root_path.exists() or not root_path.is_dir():
        return {
            "status": "missing",
            "mode": "read-only-download-triage",
            "root": {"id": root["id"], "name": root["name"], "path": str(root_path), "exists": root_path.exists()},
            "items": [],
            "item_count": 0,
            "type_counts": {},
            "risk_counts": {},
            "safe_note": "Download triage is read-only. No files were moved, opened, deleted, fetched, installed, extracted, or executed.",
        }
    try:
        children = [child for child in root_path.iterdir() if child.is_file() and not child.is_symlink()]
        children.sort(key=lambda child: child.stat().st_mtime, reverse=True)
    except Exception as exc:
        return {
            "status": "error",
            "mode": "read-only-download-triage",
            "root": {"id": root["id"], "name": root["name"], "path": str(root_path), "exists": True},
            "items": [],
            "item_count": 0,
            "type_counts": {},
            "risk_counts": {},
            "error": str(exc)[:1200],
            "safe_note": "Download triage failed during read-only listing. No file mutation was attempted.",
        }
    for child in children[:max_items]:
        try:
            stat = child.stat()
            kind = download_kind_for(child)
            risks = download_risk_for(child, kind, stat.st_size)
            digest = ""
            hash_status = "skipped-large"
            if stat.st_size <= 1024 * 1024:
                sha = hashlib.sha256()
                with child.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(65536), b""):
                        sha.update(chunk)
                digest = sha.hexdigest()
                hash_status = "ok"
            for risk in risks:
                risk_counts[risk] = risk_counts.get(risk, 0) + 1
            type_counts[kind] = type_counts.get(kind, 0) + 1
            items.append({
                "name": child.name,
                "path": str(child),
                "relative_path": child.name,
                "bytes": stat.st_size,
                "updated": stat.st_mtime,
                "extension": child.suffix.lower(),
                "kind": kind,
                "risks": risks,
                "sha256": digest,
                "hash_status": hash_status,
                "suggested_route": {
                    "image-asset": "asset-gallery-intake",
                    "document": "paper-reading-or-docs-review",
                    "archive": "quarantine-or-staging-review",
                    "executable-or-script": "manual-security-review",
                    "text": "file-vault-or-knowledge-index",
                }.get(kind, "manual-review"),
            })
        except Exception as exc:
            items.append({
                "name": child.name,
                "path": str(child),
                "kind": "unreadable",
                "risks": ["read-error"],
                "error": str(exc)[:300],
            })
            risk_counts["read-error"] = risk_counts.get("read-error", 0) + 1
    return {
        "status": "ok",
        "mode": "read-only-download-triage",
        "root": {"id": root["id"], "name": root["name"], "path": str(root_path), "exists": True},
        "items": items,
        "item_count": len(items),
        "sample_limit": max_items,
        "type_counts": type_counts,
        "risk_counts": risk_counts,
        "intake_routes": [
            "Assets should be reviewed in Asset Resource Gallery before promotion.",
            "Documents and PDFs should go through Paper Reading Room or Knowledge Tower.",
            "Archives and executables require manual review before extraction or execution.",
            "Useful text/config files can be routed into File Vault tags or Knowledge Tower indexing.",
        ],
        "safe_note": "Download triage reads bounded metadata and hashes only small recent files. It does not move, open, delete, fetch, install, extract, execute, upload, or quarantine files.",
    }


def download_root_statuses(limit: int = 24) -> list[dict]:
    roots = []
    for root in DOWNLOAD_STATION_ROOTS:
        path = Path(root["path"])
        entry = {
            "id": root["id"],
            "name": root["name"],
            "path": str(path),
            "exists": path.exists(),
            "kind": "dir" if path.is_dir() else "file" if path.is_file() else "missing",
            "sample": [],
            "sample_count": 0,
        }
        if path.exists() and path.is_dir():
            try:
                children = [child for child in path.iterdir() if child.is_file()]
                children.sort(key=lambda child: child.stat().st_mtime, reverse=True)
                sample = []
                for child in children[:limit]:
                    stat = child.stat()
                    sample.append({
                        "name": child.name,
                        "path": str(child),
                        "relative_path": child.name,
                        "bytes": stat.st_size,
                        "updated": stat.st_mtime,
                        "extension": child.suffix.lower(),
                        "kind": download_kind_for(child),
                    })
                entry["sample"] = sample
                entry["sample_count"] = len(children)
            except Exception as exc:
                entry["error"] = str(exc)
        roots.append(entry)
    return roots


def download_station_overview() -> dict:
    roots = download_root_statuses()
    drafts = markdown_draft_entries(DOWNLOAD_INTAKE_DIR, "download-intake", 20)
    triage = download_triage_snapshot("user-downloads", 8)
    type_counts: dict[str, int] = {}
    latest_files = []
    for root in roots:
        for item in root.get("sample", []):
            kind = item.get("kind", "other")
            type_counts[kind] = type_counts.get(kind, 0) + 1
            enriched = dict(item)
            enriched["root_id"] = root.get("id", "")
            enriched["root_name"] = root.get("name", "")
            latest_files.append(enriched)
    latest_files.sort(key=lambda item: item.get("updated", 0), reverse=True)
    return {
        "name": "Download Station",
        "mode": "read-only-download-triage-plus-intake-drafts",
        "draft_dir": str(DOWNLOAD_INTAKE_DIR),
        "roots": roots,
        "root_count": len(roots),
        "triage": triage,
        "triage_item_count": triage.get("item_count", 0),
        "latest_files": latest_files[:30],
        "latest_file_count": len(latest_files),
        "type_counts": type_counts,
        "drafts": drafts,
        "draft_count": len(drafts),
        "safe_note": "Download Station performs shallow allowlisted inspection and bounded triage only. It writes intake drafts under workspace/download-intake and does not move, open, delete, execute, install, extract, upload, or fetch files.",
    }


def create_download_intake_draft(req: DownloadIntakeDraftRequest) -> dict:
    title = req.title.strip() or "AI Town download intake"
    body = req.body.strip() or "Review recent downloads and decide what should become assets, docs, dependencies, or archive items."
    source = req.source_building.strip() or "download-station"
    root_id = req.root_id.strip() or "user-downloads"
    root = download_root_entry(root_id) or download_root_entry("user-downloads") or DOWNLOAD_STATION_ROOTS[0]
    overview = download_station_overview()
    root_snapshot = next((item for item in overview["roots"] if item.get("id") == root["id"]), {})
    DOWNLOAD_INTAKE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    draft_path = DOWNLOAD_INTAKE_DIR / f"{timestamp}-{slugify_filename(root['id'])}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"source: ai-town/{source}",
        f"root_id: {root['id']}",
        "status: draft",
        "safety: download-intake-draft-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Scope",
        "",
        f"- Root: {root['name']} (`{root['path']}`)",
        f"- Exists: {root_snapshot.get('exists', False)}",
        f"- Sampled files: {root_snapshot.get('sample_count', 0)}",
        "",
        "## Intake Notes",
        "",
        body,
        "",
        "## Recent Files",
        "",
    ])
    recent = root_snapshot.get("sample", []) if isinstance(root_snapshot, dict) else []
    if recent:
        content += "\n".join([
            f"- `{item.get('name', '')}` | {item.get('kind', 'other')} | {item.get('bytes', 0)} bytes"
            for item in recent[:12]
        ])
    else:
        content += "- No files sampled from this root."
    content += "\n\n## Safety\n\n- This draft does not move, delete, execute, install, download, or open any file.\n- Review manually before routing files into project assets, docs, dependencies, or archives."
    draft_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Download intake draft created: {title}",
        f"Created project-local download intake draft `{title}` for `{root['id']}`.\n\nDraft: `{draft_path}`",
        "ai-town/download-station",
    )
    return {
        "status": "saved",
        "draft_path": str(draft_path),
        "memory_event": memory,
        "preview": content,
        "root": {"id": root["id"], "name": root["name"], "path": str(root["path"])},
        "safety": "download-intake-draft-only",
    }


def asset_kind_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}:
        return "raster-image"
    if suffix in {".svg"}:
        return "vector-image"
    if suffix in {".ase", ".aseprite", ".psd", ".kra", ".blend"}:
        return "source-art"
    if suffix in {".import", ".tres", ".res", ".tscn"}:
        return "godot-resource"
    if suffix in {".md", ".txt"}:
        return "art-direction-note"
    if suffix in {".json", ".yaml", ".yml", ".toml"}:
        return "manifest-or-config"
    return "other"


def asset_root_entry(root_id: str) -> Optional[dict]:
    return next((root for root in ASSET_GALLERY_ROOTS if root["id"] == root_id), None)


def resolve_asset_candidate(root_id: str, relative_path: str) -> Optional[dict]:
    root = asset_root_entry(root_id)
    if not root:
        return None
    root_path = Path(root["path"]).resolve()
    target = (root_path / relative_path).resolve()
    if not path_is_inside(target, root_path) or not target.exists() or not target.is_file():
        return None
    kind = asset_kind_for(target)
    if kind == "other":
        return None
    try:
        stat = target.stat()
    except Exception:
        return None
    return {
        "root_id": root["id"],
        "root_name": root["name"],
        "root_path": str(root_path),
        "name": target.name,
        "path": str(target),
        "relative_path": relative_path,
        "bytes": stat.st_size,
        "updated": stat.st_mtime,
        "extension": target.suffix.lower(),
        "kind": kind,
    }


def first_asset_candidate(kind_prefix: str = "") -> Optional[dict]:
    for root in asset_root_statuses():
        for item in root.get("sample", []):
            kind = str(item.get("kind", ""))
            if kind == "folder":
                continue
            if kind_prefix and not kind.startswith(kind_prefix):
                continue
            candidate = resolve_asset_candidate(str(root.get("id", "")), str(item.get("relative_path", "")))
            if candidate:
                return candidate
    return None


def image_dimensions_from_bytes(path: Path) -> dict:
    suffix = path.suffix.lower()
    try:
        with path.open("rb") as handle:
            header = handle.read(64)
            if suffix == ".png" and header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
                return {"width": int.from_bytes(header[16:20], "big"), "height": int.from_bytes(header[20:24], "big"), "format": "png"}
            if suffix == ".gif" and header[:6] in {b"GIF87a", b"GIF89a"} and len(header) >= 10:
                return {"width": int.from_bytes(header[6:8], "little"), "height": int.from_bytes(header[8:10], "little"), "format": "gif"}
            if suffix in {".jpg", ".jpeg"} and header.startswith(b"\xff\xd8"):
                handle.seek(2)
                while True:
                    marker_start = handle.read(1)
                    if not marker_start:
                        break
                    if marker_start != b"\xff":
                        continue
                    marker = handle.read(1)
                    while marker == b"\xff":
                        marker = handle.read(1)
                    if marker in {b"\xc0", b"\xc1", b"\xc2", b"\xc3", b"\xc5", b"\xc6", b"\xc7", b"\xc9", b"\xca", b"\xcb", b"\xcd", b"\xce", b"\xcf"}:
                        _length = int.from_bytes(handle.read(2), "big")
                        _precision = handle.read(1)
                        height = int.from_bytes(handle.read(2), "big")
                        width = int.from_bytes(handle.read(2), "big")
                        return {"width": width, "height": height, "format": "jpeg"}
                    if marker in {b"\xd8", b"\xd9"}:
                        continue
                    length_bytes = handle.read(2)
                    if len(length_bytes) != 2:
                        break
                    length = int.from_bytes(length_bytes, "big")
                    handle.seek(max(length - 2, 0), 1)
            if suffix == ".webp" and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
                if header[12:16] == b"VP8X" and len(header) >= 30:
                    width = 1 + int.from_bytes(header[24:27], "little")
                    height = 1 + int.from_bytes(header[27:30], "little")
                    return {"width": width, "height": height, "format": "webp"}
                if header[12:16] == b"VP8 " and len(header) >= 30:
                    width = int.from_bytes(header[26:28], "little") & 0x3FFF
                    height = int.from_bytes(header[28:30], "little") & 0x3FFF
                    return {"width": width, "height": height, "format": "webp"}
    except Exception as exc:
        return {"width": 0, "height": 0, "format": "", "error": str(exc)[:300]}
    return {"width": 0, "height": 0, "format": ""}


def inspect_asset(root_id: str = "", relative_path: str = "") -> dict:
    candidate = resolve_asset_candidate(root_id, relative_path) if root_id and relative_path else None
    if not candidate:
        candidate = first_asset_candidate("raster-image") or first_asset_candidate()
    if not candidate:
        return {
            "status": "not-available",
            "mode": "read-only-asset-inspection",
            "safety": "asset-inspection-read-only",
            "message": "No allowlisted asset candidate was found.",
            "safe_note": "Asset inspection is read-only and no asset file was edited, moved, copied, imported, optimized, generated, or deleted.",
        }
    path = Path(candidate["path"])
    digest = ""
    hash_status = "skipped-large"
    if candidate.get("bytes", 0) <= 10 * 1024 * 1024:
        try:
            sha = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(65536), b""):
                    sha.update(chunk)
            digest = sha.hexdigest()
            hash_status = "ok"
        except Exception as exc:
            hash_status = f"error: {exc}"[:300]
    dimensions = image_dimensions_from_bytes(path) if candidate.get("kind") == "raster-image" else {"width": 0, "height": 0, "format": ""}
    return {
        "status": "ok",
        "mode": "read-only-asset-inspection",
        "safety": "asset-inspection-read-only",
        "asset": candidate,
        "sha256": digest,
        "hash_status": hash_status,
        "image": dimensions,
        "curation_checks": [
            "Source/origin is known and suitable for open-source release.",
            "Visual style matches the warm storybook / pixel-handpainted baseline.",
            "Runtime asset is intentionally located under Godot assets or documented as source/reference art.",
            "No copied game assets, marketplace packs, or untracked stock art are promoted without review.",
        ],
        "safe_note": "Asset inspection reads bounded metadata, hashes small files, and parses lightweight image headers only. It does not edit, move, delete, copy, import, optimize, generate, publish, or open assets.",
    }


def bounded_asset_entries(path: Path, limit: int = 36, max_depth: int = 3) -> list[dict]:
    if not path.exists():
        return []
    if path.is_file():
        try:
            stat = path.stat()
            return [{
                "name": path.name,
                "path": str(path),
                "relative_path": path.name,
                "bytes": stat.st_size,
                "updated": stat.st_mtime,
                "extension": path.suffix.lower(),
                "kind": asset_kind_for(path),
                "depth": 0,
            }]
        except Exception:
            return []
    entries: list[dict] = []
    queue: list[tuple[Path, int]] = [(path, 0)]
    ignored = {".git", ".godot", "node_modules", "__pycache__", ".venv", "venv"}
    while queue and len(entries) < limit:
        current, depth = queue.pop(0)
        try:
            children = sorted(current.iterdir(), key=lambda child: (not child.is_dir(), child.name.lower()))
        except Exception:
            continue
        for child in children:
            if len(entries) >= limit:
                break
            if child.name in ignored:
                continue
            try:
                stat = child.stat()
            except Exception:
                continue
            if child.is_dir():
                if depth < max_depth:
                    queue.append((child, depth + 1))
                entries.append({
                    "name": child.name,
                    "path": str(child),
                    "relative_path": str(child.relative_to(path)),
                    "bytes": 0,
                    "updated": stat.st_mtime,
                    "extension": "",
                    "kind": "folder",
                    "depth": depth + 1,
                })
            elif asset_kind_for(child) != "other":
                entries.append({
                    "name": child.name,
                    "path": str(child),
                    "relative_path": str(child.relative_to(path)),
                    "bytes": stat.st_size,
                    "updated": stat.st_mtime,
                    "extension": child.suffix.lower(),
                    "kind": asset_kind_for(child),
                    "depth": depth,
                })
    entries.sort(key=lambda item: (item.get("kind") == "folder", -item.get("updated", 0)))
    return entries[:limit]


def asset_root_statuses(limit: int = 36) -> list[dict]:
    roots = []
    for root in ASSET_GALLERY_ROOTS:
        path = Path(root["path"])
        entries = bounded_asset_entries(path, limit)
        kind_counts: dict[str, int] = {}
        for item in entries:
            kind = item.get("kind", "other")
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
        roots.append({
            "id": root["id"],
            "name": root["name"],
            "path": str(path),
            "role": root.get("role", ""),
            "exists": path.exists(),
            "kind": "dir" if path.is_dir() else "file" if path.is_file() else "missing",
            "sample": entries,
            "sample_count": len(entries),
            "kind_counts": kind_counts,
        })
    return roots


def asset_gallery_overview() -> dict:
    roots = asset_root_statuses()
    notes = markdown_draft_entries(ASSET_NOTES_DIR, "asset-note", 20)
    inspection = inspect_asset()
    all_assets = []
    kind_counts: dict[str, int] = {}
    for root in roots:
        for item in root.get("sample", []):
            kind = item.get("kind", "other")
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
            enriched = dict(item)
            enriched["root_id"] = root.get("id", "")
            enriched["root_name"] = root.get("name", "")
            all_assets.append(enriched)
    all_assets.sort(key=lambda item: item.get("updated", 0), reverse=True)
    return {
        "name": "Asset Resource Gallery",
        "mode": "read-only-asset-curation-plus-notes",
        "note_dir": str(ASSET_NOTES_DIR),
        "roots": roots,
        "root_count": len(roots),
        "assets": all_assets[:40],
        "asset_count": len(all_assets),
        "inspection": inspection,
        "inspection_status": inspection.get("status", "not-available"),
        "kind_counts": kind_counts,
        "notes": notes,
        "note_count": len(notes),
        "style_contracts": [
            "Use the warm storybook / pixel-handpainted baseline from docs/VISUAL_BASELINE.md.",
            "Keep generated or source assets traceable before they enter Godot runtime folders.",
            "Do not import copied game assets, marketplace packs, or untracked stock art.",
            "Record curation notes before promoting rough downloads into production assets.",
        ],
        "safe_note": "Asset Resource Gallery performs bounded allowlisted inventory and read-only asset inspection. It writes curation notes under workspace/asset-notes and does not edit, move, delete, copy, import, optimize, or generate assets.",
    }


def create_asset_note(req: AssetNoteRequest) -> dict:
    title = req.title.strip() or "AI Town asset curation note"
    body = req.body.strip() or "Describe the asset set, style fit, source status, and next step."
    source = req.source_building.strip() or "asset-gallery"
    root_id = req.root_id.strip() or "godot-assets"
    root = asset_root_entry(root_id) or asset_root_entry("godot-assets") or ASSET_GALLERY_ROOTS[0]
    overview = asset_gallery_overview()
    root_snapshot = next((item for item in overview["roots"] if item.get("id") == root["id"]), {})
    ASSET_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    note_path = ASSET_NOTES_DIR / f"{timestamp}-{slugify_filename(root['id'])}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"source: ai-town/{source}",
        f"root_id: {root['id']}",
        "status: draft",
        "safety: asset-curation-note-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Asset Scope",
        "",
        f"- Root: {root['name']} (`{root['path']}`)",
        f"- Role: {root.get('role', '')}",
        f"- Exists: {root_snapshot.get('exists', False)}",
        f"- Sampled entries: {root_snapshot.get('sample_count', 0)}",
        f"- Kind counts: {json.dumps(root_snapshot.get('kind_counts', {}), ensure_ascii=False)}",
        "",
        "## Curation Notes",
        "",
        body,
        "",
        "## Sampled Assets",
        "",
    ])
    sample = root_snapshot.get("sample", []) if isinstance(root_snapshot, dict) else []
    if sample:
        content += "\n".join([
            f"- `{item.get('relative_path', item.get('name', ''))}` | {item.get('kind', 'other')} | {item.get('bytes', 0)} bytes"
            for item in sample[:14]
        ])
    else:
        content += "- No matching assets sampled from this root."
    content += "\n\n## Safety\n\n- This note did not edit, move, delete, copy, import, optimize, generate, or publish any asset.\n- Promote assets only after source, license/origin, visual fit, and Godot import status are reviewed."
    note_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Asset curation note created: {title}",
        f"Created project-local asset curation note `{title}` for `{root['id']}`.\n\nNote: `{note_path}`",
        "ai-town/asset-gallery",
    )
    return {
        "status": "saved",
        "draft_path": str(note_path),
        "memory_event": memory,
        "preview": content,
        "root": {"id": root["id"], "name": root["name"], "path": str(root["path"])},
        "safety": "asset-curation-note-only",
    }


def office_kind_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if path.is_dir():
        return "folder"
    if suffix in {".md", ".txt", ".rtf"}:
        return "note"
    if suffix in {".doc", ".docx", ".odt"}:
        return "document"
    if suffix in {".ppt", ".pptx"}:
        return "slides"
    if suffix in {".xls", ".xlsx", ".csv"}:
        return "spreadsheet"
    if suffix in {".pdf"}:
        return "pdf"
    if suffix in {".json", ".yaml", ".yml", ".toml"}:
        return "structured-data"
    return "other"


def office_root_entry(root_id: str) -> Optional[dict]:
    return next((root for root in OFFICE_CENTER_ROOTS if root["id"] == root_id), None)


def bounded_office_entries(path: Path, limit: int = 32) -> list[dict]:
    if not path.exists():
        return []
    if path.is_file():
        try:
            stat = path.stat()
            return [{
                "name": path.name,
                "path": str(path),
                "relative_path": path.name,
                "kind": office_kind_for(path),
                "bytes": stat.st_size,
                "updated": stat.st_mtime,
            }]
        except Exception:
            return []
    entries = []
    ignored = {".git", ".godot", "node_modules", "__pycache__", ".venv", "venv"}
    try:
        children = sorted(path.iterdir(), key=lambda child: child.stat().st_mtime if child.exists() else 0, reverse=True)
    except Exception:
        return entries
    for child in children:
        if len(entries) >= limit:
            break
        if child.name in ignored:
            continue
        try:
            stat = child.stat()
        except Exception:
            continue
        kind = office_kind_for(child)
        if kind == "other":
            continue
        entries.append({
            "name": child.name,
            "path": str(child),
            "relative_path": child.name,
            "kind": kind,
            "bytes": 0 if child.is_dir() else stat.st_size,
            "updated": stat.st_mtime,
        })
    return entries


def office_root_statuses(limit: int = 32) -> list[dict]:
    roots = []
    for root in OFFICE_CENTER_ROOTS:
        path = Path(root["path"])
        sample = bounded_office_entries(path, limit)
        kind_counts: dict[str, int] = {}
        for item in sample:
            kind = item.get("kind", "other")
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
        roots.append({
            "id": root["id"],
            "name": root["name"],
            "path": str(path),
            "role": root.get("role", ""),
            "exists": path.exists(),
            "kind": "dir" if path.is_dir() else "file" if path.is_file() else "missing",
            "sample": sample,
            "sample_count": len(sample),
            "kind_counts": kind_counts,
        })
    return roots


def local_office_center_overview() -> dict:
    roots = office_root_statuses()
    notes = markdown_draft_entries(OFFICE_NOTES_DIR, "office-note", 20)
    recent_items = []
    type_counts: dict[str, int] = {}
    for root in roots:
        for item in root.get("sample", []):
            kind = item.get("kind", "other")
            type_counts[kind] = type_counts.get(kind, 0) + 1
            enriched = dict(item)
            enriched["root_id"] = root.get("id", "")
            enriched["root_name"] = root.get("name", "")
            recent_items.append(enriched)
    recent_items.sort(key=lambda item: item.get("updated", 0), reverse=True)
    return {
        "name": "Local Office Center",
        "mode": "read-only-office-map-plus-notes",
        "note_dir": str(OFFICE_NOTES_DIR),
        "roots": roots,
        "root_count": len(roots),
        "recent_items": recent_items[:40],
        "recent_item_count": len(recent_items),
        "type_counts": type_counts,
        "notes": notes,
        "note_count": len(notes),
        "workflows": [
            "Review company/project folders without editing them.",
            "Turn meeting-style context into project-local office notes.",
            "Route follow-ups to Task Board, Project Management Hall, Writing Studio, or Temporary Draft Box.",
            "Keep company workspace writes behind future explicit confirmation gates.",
        ],
        "safe_note": "Local Office Center performs bounded allowlisted office-folder inspection only. It writes notes under workspace/office-notes and does not edit, move, delete, open, email, upload, or sync company files.",
    }


def create_office_note(req: OfficeNoteRequest) -> dict:
    title = req.title.strip() or "AI Town office note"
    body = req.body.strip() or "Summarize the office context, decisions, follow-ups, and routing."
    source = req.source_building.strip() or "local-office-center"
    root_id = req.root_id.strip() or "company"
    root = office_root_entry(root_id) or office_root_entry("company") or OFFICE_CENTER_ROOTS[0]
    overview = local_office_center_overview()
    root_snapshot = next((item for item in overview["roots"] if item.get("id") == root["id"]), {})
    OFFICE_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    note_path = OFFICE_NOTES_DIR / f"{timestamp}-{slugify_filename(root['id'])}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"source: ai-town/{source}",
        f"root_id: {root['id']}",
        "status: draft",
        "safety: office-note-project-local-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Office Scope",
        "",
        f"- Root: {root['name']} (`{root['path']}`)",
        f"- Role: {root.get('role', '')}",
        f"- Exists: {root_snapshot.get('exists', False)}",
        f"- Sampled entries: {root_snapshot.get('sample_count', 0)}",
        f"- Kind counts: {json.dumps(root_snapshot.get('kind_counts', {}), ensure_ascii=False)}",
        "",
        "## Notes",
        "",
        body,
        "",
        "## Sampled Context",
        "",
    ])
    sample = root_snapshot.get("sample", []) if isinstance(root_snapshot, dict) else []
    if sample:
        content += "\n".join([
            f"- `{item.get('relative_path', item.get('name', ''))}` | {item.get('kind', 'other')} | {item.get('bytes', 0)} bytes"
            for item in sample[:12]
        ])
    else:
        content += "- No matching office entries sampled from this root."
    content += "\n\n## Follow-up Routes\n\n- Task Board\n- Project Management Hall\n- Writing Studio\n- Temporary Draft Box\n\n## Safety\n\n- This note was written only under workspace/office-notes.\n- It did not edit, move, delete, open, email, upload, or sync any company or source document."
    note_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Office note created: {title}",
        f"Created project-local office note `{title}` for `{root['id']}`.\n\nNote: `{note_path}`",
        "ai-town/local-office-center",
    )
    return {
        "status": "saved",
        "draft_path": str(note_path),
        "memory_event": memory,
        "preview": content,
        "root": {"id": root["id"], "name": root["name"], "path": str(root["path"])},
        "safety": "office-note-project-local-only",
    }


def schedule_signal_entries() -> list[dict]:
    entries = []
    for path in SCHEDULE_CENTER_SIGNAL_FILES:
        entry = {
            "title": path.stem,
            "path": str(path),
            "exists": path.exists(),
            "kind": "signal-file",
            "preview": "",
        }
        if path.exists() and path.is_file():
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                interesting = []
                for line in text.splitlines():
                    stripped = line.strip()
                    if not stripped:
                        continue
                    lower = stripped.lower()
                    if any(token in lower for token in ["[ ]", "next", "todo", "priority", "deadline", "schedule", "milestone", "updated", "current"]):
                        interesting.append(stripped)
                    if len(interesting) >= 8:
                        break
                entry["preview"] = "\n".join(interesting)[:900] or text[:500]
                entry["bytes"] = path.stat().st_size
                entry["updated"] = path.stat().st_mtime
            except Exception as exc:
                entry["error"] = str(exc)
        entries.append(entry)
    return entries


def schedule_plan_center_overview() -> dict:
    signals = schedule_signal_entries()
    task_board = task_board_overview()
    plan_tasks = plan_task_entries(80)
    open_plan_tasks = [task for task in plan_tasks if task.get("status") == "open"]
    office_notes = markdown_draft_entries(OFFICE_NOTES_DIR, "office-note", 8)
    schedules = markdown_draft_entries(SCHEDULE_DRAFTS_DIR, "schedule-plan", 20)
    return {
        "name": "Schedule and Plan Center",
        "mode": "read-only-planning-signals-plus-drafts",
        "draft_dir": str(SCHEDULE_DRAFTS_DIR),
        "signals": signals,
        "signal_count": len(signals),
        "open_plan_tasks": open_plan_tasks[:12],
        "open_plan_task_count": len(open_plan_tasks),
        "local_tasks": task_board.get("local_tasks", [])[:12],
        "local_task_count": task_board.get("local_task_count", 0),
        "task_status_counts": task_board.get("status_counts", {}),
        "office_notes": office_notes,
        "office_note_count": len(office_notes),
        "schedule_drafts": schedules,
        "schedule_draft_count": len(schedules),
        "planning_rules": [
            "Draft plans only; do not install calendar events or scheduled tasks.",
            "Route real execution through Task Board or confirm-required Terminal Control.",
            "Keep experiments and long-running jobs outside gameplay shortcuts unless explicitly confirmed.",
            "Use short planning windows so the town remains responsive and reviewable.",
        ],
        "safe_note": "Schedule and Plan Center reads local planning signals and writes schedule drafts under workspace/schedules only. It does not edit calendars, install schedulers, start jobs, stop services, change trackers, or notify external systems.",
    }


def create_schedule_draft(req: ScheduleDraftRequest) -> dict:
    title = req.title.strip() or "AI Town schedule plan"
    body = req.body.strip() or "Describe the planning window, priorities, time boxes, review checkpoints, and safe next action."
    horizon = slugify_filename(req.horizon or "week")
    source = req.source_building.strip() or "schedule-plan-center"
    overview = schedule_plan_center_overview()
    SCHEDULE_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    draft_path = SCHEDULE_DRAFTS_DIR / f"{timestamp}-{horizon}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"horizon: {horizon}",
        f"source: ai-town/{source}",
        "status: draft",
        "safety: schedule-draft-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Planning Window",
        "",
        body,
        "",
        "## Current Signals",
        "",
        f"- Open PLAN tasks: {overview.get('open_plan_task_count', 0)}",
        f"- Local tasks: {overview.get('local_task_count', 0)}",
        f"- Task status: {json.dumps(overview.get('task_status_counts', {}), ensure_ascii=False)}",
        f"- Office notes sampled: {overview.get('office_note_count', 0)}",
        "",
        "## Open PLAN Items",
        "",
    ])
    open_items = overview.get("open_plan_tasks", [])
    if open_items:
        content += "\n".join([f"- {item.get('title', 'task')}" for item in open_items[:10] if isinstance(item, dict)])
    else:
        content += "- No open PLAN checklist items sampled."
    content += "\n\n## Safe Next Actions\n\n- Convert concrete follow-ups into Task Board items.\n- Keep command execution behind Terminal Control confirmation.\n- Review schedule manually before adding anything to external calendars or schedulers.\n\n## Safety\n\n- This draft did not edit calendars, install schedulers, start jobs, stop services, change trackers, or notify external systems."
    draft_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Schedule draft created: {title}",
        f"Created project-local schedule draft `{title}` for `{horizon}`.\n\nDraft: `{draft_path}`",
        "ai-town/schedule-plan-center",
    )
    return {
        "status": "saved",
        "draft_path": str(draft_path),
        "memory_event": memory,
        "preview": content,
        "horizon": horizon,
        "safety": "schedule-draft-only",
    }


def skill_index_entries(limit: int = 40) -> list[dict]:
    entries = []
    try:
        content = SKILL_INDEX_PATH.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return entries
    current_category = ""
    for line in content.splitlines():
        if line.startswith("## "):
            current_category = line[3:].strip()
        elif line.startswith("### "):
            name = line[4:].strip()
            if name:
                entries.append({
                    "name": name,
                    "category": current_category,
                    "source": str(SKILL_INDEX_PATH),
                })
        if len(entries) >= limit:
            break
    return entries


def learning_signal_entries() -> list[dict]:
    signals = []
    for path in LEARNING_SIGNAL_FILES:
        entry = {
            "title": path.name,
            "path": str(path),
            "exists": path.exists(),
            "preview": "",
        }
        if path.exists() and path.is_file():
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                lines = [
                    line.strip()
                    for line in text.splitlines()
                    if line.strip() and not line.strip().startswith("---")
                ][:10]
                entry["title"] = first_markdown_heading(path)
                entry["preview"] = "\n".join(lines)[:900]
                entry["bytes"] = path.stat().st_size
                entry["updated"] = path.stat().st_mtime
            except Exception as exc:
                entry["error"] = str(exc)
        signals.append(entry)
    return signals


def learning_training_overview() -> dict:
    skill_summary = read_skills_summary()
    skills = skill_index_entries(50)
    signals = learning_signal_entries()
    learning_plans = markdown_draft_entries(LEARNING_PLANS_DIR, "learning-plan", 20)
    schedule_drafts = markdown_draft_entries(SCHEDULE_DRAFTS_DIR, "schedule-plan", 8)
    return {
        "name": "Learning Training Grounds",
        "mode": "read-only-learning-map-plus-plans",
        "plan_dir": str(LEARNING_PLANS_DIR),
        "skill_count": skill_summary.get("count", 0),
        "category_count": skill_summary.get("categories", 0),
        "skills": skills,
        "sampled_skill_count": len(skills),
        "signals": signals,
        "signal_count": len(signals),
        "learning_plans": learning_plans,
        "learning_plan_count": len(learning_plans),
        "schedule_drafts": schedule_drafts,
        "schedule_draft_count": len(schedule_drafts),
        "tracks": [
            {"id": "ai-town", "name": "AI Town Engineering", "focus": "Godot, backend adapters, safety gates, visual baseline"},
            {"id": "research", "name": "Research Workflow", "focus": "ARIS phases, experiment planning, citation and audit discipline"},
            {"id": "agent-ops", "name": "Agent Operations", "focus": "shared memory, dispatch drafts, mailboxes, and safe collaboration"},
            {"id": "visual", "name": "Visual Production", "focus": "storybook style, asset curation, UI consistency, visual smoke proof"},
        ],
        "safe_note": "Learning Training Grounds reads local skill/resource signals and writes learning plans under workspace/learning-plans only. It does not install skills, run commands, invoke agents, edit shared memory, enroll external courses, or change schedules.",
    }


def create_learning_plan(req: LearningPlanRequest) -> dict:
    title = req.title.strip() or "AI Town learning plan"
    body = req.body.strip() or "Describe the learning objective, practice loop, resources, and proof of completion."
    track = slugify_filename(req.track or "ai-town")
    source = req.source_building.strip() or "learning-training-grounds"
    overview = learning_training_overview()
    LEARNING_PLANS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    plan_path = LEARNING_PLANS_DIR / f"{timestamp}-{track}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"track: {track}",
        f"source: ai-town/{source}",
        "status: draft",
        "safety: learning-plan-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Learning Objective",
        "",
        body,
        "",
        "## Available Local Resources",
        "",
        f"- Skills indexed: {overview.get('skill_count', 0)}",
        f"- Skill categories: {overview.get('category_count', 0)}",
        f"- Learning signals: {overview.get('signal_count', 0)}",
        f"- Schedule drafts: {overview.get('schedule_draft_count', 0)}",
        "",
        "## Practice Loop",
        "",
        "1. Pick one local skill or project doc.",
        "2. Practice in a project-local draft or safe room.",
        "3. Verify with a small proof artifact.",
        "4. Record follow-up as a task, schedule draft, or memory event.",
        "",
        "## Sample Skills",
        "",
    ])
    if overview.get("skills"):
        content += "\n".join([
            f"- {item.get('name', 'skill')} | {item.get('category', '')}"
            for item in overview.get("skills", [])[:12]
            if isinstance(item, dict)
        ])
    else:
        content += "- No local skill index entries sampled."
    content += "\n\n## Safety\n\n- This plan did not install skills, run commands, invoke agents, edit shared memory, enroll external courses, or change schedules.\n- Use Task Board, Schedule Center, or Terminal Control confirmation before turning practice into execution."
    plan_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Learning plan created: {title}",
        f"Created project-local learning plan `{title}` for track `{track}`.\n\nPlan: `{plan_path}`",
        "ai-town/learning-training-grounds",
    )
    return {
        "status": "saved",
        "draft_path": str(plan_path),
        "memory_event": memory,
        "preview": content,
        "track": track,
        "safety": "learning-plan-only",
    }


def language_signal_entries() -> list[dict]:
    signals = []
    for path in LANGUAGE_SIGNAL_FILES:
        entry = {
            "title": path.name,
            "path": str(path),
            "exists": path.exists(),
            "preview": "",
        }
        if path.exists() and path.is_file():
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                interesting = []
                for line in text.splitlines():
                    stripped = line.strip()
                    if not stripped:
                        continue
                    lower = stripped.lower()
                    if any(token in lower for token in ["language", "中文", "english", "日本", "한국", "translation", "dialogue", "ui text", "text"]):
                        interesting.append(stripped)
                    if len(interesting) >= 10:
                        break
                entry["title"] = first_markdown_heading(path)
                entry["preview"] = "\n".join(interesting)[:900] or text[:500]
                entry["bytes"] = path.stat().st_size
                entry["updated"] = path.stat().st_mtime
            except Exception as exc:
                entry["error"] = str(exc)
        signals.append(entry)
    return signals


def language_learning_overview() -> dict:
    signals = language_signal_entries()
    practice_notes = markdown_draft_entries(LANGUAGE_PRACTICE_DIR, "language-practice", 20)
    learning_plans = markdown_draft_entries(LEARNING_PLANS_DIR, "learning-plan", 8)
    supported = [
        {"id": "zh-en", "name": "Chinese-English", "focus": "bilingual UI wording, project explanations, and agent dialogue"},
        {"id": "zh-ja", "name": "Chinese-Japanese", "focus": "short UI labels, quest text, and study cards"},
        {"id": "zh-ko", "name": "Chinese-Korean", "focus": "compact interface phrases and task summaries"},
        {"id": "en-tech", "name": "Technical English", "focus": "README, architecture docs, commit/release wording, and issue summaries"},
    ]
    return {
        "name": "Language Learning Area",
        "mode": "read-only-language-signals-plus-practice-notes",
        "practice_dir": str(LANGUAGE_PRACTICE_DIR),
        "supported_languages": supported,
        "supported_count": len(supported),
        "signals": signals,
        "signal_count": len(signals),
        "practice_notes": practice_notes,
        "practice_note_count": len(practice_notes),
        "learning_plans": learning_plans,
        "learning_plan_count": len(learning_plans),
        "practice_loops": [
            "Extract small phrase sets from project docs or UI labels.",
            "Write bilingual practice cards as project-local notes.",
            "Review wording manually before it becomes game UI copy.",
            "Route larger study goals to Learning Training Grounds or Schedule Center.",
        ],
        "safe_note": "Language Learning Area reads local language/UI signals and writes practice notes under workspace/language-practice only. It does not call translators, external APIs, agents, calendars, or edit source UI/documentation.",
    }


def create_language_practice(req: LanguagePracticeRequest) -> dict:
    title = req.title.strip() or "AI Town language practice"
    body = req.body.strip() or "Describe the language goal, source phrase set, practice exercise, and review proof."
    language = slugify_filename(req.language or "zh-en")
    source = req.source_building.strip() or "language-learning-area"
    overview = language_learning_overview()
    LANGUAGE_PRACTICE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    note_path = LANGUAGE_PRACTICE_DIR / f"{timestamp}-{language}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"language: {language}",
        f"source: ai-town/{source}",
        "status: draft",
        "safety: language-practice-note-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Practice Goal",
        "",
        body,
        "",
        "## Local Signals",
        "",
        f"- Supported language tracks: {overview.get('supported_count', 0)}",
        f"- Language signals: {overview.get('signal_count', 0)}",
        f"- Existing practice notes: {overview.get('practice_note_count', 0)}",
        "",
        "## Practice Cards",
        "",
        "- Source phrase:",
        "- Target phrase:",
        "- Context:",
        "- Review note:",
        "",
        "## Suggested Loops",
        "",
    ])
    content += "\n".join([f"- {loop}" for loop in overview.get("practice_loops", [])])
    content += "\n\n## Safety\n\n- This note did not call translators, external APIs, agents, calendars, or edit source UI/documentation.\n- Promote wording into UI or docs only after manual review."
    note_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Language practice created: {title}",
        f"Created project-local language practice note `{title}` for `{language}`.\n\nNote: `{note_path}`",
        "ai-town/language-learning-area",
    )
    return {
        "status": "saved",
        "draft_path": str(note_path),
        "memory_event": memory,
        "preview": content,
        "language": language,
        "safety": "language-practice-note-only",
    }


def research_data_kind_for(path: Path) -> str:
    if path.is_dir():
        return "folder"
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".feather", ".arrow"}:
        return "table"
    if suffix in {".json", ".jsonl", ".yaml", ".yml", ".pkl", ".npz", ".npy", ".h5", ".hdf5"}:
        return "data"
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".svg", ".pdf"}:
        return "figure"
    if suffix in {".log", ".out", ".err", ".txt"}:
        return "log"
    if suffix in {".pt", ".pth", ".ckpt", ".safetensors", ".onnx"}:
        return "checkpoint"
    if suffix in {".md", ".rst"}:
        return "doc"
    return "other"


def research_data_candidate_name(path: Path) -> bool:
    tokens = re.split(r"[^a-z0-9]+", path.name.lower())
    return any(token in RESEARCH_DATA_KEYWORDS for token in tokens if token)


def bounded_research_data_entries(root: Path, limit: int = 40, max_depth: int = 3) -> list[dict]:
    entries = []
    if not root.exists() or not root.is_dir():
        return entries
    ignored = {".git", ".venv", "venv", "__pycache__", "node_modules", ".mypy_cache", ".pytest_cache"}
    queue: list[tuple[Path, int]] = [(root, 0)]
    seen = 0
    while queue and len(entries) < limit and seen < limit * 6:
        folder, depth = queue.pop(0)
        seen += 1
        try:
            children = sorted(list(islice(folder.iterdir(), 80)), key=lambda item: (not item.is_dir(), item.name.lower()))
        except Exception:
            continue
        for child in children:
            if child.name in ignored or child.is_symlink():
                continue
            try:
                is_dir = child.is_dir()
                should_collect = research_data_candidate_name(child) or (not is_dir and research_data_kind_for(child) in {"table", "data", "figure", "log", "checkpoint"})
                if should_collect:
                    stat = child.stat()
                    try:
                        relative = str(child.relative_to(root))
                    except ValueError:
                        relative = child.name
                    entries.append({
                        "name": child.name,
                        "relative_path": relative,
                        "path": str(child),
                        "kind": research_data_kind_for(child),
                        "is_dir": is_dir,
                        "bytes": 0 if is_dir else stat.st_size,
                        "updated": stat.st_mtime,
                        "depth": depth,
                    })
                    if len(entries) >= limit:
                        break
                if is_dir and depth + 1 < max_depth and len(entries) < limit:
                    queue.append((child, depth + 1))
            except Exception:
                continue
    return entries


def research_data_center_overview() -> dict:
    projects = all_research_project_cards()
    notes = markdown_draft_entries(RESEARCH_DATA_NOTES_DIR, "research-data-note", 20)
    roots = []
    candidates = []
    kind_counts: dict[str, int] = {}
    for project in RESEARCH_PROJECTS:
        for root in project.get("local_dirs", [])[:3]:
            root_entry = {
                "project_id": project["id"],
                "project_name": project["name"],
                "path": str(root),
                "exists": root.exists(),
                "candidate_count": 0,
                "sample": [],
            }
            sample = bounded_research_data_entries(root, 24, 3)
            root_entry["candidate_count"] = len(sample)
            root_entry["sample"] = sample[:8]
            roots.append(root_entry)
            for item in sample:
                item_with_project = dict(item)
                item_with_project["project_id"] = project["id"]
                item_with_project["project_name"] = project["name"]
                candidates.append(item_with_project)
                kind = item.get("kind", "other")
                kind_counts[kind] = kind_counts.get(kind, 0) + 1
    candidates.sort(key=lambda item: item.get("updated", 0), reverse=True)
    return {
        "name": "Research Data Center",
        "mode": "read-only-research-data-map-plus-local-notes",
        "research_root": str(RESEARCH_ROOT),
        "research_root_exists": RESEARCH_ROOT.exists(),
        "notes_dir": str(RESEARCH_DATA_NOTES_DIR),
        "project_count": len(projects),
        "roots": roots,
        "root_count": len(roots),
        "candidates": candidates[:60],
        "candidate_count": len(candidates),
        "kind_counts": kind_counts,
        "notes": notes,
        "note_count": len(notes),
        "audit_prompts": [
            "Record dataset provenance before claiming a result.",
            "Link every metric table or figure back to the run/config that produced it.",
            "Mark missing schema, seed, split, baseline, or checkpoint metadata as an audit risk.",
            "Promote experiment execution through ARIS planning only; this room never starts runs.",
        ],
        "safe_note": "Research Data Center performs bounded read-only scans of configured research project folders and writes notes under workspace/research-data-notes only. It does not launch experiments, modify datasets, upload files, or contact servers.",
    }


def create_research_data_note(req: ResearchDataNoteRequest) -> dict:
    title = req.title.strip() or "AI Town research data note"
    body = req.body.strip() or "Describe the dataset/result location, provenance, schema or metric meaning, and reproducibility risk."
    project_id = slugify_filename(req.project_id or "ai-town")
    source = req.source_building.strip() or "research-data-center"
    overview = research_data_center_overview()
    RESEARCH_DATA_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    note_path = RESEARCH_DATA_NOTES_DIR / f"{timestamp}-{project_id}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"project_id: {project_id}",
        f"source: ai-town/{source}",
        "status: draft",
        "safety: research-data-note-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Data Or Result Context",
        "",
        body,
        "",
        "## Current Research Data Map",
        "",
        f"- Research roots sampled: {overview.get('root_count', 0)}",
        f"- Candidate data/result entries: {overview.get('candidate_count', 0)}",
        f"- Existing research data notes: {overview.get('note_count', 0)}",
        f"- Kind counts: {json.dumps(overview.get('kind_counts', {}), ensure_ascii=False)}",
        "",
        "## Audit Checklist",
        "",
    ])
    content += "\n".join([f"- {prompt}" for prompt in overview.get("audit_prompts", [])])
    content += "\n\n## Safety\n\n- This note did not launch experiments, modify datasets, upload files, or contact servers.\n- Convert execution work into an ARIS experiment plan before running anything."
    note_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Research data note created: {title}",
        f"Created project-local research data note `{title}` for `{project_id}`.\n\nNote: `{note_path}`",
        "ai-town/research-data-center",
    )
    return {
        "status": "saved",
        "draft_path": str(note_path),
        "memory_event": memory,
        "preview": content,
        "project_id": project_id,
        "safety": "research-data-note-only",
    }


def paper_candidate_name(path: Path) -> bool:
    lower = path.name.lower()
    tokens = re.split(r"[^a-z0-9]+", lower)
    return path.suffix.lower() in PAPER_READING_EXTENSIONS or any(token in PAPER_READING_KEYWORDS for token in tokens if token)


def paper_kind_for(path: Path) -> str:
    if path.is_dir():
        return "folder"
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "paper-pdf"
    if suffix == ".bib":
        return "bibliography"
    if suffix == ".tex":
        return "manuscript"
    if suffix in {".md", ".rst", ".txt"}:
        return "note"
    if suffix == ".docx":
        return "document"
    return "other"


def bounded_paper_entries(root: Path, limit: int = 45, max_depth: int = 3) -> list[dict]:
    entries = []
    if not root.exists() or not root.is_dir():
        return entries
    ignored = {".git", ".venv", "venv", "__pycache__", "node_modules", ".mypy_cache", ".pytest_cache"}
    queue: list[tuple[Path, int]] = [(root, 0)]
    seen = 0
    while queue and len(entries) < limit and seen < limit * 6:
        folder, depth = queue.pop(0)
        seen += 1
        try:
            children = sorted(list(islice(folder.iterdir(), 90)), key=lambda item: (not item.is_dir(), item.name.lower()))
        except Exception:
            continue
        for child in children:
            if child.name in ignored or child.is_symlink():
                continue
            try:
                is_dir = child.is_dir()
                if paper_candidate_name(child):
                    stat = child.stat()
                    preview = ""
                    if child.is_file() and child.suffix.lower() in {".md", ".rst", ".txt", ".bib", ".tex"} and stat.st_size <= 512 * 1024:
                        try:
                            preview = first_meaningful_lines(child, 4, 700)
                        except Exception:
                            preview = ""
                    try:
                        relative = str(child.relative_to(root))
                    except ValueError:
                        relative = child.name
                    entries.append({
                        "name": child.name,
                        "relative_path": relative,
                        "path": str(child),
                        "kind": paper_kind_for(child),
                        "is_dir": is_dir,
                        "bytes": 0 if is_dir else stat.st_size,
                        "updated": stat.st_mtime,
                        "depth": depth,
                        "preview": preview,
                    })
                    if len(entries) >= limit:
                        break
                if is_dir and depth + 1 < max_depth and len(entries) < limit:
                    queue.append((child, depth + 1))
            except Exception:
                continue
    return entries


def pdf_parser_status() -> dict:
    for module_name in ["pypdf", "PyPDF2"]:
        try:
            module = __import__(module_name)
            version = getattr(module, "__version__", "unknown")
            return {"available": True, "module": module_name, "version": version}
        except Exception:
            continue
    return {"available": False, "module": "", "version": "", "install_hint": "Install backend requirements to enable PDF text extraction: python -m pip install -r backend\\requirements.txt"}


def paper_root_by_id(root_id: str) -> Optional[dict]:
    return next((root for root in PAPER_READING_ROOTS if root.get("id") == root_id), None)


def resolve_paper_candidate(root_id: str, relative_path: str) -> Optional[dict]:
    root_def = paper_root_by_id(root_id)
    if not root_def:
        return None
    root = Path(root_def["path"]).resolve()
    target = (root / relative_path).resolve()
    if not path_is_inside(target, root) or not target.exists() or not target.is_file():
        return None
    if target.suffix.lower() not in PAPER_READING_EXTENSIONS:
        return None
    try:
        stat = target.stat()
    except Exception:
        stat = None
    return {
        "root_id": root_def["id"],
        "root_name": root_def["name"],
        "root_path": str(root),
        "relative_path": relative_path,
        "path": str(target),
        "name": target.name,
        "kind": paper_kind_for(target),
        "bytes": stat.st_size if stat else 0,
        "updated": stat.st_mtime if stat else 0,
    }


def first_pdf_candidate() -> Optional[dict]:
    overview = paper_reading_room_overview()
    for item in overview.get("papers", []):
        if item.get("kind") == "paper-pdf" and item.get("root_id") and item.get("relative_path"):
            return resolve_paper_candidate(item["root_id"], item["relative_path"])
    return None


def extract_pdf_text_pages(path: Path, max_pages: int) -> dict:
    parser = pdf_parser_status()
    if not parser.get("available"):
        return {
            "parser": parser,
            "page_count": 0,
            "pages_read": 0,
            "text": "",
            "warnings": ["PDF parser dependency is not installed in the current backend environment."],
        }
    warnings = []
    try:
        if parser["module"] == "pypdf":
            from pypdf import PdfReader  # type: ignore
        else:
            from PyPDF2 import PdfReader  # type: ignore
        reader = PdfReader(str(path))
        page_count = len(reader.pages)
        page_limit = max(1, min(max_pages, 8, page_count))
        chunks = []
        for index in range(page_limit):
            try:
                text = reader.pages[index].extract_text() or ""
            except Exception as exc:
                warnings.append(f"Page {index + 1} extraction failed: {exc}")
                text = ""
            chunks.append(f"--- page {index + 1} ---\n{text.strip()[:5000]}")
        return {
            "parser": parser,
            "page_count": page_count,
            "pages_read": page_limit,
            "text": "\n\n".join(chunks)[:20000],
            "warnings": warnings,
        }
    except Exception as exc:
        return {
            "parser": parser,
            "page_count": 0,
            "pages_read": 0,
            "text": "",
            "warnings": [f"PDF extraction failed: {exc}"],
        }


def create_paper_extraction_report(candidate: dict, max_pages: int, source_building: str = "paper-reading-room") -> dict:
    path = Path(candidate["path"])
    max_pages = max(1, min(int(max_pages or 3), 8))
    extraction = extract_pdf_text_pages(path, max_pages)
    PAPER_EXTRACTION_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    report_path = PAPER_EXTRACTION_REPORTS_DIR / f"{timestamp}-{slugify_filename(path.stem)}-pdf-extract.md"
    extracted_text = extraction.get("text", "")
    warnings = extraction.get("warnings", [])
    content = "\n".join([
        "---",
        f"title: PDF extraction report - {path.name}",
        f"source: ai-town/{source_building}",
        f"root_id: {candidate.get('root_id', '')}",
        f"relative_path: {candidate.get('relative_path', '')}",
        "status: extracted",
        "safety: bounded-pdf-extraction-report-only",
        "---",
        "",
        f"# PDF extraction report - {path.name}",
        "",
        "## Source",
        "",
        f"- Root: {candidate.get('root_name', '')}",
        f"- Relative path: `{candidate.get('relative_path', '')}`",
        f"- Bytes: `{candidate.get('bytes', 0)}`",
        f"- Parser: `{extraction.get('parser', {}).get('module', '') or 'unavailable'}`",
        f"- Pages read: `{extraction.get('pages_read', 0)}` / `{extraction.get('page_count', 0)}`",
        "",
        "## Extraction Warnings",
        "",
        *([f"- {warning}" for warning in warnings] or ["- None."]),
        "",
        "## Text Preview",
        "",
        "```text",
        extracted_text or "No text extracted. Install parser dependencies or choose a text-based PDF.",
        "```",
        "",
        "## Citation-Audit Reading Prompts",
        "",
        "- What claims does this paper make that affect our manuscript?",
        "- Which baselines, predecessor methods, datasets, and metrics need citation checks?",
        "- Are any related-work statements too broad, too recent, or missing evidence?",
        "- What should be routed into an ARIS citation audit before manuscript edits?",
        "",
        "## Safety",
        "",
        "- This job read one allowlisted local PDF with a bounded page limit.",
        "- This job wrote only this project-local report under workspace/paper-extraction-reports.",
        "- This job did not edit PDFs, BibTeX files, manuscripts, research folders, datasets, Git state, or external services.",
    ])
    report_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"PDF extraction report created: {path.name}",
        f"Created bounded PDF extraction report for `{candidate.get('relative_path', path.name)}` at `{report_path}`.",
        "ai-town/paper-reading-room",
    )
    return {
        "status": "saved",
        "kind": "paper-pdf-extraction",
        "safety": "bounded-pdf-extraction-report-only",
        "candidate": candidate,
        "parser": extraction.get("parser", {}),
        "page_count": extraction.get("page_count", 0),
        "pages_read": extraction.get("pages_read", 0),
        "warning_count": len(warnings),
        "warnings": warnings[:8],
        "text_preview": extracted_text[:2400],
        "report_path": str(report_path),
        "memory_event": memory,
    }


def queue_paper_extraction(req: PaperExtractionJobRequest) -> dict:
    candidate = None
    if req.root_id and req.relative_path:
        candidate = resolve_paper_candidate(req.root_id, req.relative_path)
    if not candidate:
        candidate = first_pdf_candidate()
    if not candidate:
        return {
            "status": "not-available",
            "safety": "bounded-pdf-extraction-report-only",
            "message": "No allowlisted PDF candidate was found in the bounded paper map.",
            "parser": pdf_parser_status(),
        }
    if candidate.get("kind") != "paper-pdf":
        return {
            "status": "unsupported",
            "safety": "bounded-pdf-extraction-report-only",
            "candidate": candidate,
            "message": "The selected paper artifact is not a PDF.",
            "parser": pdf_parser_status(),
        }
    if candidate.get("bytes", 0) > 50 * 1024 * 1024:
        return {
            "status": "too-large",
            "safety": "bounded-pdf-extraction-report-only",
            "candidate": candidate,
            "message": "PDF exceeds the 50 MB extraction guardrail.",
            "parser": pdf_parser_status(),
        }
    if req.dry_run:
        return {
            "status": "dry-run",
            "safety": "bounded-pdf-extraction-report-only",
            "candidate": candidate,
            "max_pages": max(1, min(req.max_pages, 8)),
            "parser": pdf_parser_status(),
            "message": "Dry run only. No PDF was parsed and no report was written.",
        }
    return start_job(
        "paper-pdf-extraction",
        f"Extract PDF text: {candidate.get('name', 'paper')}",
        create_paper_extraction_report,
        candidate,
        max(1, min(req.max_pages, 8)),
        req.source_building.strip() or "paper-reading-room",
    )


def paper_reading_room_overview() -> dict:
    notes = markdown_draft_entries(PAPER_READING_NOTES_DIR, "paper-reading-note", 20)
    roots = []
    papers = []
    kind_counts: dict[str, int] = {}
    for root_def in PAPER_READING_ROOTS:
        root = root_def["path"]
        sample = bounded_paper_entries(root, 26, 3)
        root_entry = {
            "id": root_def["id"],
            "name": root_def["name"],
            "path": str(root),
            "role": root_def["role"],
            "exists": root.exists(),
            "candidate_count": len(sample),
            "sample": sample[:8],
        }
        roots.append(root_entry)
        for item in sample:
            item_with_root = dict(item)
            item_with_root["root_id"] = root_def["id"]
            item_with_root["root_name"] = root_def["name"]
            papers.append(item_with_root)
            kind = item.get("kind", "other")
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
    papers.sort(key=lambda item: item.get("updated", 0), reverse=True)
    return {
        "name": "Paper Reading Room",
        "mode": "bounded-paper-map-plus-local-reading-notes",
        "notes_dir": str(PAPER_READING_NOTES_DIR),
        "roots": roots,
        "root_count": len(roots),
        "papers": papers[:70],
        "paper_count": len(papers),
        "kind_counts": kind_counts,
        "parser": pdf_parser_status(),
        "citation_audit": citation_audit_overview(10) if papers else {},
        "extraction_report_dir": str(PAPER_EXTRACTION_REPORTS_DIR),
        "extraction_reports": markdown_draft_entries(PAPER_EXTRACTION_REPORTS_DIR, "paper-pdf-extraction", 10),
        "reading_notes": notes,
        "reading_note_count": len(notes),
        "reading_loops": [
            "Select one paper or bibliography artifact and record the claim/evidence boundary.",
            "Check whether baselines, predecessor methods, and related-work claims are cited fairly.",
            "Route missing-citation or mischaracterization risks into ARIS citation audit before paper writing.",
            "Keep PDF parsing and long literature searches in backend jobs, not the Godot main thread.",
        ],
        "safe_note": "Paper Reading Room performs bounded metadata discovery over allowlisted paper/note roots, can queue bounded PDF text extraction reports, and writes notes/reports under workspace only. It does not parse PDFs on the Godot main thread, edit bibliographies, download papers, contact search APIs, or mutate research folders.",
    }


def parse_bibtex_entries(text: str) -> list[dict]:
    entries = []
    entry_pattern = re.compile(r"@(?P<type>[A-Za-z]+)\s*\{\s*(?P<key>[^,\s]+)\s*,(?P<body>.*?)(?=\n\s*@|\Z)", re.DOTALL)
    field_pattern = re.compile(r"(?im)^\s*([A-Za-z][A-Za-z0-9_\-]*)\s*=\s*[{\"].*?[}\"]\s*,?")
    for match in entry_pattern.finditer(text):
        body = match.group("body")
        fields = {field_match.group(1).lower() for field_match in field_pattern.finditer(body)}
        entries.append({
            "type": match.group("type").lower(),
            "key": match.group("key").strip(),
            "fields": sorted(fields),
            "line": text.count("\n", 0, match.start()) + 1,
        })
    return entries


def citation_audit_overview(limit: int = 18) -> dict:
    bounded_limit = max(1, min(limit, 40))
    bib_candidates = []
    for root_def in PAPER_READING_ROOTS:
        for item in bounded_paper_entries(root_def["path"], 20, 3):
            if item.get("kind") == "bibliography":
                with_root = dict(item)
                with_root["root_id"] = root_def["id"]
                with_root["root_name"] = root_def["name"]
                bib_candidates.append(with_root)
            if len(bib_candidates) >= bounded_limit:
                break
        if len(bib_candidates) >= bounded_limit:
            break
    files = []
    entry_count = 0
    key_locations: dict[str, list[str]] = {}
    missing_field_findings = []
    skipped = 0
    required_fields = {"title", "author", "year"}
    venue_fields = {"journal", "booktitle", "venue", "publisher", "school", "institution"}

    for candidate in bib_candidates[:bounded_limit]:
        path = Path(candidate.get("path", ""))
        if not path.exists() or not path.is_file():
            skipped += 1
            continue
        root_def = paper_root_by_id(str(candidate.get("root_id", "")))
        if not root_def or not path_is_inside(path, Path(root_def["path"])):
            skipped += 1
            continue
        try:
            stat = path.stat()
            if stat.st_size > 2 * 1024 * 1024:
                skipped += 1
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            skipped += 1
            continue
        entries = parse_bibtex_entries(text)
        entry_count += len(entries)
        file_missing = []
        for entry in entries:
            key = entry.get("key", "")
            if key:
                key_locations.setdefault(key.lower(), []).append(f"{candidate.get('root_id', '')}:{candidate.get('relative_path', path.name)}:{entry.get('line', 0)}")
            fields = set(entry.get("fields", []))
            missing = sorted(required_fields - fields)
            if not fields.intersection(venue_fields):
                missing.append("venue-field")
            if missing:
                finding = {
                    "key": key,
                    "type": entry.get("type", ""),
                    "line": entry.get("line", 0),
                    "missing": missing,
                }
                file_missing.append(finding)
                if len(missing_field_findings) < 24:
                    missing_field_findings.append({
                        **finding,
                        "root_id": candidate.get("root_id", ""),
                        "relative_path": candidate.get("relative_path", ""),
                    })
        files.append({
            "root_id": candidate.get("root_id", ""),
            "root_name": candidate.get("root_name", ""),
            "relative_path": candidate.get("relative_path", ""),
            "path": candidate.get("path", ""),
            "bytes": candidate.get("bytes", 0),
            "entry_count": len(entries),
            "missing_field_count": len(file_missing),
            "sample_missing": file_missing[:6],
        })

    duplicates = [
        {"key": key, "locations": locations[:8], "count": len(locations)}
        for key, locations in sorted(key_locations.items())
        if len(locations) > 1
    ]
    finding_count = len(duplicates) + len(missing_field_findings)
    status = "needs-review" if finding_count else "clean"
    return {
        "name": "Citation Audit",
        "mode": "read-only-citation-audit",
        "status": status,
        "bib_file_count": len(files),
        "skipped_files": skipped,
        "entry_count": entry_count,
        "duplicate_key_count": len(duplicates),
        "missing_field_finding_count": len(missing_field_findings),
        "finding_count": finding_count,
        "required_fields": sorted(required_fields),
        "venue_fields": sorted(venue_fields),
        "files": files,
        "duplicates": duplicates[:16],
        "missing_field_findings": missing_field_findings,
        "safe_note": "Citation Audit reads only bounded allowlisted BibTeX files and returns metadata about keys, line numbers, and missing fields. It does not edit bibliographies, manuscripts, PDFs, research folders, Git state, or external services.",
    }


def create_citation_audit_note(req: CitationAuditNoteRequest) -> dict:
    title = req.title.strip() or "AI Town citation audit note"
    body = req.body.strip() or "Review duplicate keys, missing fields, venue/year quality, and citation hygiene."
    source = req.source_building.strip() or "paper-reading-room"
    audit = citation_audit_overview()
    content = "\n".join([
        "---",
        f"title: {title}",
        f"source: ai-town/{source}",
        "status: draft",
        "safety: citation-audit-note-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Operator Notes",
        "",
        body,
        "",
        "## Audit Summary",
        "",
        f"- Status: `{audit.get('status', '')}`",
        f"- BibTeX files checked: `{audit.get('bib_file_count', 0)}`",
        f"- Entries checked: `{audit.get('entry_count', 0)}`",
        f"- Duplicate keys: `{audit.get('duplicate_key_count', 0)}`",
        f"- Missing-field findings: `{audit.get('missing_field_finding_count', 0)}`",
        "",
        "## Duplicate Keys",
        "",
    ])
    duplicates = audit.get("duplicates", [])
    content += "\n".join([f"- `{item.get('key', '')}` count={item.get('count', 0)} locations={item.get('locations', [])}" for item in duplicates] or ["- None in bounded audit."])
    content += "\n\n## Missing Fields\n\n"
    content += "\n".join([
        f"- `{item.get('key', '')}` {item.get('missing', [])} at {item.get('root_id', '')}:{item.get('relative_path', '')}:{item.get('line', 0)}"
        for item in audit.get("missing_field_findings", [])[:24]
    ] or ["- None in bounded audit."])
    content += "\n\n## Safety\n\n- This note did not edit BibTeX files, manuscripts, PDFs, research folders, Git state, or external services.\n- Use this as a review queue before any ARIS-guided manuscript or bibliography edits."
    if req.dry_run:
        return {
            "status": "dry-run",
            "safety": "citation-audit-note-only",
            "audit": audit,
            "preview": content,
            "safe_note": "Dry run only. No citation audit note was written.",
        }
    PAPER_READING_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    note_path = PAPER_READING_NOTES_DIR / f"{timestamp}-citation-audit-{slugify_filename(title)}.md"
    note_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Citation audit note created: {title}",
        f"Created project-local citation audit note at `{note_path}` with {audit.get('finding_count', 0)} bounded finding(s).",
        "ai-town/paper-reading-room",
    )
    return {
        "status": "saved",
        "safety": "citation-audit-note-only",
        "draft_path": str(note_path),
        "memory_event": memory,
        "audit": audit,
        "preview": content,
    }


def create_paper_reading_note(req: PaperReadingNoteRequest) -> dict:
    title = req.title.strip() or "AI Town paper reading note"
    body = req.body.strip() or "Summarize the paper, key claims, evidence, missing citations, and next reading action."
    topic = slugify_filename(req.topic or "ai-town")
    source = req.source_building.strip() or "paper-reading-room"
    overview = paper_reading_room_overview()
    PAPER_READING_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    note_path = PAPER_READING_NOTES_DIR / f"{timestamp}-{topic}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"topic: {topic}",
        f"source: ai-town/{source}",
        "status: draft",
        "safety: paper-reading-note-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Reading Summary",
        "",
        body,
        "",
        "## Local Paper Map",
        "",
        f"- Roots sampled: {overview.get('root_count', 0)}",
        f"- Candidate paper/reference artifacts: {overview.get('paper_count', 0)}",
        f"- Existing reading notes: {overview.get('reading_note_count', 0)}",
        f"- Kind counts: {json.dumps(overview.get('kind_counts', {}), ensure_ascii=False)}",
        "",
        "## Citation Audit Prompts",
        "",
        "- Foundational and direct predecessor papers identified?",
        "- Baselines and compared methods cited?",
        "- Competitor methods described fairly?",
        "- Recent relevant work checked?",
        "- BibTeX entries complete, deduplicated, and venue/year fields present?",
        "",
        "## Safety",
        "",
        "- This note did not parse large PDFs, edit bibliographies, download papers, contact search APIs, or mutate research folders.",
        "- Promote deeper checks through an ARIS citation-audit task before changing manuscripts.",
    ])
    note_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Paper reading note created: {title}",
        f"Created project-local paper reading note `{title}` for `{topic}`.\n\nNote: `{note_path}`",
        "ai-town/paper-reading-room",
    )
    return {
        "status": "saved",
        "draft_path": str(note_path),
        "memory_event": memory,
        "preview": content,
        "topic": topic,
        "safety": "paper-reading-note-only",
    }


def shallow_folder_snapshot(path: Path, limit: int = 24) -> dict:
    entry = {
        "path": str(path),
        "exists": path.exists(),
        "kind": "dir" if path.is_dir() else "file" if path.is_file() else "missing",
        "sample": [],
        "sample_count": 0,
        "bytes_sampled": 0,
        "latest_update": 0,
    }
    if not path.exists():
        return entry
    if path.is_file():
        try:
            stat = path.stat()
            entry["sample_count"] = 1
            entry["bytes_sampled"] = stat.st_size
            entry["latest_update"] = stat.st_mtime
        except Exception:
            pass
        return entry
    try:
        children = list(islice(path.iterdir(), max(1, limit)))
        children.sort(key=lambda child: (not child.is_dir(), child.name.lower()))
        sample = []
        bytes_sampled = 0
        latest_update = 0
        for child in children:
            try:
                stat = child.stat()
                bytes_sampled += 0 if child.is_dir() else stat.st_size
                latest_update = max(latest_update, stat.st_mtime)
                sample.append({
                    "name": child.name,
                    "kind": "dir" if child.is_dir() else "file",
                    "bytes": 0 if child.is_dir() else stat.st_size,
                    "updated": stat.st_mtime,
                })
            except Exception:
                continue
        entry["sample"] = sample
        entry["sample_count"] = len(sample)
        entry["bytes_sampled"] = bytes_sampled
        entry["latest_update"] = latest_update
    except Exception as exc:
        entry["error"] = str(exc)
    return entry


def backup_source_entry(source_id: str) -> Optional[dict]:
    return next((source for source in BACKUP_STATION_SOURCES if source["id"] == source_id), None)


def backup_target_entry(target_id: str) -> Optional[dict]:
    return next((target for target in BACKUP_STATION_TARGETS if target["id"] == target_id), None)


def backup_integrity_snapshot(source_id: str = "ai-town-project", limit: int = 18) -> dict:
    source = backup_source_entry(source_id) or backup_source_entry("ai-town-project") or BACKUP_STATION_SOURCES[0]
    root = Path(source["path"])
    max_items = max(1, min(limit, 40))
    items = []
    skipped = []
    total_bytes_sampled = 0
    if not root.exists():
        return {
            "status": "missing",
            "mode": "read-only-backup-integrity-snapshot",
            "source": {"id": source["id"], "name": source["name"], "path": str(root), "priority": source.get("priority", "")},
            "items": [],
            "item_count": 0,
            "skipped": [],
            "safe_note": "Backup integrity snapshot is read-only and no backup, restore, copy, delete, compression, upload, or scheduling action was run.",
        }
    ignored = {".git", ".venv", "venv", "__pycache__", "node_modules", ".mypy_cache", ".pytest_cache", "tools/godot"}
    queue: list[Path] = [root]
    seen_dirs = 0
    while queue and len(items) < max_items and seen_dirs < 80:
        folder = queue.pop(0)
        seen_dirs += 1
        try:
            children = sorted(list(islice(folder.iterdir(), 80)), key=lambda item: (not item.is_dir(), item.name.lower()))
        except Exception as exc:
            skipped.append({"path": str(folder), "reason": str(exc)[:200]})
            continue
        for child in children:
            try:
                relative = str(child.relative_to(root)).replace("\\", "/")
            except ValueError:
                relative = child.name
            if child.is_symlink() or any(relative == token or relative.startswith(f"{token}/") for token in ignored):
                continue
            try:
                if child.is_dir():
                    queue.append(child)
                    continue
                stat = child.stat()
                entry = {
                    "relative_path": relative,
                    "path": str(child),
                    "bytes": stat.st_size,
                    "updated": stat.st_mtime,
                    "sha256": "",
                    "hash_status": "skipped-large" if stat.st_size > 1024 * 1024 else "ok",
                }
                if stat.st_size <= 1024 * 1024:
                    digest = hashlib.sha256()
                    with child.open("rb") as handle:
                        for chunk in iter(lambda: handle.read(65536), b""):
                            digest.update(chunk)
                    entry["sha256"] = digest.hexdigest()
                    total_bytes_sampled += stat.st_size
                items.append(entry)
                if len(items) >= max_items:
                    break
            except Exception as exc:
                skipped.append({"path": str(child), "reason": str(exc)[:200]})
            if len(items) >= max_items:
                break
    return {
        "status": "ok",
        "mode": "read-only-backup-integrity-snapshot",
        "source": {"id": source["id"], "name": source["name"], "path": str(root), "priority": source.get("priority", "")},
        "items": items,
        "item_count": len(items),
        "sample_limit": max_items,
        "bytes_hashed": total_bytes_sampled,
        "skipped": skipped[:10],
        "skip_count": len(skipped),
        "restore_checks": [
            "Pick at least one hashed small file as a restore smoke proof.",
            "Record expected path, byte size, SHA-256, and modified time before any backup activation.",
            "After restore, compare file existence, byte size, and SHA-256 before trusting the backup.",
        ],
        "safe_note": "Backup integrity snapshot reads bounded metadata and hashes only small sampled files. It does not copy, delete, compress, restore, schedule, upload, or prune files.",
    }


def backup_station_overview() -> dict:
    sources = []
    for source in BACKUP_STATION_SOURCES:
        snapshot = shallow_folder_snapshot(Path(source["path"]), 18)
        sources.append({
            "id": source["id"],
            "name": source["name"],
            "path": str(source["path"]),
            "priority": source["priority"],
            **snapshot,
        })
    targets = []
    for target in BACKUP_STATION_TARGETS:
        snapshot = shallow_folder_snapshot(Path(target["path"]), 18)
        targets.append({
            "id": target["id"],
            "name": target["name"],
            "path": str(target["path"]),
            **snapshot,
        })
    plans = markdown_draft_entries(BACKUP_PLANS_DIR, "backup-plan", 20)
    integrity = backup_integrity_snapshot("ai-town-project", 8)
    return {
        "name": "Backup Station",
        "mode": "read-only-backup-map-integrity-plus-plan-drafts",
        "draft_dir": str(BACKUP_PLANS_DIR),
        "sources": sources,
        "source_count": len(sources),
        "integrity": integrity,
        "integrity_item_count": integrity.get("item_count", 0),
        "targets": targets,
        "target_count": len(targets),
        "plans": plans,
        "plan_count": len(plans),
        "safe_note": "Backup Station inspects backup candidates, target folders, and bounded integrity samples only. It writes backup plan drafts under workspace/backup-plans and does not copy, delete, compress, restore, schedule, upload, or prune files.",
    }


def create_backup_plan_draft(req: BackupPlanDraftRequest) -> dict:
    title = req.title.strip() or "AI Town backup plan"
    body = req.body.strip() or "Review backup scope, target, retention, and restore checks before running any real backup."
    source = backup_source_entry(req.source_id.strip()) or backup_source_entry("ai-town-project") or BACKUP_STATION_SOURCES[0]
    target = backup_target_entry(req.target_id.strip()) or backup_target_entry("project-backups") or BACKUP_STATION_TARGETS[0]
    source_snapshot = shallow_folder_snapshot(Path(source["path"]), 14)
    target_snapshot = shallow_folder_snapshot(Path(target["path"]), 14)
    BACKUP_PLANS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    draft_path = BACKUP_PLANS_DIR / f"{timestamp}-{slugify_filename(source['id'])}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"source: ai-town/{req.source_building.strip() or 'backup-station'}",
        f"backup_source_id: {source['id']}",
        f"backup_target_id: {target['id']}",
        "status: draft",
        "safety: backup-plan-draft-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Backup Scope",
        "",
        f"- Source: {source['name']} (`{source['path']}`)",
        f"- Priority: {source.get('priority', 'medium')}",
        f"- Source exists: {source_snapshot.get('exists', False)}",
        f"- Source sample items: {source_snapshot.get('sample_count', 0)}",
        "",
        "## Target",
        "",
        f"- Target: {target['name']} (`{target['path']}`)",
        f"- Target exists: {target_snapshot.get('exists', False)}",
        f"- Existing target sample items: {target_snapshot.get('sample_count', 0)}",
        "",
        "## Plan Notes",
        "",
        body,
        "",
        "## Restore Checks",
        "",
        "- Define at least one file-level restore check before activation.",
        "- Record retention and pruning rules before scheduling.",
        "- Keep experiments, running services, and external repos untouched until an explicit backup runner exists.",
        "",
        "## Safety",
        "",
        "- This is a plan draft only.",
        "- No files were copied, deleted, compressed, restored, uploaded, or scheduled.",
    ])
    draft_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Backup plan draft created: {title}",
        f"Created project-local backup plan `{title}` for `{source['id']}` -> `{target['id']}`.\n\nDraft: `{draft_path}`",
        "ai-town/backup-station",
    )
    return {
        "status": "saved",
        "draft_path": str(draft_path),
        "memory_event": memory,
        "preview": content,
        "source": {"id": source["id"], "name": source["name"], "path": str(source["path"])},
        "target": {"id": target["id"], "name": target["name"], "path": str(target["path"])},
        "safety": "backup-plan-draft-only",
    }


def plan_task_entries(limit: int = 40) -> list[dict]:
    plan_path = PROJECT_ROOT / "PLAN.md"
    if not plan_path.exists():
        return []
    entries = []
    try:
        for line in plan_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if stripped.startswith("- ["):
                status = "done" if stripped.startswith("- [x]") else "open"
                title = stripped[5:].strip()
                entries.append({
                    "title": title,
                    "status": status,
                    "source": str(plan_path),
                })
            if len(entries) >= limit:
                break
    except Exception:
        return []
    return entries


def goal_signal_entries(limit: int = 12) -> list[dict]:
    signals = []
    for path in GOAL_TOWER_SIGNAL_FILES:
        if not path.exists():
            signals.append({
                "title": path.name,
                "path": str(path),
                "exists": False,
                "preview": "",
            })
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            heading = next((line.strip("# ").strip() for line in text.splitlines() if line.startswith("#")), path.stem)
            preview_lines = [
                line.strip()
                for line in text.splitlines()
                if line.strip() and not line.strip().startswith("---")
            ][:8]
            signals.append({
                "title": heading,
                "path": str(path),
                "exists": True,
                "bytes": path.stat().st_size,
                "updated": path.stat().st_mtime,
                "preview": "\n".join(preview_lines)[:900],
            })
        except Exception as exc:
            signals.append({"title": path.name, "path": str(path), "exists": True, "error": str(exc), "preview": ""})
    return signals[:limit]


def goal_tower_overview() -> dict:
    tasks = plan_task_entries(80)
    open_tasks = [task for task in tasks if task.get("status") == "open"]
    done_tasks = [task for task in tasks if task.get("status") == "done"]
    task_board = task_board_overview()
    portfolio = project_management_overview()
    drafts = markdown_draft_entries(GOAL_DRAFTS_DIR, "goal-draft", 20)
    return {
        "name": "Long-Term Goal Tower",
        "mode": "read-only-goal-map-plus-drafts",
        "draft_dir": str(GOAL_DRAFTS_DIR),
        "plan_tasks": tasks[:40],
        "open_plan_tasks": open_tasks[:20],
        "done_plan_task_count": len(done_tasks),
        "open_plan_task_count": len(open_tasks),
        "signals": goal_signal_entries(),
        "signal_count": len(goal_signal_entries()),
        "task_status_counts": task_board.get("status_counts", {}),
        "local_task_count": task_board.get("local_task_count", 0),
        "portfolio_project_count": portfolio.get("project_count", 0),
        "research_project_count": portfolio.get("research_project_count", 0),
        "drafts": drafts,
        "draft_count": len(drafts),
        "safe_note": "Goal Tower reads project plans, shared memory signals, task counts, and portfolio status. It writes goal drafts under workspace/goals only and does not modify trackers, repos, experiments, schedules, or agent runners.",
    }


def create_goal_draft(req: GoalDraftRequest) -> dict:
    title = req.title.strip() or "AI Town long-term goal"
    body = req.body.strip() or "Define the long-term outcome, milestones, evidence, and next safe action."
    horizon = slugify_filename(req.horizon or "quarter")
    source = req.source_building.strip() or "goal-tower"
    overview = goal_tower_overview()
    GOAL_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    draft_path = GOAL_DRAFTS_DIR / f"{timestamp}-{horizon}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"horizon: {horizon}",
        f"source: ai-town/{source}",
        "status: draft",
        "safety: goal-draft-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Outcome",
        "",
        body,
        "",
        "## Current Signals",
        "",
        f"- Open PLAN tasks: {overview.get('open_plan_task_count', 0)}",
        f"- Completed PLAN tasks: {overview.get('done_plan_task_count', 0)}",
        f"- Local task cards: {overview.get('local_task_count', 0)}",
        f"- Portfolio projects sampled: {overview.get('portfolio_project_count', 0)}",
        f"- Research boards: {overview.get('research_project_count', 0)}",
        "",
        "## Milestones",
        "",
        "- Define one playable user-facing milestone.",
        "- Define one backend capability milestone.",
        "- Define one verification evidence milestone.",
        "",
        "## Next Safe Action",
        "",
        "- Convert this draft into a Task Board item only after review.",
        "",
        "## Safety",
        "",
        "- This draft did not modify trackers, repositories, experiments, schedules, or agent runners.",
    ])
    draft_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Goal draft created: {title}",
        f"Created project-local goal draft `{title}` for horizon `{horizon}`.\n\nDraft: `{draft_path}`",
        "ai-town/goal-tower",
    )
    return {
        "status": "saved",
        "draft_path": str(draft_path),
        "memory_event": memory,
        "preview": content,
        "horizon": horizon,
        "safety": "goal-draft-only",
    }


def inspiration_signal_entries(limit: int = 18) -> list[dict]:
    entries = []
    for path in INSPIRATION_SIGNAL_FILES:
        if not path.exists():
            entries.append({"title": path.name, "path": str(path), "exists": False, "preview": ""})
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            heading = next((line.strip("# ").strip() for line in text.splitlines() if line.startswith("#")), path.stem)
            idea_lines = []
            for line in text.splitlines():
                stripped = line.strip()
                lower = stripped.lower()
                if not stripped:
                    continue
                if any(token in lower for token in ["visual", "style", "goal", "next", "todo", "future", "baseline", "roadmap", "灵感", "目标"]):
                    idea_lines.append(stripped)
                if len(idea_lines) >= 8:
                    break
            entries.append({
                "title": heading,
                "path": str(path),
                "exists": True,
                "bytes": path.stat().st_size,
                "updated": path.stat().st_mtime,
                "preview": "\n".join(idea_lines)[:900],
            })
        except Exception as exc:
            entries.append({"title": path.name, "path": str(path), "exists": True, "error": str(exc), "preview": ""})
    return entries[:limit]


def inspiration_station_overview() -> dict:
    notes = markdown_draft_entries(INSPIRATION_NOTES_DIR, "inspiration-note", 20)
    drafts = (
        markdown_draft_entries(DRAFTS_DIR, "writing-draft", 8)
        + markdown_draft_entries(PROJECT_BRIEFS_DIR, "project-brief", 6)
        + markdown_draft_entries(GOAL_DRAFTS_DIR, "goal-draft", 6)
    )
    return {
        "name": "Inspiration Collection Station",
        "mode": "read-only-idea-inbox-plus-notes",
        "draft_dir": str(INSPIRATION_NOTES_DIR),
        "signals": inspiration_signal_entries(),
        "signal_count": len(inspiration_signal_entries()),
        "nearby_drafts": drafts[:16],
        "nearby_draft_count": len(drafts),
        "notes": notes,
        "note_count": len(notes),
        "safe_note": "Inspiration Station gathers project-local idea signals from docs, memory, and nearby drafts. It writes inspiration notes under workspace/inspiration only and does not edit source docs, shared memory, trackers, repos, or assets.",
    }


def create_inspiration_note(req: InspirationNoteRequest) -> dict:
    title = req.title.strip() or "AI Town inspiration note"
    body = req.body.strip() or "Capture the idea, why it matters, and where it might belong."
    tag = slugify_filename(req.tag or "ai-town")
    source = req.source_building.strip() or "inspiration-station"
    INSPIRATION_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    note_path = INSPIRATION_NOTES_DIR / f"{timestamp}-{tag}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"tag: {tag}",
        f"source: ai-town/{source}",
        "status: draft",
        "safety: inspiration-note-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Idea",
        "",
        body,
        "",
        "## Possible Homes",
        "",
        "- Task Board item",
        "- Goal Tower milestone",
        "- Visual baseline note",
        "- Architecture follow-up",
        "",
        "## Safety",
        "",
        "- This note is project-local only.",
        "- It did not edit source docs, shared memory, trackers, repos, assets, or agent runners.",
    ])
    note_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Inspiration note created: {title}",
        f"Created project-local inspiration note `{title}` with tag `{tag}`.\n\nNote: `{note_path}`",
        "ai-town/inspiration-station",
    )
    return {
        "status": "saved",
        "draft_path": str(note_path),
        "memory_event": memory,
        "preview": content,
        "tag": tag,
        "safety": "inspiration-note-only",
    }


def draft_shelf_statuses() -> list[dict]:
    shelves = [
        ("writing", DRAFTS_DIR, "writing-draft"),
        ("tasks", TASKS_DIR, "task-draft"),
        ("agent-dispatch", AGENT_DISPATCH_DRAFTS_DIR, "agent-dispatch-draft"),
        ("automation", AUTOMATION_DRAFTS_DIR, "automation-draft"),
        ("settings", SETTINGS_DRAFTS_DIR, "settings-draft"),
        ("tests", TEST_PLAN_DRAFTS_DIR, "test-plan"),
        ("bugs", BUG_REPORTS_DIR, "bug-report"),
        ("projects", PROJECT_BRIEFS_DIR, "project-brief"),
        ("downloads", DOWNLOAD_INTAKE_DIR, "download-intake"),
        ("assets", ASSET_NOTES_DIR, "asset-note"),
        ("office", OFFICE_NOTES_DIR, "office-note"),
        ("schedules", SCHEDULE_DRAFTS_DIR, "schedule-plan"),
        ("learning", LEARNING_PLANS_DIR, "learning-plan"),
        ("language", LANGUAGE_PRACTICE_DIR, "language-practice"),
        ("research-data", RESEARCH_DATA_NOTES_DIR, "research-data-note"),
        ("paper-reading", PAPER_READING_NOTES_DIR, "paper-reading-note"),
        ("releases", RELEASE_DRAFTS_DIR, "release-checklist"),
        ("plugins", PLUGIN_DRAFTS_DIR, "plugin-draft"),
        ("backups", BACKUP_PLANS_DIR, "backup-plan"),
        ("goals", GOAL_DRAFTS_DIR, "goal-draft"),
        ("inspiration", INSPIRATION_NOTES_DIR, "inspiration-note"),
        ("temporary", TEMP_DRAFTS_DIR, "temp-draft"),
    ]
    statuses = []
    for shelf_id, path, kind in shelves:
        entries = markdown_draft_entries(path, kind, 8)
        statuses.append({
            "id": shelf_id,
            "kind": kind,
            "path": str(path),
            "exists": path.exists(),
            "count": len(entries),
            "latest": entries[:3],
        })
    return statuses


def temporary_draft_box_overview() -> dict:
    shelves = draft_shelf_statuses()
    total = sum(shelf.get("count", 0) for shelf in shelves)
    temp_entries = markdown_draft_entries(TEMP_DRAFTS_DIR, "temp-draft", 20)
    return {
        "name": "Temporary Draft Box",
        "mode": "project-local-draft-inbox",
        "draft_dir": str(TEMP_DRAFTS_DIR),
        "shelves": shelves,
        "shelf_count": len(shelves),
        "total_known_drafts": total,
        "temp_drafts": temp_entries,
        "temp_draft_count": len(temp_entries),
        "safe_note": "Temporary Draft Box inventories project-local draft shelves and writes scratch drafts under workspace/temp-drafts only. It does not promote, delete, route, overwrite, or send drafts to agents or external tools.",
    }


def create_temp_draft(req: TempDraftRequest) -> dict:
    title = req.title.strip() or "AI Town temporary draft"
    body = req.body.strip() or "Capture a quick thought before routing it."
    route_hint = slugify_filename(req.route_hint or "triage-later")
    source = req.source_building.strip() or "temporary-draft-box"
    TEMP_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    draft_path = TEMP_DRAFTS_DIR / f"{timestamp}-{route_hint}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"route_hint: {route_hint}",
        f"source: ai-town/{source}",
        "status: temp",
        "safety: temp-draft-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Scratch",
        "",
        body,
        "",
        "## Possible Routes",
        "",
        "- Task Board",
        "- Writing Studio",
        "- Goal Tower",
        "- Bug Clinic",
        "- Project Management Hall",
        "- Inspiration Station",
        "",
        "## Safety",
        "",
        "- This is a project-local scratch draft only.",
        "- It was not promoted, sent to an agent, copied into docs, or written outside workspace/temp-drafts.",
    ])
    draft_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Temporary draft created: {title}",
        f"Created project-local temporary draft `{title}` with route hint `{route_hint}`.\n\nDraft: `{draft_path}`",
        "ai-town/temporary-draft-box",
    )
    return {
        "status": "saved",
        "draft_path": str(draft_path),
        "memory_event": memory,
        "preview": content,
        "route_hint": route_hint,
        "safety": "temp-draft-only",
    }


def record_memory_event(title: str, body: str, source: str) -> dict:
    MEMORY_EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"{timestamp}-{slugify_filename(title)}.md"
    path = MEMORY_EVENTS_DIR / filename
    content = "\n".join([
        "---",
        f"title: {title}",
        f"source: {source}",
        "status: recorded",
        "safety: project-local-memory-event",
        "---",
        "",
        f"# {title}",
        "",
        body,
    ])
    path.write_text(content, encoding="utf-8")
    return {"path": str(path), "bytes": path.stat().st_size}


def terminal_command_catalog() -> dict:
    commands = []
    for command_id, spec in TERMINAL_COMMANDS.items():
        preview = terminal_command_preview(command_id)
        commands.append({
            "id": command_id,
            "label": spec["label"],
            "description": spec["description"],
            "cwd": str(spec["cwd"]),
            "args": spec["args"],
            "timeout": spec["timeout"],
            "safety": spec["safety"],
            "preview_status": preview.get("status", "unknown"),
            "cwd_allowed": preview.get("cwd_allowed", False),
        })
    return {
        "name": "Terminal Control Room",
        "mode": "allowlisted-confirm-required",
        "confirmation_required": CONFIRM_RUN_COMMAND,
        "log_dir": str(TERMINAL_LOG_DIR),
        "commands": commands,
        "count": len(commands),
    }


def terminal_command_preview(command_id: str) -> dict:
    spec = TERMINAL_COMMANDS.get(command_id)
    if not spec:
        return {
            "mode": "terminal-command-preview",
            "status": "missing",
            "command_id": command_id,
            "safe_note": "Terminal preview is read-only and does not execute commands.",
        }
    cwd = spec["cwd"]
    try:
        cwd_allowed = cwd.resolve().is_relative_to(PROJECT_ROOT.resolve())
    except Exception:
        cwd_allowed = False
    args = [str(arg) for arg in spec.get("args", [])]
    blocked = not cwd_allowed
    return {
        "mode": "terminal-command-preview",
        "status": "blocked" if blocked else "preview",
        "command_id": command_id,
        "label": spec.get("label", command_id),
        "description": spec.get("description", ""),
        "args": args,
        "command_line": " ".join(args),
        "cwd": str(cwd),
        "cwd_allowed": cwd_allowed,
        "timeout": spec.get("timeout", 0),
        "safety": "confirm-required-allowlisted",
        "confirmation_required": CONFIRM_RUN_COMMAND,
        "expected_effects": [
            "Runs only the fixed argv shown in this preview.",
            "Uses subprocess shell=False; no free-form shell string is accepted.",
            "Writes a bounded JSON log under workspace/terminal-logs only after confirmation.",
            "Records a project-local memory event after completion.",
        ],
        "blocked_reasons": [] if cwd_allowed else ["Command cwd is outside the AI Town project allowlist."],
        "safe_note": "Terminal preview is read-only. It does not queue jobs, execute commands, mutate files, install packages, kill processes, or contact external services.",
    }


def permission_receipts(limit: int = 20) -> dict:
    bounded_limit = max(1, min(limit, 80))
    receipts: list[dict] = []

    def add_receipt(kind: str, title: str, status: str, safety: str, source: str, at: float, path: str = "", detail: str = "") -> None:
        receipts.append({
            "id": hashlib.sha1(f"{kind}|{title}|{path}|{at}".encode("utf-8", errors="ignore")).hexdigest()[:12],
            "kind": kind,
            "title": title,
            "status": status,
            "safety": safety,
            "source": source,
            "at": at,
            "path": path,
            "detail": detail,
        })

    for log in latest_terminal_logs(30):
        add_receipt(
            "confirmed-command",
            str(log.get("label", log.get("command_id", "terminal command"))),
            str(log.get("status", "unknown")),
            "confirm-required-allowlisted",
            "terminal-control",
            float(log.get("completed") or log.get("started") or 0),
            str(log.get("log_path", "")),
            f"confirmation={CONFIRM_RUN_COMMAND} returncode={log.get('returncode', '')}",
        )

    for log in latest_project_verification_logs(30):
        command = log.get("command", {}) if isinstance(log.get("command", {}), dict) else {}
        add_receipt(
            "project-verification",
            f"{log.get('project_name', 'project')} / {command.get('label', 'check')}",
            str(log.get("status", "unknown")),
            "confirm-required-project-verification",
            "code-workshop",
            float(log.get("updated_at") or 0),
            str(log.get("log_path", "")),
            f"confirmation={CONFIRM_RUN_PROJECT_CHECK} returncode={log.get('returncode', '')}",
        )

    for item in markdown_draft_entries(MODEL_TEST_RESULTS_DIR, "model-profile-test", 20):
        add_receipt(
            "model-profile-test",
            str(item.get("title", "Model profile test")),
            "recorded",
            "no-secret-model-profile-test",
            "model-market",
            float(item.get("updated", 0) or 0),
            str(item.get("path", "")),
            "dry-run or bounded live probe; raw keys are never written",
        )

    for item in model_key_vault_entries():
        add_receipt(
            "model-key-vault",
            str(item.get("label", item.get("profile_id", "model key"))),
            str(item.get("status", "stored")),
            "confirm-required-encrypted-local-secret",
            "model-market",
            float(item.get("updated_at", 0) or 0),
            str(MODEL_KEY_VAULT_PATH),
            f"profile={item.get('profile_id', '')} fingerprint={item.get('fingerprint', '')} confirmation={CONFIRM_SAVE_API_KEY}",
        )

    for item in markdown_draft_entries(MEMORY_EVENTS_DIR, "memory-event", 40):
        title = str(item.get("title", item.get("id", "memory event")))
        safety = "project-local-memory-event"
        if "draft" in title.lower() or "created" in title.lower() or "saved" in title.lower():
            safety = "project-local-write"
        add_receipt(
            "memory-event",
            title,
            "recorded",
            safety,
            "workspace/memory-events",
            float(item.get("updated", 0) or 0),
            str(item.get("path", "")),
            "project-local audit memory signal",
        )

    for item in markdown_draft_entries(MEMORY_PROMOTIONS_DIR, "memory-promotion", 40):
        add_receipt(
            "shared-memory-promotion",
            str(item.get("title", item.get("id", "memory promotion"))),
            "recorded",
            "confirm-required-shared-memory-write",
            "memory-library",
            float(item.get("updated", 0) or 0),
            str(item.get("path", "")),
            f"confirmation={CONFIRM_PROMOTE_MEMORY}",
        )

    for task in agent_task_snapshot(30).get("tasks", []):
        if isinstance(task, dict):
            add_receipt(
                "agent-task",
                str(task.get("title", task.get("task_type", "agent task"))),
                str(task.get("status", "unknown")),
                str(task.get("safety", "safe-local-agent-task")),
                str(task.get("target_agent", "agent-task-queue")),
                float(task.get("updated_at") or task.get("created_at") or 0),
                str(task.get("log_path", "")),
                str(task.get("result_summary", "")),
            )

    for invocation in agent_tool_invocation_snapshot(30).get("recent", []):
        if isinstance(invocation, dict):
            add_receipt(
                "agent-tool",
                str(invocation.get("tool_name", invocation.get("tool_id", "agent tool"))),
                str(invocation.get("status", "unknown")),
                str(invocation.get("safety", "safe-agent-tool")),
                str(invocation.get("target_agent", "agent-tool-queue")),
                float(invocation.get("updated_at") or invocation.get("created_at") or 0),
                str(invocation.get("log_path", "")),
                str(invocation.get("result_summary", "")),
            )

    for task in load_task_ledger()[:40]:
        if isinstance(task, dict):
            add_receipt(
                "local-task",
                str(task.get("title", "local task")),
                str(task.get("status", "unknown")),
                str(task.get("safety", "project-local-task")),
                str(task.get("source_building", "task-board")),
                float(task.get("updated_at") or task.get("created_at") or 0),
                str(task.get("path", "")),
                str(task.get("summary", "")),
            )

    counts: dict[str, int] = {}
    for receipt in receipts:
        kind = str(receipt.get("kind", "receipt"))
        counts[kind] = counts.get(kind, 0) + 1
    receipts = sorted(receipts, key=lambda item: item.get("at", 0), reverse=True)
    return {
        "name": "Permission Receipts",
        "mode": "read-only-local-safety-audit",
        "receipts": receipts[:bounded_limit],
        "count": len(receipts),
        "returned": min(len(receipts), bounded_limit),
        "counts": counts,
        "sources": [
            "workspace/terminal-logs",
            "workspace/model-test-results",
            "workspace/memory-events",
            "workspace/agent-task-logs",
            "workspace/agent-tool-logs",
            "workspace/tasks",
        ],
        "safe_note": "Receipts are read-only evidence of existing local actions. This view does not grant permissions, run commands, edit files, or contact external services.",
    }


def secret_audit_relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except Exception:
        return str(path)


def secret_audit_candidate_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if not target.exists() or not target.is_dir():
        return []
    files = []
    try:
        for path in target.rglob("*"):
            if len(files) >= SECRET_AUDIT_MAX_FILES:
                break
            if not path.is_file():
                continue
            if not path_is_inside(path, PROJECT_ROOT):
                continue
            suffixes = {suffix.lower() for suffix in path.suffixes}
            if path.name.lower().endswith(".env.example") or suffixes.intersection(SECRET_AUDIT_EXTENSIONS):
                files.append(path)
    except Exception:
        return files
    return files


def secret_audit_line_for_match(text: str, position: int) -> str:
    line_start = text.rfind("\n", 0, position) + 1
    line_end = text.find("\n", position)
    if line_end == -1:
        line_end = len(text)
    return text[line_start:line_end]


def secret_audit_is_safe_assignment_placeholder(line: str) -> bool:
    normalized = line.lower()
    return any(marker in normalized for marker in [
        "[redacted",
        "placeholder",
        "replace-with",
        "your-",
        "not-written",
        "fake_",
        "fake-",
        "example",
        "dummy",
    ])


def secret_exposure_audit(limit: int = 50) -> dict:
    bounded_limit = max(1, min(limit, 120))
    scanned_files = 0
    skipped_files = 0
    scanned_bytes = 0
    finding_count = 0
    pattern_counts = {name: 0 for name, _pattern in SECRET_AUDIT_PATTERNS}
    findings: list[dict] = []
    sources = []

    for target in SECRET_AUDIT_TARGETS:
        target_path = target["path"]
        source = {
            "id": target["id"],
            "name": target["name"],
            "path": secret_audit_relative_path(target_path),
            "exists": target_path.exists(),
            "kind": "dir" if target_path.is_dir() else "file" if target_path.is_file() else "missing",
        }
        sources.append(source)
        if not target_path.exists():
            continue
        if not path_is_inside(target_path, PROJECT_ROOT):
            skipped_files += 1
            continue
        for path in secret_audit_candidate_files(target_path):
            if scanned_files >= SECRET_AUDIT_MAX_FILES:
                skipped_files += 1
                continue
            try:
                size = path.stat().st_size
                if size > SECRET_AUDIT_MAX_BYTES_PER_FILE:
                    skipped_files += 1
                    continue
                raw = path.read_bytes()
                text = raw.decode("utf-8", errors="replace")
            except Exception:
                skipped_files += 1
                continue
            scanned_files += 1
            scanned_bytes += len(raw)
            per_file_counts: dict[str, int] = {}
            line_numbers: dict[str, list[int]] = {}
            for pattern_name, pattern in SECRET_AUDIT_PATTERNS:
                for match in pattern.finditer(text):
                    if pattern_name == "assigned_secret" and secret_audit_is_safe_assignment_placeholder(secret_audit_line_for_match(text, match.start())):
                        continue
                    per_file_counts[pattern_name] = per_file_counts.get(pattern_name, 0) + 1
                    pattern_counts[pattern_name] = pattern_counts.get(pattern_name, 0) + 1
                    if len(line_numbers.get(pattern_name, [])) < 8:
                        line_numbers.setdefault(pattern_name, []).append(text.count("\n", 0, match.start()) + 1)
            if per_file_counts:
                file_findings = sum(per_file_counts.values())
                finding_count += file_findings
                if len(findings) < bounded_limit:
                    findings.append({
                        "path": secret_audit_relative_path(path),
                        "bytes": size,
                        "finding_count": file_findings,
                        "pattern_counts": per_file_counts,
                        "line_numbers": line_numbers,
                    })

    return {
        "name": "Secret Exposure Audit",
        "mode": "read-only-secret-exposure-audit",
        "generated_at": time.time(),
        "status": "needs-review" if finding_count else "clean",
        "finding_count": finding_count,
        "returned": len(findings),
        "scanned_files": scanned_files,
        "skipped_files": skipped_files,
        "scanned_bytes": scanned_bytes,
        "max_files": SECRET_AUDIT_MAX_FILES,
        "max_bytes_per_file": SECRET_AUDIT_MAX_BYTES_PER_FILE,
        "pattern_counts": pattern_counts,
        "pattern_names": [name for name, _pattern in SECRET_AUDIT_PATTERNS],
        "sources": sources,
        "findings": findings,
        "safe_note": "This read-only audit scans only allowlisted project-local examples, caches, dispatches, and logs. It returns counts, filenames, and line numbers only; matched secret text is never returned and no files are changed.",
    }


def latest_terminal_logs(limit: int = 8) -> list[dict]:
    if not TERMINAL_LOG_DIR.exists():
        return []
    logs = []
    try:
        for path in sorted(TERMINAL_LOG_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["log_path"] = str(path)
            logs.append(data)
    except Exception:
            pass
    return logs


def latest_project_verification_logs(limit: int = 12) -> list[dict]:
    if not PROJECT_VERIFICATION_LOG_DIR.exists():
        return []
    logs = []
    try:
        files = sorted(PROJECT_VERIFICATION_LOG_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        for path in files[:limit]:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data["log_path"] = str(path)
                data["updated_at"] = path.stat().st_mtime
                logs.append(data)
    except Exception:
        pass
    return logs


def _timeline_event(
    event_id: str,
    kind: str,
    title: str,
    status: str,
    source: str,
    at: float,
    detail: str = "",
    path: str = "",
    safety: str = "read-only",
) -> dict:
    return {
        "id": event_id,
        "kind": kind,
        "title": title,
        "status": status,
        "source": source,
        "at": at,
        "detail": detail,
        "path": path,
        "safety": safety,
    }


def system_event_timeline(limit: int = 40) -> dict:
    bounded_limit = max(1, min(limit, 100))
    events: list[dict] = []
    counts: dict[str, int] = {}

    for item in markdown_draft_entries(MEMORY_EVENTS_DIR, "memory-event", 40):
        events.append(_timeline_event(
            str(item.get("id", "")),
            "memory-event",
            str(item.get("title", item.get("id", "memory event"))),
            "recorded",
            "workspace/memory-events",
            float(item.get("updated", 0) or 0),
            "Project-local memory event",
            str(item.get("path", "")),
            "project-local-read",
        ))

    for log in latest_terminal_logs(20):
        events.append(_timeline_event(
            str(log.get("id", log.get("command_id", "terminal-log"))),
            "terminal-log",
            str(log.get("label", log.get("command_id", "terminal command"))),
            str(log.get("status", "unknown")),
            "terminal-control",
            float(log.get("completed") or log.get("started") or 0),
            f"returncode={log.get('returncode', '')}",
            str(log.get("log_path", "")),
            "confirm-required-log",
        ))

    for log in latest_project_verification_logs(20):
        command = log.get("command", {}) if isinstance(log.get("command", {}), dict) else {}
        events.append(_timeline_event(
            hashlib.sha1(str(log.get("log_path", "")).encode("utf-8", errors="ignore")).hexdigest()[:12],
            "project-verification",
            f"{log.get('project_name', 'project')} / {command.get('label', 'check')}",
            str(log.get("status", "unknown")),
            "code-workshop",
            float(log.get("updated_at") or 0),
            f"returncode={log.get('returncode', '')}",
            str(log.get("log_path", "")),
            "confirm-required-project-verification",
        ))

    for job in job_queue_snapshot(30).get("recent", []):
        if not isinstance(job, dict):
            continue
        events.append(_timeline_event(
            str(job.get("id", "")),
            "backend-job",
            str(job.get("label", job.get("kind", "job"))),
            str(job.get("status", "unknown")),
            "backend-job-queue",
            float(job.get("updated_at") or job.get("created_at") or 0),
            str(job.get("error", "")),
            "",
            str(job.get("safety", "read-only-job")),
        ))

    for task in agent_task_snapshot(30).get("tasks", []):
        if not isinstance(task, dict):
            continue
        events.append(_timeline_event(
            str(task.get("id", "")),
            "agent-task",
            str(task.get("title", task.get("task_type", "agent task"))),
            str(task.get("status", "unknown")),
            str(task.get("target_agent", "agent-task-queue")),
            float(task.get("updated_at") or task.get("created_at") or 0),
            str(task.get("result_summary", "")),
            str(task.get("log_path", "")),
            str(task.get("safety", "safe-local-agent-task")),
        ))

    for invocation in agent_tool_invocation_snapshot(30).get("recent", []):
        if not isinstance(invocation, dict):
            continue
        events.append(_timeline_event(
            str(invocation.get("id", "")),
            "agent-tool",
            str(invocation.get("tool_name", invocation.get("tool_id", "agent tool"))),
            str(invocation.get("status", "unknown")),
            str(invocation.get("target_agent", "agent-tool-queue")),
            float(invocation.get("updated_at") or invocation.get("created_at") or 0),
            str(invocation.get("result_summary", "")),
            str(invocation.get("log_path", "")),
            str(invocation.get("safety", "safe-agent-tool")),
        ))

    for task in load_task_ledger()[:30]:
        if not isinstance(task, dict):
            continue
        events.append(_timeline_event(
            str(task.get("id", "")),
            "local-task",
            str(task.get("title", "local task")),
            str(task.get("status", "unknown")),
            str(task.get("source_building", "task-board")),
            float(task.get("updated_at") or task.get("created_at") or 0),
            str(task.get("summary", "")),
            str(task.get("path", "")),
            str(task.get("safety", "project-local-task")),
        ))

    for event in events:
        kind = str(event.get("kind", "event"))
        counts[kind] = counts.get(kind, 0) + 1

    events = sorted(events, key=lambda item: item.get("at", 0), reverse=True)
    return {
        "name": "System Event Timeline",
        "mode": "read-only-local-event-timeline",
        "events": events[:bounded_limit],
        "count": len(events),
        "returned": min(len(events), bounded_limit),
        "counts": counts,
        "sources": [
            str(MEMORY_EVENTS_DIR),
            str(TERMINAL_LOG_DIR),
            str(AGENT_TASK_LOG_DIR),
            str(AGENT_TOOL_LOG_DIR),
            str(TASK_LEDGER_PATH),
        ],
        "safe_note": "This endpoint only aggregates existing project-local events, logs, queues, and task cards. It does not run commands, invoke agents, scan new roots, or mutate files.",
    }


def folder_status(name: str, path: Path, limit: int = 12) -> dict:
    exists = path.exists()
    entry = {
        "name": name,
        "path": str(path),
        "exists": exists,
        "kind": "dir" if path.is_dir() else "file" if path.is_file() else "missing",
        "sample_count": 0,
        "sample": [],
    }
    if exists and path.is_dir():
        try:
            children = sorted(islice(path.iterdir(), limit), key=lambda item: item.name.lower())
            entry["sample_count"] = len(children)
            entry["sample"] = [{"name": child.name, "kind": "dir" if child.is_dir() else "file"} for child in children]
        except Exception as exc:
            entry["error"] = str(exc)
    elif exists and path.is_file():
        try:
            entry["bytes"] = path.stat().st_size
        except Exception:
            pass
    return entry


def permission_policy_overview() -> dict:
    buildings = load_json_registry(BUILDING_REGISTRY_PATH)
    safety_counts: dict[str, int] = {}
    building_policies = []
    for building in buildings:
        if not isinstance(building, dict):
            continue
        safety = str(building.get("safety", "unspecified"))
        safety_counts[safety] = safety_counts.get(safety, 0) + 1
        building_policies.append({
            "id": building.get("id", ""),
            "name": building.get("name", building.get("id", "")),
            "role": building.get("role", ""),
            "safety": safety,
            "backend": building.get("backend", ""),
            "real_sources": building.get("real_sources", []),
        })
    safety_classes = [
        {
            "id": "read-only",
            "label": "Read-only",
            "rule": "List, inspect, preview, summarize, and report status without writing to local or external systems.",
            "examples": ["Memory Library shelf index", "GitHub Harbor metadata", "System Monitor services"],
        },
        {
            "id": "preview-only",
            "label": "Preview-only",
            "rule": "Generate draft text or plans without saving or executing them.",
            "examples": ["release-note draft text", "work-note preview"],
        },
        {
            "id": "project-local-write",
            "label": "Project-local write",
            "rule": "Write only under the AI Town workspace folder and record a local memory event when useful.",
            "examples": ["workspace/drafts", "workspace/tasks", "workspace/automation-drafts"],
        },
        {
            "id": "confirm-required",
            "label": "Confirm-required",
            "rule": "Require an exact confirmation phrase before queueing command execution or saving gated drafts.",
            "examples": [CONFIRM_SAVE_DRAFT, CONFIRM_RUN_COMMAND],
        },
        {
            "id": "dangerous",
            "label": "Dangerous",
            "rule": "Delete, overwrite, service shutdown, credential changes, installs, long experiments, and external writes stay blocked until future strong gates exist.",
            "examples": ["stop.cmd is listed as blocked/manual-only in Automation Factory"],
        },
    ]
    confirmation_gates = [
        {
            "id": "save-local-draft",
            "phrase": CONFIRM_SAVE_DRAFT,
            "scope": "Workbench draft save",
            "endpoint": "POST /api/workbench/action",
            "status": "active",
        },
        {
            "id": "run-local-command",
            "phrase": CONFIRM_RUN_COMMAND,
            "scope": "Terminal Control allowlisted commands",
            "endpoint": "POST /api/terminal/run",
            "status": "active",
        },
    ]
    writable_scopes = [
        folder_status("drafts", DRAFTS_DIR, 8),
        folder_status("agent_dispatch", AGENT_DISPATCH_DRAFTS_DIR, 8),
        folder_status("tasks", TASKS_DIR, 8),
        folder_status("agent_chats", AGENT_CHAT_DIR, 8),
        folder_status("agent_runner_dispatches", AGENT_RUNNER_DISPATCH_DIR, 8),
        folder_status("agent_task_logs", AGENT_TASK_LOG_DIR, 8),
        folder_status("agent_tool_logs", AGENT_TOOL_LOG_DIR, 8),
        folder_status("memory_proposals", MEMORY_PROPOSALS_DIR, 8),
        folder_status("memory_promotions", MEMORY_PROMOTIONS_DIR, 8),
        folder_status("knowledge_index", KNOWLEDGE_INDEX_DIR, 8),
        folder_status("file_vault_index", FILE_VAULT_INDEX_DIR, 8),
        folder_status("file_organize_drafts", FILE_ORGANIZE_DRAFTS_DIR, 8),
        folder_status("code_contexts", CODE_CONTEXT_DIR, 8),
        folder_status("code_patch_plans", CODE_PATCH_PLANS_DIR, 8),
        folder_status("project_verification_logs", PROJECT_VERIFICATION_LOG_DIR, 8),
        folder_status("github_harbor_drafts", GITHUB_HARBOR_DRAFTS_DIR, 8),
        folder_status("model_config_drafts", MODEL_CONFIG_DRAFTS_DIR, 8),
        folder_status("model_test_results", MODEL_TEST_RESULTS_DIR, 8),
        folder_status("model_key_vault", MODEL_KEY_VAULT_DIR, 8),
        folder_status("automation_drafts", AUTOMATION_DRAFTS_DIR, 8),
        folder_status("memory_events", MEMORY_EVENTS_DIR, 8),
        folder_status("terminal_logs", TERMINAL_LOG_DIR, 8),
    ]
    file_roots = []
    for root in file_vault_workspace_roots():
        path = root.get("path")
        file_roots.append({
            "id": root.get("id", ""),
            "name": root.get("name", ""),
            "path": str(path),
            "exists": bool(path and path.exists()),
            "mode": "allowlisted-lazy-read",
        })
    audit_events = []
    for event in markdown_draft_entries(MEMORY_EVENTS_DIR, "memory-event", 8):
        audit_events.append(event)
    for log in latest_terminal_logs(5):
        audit_events.append({
            "id": log.get("id", log.get("command_id", "terminal-log")),
            "kind": "terminal-log",
            "title": log.get("label", log.get("command_id", "terminal command")),
            "path": log.get("log_path", ""),
            "status": log.get("status", ""),
            "updated": log.get("completed") or log.get("started") or 0,
        })
    audit_events = sorted(audit_events, key=lambda item: item.get("updated", 0), reverse=True)[:12]
    blocked_actions = [
        {"id": "delete-files", "label": "Delete or overwrite user files", "status": "blocked", "reason": "No destructive file runner exists."},
        {"id": "stop-services", "label": "Stop services or terminals", "status": "blocked", "reason": "The user forbids interrupting existing processes."},
        {"id": "external-git-write", "label": "Push, tag, release, or PR", "status": "future-confirm-required", "reason": "GitHub Harbor is read-only/draft-only today."},
        {"id": "scheduler-install", "label": "Install scheduled automation", "status": "blocked", "reason": "Automation Factory writes blueprints only."},
        {"id": "raw-shell", "label": "Run arbitrary shell commands", "status": "blocked", "reason": "Terminal Control accepts only allowlisted command IDs."},
    ]
    return {
        "name": "Permission Hall",
        "mode": "read-only-policy-ledger",
        "generated_at": time.time(),
        "safety_classes": safety_classes,
        "safety_counts": safety_counts,
        "building_policies": building_policies,
        "confirmation_gates": confirmation_gates,
        "writable_scopes": writable_scopes,
        "file_roots": file_roots,
        "blocked_actions": blocked_actions,
        "audit_events": audit_events,
        "permission_receipts": permission_receipts(16),
        "secret_audit": secret_exposure_audit(8),
        "safe_note": "Permission Hall is read-only. It explains current safety classes, confirmation phrases, write scopes, allowlisted file roots, and recent audit events without changing permissions.",
    }


async def system_monitor_overview() -> dict:
    buildings = load_json_registry(BUILDING_REGISTRY_PATH)
    agents = load_json_registry(AGENT_REGISTRY_PATH)
    jobs = job_queue_snapshot()
    registry_health = registry_health_overview()
    workspace_paths = [
        ("drafts", DRAFTS_DIR),
        ("agent_dispatch", AGENT_DISPATCH_DRAFTS_DIR),
        ("tasks", TASKS_DIR),
        ("agent_chats", AGENT_CHAT_DIR),
        ("agent_runner_dispatches", AGENT_RUNNER_DISPATCH_DIR),
        ("agent_task_logs", AGENT_TASK_LOG_DIR),
        ("agent_tool_logs", AGENT_TOOL_LOG_DIR),
        ("memory_proposals", MEMORY_PROPOSALS_DIR),
        ("memory_promotions", MEMORY_PROMOTIONS_DIR),
        ("knowledge_index", KNOWLEDGE_INDEX_DIR),
        ("file_vault_index", FILE_VAULT_INDEX_DIR),
        ("file_organize_drafts", FILE_ORGANIZE_DRAFTS_DIR),
        ("code_contexts", CODE_CONTEXT_DIR),
        ("code_patch_plans", CODE_PATCH_PLANS_DIR),
        ("project_verification_logs", PROJECT_VERIFICATION_LOG_DIR),
        ("github_harbor_drafts", GITHUB_HARBOR_DRAFTS_DIR),
        ("model_config_drafts", MODEL_CONFIG_DRAFTS_DIR),
        ("model_key_vault", MODEL_KEY_VAULT_DIR),
        ("memory_events", MEMORY_EVENTS_DIR),
        ("terminal_logs", TERMINAL_LOG_DIR),
        ("backend_job_logs", BACKEND_JOB_LOG_DIR),
    ]
    services = [
        {"id": "fastapi", "name": "FastAPI bridge", "status": "online", "detail": "This response was served by the local backend."},
        {"id": "agentmemory", "name": "AgentMemory service", "status": "online" if await check_agentmemory() else "offline", "detail": AGENTMEMORY_URL},
        {"id": "shared-memory", "name": "Shared memory root", "status": "online" if SHARED_MEMORY_DIR.exists() else "missing", "detail": str(SHARED_MEMORY_DIR)},
        {"id": "knowledge-base", "name": "Knowledge base root", "status": "online" if KNOWLEDGE_BASE_DIR.exists() else "missing", "detail": str(KNOWLEDGE_BASE_DIR)},
        {"id": "research-root", "name": "Research root", "status": "online" if RESEARCH_ROOT.exists() else "missing", "detail": str(RESEARCH_ROOT)},
        {"id": "devtools", "name": "Devtools root", "status": "online" if DEVTOOLS_DIR.exists() else "missing", "detail": str(DEVTOOLS_DIR)},
        {"id": "building-registry", "name": "Building registry", "status": "online" if buildings else "missing", "detail": str(BUILDING_REGISTRY_PATH)},
        {"id": "agent-registry", "name": "Agent registry", "status": "online" if agents else "missing", "detail": str(AGENT_REGISTRY_PATH)},
        {"id": "district-registry", "name": "District registry", "status": "online" if DISTRICT_REGISTRY_PATH.exists() else "missing", "detail": str(DISTRICT_REGISTRY_PATH)},
        {"id": "model-profiles", "name": "Model profile registry", "status": "online" if MODEL_PROFILE_REGISTRY_PATH.exists() else "fallback", "detail": str(MODEL_PROFILE_REGISTRY_PATH)},
        {"id": "workspace-registry", "name": "Workspace registry", "status": "online" if WORKSPACE_REGISTRY_PATH.exists() else "fallback", "detail": str(WORKSPACE_REGISTRY_PATH)},
        {"id": "quest-registry", "name": "Quest registry", "status": "online" if QUEST_REGISTRY_PATH.exists() else "fallback", "detail": str(QUEST_REGISTRY_PATH)},
        {"id": "room-scene-registry", "name": "Room scene registry", "status": "online" if ROOM_SCENE_REGISTRY_PATH.exists() else "fallback", "detail": str(ROOM_SCENE_REGISTRY_PATH)},
        {"id": "map-decor-registry", "name": "Map decor registry", "status": "online" if MAP_DECOR_REGISTRY_PATH.exists() else "fallback", "detail": str(MAP_DECOR_REGISTRY_PATH)},
        {"id": "plugin-manifest-registry", "name": "Plugin manifest registry", "status": "online" if PLUGIN_MANIFEST_REGISTRY_PATH.exists() else "missing", "detail": str(PLUGIN_MANIFEST_REGISTRY_PATH)},
        {"id": "agent-task-queue", "name": "Agent task queue", "status": "online", "detail": f"{agent_task_snapshot().get('count', 0)} in-memory task(s); logs at {AGENT_TASK_LOG_DIR}"},
        {"id": "agent-tool-queue", "name": "Agent tool queue", "status": "online", "detail": f"{agent_tool_invocation_snapshot().get('count', 0)} tool invocation(s); logs at {AGENT_TOOL_LOG_DIR}"},
        {"id": "knowledge-index", "name": "Knowledge index cache", "status": "online" if KNOWLEDGE_INDEX_CACHE_PATH.exists() else "empty", "detail": str(KNOWLEDGE_INDEX_CACHE_PATH)},
        {"id": "file-vault-index", "name": "File Vault index cache", "status": "online" if FILE_VAULT_INDEX_CACHE_PATH.exists() else "empty", "detail": str(FILE_VAULT_INDEX_CACHE_PATH)},
        {"id": "file-organize-drafts", "name": "File organize proposals", "status": "online" if FILE_ORGANIZE_DRAFTS_DIR.exists() else "empty", "detail": str(FILE_ORGANIZE_DRAFTS_DIR)},
        {"id": "code-contexts", "name": "Code context packs", "status": "online" if CODE_CONTEXT_DIR.exists() else "empty", "detail": str(CODE_CONTEXT_DIR)},
        {"id": "code-patch-plans", "name": "Code patch plans", "status": "online" if CODE_PATCH_PLANS_DIR.exists() else "empty", "detail": str(CODE_PATCH_PLANS_DIR)},
        {"id": "github-harbor-drafts", "name": "GitHub Harbor drafts", "status": "online" if GITHUB_HARBOR_DRAFTS_DIR.exists() else "empty", "detail": str(GITHUB_HARBOR_DRAFTS_DIR)},
    ]
    warnings = []
    for service in services:
        if service["status"] != "online":
            warnings.append(f"{service['name']} is {service['status']}")
    if jobs["counts"].get("failed", 0):
        warnings.append(f"{jobs['counts']['failed']} backend job(s) failed recently.")
    if registry_health.get("status") != "ok":
        warnings.append(
            f"Registry Health is {registry_health.get('status')} with "
            f"{registry_health.get('error_count', 0)} error(s) and "
            f"{registry_health.get('warning_count', 0)} warning(s)."
        )
    event_timeline = system_event_timeline(limit=8)
    return {
        "name": "System Monitor",
        "mode": "read-only",
        "generated_at": time.time(),
        "services": services,
        "warnings": warnings,
        "jobs": jobs,
        "persistent_job_logs": latest_backend_job_logs(8),
        "registry_health": registry_health,
        "event_timeline": {
            "count": event_timeline.get("count", 0),
            "counts": event_timeline.get("counts", {}),
            "recent": event_timeline.get("events", []),
            "endpoint": "/api/system/events",
        },
        "workspace": [folder_status(name, path) for name, path in workspace_paths],
        "recent_terminal_logs": latest_terminal_logs(6),
        "registries": {
            "buildings": len(buildings),
            "agents": len(agents),
            "model_profiles": len(load_model_profiles()),
            "workspaces": len(load_workspace_registry()),
            "quests": len(load_quest_registry()),
            "districts": len(load_json_registry(DISTRICT_REGISTRY_PATH)),
        },
        "environment": {
            "deepseek_key_configured": bool(DEEPSEEK_API_KEY),
            "deepseek_base_url": DEEPSEEK_BASE_URL,
            "project_root": str(PROJECT_ROOT),
        },
    }


def execute_terminal_command(command_id: str) -> dict:
    spec = TERMINAL_COMMANDS.get(command_id)
    if not spec:
        return {"status": "missing", "command_id": command_id}
    cwd = Path(spec["cwd"]).resolve()
    if not path_is_inside(cwd, PROJECT_ROOT):
        return {"status": "blocked", "command_id": command_id, "error": "Command cwd is outside the AI Town project allowlist."}
    started = time.time()
    completed = None
    result = {
        "status": "running",
        "command_id": command_id,
        "label": spec["label"],
        "args": spec["args"],
        "cwd": str(cwd),
        "timeout": spec["timeout"],
        "safety": "confirm-required-allowlisted",
    }
    try:
        proc = subprocess.run(
            spec["args"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=spec["timeout"],
            shell=False,
        )
        completed = time.time()
        result.update({
            "status": "done" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "stdout": proc.stdout[-6000:],
            "stderr": proc.stderr[-4000:],
            "duration_seconds": round(completed - started, 3),
        })
    except subprocess.TimeoutExpired as exc:
        completed = time.time()
        result.update({
            "status": "failed",
            "returncode": None,
            "stdout": (exc.stdout or "")[-6000:] if isinstance(exc.stdout, str) else "",
            "stderr": "Command timed out.",
            "duration_seconds": round(completed - started, 3),
        })
    except Exception as exc:
        completed = time.time()
        result.update({
            "status": "failed",
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "duration_seconds": round(completed - started, 3),
        })
    TERMINAL_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_name = f"{time.strftime('%Y%m%d-%H%M%S')}-{slugify_filename(command_id)}.json"
    log_path = TERMINAL_LOG_DIR / log_name
    result["log_path"] = str(log_path)
    result["completed_at"] = completed
    log_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    record_memory_event(
        f"Terminal command completed: {spec['label']}",
        f"Allowlisted command `{command_id}` completed with status `{result['status']}` and return code `{result.get('returncode')}`.\n\nLog: `{log_path}`",
        "ai-town/terminal-control",
    )
    return result


def limited_markdown_scan(root: Path, limit: int = MAX_SCAN_ITEMS) -> list[Path]:
    """Bound expensive recursive scans so the game UI never stalls on huge folders."""
    if not root.exists():
        return []
    try:
        return list(islice(root.rglob("*.md"), limit))
    except Exception:
        return []


KNOWLEDGE_EXTENSIONS = {".md", ".txt", ".rst", ".adoc", ".tex", ".bib", ".json", ".yaml", ".yml"}
KNOWLEDGE_IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".godot",
    ".import",
    "exports",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
}


def knowledge_roots() -> list[dict]:
    roots = [
        {
            "id": "knowledgebase",
            "name": "Knowledgebase",
            "path": KNOWLEDGE_BASE_DIR,
            "role": "shared knowledge base, Codex skills, notes, and memory-adjacent documents",
        },
        {
            "id": "shared-memory",
            "name": "Shared Memory",
            "path": SHARED_MEMORY_DIR,
            "role": "cross-agent memory shelves and decisions",
        },
        {
            "id": "ai-town-docs",
            "name": "AI Town Docs",
            "path": PROJECT_ROOT / "docs",
            "role": "active rebuild architecture, visual, and audit docs",
        },
        {
            "id": "ai-town-root",
            "name": "AI Town Root Docs",
            "path": PROJECT_ROOT,
            "role": "project root Markdown and configuration notes",
            "max_depth": 1,
        },
        {
            "id": "agent-resources",
            "name": "Agent Resources",
            "path": Path(r"D:\agent-resources"),
            "role": "skills, workflows, and local agent resource docs",
        },
    ]
    return roots


def knowledge_root(root_id: str) -> Optional[dict]:
    return next((root for root in knowledge_roots() if root["id"] == root_id), None)


def knowledge_doc_id(path: Path) -> str:
    return hashlib.sha1(str(path.resolve()).encode("utf-8", errors="ignore")).hexdigest()[:16]


def should_ignore_knowledge_dir(path: Path) -> bool:
    return path.name in KNOWLEDGE_IGNORE_DIRS or path.name.startswith(".cache")


def bounded_knowledge_paths(root: Path, limit: int = 320, max_depth: int = 4) -> list[Path]:
    if not root.exists():
        return []
    paths: list[Path] = []
    if root.is_file():
        return [root] if root.suffix.lower() in KNOWLEDGE_EXTENSIONS else []
    try:
        for current, dirs, files in os.walk(root):
            current_path = Path(current)
            dirs[:] = [item for item in dirs if not should_ignore_knowledge_dir(current_path / item)]
            try:
                depth = len(current_path.relative_to(root).parts)
            except Exception:
                depth = 0
            if depth > max_depth:
                dirs[:] = []
                continue
            for filename in sorted(files):
                path = current_path / filename
                if path.suffix.lower() not in KNOWLEDGE_EXTENSIONS:
                    continue
                paths.append(path)
                if len(paths) >= limit:
                    return paths
    except Exception:
        return paths
    return paths


def load_knowledge_cache() -> dict:
    global KNOWLEDGE_DOC_CACHE
    if not KNOWLEDGE_INDEX_CACHE_PATH.exists():
        KNOWLEDGE_DOC_CACHE = {}
        return {"generated_at": 0, "roots": [], "documents": []}
    try:
        data = json.loads(KNOWLEDGE_INDEX_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        KNOWLEDGE_DOC_CACHE = {}
        return {"generated_at": 0, "roots": [], "documents": []}
    docs = data.get("documents", []) if isinstance(data, dict) else []
    KNOWLEDGE_DOC_CACHE = {
        str(doc.get("id", "")): doc
        for doc in docs
        if isinstance(doc, dict) and doc.get("id")
    }
    return data if isinstance(data, dict) else {"generated_at": 0, "roots": [], "documents": []}


def save_knowledge_cache(data: dict) -> None:
    global KNOWLEDGE_DOC_CACHE
    KNOWLEDGE_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_INDEX_CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    KNOWLEDGE_DOC_CACHE = {
        str(doc.get("id", "")): doc
        for doc in data.get("documents", [])
        if isinstance(doc, dict) and doc.get("id")
    }


def knowledge_document_entry(path: Path, root_entry: dict) -> Optional[dict]:
    try:
        stat = path.stat()
    except Exception:
        return None
    try:
        relative_path = str(path.relative_to(Path(root_entry["path"])))
    except Exception:
        relative_path = path.name
    preview_lines = first_meaningful_lines(path, 4)
    preview = redact_secret_text("\n".join(preview_lines), 420)
    return {
        "id": knowledge_doc_id(path),
        "root_id": root_entry.get("id", ""),
        "root_name": root_entry.get("name", ""),
        "name": path.name,
        "title": first_markdown_heading(path),
        "path": str(path),
        "relative_path": relative_path,
        "suffix": path.suffix.lower(),
        "bytes": stat.st_size,
        "mtime": stat.st_mtime,
        "preview": preview,
    }


def build_knowledge_index(root_id: str = "all", per_root_limit: int = 320) -> dict:
    selected_roots = knowledge_roots() if root_id in {"", "all"} else [root for root in knowledge_roots() if root["id"] == root_id]
    root_summaries = []
    documents = []
    for root_entry in selected_roots:
        root_path = Path(root_entry["path"])
        max_depth = int(root_entry.get("max_depth", 4))
        paths = bounded_knowledge_paths(root_path, per_root_limit, max_depth)
        entries = []
        for path in paths:
            entry = knowledge_document_entry(path, root_entry)
            if entry:
                entries.append(entry)
        documents.extend(entries)
        root_summaries.append({
            "id": root_entry.get("id", ""),
            "name": root_entry.get("name", ""),
            "path": str(root_path),
            "exists": root_path.exists(),
            "role": root_entry.get("role", ""),
            "indexed_count": len(entries),
            "limit": per_root_limit,
            "max_depth": max_depth,
        })
    data = {
        "status": "ok",
        "mode": "allowlisted-incremental-cache",
        "generated_at": time.time(),
        "cache_path": str(KNOWLEDGE_INDEX_CACHE_PATH),
        "roots": root_summaries,
        "root_count": len(root_summaries),
        "documents": documents,
        "document_count": len(documents),
        "extensions": sorted(KNOWLEDGE_EXTENSIONS),
        "ignore_dirs": sorted(KNOWLEDGE_IGNORE_DIRS),
        "safe_note": "Knowledge index scans only allowlisted roots with depth, extension, and per-root limits. It writes a project-local cache and never starts experiments, parses large PDFs, or scans whole drives.",
    }
    save_knowledge_cache(data)
    return data


def knowledge_index_overview() -> dict:
    data = load_knowledge_cache()
    if not data.get("documents"):
        roots = []
        for root in knowledge_roots():
            path = Path(root["path"])
            roots.append({
                "id": root.get("id", ""),
                "name": root.get("name", ""),
                "path": str(path),
                "exists": path.exists(),
                "role": root.get("role", ""),
                "indexed_count": 0,
                "limit": 320,
                "max_depth": int(root.get("max_depth", 4)),
            })
        data = {
            "mode": "allowlisted-incremental-cache",
            "generated_at": 0,
            "cache_path": str(KNOWLEDGE_INDEX_CACHE_PATH),
            "roots": roots,
            "root_count": len(roots),
            "documents": [],
            "document_count": 0,
            "extensions": sorted(KNOWLEDGE_EXTENSIONS),
            "ignore_dirs": sorted(KNOWLEDGE_IGNORE_DIRS),
            "safe_note": "Knowledge index cache is empty. Use POST /api/knowledge/index-job to refresh it asynchronously.",
        }
    return {
        "status": "ok",
        "mode": data.get("mode", "allowlisted-incremental-cache"),
        "generated_at": data.get("generated_at", 0),
        "cache_path": data.get("cache_path", str(KNOWLEDGE_INDEX_CACHE_PATH)),
        "roots": data.get("roots", []),
        "root_count": data.get("root_count", 0),
        "document_count": data.get("document_count", len(data.get("documents", []))),
        "extensions": data.get("extensions", sorted(KNOWLEDGE_EXTENSIONS)),
        "ignore_dirs": data.get("ignore_dirs", sorted(KNOWLEDGE_IGNORE_DIRS)),
        "safe_note": data.get("safe_note", ""),
    }


def knowledge_search(q: str = "", root_id: str = "all", page: int = 1, page_size: int = 10) -> dict:
    query = (q or "").strip().lower()
    data = load_knowledge_cache()
    docs = data.get("documents", [])
    if root_id not in {"", "all"}:
        docs = [doc for doc in docs if doc.get("root_id") == root_id]
    results = []
    for doc in docs:
        haystack = " ".join([
            str(doc.get("title", "")),
            str(doc.get("name", "")),
            str(doc.get("relative_path", "")),
            str(doc.get("preview", "")),
            str(doc.get("root_name", "")),
        ]).lower()
        if query and query not in haystack:
            continue
        score = 0
        if query:
            if query in str(doc.get("title", "")).lower():
                score += 4
            if query in str(doc.get("relative_path", "")).lower():
                score += 2
            if query in str(doc.get("preview", "")).lower():
                score += 1
        result = dict(doc)
        result["score"] = score
        results.append(result)
    results = sorted(results, key=lambda item: (item.get("score", 0), item.get("mtime", 0)), reverse=True)
    page = max(1, page)
    page_size = max(1, min(page_size, 30))
    start = (page - 1) * page_size
    return {
        "status": "ok",
        "query": q,
        "root_id": root_id or "all",
        "page": page,
        "page_size": page_size,
        "total": len(results),
        "results": results[start:start + page_size],
        "cache_generated_at": data.get("generated_at", 0),
        "cache_path": data.get("cache_path", str(KNOWLEDGE_INDEX_CACHE_PATH)),
        "mode": "cached-allowlisted-search",
        "cache_ready": bool(data.get("documents")),
    }


def knowledge_item(doc_id: str) -> dict:
    data = load_knowledge_cache()
    doc = KNOWLEDGE_DOC_CACHE.get(doc_id)
    if not doc:
        return {"status": "missing", "doc_id": doc_id}
    path = Path(str(doc.get("path", "")))
    root_entry = knowledge_root(str(doc.get("root_id", "")))
    if not root_entry or not path.exists() or not path_is_inside(path.resolve(), Path(root_entry["path"]).resolve()):
        return {"status": "blocked", "doc_id": doc_id, "message": "Document is outside the allowlisted knowledge root."}
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        return {"status": "failed", "doc_id": doc_id, "error": str(exc)}
    return {
        "status": "ok",
        "document": doc,
        "preview": redact_secret_text(text, MEMORY_PREVIEW_CHARS),
        "truncated": len(text) > MEMORY_PREVIEW_CHARS,
        "bytes": len(text.encode("utf-8", errors="ignore")),
        "mode": "bounded-preview",
    }


def first_markdown_heading(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("#"):
                return line.strip("# ").strip()
    except Exception:
        pass
    return path.stem


def first_meaningful_lines(path: Path, limit: int = 5) -> list[str]:
    lines = []
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped or stripped in {"---"} or stripped.startswith(("title:", "date:", "tags:")):
                continue
            lines.append(redact_secret_text(stripped, 1200))
            if len(lines) >= limit:
                break
    except Exception as exc:
        return [f"read error: {exc}"]
    return lines


def bounded_child_listing(root: Path, limit: int = 16) -> list[dict]:
    if not root.exists() or not root.is_dir():
        return []
    try:
        children = sorted(islice(root.iterdir(), limit), key=lambda p: (not p.is_dir(), p.name.lower()))
    except Exception:
        return []
    return [
        {
            "name": child.name,
            "kind": "dir" if child.is_dir() else "file",
            "path": str(child),
        }
        for child in children
    ]


def file_vault_root(root_id: str) -> Optional[dict]:
    return next((root for root in file_vault_workspace_roots() if root["id"] == root_id), None)


def safe_vault_target(root_id: str, relative_path: str = "") -> Optional[Path]:
    root_entry = file_vault_root(root_id)
    if not root_entry:
        return None
    root = Path(root_entry["path"]).resolve()
    rel = (relative_path or "").replace("\\", "/").strip("/")
    if rel.startswith("..") or "/.." in rel:
        return None
    target = (root / rel).resolve()
    if not path_is_inside(target, root):
        return None
    return target


def file_vault_roots() -> dict:
    roots = []
    for item in file_vault_workspace_roots():
        root = Path(item["path"])
        entry = {
            "id": item["id"],
            "name": item["name"],
            "path": str(root),
            "exists": root.exists(),
            "kind": "dir" if root.is_dir() else "file" if root.is_file() else "missing",
            "workspace_kind": item.get("kind", "workspace"),
            "role": item.get("role", ""),
            "safety": item.get("safety", "allowlisted-lazy-read"),
        }
        if root.exists() and root.is_dir():
            try:
                children = sorted(islice(root.iterdir(), 80), key=lambda p: (not p.is_dir(), p.name.lower()))
                entry["sample_count"] = len(children)
                entry["sample"] = [{"name": child.name, "kind": "dir" if child.is_dir() else "file"} for child in children[:16]]
            except Exception as exc:
                entry["error"] = str(exc)
        roots.append(entry)
    index = file_vault_index_overview()
    return {
        "name": "File Vault",
        "mode": "read-only-whitelist-lazy",
        "registry": str(WORKSPACE_REGISTRY_PATH),
        "registry_exists": WORKSPACE_REGISTRY_PATH.exists(),
        "roots": roots,
        "count": len(roots),
        "index": index,
        "organize_audit": file_vault_organize_audit(),
        "organize_proposals": markdown_draft_entries(FILE_ORGANIZE_DRAFTS_DIR, "file-organize-proposal", 8),
        "safe_note": "File Vault reads allowlisted roots from the workspace registry and uses lazy, bounded directory listing.",
    }


def file_vault_listing(root_id: str, relative_path: str = "", offset: int = 0, limit: int = 40) -> Optional[dict]:
    root_entry = file_vault_root(root_id)
    target = safe_vault_target(root_id, relative_path)
    if not root_entry or not target or not target.exists() or not target.is_dir():
        return None
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    try:
        children = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except Exception as exc:
        return {
            "status": "error",
            "root_id": root_id,
            "relative_path": relative_path,
            "error": str(exc),
            "items": [],
            "count": 0,
        }
    page = children[offset:offset + limit]
    items = []
    root_path = Path(root_entry["path"]).resolve()
    for child in page:
        try:
            rel = child.resolve().relative_to(root_path)
            stat = child.stat()
            items.append({
                "name": child.name,
                "kind": "dir" if child.is_dir() else "file",
                "relative_path": str(rel).replace("\\", "/"),
                "bytes": 0 if child.is_dir() else stat.st_size,
                "updated": stat.st_mtime,
                "previewable": child.is_file() and child.suffix.lower() in FILE_PREVIEW_EXTENSIONS and stat.st_size <= FILE_PREVIEW_MAX_BYTES,
            })
        except Exception:
            continue
    rel_parent = ""
    if relative_path:
        parts = Path(relative_path.replace("\\", "/")).parts
        rel_parent = "/".join(parts[:-1])
    return {
        "status": "ok",
        "root_id": root_id,
        "root_name": root_entry["name"],
        "root_path": str(root_path),
        "relative_path": (relative_path or "").replace("\\", "/").strip("/"),
        "parent_relative_path": rel_parent,
        "items": items,
        "count": len(children),
        "offset": offset,
        "limit": limit,
        "has_more": offset + limit < len(children),
        "mode": "read-only-lazy",
    }


def file_vault_preview(root_id: str, relative_path: str) -> Optional[dict]:
    root_entry = file_vault_root(root_id)
    target = safe_vault_target(root_id, relative_path)
    if not root_entry or not target or not target.exists() or not target.is_file():
        return None
    stat = target.stat()
    suffix = target.suffix.lower()
    if suffix not in FILE_PREVIEW_EXTENSIONS or stat.st_size > FILE_PREVIEW_MAX_BYTES:
        return {
            "status": "blocked",
            "root_id": root_id,
            "relative_path": relative_path,
            "reason": "Only small text-like files are previewable.",
            "bytes": stat.st_size,
            "extension": suffix,
        }
    text = target.read_text(encoding="utf-8", errors="ignore")
    root_path = Path(root_entry["path"]).resolve()
    return {
        "status": "ok",
        "root_id": root_id,
        "root_name": root_entry["name"],
        "root_path": str(root_path),
        "relative_path": str(target.resolve().relative_to(root_path)).replace("\\", "/"),
        "name": target.name,
        "bytes": stat.st_size,
        "updated": stat.st_mtime,
        "preview": redact_secret_text(text, FILE_PREVIEW_CHARS),
        "preview_chars": min(len(text), FILE_PREVIEW_CHARS),
        "truncated": len(text) > FILE_PREVIEW_CHARS,
        "mode": "read-only-preview",
    }


FILE_VAULT_IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".godot",
    ".import",
    "exports",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
}


def file_vault_item_id(root_id: str, relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/")
    raw = f"{root_id}:{normalized}"
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]


def file_organize_group_for(path: str, kind: str) -> str:
    if kind == "dir":
        lower_name = Path(path).name.lower()
        if any(token in lower_name for token in ["archive", "old", "backup", "bak"]):
            return "archives"
        if any(token in lower_name for token in ["doc", "paper", "note", "readme"]):
            return "docs"
        if any(token in lower_name for token in ["src", "code", "script", "tool"]):
            return "code"
        if any(token in lower_name for token in ["data", "dataset", "csv", "json"]):
            return "data"
        if any(token in lower_name for token in ["asset", "image", "art", "audio", "video"]):
            return "assets"
        return "review"
    suffix = Path(path).suffix.lower()
    if suffix in {".md", ".txt", ".rst", ".doc", ".docx", ".pdf", ".tex"}:
        return "docs"
    if suffix in {".py", ".js", ".ts", ".tsx", ".gd", ".cs", ".rs", ".go", ".java", ".sh", ".ps1", ".bat", ".cmd"}:
        return "code"
    if suffix in {".csv", ".json", ".jsonl", ".yaml", ".yml", ".xml", ".parquet", ".xlsx", ".db", ".sqlite"}:
        return "data"
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".mp3", ".wav", ".mp4", ".blend", ".aseprite"}:
        return "assets"
    if suffix in {".zip", ".7z", ".rar", ".tar", ".gz", ".bak"}:
        return "archives"
    return "review"


def file_organize_preview_lines(groups: dict[str, list[dict]], limit: int = 14) -> list[str]:
    lines = []
    emitted = 0
    for group_name in ["docs", "code", "data", "assets", "archives", "review"]:
        entries = groups.get(group_name, [])
        if not entries:
            continue
        lines.append(f"- {group_name}: {len(entries)} item(s)")
        emitted += 1
        for entry in entries[:3]:
            lines.append(f"  - {entry.get('kind', '')}: {entry.get('relative_path', entry.get('name', ''))}")
            emitted += 1
            if emitted >= limit:
                return lines
    return lines


def should_ignore_file_vault_dir(path: Path, root_entry: Optional[dict] = None) -> bool:
    ignore_dirs = set(FILE_VAULT_IGNORE_DIRS)
    if root_entry:
        ignore_dirs.update(str(item) for item in root_entry.get("ignore_dirs", []) if str(item))
    return path.name in ignore_dirs or path.name.startswith(".cache")


def load_file_tags() -> dict:
    if not FILE_VAULT_TAGS_PATH.exists():
        return {}
    try:
        data = json.loads(FILE_VAULT_TAGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save_file_tags(tags: dict) -> None:
    FILE_VAULT_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    FILE_VAULT_TAGS_PATH.write_text(json.dumps(tags, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def load_file_vault_cache() -> dict:
    global FILE_VAULT_ITEM_CACHE
    if not FILE_VAULT_INDEX_CACHE_PATH.exists():
        FILE_VAULT_ITEM_CACHE = {}
        return {"generated_at": 0, "roots": [], "items": []}
    try:
        data = json.loads(FILE_VAULT_INDEX_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        FILE_VAULT_ITEM_CACHE = {}
        return {"generated_at": 0, "roots": [], "items": []}
    items = data.get("items", []) if isinstance(data, dict) else []
    FILE_VAULT_ITEM_CACHE = {
        str(item.get("id", "")): item
        for item in items
        if isinstance(item, dict) and item.get("id")
    }
    return data if isinstance(data, dict) else {"generated_at": 0, "roots": [], "items": []}


def save_file_vault_cache(data: dict) -> None:
    global FILE_VAULT_ITEM_CACHE
    FILE_VAULT_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    FILE_VAULT_INDEX_CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    FILE_VAULT_ITEM_CACHE = {
        str(item.get("id", "")): item
        for item in data.get("items", [])
        if isinstance(item, dict) and item.get("id")
    }


def file_vault_index_item(path: Path, root_entry: dict, tags: dict) -> Optional[dict]:
    try:
        root_path = Path(root_entry["path"]).resolve()
        resolved = path.resolve()
        relative = str(resolved.relative_to(root_path)).replace("\\", "/")
        stat = path.stat()
    except Exception:
        return None
    item_id = file_vault_item_id(str(root_entry.get("id", "")), relative)
    suffix = path.suffix.lower() if path.is_file() else ""
    tag_entry = tags.get(item_id, {})
    return {
        "id": item_id,
        "root_id": root_entry.get("id", ""),
        "root_name": root_entry.get("name", ""),
        "name": path.name,
        "kind": "dir" if path.is_dir() else "file",
        "relative_path": relative,
        "suffix": suffix,
        "bytes": 0 if path.is_dir() else stat.st_size,
        "mtime": stat.st_mtime,
        "previewable": path.is_file() and suffix in FILE_PREVIEW_EXTENSIONS and stat.st_size <= FILE_PREVIEW_MAX_BYTES,
        "tags": tag_entry.get("tags", []),
        "tag_note": tag_entry.get("note", ""),
    }


def file_vault_index_item_changed(previous: dict, current: dict) -> bool:
    for key in ["root_id", "relative_path", "kind", "suffix", "bytes", "mtime", "previewable"]:
        if previous.get(key) != current.get(key):
            return True
    return False


def build_file_vault_index(root_id: str = "all", per_root_limit: int = 120, max_depth: int = 2) -> dict:
    previous_data = load_file_vault_cache()
    previous_items = [
        item for item in previous_data.get("items", [])
        if isinstance(item, dict) and item.get("id")
    ]
    previous_by_id = {str(item.get("id")): item for item in previous_items}
    roots = file_vault_workspace_roots()
    if root_id not in {"", "all"}:
        roots = [root for root in roots if root.get("id") == root_id]
    target_root_ids = {str(root.get("id", "")) for root in roots}
    tags = load_file_tags()
    root_summaries = []
    indexed_items = []
    new_count = 0
    changed_count = 0
    reused_count = 0
    for root_entry in roots:
        root_path = Path(root_entry["path"])
        entries = []
        if root_path.exists():
            try:
                for current, dirs, files in os.walk(root_path):
                    current_path = Path(current)
                    dirs[:] = [item for item in dirs if not should_ignore_file_vault_dir(current_path / item, root_entry)]
                    try:
                        depth = len(current_path.relative_to(root_path).parts)
                    except Exception:
                        depth = 0
                    if depth > max_depth:
                        dirs[:] = []
                        continue
                    children = [current_path / name for name in sorted(dirs + files)]
                    for child in children:
                        entry = file_vault_index_item(child, root_entry, tags)
                        if entry:
                            previous = previous_by_id.get(str(entry.get("id", "")))
                            if not previous:
                                new_count += 1
                            elif file_vault_index_item_changed(previous, entry):
                                changed_count += 1
                            else:
                                reused_count += 1
                            entries.append(entry)
                            if len(entries) >= per_root_limit:
                                break
                    if len(entries) >= per_root_limit:
                        break
            except Exception:
                pass
        indexed_items.extend(entries)
        root_summaries.append({
            "id": root_entry.get("id", ""),
            "name": root_entry.get("name", ""),
            "path": str(root_path),
            "exists": root_path.exists(),
            "indexed_count": len(entries),
            "limit": per_root_limit,
            "max_depth": max_depth,
            "ignore_dirs": sorted(set(FILE_VAULT_IGNORE_DIRS).union(set(root_entry.get("ignore_dirs", [])))),
        })
    indexed_ids = {str(item.get("id", "")) for item in indexed_items if item.get("id")}
    removed_count = len([
        item for item in previous_items
        if str(item.get("root_id", "")) in target_root_ids and str(item.get("id", "")) not in indexed_ids
    ])
    preserved_items = [
        item for item in previous_items
        if root_id not in {"", "all"} and str(item.get("root_id", "")) not in target_root_ids
    ]
    items = preserved_items + indexed_items
    previous_root_summaries = [
        root for root in previous_data.get("roots", [])
        if isinstance(root, dict) and str(root.get("id", "")) not in target_root_ids
    ] if root_id not in {"", "all"} else []
    incremental_summary = {
        "strategy": "mtime-size-id-diff",
        "refreshed_root_id": root_id or "all",
        "target_root_count": len(target_root_ids),
        "previous_item_count": len(previous_items),
        "new_count": new_count,
        "changed_count": changed_count,
        "reused_count": reused_count,
        "removed_count": removed_count,
        "preserved_count": len(preserved_items),
    }
    data = {
        "status": "ok",
        "mode": "allowlisted-incremental-file-index-cache",
        "generated_at": time.time(),
        "cache_path": str(FILE_VAULT_INDEX_CACHE_PATH),
        "tag_path": str(FILE_VAULT_TAGS_PATH),
        "roots": previous_root_summaries + root_summaries,
        "root_count": len(previous_root_summaries) + len(root_summaries),
        "items": items,
        "item_count": len(items),
        "ignore_dirs": sorted(FILE_VAULT_IGNORE_DIRS),
        "incremental_summary": incremental_summary,
        "safe_note": "File Vault index scans only workspace-registry allowlisted roots with depth and per-root limits, then incrementally compares item ids, mtimes, and sizes against the previous cache. Tags are stored in AI Town workspace only; source files are not modified.",
    }
    save_file_vault_cache(data)
    return data


def file_vault_index_overview() -> dict:
    data = load_file_vault_cache()
    if not data.get("items"):
        roots = []
        for root in file_vault_workspace_roots():
            path = Path(root["path"])
            roots.append({
                "id": root.get("id", ""),
                "name": root.get("name", ""),
                "path": str(path),
                "exists": path.exists(),
                "indexed_count": 0,
                "limit": 120,
                "max_depth": 2,
            })
        data = {
            "mode": "allowlisted-incremental-file-index-cache",
            "generated_at": 0,
            "cache_path": str(FILE_VAULT_INDEX_CACHE_PATH),
            "tag_path": str(FILE_VAULT_TAGS_PATH),
            "roots": roots,
            "root_count": len(roots),
            "items": [],
            "item_count": 0,
            "ignore_dirs": sorted(FILE_VAULT_IGNORE_DIRS),
            "incremental_summary": {
                "strategy": "mtime-size-id-diff",
                "previous_item_count": 0,
                "new_count": 0,
                "changed_count": 0,
                "reused_count": 0,
                "removed_count": 0,
                "preserved_count": 0,
            },
            "safe_note": "File Vault index cache is empty. Use POST /api/file-vault/index-job to refresh it asynchronously.",
        }
    mode = data.get("mode", "allowlisted-incremental-file-index-cache")
    if mode == "allowlisted-file-index-cache":
        mode = "allowlisted-incremental-file-index-cache"
    incremental_summary = data.get("incremental_summary", {})
    if not incremental_summary:
        incremental_summary = {
            "strategy": "mtime-size-id-diff",
            "previous_item_count": data.get("item_count", len(data.get("items", []))),
            "new_count": 0,
            "changed_count": 0,
            "reused_count": data.get("item_count", len(data.get("items", []))),
            "removed_count": 0,
            "preserved_count": 0,
            "legacy_cache": True,
        }
    return {
        "status": "ok",
        "mode": mode,
        "generated_at": data.get("generated_at", 0),
        "cache_path": data.get("cache_path", str(FILE_VAULT_INDEX_CACHE_PATH)),
        "tag_path": data.get("tag_path", str(FILE_VAULT_TAGS_PATH)),
        "roots": data.get("roots", []),
        "root_count": data.get("root_count", 0),
        "item_count": data.get("item_count", len(data.get("items", []))),
        "ignore_dirs": data.get("ignore_dirs", sorted(FILE_VAULT_IGNORE_DIRS)),
        "incremental_summary": incremental_summary,
        "safe_note": data.get("safe_note", ""),
    }


def sorted_count_entries(counts: dict[str, int], limit: int = 12) -> list[dict]:
    return [
        {"id": key, "count": value}
        for key, value in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def file_vault_organize_audit() -> dict:
    data = load_file_vault_cache()
    items = [item for item in data.get("items", []) if isinstance(item, dict)]
    tags = load_file_tags()
    indexed_ids = {str(item.get("id", "")) for item in items if item.get("id")}
    if not items:
        return {
            "status": "index-missing",
            "mode": "cached-file-organization-audit",
            "source": "file-vault-cache",
            "cache_ready": False,
            "cache_path": str(FILE_VAULT_INDEX_CACHE_PATH),
            "tag_path": str(FILE_VAULT_TAGS_PATH),
            "item_count": 0,
            "group_counts": [],
            "root_counts": [],
            "extension_counts": [],
            "review_items": [],
            "large_files": [],
            "duplicate_names": [],
            "stale_tags": [
                {"id": tag_id, "root_id": entry.get("root_id", ""), "relative_path": entry.get("relative_path", "")}
                for tag_id, entry in list(tags.items())[:12]
                if tag_id not in indexed_ids and isinstance(entry, dict)
            ],
            "safe_note": "Organization audit reads only the cached File Vault index and tag ledger. Refresh the index to audit current allowlisted roots.",
        }

    group_counts: dict[str, int] = {}
    root_counts: dict[str, int] = {}
    extension_counts: dict[str, int] = {}
    name_buckets: dict[str, list[dict]] = {}
    review_items: list[dict] = []
    large_files: list[dict] = []
    tagged_count = 0
    previewable_count = 0

    for item in items:
        root_id = str(item.get("root_id", ""))
        relative = str(item.get("relative_path", ""))
        kind = str(item.get("kind", ""))
        group = file_organize_group_for(relative or str(item.get("name", "")), kind)
        group_counts[group] = group_counts.get(group, 0) + 1
        root_counts[root_id] = root_counts.get(root_id, 0) + 1
        suffix = str(item.get("suffix", "") or ("<dir>" if kind == "dir" else "<none>")).lower()
        extension_counts[suffix] = extension_counts.get(suffix, 0) + 1
        if item.get("tags"):
            tagged_count += 1
        if item.get("previewable"):
            previewable_count += 1
        if group == "review" and len(review_items) < 16:
            review_items.append({
                "root_id": root_id,
                "relative_path": relative,
                "kind": kind,
                "bytes": item.get("bytes", 0),
            })
        if kind == "file" and int(item.get("bytes", 0) or 0) >= 50_000_000 and len(large_files) < 12:
            large_files.append({
                "root_id": root_id,
                "relative_path": relative,
                "bytes": item.get("bytes", 0),
                "suffix": suffix,
            })
        name_key = str(item.get("name", "")).lower()
        if name_key:
            bucket = name_buckets.setdefault(name_key, [])
            if len(bucket) < 6:
                bucket.append({
                    "root_id": root_id,
                    "relative_path": relative,
                    "kind": kind,
                })

    duplicate_names = [
        {"name": name, "count": len(bucket), "items": bucket}
        for name, bucket in sorted(name_buckets.items())
        if len(bucket) > 1
    ][:12]
    stale_tags = [
        {"id": tag_id, "root_id": entry.get("root_id", ""), "relative_path": entry.get("relative_path", "")}
        for tag_id, entry in tags.items()
        if tag_id not in indexed_ids and isinstance(entry, dict)
    ][:12]
    status = "needs-review" if review_items or duplicate_names or stale_tags or large_files else "clean"
    return {
        "status": status,
        "mode": "cached-file-organization-audit",
        "source": "file-vault-cache",
        "cache_ready": True,
        "cache_generated_at": data.get("generated_at", 0),
        "cache_path": data.get("cache_path", str(FILE_VAULT_INDEX_CACHE_PATH)),
        "tag_path": str(FILE_VAULT_TAGS_PATH),
        "item_count": len(items),
        "root_count": len(root_counts),
        "tagged_count": tagged_count,
        "untagged_count": max(0, len(items) - tagged_count),
        "previewable_count": previewable_count,
        "group_counts": sorted_count_entries(group_counts),
        "root_counts": sorted_count_entries(root_counts),
        "extension_counts": sorted_count_entries(extension_counts),
        "review_items": review_items,
        "large_files": large_files,
        "duplicate_names": duplicate_names,
        "stale_tags": stale_tags,
        "draft_count": len(markdown_draft_entries(FILE_ORGANIZE_DRAFTS_DIR, "file-organize-proposal", 40)),
        "safe_next_steps": [
            "Use Organize Plan for a proposal-only draft before moving anything.",
            "Review duplicate names and stale tags against project docs before cleanup.",
            "Keep active experiment outputs, virtual environments, caches, and Git folders out of manual cleanup.",
        ],
        "safe_note": "Organization audit reads only workspace/file-vault-index cache metadata and project-local tags. It does not scan live folders, open files, move files, rename files, or delete files.",
    }


def file_vault_search(q: str = "", root_id: str = "all", kind: str = "all", page: int = 1, page_size: int = 12) -> dict:
    query = (q or "").strip().lower()
    data = load_file_vault_cache()
    items = data.get("items", [])
    if root_id not in {"", "all"}:
        items = [item for item in items if item.get("root_id") == root_id]
    if kind in {"file", "dir"}:
        items = [item for item in items if item.get("kind") == kind]
    results = []
    for item in items:
        haystack = " ".join([
            str(item.get("name", "")),
            str(item.get("relative_path", "")),
            str(item.get("root_name", "")),
            str(item.get("suffix", "")),
            " ".join(item.get("tags", [])),
            str(item.get("tag_note", "")),
        ]).lower()
        if query and query not in haystack:
            continue
        score = 0
        if query:
            if query in str(item.get("name", "")).lower():
                score += 4
            if query in str(item.get("relative_path", "")).lower():
                score += 2
            if query in " ".join(item.get("tags", [])).lower():
                score += 3
        result = dict(item)
        result["score"] = score
        results.append(result)
    results = sorted(results, key=lambda item: (item.get("score", 0), item.get("mtime", 0)), reverse=True)
    page = max(1, page)
    page_size = max(1, min(page_size, 40))
    start = (page - 1) * page_size
    return {
        "status": "ok",
        "query": q,
        "root_id": root_id or "all",
        "kind": kind,
        "page": page,
        "page_size": page_size,
        "total": len(results),
        "results": results[start:start + page_size],
        "cache_ready": bool(data.get("items")),
        "cache_generated_at": data.get("generated_at", 0),
        "cache_path": data.get("cache_path", str(FILE_VAULT_INDEX_CACHE_PATH)),
        "mode": "cached-allowlisted-file-search",
    }


def tag_file_vault_item(req: FileTagRequest) -> dict:
    target = safe_vault_target(req.root_id, req.path)
    root_entry = file_vault_root(req.root_id)
    if not root_entry or not target or not target.exists():
        return {"status": "missing", "root_id": req.root_id, "relative_path": req.path}
    root_path = Path(root_entry["path"]).resolve()
    relative = str(target.resolve().relative_to(root_path)).replace("\\", "/")
    item_id = file_vault_item_id(req.root_id, relative)
    tag = slugify_filename(req.tag.strip() or "review")
    tags = load_file_tags()
    entry = tags.get(item_id, {
        "id": item_id,
        "root_id": req.root_id,
        "relative_path": relative,
        "path": str(target),
        "tags": [],
        "created_at": time.time(),
    })
    if tag not in entry["tags"]:
        entry["tags"].append(tag)
    entry["note"] = req.note.strip()[:500]
    entry["updated_at"] = time.time()
    tags[item_id] = entry
    save_file_tags(tags)
    record_memory_event(
        f"File Vault tag added: {tag}",
        f"Tagged `{req.root_id}/{relative}` with `{tag}` in the AI Town File Vault tag ledger. Source file was not modified.\n\nNote: {entry.get('note', '')}",
        "ai-town/file-vault",
    )
    return {
        "status": "saved",
        "safety": "project-local-tag-ledger-only",
        "item": entry,
        "tag_path": str(FILE_VAULT_TAGS_PATH),
    }


def open_file_vault_item(req: FileOpenRequest) -> dict:
    target = safe_vault_target(req.root_id, req.path)
    root_entry = file_vault_root(req.root_id)
    if not root_entry or not target or not target.exists():
        return {"status": "missing", "root_id": req.root_id, "relative_path": req.path}

    root_path = Path(root_entry["path"]).resolve()
    relative = "" if target.resolve() == root_path else str(target.resolve().relative_to(root_path)).replace("\\", "/")
    mode = (req.mode or "reveal").strip().lower()
    if mode not in {"reveal", "open"}:
        mode = "reveal"
    action = "open-folder" if target.is_dir() else "reveal-file"
    command_preview = ["explorer", str(target)]
    if target.is_file():
        command_preview = ["explorer", f"/select,{target}"]
        if mode == "open":
            action = "open-file"
            command_preview = ["os.startfile", str(target)]

    launched = False
    error = ""
    if not req.dry_run:
        try:
            if target.is_file() and mode == "open":
                if not hasattr(os, "startfile"):
                    raise RuntimeError("os.startfile is unavailable on this platform")
                os.startfile(str(target))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(command_preview, cwd=str(root_path))
            launched = True
        except Exception as exc:
            error = str(exc)

    status = "dry-run" if req.dry_run else ("opened" if launched else "failed")
    memory = record_memory_event(
        f"File Vault item {status}: {action}",
        f"{status} `{req.root_id}/{relative}` from `{req.source_building}` using `{action}`. Target stayed inside allowlisted root `{root_path}`. No file contents were modified.",
        "ai-town/file-vault",
    )
    return {
        "status": status,
        "safety": "allowlisted-local-open-no-file-mutation",
        "root_id": req.root_id,
        "root_name": root_entry.get("name", req.root_id),
        "relative_path": relative,
        "target_path": str(target),
        "opened_path": str(target),
        "kind": "dir" if target.is_dir() else "file",
        "open_action": action,
        "mode": mode,
        "dry_run": req.dry_run,
        "launched": launched,
        "command_preview": " ".join(command_preview),
        "error": error,
        "memory_event": memory,
    }


def create_file_organize_proposal(req: FileOrganizeProposalRequest) -> dict:
    root_entry = file_vault_root(req.root_id)
    target = safe_vault_target(req.root_id, req.path)
    if not root_entry or not target or not target.exists():
        return {"status": "missing", "root_id": req.root_id, "relative_path": req.path}

    root_path = Path(root_entry["path"]).resolve()
    relative = "" if target.resolve() == root_path else str(target.resolve().relative_to(root_path)).replace("\\", "/")
    sampled_items: list[dict] = []
    preview_text = ""
    if target.is_dir():
        listing = file_vault_listing(req.root_id, relative, 0, 30)
        sampled_items = listing.get("items", []) if listing else []
    else:
        stat = target.stat()
        sampled_items = [{
            "name": target.name,
            "kind": "file",
            "relative_path": relative,
            "bytes": stat.st_size,
            "updated": stat.st_mtime,
            "previewable": target.suffix.lower() in FILE_PREVIEW_EXTENSIONS and stat.st_size <= FILE_PREVIEW_MAX_BYTES,
        }]
        preview = file_vault_preview(req.root_id, relative)
        if preview and preview.get("status") == "ok":
            preview_text = str(preview.get("preview", ""))[:1200]

    groups: dict[str, list[dict]] = {}
    for item in sampled_items:
        item_path = str(item.get("relative_path", item.get("name", "")))
        group = file_organize_group_for(item_path, str(item.get("kind", "")))
        groups.setdefault(group, []).append(item)

    title = req.title.strip() or "AI Town file organization proposal"
    strategy = slugify_filename(req.strategy or "review-and-group")
    source = req.source_building.strip() or "file-vault"
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    FILE_ORGANIZE_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    proposal_path = FILE_ORGANIZE_DRAFTS_DIR / f"{timestamp}-{req.root_id}-{strategy}-{slugify_filename(title)}.md"
    target_kind = "dir" if target.is_dir() else "file"
    target_stat = target.stat()
    preview_lines = file_organize_preview_lines(groups)
    content = "\n".join([
        "---",
        f"title: {title}",
        f"source: ai-town/{source}",
        f"root_id: {req.root_id}",
        f"path: {relative}",
        f"strategy: {strategy}",
        "status: draft",
        "safety: file-organization-proposal-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Safety Boundary",
        "",
        "- This proposal did not move, delete, rename, copy, overwrite, or open source files.",
        "- Any future file operation must be reviewed separately with explicit confirmation.",
        "- Suggested groups are heuristic and based on a bounded sample only.",
        "",
        "## Current Location",
        "",
        f"- Root: {root_entry.get('name', req.root_id)} (`{req.root_id}`)",
        f"- Root path: `{root_path}`",
        f"- Selected path: `/{relative}`",
        f"- Kind: {target_kind}",
        f"- Bytes: {0 if target.is_dir() else target_stat.st_size}",
        "",
        "## Suggested Groups",
        "",
        *(preview_lines or ["- review: no sampled children found"]),
        "",
        "## Sampled Items",
        "",
        *[
            "- {kind} `{path}` bytes={bytes}".format(
                kind=item.get("kind", ""),
                path=item.get("relative_path", item.get("name", "")),
                bytes=item.get("bytes", 0),
            )
            for item in sampled_items[:30]
        ],
        "",
        "## Risks And Review Notes",
        "",
        "- Confirm duplicate names, generated caches, and active experiment outputs before any future move.",
        "- Keep `.git`, virtual environments, build outputs, and running experiment folders out of manual cleanup unless project docs say otherwise.",
        "- Prefer creating a new staging folder or manifest before touching important D-drive research, code, or memory roots.",
        "",
        "## Confirmation Checklist",
        "",
        "- [ ] User reviewed this plan in File Vault.",
        "- [ ] Exact source and destination paths are listed for any future operation.",
        "- [ ] Backup or Git status is checked where relevant.",
        "- [ ] No running experiment, API proxy, or service depends on the target path.",
        "",
        "## Optional File Preview",
        "",
        preview_text if preview_text else "_No text preview included for this target._",
    ])
    proposal_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"File organize proposal created: {title}",
        f"Created proposal-only File Vault organization draft at `{proposal_path}` for `{req.root_id}/{relative}`. No source files were modified.",
        "ai-town/file-vault",
    )
    return {
        "status": "saved",
        "safety": "file-organization-proposal-only",
        "proposal_path": str(proposal_path),
        "memory_event": memory,
        "target": {
            "root_id": req.root_id,
            "root_name": root_entry.get("name", ""),
            "root_path": str(root_path),
            "relative_path": relative,
            "kind": target_kind,
            "sample_count": len(sampled_items),
        },
        "groups": {key: len(value) for key, value in groups.items()},
        "preview": "\n".join(preview_lines[:12]) if preview_lines else "No sampled children found.",
    }


def experiment_candidates(root: Path, limit: int = 18) -> list[dict]:
    """Find likely experiment entry points without deep, unbounded traversal."""
    if not root.exists():
        return []
    patterns = [
        "README.md",
        "readme.md",
        "run*.py",
        "train*.py",
        "eval*.py",
        "experiment*.py",
        "scripts/*.py",
        "scripts/*.sh",
        "experiments/*.py",
        "configs/*",
        "results/*",
    ]
    seen = set()
    candidates = []
    for pattern in patterns:
        try:
            matches = sorted(root.glob(pattern), key=lambda p: str(p).lower())
        except Exception:
            continue
        for match in matches:
            key = str(match)
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                "name": match.name,
                "kind": "dir" if match.is_dir() else "file",
                "path": key,
                "relative_path": str(match.relative_to(root)) if match.is_relative_to(root) else key,
            })
            if len(candidates) >= limit:
                return candidates
    return candidates


def research_status_docs(project: dict, include_excerpt: bool = False) -> list[dict]:
    docs = []
    for path in project.get("status_files", []):
        entry = {
            "name": path.name,
            "path": str(path),
            "exists": path.exists(),
        }
        if path.exists():
            entry["title"] = first_markdown_heading(path)
            if include_excerpt:
                entry["excerpt"] = first_meaningful_lines(path)
        docs.append(entry)
    return docs


def research_project_card(project: dict) -> dict:
    local_dirs = []
    for root in project.get("local_dirs", []):
        local_dirs.append({
            "path": str(root),
            "exists": root.exists(),
            "sample": bounded_child_listing(root, 8),
        })
    status_docs = research_status_docs(project)
    return {
        "id": project["id"],
        "name": project["name"],
        "theme": project["theme"],
        "priority": project["priority"],
        "local_dirs": local_dirs,
        "status_docs": status_docs,
        "status_count": len([doc for doc in status_docs if doc.get("exists")]),
        "server": project.get("server", ""),
        "next_action": project.get("next_action", ""),
        "exists": any(item["exists"] for item in local_dirs),
    }


def all_research_project_cards() -> list[dict]:
    return [research_project_card(project) for project in sorted(RESEARCH_PROJECTS, key=lambda item: item["priority"])]


def research_project_detail(project_id: str) -> Optional[dict]:
    project = next((item for item in RESEARCH_PROJECTS if item["id"] == project_id), None)
    if not project:
        return None
    detail = research_project_card(project)
    detail["status_docs"] = research_status_docs(project, include_excerpt=True)
    detail["experiment_entries"] = []
    for root in project.get("local_dirs", []):
        detail["experiment_entries"].append({
            "root": str(root),
            "exists": root.exists(),
            "candidates": experiment_candidates(root),
        })
    detail["safe_actions"] = [
        {
            "id": "open-status-doc",
            "label": "Read status document in-game",
            "safety": "read-only",
        },
        {
            "id": "prepare-research-log",
            "label": "Prepare project-local research log draft",
            "safety": "preview-only",
        },
        {
            "id": "plan-experiment",
            "label": "Convert candidates into an ARIS experiment quest",
            "safety": "planning-only",
        },
    ]
    return detail


def create_research_log_draft(project_id: str, req: ResearchLogDraftRequest) -> Optional[dict]:
    detail = research_project_detail(project_id)
    if not detail:
        return None
    safe_project_id = slugify_filename(project_id or "research-project")
    title = req.title.strip() or f"Research log for {detail.get('name', safe_project_id)}"
    focus = slugify_filename(req.focus or "next-safe-action")
    body = req.body.strip() or "Capture current project evidence, risks, and next safe action from AI Town Research Hall."
    source = req.source_building.strip() or "research-hall"
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    RESEARCH_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = RESEARCH_LOGS_DIR / f"{timestamp}-{safe_project_id}-{focus}-{slugify_filename(title)}.md"
    status_docs = [doc for doc in detail.get("status_docs", []) if isinstance(doc, dict)]
    experiment_roots = [root for root in detail.get("experiment_entries", []) if isinstance(root, dict)]
    candidate_count = sum(len(root.get("candidates", [])) for root in experiment_roots)
    lines = [
        "---",
        f"title: {title}",
        f"project_id: {safe_project_id}",
        f"project_name: {detail.get('name', safe_project_id)}",
        f"focus: {focus}",
        f"source: ai-town/{source}",
        "status: draft",
        "safety: project-local-research-log-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Project Snapshot",
        "",
        f"- Project: {detail.get('name', safe_project_id)} (`{safe_project_id}`)",
        f"- Theme: {detail.get('theme', '')}",
        f"- Priority: P{detail.get('priority', '?')}",
        f"- Server: {detail.get('server', '')}",
        f"- Exists locally: {detail.get('exists', False)}",
        f"- Next recorded action: {detail.get('next_action', '')}",
        "",
        "## User Note",
        "",
        body,
        "",
        "## Local Directories",
        "",
    ]
    for root in detail.get("local_dirs", []):
        if isinstance(root, dict):
            lines.append(f"- `{root.get('path', '')}` | exists={root.get('exists', False)}")
    lines.extend([
        "",
        "## Evidence Snapshot",
        "",
        f"- Status docs sampled: {len(status_docs)}",
        f"- Experiment entry candidates sampled: {candidate_count}",
        "",
        "### Status Docs",
        "",
    ])
    for doc in status_docs[:5]:
        lines.append(f"- `{doc.get('path', doc.get('name', 'doc'))}` | exists={doc.get('exists', False)}")
        for excerpt in doc.get("excerpt", [])[:4]:
            lines.append(f"  - {excerpt}")
    lines.extend([
        "",
        "### Experiment Entry Candidates",
        "",
    ])
    for root in experiment_roots[:4]:
        lines.append(f"- Root: `{root.get('root', '')}` | exists={root.get('exists', False)}")
        for candidate in root.get("candidates", [])[:8]:
            if isinstance(candidate, dict):
                lines.append(f"  - {candidate.get('relative_path', candidate.get('name', 'candidate'))} [{candidate.get('kind', 'unknown')}]")
    lines.extend([
        "",
        "## Safety Checklist",
        "",
        "- This draft was written only under the AI Town project workspace.",
        "- This action did not run experiments, contact servers, mutate datasets, or edit research repositories.",
        "- Treat this as a working log until a human or ARIS audit promotes claims into project documentation.",
        "",
        "## Next Safe Actions",
        "",
        "- Read the latest status document in-game before changing experiment plans.",
        "- Queue a Research Agent `research-brief` task when a cross-check is needed.",
        "- Create a Research Data Center note if dataset, result, schema, or metric provenance is unclear.",
    ])
    content = "\n".join(lines)
    log_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Research log drafted: {title}",
        f"Created project-local Research Hall log for `{safe_project_id}`.\n\nLog: `{log_path}`",
        "ai-town/research-hall",
    )
    return {
        "status": "created",
        "project_id": safe_project_id,
        "project_name": detail.get("name", safe_project_id),
        "log_path": str(log_path),
        "memory_event": memory,
        "preview": content[:2400],
        "safety": "project-local-research-log-only",
    }


def agent_launcher_entry(agent_id: str, agent: dict) -> dict:
    launcher_names = {
        "opus": ["cc.cmd", "claude.cmd"],
        "pixelcat": ["pixelcat.cmd"],
        "codex": ["codex.cmd"],
        "deepseek": ["deepseek.cmd"],
        "sonnet": ["claude.cmd"],
        "haiku": ["claude.cmd"],
        "aris": ["aris.cmd"],
    }
    candidates = [DEVTOOLS_DIR / name for name in launcher_names.get(agent_id, [f"{agent_id}.cmd"])]
    existing = next((path for path in candidates if path.exists()), None)
    return {
        "id": agent_id,
        "name": agent.get("name", agent_id),
        "role": agent.get("role", ""),
        "zone": agent.get("zone", ""),
        "launcher": str(existing) if existing else "",
        "launcher_exists": existing is not None,
        "candidate_launchers": [str(path) for path in candidates],
        "dispatch_mode": "draft-only",
    }


def redact_secret_text(value: str, limit: int = 2400) -> str:
    text = value or ""
    text = re.sub(
        r"(?im)^(\s*(?:set\s+)?[\"']?[^=\r\n]*(?:API[_-]?KEY|AUTH[_-]?TOKEN|ACCESS[_-]?TOKEN|SECRET|PASSWORD|PRIVATE[_-]?KEY)[^=\r\n]*\s*=\s*)([^\r\n\"']+)([\"']?)",
        r"\1[redacted-secret]\3",
        text,
    )
    text = re.sub(r"(?i)\b(sk-[A-Za-z0-9_\-]{12,})", "[redacted-openai-key]", text)
    text = re.sub(r"(?i)\b(gh[pousr]_[A-Za-z0-9_]{12,})", "[redacted-github-token]", text)
    text = re.sub(r"(?i)\b(xox[baprs]-[A-Za-z0-9\-]{12,})", "[redacted-slack-token]", text)
    text = re.sub(r"(https?://)([^/@\s]+)@([^/\s]+)", r"\1[redacted]@\3", text)
    return text[:limit]


def agent_runner_readiness_entry(agent_id: str, agent: dict) -> dict:
    launcher = agent_launcher_entry(agent_id, agent)
    launcher_path = Path(launcher["launcher"]) if launcher.get("launcher") else None
    preview = ""
    launcher_hash = ""
    launcher_bytes = 0
    launcher_updated = 0.0
    if launcher_path and launcher_path.exists() and path_is_inside(launcher_path, DEVTOOLS_DIR):
        try:
            raw = launcher_path.read_bytes()
            launcher_hash = hashlib.sha256(raw).hexdigest()
            launcher_bytes = launcher_path.stat().st_size
            launcher_updated = launcher_path.stat().st_mtime
            preview = redact_secret_text(raw[:1600].decode("utf-8", errors="replace"), 900)
        except Exception as exc:
            preview = f"launcher preview unavailable: {exc}"
    handoff_dir_exists = AGENT_RUNNER_DISPATCH_DIR.exists()
    ready = bool(launcher.get("launcher_exists")) and DEVTOOLS_DIR.exists()
    blockers = []
    if not DEVTOOLS_DIR.exists():
        blockers.append(f"Devtools directory missing: {DEVTOOLS_DIR}")
    if not launcher.get("launcher_exists"):
        blockers.append("No known launcher file exists for this agent.")
    return {
        **launcher,
        "runner_ready": ready,
        "readiness": "ready-for-confirmed-handoff" if ready else "launcher-missing",
        "blockers": blockers,
        "launcher_sha256": launcher_hash,
        "launcher_bytes": launcher_bytes,
        "launcher_updated": launcher_updated,
        "launcher_preview": preview,
        "handoff_dir": str(AGENT_RUNNER_DISPATCH_DIR),
        "handoff_dir_exists": handoff_dir_exists,
        "supported_handoff_modes": ["project-local-dispatch-file", "manual-copy"],
        "command_template": "\"{launcher}\"",
        "permission_gate": "future-confirm-required-agent-runner",
        "safe_note": "Readiness inspects launcher files and builds dispatch previews only. It does not start, stop, or kill agent processes.",
    }


def agent_runner_readiness() -> dict:
    runners = [
        agent_runner_readiness_entry(agent_id, agent)
        for agent_id, agent in AGENT_PERSONALITIES.items()
    ]
    return {
        "status": "ok",
        "mode": "read-only-agent-runner-readiness",
        "devtools": str(DEVTOOLS_DIR),
        "devtools_exists": DEVTOOLS_DIR.exists(),
        "handoff_dir": str(AGENT_RUNNER_DISPATCH_DIR),
        "runner_count": len(runners),
        "ready_count": len([runner for runner in runners if runner.get("runner_ready")]),
        "runners": runners,
        "safe_note": "This is a preflight view for real agent runners. It reads launcher metadata and never starts, stops, kills, or contacts external agent runners.",
    }


def create_agent_runner_dispatch_preview(req: AgentRunnerDispatchPreviewRequest) -> dict:
    target = req.target_agent.strip().lower() or "codex"
    if target not in AGENT_PERSONALITIES:
        target = "codex"
    title = req.task_title.strip() or "AI Town runner handoff"
    body = req.task_body.strip() or "Review the current AI Town rebuild state and propose the next safe implementation slice."
    runner = agent_runner_readiness_entry(target, AGENT_PERSONALITIES[target])
    now = time.time()
    dispatch_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{slugify_filename(target)}-{uuid.uuid4().hex[:8]}"
    AGENT_RUNNER_DISPATCH_DIR.mkdir(parents=True, exist_ok=True)
    markdown_path = AGENT_RUNNER_DISPATCH_DIR / f"{dispatch_id}.md"
    json_path = AGENT_RUNNER_DISPATCH_DIR / f"{dispatch_id}.json"
    launcher = str(runner.get("launcher", ""))
    command_preview = f"\"{launcher}\"" if launcher else ""
    content = "\n".join([
        "---",
        f"title: {title}",
        f"target_agent: {target}",
        f"source: ai-town/{req.source_building.strip() or 'agent-hub'}",
        "status: dispatch-preview",
        "safety: confirm-required-agent-runner-preview",
        f"created_at: {now}",
        "---",
        "",
        f"# {title}",
        "",
        f"Target agent: {target}",
        f"Runner readiness: {runner.get('readiness', '')}",
        f"Launcher: {launcher}",
        f"Command preview: {command_preview}",
        "",
        "## Task",
        "",
        body,
        "",
        "## Safety Gate",
        "",
        "- This dispatch preview did not start an external agent runner.",
        "- Review launcher, working directory, task body, and permissions before any future confirmed run.",
        "- Do not use this preview to stop, kill, overwrite, install, push, or commit without a separate explicit workflow.",
        "",
        "## Launcher Preview",
        "",
        "```cmd",
        str(runner.get("launcher_preview", ""))[:1200],
        "```",
    ])
    preview = {
        "id": dispatch_id,
        "status": "preview-saved",
        "mode": "confirm-required-agent-runner-preview",
        "target_agent": target,
        "title": title,
        "runner_ready": bool(runner.get("runner_ready")),
        "readiness": runner.get("readiness", ""),
        "blockers": runner.get("blockers", []),
        "launcher": launcher,
        "launcher_sha256": runner.get("launcher_sha256", ""),
        "command_preview": command_preview,
        "handoff_path": str(markdown_path),
        "json_path": str(json_path),
        "dry_run": True,
        "source_building": req.source_building.strip() or "agent-hub",
        "created_at": now,
        "safe_note": "Preview saved only. No external agent runner, command, service, Git operation, or API call was started.",
    }
    markdown_path.write_text(content, encoding="utf-8")
    preview["bytes"] = markdown_path.stat().st_size
    preview["preview"] = content[:2600]
    json_path.write_text(json.dumps(preview, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    record_memory_event(
        f"Agent runner dispatch preview: {title}",
        f"AI Town prepared a confirm-required dispatch preview for {target}. Launcher ready={preview['runner_ready']}. Handoff: {markdown_path}",
        "agent-runner-dispatch-preview",
    )
    return preview


def resolve_runner_handoff_path(raw_path: str) -> Optional[Path]:
    if not raw_path:
        return None
    try:
        path = Path(raw_path).resolve()
    except Exception:
        return None
    if not path.exists() or not path_is_inside(path, AGENT_RUNNER_DISPATCH_DIR):
        return None
    if path.suffix.lower() not in {".md", ".json"}:
        return None
    return path


def run_agent_runner_command(launcher: Path, handoff_path: Path, target_agent: str) -> dict:
    argv = [str(launcher), str(handoff_path)]
    started = time.time()
    completed = subprocess.run(
        argv,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        encoding="utf-8",
        errors="replace",
    )
    stdout = redact_secret_text(completed.stdout or "", 12000)
    stderr = redact_secret_text(completed.stderr or "", 12000)
    log = {
        "id": uuid.uuid4().hex[:12],
        "target_agent": target_agent,
        "launcher": str(launcher),
        "handoff_path": str(handoff_path),
        "argv": argv,
        "returncode": completed.returncode,
        "duration_seconds": round(time.time() - started, 3),
        "stdout": stdout,
        "stderr": stderr,
        "safety": "confirm-required-agent-runner",
        "rollback_note": "AI Town only started the configured launcher with one handoff file argument. It did not kill existing processes, mutate Git, install packages, or stop services.",
    }
    AGENT_RUNNER_DISPATCH_DIR.mkdir(parents=True, exist_ok=True)
    log_path = AGENT_RUNNER_DISPATCH_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}-{slugify_filename(target_agent)}-runner-result-{log['id']}.json"
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    record_memory_event(
        f"Agent runner launch job completed: {target_agent}",
        f"Confirmed runner launch for `{target_agent}` returned {completed.returncode}. Log: {log_path}",
        "agent-runner-launch-job",
    )
    return {
        "summary": f"{target_agent} runner returned {completed.returncode}",
        "returncode": completed.returncode,
        "log_path": str(log_path),
        "stdout_preview": stdout[:1200],
        "stderr_preview": stderr[:1200],
    }


def create_agent_runner_launch_job(req: AgentRunnerLaunchJobRequest) -> dict:
    target = req.target_agent.strip().lower() or "codex"
    if target not in AGENT_PERSONALITIES:
        target = "codex"
    runner = agent_runner_readiness_entry(target, AGENT_PERSONALITIES[target])
    handoff_path = resolve_runner_handoff_path(req.handoff_path)
    launcher_path = Path(runner.get("launcher", "")).resolve() if runner.get("launcher") else None
    command = {
        "target_agent": target,
        "launcher": str(launcher_path) if launcher_path else "",
        "handoff_path": str(handoff_path) if handoff_path else "",
        "argv": [str(launcher_path), str(handoff_path)] if launcher_path and handoff_path else [],
        "cwd": str(PROJECT_ROOT),
        "timeout_seconds": 120,
    }
    base = {
        "status": "confirmation-required",
        "mode": "confirm-required-agent-runner-launch",
        "confirmation_required": CONFIRM_RUN_AGENT_RUNNER,
        "runner_ready": bool(runner.get("runner_ready")),
        "readiness": runner.get("readiness", ""),
        "blockers": runner.get("blockers", []),
        "command": command,
        "safe_note": "Launching external agent runners is disabled unless the exact confirmation phrase is supplied. Dry-run and missing-confirmation requests do not start any process.",
    }
    if not launcher_path or not launcher_path.exists() or not path_is_inside(launcher_path, DEVTOOLS_DIR):
        base["status"] = "blocked"
        base["blockers"] = list(base["blockers"]) + ["Launcher missing or outside D:\\devtools."]
        return base
    if not handoff_path:
        base["status"] = "blocked"
        base["blockers"] = list(base["blockers"]) + ["Handoff path is missing, outside workspace\\agent-runner-dispatches, or not a .md/.json file."]
        return base
    if req.dry_run or req.confirmation != CONFIRM_RUN_AGENT_RUNNER:
        return base
    job = start_job(
        "agent-runner-launch",
        f"Run {target} agent launcher with dispatch handoff",
        run_agent_runner_command,
        launcher_path,
        handoff_path,
        target,
    )
    job["cancelable"] = False
    job["rollback_note"] = "External runner launch was explicitly confirmed. AI Town will not kill existing unrelated processes; review runner logs for any follow-up cleanup."
    return {
        "status": "queued",
        "mode": "confirm-required-agent-runner-launch",
        "job_id": job["id"],
        "target_agent": target,
        "command": command,
        "confirmation_used": CONFIRM_RUN_AGENT_RUNNER,
        "safe_note": "Confirmed launch job queued. AI Town started only its own backend job wrapper and will not stop unrelated processes or services.",
    }


def agent_companion_cards() -> list[dict]:
    registry = load_json_registry(AGENT_REGISTRY_PATH)
    by_id = {str(item.get("id", "")): item for item in registry if isinstance(item, dict)}
    tool_hints = {
        "codex": ["project-index", "system-snapshot", "file-search"],
        "opus": ["system-snapshot", "project-index"],
        "sonnet": ["memory-index", "knowledge-search"],
        "pixelcat": ["project-index", "file-search"],
        "haiku": ["system-snapshot"],
        "deepseek": ["knowledge-search", "file-search"],
        "aris": ["knowledge-search", "memory-index"],
    }
    cards = []
    for agent_id, agent in AGENT_PERSONALITIES.items():
        registry_item = by_id.get(agent_id, {})
        launcher = agent_launcher_entry(agent_id, agent)
        cards.append({
            "id": agent_id,
            "name": agent.get("name", agent_id),
            "display_name": registry_item.get("display_name", agent.get("name", agent_id)),
            "role": agent.get("role", ""),
            "zone": agent.get("zone", ""),
            "agent_kind": registry_item.get("agent_kind", "real-agent"),
            "sheet": registry_item.get("sheet", ""),
            "launcher_exists": launcher.get("launcher_exists", False),
            "launcher": launcher.get("launcher", ""),
            "tool_hints": tool_hints.get(agent_id, []),
            "starting_affinity": 1,
            "safety": "local-player-companion-only",
        })
    return cards


def agent_mailbox_entries() -> list[dict]:
    entries = []
    if AGENT_HUB_STATE_DIR.exists():
        for path in sorted(AGENT_HUB_STATE_DIR.glob("messages-*.json"), key=lambda item: item.name.lower()):
            try:
                entries.append({
                    "agent": path.stem.replace("messages-", ""),
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "updated": path.stat().st_mtime,
                    "exists": True,
                })
            except Exception:
                pass
    return entries


def agent_log_entries() -> list[dict]:
    logs = []
    log_dir = DEVTOOLS_DIR / "logs"
    if log_dir.exists():
        for path in sorted(log_dir.glob("*.log"), key=lambda item: item.stat().st_mtime, reverse=True)[:12]:
            try:
                logs.append({
                    "name": path.name,
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "updated": path.stat().st_mtime,
                })
            except Exception:
                pass
    return logs


def agent_hub_overview() -> dict:
    roster = [
        agent_launcher_entry(agent_id, agent)
        for agent_id, agent in AGENT_PERSONALITIES.items()
    ]
    runner_readiness = agent_runner_readiness()
    mailboxes = agent_mailbox_entries()
    logs = agent_log_entries()
    task_queue = agent_task_snapshot()
    tool_queue = agent_tool_invocation_snapshot()
    chat_sessions = agent_chat_sessions(limit=10)
    return {
        "name": "Agent Hub",
        "devtools": str(DEVTOOLS_DIR),
        "devtools_exists": DEVTOOLS_DIR.exists(),
        "hub_path": str(AGENT_HUB_DIR),
        "hub_exists": AGENT_HUB_DIR.exists(),
        "state_path": str(AGENT_HUB_STATE_DIR),
        "state_exists": AGENT_HUB_STATE_DIR.exists(),
        "roster": roster,
        "runner_readiness": runner_readiness,
        "runner_ready_count": runner_readiness.get("ready_count", 0),
        "runner_handoff_dir": str(AGENT_RUNNER_DISPATCH_DIR),
        "companions": agent_companion_cards(),
        "companion_count": len(agent_companion_cards()),
        "agent_count": len(roster),
        "launcher_count": len([item for item in roster if item.get("launcher_exists")]),
        "mailboxes": mailboxes,
        "mailbox_count": len(mailboxes),
        "logs": logs,
        "log_count": len(logs),
        "chat_sessions": chat_sessions,
        "chat_count": len(chat_sessions),
        "chat_dir": str(AGENT_CHAT_DIR),
        "task_queue": task_queue,
        "task_count": task_queue["count"],
        "task_log_dir": str(AGENT_TASK_LOG_DIR),
        "task_logs": latest_agent_task_logs(6),
        "tool_queue": tool_queue,
        "tool_count": tool_queue["count"],
        "tool_log_dir": str(AGENT_TOOL_LOG_DIR),
        "tool_logs": latest_agent_tool_logs(6),
        "dispatch_mode": "project-local-draft-plus-runner-preview",
        "safe_note": "Agent Hub does not start, stop, or kill external agent processes. Dispatch creates drafts and confirm-required runner previews; Agent Chat records local sessions; Agent Tasks and Agent Tools run bounded local safe adapters only. Companions are saved locally in the Godot player profile.",
    }


def create_agent_dispatch_draft(req: AgentDispatchDraftRequest) -> dict:
    target = req.target_agent.strip().lower() or "codex"
    if target not in AGENT_PERSONALITIES:
        target = "codex"
    title = req.task_title.strip() or "AI Town follow-up task"
    filename = f"{slugify_filename(target)}-{slugify_filename(title)}.md"
    AGENT_DISPATCH_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    target_path = AGENT_DISPATCH_DRAFTS_DIR / filename
    content = "\n".join([
        "---",
        f"title: {title}",
        f"target_agent: {target}",
        f"source: ai-town/{req.source_building}",
        "status: draft",
        "safety: project-local-draft",
        "---",
        "",
        f"# {title}",
        "",
        f"Target agent: {target}",
        "",
        "## Task",
        "",
        req.task_body.strip() or "Review the current AI Town rebuild state and propose the next safe implementation slice.",
        "",
        "## Safety",
        "",
        "- This is a draft only. It was not sent to an external agent runner.",
        "- Review before copying into Agent Hub, Codex, Claude Code, or any command runner.",
    ])
    target_path.write_text(content, encoding="utf-8")
    return {
        "status": "saved",
        "safety": "project-local-write",
        "target_agent": target,
        "target_path": str(target_path),
        "bytes": target_path.stat().st_size,
        "preview": content,
    }


def agent_chat_path(session_id: str) -> Path:
    safe_id = slugify_filename(session_id)[:80] or "chat"
    return AGENT_CHAT_DIR / f"{safe_id}.json"


def save_agent_chat(session: dict) -> dict:
    AGENT_CHAT_DIR.mkdir(parents=True, exist_ok=True)
    path = agent_chat_path(str(session.get("id", "")))
    session["path"] = str(path)
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return session


def load_agent_chat(session_id: str) -> Optional[dict]:
    path = agent_chat_path(session_id)
    if not path.exists() or not path_is_inside(path, AGENT_CHAT_DIR):
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    data["path"] = str(path)
    return data


def agent_chat_summary(session: dict) -> dict:
    messages = session.get("messages", [])
    return {
        "id": session.get("id", ""),
        "title": session.get("title", ""),
        "agent_id": session.get("agent_id", ""),
        "agent_name": AGENT_PERSONALITIES.get(session.get("agent_id", ""), {}).get("name", session.get("agent_id", "")),
        "source_building": session.get("source_building", ""),
        "message_count": len(messages) if isinstance(messages, list) else 0,
        "created_at": session.get("created_at", 0),
        "updated_at": session.get("updated_at", 0),
        "path": session.get("path", ""),
        "last_message": messages[-1].get("content", "")[:180] if isinstance(messages, list) and messages else "",
    }


def agent_chat_sessions(limit: int = 20) -> list[dict]:
    if not AGENT_CHAT_DIR.exists():
        return []
    sessions = []
    try:
        files = sorted(AGENT_CHAT_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    except Exception:
        return []
    for path in files[:limit]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data["path"] = str(path)
                sessions.append(agent_chat_summary(data))
        except Exception:
            pass
    return sessions


def create_agent_chat_session(req: AgentChatSessionRequest) -> dict:
    agent_id = req.agent_id.strip().lower() or "codex"
    if agent_id not in AGENT_PERSONALITIES:
        agent_id = "codex"
    now = time.time()
    session_id = uuid.uuid4().hex[:12]
    title = req.title.strip() or f"Chat with {AGENT_PERSONALITIES[agent_id]['name']}"
    session = {
        "id": session_id,
        "title": title,
        "agent_id": agent_id,
        "source_building": req.source_building.strip() or "agent-hub",
        "context": req.context if isinstance(req.context, dict) else {},
        "created_at": now,
        "updated_at": now,
        "safety": "project-local-agent-chat-log",
        "provider": {
            "configured": bool(DEEPSEEK_API_KEY),
            "base_url": DEEPSEEK_BASE_URL,
            "mode": "local-session-log-with-safe-context",
        },
        "messages": [
            {
                "role": "system",
                "content": "Agent Chat session created. Messages are stored under AI Town workspace. Safe tools and task queues are available as explicit follow-up actions.",
                "at": now,
            }
        ],
    }
    save_agent_chat(session)
    return {
        "status": "created",
        "safety": session["safety"],
        "chat_session": agent_chat_summary(session),
        "session": session,
    }


def build_agent_chat_reply(session: dict, message: str, context: dict) -> dict:
    agent_id = session.get("agent_id", "codex")
    agent = AGENT_PERSONALITIES.get(agent_id, AGENT_PERSONALITIES["codex"])
    lower = message.lower()
    tool_suggestions = []
    if "memory" in lower or "记忆" in message:
        tool_suggestions.append("memory-index")
    if "knowledge" in lower or "search" in lower or "知识" in message or "搜索" in message:
        tool_suggestions.append("knowledge-search")
    if "file" in lower or "文件" in message:
        tool_suggestions.append("file-search")
    if "project" in lower or "code" in lower or "repo" in lower or "代码" in message:
        tool_suggestions.append("project-index")
    if "status" in lower or "system" in lower or "状态" in message:
        tool_suggestions.append("system-snapshot")
    memory = memory_index(limit_per_category=1)
    task_queue = agent_task_snapshot(limit=5)
    tool_queue = agent_tool_invocation_snapshot(limit=5)
    reply_lines = [
        f"{agent['name']} is listening from {agent.get('zone', 'Agent Hub')}.",
        f"I stored this turn in a project-local chat log and checked safe local context: {len(memory.get('categories', []))} memory shelves, {task_queue.get('count', 0)} queued/completed agent tasks, and {tool_queue.get('count', 0)} tool invocations.",
    ]
    if tool_suggestions:
        reply_lines.append("Suggested safe tools for this request: " + ", ".join(dict.fromkeys(tool_suggestions)) + ".")
    else:
        reply_lines.append("Suggested next step: choose Agent Tasks for a bounded brief, Tool Catalog for a registered tool, or Draft Dispatch for an external-runner handoff.")
    if context:
        reply_lines.append(f"Attached context keys: {', '.join(sorted(context.keys())[:8])}.")
    reply_lines.append("No external runner was started, no shell command was executed, and no source repository was modified.")
    return {
        "role": "assistant",
        "content": "\n".join(reply_lines),
        "at": time.time(),
        "agent_id": agent_id,
        "tool_suggestions": list(dict.fromkeys(tool_suggestions)),
        "context_summary": {
            "memory_shelves": len(memory.get("categories", [])),
            "agent_task_count": task_queue.get("count", 0),
            "agent_tool_invocation_count": tool_queue.get("count", 0),
            "provider_configured": bool(DEEPSEEK_API_KEY),
        },
    }


def append_agent_chat_message(session_id: str, req: AgentChatMessageRequest) -> dict:
    session = load_agent_chat(session_id)
    if not session:
        return {"status": "missing", "session_id": session_id}
    now = time.time()
    context = req.context if isinstance(req.context, dict) else {}
    user_message = {
        "role": "user",
        "content": req.message.strip() or "Summarize the current AI Town state.",
        "at": now,
        "source_building": req.source_building.strip() or "agent-hub",
        "context": context,
    }
    session.setdefault("messages", []).append(user_message)
    assistant_message = build_agent_chat_reply(session, user_message["content"], context)
    session["messages"].append(assistant_message)
    session["updated_at"] = assistant_message["at"]
    save_agent_chat(session)
    record_memory_event(
        f"Agent chat updated: {session.get('title', session_id)}",
        f"Agent `{session.get('agent_id', '')}` responded in AI Town Agent Chat.\n\nSession: `{session.get('path', '')}`\n\nSummary: {assistant_message.get('content', '')[:600]}",
        "agent-chat",
    )
    return {
        "status": "ok",
        "safety": session.get("safety", "project-local-agent-chat-log"),
        "chat_session": agent_chat_summary(session),
        "session": session,
        "message": assistant_message,
    }


def agent_task_catalog() -> list[dict]:
    return [
        {
            "id": "memory-brief",
            "name": "Memory Brief",
            "description": "Summarize shared memory categories and recent notes.",
            "safety": "read-only-local-files",
        },
        {
            "id": "project-brief",
            "name": "Project Brief",
            "description": "Inspect bounded AI Town project docs and local Git signals.",
            "safety": "read-only-local-files-plus-git-status",
        },
        {
            "id": "workspace-brief",
            "name": "Workspace Brief",
            "description": "Summarize configured workspace registry roots and availability.",
            "safety": "read-only-local-files",
        },
        {
            "id": "code-review-brief",
            "name": "Code Review Brief",
            "description": "Inspect one selected local Git repository and build a bounded development analysis brief.",
            "safety": "read-only-local-files-plus-git-status",
        },
        {
            "id": "code-explain-brief",
            "name": "Code Explain Brief",
            "description": "Explain one selected local Git repository for onboarding: purpose, entry points, key files, and reading path.",
            "safety": "read-only-local-files-plus-git-status",
        },
        {
            "id": "research-brief",
            "name": "Research Brief",
            "description": "Inspect one configured local research project and build a bounded ARIS-style next-action brief.",
            "safety": "read-only-local-files",
        },
        {
            "id": "task-brief",
            "name": "Task Brief",
            "description": "Inspect one project-local Task Board item and build a bounded execution brief.",
            "safety": "read-only-project-local-task",
        },
    ]


def prune_agent_tasks() -> None:
    if len(AGENT_TASKS) <= MAX_AGENT_TASKS:
        return
    ordered = sorted(AGENT_TASKS.items(), key=lambda item: item[1].get("created_at", 0))
    for task_id, _task in ordered[:len(AGENT_TASKS) - MAX_AGENT_TASKS]:
        AGENT_TASKS.pop(task_id, None)


def agent_task_queue_policy() -> dict:
    try:
        configured = int(os.getenv("AI_TOWN_AGENT_TASK_MAX_RUNNING", str(DEFAULT_AGENT_TASK_MAX_RUNNING)))
    except Exception:
        configured = DEFAULT_AGENT_TASK_MAX_RUNNING
    max_running = max(1, min(configured, 4))
    running_like = [
        task for task in AGENT_TASKS.values()
        if str(task.get("status", "")) in {"dispatching", "running"}
    ]
    queued = [
        task for task in AGENT_TASKS.values()
        if str(task.get("status", "")) == "queued"
    ]
    paused = [
        task for task in AGENT_TASKS.values()
        if str(task.get("status", "")) == "paused"
    ]
    return {
        "mode": "safe-local-agent-task-concurrency-policy",
        "max_running": max_running,
        "running_count": len(running_like),
        "queued_count": len(queued),
        "paused_count": len(paused),
        "available_slots": max(0, max_running - len(running_like)),
        "saturated": len(running_like) >= max_running,
        "env_var": "AI_TOWN_AGENT_TASK_MAX_RUNNING",
        "executor": "shared-ai-town-job-executor",
        "safe_note": "Only safe local read-only brief builders are scheduled by this policy. External agent runners, shell commands, repo writes, services, and remote APIs are not started.",
    }


def dispatch_agent_task(task_id: str) -> bool:
    task = AGENT_TASKS.get(task_id)
    if not task or task.get("status") != "queued":
        return False
    policy = agent_task_queue_policy()
    if int(policy.get("available_slots", 0)) <= 0:
        return False
    now = time.time()
    task["status"] = "dispatching"
    task["updated_at"] = now
    task.setdefault("events", []).append({
        "at": now,
        "message": f"Task dispatched under concurrency policy: max_running={policy.get('max_running', 1)}.",
    })
    JOB_EXECUTOR.submit(run_agent_task, task_id)
    return True


def schedule_agent_tasks() -> dict:
    dispatched = []
    while int(agent_task_queue_policy().get("available_slots", 0)) > 0:
        queued = sorted(
            [
                task for task in AGENT_TASKS.values()
                if str(task.get("status", "")) == "queued" and not task.get("cancel_requested")
            ],
            key=lambda item: item.get("created_at", 0),
        )
        if not queued:
            break
        task_id = str(queued[0].get("id", ""))
        if not task_id or not dispatch_agent_task(task_id):
            break
        dispatched.append(task_id)
    policy = agent_task_queue_policy()
    policy["dispatched"] = dispatched
    return policy


def agent_task_summary(task: dict) -> dict:
    status = str(task.get("status", ""))
    return {
        "id": task.get("id", ""),
        "target_agent": task.get("target_agent", ""),
        "task_type": task.get("task_type", ""),
        "title": task.get("title", ""),
        "status": status,
        "safety": task.get("safety", ""),
        "created_at": task.get("created_at", 0),
        "updated_at": task.get("updated_at", 0),
        "source_building": task.get("source_building", ""),
        "parameters": task.get("parameters", {}),
        "log_path": task.get("log_path", ""),
        "error": task.get("error", ""),
        "result_summary": task.get("result_summary", ""),
        "cancelable": status in {"queued", "paused", "dispatching", "running"},
        "cancel_requested": bool(task.get("cancel_requested", False)),
        "rollback_note": task.get("rollback_note", ""),
    }


def agent_task_snapshot(limit: int = 16) -> dict:
    counts: dict[str, int] = {}
    for task in AGENT_TASKS.values():
        status = str(task.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    recent = [
        agent_task_summary(task)
        for task in sorted(
            AGENT_TASKS.values(),
            key=lambda item: item.get("updated_at", item.get("created_at", 0)),
            reverse=True,
        )[:limit]
    ]
    return {
        "status": "ok",
        "mode": "safe-local-agent-task-queue",
        "count": len(AGENT_TASKS),
        "counts": counts,
        "tasks": recent,
        "catalog": agent_task_catalog(),
        "policy": agent_task_queue_policy(),
        "log_dir": str(AGENT_TASK_LOG_DIR),
        "safe_note": "Tasks run only bounded local read-only brief builders through a visible concurrency policy, write JSON logs under workspace/agent-task-logs, and never start external agent processes.",
    }


def build_agent_task_payload(task: dict) -> dict:
    task_type = task.get("task_type", "memory-brief")
    parameters = task.get("parameters", {}) if isinstance(task.get("parameters", {}), dict) else {}
    if task_type == "workspace-brief":
        overview = workspace_registry_overview()
        roots = []
        for root in overview.get("workspaces", [])[:10]:
            roots.append({
                "id": root.get("id", ""),
                "name": root.get("name", ""),
                "exists": root.get("exists", False),
                "role": root.get("role", ""),
                "path": root.get("path", ""),
            })
        return {
            "kind": "workspace-brief",
            "summary": f"{overview.get('count', 0)} workspace roots configured; registry exists={overview.get('exists', False)}.",
            "registry": overview.get("path", ""),
            "roots": roots,
        }
    if task_type == "project-brief":
        git = git_summary(PROJECT_ROOT)
        files = important_project_files(PROJECT_ROOT)
        repos = discover_git_repos(limit=5)
        return {
            "kind": "project-brief",
            "summary": f"AI Town branch {git.get('branch', '') or 'unknown'} with {git.get('dirty_count', 0)} changed entries and {len(files)} key docs.",
            "project_root": str(PROJECT_ROOT),
            "git": git,
            "important_files": files,
            "nearby_repos": repos,
        }
    if task_type == "code-review-brief":
        project_id = str(parameters.get("project_id", "")).strip()
        if not project_id:
            projects = discover_git_repos(limit=1)
            project_id = projects[0]["id"] if projects else ""
        detail = project_detail(project_id) if project_id else None
        if not detail:
            return {
                "kind": "code-review-brief",
                "summary": f"Selected project `{project_id}` was not found in the bounded project cache.",
                "project_id": project_id,
                "status": "missing",
            }
        repo = Path(detail["path"])
        file_previews = []
        for item in detail.get("important_files", [])[:8]:
            if not isinstance(item, dict):
                continue
            path = Path(str(item.get("path", "")))
            if path.exists() and path_is_inside(path, repo):
                file_previews.append(read_project_file_preview(path, limit=1200))
        commands = detect_project_commands(repo)
        risks = []
        git = detail.get("git", {})
        dirty_count = int(git.get("dirty_count", 0) or 0)
        if dirty_count:
            risks.append(f"Repository has {dirty_count} changed entries; avoid broad rewrites before reviewing user/agent edits.")
        if not commands:
            risks.append("No obvious verification command detected from bounded files.")
        if not detail.get("readme_preview"):
            risks.append("README preview is empty or missing.")
        recommended_next_steps = [
            "Open the repo detail and context pack before editing.",
            "Choose one narrow implementation slice with matching tests or smoke checks.",
            "Update docs and memory after the slice.",
            "Keep destructive Git, install, and terminal actions behind explicit confirmation.",
        ]
        return {
            "kind": "code-review-brief",
            "summary": f"{detail['name']} on branch {git.get('branch', '') or 'unknown'} with {dirty_count} changed entries, {len(file_previews)} sampled files, and {len(commands)} suggested verification commands.",
            "project_id": project_id,
            "project_name": detail["name"],
            "project_path": detail["path"],
            "git": git,
            "recent_commits": detail.get("recent_commits", [])[:5],
            "file_previews": file_previews,
            "commands": commands,
            "risks": risks,
            "recommended_next_steps": recommended_next_steps,
            "safety": "read-only-local-files-plus-git-status",
        }
    if task_type == "code-explain-brief":
        project_id = str(parameters.get("project_id", "")).strip()
        if not project_id:
            projects = discover_git_repos(limit=1)
            project_id = projects[0]["id"] if projects else ""
        detail = project_detail(project_id) if project_id else None
        if not detail:
            return {
                "kind": "code-explain-brief",
                "summary": f"Selected project `{project_id}` was not found in the bounded project cache.",
                "project_id": project_id,
                "status": "missing",
            }
        repo = Path(detail["path"])
        file_previews = []
        for item in detail.get("important_files", [])[:10]:
            if not isinstance(item, dict):
                continue
            path = Path(str(item.get("path", "")))
            if path.exists() and path_is_inside(path, repo):
                file_previews.append(read_project_file_preview(path, limit=1000))
        commands = detect_project_commands(repo)
        git = detail.get("git", {})
        readme = str(detail.get("readme_preview", "")).strip()
        todo = str(detail.get("todo_preview", "")).strip()
        entry_points = []
        for candidate in [
            "README.md",
            "PLAN.md",
            "STRUCTURE.md",
            "package.json",
            "pyproject.toml",
            "backend/main.py",
            "src/main.ts",
            "godot/project.godot",
            "godot/scripts/main.gd",
        ]:
            path = repo / candidate
            if path.exists():
                entry_points.append({"name": candidate, "path": str(path), "bytes": path.stat().st_size})
        key_files = []
        for preview in file_previews[:8]:
            key_files.append({
                "name": preview.get("name", ""),
                "relative_path": str(Path(preview.get("path", "")).resolve().relative_to(repo)).replace("\\", "/") if preview.get("path") else "",
                "bytes": preview.get("bytes", 0),
                "preview": str(preview.get("preview", ""))[:700],
            })
        recommended_next_steps = [
            "Read README/PLAN first, then open the listed entry points in order.",
            "Use Context Pack for a deeper handoff before editing.",
            "Use Patch Plan only after the explanation matches the intended change.",
            "Keep tests, formatters, installs, and Git writes behind Terminal Control or explicit confirmation.",
        ]
        concepts = []
        if readme:
            concepts.append("README explains project purpose and user-facing setup.")
        if todo:
            concepts.append("PLAN/TODO gives current implementation direction.")
        if commands:
            concepts.append("Detected verification commands are candidates only; they are not executed by this brief.")
        dirty_count = int(git.get("dirty_count", 0) or 0)
        if dirty_count:
            concepts.append(f"Working tree has {dirty_count} changed entries; treat current files as live collaborative state.")
        return {
            "kind": "code-explain-brief",
            "summary": f"{detail['name']} explained from {len(entry_points)} entry point(s), {len(key_files)} sampled key file(s), and {len(commands)} candidate command(s).",
            "project_id": project_id,
            "project_name": detail["name"],
            "project_path": detail["path"],
            "git": git,
            "entry_points": entry_points,
            "key_files": key_files,
            "readme_excerpt": readme[:1800],
            "plan_excerpt": todo[:1200],
            "commands": commands,
            "concepts": concepts,
            "recommended_next_steps": recommended_next_steps,
            "safety": "read-only-local-files-plus-git-status",
        }
    if task_type == "research-brief":
        project_id = str(parameters.get("project_id", "")).strip()
        if not project_id:
            cards = all_research_project_cards()
            project_id = cards[0]["id"] if cards else ""
        detail = research_project_detail(project_id) if project_id else None
        if not detail:
            return {
                "kind": "research-brief",
                "summary": f"Selected research project `{project_id}` was not found in the configured research boards.",
                "project_id": project_id,
                "status": "missing",
            }
        status_docs = []
        for doc in detail.get("status_docs", [])[:6]:
            if isinstance(doc, dict):
                status_docs.append({
                    "name": doc.get("name", ""),
                    "path": doc.get("path", ""),
                    "exists": doc.get("exists", False),
                    "excerpt": doc.get("excerpt", [])[:6],
                })
        experiment_entries = []
        for root in detail.get("experiment_entries", [])[:4]:
            if isinstance(root, dict):
                experiment_entries.append({
                    "root": root.get("root", ""),
                    "exists": root.get("exists", False),
                    "candidates": root.get("candidates", [])[:8],
                })
        local_dirs = [
            {
                "path": item.get("path", ""),
                "exists": item.get("exists", False),
                "sample": item.get("sample", [])[:6],
            }
            for item in detail.get("local_dirs", [])
            if isinstance(item, dict)
        ]
        risks = []
        if not any(item.get("exists") for item in local_dirs):
            risks.append("No configured local directory exists for this research board.")
        if detail.get("status_count", 0) == 0:
            risks.append("No shared-memory status document was found for this project.")
        if not experiment_entries:
            risks.append("No bounded experiment entry candidates were found.")
        recommended_next_steps = [
            f"Read the newest status document for `{detail.get('name', project_id)}`.",
            "Turn the next_action into a small ARIS plan: claim, evidence, experiment command, expected table/figure, and stop condition.",
            "Create a project-local research note before running any experiment.",
            "Keep server/long-running experiment execution outside the game until a confirm-required runner is added.",
        ]
        return {
            "kind": "research-brief",
            "summary": f"{detail.get('name', project_id)}: {detail.get('theme', '')} Next: {detail.get('next_action', '')}",
            "project_id": project_id,
            "project_name": detail.get("name", ""),
            "theme": detail.get("theme", ""),
            "priority": detail.get("priority", ""),
            "server": detail.get("server", ""),
            "next_action": detail.get("next_action", ""),
            "local_dirs": local_dirs,
            "status_docs": status_docs,
            "experiment_entries": experiment_entries,
            "risks": risks,
            "recommended_next_steps": recommended_next_steps,
            "safety": "read-only-local-files",
        }
    if task_type == "task-brief":
        local_task_id = str(parameters.get("task_id", "")).strip()
        if not local_task_id:
            local_tasks = task_board_overview().get("local_tasks", [])
            local_task_id = str(local_tasks[0].get("id", "")) if local_tasks else ""
        detail = get_local_task_detail(local_task_id) if local_task_id else None
        if not detail:
            return {
                "kind": "task-brief",
                "summary": f"Selected local task `{local_task_id}` was not found in the Task Board ledger.",
                "task_id": local_task_id,
                "status": "missing",
                "safety": "read-only-project-local-task",
            }
        local_task = detail.get("task", {})
        preview = str(detail.get("preview", ""))
        risks = []
        if not detail.get("draft_exists", False):
            risks.append("Task draft file is missing; rely on ledger metadata only.")
        if str(local_task.get("status", "")) in {"done", "archived"}:
            risks.append("Task is already marked complete or archived.")
        if len(preview.strip()) < 80:
            risks.append("Task draft preview is short; clarify acceptance criteria before execution.")
        recommended_next_steps = [
            "Confirm the task still matches the current project state.",
            "Break the request into one safe, testable slice.",
            "Choose the relevant building or agent queue before execution.",
            "Keep file writes, terminal commands, Git, and external tracker updates behind the existing safety gates.",
        ]
        return {
            "kind": "task-brief",
            "summary": f"{local_task.get('title', local_task_id)} is {local_task.get('status', 'unknown')} for {local_task.get('target_agent', 'codex')}.",
            "task_id": local_task_id,
            "task": local_task,
            "draft_path": detail.get("draft_path", ""),
            "preview": preview[:1800],
            "truncated": detail.get("truncated", False),
            "risks": risks,
            "recommended_next_steps": recommended_next_steps,
            "safety": "read-only-project-local-task",
        }
    index = memory_index(limit_per_category=3)
    category_counts = {
        shelf.get("category", "memory"): shelf.get("count", 0)
        for shelf in index.get("categories", [])
        if isinstance(shelf, dict)
    }
    recent = []
    for item in index.get("recent", [])[:8]:
        if isinstance(item, dict):
            recent.append({
                "category": item.get("category", ""),
                "filename": item.get("filename", ""),
                "title": item.get("title", item.get("name", "")),
            })
    return {
        "kind": "memory-brief",
        "summary": f"{len(category_counts)} memory shelves indexed; {sum(category_counts.values())} notes visible.",
        "root": index.get("root", ""),
        "root_exists": index.get("root_exists", False),
        "category_counts": category_counts,
        "recent": recent,
    }


def write_agent_task_log(task: dict) -> dict:
    AGENT_TASK_LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = AGENT_TASK_LOG_DIR / f"{stamp}-{task.get('id', 'task')}.json"
    path.write_text(json.dumps(task, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    task["log_path"] = str(path)
    return {"path": str(path), "bytes": path.stat().st_size}


def latest_agent_task_logs(limit: int = 12) -> list[dict]:
    if not AGENT_TASK_LOG_DIR.exists():
        return []
    try:
        paths = sorted(
            [path for path in AGENT_TASK_LOG_DIR.glob("*.json") if path.is_file()],
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
    except Exception:
        return []
    logs = []
    for path in paths[:max(1, min(limit, 50))]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        events = data.get("events", [])
        logs.append({
            "log_id": path.stem,
            "id": data.get("id", path.stem),
            "target_agent": data.get("target_agent", ""),
            "task_type": data.get("task_type", ""),
            "title": data.get("title", path.stem),
            "status": data.get("status", "unknown"),
            "safety": data.get("safety", ""),
            "created_at": data.get("created_at", 0),
            "updated_at": data.get("updated_at", path.stat().st_mtime),
            "event_count": len(events) if isinstance(events, list) else 0,
            "result_summary": data.get("result_summary", ""),
            "rollback_note": data.get("rollback_note", ""),
            "log_path": str(path),
            "bytes": path.stat().st_size,
        })
    return logs


def read_agent_task_log(log_id: str) -> dict:
    safe_id = slugify_filename(log_id.strip())
    if not safe_id:
        return {"status": "missing", "log_id": log_id}
    path = (AGENT_TASK_LOG_DIR / f"{safe_id}.json").resolve()
    if not path.exists() or not path_is_inside(path, AGENT_TASK_LOG_DIR.resolve()):
        return {"status": "missing", "log_id": safe_id}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "status": "error",
            "mode": "read-only-agent-task-log-detail",
            "log_id": safe_id,
            "log_path": str(path),
            "error": f"Could not parse agent task log: {exc}",
            "safe_note": "Agent task log detail is read-only. Parse errors do not retry tasks, start agents, run commands, or perform rollback.",
        }
    result_preview = ""
    result = data.get("result")
    if result is not None:
        try:
            result_preview = json.dumps(result, ensure_ascii=False, indent=2, default=str)[:3200]
        except Exception:
            result_preview = str(result)[:3200]
    result_preview = redact_secret_text(result_preview)
    events = data.get("events", [])
    if not isinstance(events, list):
        events = []
    return {
        "status": "ok",
        "mode": "read-only-agent-task-log-detail",
        "log_id": safe_id,
        "log_path": str(path),
        "bytes": path.stat().st_size,
        "task": {
            "id": data.get("id", ""),
            "target_agent": data.get("target_agent", ""),
            "task_type": data.get("task_type", ""),
            "title": data.get("title", ""),
            "status": data.get("status", ""),
            "safety": data.get("safety", ""),
            "source_building": data.get("source_building", ""),
            "created_at": data.get("created_at", 0),
            "updated_at": data.get("updated_at", 0),
            "error": data.get("error", ""),
            "cancel_requested": data.get("cancel_requested", False),
            "rollback_note": data.get("rollback_note", ""),
            "result_summary": data.get("result_summary", ""),
        },
        "events": events[:80],
        "event_count": len(events),
        "result_preview": result_preview,
        "safe_note": "Agent task log detail is read-only project-local execution evidence. It does not replay tasks, start external runners, execute shell commands, mutate files, contact remote APIs, or perform rollback.",
    }


def run_agent_task(task_id: str) -> None:
    try:
        task = AGENT_TASKS.get(task_id)
        if not task:
            return
        if task.get("status") == "cancelled":
            task["updated_at"] = time.time()
            task.setdefault("events", []).append({"at": task["updated_at"], "message": "Task was already cancelled before execution."})
            return
        if task.get("cancel_requested"):
            task["status"] = "cancelled"
            task["updated_at"] = time.time()
            task["result_summary"] = "Cancelled before the safe local brief builder started."
            task.setdefault("events", []).append({"at": task["updated_at"], "message": "Task cancelled before execution."})
            try:
                log = write_agent_task_log(task)
                task["log_path"] = log["path"]
            except Exception:
                pass
            return
        if task.get("status") == "paused":
            task["updated_at"] = time.time()
            task.setdefault("events", []).append({"at": task["updated_at"], "message": "Task is paused before execution."})
            return
        task["status"] = "running"
        task["updated_at"] = time.time()
        task.setdefault("events", []).append({"at": task["updated_at"], "message": "Task started."})
        try:
            result = build_agent_task_payload(task)
            task["result"] = result
            task["result_summary"] = result.get("summary", "")
            task["updated_at"] = time.time()
            task.setdefault("events", []).append({"at": task["updated_at"], "message": "Task result built."})
            if task.get("cancel_requested"):
                task["status"] = "cancelled"
                task["result_summary"] = task.get("result_summary", "") or "Cancelled after the safe local brief builder finished."
                task.setdefault("events", []).append({"at": task["updated_at"], "message": "Task cancellation applied after local result build; no external runner was started."})
                log = write_agent_task_log(task)
                task["log_path"] = log["path"]
                return
            log = write_agent_task_log(task)
            task["log_path"] = log["path"]
            record_memory_event(
                f"Agent task completed: {task.get('title', 'Untitled')}",
                f"{task.get('target_agent', 'codex')} ran {task.get('task_type', 'memory-brief')} via AI Town Agent Hub. Result: {task.get('result_summary', '')}\n\nLog: {task.get('log_path', '')}",
                "agent-task-queue",
            )
            task["status"] = "done"
            task["updated_at"] = time.time()
            task.setdefault("events", []).append({"at": task["updated_at"], "message": "Task completed."})
        except Exception as exc:
            task["status"] = "failed"
            task["error"] = str(exc)
            task["updated_at"] = time.time()
            task.setdefault("events", []).append({"at": task["updated_at"], "message": f"Task failed: {exc}"})
            try:
                log = write_agent_task_log(task)
                task["log_path"] = log["path"]
            except Exception:
                pass
    finally:
        schedule_agent_tasks()


def submit_agent_task(req: AgentTaskSubmitRequest) -> dict:
    prune_agent_tasks()
    allowed = {item["id"] for item in agent_task_catalog()}
    task_type = req.task_type.strip().lower() or "memory-brief"
    if task_type not in allowed:
        task_type = "memory-brief"
    target = req.target_agent.strip().lower() or "codex"
    if target not in AGENT_PERSONALITIES:
        target = "codex"
    now = time.time()
    task_id = uuid.uuid4().hex[:12]
    task = {
        "id": task_id,
        "target_agent": target,
        "task_type": task_type,
        "title": req.title.strip() or "AI Town safe agent task",
        "body": req.body.strip() or "Summarize a safe local status signal.",
        "source_building": req.source_building.strip() or "agent-hub",
        "parameters": req.parameters if isinstance(req.parameters, dict) else {},
        "status": "paused" if req.start_paused else "queued",
        "safety": "safe-local-readonly-brief-plus-json-log",
        "created_at": now,
        "updated_at": now,
        "events": [{"at": now, "message": "Task submitted."}],
        "result": None,
        "result_summary": "",
        "error": "",
        "log_path": "",
        "cancel_requested": False,
        "rollback_note": "No external runner, shell command, repo write, service change, or remote API is started by this safe local brief task.",
    }
    AGENT_TASKS[task_id] = task
    if not req.start_paused:
        schedule_agent_tasks()
    return {
        "status": "queued" if not req.start_paused else "paused",
        "task": agent_task_summary(task),
        "queue": agent_task_snapshot(),
    }


def get_agent_task(task_id: str) -> dict:
    task = AGENT_TASKS.get(task_id)
    if not task:
        return {"status": "missing", "task_id": task_id}
    return {"status": "ok", "task": task, "queue": agent_task_snapshot()}


def get_agent_task_events(task_id: str, since: int = 0, limit: int = 32) -> dict:
    task = AGENT_TASKS.get(task_id)
    if not task:
        return {"status": "missing", "task_id": task_id, "events": [], "next_cursor": max(0, since)}
    events = task.get("events", [])
    if not isinstance(events, list):
        events = []
    start = max(0, since)
    bounded_limit = min(max(1, limit), 100)
    selected = events[start:start + bounded_limit]
    indexed_events = []
    for offset, event in enumerate(selected, start=start):
        if isinstance(event, dict):
            indexed_event = dict(event)
        else:
            indexed_event = {"message": str(event)}
        indexed_event["index"] = offset
        indexed_events.append(indexed_event)
    return {
        "status": "ok",
        "task": agent_task_summary(task),
        "events": indexed_events,
        "event_count": len(events),
        "next_cursor": start + len(selected),
        "has_more": start + len(selected) < len(events),
        "queue": agent_task_snapshot(),
        "safe_note": "Event stream is a bounded polling view over one safe local agent task. It does not start external runners or execute shell commands.",
    }


def pause_agent_task(task_id: str) -> dict:
    task = AGENT_TASKS.get(task_id)
    if not task:
        return {"status": "missing", "task_id": task_id}
    if task.get("status") in {"queued", "paused"}:
        task["status"] = "paused"
        task["updated_at"] = time.time()
        task.setdefault("events", []).append({"at": task["updated_at"], "message": "Task paused."})
    elif task.get("status") == "dispatching":
        task["pause_requested"] = True
        task["updated_at"] = time.time()
        task.setdefault("events", []).append({"at": task["updated_at"], "message": "Pause requested after dispatch; safe brief may start first."})
    elif task.get("status") == "running":
        task["pause_requested"] = True
        task["updated_at"] = time.time()
        task.setdefault("events", []).append({"at": task["updated_at"], "message": "Pause requested while running; brief task may finish first."})
    return {"status": "ok", "task": agent_task_summary(task), "queue": agent_task_snapshot()}


def cancel_agent_task(task_id: str, req: AgentTaskCancelRequest) -> dict:
    task = AGENT_TASKS.get(task_id)
    if not task:
        return {"status": "missing", "task_id": task_id}
    now = time.time()
    reason = req.reason.strip() or "Cancelled from Agent Hub."
    source = req.source_building.strip() or "agent-hub"
    status = str(task.get("status", ""))
    task["updated_at"] = now
    task["cancel_requested"] = True
    task["cancel_reason"] = reason
    task["cancel_source_building"] = source
    task["rollback_note"] = "Cancelled safely: AI Town Agent Tasks do not start external runners, execute shell commands, mutate repositories, stop services, or call remote APIs."
    if status in {"queued", "paused"}:
        task["status"] = "cancelled"
        task["result_summary"] = f"Cancelled before execution: {reason}"
        task.setdefault("events", []).append({"at": now, "message": f"Task cancelled before execution by {source}: {reason}"})
        try:
            log = write_agent_task_log(task)
            task["log_path"] = log["path"]
        except Exception:
            pass
    elif status in {"dispatching", "running"}:
        task.setdefault("events", []).append({"at": now, "message": f"Cancellation requested by {source}; current safe brief may finish first: {reason}"})
    elif status == "cancelled":
        task.setdefault("events", []).append({"at": now, "message": f"Cancellation confirmed by {source}: task was already cancelled."})
    else:
        task.setdefault("events", []).append({"at": now, "message": f"Cancellation noted by {source}, but task is already {status or 'complete'}."})
    if status in {"queued", "paused"}:
        schedule_agent_tasks()
    return {"status": "ok", "task": agent_task_summary(task), "queue": agent_task_snapshot()}


def resume_agent_task(task_id: str) -> dict:
    task = AGENT_TASKS.get(task_id)
    if not task:
        return {"status": "missing", "task_id": task_id}
    if task.get("status") == "paused":
        task["status"] = "queued"
        task["updated_at"] = time.time()
        task.setdefault("events", []).append({"at": task["updated_at"], "message": "Task resumed."})
        schedule_agent_tasks()
    return {"status": "ok", "task": agent_task_summary(task), "queue": agent_task_snapshot()}


def agent_tool_catalog() -> list[dict]:
    return [
        {
            "id": "memory-index",
            "name": "Memory Index",
            "description": "Read shared memory shelf counts and recent notes.",
            "parameters": {"limit_per_category": "int, default 3"},
            "safety": "read-only-local-files",
        },
        {
            "id": "knowledge-search",
            "name": "Knowledge Search",
            "description": "Search the cached Knowledge Tower index.",
            "parameters": {"q": "string, default memory", "page_size": "int, default 5"},
            "safety": "cached-read-only",
        },
        {
            "id": "file-search",
            "name": "File Search",
            "description": "Search the cached File Vault index.",
            "parameters": {"q": "string, default README", "page_size": "int, default 5"},
            "safety": "cached-read-only",
        },
        {
            "id": "project-index",
            "name": "Project Index",
            "description": "List bounded local Git project cards.",
            "parameters": {"limit": "int, default 8"},
            "safety": "read-only-git-metadata",
        },
        {
            "id": "system-snapshot",
            "name": "System Snapshot",
            "description": "Read backend job queue, registries, model gateway, and index cache status.",
            "parameters": {},
            "safety": "read-only-runtime-metadata",
        },
    ]


def prune_agent_tool_invocations() -> None:
    if len(AGENT_TOOL_INVOCATIONS) <= MAX_AGENT_TOOL_INVOCATIONS:
        return
    ordered = sorted(AGENT_TOOL_INVOCATIONS.items(), key=lambda item: item[1].get("created_at", 0))
    for invocation_id, _item in ordered[:len(AGENT_TOOL_INVOCATIONS) - MAX_AGENT_TOOL_INVOCATIONS]:
        AGENT_TOOL_INVOCATIONS.pop(invocation_id, None)


def agent_tool_summary(invocation: dict) -> dict:
    return {
        "id": invocation.get("id", ""),
        "tool_id": invocation.get("tool_id", ""),
        "tool_name": invocation.get("tool_name", ""),
        "target_agent": invocation.get("target_agent", ""),
        "status": invocation.get("status", ""),
        "safety": invocation.get("safety", ""),
        "created_at": invocation.get("created_at", 0),
        "updated_at": invocation.get("updated_at", 0),
        "result_summary": invocation.get("result_summary", ""),
        "error": invocation.get("error", ""),
        "log_path": invocation.get("log_path", ""),
    }


def agent_tool_invocation_snapshot(limit: int = 16) -> dict:
    counts: dict[str, int] = {}
    for invocation in AGENT_TOOL_INVOCATIONS.values():
        status = str(invocation.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    recent = [
        agent_tool_summary(invocation)
        for invocation in sorted(
            AGENT_TOOL_INVOCATIONS.values(),
            key=lambda item: item.get("updated_at", item.get("created_at", 0)),
            reverse=True,
        )[:limit]
    ]
    return {
        "status": "ok",
        "mode": "safe-agent-tool-invocation-queue",
        "count": len(AGENT_TOOL_INVOCATIONS),
        "counts": counts,
        "recent": recent,
        "catalog": agent_tool_catalog(),
        "log_dir": str(AGENT_TOOL_LOG_DIR),
        "safe_note": "Agent tools are registered safe adapters. This queue does not run arbitrary shell commands or invoke external agent runners.",
    }


def execute_agent_tool(tool_id: str, parameters: Optional[dict]) -> dict:
    params = parameters if isinstance(parameters, dict) else {}
    if tool_id == "knowledge-search":
        q = str(params.get("q", "memory"))
        page_size = int(params.get("page_size", 5))
        result = knowledge_search(q=q, page_size=page_size)
        return {"summary": f"{result.get('total', 0)} cached knowledge result(s) for `{q}`.", "result": result}
    if tool_id == "file-search":
        q = str(params.get("q", "README"))
        page_size = int(params.get("page_size", 5))
        result = file_vault_search(q=q, page_size=page_size)
        return {"summary": f"{result.get('total', 0)} cached file result(s) for `{q}`.", "result": result}
    if tool_id == "project-index":
        limit = max(1, min(int(params.get("limit", 8)), 20))
        projects = discover_git_repos(limit=limit)
        return {"summary": f"{len(projects)} local Git project card(s) sampled.", "result": {"projects": projects, "count": len(projects)}}
    if tool_id == "system-snapshot":
        result = {
            "jobs": job_queue_snapshot(),
            "agent_tasks": agent_task_snapshot(),
            "agent_tools": agent_tool_invocation_snapshot(),
            "model_gateway": model_gateway_status(),
            "knowledge_index": knowledge_index_overview(),
            "file_vault_index": file_vault_index_overview(),
            "registries": {
                "buildings": len(load_json_registry(BUILDING_REGISTRY_PATH)),
                "agents": len(load_json_registry(AGENT_REGISTRY_PATH)),
                "workspaces": len(load_workspace_registry()),
                "quests": len(load_quest_registry()),
                "districts": len(load_json_registry(DISTRICT_REGISTRY_PATH)),
                "room_scenes": len(load_json_registry(ROOM_SCENE_REGISTRY_PATH)),
                "map_decor": len(load_json_registry(MAP_DECOR_REGISTRY_PATH)),
            },
        }
        return {"summary": "Runtime snapshot collected from local backend state.", "result": result}
    result = memory_index(limit_per_category=int(params.get("limit_per_category", 3)))
    return {"summary": f"{len(result.get('categories', []))} shared memory shelf/shelves indexed.", "result": result}


def write_agent_tool_log(invocation: dict) -> dict:
    AGENT_TOOL_LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = AGENT_TOOL_LOG_DIR / f"{stamp}-{invocation.get('id', 'tool')}.json"
    path.write_text(json.dumps(invocation, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    invocation["log_path"] = str(path)
    return {"path": str(path), "bytes": path.stat().st_size}


def latest_agent_tool_logs(limit: int = 12) -> list[dict]:
    if not AGENT_TOOL_LOG_DIR.exists():
        return []
    try:
        paths = sorted(
            [path for path in AGENT_TOOL_LOG_DIR.glob("*.json") if path.is_file()],
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
    except Exception:
        return []
    logs = []
    for path in paths[:max(1, min(limit, 50))]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        events = data.get("events", [])
        logs.append({
            "log_id": path.stem,
            "id": data.get("id", path.stem),
            "tool_id": data.get("tool_id", ""),
            "tool_name": data.get("tool_name", ""),
            "target_agent": data.get("target_agent", ""),
            "status": data.get("status", "unknown"),
            "safety": data.get("safety", ""),
            "created_at": data.get("created_at", 0),
            "updated_at": data.get("updated_at", path.stat().st_mtime),
            "event_count": len(events) if isinstance(events, list) else 0,
            "result_summary": data.get("result_summary", ""),
            "log_path": str(path),
            "bytes": path.stat().st_size,
        })
    return logs


def read_agent_tool_log(log_id: str) -> dict:
    safe_id = slugify_filename(log_id.strip())
    if not safe_id:
        return {"status": "missing", "log_id": log_id}
    path = (AGENT_TOOL_LOG_DIR / f"{safe_id}.json").resolve()
    if not path.exists() or not path_is_inside(path, AGENT_TOOL_LOG_DIR.resolve()):
        return {"status": "missing", "log_id": safe_id}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "status": "error",
            "mode": "read-only-agent-tool-log-detail",
            "log_id": safe_id,
            "log_path": str(path),
            "error": f"Could not parse agent tool log: {exc}",
            "safe_note": "Agent tool log detail is read-only. Parse errors do not retry tools, start agents, run commands, or perform rollback.",
        }
    result_preview = ""
    result = data.get("result")
    if result is not None:
        try:
            result_preview = json.dumps(result, ensure_ascii=False, indent=2, default=str)[:3200]
        except Exception:
            result_preview = str(result)[:3200]
    result_preview = redact_secret_text(result_preview)
    events = data.get("events", [])
    if not isinstance(events, list):
        events = []
    return {
        "status": "ok",
        "mode": "read-only-agent-tool-log-detail",
        "log_id": safe_id,
        "log_path": str(path),
        "bytes": path.stat().st_size,
        "invocation": {
            "id": data.get("id", ""),
            "tool_id": data.get("tool_id", ""),
            "tool_name": data.get("tool_name", ""),
            "target_agent": data.get("target_agent", ""),
            "status": data.get("status", ""),
            "safety": data.get("safety", ""),
            "source_building": data.get("source_building", ""),
            "created_at": data.get("created_at", 0),
            "updated_at": data.get("updated_at", 0),
            "error": data.get("error", ""),
            "result_summary": data.get("result_summary", ""),
            "parameters": data.get("parameters", {}),
        },
        "events": events[:80],
        "event_count": len(events),
        "result_preview": result_preview,
        "safe_note": "Agent tool log detail is read-only project-local tool evidence. It does not replay tools, start external runners, execute shell commands, mutate files, contact remote APIs, or perform rollback.",
    }


def run_agent_tool_invocation(invocation_id: str) -> None:
    invocation = AGENT_TOOL_INVOCATIONS.get(invocation_id)
    if not invocation:
        return
    invocation["status"] = "running"
    invocation["updated_at"] = time.time()
    invocation.setdefault("events", []).append({"at": invocation["updated_at"], "message": "Tool invocation started."})
    try:
        payload = execute_agent_tool(invocation.get("tool_id", "memory-index"), invocation.get("parameters", {}))
        invocation["result"] = payload.get("result")
        invocation["result_summary"] = payload.get("summary", "")
        invocation["updated_at"] = time.time()
        invocation.setdefault("events", []).append({"at": invocation["updated_at"], "message": "Tool result built."})
        log = write_agent_tool_log(invocation)
        invocation["log_path"] = log["path"]
        record_memory_event(
            f"Agent tool invoked: {invocation.get('tool_name', invocation.get('tool_id', 'tool'))}",
            f"{invocation.get('target_agent', 'codex')} invoked `{invocation.get('tool_id', '')}` via AI Town Agent Hub. Result: {invocation.get('result_summary', '')}\n\nLog: {invocation.get('log_path', '')}",
            "agent-tool-registry",
        )
        invocation["status"] = "done"
        invocation["updated_at"] = time.time()
        invocation.setdefault("events", []).append({"at": invocation["updated_at"], "message": "Tool invocation completed."})
    except Exception as exc:
        invocation["status"] = "failed"
        invocation["error"] = str(exc)
        invocation["updated_at"] = time.time()
        invocation.setdefault("events", []).append({"at": invocation["updated_at"], "message": f"Tool invocation failed: {exc}"})
        try:
            log = write_agent_tool_log(invocation)
            invocation["log_path"] = log["path"]
        except Exception:
            pass


def invoke_agent_tool(req: AgentToolInvokeRequest) -> dict:
    prune_agent_tool_invocations()
    catalog_by_id = {item["id"]: item for item in agent_tool_catalog()}
    tool_id = req.tool_id.strip().lower() or "memory-index"
    if tool_id not in catalog_by_id:
        tool_id = "memory-index"
    target = req.target_agent.strip().lower() or "codex"
    if target not in AGENT_PERSONALITIES:
        target = "codex"
    now = time.time()
    invocation_id = uuid.uuid4().hex[:12]
    tool = catalog_by_id[tool_id]
    invocation = {
        "id": invocation_id,
        "tool_id": tool_id,
        "tool_name": tool["name"],
        "target_agent": target,
        "parameters": req.parameters if isinstance(req.parameters, dict) else {},
        "source_building": req.source_building.strip() or "agent-hub",
        "status": "queued",
        "safety": tool["safety"],
        "created_at": now,
        "updated_at": now,
        "events": [{"at": now, "message": "Tool invocation queued."}],
        "result": None,
        "result_summary": "",
        "error": "",
        "log_path": "",
    }
    AGENT_TOOL_INVOCATIONS[invocation_id] = invocation
    JOB_EXECUTOR.submit(run_agent_tool_invocation, invocation_id)
    return {
        "status": "queued",
        "invocation": agent_tool_summary(invocation),
        "queue": agent_tool_invocation_snapshot(),
    }


def get_agent_tool_invocation(invocation_id: str) -> dict:
    invocation = AGENT_TOOL_INVOCATIONS.get(invocation_id)
    if not invocation:
        return {"status": "missing", "invocation_id": invocation_id}
    return {"status": "ok", "invocation": invocation, "queue": agent_tool_invocation_snapshot()}


def get_agent_tool_invocation_events(invocation_id: str, since: int = 0, limit: int = 32) -> dict:
    invocation = AGENT_TOOL_INVOCATIONS.get(invocation_id)
    if not invocation:
        return {"status": "missing", "invocation_id": invocation_id, "events": [], "next_cursor": max(0, since)}
    events = invocation.get("events", [])
    if not isinstance(events, list):
        events = []
    start = max(0, since)
    bounded_limit = min(max(1, limit), 100)
    selected = events[start:start + bounded_limit]
    indexed_events = []
    for offset, event in enumerate(selected, start=start):
        if isinstance(event, dict):
            indexed_event = dict(event)
        else:
            indexed_event = {"message": str(event)}
        indexed_event["index"] = offset
        indexed_events.append(indexed_event)
    return {
        "status": "ok",
        "invocation": agent_tool_summary(invocation),
        "events": indexed_events,
        "event_count": len(events),
        "next_cursor": start + len(selected),
        "has_more": start + len(selected) < len(events),
        "queue": agent_tool_invocation_snapshot(),
        "safe_note": "Event stream is a bounded polling view over one safe registered tool invocation. It does not start external runners or execute shell commands.",
    }


PROJECT_SCAN_ROOTS = [
    ("AI Town", PROJECT_ROOT),
    ("Company", Path(r"D:\Company")),
    ("Research", RESEARCH_ROOT),
    ("Devtools", DEVTOOLS_DIR),
]


def project_id_for(path: Path) -> str:
    digest = hashlib.sha1(str(path.resolve()).encode("utf-8", errors="ignore")).hexdigest()[:10]
    return f"{slugify_filename(path.name)}-{digest}"


def run_git_readonly(repo: Path, args: list[str], timeout: float = 0.6) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except Exception as exc:
        return f"git unavailable: {exc}"
    output = (proc.stdout or proc.stderr or "").strip()
    return output[:4000]


def git_summary(repo: Path) -> dict:
    status = run_git_readonly(repo, ["status", "--short", "--branch"], timeout=0.9)
    lines = status.splitlines()
    branch = ""
    dirty = []
    if lines and lines[0].startswith("## "):
        branch = lines[0][3:]
        dirty = lines[1:]
    else:
        dirty = lines
    return {
        "status_text": status,
        "branch": branch,
        "dirty_count": len([line for line in dirty if line.strip()]),
        "is_git_repo": (repo / ".git").exists(),
    }


def important_project_files(repo: Path) -> list[dict]:
    names = [
        "README.md",
        "readme.md",
        "TODO.md",
        "PLAN.md",
        "STRUCTURE.md",
        "pyproject.toml",
        "package.json",
        "project.godot",
        "Cargo.toml",
    ]
    files = []
    for name in names:
        path = repo / name
        if path.exists():
            try:
                files.append({"name": name, "path": str(path), "bytes": path.stat().st_size})
            except Exception:
                files.append({"name": name, "path": str(path)})
    return files


def discover_git_repos(limit: int = 8) -> list[dict]:
    repos: list[Path] = []
    seen = set()
    scan_roots = project_scan_roots()
    for label, root in scan_roots:
        if not root.exists():
            continue
        candidates = [root]
        try:
            candidates.extend([child for child in root.iterdir() if child.is_dir()][:18])
        except Exception:
            pass
        for candidate in candidates:
            if not (candidate / ".git").exists():
                continue
            key = str(candidate.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            repos.append(candidate)
            if len(repos) >= limit:
                break
        if len(repos) >= limit:
            break
    projects = []
    for repo in repos[:limit]:
        family = next((label for label, root in scan_roots if path_is_inside(repo, root)), "Local")
        branch = run_git_readonly(repo, ["branch", "--show-current"], timeout=0.35)
        project_id = project_id_for(repo)
        PROJECT_PATH_CACHE[project_id] = str(repo)
        projects.append({
            "id": project_id,
            "name": repo.name,
            "path": str(repo),
            "family": family,
            "branch": branch,
            "dirty_count": -1,
            "has_readme": any(item["name"].lower() == "readme.md" for item in important_project_files(repo)),
            "important_files": important_project_files(repo)[:6],
        })
    return projects


def project_detail(project_id: str) -> Optional[dict]:
    if project_id not in PROJECT_PATH_CACHE:
        discover_git_repos()
    if project_id not in PROJECT_PATH_CACHE:
        return None
    repo = Path(PROJECT_PATH_CACHE[project_id])
    family = next((label for label, root in project_scan_roots() if path_is_inside(repo, root)), "Local")
    project = {
        "id": project_id,
        "name": repo.name,
        "path": str(repo),
        "family": family,
        "important_files": important_project_files(repo)[:6],
    }
    readme_preview = ""
    for name in ["README.md", "readme.md"]:
        path = repo / name
        if path.exists():
            readme_preview = path.read_text(encoding="utf-8", errors="ignore")[:2400]
            break
    todo_preview = ""
    for name in ["TODO.md", "PLAN.md"]:
        path = repo / name
        if path.exists():
            todo_preview = path.read_text(encoding="utf-8", errors="ignore")[:1600]
            break
    detail = dict(project)
    detail.update({
        "status": "ok",
        "git": git_summary(repo),
        "recent_commits": run_git_readonly(repo, ["log", "--oneline", "-5"], timeout=0.9).splitlines(),
        "readme_preview": readme_preview,
        "todo_preview": todo_preview,
        "safe_actions": [
            {"id": "inspect", "label": "Inspect project metadata", "safety": "read-only"},
            {"id": "prepare-code-task", "label": "Prepare coding-agent task draft", "safety": "project-local-draft"},
            {"id": "run-tests", "label": "Future controlled test run", "safety": "confirm-required"},
        ],
    })
    return detail


def create_code_task_draft(project_id: str, req: CodeTaskDraftRequest) -> Optional[dict]:
    detail = project_detail(project_id)
    if not detail:
        return None
    repo = Path(detail["path"])
    task_id = uuid.uuid4().hex[:12]
    target_agent = req.target_agent.strip().lower() or "codex"
    if target_agent not in AGENT_PERSONALITIES:
        target_agent = "codex"
    title = req.task_title.strip() or f"Inspect {detail['name']}"
    body = req.task_body.strip() or "Inspect the selected project and propose a safe next implementation slice."
    priority = slugify_filename(req.priority or "normal")
    acceptance = req.acceptance_criteria.strip() or "Define a narrow completion proof, verification command, and documentation update before coding."
    source = req.source_building.strip() or "code-workshop"
    files = []
    for item in detail.get("important_files", [])[:8]:
        if not isinstance(item, dict):
            continue
        path = Path(str(item.get("path", "")))
        if path.exists() and path_is_inside(path, repo):
            files.append(read_project_file_preview(path, limit=900))
    commands = detect_project_commands(repo)
    dirty_count = detail.get("git", {}).get("dirty_count", 0)
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    draft_path = TASKS_DIR / f"{task_id}-{slugify_filename(title)}.md"
    lines = [
        "---",
        f"id: {task_id}",
        f"title: {title}",
        f"target_agent: {target_agent}",
        f"source: ai-town/{source}",
        f"project_id: {project_id}",
        f"project_path: {detail['path']}",
        f"priority: {priority}",
        "status: ready",
        "safety: project-local-code-task-draft",
        "---",
        "",
        f"# {title}",
        "",
        "## Repository Snapshot",
        "",
        f"- Project: {detail['name']} (`{project_id}`)",
        f"- Path: `{detail['path']}`",
        f"- Family: `{detail.get('family', '')}`",
        f"- Branch: `{detail.get('git', {}).get('branch', '')}`",
        f"- Dirty files: `{dirty_count}`",
        f"- Target agent: `{target_agent}`",
        f"- Priority: `{priority}`",
        "",
        "## Request",
        "",
        body,
        "",
        "## Acceptance Criteria",
        "",
        acceptance,
        "",
        "## Current Git Status",
        "",
        "```text",
        str(detail.get("git", {}).get("status_text", ""))[:3000] or "clean or unavailable",
        "```",
        "",
        "## Recent Commits",
        "",
    ]
    lines.extend([f"- {commit}" for commit in detail.get("recent_commits", [])[:5]] or ["- No recent commits found in bounded read."])
    lines.extend([
        "",
        "## Candidate Files",
        "",
    ])
    if files:
        for file_info in files:
            lines.extend([
                f"### {file_info.get('name', 'file')}",
                "",
                f"- Path: `{file_info.get('path', '')}`",
                f"- Bytes: `{file_info.get('bytes', 0)}`",
                "",
                "```text",
                str(file_info.get("preview", file_info.get("error", "")))[:900],
                "```",
                "",
            ])
    else:
        lines.append("- No bounded candidate files were found.")
    lines.extend([
        "",
        "## Verification Candidates",
        "",
    ])
    if commands:
        lines.extend([f"- `{item['command']}` ({item['label']}, {item['safety']})" for item in commands])
    else:
        lines.append("- No obvious verification command detected from bounded project files.")
    lines.extend([
        "",
        "## Agent Handoff Prompt",
        "",
        "```text",
        f"You are working on {detail['name']} at {detail['path']}.",
        f"Task: {body}",
        f"Acceptance: {acceptance}",
        "Inspect current files before editing, preserve unrelated user changes, keep the patch narrow, update verification/docs, and report evidence before any Git operation.",
        "```",
        "",
        "## Safety",
        "",
        "- This draft is stored under the AI Town workspace only.",
        "- It was not sent to an agent runner and did not modify the target repository.",
        "- It did not edit, format, stage, commit, push, install dependencies, run tests, or execute shell commands.",
        "- Future execution must go through explicit command/edit/Git gates.",
    ])
    draft = "\n".join(lines)
    draft_path.write_text(draft, encoding="utf-8")
    task = {
        "id": task_id,
        "title": title,
        "target_agent": target_agent,
        "project_id": project_id,
        "project_name": detail["name"],
        "project_path": detail["path"],
        "status": "ready",
        "priority": priority,
        "acceptance_criteria": acceptance,
        "candidate_file_count": len(files),
        "verification_commands": commands,
        "dirty_count": dirty_count,
        "safety": "project-local-code-task-draft",
        "draft_path": str(draft_path),
        "created_at": time.time(),
    }
    append_local_task(task)
    memory = record_memory_event(
        f"Code task drafted: {title}",
        f"Prepared a safe code-task draft for `{detail['name']}` at `{detail['path']}`.\n\nTarget agent: `{target_agent}`\n\nTask: {body}",
        "ai-town/code-workshop",
    )
    return {
        "status": "saved",
        "safety": "project-local-code-task-draft",
        "task": task,
        "draft_path": str(draft_path),
        "memory_event": memory,
        "preview": draft,
    }


def read_project_file_preview(path: Path, limit: int = 1800) -> dict:
    entry = {"name": path.name, "path": str(path), "exists": path.exists()}
    if not path.exists() or not path.is_file():
        return entry
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        entry.update({
            "bytes": path.stat().st_size,
            "preview": redact_secret_text(text, limit),
            "truncated": len(text) > limit,
        })
    except Exception as exc:
        entry["error"] = str(exc)
    return entry


def detect_project_commands(repo: Path) -> list[dict]:
    commands = []
    if (repo / "backend" / "main.py").exists():
        commands.append({
            "label": "python-compile",
            "command": "python -m py_compile backend\\main.py",
            "argv": ["python", "-m", "py_compile", "backend\\main.py"],
            "safety": "confirm-required",
        })
    if (repo / "tools" / "verify-smoke.ps1").exists():
        commands.append({
            "label": "smoke",
            "command": "powershell -ExecutionPolicy Bypass -File tools\\verify-smoke.ps1",
            "argv": ["powershell", "-ExecutionPolicy", "Bypass", "-File", "tools\\verify-smoke.ps1"],
            "safety": "confirm-required",
        })
    if (repo / "tools" / "capture-visual-smoke.ps1").exists():
        commands.append({
            "label": "visual-smoke",
            "command": "powershell -ExecutionPolicy Bypass -File tools\\capture-visual-smoke.ps1",
            "argv": ["powershell", "-ExecutionPolicy", "Bypass", "-File", "tools\\capture-visual-smoke.ps1"],
            "safety": "confirm-required",
        })
    if (repo / "pyproject.toml").exists() or (repo / "pytest.ini").exists():
        commands.append({"label": "python-tests", "command": "python -m pytest", "argv": ["python", "-m", "pytest"], "safety": "confirm-required"})
    if (repo / "package.json").exists():
        commands.append({"label": "node-tests", "command": "npm test", "argv": ["npm", "test"], "safety": "confirm-required"})
    if (repo / "project.godot").exists():
        commands.append({"label": "godot-headless", "command": "godot --headless --path . --quit", "argv": ["godot", "--headless", "--path", ".", "--quit"], "safety": "confirm-required"})
    return commands[:8]


def project_command_by_label(repo: Path, command_label: str) -> Optional[dict]:
    commands = detect_project_commands(repo)
    preferred = command_label.strip() or ""
    for command in commands:
        if command.get("label") == preferred:
            return command
    return commands[0] if commands else None


def run_project_verification(project_id: str, command_label: str, source_building: str = "code-workshop") -> Optional[dict]:
    detail = project_detail(project_id)
    if not detail:
        return None
    repo = Path(detail["path"])
    command = project_command_by_label(repo, command_label)
    if not command:
        return {
            "status": "missing-command",
            "project_id": project_id,
            "project_name": detail["name"],
            "commands": [],
            "safety": "confirm-required-project-verification",
        }
    argv = command.get("argv", [])
    if not isinstance(argv, list) or not argv:
        return {"status": "blocked", "reason": "Command has no argv allowlist.", "safety": "argv-required"}
    started = time.time()
    timeout_seconds = 180
    try:
        proc = subprocess.run(
            [str(part) for part in argv],
            cwd=str(repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
        returncode = proc.returncode
        stdout = (proc.stdout or "")[:12000]
        stderr = (proc.stderr or "")[:12000]
        status = "passed" if returncode == 0 else "failed"
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        returncode = -1
        stdout = (exc.stdout or "")[:12000] if isinstance(exc.stdout, str) else ""
        stderr = ((exc.stderr or "") if isinstance(exc.stderr, str) else "")[:12000]
        status = "timeout"
        timed_out = True
    finished = time.time()
    PROJECT_VERIFICATION_LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    log_path = PROJECT_VERIFICATION_LOG_DIR / f"{timestamp}-{project_id}-{slugify_filename(str(command.get('label', 'check')))}.json"
    result = {
        "status": status,
        "project_id": project_id,
        "project_name": detail["name"],
        "project_path": detail["path"],
        "command": {key: value for key, value in command.items() if key != "argv"},
        "argv": argv,
        "returncode": returncode,
        "timed_out": timed_out,
        "timeout_seconds": timeout_seconds,
        "duration_seconds": round(finished - started, 3),
        "stdout": stdout,
        "stderr": stderr,
        "log_path": str(log_path),
        "safety": "confirm-required-project-verification",
        "source": f"ai-town/{source_building}",
    }
    log_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    memory = record_memory_event(
        f"Project verification {status}: {detail['name']}",
        f"Ran `{command.get('label', '')}` for `{detail['name']}` through Code Workshop.\n\nReturn code: `{returncode}`\n\nLog: `{log_path}`",
        f"ai-town/{source_building}",
    )
    result["memory_event"] = memory
    return result


def queue_project_verification(project_id: str, req: CodeVerificationJobRequest) -> dict:
    detail = project_detail(project_id)
    if not detail:
        return {"status": "missing", "project_id": project_id}
    repo = Path(detail["path"])
    command = project_command_by_label(repo, req.command_label)
    if not command:
        return {
            "status": "missing-command",
            "project_id": project_id,
            "project_name": detail["name"],
            "commands": detect_project_commands(repo),
            "safety": "confirm-required-project-verification",
        }
    base = {
        "project_id": project_id,
        "project_name": detail["name"],
        "project_path": detail["path"],
        "command": {key: value for key, value in command.items() if key != "argv"},
        "commands": [{key: value for key, value in item.items() if key != "argv"} for item in detect_project_commands(repo)],
        "safety": "confirm-required-project-verification",
        "confirmation_required": CONFIRM_RUN_PROJECT_CHECK,
        "log_dir": str(PROJECT_VERIFICATION_LOG_DIR),
    }
    if req.dry_run:
        return {"status": "dry-run", **base}
    if req.confirmation != CONFIRM_RUN_PROJECT_CHECK:
        return {"status": "confirmation-required", **base}
    job = start_job(
        "project-verification",
        f"Verify {detail['name']} with {command.get('label', '')}",
        run_project_verification,
        project_id,
        str(command.get("label", "")),
        req.source_building.strip() or "code-workshop",
    )
    job["safety"] = "confirm-required-project-verification"
    return {
        "status": "queued",
        "job_id": job["id"],
        "kind": job["kind"],
        "label": job["label"],
        **base,
    }


def create_code_context_pack(project_id: str, req: CodeContextPackRequest) -> Optional[dict]:
    detail = project_detail(project_id)
    if not detail:
        return None
    repo = Path(detail["path"])
    focus = slugify_filename(req.focus or "architecture-tests")
    target_agent = req.target_agent.strip().lower() or "codex"
    if target_agent not in AGENT_PERSONALITIES:
        target_agent = "codex"
    files = []
    for item in detail.get("important_files", [])[:8]:
        if not isinstance(item, dict):
            continue
        path = Path(str(item.get("path", "")))
        if path.exists() and path_is_inside(path, repo):
            files.append(read_project_file_preview(path))
    commands = detect_project_commands(repo)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    CODE_CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    context_path = CODE_CONTEXT_DIR / f"{timestamp}-{project_id}-{focus}.md"
    lines = [
        "---",
        f"project_id: {project_id}",
        f"project_name: {detail['name']}",
        f"target_agent: {target_agent}",
        f"focus: {focus}",
        "safety: project-local-context-pack",
        "---",
        "",
        f"# Code Context Pack - {detail['name']}",
        "",
        "## Repository",
        "",
        f"- Path: `{detail['path']}`",
        f"- Family: `{detail.get('family', '')}`",
        f"- Branch: `{detail.get('git', {}).get('branch', '')}`",
        f"- Dirty files: `{detail.get('git', {}).get('dirty_count', 0)}`",
        f"- Focus: `{focus}`",
        "",
        "## Recent Commits",
        "",
    ]
    commits = detail.get("recent_commits", [])[:5]
    lines.extend([f"- {commit}" for commit in commits] or ["- No recent commits found in bounded read."])
    lines.extend([
        "",
        "## Git Status",
        "",
        "```text",
        str(detail.get("git", {}).get("status_text", ""))[:3000],
        "```",
        "",
        "## Candidate Verification Commands",
        "",
    ])
    if commands:
        lines.extend([f"- `{item['command']}` ({item['label']}, {item['safety']})" for item in commands])
    else:
        lines.append("- No obvious test command detected from bounded project files.")
    lines.extend([
        "",
        "## Important File Previews",
        "",
    ])
    for file_info in files:
        lines.extend([
            f"### {file_info.get('name', 'file')}",
            "",
            f"Path: `{file_info.get('path', '')}`",
            "",
            "```text",
            str(file_info.get("preview", file_info.get("error", "")))[:1800],
            "```",
            "",
        ])
    lines.extend([
        "## Development Brief",
        "",
        f"Target agent: `{target_agent}`",
        "",
        "1. Read this context pack and the selected repository metadata.",
        "2. Propose a narrow implementation slice aligned with existing project docs.",
        "3. Include verification commands and documentation updates before coding.",
        "4. Do not modify files outside the selected repository unless the user explicitly asks.",
        "",
        "## Safety",
        "",
        "- This pack was generated by AI Town Code Workshop.",
        "- It is stored under the AI Town workspace only.",
        "- The selected repository was read but not modified.",
        "- Commands above are suggestions only and were not executed by this endpoint.",
    ])
    preview = "\n".join(lines)
    context_path.write_text(preview, encoding="utf-8")
    memory = record_memory_event(
        f"Code context pack created: {detail['name']}",
        f"Created a safe code context pack for `{detail['name']}` at `{context_path}`.\n\nFocus: `{focus}`\n\nRepository: `{detail['path']}`",
        "ai-town/code-workshop",
    )
    pack = {
        "id": context_path.stem,
        "project_id": project_id,
        "project_name": detail["name"],
        "project_path": detail["path"],
        "focus": focus,
        "target_agent": target_agent,
        "context_path": str(context_path),
        "commands": commands,
        "file_count": len(files),
        "created_at": time.time(),
    }
    return {
        "status": "saved",
        "safety": "project-local-context-pack",
        "context_pack": pack,
        "context_path": str(context_path),
        "memory_event": memory,
        "preview": preview[:9000],
    }


def create_code_patch_plan(project_id: str, req: CodePatchPlanRequest) -> Optional[dict]:
    detail = project_detail(project_id)
    if not detail:
        return None
    repo = Path(detail["path"])
    target_agent = req.target_agent.strip().lower() or "codex"
    if target_agent not in AGENT_PERSONALITIES:
        target_agent = "codex"
    title = req.title.strip() or f"Safe implementation patch plan for {detail['name']}"
    goal = req.goal.strip() or "Plan a narrow code change with tests and documentation updates."
    scope = slugify_filename(req.scope_hint or "small-safe-slice")
    source = req.source_building.strip() or "code-workshop"
    files = []
    for item in detail.get("important_files", [])[:10]:
        if not isinstance(item, dict):
            continue
        path = Path(str(item.get("path", "")))
        if path.exists() and path_is_inside(path, repo):
            files.append(read_project_file_preview(path, limit=900))
    commands = detect_project_commands(repo)
    task_id = uuid.uuid4().hex[:12]
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    CODE_PATCH_PLANS_DIR.mkdir(parents=True, exist_ok=True)
    plan_path = CODE_PATCH_PLANS_DIR / f"{timestamp}-{project_id}-{scope}-{slugify_filename(title)}.md"
    dirty_count = detail.get("git", {}).get("dirty_count", 0)
    lines = [
        "---",
        f"id: {task_id}",
        f"title: {title}",
        f"source: ai-town/{source}",
        f"project_id: {project_id}",
        f"project_name: {detail['name']}",
        f"target_agent: {target_agent}",
        f"scope_hint: {scope}",
        "status: draft",
        "safety: project-local-patch-plan-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Goal",
        "",
        goal,
        "",
        "## Repository Snapshot",
        "",
        f"- Path: `{detail['path']}`",
        f"- Family: `{detail.get('family', '')}`",
        f"- Branch: `{detail.get('git', {}).get('branch', '')}`",
        f"- Dirty files: `{dirty_count}`",
        f"- Target agent: `{target_agent}`",
        "",
        "## Safety Boundary",
        "",
        "- This plan is a project-local handoff document only.",
        "- This endpoint did not edit, format, stage, commit, push, install, run tests, or execute shell commands.",
        "- If dirty files already exist, inspect them before applying any future patch.",
        "- Future code edits must stay inside the selected repository unless explicitly approved.",
        "",
        "## Current Git Status",
        "",
        "```text",
        str(detail.get("git", {}).get("status_text", ""))[:3000] or "clean or unavailable",
        "```",
        "",
        "## Candidate Files To Inspect First",
        "",
    ]
    if files:
        for file_info in files:
            lines.extend([
                f"### {file_info.get('name', 'file')}",
                "",
                f"- Path: `{file_info.get('path', '')}`",
                f"- Bytes: `{file_info.get('bytes', 0)}`",
                "",
                "```text",
                str(file_info.get("preview", file_info.get("error", "")))[:900],
                "```",
                "",
            ])
    else:
        lines.append("- No bounded candidate files were found.")
    lines.extend([
        "",
        "## Proposed Patch Sequence",
        "",
        "1. Re-read the goal, repository snapshot, and existing dirty files.",
        "2. Identify the smallest files and functions that satisfy the goal.",
        "3. Draft the implementation in one narrow behavioral slice.",
        "4. Add or update focused verification/docs proportional to risk.",
        "5. Run only reviewed verification commands through an explicit command gate.",
        "6. Summarize changed files, residual risks, and follow-up tasks before any commit.",
        "",
        "## Verification Candidates",
        "",
    ])
    if commands:
        lines.extend([f"- `{item['command']}` ({item['label']}, {item['safety']})" for item in commands])
    else:
        lines.append("- No obvious verification command detected from bounded project files.")
    lines.extend([
        "",
        "## Agent Handoff Prompt",
        "",
        "```text",
        f"You are working on {detail['name']} at {detail['path']}.",
        f"Goal: {goal}",
        "Use this patch plan as context. Inspect current files before editing, preserve unrelated user changes, keep the slice narrow, update docs/tests as needed, and report verification evidence.",
        "```",
        "",
        "## Confirmation Checklist",
        "",
        "- [ ] User accepts this patch-plan scope.",
        "- [ ] Existing dirty files are understood and preserved.",
        "- [ ] Future edits stay inside the selected repository.",
        "- [ ] Verification command(s) are explicitly chosen before execution.",
        "- [ ] Git staging/commit/push remains separate and confirm-required.",
    ])
    preview = "\n".join(lines)
    plan_path.write_text(preview, encoding="utf-8")
    task = {
        "id": task_id,
        "title": title,
        "target_agent": target_agent,
        "project_id": project_id,
        "project_name": detail["name"],
        "project_path": detail["path"],
        "status": "planned",
        "safety": "project-local-patch-plan-only",
        "draft_path": str(plan_path),
        "created_at": time.time(),
    }
    append_local_task(task)
    memory = record_memory_event(
        f"Code patch plan created: {title}",
        f"Created a project-local patch plan for `{detail['name']}` at `{plan_path}`.\n\nGoal: {goal}\n\nRepository: `{detail['path']}`",
        "ai-town/code-workshop",
    )
    return {
        "status": "saved",
        "safety": "project-local-patch-plan-only",
        "patch_plan": {
            "id": plan_path.stem,
            "task_id": task_id,
            "project_id": project_id,
            "project_name": detail["name"],
            "project_path": detail["path"],
            "target_agent": target_agent,
            "scope_hint": scope,
            "patch_plan_path": str(plan_path),
            "candidate_file_count": len(files),
            "command_count": len(commands),
            "dirty_count": dirty_count,
        },
        "task": task,
        "patch_plan_path": str(plan_path),
        "memory_event": memory,
        "preview": preview[:9000],
    }


def github_repo_card(project: dict) -> dict:
    repo = Path(project["path"])
    remotes = run_git_readonly(repo, ["remote", "-v"], timeout=0.6).splitlines()
    tags = run_git_readonly(repo, ["tag", "--sort=-creatordate"], timeout=0.6).splitlines()[:5]
    return {
        "id": project["id"],
        "name": project["name"],
        "path": project["path"],
        "family": project.get("family", ""),
        "branch": project.get("branch", ""),
        "remotes": remotes[:6],
        "has_remote": len(remotes) > 0,
        "tags": tags,
        "tag_count_sampled": len(tags),
    }


def github_harbor_index() -> dict:
    projects = discover_git_repos()
    repos = [github_repo_card(project) for project in projects]
    return {
        "name": "GitHub Harbor",
        "mode": "read-only",
        "repos": repos,
        "count": len(repos),
        "draft_dir": str(GITHUB_HARBOR_DRAFTS_DIR),
        "drafts": markdown_draft_entries(GITHUB_HARBOR_DRAFTS_DIR, "github-harbor-draft", 10),
        "safe_note": "Harbor reads local Git metadata only. Push, PR, release, and tag creation remain future confirm-required actions.",
    }


def github_repo_detail(project_id: str) -> Optional[dict]:
    detail = project_detail(project_id)
    if not detail:
        return None
    repo = Path(detail["path"])
    detail.update({
        "remotes": run_git_readonly(repo, ["remote", "-v"], timeout=0.8).splitlines()[:10],
        "branches": run_git_readonly(repo, ["branch", "--all", "--verbose", "--no-abbrev"], timeout=0.8).splitlines()[:20],
        "tags": run_git_readonly(repo, ["tag", "--sort=-creatordate"], timeout=0.8).splitlines()[:10],
        "release_notes_draft": "\n".join([
            f"# Release Notes Draft - {detail['name']}",
            "",
            "## Recent commits",
            *[f"- {commit}" for commit in detail.get("recent_commits", [])[:5]],
            "",
            "## Safety",
            "",
            "- This is a read-only draft view. No tag, release, PR, or push was created.",
        ]),
        "safe_actions": [
            {"id": "inspect-git", "label": "Inspect local Git metadata", "safety": "read-only"},
            {"id": "draft-release-notes", "label": "Draft release notes locally", "safety": "preview-only"},
            {"id": "push", "label": "Future push", "safety": "confirm-required"},
            {"id": "create-pr", "label": "Future PR", "safety": "confirm-required"},
        ],
    })
    return detail


def sanitize_cli_text(value: str, limit: int = 2400) -> str:
    text = (value or "").strip()
    text = re.sub(r"(gh[pousr]_[A-Za-z0-9_]+)", "[redacted-token]", text)
    text = re.sub(r"(https?://)([^/@\s]+)@github\.com", r"\1[redacted]@github.com", text)
    return text[:limit]


def run_gh_readonly(repo: Path, args: list[str], timeout: float = 8.0) -> dict:
    if not args:
        return {"ok": False, "exit_code": -1, "stdout": "", "stderr": "missing gh args"}
    if args[0] not in {"auth", "repo", "issue", "release"}:
        return {"ok": False, "exit_code": -1, "stdout": "", "stderr": "blocked non-readonly gh command"}
    try:
        proc = subprocess.run(
            ["gh", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {"ok": False, "exit_code": -1, "stdout": "", "stderr": "gh CLI is not installed or not on PATH"}
    except Exception as exc:
        return {"ok": False, "exit_code": -1, "stdout": "", "stderr": sanitize_cli_text(str(exc), 800)}
    return {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": sanitize_cli_text(proc.stdout, 12000),
        "stderr": sanitize_cli_text(proc.stderr, 4000),
    }


def github_slug_from_remotes(remotes: list[str]) -> str:
    for remote in remotes:
        match = re.search(r"github\.com[:/]([^/\s:]+)/([^/\s]+?)(?:\.git)?(?:\s|$)", remote)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
    return ""


def parse_json_output(result: dict, fallback):
    if not result.get("ok") or not result.get("stdout"):
        return fallback
    try:
        return json.loads(result["stdout"])
    except Exception:
        return fallback


def github_cli_snapshot(project_id: str) -> Optional[dict]:
    detail = github_repo_detail(project_id)
    if not detail:
        return None
    repo = Path(detail["path"])
    auth = run_gh_readonly(repo, ["auth", "status"], timeout=5.0)
    repo_view_result = run_gh_readonly(
        repo,
        ["repo", "view", "--json", "nameWithOwner,url,defaultBranchRef,isPrivate"],
        timeout=8.0,
    )
    repo_view = parse_json_output(repo_view_result, {})
    remotes = detail.get("remotes", [])
    remote_slug = github_slug_from_remotes(remotes)
    name_with_owner = repo_view.get("nameWithOwner") or remote_slug
    issue_result = run_gh_readonly(
        repo,
        ["issue", "list", "--limit", "8", "--json", "number,title,state,labels,assignees,updatedAt,url"],
        timeout=8.0,
    )
    issues = parse_json_output(issue_result, [])
    release_result = run_gh_readonly(
        repo,
        ["release", "list", "--limit", "8", "--json", "tagName,name,isDraft,isPrerelease,publishedAt,url"],
        timeout=8.0,
    )
    releases = parse_json_output(release_result, [])
    release_lines = []
    if not release_result.get("ok") or not isinstance(releases, list):
        fallback = run_gh_readonly(repo, ["release", "list", "--limit", "8"], timeout=8.0)
        release_lines = fallback.get("stdout", "").splitlines()[:8] if fallback.get("ok") else []
        releases = []
        if not release_result.get("ok") and fallback.get("ok"):
            release_result = fallback
    status = "ok"
    if "gh CLI is not installed" in auth.get("stderr", ""):
        status = "gh-unavailable"
    elif not auth.get("ok"):
        status = "auth-unavailable"
    elif not repo_view_result.get("ok"):
        status = "repo-unavailable"
    return {
        "status": status,
        "mode": "read-only-github-cli-snapshot",
        "safety": "read-only-gh-cli-no-write",
        "project_id": project_id,
        "project_name": detail["name"],
        "project_path": detail["path"],
        "repository": {
            "name_with_owner": name_with_owner,
            "url": repo_view.get("url", ""),
            "default_branch": repo_view.get("defaultBranchRef", {}).get("name", "") if isinstance(repo_view.get("defaultBranchRef"), dict) else "",
            "private": repo_view.get("isPrivate", None),
            "remote_slug": remote_slug,
        },
        "auth": {
            "ok": auth.get("ok", False),
            "exit_code": auth.get("exit_code", -1),
            "summary": (auth.get("stdout") or auth.get("stderr", "")).splitlines()[:8],
        },
        "issues": issues if isinstance(issues, list) else [],
        "issue_count": len(issues) if isinstance(issues, list) else 0,
        "issue_status": "ok" if issue_result.get("ok") else "unavailable",
        "issue_error": issue_result.get("stderr", "")[:1200] if not issue_result.get("ok") else "",
        "releases": releases if isinstance(releases, list) else [],
        "release_lines": release_lines,
        "release_count": len(releases) if isinstance(releases, list) else len(release_lines),
        "release_status": "ok" if release_result.get("ok") else "unavailable",
        "release_error": release_result.get("stderr", "")[:1200] if not release_result.get("ok") else "",
        "safe_note": "This snapshot runs fixed GitHub CLI read commands only: auth status, repo view, issue list, and release list. It does not stage, commit, tag, push, create PRs, create issues, or create releases.",
    }


def github_publish_readiness(project_id: str) -> Optional[dict]:
    detail = github_repo_detail(project_id)
    if not detail:
        return None
    repo = Path(detail["path"])
    git = detail.get("git", {})
    remotes = detail.get("remotes", [])
    branch = str(git.get("branch", ""))
    dirty_count = int(git.get("dirty_count", 0) or 0)
    remote_slug = github_slug_from_remotes(remotes)
    upstream = run_git_readonly(repo, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], timeout=0.8)
    ahead_behind = run_git_readonly(repo, ["rev-list", "--left-right", "--count", "HEAD...@{u}"], timeout=0.8)
    diff_stat = run_git_readonly(repo, ["diff", "--stat"], timeout=1.2)
    staged_stat = run_git_readonly(repo, ["diff", "--cached", "--stat"], timeout=1.2)
    verification_entries = plan_verification_entries(8)
    latest_verification = verification_entries[0] if verification_entries else {}
    checks = [
        {"id": "has-remote", "label": "Git remote is configured", "pass": bool(remotes), "detail": remotes[0] if remotes else "No remote detected."},
        {"id": "github-remote", "label": "GitHub remote slug is detectable", "pass": bool(remote_slug), "detail": remote_slug or "No github.com remote found."},
        {"id": "branch", "label": "Current branch is known", "pass": bool(branch), "detail": branch or "Branch unavailable."},
        {"id": "upstream", "label": "Upstream branch can be resolved", "pass": bool(upstream) and "fatal:" not in upstream.lower(), "detail": upstream[:300] or "Upstream unavailable."},
        {"id": "dirty-review", "label": "Working tree changes require review", "pass": dirty_count == 0, "detail": f"{dirty_count} changed entrie(s)."},
        {"id": "verification-log", "label": "Recent verification evidence exists", "pass": bool(latest_verification), "detail": str(latest_verification.get("title", latest_verification.get("path", "")))[:300]},
    ]
    blockers = [item["label"] for item in checks if not item["pass"] and item["id"] in {"has-remote", "github-remote", "branch"}]
    warnings = [item["label"] for item in checks if not item["pass"] and item["id"] not in {"has-remote", "github-remote", "branch"}]
    status = "ready-for-plan"
    if blockers:
        status = "blocked"
    elif warnings:
        status = "needs-review"
    return {
        "name": "GitHub Publish Readiness",
        "mode": "read-only-github-publish-readiness",
        "status": status,
        "safety": "read-only-git-github-readiness",
        "project_id": project_id,
        "project_name": detail["name"],
        "project_path": detail["path"],
        "branch": branch,
        "dirty_count": dirty_count,
        "remote_slug": remote_slug,
        "upstream": upstream,
        "ahead_behind": ahead_behind,
        "checks": checks,
        "checks_passed": len([item for item in checks if item["pass"]]),
        "checks_total": len(checks),
        "blockers": blockers,
        "warnings": warnings,
        "diff_stat": diff_stat[:2000],
        "staged_stat": staged_stat[:2000],
        "recent_commits": detail.get("recent_commits", [])[:8],
        "verification_entries": verification_entries,
        "confirmation_required": CONFIRM_GITHUB_PUBLISH_PLAN,
        "safe_note": "Publish readiness only reads local Git metadata and local verification evidence. It does not stage, commit, tag, push, create PRs, create issues, create releases, or call GitHub write APIs.",
    }


def create_github_publish_plan(project_id: str, req: GitHubPublishPlanRequest) -> Optional[dict]:
    readiness = github_publish_readiness(project_id)
    if not readiness:
        return None
    publish_type = slugify_filename(req.publish_type or "pull-request")
    if publish_type not in {"pull-request", "issue", "release"}:
        publish_type = "pull-request"
    title = req.title.strip() or f"{readiness['project_name']} GitHub publish plan"
    body = req.body.strip() or "Review branch, remotes, dirty files, verification evidence, and public text before any GitHub write."
    target_branch = slugify_filename(req.target_branch or "main")
    source = req.source_building.strip() or "github-harbor"
    if req.confirmation != CONFIRM_GITHUB_PUBLISH_PLAN:
        return {
            "status": "confirmation-required",
            "safety": "github-publish-plan-only",
            "confirmation_required": CONFIRM_GITHUB_PUBLISH_PLAN,
            "project_id": project_id,
            "publish_type": publish_type,
            "readiness": readiness,
            "preview": f"Create a local {publish_type} publish plan for `{readiness['project_name']}` targeting `{target_branch}`. No Git or GitHub write action will run.",
        }
    GITHUB_HARBOR_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    plan_path = GITHUB_HARBOR_DRAFTS_DIR / f"{timestamp}-{project_id}-{publish_type}-publish-plan-{slugify_filename(title)}.md"
    lines = [
        "---",
        f"title: {title}",
        f"publish_type: {publish_type}",
        f"source: ai-town/{source}",
        f"project_id: {project_id}",
        f"project_name: {readiness['project_name']}",
        f"target_branch: {target_branch}",
        "status: publish-plan",
        "safety: github-publish-plan-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Operator Notes",
        "",
        body,
        "",
        "## Readiness",
        "",
        f"- Status: `{readiness.get('status', '')}`",
        f"- Branch: `{readiness.get('branch', '')}`",
        f"- Target branch: `{target_branch}`",
        f"- Remote slug: `{readiness.get('remote_slug', '')}`",
        f"- Upstream: `{readiness.get('upstream', '')}`",
        f"- Ahead/behind: `{readiness.get('ahead_behind', '')}`",
        f"- Dirty files: `{readiness.get('dirty_count', 0)}`",
        f"- Checks: `{readiness.get('checks_passed', 0)} / {readiness.get('checks_total', 0)}`",
        "",
        "## Checks",
        "",
    ]
    for check in readiness.get("checks", []):
        mark = "x" if check.get("pass") else " "
        lines.append(f"- [{mark}] {check.get('label', '')}: {check.get('detail', '')}")
    lines.extend([
        "",
        "## Recent Commits",
        "",
    ])
    lines.extend([f"- {commit}" for commit in readiness.get("recent_commits", [])] or ["- No recent commits returned."])
    lines.extend([
        "",
        "## Diff Stat",
        "",
        "```text",
        readiness.get("diff_stat", "") or "No unstaged diff stat.",
        "```",
        "",
        "## Staged Stat",
        "",
        "```text",
        readiness.get("staged_stat", "") or "No staged diff stat.",
        "```",
        "",
        "## Future GitHub Text Draft",
        "",
        "```markdown",
        f"Title: {title}",
        "",
        body,
        "",
        "Verification:",
    ])
    for entry in readiness.get("verification_entries", [])[:5]:
        lines.append(f"- {entry.get('title', entry.get('path', 'verification evidence'))}")
    lines.extend([
        "```",
        "",
        "## Safety Boundary",
        "",
        "- This plan did not stage, commit, tag, push, create a PR, create an issue, create a release, or call GitHub write APIs.",
        "- A future write workflow must require explicit user approval and fresh verification evidence.",
        "- Review dirty files carefully because this workspace is shared with other agents.",
    ])
    content = "\n".join(lines)
    plan_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"GitHub publish plan created: {title}",
        f"Created `{publish_type}` publish plan for `{readiness['project_name']}` at `{plan_path}`. No Git or GitHub write action was performed.",
        "ai-town/github-harbor",
    )
    return {
        "status": "saved",
        "safety": "github-publish-plan-only",
        "plan_path": str(plan_path),
        "memory_event": memory,
        "publish_type": publish_type,
        "readiness": readiness,
        "preview": content[:9000],
    }


def create_github_harbor_draft(project_id: str, req: GitHubHarborDraftRequest) -> Optional[dict]:
    detail = github_repo_detail(project_id)
    if not detail:
        return None
    draft_type = slugify_filename(req.draft_type or "pull-request")
    if draft_type not in {"pull-request", "issue", "release"}:
        draft_type = "pull-request"
    title = req.title.strip() or f"{detail['name']} GitHub handoff draft"
    body = req.body.strip() or "Prepare a safe GitHub handoff for this repository."
    source = req.source_building.strip() or "github-harbor"
    target_branch = slugify_filename(req.target_branch or "main")
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    GITHUB_HARBOR_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    draft_path = GITHUB_HARBOR_DRAFTS_DIR / f"{timestamp}-{project_id}-{draft_type}-{slugify_filename(title)}.md"
    git = detail.get("git", {})
    remote_lines = detail.get("remotes", [])
    commit_lines = detail.get("recent_commits", [])[:8]
    type_label = {
        "pull-request": "Pull Request Draft",
        "issue": "Issue Draft",
        "release": "Release Draft",
    }.get(draft_type, "GitHub Draft")
    content = "\n".join([
        "---",
        f"title: {title}",
        f"draft_type: {draft_type}",
        f"source: ai-town/{source}",
        f"project_id: {project_id}",
        f"project_name: {detail['name']}",
        f"target_branch: {target_branch}",
        "status: draft",
        "safety: github-handoff-draft-only",
        "---",
        "",
        f"# {type_label}: {title}",
        "",
        "## Body",
        "",
        body,
        "",
        "## Repository Snapshot",
        "",
        f"- Path: `{detail['path']}`",
        f"- Current branch: `{git.get('branch', '')}`",
        f"- Target branch: `{target_branch}`",
        f"- Dirty files: `{git.get('dirty_count', 0)}`",
        f"- Has remote: `{bool(remote_lines)}`",
        "",
        "## Remotes",
        "",
        *([f"- `{line}`" for line in remote_lines[:10]] or ["- No remote detected in bounded local Git read."]),
        "",
        "## Recent Commits",
        "",
        *([f"- {line}" for line in commit_lines] or ["- No recent commit output detected."]),
        "",
        "## Local Git Status",
        "",
        "```text",
        str(git.get("status_text", ""))[:3000] or "clean or unavailable",
        "```",
        "",
        "## Suggested GitHub Handoff",
        "",
        "```markdown",
        f"Title: {title}",
        "",
        body,
        "",
        "Recent commits:",
        *[f"- {line}" for line in commit_lines[:5]],
        "```",
        "",
        "## Safety Boundary",
        "",
        "- This draft did not call GitHub APIs.",
        "- This draft did not stage, commit, tag, push, create a PR, create an issue, or create a release.",
        "- Review dirty files, remotes, branches, and verification evidence before any future GitHub write.",
        "- GitHub writes remain a separate confirm-required workflow.",
        "",
        "## Confirmation Checklist",
        "",
        "- [ ] Local changes are reviewed and intentionally included or excluded.",
        "- [ ] Tests or smoke checks are current enough for the handoff.",
        "- [ ] Target branch and remote are correct.",
        "- [ ] No secrets, private paths, or internal-only notes are included in public text.",
        "- [ ] User explicitly approves any future GitHub write action.",
    ])
    draft_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"GitHub Harbor draft created: {title}",
        f"Created `{draft_type}` handoff draft for `{detail['name']}` at `{draft_path}`. No GitHub or Git write action was performed.",
        "ai-town/github-harbor",
    )
    return {
        "status": "saved",
        "safety": "github-handoff-draft-only",
        "draft_path": str(draft_path),
        "memory_event": memory,
        "draft": {
            "id": draft_path.stem,
            "draft_type": draft_type,
            "title": title,
            "project_id": project_id,
            "project_name": detail["name"],
            "project_path": detail["path"],
            "branch": git.get("branch", ""),
            "target_branch": target_branch,
            "dirty_count": git.get("dirty_count", 0),
            "remote_count": len(remote_lines),
            "commit_count": len(commit_lines),
        },
        "preview": content[:9000],
    }


def release_readiness_file_entries() -> list[dict]:
    entries = []
    for spec in RELEASE_READINESS_FILES:
        path = spec["path"]
        entry = {
            "id": spec["id"],
            "name": spec["name"],
            "path": str(path),
            "required": spec["required"],
            "role": spec["role"],
            "exists": path.exists(),
            "kind": "file" if path.is_file() else "dir" if path.is_dir() else "missing",
            "bytes": 0,
            "preview": "",
            "status": "missing",
        }
        if path.exists():
            try:
                stat = path.stat()
                entry["bytes"] = stat.st_size
                entry["updated"] = stat.st_mtime
                entry["status"] = "present"
                if path.is_file() and path.suffix.lower() in {".md", ".txt"}:
                    entry["preview"] = first_meaningful_lines(path, 4, 500)
            except Exception as exc:
                entry["status"] = "error"
                entry["error"] = str(exc)
        entries.append(entry)
    return entries


def release_plaza_overview() -> dict:
    files = release_readiness_file_entries()
    missing_required = [item for item in files if item.get("required") and not item.get("exists")]
    visual = next((item for item in files if item["id"] == "visual-smoke"), {})
    visual_manifest = visual_manifest_audit()
    build_readiness = build_readiness_audit()
    export_tool = godot_export_tool_audit()
    packaged_launch = packaged_launch_readiness()
    release_manifest = release_package_manifest_audit()
    smoke_log = plan_verification_entries(8)
    git_status = run_git_readonly(PROJECT_ROOT, ["status", "--short"], timeout=1.0).splitlines()
    remotes = run_git_readonly(PROJECT_ROOT, ["remote", "-v"], timeout=0.8).splitlines()
    branch = run_git_readonly(PROJECT_ROOT, ["branch", "--show-current"], timeout=0.6).strip()
    tags = run_git_readonly(PROJECT_ROOT, ["tag", "--sort=-creatordate"], timeout=0.8).splitlines()[:8]
    drafts = markdown_draft_entries(RELEASE_DRAFTS_DIR, "release-checklist", 20)
    reports = markdown_draft_entries(RELEASE_READINESS_REPORTS_DIR, "release-readiness-report", 10)
    vertical_proofs = markdown_draft_entries(VERTICAL_SLICE_PROOFS_DIR, "vertical-slice-proof", 5)
    readiness_score = len([item for item in files if item.get("exists") and item.get("required")])
    required_count = len([item for item in files if item.get("required")])
    return {
        "name": "Version Release Plaza",
        "mode": "release-readiness-preview-plus-local-checklists",
        "draft_dir": str(RELEASE_DRAFTS_DIR),
        "files": files,
        "file_count": len(files),
        "required_count": required_count,
        "ready_required_count": readiness_score,
        "missing_required": missing_required,
        "missing_required_count": len(missing_required),
        "visual_artifact": visual,
        "visual_manifest": visual_manifest,
        "build_readiness": build_readiness,
        "export_tool": export_tool,
        "packaged_launch": packaged_launch,
        "release_manifest": release_manifest,
        "verification_log": smoke_log,
        "verification_log_count": len(smoke_log),
        "git": {
            "branch": branch,
            "status_count": len(git_status),
            "status_sample": git_status[:20],
            "remotes": remotes[:8],
            "remote_count": len(remotes),
            "tags": tags,
            "tag_count_sampled": len(tags),
        },
        "drafts": drafts,
        "draft_count": len(drafts),
        "report_dir": str(RELEASE_READINESS_REPORTS_DIR),
        "reports": reports,
        "report_count": len(reports),
        "vertical_slice_proofs": vertical_proofs,
        "vertical_slice_proof_count": len(vertical_proofs),
        "release_gates": [
            "README explains Godot-first launch and real-work safety boundaries.",
            "LICENSE, CONTRIBUTING, SECURITY, and ROADMAP exist before public release.",
            "Godot project, launchers, pinned binaries, Windows export preset, export preflight script, packaged launcher, and release package manifest are present.",
            "Visual smoke screenshot, all-room visual manifest, and smoke-test logs are fresh enough for release notes.",
            "GitHub write actions remain explicit, separate, and confirm-required.",
        ],
        "safe_note": "Version Release Plaza reads local release-readiness evidence and writes checklist drafts under workspace/release-drafts only. It does not commit, stage, tag, push, create PRs, create releases, overwrite docs, run exports, launch packaged sessions, kill processes, or change remotes.",
    }


def create_release_checklist_draft(req: ReleaseChecklistDraftRequest) -> dict:
    title = req.title.strip() or "AI Town release readiness checklist"
    body = req.body.strip() or "Summarize the release target, missing public artifacts, verification evidence, and next safe GitHub action."
    release_target = slugify_filename(req.release_target or "local-preview")
    source = req.source_building.strip() or "version-release-plaza"
    overview = release_plaza_overview()
    RELEASE_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    draft_path = RELEASE_DRAFTS_DIR / f"{timestamp}-{release_target}-{slugify_filename(title)}.md"
    missing = overview.get("missing_required", [])
    content = "\n".join([
        "---",
        f"title: {title}",
        f"release_target: {release_target}",
        f"source: ai-town/{source}",
        "status: draft",
        "safety: release-checklist-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Release Target",
        "",
        body,
        "",
        "## Readiness Snapshot",
        "",
        f"- Required artifacts ready: {overview.get('ready_required_count', 0)} / {overview.get('required_count', 0)}",
        f"- Missing required artifacts: {overview.get('missing_required_count', 0)}",
        f"- Git branch: {overview.get('git', {}).get('branch', '')}",
        f"- Git status entries: {overview.get('git', {}).get('status_count', 0)}",
        f"- Verification log entries sampled: {overview.get('verification_log_count', 0)}",
        "",
        "## Missing Required Artifacts",
        "",
    ])
    if missing:
        content += "\n".join([f"- {item.get('name', item.get('id', 'artifact'))}: {item.get('path', '')}" for item in missing])
    else:
        content += "- None from the current release-readiness file list."
    content += "\n\n## Release Gates\n\n"
    content += "\n".join([f"- {gate}" for gate in overview.get("release_gates", [])])
    content += "\n\n## Safety\n\n- This draft did not stage, commit, tag, push, create a PR, create a release, overwrite docs, or change remotes.\n- Route GitHub writes through future confirm-required release workflows."
    draft_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Release checklist drafted: {title}",
        f"Created project-local release checklist `{title}` for `{release_target}`.\n\nDraft: `{draft_path}`",
        "ai-town/version-release-plaza",
    )
    return {
        "status": "saved",
        "draft_path": str(draft_path),
        "memory_event": memory,
        "preview": content,
        "release_target": release_target,
        "safety": "release-checklist-only",
    }


def create_release_readiness_report(req: ReleaseReadinessReportRequest) -> dict:
    title = req.title.strip() or "AI Town release readiness report"
    release_target = slugify_filename(req.release_target or "local-preview")
    source = req.source_building.strip() or "version-release-plaza"
    overview = release_plaza_overview()
    RELEASE_READINESS_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    report_path = RELEASE_READINESS_REPORTS_DIR / f"{timestamp}-{release_target}-{slugify_filename(title)}.md"
    git = overview.get("git", {})
    vertical_proofs = overview.get("vertical_slice_proofs", [])
    permission = permission_receipts(8)
    harbor = github_harbor_index()
    gates = [
        ("Required public artifacts", overview.get("missing_required_count", 0) == 0, f"{overview.get('ready_required_count', 0)} / {overview.get('required_count', 0)} ready"),
        ("Visual evidence", bool(overview.get("visual_artifact", {}).get("exists")), str(overview.get("visual_artifact", {}).get("path", ""))),
        ("All-room visual manifest", bool(overview.get("visual_manifest", {}).get("coverage_ok")), f"{overview.get('visual_manifest', {}).get('valid_screenshot_count', 0)} / {overview.get('visual_manifest', {}).get('registry_room_count', 0)} verified"),
        ("Godot build readiness", overview.get("build_readiness", {}).get("status") == "ok", f"{overview.get('build_readiness', {}).get('checks_passed', 0)} / {overview.get('build_readiness', {}).get('checks_total', 0)} checks"),
        ("Godot export tool", overview.get("export_tool", {}).get("script_exists") and overview.get("export_tool", {}).get("report_exists"), f"latest={overview.get('export_tool', {}).get('status', 'missing')} blockers={overview.get('export_tool', {}).get('blocker_count', 0)}"),
        ("Packaged launcher", overview.get("packaged_launch", {}).get("status") == "ok", f"{overview.get('packaged_launch', {}).get('checks_passed', 0)} / {overview.get('packaged_launch', {}).get('checks_total', 0)} checks"),
        ("Release package manifest", overview.get("release_manifest", {}).get("status") == "ok", f"{overview.get('release_manifest', {}).get('file_count', 0)} files, exe={overview.get('release_manifest', {}).get('exe_bytes', 0)} bytes"),
        ("Verification log", overview.get("verification_log_count", 0) > 0, f"{overview.get('verification_log_count', 0)} PLAN entries"),
        ("Vertical slice proof", len(vertical_proofs) > 0, f"{len(vertical_proofs)} proof report(s)"),
        ("Git remotes visible", git.get("remote_count", 0) > 0, f"{git.get('remote_count', 0)} remote rows"),
        ("Git status disclosed", True, f"{git.get('status_count', 0)} working-tree entries"),
        ("Permission receipts", permission.get("count", 0) > 0, f"{permission.get('count', 0)} receipts"),
        ("Harbor repo docks", harbor.get("repo_count", 0) > 0, f"{harbor.get('repo_count', 0)} local repos"),
    ]
    passed = [gate for gate in gates if gate[1]]
    content = "\n".join([
        "---",
        f"title: {title}",
        f"release_target: {release_target}",
        f"source: ai-town/{source}",
        "status: recorded",
        "safety: release-readiness-report-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Summary",
        "",
        f"- release_target: `{release_target}`",
        f"- gates_passed: {len(passed)} / {len(gates)}",
        f"- generated_at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Gates",
        "",
        *[f"- [{'x' if ok else ' '}] {name}: {detail}" for name, ok, detail in gates],
        "",
        "## Public Artifact Set",
        "",
        *[f"- {item.get('name', item.get('id', 'artifact'))}: status={item.get('status', '')} required={item.get('required', False)} path=`{item.get('path', '')}`" for item in overview.get("files", [])],
        "",
        "## Git Snapshot",
        "",
        f"- branch: `{git.get('branch', '')}`",
        f"- status_entries: {git.get('status_count', 0)}",
        f"- remotes: {git.get('remote_count', 0)}",
        f"- sampled_tags: {git.get('tag_count_sampled', 0)}",
        "",
        "## Vertical Slice Proofs",
        "",
        *[f"- {proof.get('title', proof.get('id', 'proof'))}: `{proof.get('path', '')}`" for proof in vertical_proofs],
        "",
        "## Visual Manifest",
        "",
        f"- status: {overview.get('visual_manifest', {}).get('status', '')}",
        f"- coverage_ok: {overview.get('visual_manifest', {}).get('coverage_ok', False)}",
        f"- screenshots: {overview.get('visual_manifest', {}).get('valid_screenshot_count', 0)} / {overview.get('visual_manifest', {}).get('registry_room_count', 0)}",
        f"- manifest: `{overview.get('visual_manifest', {}).get('manifest_path', '')}`",
        "",
        "## Godot Build Readiness",
        "",
        f"- status: {overview.get('build_readiness', {}).get('status', '')}",
        f"- checks: {overview.get('build_readiness', {}).get('checks_passed', 0)} / {overview.get('build_readiness', {}).get('checks_total', 0)}",
        f"- export: `{overview.get('build_readiness', {}).get('export', {}).get('export_path', '')}`",
        "",
        "## Godot Export Tool",
        "",
        f"- script: `{overview.get('export_tool', {}).get('script_path', '')}`",
        f"- latest_status: {overview.get('export_tool', {}).get('status', '')}",
        f"- latest_report: `{overview.get('export_tool', {}).get('report_path', '')}`",
        f"- output_exists: {overview.get('export_tool', {}).get('output_exists', False)}",
        f"- blockers: {overview.get('export_tool', {}).get('blocker_count', 0)}",
        "",
        "## Packaged Launcher",
        "",
        f"- status: {overview.get('packaged_launch', {}).get('status', '')}",
        f"- checks: {overview.get('packaged_launch', {}).get('checks_passed', 0)} / {overview.get('packaged_launch', {}).get('checks_total', 0)}",
        f"- launcher: `{overview.get('packaged_launch', {}).get('launcher_path', '')}`",
        f"- game: `{overview.get('packaged_launch', {}).get('game_path', '')}`",
        "",
        "## Release Package Manifest",
        "",
        f"- status: {overview.get('release_manifest', {}).get('status', '')}",
        f"- manifest: `{overview.get('release_manifest', {}).get('manifest_path', '')}`",
        f"- files: {overview.get('release_manifest', {}).get('file_count', 0)}",
        f"- exe_sha256: `{overview.get('release_manifest', {}).get('exe_sha256', '')}`",
        "",
        "## Permission Receipts",
        "",
        f"- count: {permission.get('count', 0)}",
        f"- classes: {permission.get('counts', {})}",
        "",
        "## Safety",
        "",
        "- This report did not stage, commit, tag, push, create a PR, create an issue, create a release, overwrite docs, run exports, kill processes, or change remotes.",
        "- GitHub writes remain future confirm-required workflows.",
        "- Dirty Git state is disclosed as release readiness evidence, not changed.",
    ])
    report_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Release readiness report recorded: {title}",
        f"Recorded release readiness report at `{report_path}` with {len(passed)} / {len(gates)} gates passing.",
        "ai-town/version-release-plaza",
    )
    return {
        "status": "saved",
        "safety": "release-readiness-report-only",
        "report_path": str(report_path),
        "memory_event": memory,
        "release_target": release_target,
        "gates_passed": len(passed),
        "gates_total": len(gates),
        "preview": content,
    }


def plugin_candidate_kind(path: Path) -> str:
    name = path.name.lower()
    suffix = path.suffix.lower()
    if path.is_dir() and (path / "SKILL.md").exists():
        return "skill"
    if path.is_dir():
        if "plugin" in name or "extension" in name:
            return "plugin-folder"
        if "skill" in name:
            return "skill-folder"
        if "tool" in name:
            return "tool-folder"
        return "folder"
    if suffix == ".json":
        return "json-registry"
    if suffix == ".gd":
        return "godot-script"
    if suffix in {".ps1", ".cmd", ".py"}:
        return "local-script"
    if suffix == ".md":
        if name == "skill.md":
            return "skill-manifest"
        return "docs"
    if suffix in {".toml", ".yaml", ".yml"}:
        return "config"
    return "asset"


def bounded_plugin_candidates(root: Path, limit: int = 28) -> list[dict]:
    if not root.exists():
        return []
    candidates = []
    blocked_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", ".godot", ".import", "exports"}
    try:
        if root.is_file():
            paths = [root]
        else:
            paths = []
            for current, dirs, files in os.walk(root):
                dirs[:] = [item for item in dirs if item not in blocked_dirs]
                current_path = Path(current)
                depth = len(current_path.relative_to(root).parts) if current_path != root else 0
                if depth > 3:
                    dirs[:] = []
                    continue
                if (current_path / "SKILL.md").exists() or any(token in current_path.name.lower() for token in ["plugin", "extension", "skill", "tool"]):
                    paths.append(current_path)
                for filename in files:
                    path = current_path / filename
                    lower_name = filename.lower()
                    if path.suffix.lower() in PLUGIN_FILE_EXTENSIONS or lower_name in {"manifest.json", "plugin.cfg", "skill.md"}:
                        paths.append(path)
                    if len(paths) >= limit:
                        break
                if len(paths) >= limit:
                    break
        seen = set()
        for path in paths:
            try:
                key = str(path.resolve())
                if key in seen:
                    continue
                seen.add(key)
                stat = path.stat()
                rel = str(path.relative_to(root)) if path != root else "."
                preview = []
                if path.is_file() and path.suffix.lower() in {".md", ".json", ".toml", ".yaml", ".yml", ".gd", ".py"}:
                    preview = first_meaningful_lines(path, 3)
                candidates.append({
                    "id": slugify_filename(rel),
                    "name": path.name,
                    "relative_path": rel,
                    "path": str(path),
                    "kind": plugin_candidate_kind(path),
                    "bytes": stat.st_size if path.is_file() else 0,
                    "updated": stat.st_mtime,
                    "preview": preview,
                })
            except Exception:
                continue
    except Exception:
        return []
    return candidates[:limit]


def plugin_registry_inventory() -> list[dict]:
    registries = [
        {"id": "buildings", "name": "Building Registry", "path": BUILDING_REGISTRY_PATH, "role": "playable room/building manifest"},
        {"id": "agents", "name": "Agent Registry", "path": AGENT_REGISTRY_PATH, "role": "NPC manifest"},
        {"id": "model-profiles", "name": "Model Profile Registry", "path": MODEL_PROFILE_REGISTRY_PATH, "role": "API/model profile manifest"},
        {"id": "workspaces", "name": "Workspace Registry", "path": WORKSPACE_REGISTRY_PATH, "role": "allowlisted local workspace manifest"},
        {"id": "quests", "name": "Quest Registry", "path": QUEST_REGISTRY_PATH, "role": "playable work quest and reward manifest"},
        {"id": "npc-quests", "name": "NPC Quest Registry", "path": NPC_QUEST_REGISTRY_PATH, "role": "room NPC quest-chain manifest"},
        {"id": "room-scenes", "name": "Room Scene Registry", "path": ROOM_SCENE_REGISTRY_PATH, "role": "interior room scene and station manifest"},
        {"id": "map-decor", "name": "Map Decor Registry", "path": MAP_DECOR_REGISTRY_PATH, "role": "clickable plaza landmark manifest"},
        {"id": "districts", "name": "District Registry", "path": DISTRICT_REGISTRY_PATH, "role": "map district and teleport manifest"},
        {"id": "plugin-manifests", "name": "Plugin Manifest Registry", "path": PLUGIN_MANIFEST_REGISTRY_PATH, "role": "typed extension manifest and activation-gate manifest"},
    ]
    inventory = []
    health_by_id = {
        item.get("id", ""): item
        for item in registry_health_overview().get("registries", [])
        if isinstance(item, dict)
    }
    for registry in registries:
        path = registry["path"]
        if registry["id"] == "workspaces":
            items = load_workspace_registry()
        elif registry["id"] == "quests":
            items = load_quest_registry()
        else:
            items = load_json_registry(path)
        health = health_by_id.get(registry["id"], {})
        inventory.append({
            **registry,
            "path": str(path),
            "exists": path.exists(),
            "count": len(items),
            "status": health.get("status", "online" if items else "missing-or-empty"),
            "error_count": health.get("error_count", 0),
            "warning_count": health.get("warning_count", 0),
        })
    return inventory


def plugin_manifest_catalog() -> dict:
    manifests = load_json_registry(PLUGIN_MANIFEST_REGISTRY_PATH)
    building_ids = {str(item.get("id", "")) for item in load_json_registry(BUILDING_REGISTRY_PATH)}
    manifest_entries = []
    category_counts: dict[str, int] = {}
    safety_counts: dict[str, int] = {}
    activation_counts: dict[str, int] = {}
    warnings = []
    required_fields = ["id", "name", "category", "version", "owner_building", "safety", "activation_mode", "permissions", "files", "verification"]
    for manifest in manifests:
        manifest_id = str(manifest.get("id", ""))
        category = str(manifest.get("category", "uncategorized"))
        safety = str(manifest.get("safety", "unspecified"))
        activation_mode = str(manifest.get("activation_mode", "review-required"))
        owner = str(manifest.get("owner_building", ""))
        missing = [field for field in required_fields if field not in manifest or manifest.get(field) in ("", None, [])]
        if owner and owner not in building_ids:
            warnings.append(f"{manifest_id} owner_building `{owner}` is not in building registry.")
        if missing:
            warnings.append(f"{manifest_id} missing fields: {', '.join(missing)}")
        category_counts[category] = category_counts.get(category, 0) + 1
        safety_counts[safety] = safety_counts.get(safety, 0) + 1
        activation_counts[activation_mode] = activation_counts.get(activation_mode, 0) + 1
        manifest_entries.append({
            "id": manifest_id,
            "name": manifest.get("name", manifest_id),
            "category": category,
            "version": manifest.get("version", ""),
            "owner_building": owner,
            "safety": safety,
            "activation_mode": activation_mode,
            "permissions": manifest.get("permissions", []),
            "files": manifest.get("files", []),
            "endpoints": manifest.get("endpoints", []),
            "verification": manifest.get("verification", []),
            "rollback": manifest.get("rollback", []),
            "status": "warning" if missing or (owner and owner not in building_ids) else "ready-for-plan",
            "missing_fields": missing,
        })
    return {
        "name": "Plugin Manifests",
        "mode": "read-only-typed-plugin-manifest-audit",
        "path": str(PLUGIN_MANIFEST_REGISTRY_PATH),
        "exists": PLUGIN_MANIFEST_REGISTRY_PATH.exists(),
        "manifests": manifest_entries,
        "manifest_count": len(manifest_entries),
        "category_counts": category_counts,
        "safety_counts": safety_counts,
        "activation_counts": activation_counts,
        "warnings": warnings[:16],
        "warning_count": len(warnings),
        "required_fields": required_fields,
        "confirmation_required": CONFIRM_PLUGIN_ACTIVATION_PLAN,
        "safe_note": "Plugin manifests are read-only typed extension descriptors. Activation requires a separate review plan and does not install plugins, run package managers, execute scripts, edit registries, download assets, change skills, or invoke agents.",
    }


def plugin_manifest_by_id(manifest_id: str) -> dict | None:
    normalized = slugify_filename(manifest_id or "")
    for manifest in plugin_manifest_catalog().get("manifests", []):
        if manifest.get("id") == normalized:
            return manifest
    return None


def plugin_registry_overview() -> dict:
    roots = []
    all_candidates = []
    kind_counts: dict[str, int] = {}
    for spec in PLUGIN_REGISTRY_ROOTS:
        path = spec["path"]
        candidates = bounded_plugin_candidates(path)
        for candidate in candidates:
            candidate["root_id"] = spec["id"]
            candidate["root_name"] = spec["name"]
            kind = candidate.get("kind", "unknown")
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
        all_candidates.extend(candidates)
        roots.append({
            "id": spec["id"],
            "name": spec["name"],
            "path": str(path),
            "role": spec["role"],
            "exists": path.exists(),
            "candidate_count": len(candidates),
        })
    drafts = markdown_draft_entries(PLUGIN_DRAFTS_DIR, "plugin-draft", 20)
    inventory = plugin_registry_inventory()
    registry_health = registry_health_overview()
    manifest_catalog = plugin_manifest_catalog()
    return {
        "name": "Plugin Registry",
        "mode": "read-only-extension-map-plus-local-plugin-drafts",
        "draft_dir": str(PLUGIN_DRAFTS_DIR),
        "roots": roots,
        "root_count": len(roots),
        "registries": inventory,
        "registry_count": len(inventory),
        "registry_health": registry_health,
        "manifest_catalog": manifest_catalog,
        "manifest_count": manifest_catalog.get("manifest_count", 0),
        "candidates": sorted(all_candidates, key=lambda item: (item.get("root_id", ""), item.get("relative_path", "")))[:80],
        "candidate_count": len(all_candidates),
        "kind_counts": kind_counts,
        "drafts": drafts,
        "draft_count": len(drafts),
        "extension_gates": [
            "Describe manifest shape, room ownership, and safety class before implementation.",
            "Keep plugin installation, external downloads, and command execution outside this room.",
            "Verify backend endpoint, Godot room wiring, registry JSON, smoke test, and visual smoke.",
            f"Create an activation plan with `{CONFIRM_PLUGIN_ACTIVATION_PLAN}` before any plugin implementation or registry edit.",
            "Promote a draft into code only after explicit implementation request or confirm-required workflow.",
        ],
        "safe_note": "Plugin Registry inventories local extension candidates and writes plugin proposal drafts under workspace/plugin-drafts only. It does not install plugins, run package managers, execute scripts, edit registries, download assets, change skills, or invoke agents.",
    }


def create_plugin_draft(req: PluginDraftRequest) -> dict:
    title = req.title.strip() or "AI Town plugin proposal"
    body = req.body.strip() or "Describe the extension idea, safety boundary, and verification proof."
    plugin_id = slugify_filename(req.plugin_id or "ai-town-extension")
    category = slugify_filename(req.category or "workflow")
    source = req.source_building.strip() or "plugin-registry"
    overview = plugin_registry_overview()
    PLUGIN_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    draft_path = PLUGIN_DRAFTS_DIR / f"{timestamp}-{category}-{plugin_id}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"plugin_id: {plugin_id}",
        f"category: {category}",
        f"source: ai-town/{source}",
        "status: draft",
        "safety: plugin-proposal-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Proposal",
        "",
        body,
        "",
        "## Current Extension Map",
        "",
        f"- Roots inspected: {overview.get('root_count', 0)}",
        f"- Candidates sampled: {overview.get('candidate_count', 0)}",
        f"- Registries online: {len([item for item in overview.get('registries', []) if item.get('exists')])} / {overview.get('registry_count', 0)}",
        f"- Candidate types: {json.dumps(overview.get('kind_counts', {}), ensure_ascii=False)}",
        "",
        "## Extension Gates",
        "",
    ])
    content += "\n".join([f"- {gate}" for gate in overview.get("extension_gates", [])])
    content += "\n\n## Safety\n\n- This draft did not install plugins, run package managers, execute scripts, edit registries, download assets, change skills, or invoke agents.\n- Promote it through a separate implementation slice with smoke and visual verification."
    draft_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Plugin proposal drafted: {title}",
        f"Created project-local plugin proposal `{title}` for `{plugin_id}`.\n\nDraft: `{draft_path}`",
        "ai-town/plugin-registry",
    )
    return {
        "status": "saved",
        "draft_path": str(draft_path),
        "memory_event": memory,
        "preview": content,
        "plugin_id": plugin_id,
        "category": category,
        "safety": "plugin-proposal-only",
    }


def create_plugin_activation_plan(req: PluginActivationPlanRequest) -> dict:
    manifest_id = slugify_filename(req.manifest_id or "permission-secret-audit")
    title = req.title.strip() or "AI Town plugin activation plan"
    body = req.body.strip() or "Review manifest ownership, permissions, verification gates, and rollback notes."
    source = req.source_building.strip() or "plugin-registry"
    manifest = plugin_manifest_by_id(manifest_id)
    if not manifest:
        return {
            "status": "missing",
            "manifest_id": manifest_id,
            "available_manifest_ids": [item.get("id", "") for item in plugin_manifest_catalog().get("manifests", [])],
            "safe_note": "No activation plan was created and no plugin files changed.",
        }
    if req.confirmation != CONFIRM_PLUGIN_ACTIVATION_PLAN:
        return {
            "status": "confirmation-required",
            "manifest_id": manifest_id,
            "manifest": manifest,
            "confirmation_required": CONFIRM_PLUGIN_ACTIVATION_PLAN,
            "safety": "activation-plan-only",
            "preview": (
                f"Plan activation for `{manifest.get('name', manifest_id)}` owned by `{manifest.get('owner_building', '')}`. "
                f"Permissions: {', '.join(manifest.get('permissions', []))}. "
                "This will create a review plan only; it will not install, execute, edit registries, or invoke agents."
            ),
        }
    PLUGIN_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    plan_path = PLUGIN_DRAFTS_DIR / f"{timestamp}-activation-plan-{manifest_id}-{slugify_filename(title)}.md"
    content = "\n".join([
        "---",
        f"title: {title}",
        f"manifest_id: {manifest_id}",
        f"source: ai-town/{source}",
        "status: activation-plan",
        "safety: activation-plan-only",
        "---",
        "",
        f"# {title}",
        "",
        "## Manifest",
        "",
        f"- Name: {manifest.get('name', manifest_id)}",
        f"- Category: {manifest.get('category', '')}",
        f"- Version: {manifest.get('version', '')}",
        f"- Owner building: {manifest.get('owner_building', '')}",
        f"- Safety: {manifest.get('safety', '')}",
        f"- Activation mode: {manifest.get('activation_mode', '')}",
        "",
        "## Operator Notes",
        "",
        body,
        "",
        "## Permissions",
        "",
    ])
    content += "\n".join([f"- {item}" for item in manifest.get("permissions", [])])
    content += "\n\n## Files\n\n"
    content += "\n".join([f"- {item}" for item in manifest.get("files", [])])
    content += "\n\n## Endpoints\n\n"
    content += "\n".join([f"- {item}" for item in manifest.get("endpoints", [])])
    content += "\n\n## Verification\n\n"
    content += "\n".join([f"- {item}" for item in manifest.get("verification", [])])
    content += "\n\n## Rollback Notes\n\n"
    rollback = manifest.get("rollback", []) or ["Remove only files introduced by the implementation slice after reviewing git diff."]
    content += "\n".join([f"- {item}" for item in rollback])
    content += "\n\n## Safety\n\n- This activation plan did not install plugins, run package managers, execute scripts, edit registries, download assets, change skills, invoke agents, or activate code.\n- Treat implementation as a separate explicit task with smoke, registry health, and visual proof."
    plan_path.write_text(content, encoding="utf-8")
    memory = record_memory_event(
        f"Plugin activation plan created: {title}",
        f"Created project-local activation plan for `{manifest_id}` at `{plan_path}`. No plugin was activated.",
        "ai-town/plugin-registry",
    )
    return {
        "status": "saved",
        "safety": "activation-plan-only",
        "manifest_id": manifest_id,
        "manifest": manifest,
        "plan_path": str(plan_path),
        "memory_event": memory,
        "preview": content,
    }


def room_cards_for(building_id: str, data: dict) -> list[dict]:
    """Convert raw adapter data into game-readable shelf/workbench cards."""
    cards = []
    if building_id == "file-vault":
        index = data.get("index", {})
        cards.append({"title": "File Index", "body": f"{index.get('item_count', 0)} cached items | {index.get('root_count', 0)} roots | {index.get('cache_path', '')}"})
        for root in data.get("roots", [])[:8]:
            item_names = ", ".join(item.get("name", "") for item in root.get("items", [])[:6])
            cards.append({
                "title": root.get("name", "Root"),
                "body": f"{root.get('path', '')} | {root.get('count', 0)} sampled items | {item_names}",
            })
    elif building_id == "memory-library":
        summary = data.get("summary", {})
        service = "online" if data.get("agentmemory_service") else "offline"
        cards.append({"title": "Memory Counts", "body": f"{json.dumps(summary, ensure_ascii=False)} | agentmemory service: {service}"})
        for shelf in data.get("categories", [])[:8]:
            cards.append({
                "title": f"Shelf: {shelf.get('category', 'memory')}",
                "body": f"{shelf.get('count', 0)} notes | {shelf.get('path', '')}",
            })
        for item in data.get("recent", [])[:4]:
            cards.append({"title": item.get("title", item.get("name", "memory")), "body": f"{item.get('category', '')}/{item.get('filename', '')}"})
    elif building_id == "skill-workshop":
        cards.append({"title": "Skill Library", "body": f"{data.get('total_skills', 0)} skills across {data.get('categories', 0)} categories"})
        for item in data.get("skills", [])[:8]:
            cards.append({"title": item.get("name", "skill"), "body": item.get("category", "")})
    elif building_id == "research-hall":
        for item in data.get("projects", data.get("active_projects", []))[:10]:
            if "theme" in item:
                local = next((root.get("path", "") for root in item.get("local_dirs", []) if root.get("exists")), "missing local folder")
                cards.append({
                    "title": f"P{item.get('priority', '?')} {item.get('name', item.get('id', 'project'))}",
                    "body": f"{item.get('theme', '')} | {local} | next: {item.get('next_action', '')}",
                })
            else:
                cards.append({"title": item.get("title", item.get("file", "project")), "body": item.get("path", "")})
    elif building_id == "agent-hub":
        cards.append({"title": "Hub State", "body": f"devtools={data.get('devtools_exists')} hub={data.get('hub_exists')} state={data.get('state_exists')} mailboxes={data.get('mailbox_count', 0)} launchers={data.get('launcher_count', 0)}"})
        task_queue = data.get("task_queue", {})
        tool_queue = data.get("tool_queue", {})
        cards.append({"title": "Agent Task Queue", "body": f"{task_queue.get('count', 0)} tasks | {json.dumps(task_queue.get('counts', {}), ensure_ascii=False)} | logs={data.get('task_log_dir', '')}"})
        cards.append({"title": "Agent Tool Queue", "body": f"{tool_queue.get('count', 0)} invocations | {json.dumps(tool_queue.get('counts', {}), ensure_ascii=False)} | tools={len(tool_queue.get('catalog', []))} | logs={data.get('tool_log_dir', '')}"})
        tool_logs = data.get("tool_logs", [])
        if tool_logs:
            cards.append({"title": "Tool Log Archive", "body": f"{len(tool_logs)} recent durable agent tool log(s) under {data.get('tool_log_dir', '')}"})
        task_logs = data.get("task_logs", [])
        if task_logs:
            cards.append({"title": "Task Log Archive", "body": f"{len(task_logs)} recent durable agent task log(s) under {data.get('task_log_dir', '')}"})
        for item in data.get("roster", [])[:8]:
            cards.append({"title": item.get("name", item.get("id", "agent")), "body": f"{item.get('role', '')} | launcher={item.get('launcher_exists')} | {item.get('launcher', '')}"})
        for item in task_queue.get("tasks", [])[:4]:
            cards.append({"title": f"Task: {item.get('title', item.get('id', 'task'))}", "body": f"{item.get('status', '')} | {item.get('task_type', '')} | {item.get('result_summary', '')}"})
        for item in data.get("mailboxes", [])[:8]:
            cards.append({"title": item.get("agent", "agent"), "body": f"{item.get('bytes', 0)} bytes | {item.get('path', '')}"})
    elif building_id == "devtools-lab":
        for item in data.get("tools", [])[:10]:
            cards.append({"title": item.get("name", "tool"), "body": item.get("path", "")})
    elif building_id == "code-workshop":
        cards.append({"title": "Project Index", "body": f"{data.get('count', 0)} git repositories sampled from D: roots"})
        for item in data.get("projects", [])[:10]:
            cards.append({"title": item.get("name", "repo"), "body": f"{item.get('family', '')} | {item.get('branch', '')} | dirty={item.get('dirty_count', 0)} | {item.get('path', '')}"})
    elif building_id == "github-harbor":
        cards.append({"title": "Harbor Index", "body": f"{data.get('count', 0)} local git docks | mode={data.get('mode', 'read-only')}"})
        for item in data.get("repos", [])[:10]:
            remote_hint = item.get("remotes", ["no remote"])
            if isinstance(remote_hint, list):
                remote_hint = remote_hint[0] if remote_hint else "no remote"
            cards.append({"title": item.get("name", "repo"), "body": f"{item.get('branch', '')} | remote={item.get('has_remote')} | {remote_hint}"})
    elif building_id == "terminal-control":
        cards.append({"title": "Command Allowlist", "body": f"{data.get('count', 0)} commands | mode={data.get('mode', 'confirm-required')}"})
        for item in data.get("commands", [])[:8]:
            cards.append({"title": item.get("label", "command"), "body": f"{item.get('id', '')} | preview={item.get('preview_status', '')} | timeout={item.get('timeout', 0)}s | cwd={item.get('cwd', '')}"})
        cards.append({"title": "Command Preview", "body": "read-only argv/cwd/timeout/safety dry-run before confirmation"})
        for item in data.get("recent_logs", [])[:4]:
            cards.append({"title": f"Log: {item.get('label', item.get('command_id', 'command'))}", "body": f"{item.get('status', '')} rc={item.get('returncode')} | {item.get('log_path', '')}"})
    elif building_id == "system-monitor":
        services = data.get("services", [])
        jobs = data.get("jobs", {})
        cards.append({"title": "Service Lanterns", "body": f"{len(services)} services | warnings={len(data.get('warnings', []))} | mode={data.get('mode', 'read-only')}"})
        cancelable = sum(1 for item in jobs.get("recent", []) if item.get("cancelable"))
        cards.append({"title": "Job Queue", "body": f"{jobs.get('count', 0)} jobs | {json.dumps(jobs.get('counts', {}), ensure_ascii=False)}"})
        cards.append({"title": "Cancel Job", "body": f"{cancelable} currently cancelable | rollback notes shown in System Monitor Job Queue"})
        for item in services[:8]:
            cards.append({"title": item.get("name", item.get("id", "service")), "body": f"{item.get('status', '')} | {item.get('detail', '')}"})
        for item in data.get("workspace", [])[:5]:
            cards.append({"title": f"Workspace: {item.get('name', '')}", "body": f"{item.get('kind', '')} exists={item.get('exists')} sample={item.get('sample_count', 0)} | {item.get('path', '')}"})
    elif building_id == "model-market":
        cards.append({"title": "Gateway Ledger", "body": f"{data.get('configured_count', 0)} / {data.get('count', 0)} profiles configured | mode={data.get('mode', 'read-only')}"})
        for item in data.get("profiles", [])[:10]:
            cards.append({"title": item.get("name", item.get("id", "model")), "body": f"{item.get('status', '')} | env={item.get('key_env', '')} | base={item.get('base_url', '')}"})
    elif building_id == "task-board":
        cards.append({"title": "Local Tasks", "body": f"{data.get('local_task_count', 0)} tasks | {json.dumps(data.get('status_counts', {}), ensure_ascii=False)}"})
        cards.append({"title": "Draft Signals", "body": f"{data.get('dispatch_draft_count', 0)} dispatch drafts | {data.get('memory_event_count', 0)} memory events"})
        for item in data.get("local_tasks", [])[:8]:
            cards.append({"title": item.get("title", "task"), "body": f"{item.get('status', '')} | agent={item.get('target_agent', '')} | {item.get('draft_path', '')}"})
    elif building_id == "writing-studio":
        cards.append({"title": "Project Documents", "body": f"{data.get('document_count', 0)} core docs | drafts={data.get('draft_count', 0)}"})
        for item in data.get("documents", [])[:6]:
            cards.append({"title": item.get("title", item.get("name", "doc")), "body": f"{item.get('relative_path', '')} | {item.get('bytes', 0)} bytes"})
        for item in data.get("drafts", [])[:4]:
            cards.append({"title": f"Draft: {item.get('title', '')}", "body": item.get("path", "")})
    elif building_id == "automation-factory":
        cards.append({"title": "Automation Blueprints", "body": f"{data.get('script_count', 0)} scripts cataloged | drafts={data.get('draft_count', 0)} | mode={data.get('mode', 'draft-only')}"})
        for item in data.get("scripts", [])[:8]:
            cards.append({"title": item.get("name", item.get("id", "script")), "body": f"{item.get('safety', '')} | {item.get('relative_path', '')}"})
        for item in data.get("drafts", [])[:4]:
            cards.append({"title": f"Draft: {item.get('title', '')}", "body": item.get("path", "")})
    elif building_id == "permission-hall":
        cards.append({"title": "Safety Ledger", "body": f"{len(data.get('safety_classes', []))} safety classes | mode={data.get('mode', 'read-only')}"})
        cards.append({"title": "Building Policies", "body": json.dumps(data.get("safety_counts", {}), ensure_ascii=False)})
        for item in data.get("confirmation_gates", [])[:4]:
            cards.append({"title": item.get("scope", "confirmation"), "body": f"{item.get('phrase', '')} | {item.get('endpoint', '')}"})
        for item in data.get("blocked_actions", [])[:4]:
            cards.append({"title": item.get("label", "blocked"), "body": f"{item.get('status', '')} | {item.get('reason', '')}"})
    elif building_id == "settings-center":
        cards.append({"title": "Config Registries", "body": f"{data.get('registry_count', 0)} registries | env requirements={data.get('env_count', 0)}"})
        for item in data.get("registries", [])[:5]:
            cards.append({"title": item.get("name", item.get("id", "registry")), "body": f"exists={item.get('exists')} count={item.get('count', 0)} | {item.get('path', '')}"})
        for item in data.get("env_requirements", [])[:5]:
            cards.append({"title": item.get("name", "env"), "body": f"{item.get('kind', '')} | configured={item.get('configured')} | {item.get('provider', '')}"})
    elif building_id == "testing-arena":
        artifact = data.get("visual_artifact", {})
        manifest = data.get("visual_manifest", {})
        cards.append({"title": "Verification Scripts", "body": f"{data.get('script_count', 0)} scripts | drafts={data.get('draft_count', 0)} | visual={artifact.get('status', 'unknown')}"})
        cards.append({"title": "Room Visual Manifest", "body": f"{manifest.get('valid_screenshot_count', 0)}/{manifest.get('registry_room_count', 0)} rooms verified | status={manifest.get('status', 'unknown')} | hashes={manifest.get('hash_mismatch_count', 0)} mismatches"})
        for item in data.get("scripts", [])[:4]:
            cards.append({"title": item.get("name", item.get("id", "script")), "body": f"exists={item.get('exists')} | {item.get('description', '')}"})
        for item in data.get("verification_log", [])[:5]:
            cards.append({"title": "Verification Log", "body": item.get("title", "")})
    elif building_id == "bug-clinic":
        cards.append({"title": "Diagnostic Snapshot", "body": f"failed jobs={data.get('failed_job_count', 0)} | failed terminal logs={data.get('failed_terminal_log_count', 0)} | reports={data.get('bug_report_count', 0)}"})
        for item in data.get("diagnostics", [])[:5]:
            cards.append({"title": item.get("title", item.get("id", "diagnostic")), "body": f"{item.get('status', '')} | {item.get('detail', '')}"})
        for item in data.get("diagnostic_events", [])[:4]:
            cards.append({"title": f"Signal: {item.get('title', '')}", "body": item.get("path", "")})
    elif building_id == "project-management-hall":
        cards.append({"title": "Portfolio Snapshot", "body": f"{data.get('project_count', 0)} repos | {data.get('research_project_count', 0)} research boards | {data.get('local_task_count', 0)} local tasks"})
        cards.append({"title": "Task Status", "body": json.dumps(data.get("task_status_counts", {}), ensure_ascii=False)})
        for item in data.get("projects", [])[:5]:
            cards.append({"title": item.get("name", item.get("id", "project")), "body": f"{item.get('family', '')} | branch={item.get('branch', '')} | {item.get('path', '')}"})
        for item in data.get("research_projects", [])[:4]:
            cards.append({"title": f"Research: {item.get('name', item.get('id', 'project'))}", "body": item.get("theme", item.get("next_action", ""))})
    elif building_id == "download-station":
        cards.append({"title": "Intake Roots", "body": f"{data.get('root_count', 0)} allowlisted roots | drafts={data.get('draft_count', 0)} | mode={data.get('mode', 'read-only')}"})
        cards.append({"title": "File Types", "body": json.dumps(data.get("type_counts", {}), ensure_ascii=False)})
        for item in data.get("roots", [])[:5]:
            cards.append({"title": item.get("name", item.get("id", "root")), "body": f"exists={item.get('exists')} | files={item.get('sample_count', 0)} | {item.get('path', '')}"})
        for item in data.get("latest_files", [])[:5]:
            cards.append({"title": item.get("name", "download"), "body": f"{item.get('kind', 'other')} | {item.get('root_name', '')} | {item.get('bytes', 0)} bytes"})
    elif building_id == "asset-gallery":
        cards.append({"title": "Asset Shelves", "body": f"{data.get('root_count', 0)} roots | assets={data.get('asset_count', 0)} | notes={data.get('note_count', 0)} | mode={data.get('mode', 'read-only')}"})
        cards.append({"title": "Asset Types", "body": json.dumps(data.get("kind_counts", {}), ensure_ascii=False)})
        for item in data.get("roots", [])[:5]:
            cards.append({"title": item.get("name", item.get("id", "root")), "body": f"exists={item.get('exists')} | sample={item.get('sample_count', 0)} | {item.get('role', '')}"})
        for item in data.get("assets", [])[:5]:
            cards.append({"title": item.get("relative_path", item.get("name", "asset")), "body": f"{item.get('kind', 'other')} | {item.get('root_name', '')} | {item.get('bytes', 0)} bytes"})
    elif building_id == "local-office-center":
        cards.append({"title": "Office Map", "body": f"{data.get('root_count', 0)} roots | recent={data.get('recent_item_count', 0)} | notes={data.get('note_count', 0)} | mode={data.get('mode', 'read-only')}"})
        cards.append({"title": "Office Types", "body": json.dumps(data.get("type_counts", {}), ensure_ascii=False)})
        for item in data.get("roots", [])[:5]:
            cards.append({"title": item.get("name", item.get("id", "root")), "body": f"exists={item.get('exists')} | sample={item.get('sample_count', 0)} | {item.get('role', '')}"})
        for item in data.get("recent_items", [])[:5]:
            cards.append({"title": item.get("relative_path", item.get("name", "office item")), "body": f"{item.get('kind', 'other')} | {item.get('root_name', '')} | {item.get('bytes', 0)} bytes"})
    elif building_id == "schedule-plan-center":
        cards.append({"title": "Planning Signals", "body": f"{data.get('signal_count', 0)} signals | open PLAN={data.get('open_plan_task_count', 0)} | tasks={data.get('local_task_count', 0)} | drafts={data.get('schedule_draft_count', 0)}"})
        cards.append({"title": "Task Status", "body": json.dumps(data.get("task_status_counts", {}), ensure_ascii=False)})
        for item in data.get("open_plan_tasks", [])[:5]:
            cards.append({"title": "Open PLAN", "body": item.get("title", "")})
        for item in data.get("signals", [])[:4]:
            cards.append({"title": item.get("title", "signal"), "body": item.get("preview", item.get("path", ""))[:220]})
    elif building_id == "learning-training-grounds":
        cards.append({"title": "Training Map", "body": f"{data.get('skill_count', 0)} skills | {data.get('category_count', 0)} categories | plans={data.get('learning_plan_count', 0)} | mode={data.get('mode', 'read-only')}"})
        for item in data.get("tracks", [])[:4]:
            cards.append({"title": item.get("name", item.get("id", "track")), "body": item.get("focus", "")})
        for item in data.get("skills", [])[:5]:
            cards.append({"title": item.get("name", "skill"), "body": item.get("category", "")})
        for item in data.get("signals", [])[:3]:
            cards.append({"title": item.get("title", "signal"), "body": item.get("preview", item.get("path", ""))[:180]})
    elif building_id == "language-learning-area":
        cards.append({"title": "Language Practice", "body": f"{data.get('supported_count', 0)} tracks | signals={data.get('signal_count', 0)} | notes={data.get('practice_note_count', 0)} | mode={data.get('mode', 'read-only')}"})
        for item in data.get("supported_languages", [])[:4]:
            cards.append({"title": item.get("name", item.get("id", "language")), "body": item.get("focus", "")})
        for item in data.get("signals", [])[:4]:
            cards.append({"title": item.get("title", "signal"), "body": item.get("preview", item.get("path", ""))[:180]})
        for item in data.get("practice_notes", [])[:3]:
            cards.append({"title": f"Practice: {item.get('title', '')}", "body": item.get("path", "")})
    elif building_id == "research-data-center":
        cards.append({"title": "Research Data Map", "body": f"{data.get('root_count', 0)} roots | candidates={data.get('candidate_count', 0)} | notes={data.get('note_count', 0)} | mode={data.get('mode', 'read-only')}"})
        cards.append({"title": "Candidate Types", "body": json.dumps(data.get("kind_counts", {}), ensure_ascii=False)})
        for item in data.get("roots", [])[:4]:
            cards.append({"title": item.get("project_name", item.get("project_id", "research")), "body": f"exists={item.get('exists')} | candidates={item.get('candidate_count', 0)} | {item.get('path', '')}"})
        for item in data.get("candidates", [])[:5]:
            cards.append({"title": item.get("relative_path", item.get("name", "candidate")), "body": f"{item.get('kind', 'other')} | {item.get('project_name', '')} | {item.get('path', '')}"})
        for item in data.get("notes", [])[:2]:
            cards.append({"title": f"Data note: {item.get('title', '')}", "body": item.get("path", "")})
    elif building_id == "paper-reading-room":
        cards.append({"title": "Paper Map", "body": f"{data.get('root_count', 0)} roots | candidates={data.get('paper_count', 0)} | notes={data.get('reading_note_count', 0)} | mode={data.get('mode', 'read-only')}"})
        cards.append({"title": "Reference Types", "body": json.dumps(data.get("kind_counts", {}), ensure_ascii=False)})
        for item in data.get("roots", [])[:4]:
            cards.append({"title": item.get("name", item.get("id", "root")), "body": f"exists={item.get('exists')} | candidates={item.get('candidate_count', 0)} | {item.get('role', '')}"})
        for item in data.get("papers", [])[:5]:
            cards.append({"title": item.get("relative_path", item.get("name", "paper")), "body": f"{item.get('kind', 'other')} | {item.get('root_name', '')} | {item.get('path', '')}"})
        for item in data.get("reading_notes", [])[:2]:
            cards.append({"title": f"Reading note: {item.get('title', '')}", "body": item.get("path", "")})
    elif building_id == "version-release-plaza":
        git = data.get("git", {})
        manifest = data.get("visual_manifest", {})
        build = data.get("build_readiness", {})
        cards.append({"title": "Release Readiness", "body": f"required={data.get('ready_required_count', 0)}/{data.get('required_count', 0)} | missing={data.get('missing_required_count', 0)} | drafts={data.get('draft_count', 0)}"})
        cards.append({"title": "Visual Evidence", "body": f"visual={data.get('visual_artifact', {}).get('status', 'unknown')} | all-room={manifest.get('valid_screenshot_count', 0)}/{manifest.get('registry_room_count', 0)} | status={manifest.get('status', 'unknown')}"})
        cards.append({"title": "Godot Build Readiness", "body": f"{build.get('status', 'unknown')} | checks={build.get('checks_passed', 0)}/{build.get('checks_total', 0)} | export={build.get('export', {}).get('export_path', '')}"})
        export_tool = data.get("export_tool", {})
        cards.append({"title": "Godot Export Tool", "body": f"{export_tool.get('status', 'missing')} | blockers={export_tool.get('blocker_count', 0)} | output={export_tool.get('output_exists', False)}"})
        packaged = data.get("packaged_launch", {})
        cards.append({"title": "Packaged Launcher", "body": f"{packaged.get('status', 'unknown')} | checks={packaged.get('checks_passed', 0)}/{packaged.get('checks_total', 0)} | game={packaged.get('game_exists', False)}"})
        manifest = data.get("release_manifest", {})
        cards.append({"title": "Release Manifest", "body": f"{manifest.get('status', 'unknown')} | files={manifest.get('file_count', 0)} | exe={manifest.get('exe_bytes', 0)} bytes"})
        cards.append({"title": "Git Snapshot", "body": f"branch={git.get('branch', '')} | status entries={git.get('status_count', 0)} | remotes={git.get('remote_count', 0)} | tags={git.get('tag_count_sampled', 0)}"})
        for item in data.get("files", [])[:6]:
            cards.append({"title": item.get("name", item.get("id", "artifact")), "body": f"{item.get('status', '')} | required={item.get('required')} | {item.get('path', '')}"})
        for item in data.get("drafts", [])[:3]:
            cards.append({"title": f"Release draft: {item.get('title', '')}", "body": item.get("path", "")})
    elif building_id == "plugin-registry":
        cards.append({"title": "Extension Map", "body": f"roots={data.get('root_count', 0)} | registries={data.get('registry_count', 0)} | candidates={data.get('candidate_count', 0)} | drafts={data.get('draft_count', 0)}"})
        cards.append({"title": "Candidate Types", "body": json.dumps(data.get("kind_counts", {}), ensure_ascii=False)})
        for item in data.get("registries", [])[:3]:
            cards.append({"title": item.get("name", item.get("id", "registry")), "body": f"{item.get('status', '')} | count={item.get('count', 0)} | {item.get('path', '')}"})
        for item in data.get("roots", [])[:4]:
            cards.append({"title": item.get("name", item.get("id", "root")), "body": f"exists={item.get('exists')} | candidates={item.get('candidate_count', 0)} | {item.get('role', '')}"})
        for item in data.get("drafts", [])[:2]:
            cards.append({"title": f"Plugin draft: {item.get('title', '')}", "body": item.get("path", "")})
    elif building_id == "backup-station":
        cards.append({"title": "Backup Map", "body": f"{data.get('source_count', 0)} sources | {data.get('target_count', 0)} targets | plans={data.get('plan_count', 0)}"})
        for item in data.get("sources", [])[:5]:
            cards.append({"title": item.get("name", item.get("id", "source")), "body": f"{item.get('priority', '')} | exists={item.get('exists')} | sample={item.get('sample_count', 0)} | {item.get('path', '')}"})
        for item in data.get("targets", [])[:4]:
            cards.append({"title": f"Target: {item.get('name', item.get('id', 'target'))}", "body": f"exists={item.get('exists')} | sample={item.get('sample_count', 0)} | {item.get('path', '')}"})
    elif building_id == "goal-tower":
        cards.append({"title": "Goal Map", "body": f"{data.get('open_plan_task_count', 0)} open PLAN tasks | {data.get('done_plan_task_count', 0)} done | drafts={data.get('draft_count', 0)}"})
        cards.append({"title": "Portfolio Signals", "body": f"{data.get('portfolio_project_count', 0)} projects | {data.get('research_project_count', 0)} research boards | local tasks={data.get('local_task_count', 0)}"})
        for item in data.get("open_plan_tasks", [])[:6]:
            cards.append({"title": "Open PLAN Task", "body": item.get("title", "")})
        for item in data.get("signals", [])[:4]:
            cards.append({"title": item.get("title", "signal"), "body": item.get("path", "")})
    elif building_id == "inspiration-station":
        cards.append({"title": "Idea Inbox", "body": f"{data.get('signal_count', 0)} source signals | {data.get('nearby_draft_count', 0)} nearby drafts | notes={data.get('note_count', 0)}"})
        for item in data.get("signals", [])[:5]:
            cards.append({"title": item.get("title", "signal"), "body": item.get("preview", item.get("path", ""))[:220]})
        for item in data.get("notes", [])[:4]:
            cards.append({"title": f"Note: {item.get('title', '')}", "body": item.get("path", "")})
    elif building_id == "temporary-draft-box":
        cards.append({"title": "Draft Inbox", "body": f"{data.get('shelf_count', 0)} shelves | {data.get('total_known_drafts', 0)} known drafts | temp={data.get('temp_draft_count', 0)}"})
        for item in data.get("shelves", [])[:8]:
            cards.append({"title": item.get("id", "shelf"), "body": f"{item.get('count', 0)} {item.get('kind', 'drafts')} | exists={item.get('exists')} | {item.get('path', '')}"})
        for item in data.get("temp_drafts", [])[:4]:
            cards.append({"title": f"Temp: {item.get('title', '')}", "body": item.get("path", "")})
    elif building_id == "knowledge-tower":
        index = data.get("index", {})
        cards.append({"title": "Knowledge Index", "body": f"{index.get('document_count', data.get('sampled_pages', 0))} cached docs | {index.get('root_count', 0)} allowlisted roots | {index.get('cache_path', '')}"})
        for topic in data.get("topics", [])[:12]:
            cards.append({"title": "Knowledge Root", "body": topic})
    elif building_id == "town-hall":
        atlas = data.get("capability_atlas", {})
        if atlas:
            cards.append({
                "title": "Capability Atlas",
                "body": f"{atlas.get('connected_count', 0)}/{atlas.get('building_count', 0)} buildings mapped to real paths, endpoints, tools, agents, or APIs",
            })
            for item in atlas.get("entries", [])[:7]:
                if not item.get("has_real_connection"):
                    continue
                capabilities = ", ".join(item.get("capabilities", [])[:3])
                endpoints = ", ".join(item.get("endpoints", [])[:2])
                cards.append({
                    "title": item.get("name", item.get("id", "building")),
                    "body": f"{capabilities} | {endpoints}".strip(" |"),
                })
        workflow_routes = data.get("workflow_routes", {})
        if workflow_routes:
            cards.append({
                "title": "Workflow Routes",
                "body": f"{workflow_routes.get('route_count', 0)} reusable multi-building work routes | {workflow_routes.get('connected_building_count', 0)} buildings",
            })
            for route in workflow_routes.get("routes", [])[:4]:
                cards.append({
                    "title": route.get("title", route.get("id", "workflow")),
                    "body": f"{route.get('purpose', '')} | {', '.join(route.get('building_ids', [])[:4])}",
                })
        for item in data.get("recent_decisions", [])[:8]:
            cards.append({"title": item.get("title", "decision"), "body": item.get("name", "")})
    else:
        for key, value in data.items():
            if key != "name":
                cards.append({"title": key, "body": json.dumps(value, ensure_ascii=False)})
    return cards[:12]


def slugify_filename(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return slug or "work-note"


def draft_note_for(building_id: str, data: dict) -> tuple[str, str]:
    title = f"{data.get('name', building_id)} Work Note"
    cards = room_cards_for(building_id, data)
    lines = [
        "---",
        f"title: {title}",
        f"source: ai-town/{building_id}",
        "status: draft",
        "---",
        "",
        f"# {title}",
        "",
        "## Summary",
        "",
        f"This draft was prepared from the Agent Town {data.get('name', building_id)} room.",
        "",
        "## Room Cards",
        "",
    ]
    for card in cards[:8]:
        lines.append(f"- **{card.get('title', 'Item')}**: {card.get('body', '')}")
    lines.extend([
        "",
        "## Next Action",
        "",
        "- Review this note and decide whether it should become a task, wiki page, or research log.",
    ])
    return title, "\n".join(lines)


async def building_data_for(building_id: str) -> Optional[dict]:
    building_map = {
        "memory-library": building_memory_library,
        "skill-workshop": building_skill_workshop,
        "knowledge-tower": building_knowledge_tower,
        "devtools-lab": building_devtools_lab,
        "code-workshop": building_code_workshop,
        "github-harbor": building_github_harbor,
        "terminal-control": building_terminal_control,
        "system-monitor": building_system_monitor,
        "model-market": building_model_market,
        "task-board": building_task_board,
        "writing-studio": building_writing_studio,
        "automation-factory": building_automation_factory,
        "permission-hall": building_permission_hall,
        "settings-center": building_settings_center,
        "testing-arena": building_testing_arena,
        "bug-clinic": building_bug_clinic,
        "project-management-hall": building_project_management_hall,
        "download-station": building_download_station,
        "asset-gallery": building_asset_gallery,
        "local-office-center": building_local_office_center,
        "schedule-plan-center": building_schedule_plan_center,
        "learning-training-grounds": building_learning_training_grounds,
        "language-learning-area": building_language_learning_area,
        "research-data-center": building_research_data_center,
        "paper-reading-room": building_paper_reading_room,
        "version-release-plaza": building_version_release_plaza,
        "plugin-registry": building_plugin_registry,
        "backup-station": building_backup_station,
        "goal-tower": building_goal_tower,
        "inspiration-station": building_inspiration_station,
        "temporary-draft-box": building_temporary_draft_box,
        "town-hall": building_town_hall,
        "file-vault": building_file_vault,
        "research-hall": building_research_hall,
        "agent-hub": building_agent_hub,
        "resource-market": building_resource_market,
    }
    handler = building_map.get(building_id)
    if not handler:
        return None
    return await handler()


@app.get("/api/agents")
async def get_agents():
    return [
        {"id": k, "name": v["name"], "role": v["role"], "zone": v["zone"]}
        for k, v in AGENT_PERSONALITIES.items()
    ]


@app.get("/api/config/buildings")
async def get_building_registry():
    """Return the active building registry used by the Godot client."""
    buildings = load_json_registry(BUILDING_REGISTRY_PATH)
    return {
        "status": "ok" if buildings else "missing",
        "path": str(BUILDING_REGISTRY_PATH),
        "count": len(buildings),
        "buildings": buildings,
    }


@app.get("/api/config/agents")
async def get_agent_registry():
    """Return the active agent registry used by the Godot client."""
    agents = load_json_registry(AGENT_REGISTRY_PATH)
    return {
        "status": "ok" if agents else "missing",
        "path": str(AGENT_REGISTRY_PATH),
        "count": len(agents),
        "agents": agents,
    }


@app.get("/api/config/workspaces")
async def get_workspace_registry():
    """Return the active allowlisted workspace registry used by File Vault and project discovery."""
    return workspace_registry_overview()


@app.get("/api/config/quests")
async def get_quest_registry():
    """Return the active quest registry with resolved local status templates."""
    return quest_registry_overview()


@app.get("/api/config/npc-quests")
async def get_npc_quest_registry():
    """Return read-only NPC quest-chain registry data for room progression."""
    return npc_quest_registry_overview()


@app.get("/api/config/room-scenes")
async def get_room_scene_registry():
    """Return read-only room-scene interior layout and station metadata."""
    return room_scene_registry_overview()


@app.get("/api/config/map-decor")
async def get_map_decor_registry():
    """Return read-only clickable map landmark metadata for the Godot plaza."""
    return map_decor_registry_overview()


@app.get("/api/config/plugin-manifests")
async def get_plugin_manifest_registry():
    """Return read-only typed plugin manifest metadata."""
    return plugin_manifest_catalog()


@app.get("/api/config/registry-health")
async def get_registry_health():
    """Return read-only schema validation for all Godot data registries."""
    return registry_health_overview()


@app.get("/api/town/capability-atlas")
async def get_town_capability_atlas():
    """Return the read-only map from buildings to their real local capabilities."""
    return town_capability_atlas()


@app.get("/api/town/capability-atlas/{building_id}")
async def get_town_capability_detail(building_id: str):
    """Return one building's read-only real capability connections."""
    return town_capability_detail(building_id)


@app.get("/api/town/workflow-routes")
async def get_town_workflow_routes():
    """Return reusable read-only multi-building work route guidance."""
    return town_workflow_routes()


@app.get("/api/town/workflow-routes/{route_id}")
async def get_town_workflow_route_detail(route_id: str):
    """Return one read-only multi-building work route."""
    return town_workflow_route_detail(route_id)


@app.get("/api/player/collection-codex")
async def get_collection_codex():
    """Return possible collectible rewards. Ownership is merged from Godot local save data."""
    return collection_codex_overview()


@app.get("/api/config/districts")
async def get_district_registry():
    """Return the active district/teleport registry used by the Godot map."""
    districts = load_json_registry(DISTRICT_REGISTRY_PATH)
    return {
        "status": "ok" if districts else "missing",
        "path": str(DISTRICT_REGISTRY_PATH),
        "count": len(districts),
        "districts": districts,
        "safe_note": "District registry is read-only map routing data. It moves the in-game player/camera only and does not touch files, agents, services, or external tools.",
    }


@app.get("/api/buildings/memory-library")
async def building_memory_library():
    """Real data from shared memory system."""
    index = memory_index()
    index["agentmemory_service"] = await check_agentmemory()
    return index


@app.get("/api/memory/index")
async def get_memory_index():
    """Read-only index of shared memory shelves used by the Memory Library."""
    index = memory_index()
    index["agentmemory_service"] = await check_agentmemory()
    return index


@app.get("/api/memory/items/{category}")
async def get_memory_items(category: str):
    """List recent memory notes in one category."""
    if category not in MEMORY_CATEGORIES:
        return {"status": "missing", "category": category, "items": [], "count": 0}
    result = memory_category_index(category, 40)
    result["status"] = "ok"
    return result


@app.get("/api/memory/items/{category}/{filename}")
async def get_memory_item(category: str, filename: str):
    """Return a bounded preview for one shared memory note."""
    detail = memory_item_detail(category, filename)
    if not detail:
        return {"status": "missing", "category": category, "filename": filename}
    detail["status"] = "ok"
    return detail


@app.post("/api/memory/proposals")
async def post_memory_proposal(req: MemoryProposalRequest):
    """Create a project-local memory proposal without writing shared memory directly."""
    return create_memory_proposal(req)


@app.post("/api/memory/promotions")
async def post_memory_promotion(req: MemoryPromotionRequest):
    """Promote a reviewed memory proposal into shared memory after explicit confirmation."""
    return promote_memory_proposal(req)


@app.get("/api/buildings/skill-workshop")
async def building_skill_workshop():
    """Real data from skill index."""
    skills_data = []
    try:
        content = SKILL_INDEX_PATH.read_text(encoding="utf-8")
        current_category = ""
        for line in content.split("\n"):
            if line.startswith("## "):
                current_category = line[3:].strip()
            elif line.startswith("### "):
                skill_name = line[4:].strip()
                skills_data.append({"name": skill_name, "category": current_category})
    except:
        pass
    summary = read_skills_summary()
    return {"name": "Skill Workshop", "total_skills": summary["count"], "categories": summary["categories"], "skills": skills_data[:30]}


@app.get("/api/buildings/knowledge-tower")
async def building_knowledge_tower():
    """Real data from knowledge base."""
    overview = knowledge_index_overview()
    topics = [root.get("name", root.get("id", "root")) for root in overview.get("roots", [])]
    return {
        "name": "Knowledge Tower",
        "sampled_pages": overview.get("document_count", 0),
        "sample_limit": 320,
        "topics": topics,
        "index": overview,
        "mode": "cached-allowlisted-search",
    }


@app.get("/api/knowledge/index")
async def get_knowledge_index():
    """Return cached allowlisted knowledge index status for Knowledge Tower."""
    return knowledge_index_overview()


@app.post("/api/knowledge/index-job")
async def post_knowledge_index_job():
    """Queue a bounded allowlisted knowledge index refresh."""
    job = start_job("knowledge-index", "Refresh Knowledge Tower cache", build_knowledge_index)
    return {
        "status": "queued",
        "job_id": job["id"],
        "kind": job["kind"],
        "safety": "allowlisted-read-cache-write",
    }


@app.get("/api/knowledge/search")
async def get_knowledge_search(q: str = "", root_id: str = "all", page: int = 1, page_size: int = 10):
    """Search the cached allowlisted knowledge index with pagination."""
    return knowledge_search(q, root_id, page, page_size)


@app.get("/api/knowledge/items/{doc_id}")
async def get_knowledge_item(doc_id: str):
    """Return a bounded preview for one indexed knowledge document."""
    return knowledge_item(doc_id)


@app.get("/api/buildings/devtools-lab")
async def building_devtools_lab():
    """Real data from devtools directory."""
    tools = []
    try:
        cmd_files = list(DEVTOOLS_DIR.glob("*.cmd"))
        for f in cmd_files:
            tools.append({"name": f.stem, "path": str(f)})
    except:
        pass
    return {"name": "Devtools Lab", "tools": tools, "count": len(tools)}


@app.get("/api/buildings/code-workshop")
async def building_code_workshop():
    """Read-only local software project and Git status index."""
    projects = discover_git_repos()
    return {
        "name": "Code Workshop",
        "roots": [{"name": label, "path": str(root), "exists": root.exists()} for label, root in project_scan_roots()],
        "projects": projects,
        "count": len(projects),
        "context_pack_dir": str(CODE_CONTEXT_DIR),
        "context_packs": markdown_draft_entries(CODE_CONTEXT_DIR, "code-context-pack", 10),
        "patch_plan_dir": str(CODE_PATCH_PLANS_DIR),
        "patch_plans": markdown_draft_entries(CODE_PATCH_PLANS_DIR, "code-patch-plan", 10),
        "verification_log_dir": str(PROJECT_VERIFICATION_LOG_DIR),
        "verification_logs": markdown_draft_entries(PROJECT_VERIFICATION_LOG_DIR, "project-verification-log", 10),
        "confirmation_required": CONFIRM_RUN_PROJECT_CHECK,
        "mode": "read-only",
        "safe_note": "Code Workshop reads local Git metadata, creates local planning artifacts, and can run detected verification commands only after explicit confirmation.",
    }


@app.get("/api/projects")
async def get_projects():
    """Return bounded local Git project index for the Code Workshop."""
    projects = discover_git_repos()
    return {
        "name": "Project Index",
        "projects": projects,
        "count": len(projects),
        "mode": "read-only",
    }


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Return bounded detail for one local Git project."""
    detail = project_detail(project_id)
    if not detail:
        return {"status": "missing", "project_id": project_id}
    return detail


@app.get("/api/buildings/github-harbor")
async def building_github_harbor():
    """Read-only local GitHub/Git harbor view based on local .git metadata."""
    return github_harbor_index()


@app.get("/api/github-harbor/repos")
async def get_github_harbor_repos():
    """Return local Git repositories with remote/tag metadata for GitHub Harbor."""
    return github_harbor_index()


@app.get("/api/github-harbor/repos/{project_id}")
async def get_github_harbor_repo(project_id: str):
    """Return detailed local Git remote/branch/tag/release-note draft metadata."""
    detail = github_repo_detail(project_id)
    if not detail:
        return {"status": "missing", "project_id": project_id}
    detail["status"] = "ok"
    return detail


@app.get("/api/github-harbor/repos/{project_id}/github")
async def get_github_harbor_github_snapshot(project_id: str):
    """Return a read-only GitHub CLI snapshot for one local repository."""
    snapshot = github_cli_snapshot(project_id)
    if not snapshot:
        return {"status": "missing", "project_id": project_id}
    return snapshot


@app.get("/api/github-harbor/repos/{project_id}/publish-readiness")
async def get_github_harbor_publish_readiness(project_id: str):
    """Return read-only local publish readiness for a repository."""
    readiness = github_publish_readiness(project_id)
    if not readiness:
        return {"status": "missing", "project_id": project_id}
    return readiness


@app.post("/api/github-harbor/repos/{project_id}/drafts")
async def post_github_harbor_draft(project_id: str, req: GitHubHarborDraftRequest):
    """Create a project-local GitHub handoff draft without writing to Git or GitHub."""
    result = create_github_harbor_draft(project_id, req)
    if not result:
        return {"status": "missing", "project_id": project_id}
    return result


@app.post("/api/github-harbor/repos/{project_id}/publish-plans")
async def post_github_harbor_publish_plan(project_id: str, req: GitHubPublishPlanRequest):
    """Create a confirm-gated local GitHub publish plan. No Git or GitHub write action is performed."""
    result = create_github_publish_plan(project_id, req)
    if not result:
        return {"status": "missing", "project_id": project_id}
    return result


@app.get("/api/buildings/terminal-control")
async def building_terminal_control():
    """Allowlisted command catalog and recent command logs for Terminal Control."""
    catalog = terminal_command_catalog()
    catalog["recent_logs"] = latest_terminal_logs()
    return catalog


@app.get("/api/terminal/commands")
async def get_terminal_commands():
    """Return safe allowlisted terminal commands. No command is run here."""
    catalog = terminal_command_catalog()
    catalog["recent_logs"] = latest_terminal_logs()
    return catalog


@app.get("/api/terminal/commands/{command_id}/preview")
async def get_terminal_command_preview(command_id: str):
    """Return a read-only dry-run preview for one allowlisted command."""
    return terminal_command_preview(command_id)


@app.get("/api/permissions/receipts")
async def get_permission_receipts(limit: int = 20):
    """Return read-only local safety receipts for confirmed writes, commands, and tool/model activity."""
    return permission_receipts(limit)


@app.get("/api/permissions/secret-audit")
async def get_permission_secret_audit(limit: int = 50):
    """Return a bounded read-only audit for secret-shaped strings in project-local caches and logs."""
    return secret_exposure_audit(limit)


@app.post("/api/terminal/run")
async def post_terminal_run(req: TerminalCommandRequest):
    """Queue a confirm-required allowlisted command job."""
    spec = TERMINAL_COMMANDS.get(req.command_id)
    if not spec:
        return {"status": "missing", "command_id": req.command_id}
    if req.confirmation != CONFIRM_RUN_COMMAND:
        return {
            "status": "confirmation-required",
            "command_id": req.command_id,
            "label": spec["label"],
            "args": spec["args"],
            "cwd": str(spec["cwd"]),
            "timeout": spec["timeout"],
            "safety": "confirm-required-allowlisted",
            "confirmation_required": CONFIRM_RUN_COMMAND,
            "preview": f"{spec['label']} -> {' '.join(spec['args'])}",
        }
    job = start_job("terminal-command", spec["label"], execute_terminal_command, req.command_id)
    job["safety"] = "confirm-required-allowlisted"
    return {
        "status": "queued",
        "job_id": job["id"],
        "kind": job["kind"],
        "label": job["label"],
        "safety": job["safety"],
    }


@app.get("/api/buildings/system-monitor")
async def building_system_monitor():
    """Read-only local service, queue, registry, and workspace status."""
    return await system_monitor_overview()


@app.get("/api/system/overview")
async def get_system_overview():
    """Read-only status view for the System Monitor building."""
    return await system_monitor_overview()


@app.get("/api/system/jobs")
async def get_system_jobs():
    """Read-only backend job queue snapshot."""
    return job_queue_snapshot()


@app.get("/api/system/job-logs")
async def get_system_job_logs(limit: int = 20):
    """Return project-local backend job lifecycle log summaries."""
    bounded_limit = max(1, min(limit, 50))
    logs = latest_backend_job_logs(bounded_limit)
    return {
        "mode": "read-only-backend-job-log-index",
        "log_dir": str(BACKEND_JOB_LOG_DIR),
        "count": len(logs),
        "logs": logs,
        "safe_note": "Backend job logs are read-only project-local lifecycle evidence. This endpoint does not replay jobs, kill processes, run commands, or perform rollback.",
    }


@app.get("/api/system/job-logs/{log_id}")
async def get_system_job_log_detail(log_id: str):
    """Return one project-local backend job lifecycle log detail."""
    return read_backend_job_log(log_id)


@app.get("/api/system/events")
async def get_system_events(limit: int = 40):
    """Return a unified read-only timeline of local events, logs, tasks, and tool invocations."""
    return system_event_timeline(limit=limit)


@app.get("/api/buildings/model-market")
async def building_model_market():
    """Read-only model/API gateway status without exposing secrets."""
    return model_gateway_status()


@app.get("/api/model-gateway/status")
async def get_model_gateway_status():
    """Return provider/profile configuration status. Raw API keys are never returned."""
    return model_gateway_status()


@app.get("/api/model-gateway/profiles")
async def get_model_gateway_profiles():
    """Return configured model profiles and safety metadata without secrets."""
    status = model_gateway_status()
    return {
        "name": "Model Profiles",
        "mode": status["mode"],
        "profile_path": status["profile_path"],
        "profiles": status["profiles"],
        "count": status["count"],
        "secret_policy": status["secret_policy"],
    }


@app.post("/api/model-gateway/chat")
async def post_model_gateway_chat(req: ModelChatRequest):
    """Call the configured model gateway or dry-run the route. Raw API keys are never returned."""
    return await call_model_gateway_chat(req)


@app.post("/api/model-gateway/profile-tests")
async def post_model_gateway_profile_test(req: ModelProfileTestRequest):
    """Record a bounded model profile test report. Raw API keys are never returned or written."""
    return await create_model_profile_test(req)


@app.post("/api/model-gateway/config-drafts")
async def post_model_gateway_config_draft(req: ModelConfigDraftRequest):
    """Create a no-secret model/API gateway setup draft."""
    return create_model_config_draft(req)


@app.get("/api/model-gateway/key-vault")
async def get_model_gateway_key_vault():
    """Return encrypted local API key vault metadata without raw secrets."""
    return model_key_vault_status()


@app.post("/api/model-gateway/key-vault")
async def post_model_gateway_key_vault(req: ModelKeyVaultSaveRequest):
    """Save a local model API key with explicit confirmation and DPAPI encryption."""
    return save_model_key_to_vault(req)


@app.get("/api/buildings/task-board")
async def building_task_board():
    """Read project-local task ledger, dispatch drafts, and recent memory events."""
    return task_board_overview()


@app.get("/api/task-board/overview")
async def get_task_board_overview():
    """Return a unified read-only board for local tasks and draft signals."""
    return task_board_overview()


@app.post("/api/task-board/tasks")
async def post_task_board_task(req: LocalTaskRequest):
    """Create a project-local task draft and memory event. No external runner is invoked."""
    return create_local_task(req)


@app.get("/api/task-board/tasks/{task_id}")
async def get_task_board_task(task_id: str):
    """Return one project-local task with a bounded Markdown draft preview."""
    detail = get_local_task_detail(task_id)
    if not detail:
        return {"status": "not-found", "task_id": task_id, "safety": "bounded-project-local-preview"}
    return detail


@app.patch("/api/task-board/tasks/{task_id}")
async def patch_task_board_task(task_id: str, req: LocalTaskStatusRequest):
    """Update a project-local task status. No external tracker or runner is invoked."""
    updated = update_local_task_status(task_id, req)
    if not updated:
        return {"status": "not-found", "task_id": task_id, "safety": "project-local-status-update"}
    return updated


@app.get("/api/buildings/writing-studio")
async def building_writing_studio():
    """Read project docs and local writing drafts."""
    return writing_studio_overview()


@app.get("/api/writing-studio/overview")
async def get_writing_studio_overview():
    """Return project documents and local writing drafts."""
    return writing_studio_overview()


@app.post("/api/writing-studio/drafts")
async def post_writing_studio_draft(req: WritingDraftRequest):
    """Create a project-local Markdown draft and memory event."""
    return create_writing_draft(req)


@app.get("/api/buildings/automation-factory")
async def building_automation_factory():
    """Catalog local automation scripts and draft safe automation blueprints."""
    return automation_factory_overview()


@app.get("/api/automation-factory/overview")
async def get_automation_factory_overview():
    """Return draft-only automation script catalog, recent blueprints, and job context."""
    return automation_factory_overview()


@app.get("/api/automation-factory/scheduler")
async def get_automation_factory_scheduler():
    """Return a bounded read-only Windows scheduler snapshot."""
    return automation_scheduled_task_snapshot(20)


@app.post("/api/automation-factory/drafts")
async def post_automation_factory_draft(req: AutomationDraftRequest):
    """Create a project-local automation blueprint. No script or scheduler is invoked."""
    return create_automation_draft(req)


@app.get("/api/buildings/permission-hall")
async def building_permission_hall():
    """Read current safety classes, confirmation gates, scopes, and audit signals."""
    return permission_policy_overview()


@app.get("/api/permissions/overview")
async def get_permission_overview():
    """Return read-only policy ledger for the Permission Hall building."""
    return permission_policy_overview()


@app.get("/api/buildings/settings-center")
async def building_settings_center():
    """Inspect config registries, launchers, env requirements, and settings drafts."""
    return settings_center_overview()


@app.get("/api/settings-center/overview")
async def get_settings_center_overview():
    """Return read-only settings/config status without exposing secrets."""
    return settings_center_overview()


@app.post("/api/settings-center/drafts")
async def post_settings_center_draft(req: SettingsDraftRequest):
    """Create a project-local settings draft. No live config or secret is changed."""
    return create_settings_draft(req)


@app.get("/api/buildings/testing-arena")
async def building_testing_arena():
    """Inspect verification scripts, visual smoke artifact, logs, and test-plan drafts."""
    return testing_arena_overview()


@app.get("/api/testing-arena/overview")
async def get_testing_arena_overview():
    """Return read-only verification status and existing test-plan drafts."""
    return testing_arena_overview()


@app.get("/api/testing-arena/visual-manifest")
async def get_testing_arena_visual_manifest():
    """Return read-only all-room screenshot manifest integrity status."""
    return visual_manifest_audit()


@app.post("/api/testing-arena/test-plans")
async def post_testing_arena_test_plan(req: TestPlanDraftRequest):
    """Create a project-local test-plan draft. No command is executed."""
    return create_test_plan_draft(req)


@app.post("/api/testing-arena/vertical-slice-proofs")
async def post_testing_arena_vertical_slice_proof(req: VerticalSliceProofRequest):
    """Create a project-local vertical-slice proof report from existing evidence. No command is executed."""
    return create_vertical_slice_proof(req)


@app.get("/api/testing-arena/vertical-slice-proofs/{proof_id}")
async def get_testing_arena_vertical_slice_proof(proof_id: str):
    """Return a bounded preview of one project-local vertical-slice proof report."""
    detail = vertical_slice_proof_detail(proof_id)
    if not detail:
        return {"status": "not-found", "proof_id": proof_id, "safety": "bounded-vertical-slice-proof-preview"}
    return detail


@app.get("/api/buildings/bug-clinic")
async def building_bug_clinic():
    """Read diagnostic signals and project-local bug-report drafts."""
    return bug_clinic_overview()


@app.get("/api/bug-clinic/overview")
async def get_bug_clinic_overview():
    """Return read-only diagnostics for failed jobs/logs and known issues."""
    return bug_clinic_overview()


@app.post("/api/bug-clinic/reports")
async def post_bug_clinic_report(req: BugReportDraftRequest):
    """Create a project-local bug report draft. No fix is applied."""
    return create_bug_report_draft(req)


@app.get("/api/buildings/project-management-hall")
async def building_project_management_hall():
    """Read portfolio status across local repos, research projects, tasks, and Git metadata."""
    return project_management_overview()


@app.get("/api/project-management/overview")
async def get_project_management_overview():
    """Return read-only project portfolio status and local brief drafts."""
    return project_management_overview()


@app.post("/api/project-management/briefs")
async def post_project_management_brief(req: ProjectBriefDraftRequest):
    """Create a project-local brief draft. No repo, issue tracker, or experiment is modified."""
    return create_project_brief_draft(req)


@app.get("/api/buildings/download-station")
async def building_download_station():
    """Inspect allowlisted download folders and project-local intake drafts."""
    return download_station_overview()


@app.get("/api/download-station/overview")
async def get_download_station_overview():
    """Return shallow, read-only download intake status."""
    return download_station_overview()


@app.get("/api/download-station/triage")
async def get_download_station_triage(root_id: str = "user-downloads", limit: int = 18):
    """Return bounded read-only download risk and route triage."""
    return download_triage_snapshot(root_id, limit)


@app.post("/api/download-station/intake-drafts")
async def post_download_station_intake_draft(req: DownloadIntakeDraftRequest):
    """Create a project-local download intake draft. No files are moved, opened, fetched, or executed."""
    return create_download_intake_draft(req)


@app.get("/api/buildings/asset-gallery")
async def building_asset_gallery():
    """Inspect allowlisted asset roots, style contracts, and curation notes."""
    return asset_gallery_overview()


@app.get("/api/asset-gallery/overview")
async def get_asset_gallery_overview():
    """Return bounded asset inventory and project-local curation notes."""
    return asset_gallery_overview()


@app.get("/api/asset-gallery/inspect")
async def get_asset_gallery_inspect(root_id: str = "", relative_path: str = ""):
    """Inspect one allowlisted asset with read-only hash and image metadata."""
    return inspect_asset(root_id, relative_path)


@app.post("/api/asset-gallery/notes")
async def post_asset_gallery_note(req: AssetNoteRequest):
    """Create a project-local asset curation note. No asset file is changed."""
    return create_asset_note(req)


@app.get("/api/buildings/local-office-center")
async def building_local_office_center():
    """Inspect allowlisted office roots and project-local office notes."""
    return local_office_center_overview()


@app.get("/api/local-office-center/overview")
async def get_local_office_center_overview():
    """Return bounded office workspace status and local office notes."""
    return local_office_center_overview()


@app.post("/api/local-office-center/notes")
async def post_local_office_center_note(req: OfficeNoteRequest):
    """Create a project-local office note. No company or source document is changed."""
    return create_office_note(req)


@app.get("/api/buildings/schedule-plan-center")
async def building_schedule_plan_center():
    """Inspect local planning signals and schedule drafts without touching calendars."""
    return schedule_plan_center_overview()


@app.get("/api/schedule-plan-center/overview")
async def get_schedule_plan_center_overview():
    """Return read-only planning signals and local schedule drafts."""
    return schedule_plan_center_overview()


@app.post("/api/schedule-plan-center/drafts")
async def post_schedule_plan_center_draft(req: ScheduleDraftRequest):
    """Create a project-local schedule draft. No scheduler, calendar, or task runner is changed."""
    return create_schedule_draft(req)


@app.get("/api/buildings/learning-training-grounds")
async def building_learning_training_grounds():
    """Inspect local skill/resource signals and learning plans without installing anything."""
    return learning_training_overview()


@app.get("/api/learning-training-grounds/overview")
async def get_learning_training_grounds_overview():
    """Return read-only local learning resources and project-local plans."""
    return learning_training_overview()


@app.post("/api/learning-training-grounds/plans")
async def post_learning_training_plan(req: LearningPlanRequest):
    """Create a project-local learning plan. No skill, command, agent, or external course is invoked."""
    return create_learning_plan(req)


@app.get("/api/buildings/language-learning-area")
async def building_language_learning_area():
    """Inspect local language/UI signals and practice notes without calling translators."""
    return language_learning_overview()


@app.get("/api/language-learning-area/overview")
async def get_language_learning_area_overview():
    """Return read-only language practice signals and local notes."""
    return language_learning_overview()


@app.post("/api/language-learning-area/practice")
async def post_language_learning_practice(req: LanguagePracticeRequest):
    """Create a project-local language practice note. No translator, API, or source file is changed."""
    return create_language_practice(req)


@app.get("/api/buildings/research-data-center")
async def building_research_data_center():
    """Inspect bounded research data/result candidates without launching experiments."""
    return research_data_center_overview()


@app.get("/api/research-data-center/overview")
async def get_research_data_center_overview():
    """Return read-only research data/result candidates and local audit notes."""
    return research_data_center_overview()


@app.post("/api/research-data-center/notes")
async def post_research_data_center_note(req: ResearchDataNoteRequest):
    """Create a project-local research data note. No dataset, experiment, or server is changed."""
    return create_research_data_note(req)


@app.get("/api/buildings/paper-reading-room")
async def building_paper_reading_room():
    """Inspect bounded paper/reference candidates and local reading notes."""
    return paper_reading_room_overview()


@app.get("/api/paper-reading-room/overview")
async def get_paper_reading_room_overview():
    """Return read-only paper/reference candidates and local citation-audit notes."""
    return paper_reading_room_overview()


@app.get("/api/paper-reading-room/citation-audit")
async def get_paper_reading_room_citation_audit():
    """Return bounded read-only BibTeX duplicate and missing-field audit metadata."""
    return citation_audit_overview()


@app.post("/api/paper-reading-room/notes")
async def post_paper_reading_room_note(req: PaperReadingNoteRequest):
    """Create a project-local paper reading note. No PDFs, bibliographies, or research folders are changed."""
    return create_paper_reading_note(req)


@app.post("/api/paper-reading-room/citation-audits")
async def post_paper_reading_room_citation_audit(req: CitationAuditNoteRequest):
    """Create a project-local citation audit note. No bibliographies or manuscripts are changed."""
    return create_citation_audit_note(req)


@app.post("/api/paper-reading-room/extract-jobs")
async def post_paper_reading_room_extract_job(req: PaperExtractionJobRequest):
    """Queue bounded PDF text extraction for one allowlisted local paper candidate."""
    return queue_paper_extraction(req)


@app.get("/api/buildings/version-release-plaza")
async def building_version_release_plaza():
    """Inspect local open-source release readiness without changing GitHub or Git state."""
    return release_plaza_overview()


@app.get("/api/version-release-plaza/overview")
async def get_version_release_plaza_overview():
    """Return release-readiness artifacts, git status, verification evidence, and local drafts."""
    return release_plaza_overview()


@app.get("/api/version-release-plaza/build-readiness")
async def get_version_release_build_readiness():
    """Return read-only Godot project/export/launcher readiness."""
    return build_readiness_audit()


@app.get("/api/version-release-plaza/export-tool")
async def get_version_release_export_tool():
    """Return the latest project-local Godot export preflight/run report."""
    return godot_export_tool_audit()


@app.get("/api/version-release-plaza/packaged-launch")
async def get_version_release_packaged_launch():
    """Return read-only readiness for the packaged game launcher."""
    return packaged_launch_readiness()


@app.get("/api/version-release-plaza/release-manifest")
async def get_version_release_manifest():
    """Return read-only release package manifest integrity."""
    return release_package_manifest_audit()


@app.post("/api/version-release-plaza/checklists")
async def post_version_release_checklist(req: ReleaseChecklistDraftRequest):
    """Create a project-local release checklist. No commit, tag, push, PR, or release is created."""
    return create_release_checklist_draft(req)


@app.post("/api/version-release-plaza/reports")
async def post_version_release_report(req: ReleaseReadinessReportRequest):
    """Create a project-local release readiness report. No Git or GitHub write action is created."""
    return create_release_readiness_report(req)


@app.get("/api/buildings/plugin-registry")
async def building_plugin_registry():
    """Inspect local extension candidates and plugin drafts without installing or executing anything."""
    return plugin_registry_overview()


@app.get("/api/plugin-registry/overview")
async def get_plugin_registry_overview():
    """Return read-only plugin, registry, skill, script, and extension candidate status."""
    return plugin_registry_overview()


@app.get("/api/plugin-registry/manifests")
async def get_plugin_registry_manifests():
    """Return read-only typed plugin manifest status and activation gates."""
    return plugin_manifest_catalog()


@app.post("/api/plugin-registry/drafts")
async def post_plugin_registry_draft(req: PluginDraftRequest):
    """Create a project-local plugin proposal. No plugin, skill, registry, or script is changed."""
    return create_plugin_draft(req)


@app.post("/api/plugin-registry/activation-plans")
async def post_plugin_registry_activation_plan(req: PluginActivationPlanRequest):
    """Create a confirm-required plugin activation review plan. No plugin is activated."""
    return create_plugin_activation_plan(req)


@app.get("/api/buildings/backup-station")
async def building_backup_station():
    """Inspect backup candidates, target folders, and plan drafts without copying files."""
    return backup_station_overview()


@app.get("/api/backup-station/overview")
async def get_backup_station_overview():
    """Return read-only backup source/target status and local plan drafts."""
    return backup_station_overview()


@app.get("/api/backup-station/integrity")
async def get_backup_station_integrity(source_id: str = "ai-town-project", limit: int = 18):
    """Return bounded read-only file metadata and hashes for restore-check planning."""
    return backup_integrity_snapshot(source_id, limit)


@app.post("/api/backup-station/plans")
async def post_backup_station_plan(req: BackupPlanDraftRequest):
    """Create a project-local backup plan draft. No backup or restore action is run."""
    return create_backup_plan_draft(req)


@app.get("/api/buildings/goal-tower")
async def building_goal_tower():
    """Inspect long-term goals, plan tasks, memory signals, and goal drafts."""
    return goal_tower_overview()


@app.get("/api/goal-tower/overview")
async def get_goal_tower_overview():
    """Return read-only long-term goal signals and local goal drafts."""
    return goal_tower_overview()


@app.post("/api/goal-tower/goals")
async def post_goal_tower_goal(req: GoalDraftRequest):
    """Create a project-local goal draft. No external tracker or repo is modified."""
    return create_goal_draft(req)


@app.get("/api/buildings/inspiration-station")
async def building_inspiration_station():
    """Inspect idea signals and project-local inspiration notes."""
    return inspiration_station_overview()


@app.get("/api/inspiration-station/overview")
async def get_inspiration_station_overview():
    """Return read-only inspiration signals and local idea notes."""
    return inspiration_station_overview()


@app.post("/api/inspiration-station/notes")
async def post_inspiration_station_note(req: InspirationNoteRequest):
    """Create a project-local inspiration note. No source doc, repo, asset, or tracker is modified."""
    return create_inspiration_note(req)


@app.get("/api/buildings/temporary-draft-box")
async def building_temporary_draft_box():
    """Inspect project-local draft shelves and temporary scratch drafts."""
    return temporary_draft_box_overview()


@app.get("/api/temporary-draft-box/overview")
async def get_temporary_draft_box_overview():
    """Return draft shelf status and local temporary drafts."""
    return temporary_draft_box_overview()


@app.post("/api/temporary-draft-box/drafts")
async def post_temporary_draft(req: TempDraftRequest):
    """Create a project-local temporary draft. No promotion, routing, or external write is performed."""
    return create_temp_draft(req)


@app.post("/api/projects/{project_id}/inspect-job")
async def post_project_inspect_job(project_id: str):
    """Queue a bounded, read-only project inspection job."""
    job = start_job("project-inspect", f"Inspect project {project_id}", project_detail, project_id)
    return {
        "status": "queued",
        "job_id": job["id"],
        "kind": job["kind"],
        "label": job["label"],
        "safety": job["safety"],
    }


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Return status/result for a local backend job."""
    job = JOBS.get(job_id)
    if not job:
        return {"status": "missing", "job_id": job_id}
    return job


@app.get("/api/jobs/{job_id}/events")
async def get_job_events(job_id: str, since: int = 0, limit: int = 32):
    """Return incremental lifecycle events for a backend job."""
    return backend_job_events(job_id, since=since, limit=limit)


@app.post("/api/jobs/{job_id}/cancel")
async def post_job_cancel(job_id: str, req: JobCancelRequest):
    """Record a safe cancellation request for a backend job without killing processes."""
    return cancel_job(job_id, req)


@app.post("/api/projects/{project_id}/code-task-draft")
async def post_code_task_draft(project_id: str, req: CodeTaskDraftRequest):
    """Create a project-local coding task draft and record local task/memory state."""
    result = create_code_task_draft(project_id, req)
    if not result:
        return {"status": "missing", "project_id": project_id}
    return result


@app.post("/api/projects/{project_id}/context-pack")
async def post_code_context_pack(project_id: str, req: CodeContextPackRequest):
    """Create a project-local development context pack for a selected repository."""
    result = create_code_context_pack(project_id, req)
    if not result:
        return {"status": "missing", "project_id": project_id}
    return result


@app.post("/api/projects/{project_id}/verification-jobs")
async def post_project_verification_job(project_id: str, req: CodeVerificationJobRequest):
    """Preview or queue a confirm-required project verification command."""
    return queue_project_verification(project_id, req)


@app.post("/api/projects/{project_id}/patch-plan")
async def post_code_patch_plan(project_id: str, req: CodePatchPlanRequest):
    """Create a project-local patch plan for a selected repository without editing it."""
    result = create_code_patch_plan(project_id, req)
    if not result:
        return {"status": "missing", "project_id": project_id}
    return result


@app.get("/api/buildings/town-hall")
async def building_town_hall():
    """Architecture and decisions overview."""
    decisions = []
    try:
        dec_dir = SHARED_MEMORY_DIR / "decisions"
        for f in sorted(dec_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            first_line = f.read_text(encoding="utf-8").split("\n")[0]
            decisions.append({"name": f.stem, "title": first_line.strip("# -")})
    except:
        pass
    atlas = town_capability_atlas()
    workflow_routes = town_workflow_routes()
    return {
        "name": "Town Hall",
        "role": "Architecture & Global Decisions",
        "recent_decisions": decisions,
        "capability_atlas": atlas,
        "workflow_routes": workflow_routes,
        "capability_count": atlas.get("connected_count", 0),
        "building_count": atlas.get("building_count", 0),
        "workflow_route_count": workflow_routes.get("route_count", 0),
        "safe_note": "Town Hall shows architecture decisions and a read-only capability atlas. It does not scan new roots, run commands, invoke agents, edit files, or contact external services.",
    }


@app.get("/api/buildings/file-vault")
async def building_file_vault():
    """Read-only local file and project map for the Godot File Vault."""
    return file_vault_roots()


@app.get("/api/file-vault/roots")
async def get_file_vault_roots():
    """Return allowlisted File Vault roots. No recursive scan is performed."""
    return file_vault_roots()


@app.get("/api/file-vault/list/{root_id}")
async def get_file_vault_list(root_id: str, path: str = "", offset: int = 0, limit: int = 40):
    """Return one lazy, bounded directory page inside an allowlisted root."""
    listing = file_vault_listing(root_id, path, offset, limit)
    if not listing:
        return {"status": "missing", "root_id": root_id, "relative_path": path, "items": [], "count": 0}
    return listing


@app.get("/api/file-vault/preview/{root_id}")
async def get_file_vault_preview(root_id: str, path: str = ""):
    """Return a bounded preview for a small text-like file inside an allowlisted root."""
    preview = file_vault_preview(root_id, path)
    if not preview:
        return {"status": "missing", "root_id": root_id, "relative_path": path}
    return preview


@app.get("/api/file-vault/index")
async def get_file_vault_index():
    """Return File Vault cached index status without scanning live folders."""
    return file_vault_index_overview()


@app.post("/api/file-vault/index-job")
async def post_file_vault_index_job():
    """Queue a bounded allowlisted File Vault index refresh."""
    job = start_job("file-vault-index", "Refresh File Vault cache", build_file_vault_index)
    return {
        "status": "queued",
        "job_id": job["id"],
        "kind": job["kind"],
        "safety": "allowlisted-read-cache-write",
    }


@app.get("/api/file-vault/search")
async def get_file_vault_search(q: str = "", root_id: str = "all", kind: str = "all", page: int = 1, page_size: int = 12):
    """Search the cached File Vault index with pagination."""
    return file_vault_search(q, root_id, kind, page, page_size)


@app.get("/api/file-vault/organize-audit")
async def get_file_vault_organize_audit():
    """Audit cached File Vault organization signals without scanning or modifying source files."""
    return file_vault_organize_audit()


@app.post("/api/file-vault/tags")
async def post_file_vault_tag(req: FileTagRequest):
    """Save a project-local tag for an allowlisted File Vault item without editing the source file."""
    return tag_file_vault_item(req)


@app.post("/api/file-vault/open")
async def post_file_vault_open(req: FileOpenRequest):
    """Open or reveal an allowlisted File Vault item with the local OS. No file contents are changed."""
    return open_file_vault_item(req)


@app.post("/api/file-vault/organize-proposals")
async def post_file_vault_organize_proposal(req: FileOrganizeProposalRequest):
    """Create a project-local file organization proposal without modifying source files."""
    return create_file_organize_proposal(req)


@app.get("/api/buildings/research-hall")
async def building_research_hall():
    """Summarize active research projects from real local roots and shared memory facts."""
    projects = []
    fact_names = [
        "pony-current-status.md",
        "pony-ccrp-four-domain-status.md",
        "proteinshift-status.md",
        "analog-agent-status.md",
        "donebench-status.md",
        "tglrec-current-status.md",
        "truce-rec-current-status.md",
    ]
    facts_dir = SHARED_MEMORY_DIR / "facts"
    for name in fact_names:
        path = facts_dir / name
        if not path.exists():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            title = next((line.strip("# ").strip() for line in lines if line.startswith("#")), path.stem)
            projects.append({"file": name, "title": title, "path": str(path)})
        except Exception as exc:
            projects.append({"file": name, "title": path.stem, "error": str(exc)})
    real_projects = all_research_project_cards()
    return {
        "name": "Research Hall",
        "research_root": str(RESEARCH_ROOT),
        "research_root_exists": RESEARCH_ROOT.exists(),
        "active_projects": projects,
        "projects": real_projects,
        "count": len(real_projects),
        "status_file_count": len(projects),
    }


@app.get("/api/research/projects")
async def get_research_projects():
    """List playable real research projects for the Research Hall."""
    projects = all_research_project_cards()
    return {
        "name": "Research Project Index",
        "research_root": str(RESEARCH_ROOT),
        "research_root_exists": RESEARCH_ROOT.exists(),
        "projects": projects,
        "count": len(projects),
        "mode": "read-only",
    }


@app.get("/api/research/projects/{project_id}")
async def get_research_project(project_id: str):
    """Return bounded details for one real research project."""
    detail = research_project_detail(project_id)
    if not detail:
        return {
            "status": "missing",
            "project_id": project_id,
            "message": "Unknown research project id.",
        }
    detail["status"] = "ok"
    return detail


@app.post("/api/research/projects/{project_id}/logs")
async def post_research_project_log(project_id: str, req: ResearchLogDraftRequest):
    """Create a project-local Research Hall log draft without touching research repos."""
    result = create_research_log_draft(project_id, req)
    if not result:
        return {
            "status": "missing",
            "project_id": project_id,
            "message": "Unknown research project id.",
        }
    return result


@app.get("/api/buildings/agent-hub")
async def building_agent_hub():
    """Read-only status for local agent coordination files."""
    return agent_hub_overview()


@app.get("/api/agent-hub/overview")
async def get_agent_hub_overview():
    """Return the real local multi-agent coordination surface without launching anything."""
    return agent_hub_overview()


@app.get("/api/agent-hub/roster")
async def get_agent_hub_roster():
    """Return detected local agent launchers and draft-only dispatch metadata."""
    overview = agent_hub_overview()
    return {
        "status": "ok",
        "name": "Agent Roster",
        "roster": overview["roster"],
        "runner_readiness": overview["runner_readiness"],
        "runner_ready_count": overview["runner_ready_count"],
        "runner_handoff_dir": overview["runner_handoff_dir"],
        "companions": overview["companions"],
        "companion_count": overview["companion_count"],
        "agent_count": overview["agent_count"],
        "launcher_count": overview["launcher_count"],
        "dispatch_mode": overview["dispatch_mode"],
        "safe_note": overview["safe_note"],
    }


@app.get("/api/agent-runners/readiness")
async def get_agent_runner_readiness():
    """Return read-only local agent runner readiness without starting any runner."""
    return agent_runner_readiness()


@app.post("/api/agent-runners/dispatch-preview")
async def post_agent_runner_dispatch_preview(req: AgentRunnerDispatchPreviewRequest):
    """Create a confirm-required local agent runner dispatch preview without launching a runner."""
    return create_agent_runner_dispatch_preview(req)


@app.post("/api/agent-runners/launch-jobs")
async def post_agent_runner_launch_job(req: AgentRunnerLaunchJobRequest):
    """Preview or queue a confirm-required external agent runner launch job."""
    return create_agent_runner_launch_job(req)


@app.get("/api/agent-hub/companions")
async def get_agent_hub_companions():
    """Return recruitable Agent Hub companion metadata. Player ownership is saved locally in Godot."""
    companions = agent_companion_cards()
    return {
        "status": "ok",
        "mode": "local-player-companion-metadata",
        "companions": companions,
        "count": len(companions),
        "safe_note": "This endpoint returns metadata only. Recruiting/equipping companions updates the Godot local save file and does not launch, stop, or contact agent runners.",
    }


@app.get("/api/agent-hub/mailboxes")
async def get_agent_hub_mailboxes():
    """Return real Agent Hub mailbox files when the hub state directory exists."""
    overview = agent_hub_overview()
    return {
        "status": "ok",
        "hub_exists": overview["hub_exists"],
        "state_exists": overview["state_exists"],
        "mailboxes": overview["mailboxes"],
        "mailbox_count": overview["mailbox_count"],
        "logs": overview["logs"],
        "log_count": overview["log_count"],
    }


@app.post("/api/agent-hub/dispatch-drafts")
async def post_agent_dispatch_draft(req: AgentDispatchDraftRequest):
    """Create a project-local dispatch draft; do not send to or start an agent runner."""
    return create_agent_dispatch_draft(req)


@app.get("/api/agent-chat/sessions")
async def get_agent_chat_sessions():
    """Return project-local Agent Chat sessions."""
    sessions = agent_chat_sessions()
    return {
        "status": "ok",
        "mode": "project-local-agent-chat",
        "sessions": sessions,
        "count": len(sessions),
        "chat_dir": str(AGENT_CHAT_DIR),
        "safe_note": "Agent Chat stores local session logs and safe context. It does not start external runners or execute shell commands.",
    }


@app.post("/api/agent-chat/sessions")
async def post_agent_chat_session(req: AgentChatSessionRequest):
    """Create a project-local Agent Chat session."""
    return create_agent_chat_session(req)


@app.get("/api/agent-chat/sessions/{session_id}")
async def get_agent_chat_session(session_id: str):
    """Return one Agent Chat session."""
    session = load_agent_chat(session_id)
    if not session:
        return {"status": "missing", "session_id": session_id}
    return {
        "status": "ok",
        "chat_session": agent_chat_summary(session),
        "session": session,
    }


@app.post("/api/agent-chat/sessions/{session_id}/messages")
async def post_agent_chat_message(session_id: str, req: AgentChatMessageRequest):
    """Append a message to a project-local Agent Chat session and build a safe context response."""
    return append_agent_chat_message(session_id, req)


@app.get("/api/agent-tasks/queue")
async def get_agent_tasks_queue():
    """Return the safe local agent task queue without launching external agent runners."""
    return agent_task_snapshot()


@app.get("/api/agent-tasks/policy")
async def get_agent_tasks_policy():
    """Return the safe local agent task concurrency policy and backpressure state."""
    return agent_task_queue_policy()


@app.get("/api/agent-tasks/logs")
async def get_agent_task_logs(limit: int = 20):
    """Return recent durable safe local agent task logs without replaying tasks."""
    bounded_limit = max(1, min(limit, 50))
    logs = latest_agent_task_logs(bounded_limit)
    return {
        "status": "ok",
        "mode": "read-only-agent-task-log-archive",
        "logs": logs,
        "count": len(logs),
        "returned": len(logs),
        "log_dir": str(AGENT_TASK_LOG_DIR),
        "safe_note": "Agent task log archive is read-only project-local evidence. It does not replay tasks, start external runners, execute shell commands, mutate files, contact remote APIs, or perform rollback.",
    }


@app.get("/api/agent-tasks/logs/{log_id}")
async def get_agent_task_log_detail(log_id: str):
    """Return one durable safe local agent task log with bounded result preview."""
    return read_agent_task_log(log_id)


@app.post("/api/agent-tasks/submit")
async def post_agent_task(req: AgentTaskSubmitRequest):
    """Submit a bounded local read-only brief task for Agent Hub visibility."""
    return submit_agent_task(req)


@app.get("/api/agent-tasks/{task_id}")
async def get_agent_task_detail(task_id: str):
    """Return one safe local agent task and its result/log metadata."""
    return get_agent_task(task_id)


@app.get("/api/agent-tasks/{task_id}/events")
async def get_agent_task_event_stream(task_id: str, since: int = 0, limit: int = 32):
    """Return a bounded polling event stream for one safe local agent task."""
    return get_agent_task_events(task_id, since=since, limit=limit)


@app.post("/api/agent-tasks/{task_id}/pause")
async def post_agent_task_pause(task_id: str):
    """Pause a queued local agent task when possible."""
    return pause_agent_task(task_id)


@app.post("/api/agent-tasks/{task_id}/cancel")
async def post_agent_task_cancel(task_id: str, req: Optional[AgentTaskCancelRequest] = None):
    """Cancel a queued or paused local agent task, or request cancellation for a running one."""
    return cancel_agent_task(task_id, req or AgentTaskCancelRequest())


@app.post("/api/agent-tasks/{task_id}/resume")
async def post_agent_task_resume(task_id: str):
    """Resume a paused local agent task."""
    return resume_agent_task(task_id)


@app.get("/api/agent-tools/catalog")
async def get_agent_tool_catalog():
    """Return safe registered tools available to Agent Hub and future agent runners."""
    return {
        "status": "ok",
        "mode": "safe-agent-tool-registry",
        "tools": agent_tool_catalog(),
        "count": len(agent_tool_catalog()),
        "queue": agent_tool_invocation_snapshot(),
    }


@app.get("/api/agent-tools/invocations")
async def get_agent_tool_invocations():
    """Return recent safe agent tool invocations."""
    return agent_tool_invocation_snapshot()


@app.get("/api/agent-tools/logs")
async def get_agent_tool_logs(limit: int = 20):
    """Return recent durable safe registered tool logs without replaying tools."""
    bounded_limit = max(1, min(limit, 50))
    logs = latest_agent_tool_logs(bounded_limit)
    return {
        "status": "ok",
        "mode": "read-only-agent-tool-log-archive",
        "logs": logs,
        "count": len(logs),
        "returned": len(logs),
        "log_dir": str(AGENT_TOOL_LOG_DIR),
        "safe_note": "Agent tool log archive is read-only project-local evidence. It does not replay tools, start external runners, execute shell commands, mutate files, contact remote APIs, or perform rollback.",
    }


@app.get("/api/agent-tools/logs/{log_id}")
async def get_agent_tool_log_detail(log_id: str):
    """Return one durable safe registered tool log with bounded result preview."""
    return read_agent_tool_log(log_id)


@app.post("/api/agent-tools/invoke")
async def post_agent_tool_invoke(req: AgentToolInvokeRequest):
    """Queue a safe registered tool invocation."""
    return invoke_agent_tool(req)


@app.get("/api/agent-tools/invocations/{invocation_id}")
async def get_agent_tool_invocation_detail(invocation_id: str):
    """Return one agent tool invocation result and log metadata."""
    return get_agent_tool_invocation(invocation_id)


@app.get("/api/agent-tools/invocations/{invocation_id}/events")
async def get_agent_tool_invocation_event_stream(invocation_id: str, since: int = 0, limit: int = 32):
    """Return a bounded polling event stream for one safe registered tool invocation."""
    return get_agent_tool_invocation_events(invocation_id, since=since, limit=limit)


@app.get("/api/buildings/resource-market")
async def building_resource_market():
    """Summarize available local agent resources."""
    root = Path(r"D:\agent-resources")
    entries = []
    if root.exists():
        for child in sorted(root.iterdir(), key=lambda p: p.name.lower())[:30]:
            entries.append({"name": child.name, "kind": "dir" if child.is_dir() else "file", "path": str(child)})
    return {"name": "Resource Market", "exists": root.exists(), "entries": entries, "count": len(entries)}


@app.get("/api/workbench/quests")
async def get_workbench_quests():
    """Playable read-only work quests for the Godot client."""
    overview = quest_registry_overview()
    return {
        "quests": overview["quests"],
        "mode": overview["mode"],
        "registry": overview["path"],
        "registry_exists": overview["exists"],
        "count": overview["count"],
    }


@app.get("/api/workbench/daily-routes")
async def get_workbench_daily_routes():
    """Generate today's safe playable local-work routes for the Godot client."""
    return daily_routes_overview()


@app.post("/api/workbench/action")
async def run_workbench_action(req: WorkbenchActionRequest):
    """Run local workbench actions with explicit safety levels."""
    if req.action_id == "scan-current-building" and req.building_id:
        data = await building_data_for(req.building_id)
        if data:
            return {
                "status": "done",
                "safety": "read-only",
                "action_id": req.action_id,
                "building_id": req.building_id,
                "result": data,
            }
    if req.action_id in {"prepare-work-note", "confirm-save-work-note"} and req.building_id:
        data = await building_data_for(req.building_id)
        if data:
            title, content = draft_note_for(req.building_id, data)
            if req.draft_title:
                title = req.draft_title.strip() or title
                content = content.replace(content.splitlines()[1], f"title: {title}", 1).replace(content.splitlines()[6], f"# {title}", 1)
            filename = f"{slugify_filename(title)}.md"
            target = DRAFTS_DIR / filename
            if req.action_id == "prepare-work-note":
                return {
                    "status": "preview",
                    "safety": "write-requires-confirmation",
                    "action_id": req.action_id,
                    "building_id": req.building_id,
                    "target_path": str(target),
                    "confirmation_required": CONFIRM_SAVE_DRAFT,
                    "preview": content,
                }
            if req.confirmation != CONFIRM_SAVE_DRAFT:
                return {
                    "status": "confirmation-required",
                    "safety": "write-blocked",
                    "action_id": req.action_id,
                    "building_id": req.building_id,
                    "target_path": str(target),
                    "confirmation_required": CONFIRM_SAVE_DRAFT,
                    "message": "Send the exact confirmation phrase to save this project-local draft.",
                }
            DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return {
                "status": "saved",
                "safety": "project-local-write",
                "action_id": req.action_id,
                "building_id": req.building_id,
                "target_path": str(target),
                "bytes": target.stat().st_size,
            }
    return {
        "status": "unsupported",
        "safety": "read-only",
        "action_id": req.action_id,
        "building_id": req.building_id,
        "message": "Supported actions: scan-current-building, prepare-work-note, confirm-save-work-note.",
    }


@app.get("/api/workbench/rooms/{building_id}")
async def get_workbench_room(building_id: str):
    """Return a game-oriented room payload for a building interior/workbench."""
    data = await building_data_for(building_id)
    if not data:
        return {
            "status": "missing",
            "building_id": building_id,
            "room_title": building_id,
            "cards": [],
            "actions": [],
        }
    meta = ROOM_META.get(building_id, {})
    return {
        "status": "ok",
        "building_id": building_id,
        "room_title": meta.get("room_title", data.get("name", building_id)),
        "npc": meta.get("npc", "Codex"),
        "atmosphere": meta.get("atmosphere", "a local workspace room"),
        "workbench": meta.get("workbench", "Workbench"),
        "cards": room_cards_for(building_id, data),
        "actions": [
            {
                "id": "scan-current-building",
                "label": "Run safe read-only scan",
                "safety": "read-only",
            },
            {
                "id": "prepare-work-note",
                "label": "Prepare work note preview",
                "safety": "preview-only",
            },
            {
                "id": "confirm-save-work-note",
                "label": "Confirm and save work note",
                "safety": "project-local-write",
                "confirmation_required": CONFIRM_SAVE_DRAFT,
            }
        ],
    }


@app.get("/api/tasks")
async def get_tasks():
    """Get current tasks/actions from agentmemory if available."""
    local_tasks = load_task_ledger()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(f"{AGENTMEMORY_URL}/mcp/call", json={
                "method": "memory_frontier",
                "params": {"limit": 10}
            })
            if r.status_code == 200:
                data = r.json()
                data["local_tasks"] = local_tasks[:30]
                data["local_task_count"] = len(local_tasks)
                return data
    except:
        pass
    return {"tasks": local_tasks[:30], "local_task_count": len(local_tasks), "source": "project-local-ledger"}


@app.get("/api/inventory")
async def get_inventory():
    """List real projects from D: drive."""
    projects = []
    project_dirs = [
        ("Research", Path(r"D:\Research")),
        ("Company", Path(r"D:\Company")),
        ("Terraria Archive", Path(r"D:\Terraria_doc")),
        ("Agent Resources", Path(r"D:\agent-resources")),
        ("Devtools", Path(r"D:\devtools")),
    ]
    for name, p in project_dirs:
        if p.exists():
            children = list(islice(p.iterdir(), 100))
            subdirs = [d.name for d in children if d.is_dir()][:10]
            projects.append({"name": name, "path": str(p), "items": subdirs, "sampled_count": len(children), "sample_limit": 100})
    return {"projects": projects}
