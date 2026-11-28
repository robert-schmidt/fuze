# FAQ

This page answers common questions in a sentence or two each, with links to the full explanation.

**What does it cost?**
Nothing. The signal is free and public, the agent is open source, and FUZE takes no fee or share. Exchange fees and
funding on your own trades are yours.

**Is it real money today?**
The account trades practice money. The agent's default is a simulated account with no money. Mainnet (real money)
stays locked on each machine until that machine has passed the testnet rehearsal. See [The three modes](modes/README.md).

**Will I make money?**
Nobody can say, and we make no claim. Our own tests say the short-term trades lose a little after costs and only the
slow trend made money in history. See [What the tests found](../research/findings.md).

**Does FUZE see my account, balance or keys?**
No. The agent sends nothing to our server. Your key stays on your machine and orders are signed there.

**Why only Bitcoin and Ether?**
They are what the account trades. The protocol and the agent accept only those two coins.

**Why only Lighter?**
Lighter charges no trading fee on regular orders on a standard account, and costs decide whether short-term trading
loses. See [Why costs decide](../research/costs.md). Lighter describes itself as "a zero-knowledge rollup on top of
Ethereum" and says "All operations including matching and liquidations are proven cryptographically and verified
publicly on Ethereum" (https://lighter.xyz); its sequencer first gives "soft finality", before the proofs land
(https://docs.lighter.xyz/about-lighter/technical-architecture-lighter-core.md). Lighter's terms exclude residents of
some countries; check yours.

**Why does my position differ from the account's?**
Your fills come at a different moment and price, your caps can cut it, and changes under the larger of $10 and 2% of
your balance are skipped: a very small size can mean nothing is held. `fuze status` shows per coin what the signal asks
for and what you hold. See [How following works](following.md).

**I lowered a limit. When does my position shrink?**
Within seconds, if the agent is running: it notices the changed settings on its next step and resizes, on the same
signal revision. A raise you confirmed with `RAISE` applies the same way, without a restart.

**Can I follow only the slow trend?**
Not today. The signal is the whole account.

**What happens if my computer sleeps or the agent stops?**
Positions stay as they are. On Lighter the short-term part keeps its take profit and stop loss on the exchange, and
the rest of each position keeps its [emergency stop](following.md#5-the-emergency-stop), about 20% from the price the
agent last saw. When the agent starts again it reads the account and catches up with the latest signal.

**What happens if the FUZE server goes down?**
After 60 seconds without a valid message the agent holds and opens nothing new. Set `stale_flat_min` to close everything
after a while instead. See [Freshness and states](../signal/states.md).

**Can my AI tool raise my limits or switch to real money?**
Not through the MCP server. With shell access it could do anything you can, typed confirmations included, and read your
key: the confirmations are not a barrier against a program running as you. Do not give an AI tool unattended shell
access on a machine that holds a mainnet key. See [Security model](security.md) for why the exchange-side setup is what
protects the money.

**Where do I install it from?**
Only from its repository, https://github.com/robert-schmidt/fuze: `uv tool install` or `pipx install` with that address
in the command, or a clone. See [Install](start/install.md).

**Can I run it on a server?**
Yes, on Linux, in a terminal or a service you control. Set `FUZE_NO_KEYRING=1` if there is no keyring. Typing the key and
the confirmations still need a terminal.

**How do I stop everything right now?**
`fuze flatten` (or ask your AI tool to flatten). Then stop the agent once it is flat.

**Is this financial advice?**
No. It mirrors one account. Read [Risks, plainly](../risks.md).
