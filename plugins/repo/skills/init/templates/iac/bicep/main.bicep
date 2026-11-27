// Infrastructure of {{project}}: one resource group per environment, deployed as a
// deployment stack by .github/workflows/deploy.yml. Values per environment live in
// main.<environment>.bicepparam, never in this file.
targetScope = 'resourceGroup'

@description('Short name of the environment: staging or production.')
@allowed([
  'staging'
  'production'
])
param environmentName string

@description('Azure region of every resource. Defaults to the resource group\'s.')
param location string = resourceGroup().location

@description('Tags applied to every resource.')
param tags object = {}

var suffix = '{{project}}-${environmentName}'

// Azure Verified Modules come from the public registry, pinned to an exact version.
// Renovate proposes newer versions (see renovate-rules.json); the linter warns when
// one is old (use-recent-module-versions).
module logs 'br/public:avm/res/operational-insights/workspace:0.16.2' = {
  params: {
    name: 'log-${suffix}'
    location: location
    tags: tags
  }
}

module identity 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = {
  params: {
    name: 'id-${suffix}'
    location: location
    tags: tags
  }
}

@description('Resource ID of the Log Analytics workspace.')
output logAnalyticsWorkspaceId string = logs.outputs.resourceId

@description('Client ID of the workload identity.')
output identityClientId string = identity.outputs.clientId
