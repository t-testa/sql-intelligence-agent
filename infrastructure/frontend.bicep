// Preparation only. Must target a verified INTERNAL environment with public networking disabled.
// No role assignments or Entra grants are made here. Private registry permissions are separate.
targetScope = 'resourceGroup'
param location string = resourceGroup().location
param environmentName string
param frontendIdentityName string
param image string
param registryServer string
param apiFqdn string
param apiClientId string
param frontendClientId string
param approvedUserObjectId string
@description('Same explicitly approved tenant used by the independently validating API.')
param entraTenantId string
@secure()
param frontendClientSecret string
@secure()
@description('HTTPS SAS URL scoped to the private auth-tokens container; read/write/delete only.')
param tokenStoreSasUrl string
param appName string = 'sql-intelligence-web'
@description('Keep ingress off on first deployment. Enable only after reading back owner-only Easy Auth.')
param enablePrivateIngress bool = false

resource environment 'Microsoft.App/managedEnvironments@2025-07-01' existing = { name: environmentName }
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = { name: frontendIdentityName }
resource app 'Microsoft.App/containerApps@2025-07-01' = {
  name: appName
  location: location
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  properties: {
    managedEnvironmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [{ server: registryServer, identity: identity.id }]
      // external:true permits the PRIVATE VNet browser route outside this internal ACA environment.
      // Never use this template with an external environment; private_preflight rejects that state.
      ingress: enablePrivateIngress ? {
        external: true
        targetPort: 8501
        allowInsecure: false
        transport: 'http'
      } : null
      secrets: [
        { name: 'entra-client-secret', value: frontendClientSecret }
        { name: 'token-store-sas', value: tokenStoreSasUrl }
      ]
    }
    template: {
      containers: [{
        name: 'frontend'
        image: image
        command: ['python', '-m', 'streamlit', 'run', 'frontend/app.py']
        args: ['--server.address=0.0.0.0', '--server.headless=true', '--browser.gatherUsageStats=false']
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
          { name: 'APP_ENV', value: 'cloud' }
          { name: 'API_URL', value: 'https://${apiFqdn}' }
        ]
        probes: [{ type: 'Liveness', tcpSocket: { port: 8501 }, initialDelaySeconds: 30 }]
      }]
      scale: { minReplicas: 0, maxReplicas: 1 }
    }
  }
}

resource authentication 'Microsoft.App/containerApps/authConfigs@2025-07-01' = {
  parent: app
  name: 'current'
  properties: {
    platform: { enabled: true }
    globalValidation: {
      unauthenticatedClientAction: 'RedirectToLoginPage'
      redirectToProvider: 'azureActiveDirectory'
      excludedPaths: []
    }
    httpSettings: { requireHttps: true }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: {
          clientId: frontendClientId
          clientSecretSettingName: 'entra-client-secret'
          openIdIssuer: '${az.environment().authentication.loginEndpoint}${entraTenantId}/v2.0'
        }
        login: { loginParameters: ['scope=openid profile offline_access api://${apiClientId}/access_as_user'] }
        validation: {
          allowedAudiences: [frontendClientId]
          defaultAuthorizationPolicy: { allowedPrincipals: { identities: [approvedUserObjectId] } }
        }
      }
    }
    login: {
      allowedExternalRedirectUrls: []
      cookieExpiration: { convention: 'FixedTime', timeToExpiration: '01:00:00' }
      nonce: { validateNonce: true, nonceExpirationInterval: '00:05:00' }
      tokenStore: {
        enabled: true
        tokenRefreshExtensionHours: 0
        azureBlobStorage: { sasUrlSettingName: 'token-store-sas' }
      }
    }
  }
}

// Keep the API access switch OFF until this resource is deployed and private auth acceptance passes.
output privateFrontendFqdn string = enablePrivateIngress ? app.properties.configuration.ingress.fqdn : ''
