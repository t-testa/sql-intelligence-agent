// M2 foundation only. Review costs, tenant and region, then obtain explicit approval before deployment.
targetScope = 'resourceGroup'

param location string = resourceGroup().location
@minLength(3)
@maxLength(12)
param prefix string = 'sqlintel'
@description('Object ID of the explicitly approved Entra SQL administrator group.')
param sqlAdminObjectId string
param sqlAdminDisplayName string
param deployKeyVault bool = false

var suffix = uniqueString(resourceGroup().id)
var tags = { project: 'sql-intelligence-agent', data: 'synthetic', milestone: 'M2' }

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-runtime'
  location: location
  tags: tags
}

resource network 'Microsoft.Network/virtualNetworks@2023-09-01' = {
  name: '${prefix}-vnet'
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: ['10.48.0.0/16'] }
    subnets: [
      {
        name: 'container-apps'
        properties: {
          addressPrefix: '10.48.0.0/23'
          delegations: [{ name: 'apps', properties: { serviceName: 'Microsoft.App/environments' } }]
        }
      }
      {
        name: 'private-endpoints'
        properties: {
          addressPrefix: '10.48.2.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    workspaceCapping: { dailyQuotaGb: 1 }
  }
}

resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${prefix}-insights'
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id
    RetentionInDays: 30
    IngestionMode: 'LogAnalytics'
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${prefix}-environment'
  location: location
  tags: tags
  properties: {
    vnetConfiguration: {
      infrastructureSubnetId: '${network.id}/subnets/container-apps'
      internal: true
    }
    workloadProfiles: [{ name: 'Consumption', workloadProfileType: 'Consumption' }]
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: workspace.properties.customerId
        sharedKey: workspace.listKeys().primarySharedKey
      }
    }
  }
}

resource sql 'Microsoft.Sql/servers@2023-08-01' = {
  name: '${prefix}-${suffix}'
  location: location
  tags: tags
  properties: {
    version: '12.0'
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Disabled'
    administrators: {
      administratorType: 'ActiveDirectory'
      principalType: 'Group'
      login: sqlAdminDisplayName
      sid: sqlAdminObjectId
      tenantId: tenant().tenantId
      azureADOnlyAuthentication: true
    }
  }
}

resource database 'Microsoft.Sql/servers/databases@2023-08-01' = {
  parent: sql
  name: 'SQLIntelligence'
  location: location
  tags: tags
  sku: { name: 'Basic', tier: 'Basic', capacity: 5 }
  properties: { maxSizeBytes: 2147483648 }
}

resource openai 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: '${prefix}-ai-${suffix}'
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: '${prefix}-ai-${suffix}'
    publicNetworkAccess: 'Disabled'
    disableLocalAuth: true
    networkAcls: { defaultAction: 'Deny', ipRules: [], virtualNetworkRules: [] }
  }
}

// Narrow resource-scoped inference permission; no Contributor/Owner grants.
resource openaiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openai.id, identity.id, 'openai-user')
  scope: openai
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

var privateServices = [
  { name: 'sql', id: sql.id, group: 'sqlServer', zone: 'privatelink${az.environment().suffixes.sqlServerHostname}' }
  { name: 'openai', id: openai.id, group: 'account', zone: 'privatelink.openai.azure.com' }
]
resource zones 'Microsoft.Network/privateDnsZones@2020-06-01' = [for service in privateServices: {
  name: service.zone
  location: 'global'
  tags: tags
}]
resource links 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = [for (service, i) in privateServices: {
  parent: zones[i]
  name: '${prefix}-vnet-link'
  location: 'global'
  properties: { registrationEnabled: false, virtualNetwork: { id: network.id } }
}]
resource endpoints 'Microsoft.Network/privateEndpoints@2023-09-01' = [for service in privateServices: {
  name: '${prefix}-${service.name}-pe'
  location: location
  tags: tags
  properties: {
    subnet: { id: '${network.id}/subnets/private-endpoints' }
    privateLinkServiceConnections: [{
      name: service.name
      properties: { privateLinkServiceId: service.id, groupIds: [service.group] }
    }]
  }
}]
resource zoneGroups 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-09-01' = [for (service, i) in privateServices: {
  parent: endpoints[i]
  name: 'default'
  properties: { privateDnsZoneConfigs: [{ name: service.name, properties: { privateDnsZoneId: zones[i].id } }] }
}]

// Optional future secret store; M1/M2 runtime itself uses managed identities.
resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = if (deployKeyVault) {
  name: '${prefix}-kv-${suffix}'
  location: location
  tags: tags
  properties: {
    tenantId: tenant().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enablePurgeProtection: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Disabled'
    networkAcls: { defaultAction: 'Deny', bypass: 'None' }
    accessPolicies: []
  }
}

output environmentName string = environment.name
output sqlServerFqdn string = sql.properties.fullyQualifiedDomainName
output runtimeIdentityName string = identity.name
output runtimePrincipalId string = identity.properties.principalId
output runtimeClientId string = identity.properties.clientId
output openaiEndpoint string = openai.properties.endpoint
output insightsResourceId string = insights.id
