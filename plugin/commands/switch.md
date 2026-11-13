---
description: Change the active Claude account (with a number, to that one; without it, to the one with the most room)
argument-hint: "[number]"
allowed-tools: Bash(usage switch:*)
---

!`usage switch $ARGUMENTS`

Say which account is now active, in the language of that output. Point out that this session keeps using the previous account: to carry on this conversation with the new one, exit and run `claude --continue`. Do not run anything else.
