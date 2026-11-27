using 'main.bicep'

param environmentName = 'production'
param tags = {
  project: '{{project}}'
  environment: 'production'
  repository: '{{owner}}/{{repo}}'
}
