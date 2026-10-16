# macOS context

My personal MacBook currently handles both personal use and professional work.
Treat it as an active everyday machine. The shared instructions describe the
boundaries around accounts, unrelated processes, and private data.

I use React Native and sometimes need the iOS simulator. Use macOS when the task
needs Xcode, the simulator, signing, or another Apple-specific capability. Preserve
existing simulator sessions and development state unless the task requires changing
them. Don't change signing identities or provisioning configuration incidentally.

Storage is a recurring constraint, especially with worktrees and build artifacts.
Inspect available space before creating substantial duplicate environments. Explain
what can be reclaimed before removing anything outside the task's temporary files.

My longer-term goal is to move general development to Linux and reserve the MacBook
primarily for iOS development. This is a direction, not today's operating restriction.
Don't assume another computer is reachable or move work there without a configured
and authorized workflow.

## Agent workloads

Keep the desktop responsive when several agents run. Lightweight commands and
model conversations can run concurrently. Stagger full builds, broad test suites,
and browser or simulator verification. Before starting heavy local verification,
check for other builds or test suites and wait for capacity when they are busy.
Never stop another task's processes to make room.

Default to at most two workers for local test runners that support a worker limit,
using their supported command options. An explicit task requirement can override
this default. Keep useful dependency and build caches for repeated verification.
