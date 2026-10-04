#!/usr/bin/env python3
"""claude-monitor's agent (cm-agent) for `install.py --with-monitor`: clone, build, register, optionally connect.

Built from source because claude-monitor publishes no release yet (its ADR-0002 phase 4 brings installers and
hosting), so it needs the .NET 10 SDK. Nothing is registered with the OS: `cm-agent install` copies the binary to
the agent home and registers a Claude Code plugin (hooks + MCP), and Claude Code starts the agent with its
sessions. Connecting (`--monitor-server URL`) shows a code that a person approves on the web — it cannot be
completed unattended, and without it the agent only queues events locally.

Exit codes: 0 done · 2 refused or failed · 3 installed but incomplete (the output names the step that did not run).
"""
import os
import platform
import subprocess

REPO_URL = 'https://github.com/adyusuf/claude-monitor.git'
HOME_ENV = 'CLAUDE_MONITOR_HOME'                       # the same variable the board launchers read
DEFAULT_CLONE = os.path.join('~', 'ClaudeCode', 'claude-monitor')
PROJECT = os.path.join('src', 'ClaudeMonitor.Agent')
SDK_MAJOR = '10'


def default_run(command, capture=False):
    try:
        return subprocess.run(command, capture_output=capture, text=True)
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


def install(server=None, run=default_run, env=os.environ, system=platform.system(), machine=platform.machine(),
            exists=os.path.exists):
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
    code = 0
    registered = run([os.path.join(out, binary_name(system)), 'install']).returncode
    if registered == 1:                                  # the agent printed the two `claude plugin` commands
        print('⚠️  INCOMPLETE: the plugin is NOT registered — the claude CLI was not on PATH. '
              'Run the two `claude plugin` commands printed above.')
        code = 3
    elif registered:
        print(f'✗ cm-agent install failed (exit {registered})')
        return 2
    binary = installed_binary(env, system)
    if server:
        if run([binary, 'login', '--server', server]).returncode:
            print('✗ cm-agent login did not complete')
            return 2
    else:
        print(f'⚠️  NOT CONNECTED: events stay queued on this machine until you run  "{binary}" login --server <url>')
        code = code or 3
    run([binary, 'status'])
    return code


def check(run=default_run, env=os.environ, system=platform.system(), exists=os.path.exists):
    """Problems found: the agent not installed, or installed but not connected (status exits 1)."""
    binary = installed_binary(env, system)
    if not exists(binary):
        print(f'  missing     {binary} (cm-agent)')
        return 1
    print(f'  ok          {binary}')
    return 1 if run([binary, 'status']).returncode else 0


def remove(run=default_run, env=os.environ, system=platform.system(), exists=os.path.exists):
    """Unregisters the plugin. The agent's data stays in its home (the agent's own uninstall does the same)."""
    binary = installed_binary(env, system)
    if exists(binary):
        run([binary, 'uninstall'])
    else:
        print(f'  cm-agent is not installed ({binary})')
    return 0
