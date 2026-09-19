# bash step.sh <log-name> '<commands>': run a runbook step with the rehearsal variables,
# echo the commands, time them, and keep the output in demo-logs/rehearsal2/b7/<log-name>.txt
cd /Users/apple/orca/projects/trace-pay/.claude/worktrees/agent-adafdc763e2a934c0
. /private/tmp/claude-501/-Users-apple-orca-workspaces-trace-pay-pelican/81951f95-6768-4335-9ebf-6930a2d5a39b/scratchpad/b8b7/vars.sh
[ -f /private/tmp/claude-501/-Users-apple-orca-workspaces-trace-pay-pelican/81951f95-6768-4335-9ebf-6930a2d5a39b/scratchpad/b8b7/p.sh ] && . /private/tmp/claude-501/-Users-apple-orca-workspaces-trace-pay-pelican/81951f95-6768-4335-9ebf-6930a2d5a39b/scratchpad/b8b7/p.sh
now() { perl -MTime::HiRes=time -e 'printf "%.2f", time'; }
{
  echo "\$ $2"
  start=$(now)
  eval "$2"
  echo "[exit $?] [$(perl -e "printf '%.2f', $(now) - $start") s] [$(date '+%H:%M:%S')]"
} 2>&1 | tee -a "$LOG/$1.txt"
