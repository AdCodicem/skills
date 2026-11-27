// Self-hosted Renovate for {{owner}}'s repositories (references/renovate.md).
// The GitHub App's installations decide which repositories it can see;
// requireConfig leaves alone any repository without a renovate.json.
module.exports = {
  platform: "github",
  autodiscover: true,
  autodiscoverFilter: ["{{owner}}/*"],
  onboarding: false,
  requireConfig: "required",
  // The App's bot identity, so commits show as the App: {{renovate-bot}}[bot].
  gitAuthor: "{{renovate-bot}}[bot] <{{renovate-bot-id}}+{{renovate-bot}}[bot]@users.noreply.github.com>",
  username: "{{renovate-bot}}[bot]",
  repositoryCache: "enabled",
};
