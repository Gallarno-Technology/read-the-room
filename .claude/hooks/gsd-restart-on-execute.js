#!/usr/bin/env node
// PostToolUse hook: runs 'make restart' when a gsd-executor completes
//
// Detects executor completion by checking if the Agent tool's response
// contains "PLAN COMPLETE" — the standard completion marker used by
// gsd-executor (both phase and quick-task executors).
//
// Fires after execute-phase and gsd:quick executions automatically.

const { execFileSync } = require('child_process');
const path = require('path');

let input = '';
const stdinTimeout = setTimeout(() => process.exit(0), 15000);
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  clearTimeout(stdinTimeout);
  try {
    const data = JSON.parse(input);

    // Only care about Agent tool completions
    if (data.tool_name !== 'Agent' && data.tool_name !== 'Task') {
      process.exit(0);
    }

    // Check for executor completion signal in the tool response
    const resultStr = JSON.stringify(data.tool_response || '');
    if (!resultStr.includes('PLAN COMPLETE')) {
      process.exit(0);
    }

    // Run make restart in the project directory
    const cwd = data.cwd || process.cwd();
    try {
      execFileSync('make', ['restart'], {
        cwd,
        stdio: 'ignore',
        timeout: 120000
      });
    } catch (e) {
      // Don't block on make restart failures — docker may not be running
    }

    process.exit(0);
  } catch (e) {
    // Silent fail — never block tool execution
    process.exit(0);
  }
});
