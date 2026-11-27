# renovate

Runs [Renovate](https://docs.renovatebot.com/) hourly over every repository the
`{{renovate-bot}}` GitHub App is installed on. Each repository opts in with a
`renovate.json` that extends [`{{owner}}/renovate-config`](https://github.com/{{owner}}/renovate-config).

## Setup

1. Create the GitHub App (Settings, Developer settings, GitHub Apps): no
   webhook; repository permissions Contents, Pull requests, Issues, Workflows,
   Checks and Commit statuses read and write, Dependabot alerts and
   Administration read, Metadata read; installable on this account only.
   Generate a private key.
2. Install it on this repository and on every repository Renovate manages.
3. Create the `renovate` environment here, limited to `main`, with the variable
   `RENOVATE_APP_CLIENT_ID` and the secret `RENOVATE_APP_PRIVATE_KEY`.
4. Fill `config.js` (`gitAuthor` takes the App's bot user ID, from
   `https://api.github.com/users/{{renovate-bot}}%5Bbot%5D`).
5. Dispatch the workflow with `log_level: debug` once and read its log.
