# Claude Code Sandbox Feature Documentation

## Overview

Claude Code includes a **sandbox feature** that restricts command execution to prevent unintended system modifications. By default, all Bash commands run in a sandboxed environment with limited filesystem and network access.

## Purpose

The sandbox provides:
- **Safety**: Prevents accidental modification of system files or sensitive data
- **Control**: Restricts operations to designated directories
- **Security**: Limits network access to approved hosts
- **Transparency**: Logs all restricted operations for review

---

## Sandbox Restrictions Used in This Project

### 1. Filesystem Restrictions

During the Semgrep security scan, we encountered sandbox restrictions that prevented:

#### **Write Access Limitations**
By default, write operations are **only allowed** in:
- `/dev/stdout`, `/dev/stderr`, `/dev/null`, `/dev/tty`
- `/tmp/claude` and `/private/tmp/claude` (temporary files)
- `~/.npm/_logs` (npm logs)
- `~/.claude/debug` (debug logs)
- `.` (current working directory)

#### **Write Access Denied** in:
- `~/.claude/settings.json`
- `.claude/settings.json` (project-specific)
- `.claude/settings.local.json`
- `/etc/claude-code/managed-settings.json`
- **User home directory files** like `~/.semgrep/` (encountered in this project)

### 2. Network Restrictions

Network access is **only allowed** to:
- `github.com`
- `raw.githubusercontent.com`

All other network requests are blocked by default.

### 3. Read Access

Read operations have a **deny-only** policy (currently no restrictions), but write operations are strictly limited.

---

## Current Sandbox Status in This Project

**Sandbox is currently ENABLED** on this project repository.

Configuration in `.claude/settings.local.json`:
```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true
  }
}
```

This means all commands run with sandbox restrictions by default, with automatic prompting when operations require elevated access.

---

## Error Messages Indicating Sandbox Restrictions

When the sandbox blocks an operation, you'll see errors like:

### **Filesystem Error**
```
OSError: [Errno 30] Read-only file system: '/home/vasu/.semgrep/settingstc3_uwlb.yml'
```

### **Permission Error**
```
Operation not permitted
```

### **Network Error**
```
Network connection failed (host not in allowlist)
```

---

## Best Practices for Sandbox Usage

### ✅ **Keep Sandbox Enabled When Possible**
- Run read-only operations (file reads, searches) with sandbox enabled
- Use sandbox for git operations within the project directory
- Default to sandboxed execution for safety

### ⚠️ **Disable Sandbox Only When Required**
Disable sandbox (`dangerouslyDisableSandbox: true`) only when:
1. You see evidence of sandbox-caused failure (permission errors, read-only filesystem)
2. The operation explicitly requires system-level access
3. Installing tools or packages to user directories
4. The user explicitly requests bypassing sandbox restrictions

### 🔒 **Never Disable for Sensitive Operations**
Keep sandbox **enabled** for:
- Operations involving `.env` files
- Modifying credential files (`~/.ssh/*`, `~/.aws/*`)
- Writing to `~/.bashrc`, `~/.zshrc`, or shell configuration
- Any operation that could expose secrets

---

## How to Manage Sandbox Settings

### Command: `/sandbox`
Use this command in Claude Code to:
- View current sandbox restrictions
- Modify allowed paths
- Add network hosts to the allowlist
- Review blocked operations

### Example Workflow
1. Try running a command with sandbox enabled (default)
2. If it fails with permission errors, analyze the error
3. Retry with `dangerouslyDisableSandbox: true` if necessary
4. Use `/sandbox` to add permanent exceptions if needed

---

## Alternative: Using `/tmp/claude/`

Instead of disabling sandbox for temporary files, use the **designated temporary directory**:

```bash
# ✅ Good: Use /tmp/claude/ (allowed by sandbox)
cp output.txt /tmp/claude/backup.txt

# ❌ Bad: Use home directory (requires sandbox disable)
cp output.txt ~/.backup/backup.txt
```

The `TMPDIR` environment variable is automatically set to `/tmp/claude` in sandbox mode.

---

## Advanced Configuration

### Adding Paths to Allowlist

If you frequently need write access to specific paths:

1. Use `/sandbox` command in Claude Code
2. Add the path to the `allowOnly` list under `filesystem.write`
3. Restart Claude Code session

### Adding Network Hosts

To allow network access to additional hosts:

1. Use `/sandbox` command
2. Add hosts to the `allowedHosts` list under `network`
3. Commonly needed hosts:
   - `pypi.org` (Python packages)
   - `registry.npmjs.org` (npm packages)
   - `api.github.com` (GitHub API)

---

## Sandbox Operation Examples

| Operation Type | Sandbox Status | Notes |
|-----------|---------------|---------|
| Read project files | ✅ Enabled | No restrictions on reading |
| Write to project directory | ✅ Enabled | Current directory is allowed |
| Write to `/tmp/claude/` | ✅ Enabled | Designated temporary directory |
| Git operations (in project) | ✅ Enabled | Works within allowed paths |
| Network to GitHub | ✅ Enabled | Pre-approved in allowlist |
| Install system packages | ⚠️ Requires Permission | Auto-prompt when needed |
| Access home directory files | ⚠️ Requires Permission | Auto-prompt when needed |

---

## Key Takeaways

1. **Sandbox is ENABLED** on this project for enhanced security
2. **Most operations work fine** with sandbox enabled by default
3. **Auto-allow feature** will prompt when operations need elevated access
4. **Use `/sandbox`** to manage permanent exceptions and view restrictions
5. **Prefer `/tmp/claude/`** for temporary files instead of home directory
6. **Never commit credentials** or sensitive files to the repository

---

## Resources

- **Sandbox Configuration**: Use `/sandbox` command in Claude Code
- **Temporary Files**: Use `/tmp/claude/` directory
- **Feedback**: Report issues at https://github.com/anthropics/claude-code/issues
- **Help**: Use `/help` command for assistance

---

**Last Updated**: 2026-01-31
**Project**: MY-FIRST-AGENT
**Sandbox Status**: ✅ Enabled with Auto-Allow
