"""
Observer Bot — read-only watcher for ChatGPT-authored code.

Polls the repo for file changes, runs lint pre-filters, then sends diffs
through Haiku 4.5 (and escalates CRITICAL findings to Sonnet 4.5). Emits
findings to terminal, log file, Telegram, and optional GitHub PR — but
NEVER edits source files. Hands-off by design.
"""
