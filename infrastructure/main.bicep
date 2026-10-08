// PRIVATE foundation proposal. Compile only until identities, network, costs and changes are approved.
targetScope = 'resourceGroup'

param location string = resourceGroup().location
@minLength(3)
@maxLength(12)
param prefix string = 'sqlintel'
@description('Object ID of the explicitly approved Entra SQL administrator group.')
param sqlAdminObjectId string
param sqlAdminDisplayName string
param existingOpenaiName string
param existingOpenaiResourceGroup string
param existingOpenaiSubscriptionId string = subscription().subscriptionId
@description('Explicit migration-host subnet only; empty means no migration access to private endpoints.')
param migrationSubnetPrefix string = ''

var suffix = uniqueString(resourceGroup().id)
var tags = { project: 'sql-intelligence-agent', data: 'synthetic', milestone: 'M2' }

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-runtime'
  location: location
  tags: tags
}

resource frontendIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-frontend'
  location: location
  tags: tags
}

// Private endpoint NSG rules exclude the browser/VPN subnet from SQL and token storage.
resource endpointSecurity 'Microsoft.Network/networkSecurityGroups@2023-09-01' = {
  name: '${prefix}-endpoint-nsg'
  location: location
  tags: tags
  properties: {
    securityRules: concat([
      {
        name: 'AllowApplicationSubnet'
        properties: {
          priority: 100
          access: 'Allow'
          direction: 'Inbound'
          protocol: 'Tcp'
          sourceAddressPrefix: '10.48.0.0/23'
          sourcePortRange: '*'
          destinationAddressPrefix: '10.48.2.0/24'
          destinationPortRanges: ['443', '1433']
        }
      }
      {
        name: 'DenyOtherInbound'
        properties: {
          priority: 4000
          access: 'Deny'
          direction: 'Inbound'
          protocol: '*'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ], empty(migrationSubnetPrefix) ? [] : [
      {
        name: 'AllowApprovedMigrationSubnet'
        properties: {
          priority: 110
          access: 'Allow'
          direction: 'Inbound'
          protocol: 'Tcp'
          sourceAddressPrefix: migrationSubnetPrefix
          sourcePortRange: '*'
          destinationAddressPrefix: '10.48.2.0/24'
          destinationPortRange: '1433'
        }
      }
    ])
  }
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
          privateEndpointNetworkPolicies: 'Enabled'
          networkSecurityGroup: { id: endpointSecurity.id }
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

resource environment 'Microsoft.App/managedEnvironments@2025-07-01' = {
  name: '${prefix}-environment'
  location: location
  tags: tags
  properties: {
    publicNetworkAccess: 'Disabled'
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
resource sqlConnectionPolicy 'Microsoft.Sql/servers/connectionPolicies@2023-08-01' = {
  parent: sql
  name: 'default'
  properties: { connectionType: 'Proxy' }
}

// REUSE ONLY. No new OpenAI account, deployment, role grant or existing-account network change.
resource openai 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: existingOpenaiName
  scope: resourceGroup(existingOpenaiSubscriptionId, existingOpenaiResourceGroup)
}

resource tokenStorage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: '${prefix}auth${take(suffix, 8)}'
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    publicNetworkAccess: 'Disabled'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    networkAcls: { defaultAction: 'Deny', bypass: 'None' }
  }
}
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: tokenStorage
  name: 'default'
  properties: {}
}
resource tokenContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'auth-tokens'
  properties: { publicAccess: 'None' }
}

resource registry 'Microsoft.ContainerRegistry/registries@2025-04-01' = {
  name: '${prefix}images${take(suffix, 6)}'
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false, anonymousPullEnabled: false }
}

var privateServices = [
  { name: 'sql', id: sql.id, group: 'sqlServer', zone: 'privatelink${az.environment().suffixes.sqlServerHostname}' }
  { name: 'openai', id: openai.id, group: 'account', zone: 'privatelink.openai.azure.com' }
  { name: 'authstore', id: tokenStorage.id, group: 'blob', zone: 'privatelink.blob.${az.environment().suffixes.storage}' }
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

output environmentName string = environment.name
output sqlServerFqdn string = sql.properties.fullyQualifiedDomainName
output runtimeIdentityName string = identity.name
output runtimePrincipalId string = identity.properties.principalId
output runtimeClientId string = identity.properties.clientId
output openaiEndpoint string = openai.properties.endpoint
output insightsResourceId string = insights.id
output frontendIdentityName string = frontendIdentity.name
output frontendPrincipalId string = frontendIdentity.properties.principalId
output registryServer string = registry.properties.loginServer
output tokenStorageName string = tokenStorage.name
