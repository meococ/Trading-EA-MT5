# Security Policy

Trading-EA-MT5 is an active pre-release research project. Security reports that protect contributors, local MT5 installations, credentials, broker data, and research integrity are welcome.

## Supported version

Only the current `main` branch is reviewed. There is no production or live-trading release at this time.

## Reporting a vulnerability

Use GitHub private vulnerability reporting for this repository when it is available. If that option is not visible, open a minimal public issue asking the maintainer for a private contact channel, but do **not** include the vulnerability details, proof of concept, credentials, account identifiers, or personal data in that issue.

Please include privately:

- the affected path and revision;
- impact and realistic attack conditions;
- minimal reproduction steps;
- any safe mitigation you have tested.

## Sensitive-data exposure

If a credential, token, broker account identifier, personal trade export, or machine-local path is found:

1. do not copy it into an issue or pull request;
2. notify the maintainer privately;
3. rotate or revoke affected credentials immediately;
4. treat Git-history cleanup as a separate remediation step.

Deleting a file from the latest branch does not erase it from earlier commits or existing clones.

## Out of scope

- requests to prove a strategy is profitable;
- losses caused by live trading or broker behavior;
- findings that require publishing someone else's credentials or financial data;
- social-engineering attempts against maintainers or contributors.

## Safe harbor

Good-faith research that avoids privacy violations, service disruption, financial activity, and unauthorized access is appreciated. Please give the maintainer reasonable time to investigate before public disclosure.

