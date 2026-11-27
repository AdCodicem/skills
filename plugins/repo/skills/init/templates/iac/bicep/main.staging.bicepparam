using 'main.bicep'

param environmentName = 'staging'
param tags = {
  project: '{{project}}'
  environment: 'staging'
  repository: '{{owner}}/{{repo}}'
}
