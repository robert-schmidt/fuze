# Freshness and states

This page explains how long a message stays valid, how often new ones come, and what the three states (live, flat,
offline) ask a follower to do.

## Freshness

- A message is valid for **60 seconds** after it was signed (`expires` = `ts` + 60).
- A **heartbeat** (a new signed message with the same `rev`) comes every **5 seconds**, so a valid message is always
  available while the signer runs.
- A follower that has seen no valid message for 60 seconds treats the signal as offline.

## The three states

| State | What it means | What a follower does |
|---|---|---|
| `live` | We hold the targets in the message | Follow them |
| `flat` | We closed everything and are staying out | Close everything and stay out |
| `offline` | We have no fresh reading of the account | Hold what you have, open nothing new |

## Why "offline" means hold, not close

If our side stops, closing everything at once would turn a technical problem into a market order at a bad moment, for
every follower at the same time. Holding is the calmer default, and each short-term part keeps its take profit and stop
loss on the exchange. A follower who prefers to close can set a time limit: the agent's `stale_flat_min` closes
everything after that many minutes without a live signal (see [Limits and safety switches](../agent/limits.md)).

## Sequence, revision and timestamp

| Number | Rises when | Use it for |
|---|---|---|
| `seq` | Every signed message | Spotting gaps. It may restart if the signer is rebuilt |
| `rev` | The position, its bracket or the state changes | Deciding when to act |
| `ts` | Every message | The replay guard: accept only a message newer than the newest accepted |

A replayed message is at most 60 seconds old and never newer than one already accepted, so it cannot move a follower
back to an earlier position.
