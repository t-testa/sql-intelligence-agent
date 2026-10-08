// Subscription-level what-if can review a new group without creating it first.
targetScope = 'subscription'

param location string = 'canadaeast'
param labResourceGroupName string = 'sqlintel-lab'
param prefix string = 'sqlintel'
param sqlAdminObjectId string
param sqlAdminDisplayName string
param entraTenantId string
param existingOpenaiName string
param existingOpenaiResourceGroup string
param createValidationDatabase bool = true
param migrationSubnetPrefix string = ''
param includeOperatorSubnets bool = false
@description('Cost exception: VM, disk, outbound IP and free Bastion Developer. Requires explicit approval.')
param includeOperatorHost bool = false
@secure()
param operatorAdministratorPassword string = ''

resource lab 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: labResourceGroupName
  location: location
  tags: { project: 'sql-intelligence-agent', purpose: 'temporary-private-lab' }
}

module foundation './main.bicep' = {
  name: 'foundation'
  scope: lab
  params: {
    location: location
    prefix: prefix
    sqlAdminObjectId: sqlAdminObjectId
    sqlAdminDisplayName: sqlAdminDisplayName
    sqlAdminPrincipalType: 'User'
    entraTenantId: entraTenantId
    existingOpenaiName: existingOpenaiName
    existingOpenaiResourceGroup: existingOpenaiResourceGroup
    createValidationDatabase: createValidationDatabase
    migrationSubnetPrefix: migrationSubnetPrefix
    includeOperatorSubnets: includeOperatorSubnets || includeOperatorHost
  }
}

module operator './operator.bicep' = if (includeOperatorHost) {
  name: 'private-operator'
  scope: lab
  params: {
    location: location
    prefix: prefix
    administratorPassword: operatorAdministratorPassword
  }
  dependsOn: [foundation]
}
