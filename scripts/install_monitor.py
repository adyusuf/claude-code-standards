#!/usr/bin/env python3
"""claude-monitor's agent (cm-agent) for `install.py --with-monitor`: clone, build, register, connect.

Built from source because claude-monitor publishes no release yet (its ADR-0002 phase 4 brings installers and
hosting), so it needs the .NET 10 SDK. Nothing is registered with the OS: the agent ships as a Claude Code plugin
(11 hooks + an MCP server), and Claude Code starts it with its sessions.

ACTIVE ONLY WHILE CONNECTED (user decision 04/10/2026): with no server there is nowhere to send events, so the
plugin is registered DISABLED — Claude Code then runs none of its hooks and no MCP server, the daemon is never
woken, and nothing is queued. Connecting enables it; every run re-derives the switch from `cm-agent status`:
    install.py --with-monitor                 build + register; enabled only if already connected
    install.py --monitor-server URL           connect (a code a person approves on the web) -> enabled
    cm-agent logout; install.py --monitor-sync   -> disabled again
The switch is written straight into ~/.claude/settings.json (extraKnownMarketplaces + enabledPlugins), so the
`claude` CLI is not needed; settings.json is backed up first and an unparsable one is never touched.

Exit codes: 0 done (ACTIVE, or DORMANT because no server is connected — said loudly) · 2 refused or failed.
"""
import importlib.util
import os
import platform
import subprocess

HERE = os.path.dirname(os.path.realpath(__file__))
REPO_URL = 'https://github.com/adyusuf/claude-monitor.git'
# The ONE place the claude-monitor servers are named (#2); `install.py --prod` (default) / `--test` / `--dev`
# pick one, `--monitor-server` overrides it. User decision 04/10/2026; dev is a LOCAL API on port 9872 (the
# agent accepts http only on loopback).
SERVERS = {'prod': 'https://monitor.bitreka.com', 'test': 'https://testmonitor.bitreka.com',
           'dev': 'http://localhost:9872'}
HOME_ENV = 'CLAUDE_MONITOR_HOME'                       # the same variable the board launchers read
DEFAULT_CLONE = os.path.join('~', 'ClaudeCode', 'claude-monitor')
PROJECT = os.path.join('src', 'ClaudeMonitor.Agent')
SDK_MAJOR = '10'
MARKETPLACE = 'monitor-agent-local'                    # AgentConfig.MarketplaceName
PLUGIN = 'monitor-agent@' + MARKETPLACE                # AgentConfig.PluginName @ marketplace

_spec = importlib.util.spec_from_file_location('install_live_hooks', os.path.join(HERE, 'install-live-hooks.py'))
settings_io = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(settings_io)


def default_run(command, capture=False):
    """capture: return the output. Otherwise STREAM it, line by line, through this process's stdout — so that
    install.py's log holds the git/dotnet/cm-agent output too, not only the console (user request 04/10/2026)."""
    try:
        if capture:
            return subprocess.run(command, capture_output=True, text=True)
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                              encoding='utf-8', errors='replace', bufsize=1) as child:
            for line in child.stdout:
                print(line, end='')
        return subprocess.CompletedProcess(command, child.returncode, '', '')
    except OSError as error:                            # the tool is not installed
        return subprocess.CompletedProcess(command, 127, '', str(error))


def clone_dir(env):
    return os.path.expanduser(env.get(HOME_ENV) or DEFAULT_CLONE)


def runtime_id(system, machine):
    """The dotnet RID the agent ships for (osx-arm64, osx-x64, win-x64, win-arm64), or None."""
    arch = {'arm64': 'arm64', 'aarch64': 'arm64', 'x86_64': 'x64', 'amd64': 'x64'}.get(machine.lower())
    family = {'Windows': 'win', 'Darwin': 'osx'}.get(system)
    return f'{family}-{arch}' if family and arch else None


def binary_name(system):
    return 'cm-agent.exe' if system == 'Windows' else 'cm-agent'


def agent_home(env, system):
    """Mirrors the agent's AgentConfig.DefaultHome (CM_AGENT_HOME overrides it there too)."""
    if env.get('CM_AGENT_HOME'):
        return env['CM_AGENT_HOME']
    if system == 'Windows':
        return os.path.join(env.get('LOCALAPPDATA') or os.path.expanduser(os.path.join('~', 'AppData', 'Local')),
                            'ClaudeMonitor')
    return os.path.expanduser(os.path.join('~', 'Library', 'Application Support', 'ClaudeMonitor'))


def installed_binary(env, system):
    return os.path.join(agent_home(env, system), 'bin', binary_name(system))


def has_sdk(run):
    result = run(['dotnet', '--list-sdks'], capture=True)
    return result.returncode == 0 and any(line.split('.')[0] == SDK_MAJOR for line in result.stdout.splitlines())


def is_connected(run, binary):
    return run([binary, 'status'], capture=True).returncode == 0          # status exits 1 when not connected


def plugin_state(home):
    """True/False as registered in settings.json, None if not registered (or unreadable)."""
    try:
        data, _ = settings_io.load_settings(os.path.join(home, '.claude', 'settings.json'))
    except (ValueError, OSError):
        return None
    return data.get('enabledPlugins', {}).get(PLUGIN)


def set_plugin(home, plugin_dir, enabled):
    """Register the agent's local marketplace and switch its plugin on or off. None if settings.json is unreadable."""
    claude = os.path.join(home, '.claude')
    path = os.path.join(claude, 'settings.json')
    try:
        data, newline = settings_io.load_settings(path)
    except (ValueError, OSError) as error:
        print(f'✗ settings.json is unreadable, nothing changed: {error}')
        return None
    marketplace = {'source': {'source': 'directory', 'path': plugin_dir}}
    if data.get('extraKnownMarketplaces', {}).get(MARKETPLACE) == marketplace and \
            data.get('enabledPlugins', {}).get(PLUGIN) is enabled:
        return enabled
    data.setdefault('extraKnownMarketplaces', {})[MARKETPLACE] = marketplace
    data.setdefault('enabledPlugins', {})[PLUGIN] = enabled
    settings_io.backup(path, os.path.join(claude, 'backups'))
    os.makedirs(claude, exist_ok=True)
    settings_io.save_settings(path, data, newline)
    return enabled


def sync(run=default_run, env=os.environ, system=platform.system(), home=os.path.expanduser('~')):
    """Derive the switch from the connection: connected -> enabled, otherwise disabled. Says which, loudly."""
    binary = installed_binary(env, system)
    connected = is_connected(run, binary)
    if set_plugin(home, os.path.join(agent_home(env, system), 'claude-plugin'), connected) is None:
        return 2
    if connected:
        print('  ACTIVE    connected: the plugin is ENABLED — its hooks and the agent run from the next session')
    else:
        print('⚠️  DORMANT: no server connected — the plugin (11 hooks + MCP) is DISABLED, the agent does not run and '
              f'nothing is queued. Activate it with: install.py --monitor-server <url>')
    return 0


def install(server=None, run=default_run, env=os.environ, system=platform.system(), machine=platform.machine(),
            exists=os.path.exists, home=os.path.expanduser('~')):
    binary = installed_binary(env, system)
    if server and exists(binary):                       # already built: connecting needs no rebuild
        return connect(server, run, env, system, home)
    rid = runtime_id(system, machine)
    if not rid:
        print(f'✗ cm-agent ships for macOS and Windows only; this is {system}/{machine}')
        return 2
    if not has_sdk(run):
        print(f'✗ the .NET {SDK_MAJOR} SDK is required to build cm-agent (dotnet --list-sdks shows none)')
        return 2
    clone = clone_dir(env)
    if exists(os.path.join(clone, PROJECT)):
        print(f'  using     {clone} (left as it is; update it with git -C "{clone}" pull)')
    elif exists(clone):
        print(f'✗ {clone} exists but has no {PROJECT} — an older checkout (the archived Python board?). '
              f'Move it aside, or point {HOME_ENV} somewhere else')
        return 2
    elif run(['git', 'clone', REPO_URL, clone]).returncode != 0:
        print(f'✗ git clone {REPO_URL} failed')
        return 2
    out = os.path.join(clone, 'out', rid)
    if run(['dotnet', 'publish', os.path.join(clone, PROJECT), '-c', 'Release', '-r', rid, '-o', out]).returncode:
        print('✗ dotnet publish failed — the output above says why')
        return 2
    # Copies the binary and writes the plugin. Its own `claude plugin` registration may fail without the CLI
    # (exit 1): that is fine, set_plugin() registers it through settings.json and decides on/off.
    registered = run([os.path.join(out, binary_name(system)), 'install']).returncode
    if registered not in (0, 1):
        print(f'✗ cm-agent install failed (exit {registered})')
        return 2
    return connect(server, run, env, system, home) if server else sync(run, env, system, home)


def connected_to(run, binary):
    """The server cm-agent is connected to, from `status` ("connected: <url>"), or None."""
    result = run([binary, 'status'], capture=True)
    for line in (result.stdout or '').splitlines():
        if result.returncode == 0 and line.startswith('connected: '):
            return line[len('connected: '):].strip().rstrip('/')
    return None


def connect(server, run=default_run, env=os.environ, system=platform.system(), home=os.path.expanduser('~')):
    binary = installed_binary(env, system)
    if connected_to(run, binary) == server.rstrip('/'):
        print(f'  already connected to {server} — no new code needed')
        return sync(run, env, system, home)
    if run([binary, 'login', '--server', server]).returncode:
        print('✗ cm-agent login did not complete (denied, expired, or the server did not answer)')
        sync(run, env, system, home)                     # the switch still follows the connection: no dangling hooks
        return 2
    return sync(run, env, system, home)


def check(run=default_run, env=os.environ, system=platform.system(), exists=os.path.exists,
          home=os.path.expanduser('~')):
    """Problems: the agent not installed, or the switch disagreeing with the connection. DORMANT is not a problem."""
    binary = installed_binary(env, system)
    if not exists(binary):
        print(f'  missing     {binary} (cm-agent)')
        return 1
    connected, enabled = is_connected(run, binary), plugin_state(home)
    if enabled is connected:
        print(f'  ok          cm-agent {"ACTIVE (connected, enabled)" if connected else "DORMANT (no server, disabled)"}')
        return 0
    print(f'  MISMATCH    connected={connected} but plugin enabled={enabled} — run install.py --monitor-sync')
    return 1


def remove(run=default_run, env=os.environ, system=platform.system(), exists=os.path.exists,
           home=os.path.expanduser('~')):
    """Unregisters the plugin. The agent's data stays in its home (the agent's own uninstall does the same)."""
    binary = installed_binary(env, system)
    if exists(binary):
        run([binary, 'uninstall'])
    path = os.path.join(home, '.claude', 'settings.json')
    try:
        data, newline = settings_io.load_settings(path)
    except (ValueError, OSError):
        return 0
    known, enabled = data.get('extraKnownMarketplaces', {}), data.get('enabledPlugins', {})
    if MARKETPLACE in known or PLUGIN in enabled:
        known.pop(MARKETPLACE, None)
        enabled.pop(PLUGIN, None)
        for key in ('extraKnownMarketplaces', 'enabledPlugins'):
            if key in data and not data[key]:
                del data[key]
        settings_io.backup(path, os.path.join(home, '.claude', 'backups'))
        settings_io.save_settings(path, data, newline)
        print('  removed   the monitor plugin from settings.json')
    return 0
