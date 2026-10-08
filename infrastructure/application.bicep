// M2 second stage. Requires approved identity bootstrap, image and model deployment.
targetScope = 'resourceGroup'
param location string = resourceGroup().location
param environmentName string
param runtimeIdentityName string
param runtimeClientId string
param image string
param sqlServerFqdn string
param openaiEndpoint string
param openaiDeploymentName string
param apiAudience string
param frontendClientId string
@description('Explicitly approved Entra tenant; never inferred from the deployment operator.')
param entraTenantId string
@minLength(1)
@maxLength(1)
param allowedUserObjectIds array
@description('Fail closed until private cloud acceptance tests are explicitly enabled.')
param applicationAccessEnabled bool = false
param registryServer string
param appName string = 'sql-intelligence-api'

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' existing = { name: environmentName }
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = { name: runtimeIdentityName }

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  properties: {
    managedEnvironmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [{ server: registryServer, identity: identity.id }]
      ingress: { external: false, targetPort: 8000, allowInsecure: false, transport: 'http' }
    }
    template: {
      containers: [{
        name: 'api'
        image: image
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
          { name: 'APP_ENV', value: 'cloud' }
          { name: 'AUTH_MODE', value: 'entra' }
          { name: 'AZURE_CLIENT_ID', value: runtimeClientId }
          { name: 'ENTRA_TENANT_ID', value: entraTenantId }
          { name: 'ENTRA_AUDIENCE', value: apiAudience }
          { name: 'ENTRA_FRONTEND_CLIENT_ID', value: frontendClientId }
          { name: 'ENTRA_ALLOWED_OBJECT_IDS', value: string(allowedUserObjectIds) }
          { name: 'APPLICATION_ACCESS_ENABLED', value: string(applicationAccessEnabled) }
          { name: 'SQL_HOST', value: sqlServerFqdn }
          { name: 'SQL_PORT', value: '1433' }
          { name: 'SQL_DATABASE', value: 'SQLIntelligence' }
          { name: 'SQL_EXPECTED_PRINCIPAL', value: 'sql_runtime' }
          { name: 'SQL_MANAGED_IDENTITY', value: 'true' }
          { name: 'SQL_TRUST_CERTIFICATE', value: 'false' }
          { name: 'AGENT_MODE', value: 'azure' }
          { name: 'AZURE_OPENAI_ENDPOINT', value: openaiEndpoint }
          { name: 'AZURE_OPENAI_DEPLOYMENT', value: openaiDeploymentName }
          { name: 'AZURE_OPENAI_MAX_OUTPUT_TOKENS', value: '1000' }
          { name: 'AZURE_OPENAI_REQUESTS_PER_MINUTE', value: '6' }
          { name: 'AZURE_OPENAI_TOKENS_PER_MINUTE', value: '18000' }
          { name: 'AZURE_OPENAI_DAILY_REQUEST_LIMIT', value: '100' }
        ]
        probes: [{ type: 'Liveness', httpGet: { path: '/health', port: 8000 }, initialDelaySeconds: 30 }]
      }]
      scale: { minReplicas: 0, maxReplicas: 1 }
    }
  }
}
output privateApiFqdn string = app.properties.configuration.ingress.fqdn
