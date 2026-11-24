# Work process

This summary reconstructs the project phases from repository history and GitHub issues. The dates below are commit periods.

| Period | Work in the repository | Related issues |
| --- | --- | --- |
| September–October | Set up the Python package with uv, added the packet API, and drafted the protocol outline. See commits `a215538`, `23690eb`, and `d2b58dd`. | [Protocol design #10](https://github.com/Gamesandwebsite-developer/IDATA2304-Smart-House-project/issues/10) |
| Early November | Added discovery and sensor-update commands, the TCP client, and role checks. Expanded the protocol draft. See `39176a9`, `01ace3c`, `2480cb1`, and `cc95647`. | [Protocol implementation #8](https://github.com/Gamesandwebsite-developer/IDATA2304-Smart-House-project/issues/8) · [Protocol MVP #17](https://github.com/Gamesandwebsite-developer/IDATA2304-Smart-House-project/issues/17) |
| Late November | Moved device rules into JSON, added hierarchical addressing, built the CLI, and added anomaly limits. The final implementation pass connects the simulated nodes over TCP and exercises the full path from the menu. See `1bfdf16`, `293a2e1`, `b9b3e1d`, and `ef51a3c`. | [Simulation #19](https://github.com/Gamesandwebsite-developer/IDATA2304-Smart-House-project/issues/19) · [Anomaly detection #28](https://github.com/Gamesandwebsite-developer/IDATA2304-Smart-House-project/issues/28) · [Control panel #30](https://github.com/Gamesandwebsite-developer/IDATA2304-Smart-House-project/issues/30) |

The commits above show Jiaqi contributing the package setup and packet API, Gamesandwebsite-developer contributing TCP framing, server routing, access control, and device validation, and Kenneth Solhaug contributing the protocol description and CLI. The Git history records individual commits. The team's original sprint plans, issue assignments, and retrospectives still need to be linked or filled in from team records.

## Results and future work

The original tests covered in-process routing and anomaly thresholds. A TCP integration test now checks that an actuator change made through one panel is visible to a second and that the server reports an unavailable node. For a deployment beyond the trusted demo network, TLS and automatic node reconnection would be useful next steps.

The sensor-node and control-panel changes in the final implementation pass were developed with Codex assistance.

## Inspera hand-in

- Submit the repository URL and the protocol and work-process links. Include the team's sprint records.
- Supply the candidate-number to GitHub-username mapping from the team.
- Record the English presentation with each team member visible and presenting. Demonstrate node discovery, a sensor warning, an actuator write and status read, and the protocol on both TCP connections. [Presentation issue #13](https://github.com/Gamesandwebsite-developer/IDATA2304-Smart-House-project/issues/13)
