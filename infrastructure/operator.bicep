// Optional cost exception: deploy only after approval of the private browser route.
// Bastion Developer is free; VM, disk and explicit outbound IP are billable.
targetScope = 'resourceGroup'
param location string = resourceGroup().location
param prefix string = 'sqlintel'
param vnetName string = '${prefix}-vnet'
@allowed(['operator-browser', 'operator-maintenance'])
@description('Maintenance is temporary. Stop/deallocate before changing the NIC subnet.')
param operatorSubnetName string = 'operator-browser'
param administratorName string = 'laboperator'
@secure()
param administratorPassword string
@description('Pin the reviewed Windows Desktop Experience image; do not silently change editions.')
param imageVersion string = '26100.33438.260905'

var tags = { project: 'sql-intelligence-agent', purpose: 'temporary-private-lab' }
resource vnet 'Microsoft.Network/virtualNetworks@2023-09-01' existing = { name: vnetName }
resource outbound 'Microsoft.Network/publicIPAddresses@2023-09-01' = {
  name: '${prefix}-operator-egress'
  location: location
  tags: tags
  sku: { name: 'Standard' }
  properties: { publicIPAllocationMethod: 'Static', publicIPAddressVersion: 'IPv4' }
}
resource nsg 'Microsoft.Network/networkSecurityGroups@2023-09-01' = {
  name: '${prefix}-operator-nsg'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'PrivateRdpOnly'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '3389'
        }
      }
      {
        name: 'DenyAllOtherInbound'
        properties: {
          priority: 4096
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ]
  }
}
resource nic 'Microsoft.Network/networkInterfaces@2023-09-01' = {
  name: '${prefix}-operator-nic'
  location: location
  tags: tags
  properties: {
    enableIPForwarding: false
    networkSecurityGroup: { id: nsg.id }
    ipConfigurations: [{
      name: 'primary'
      properties: {
        privateIPAllocationMethod: 'Dynamic'
        subnet: { id: '${vnet.id}/subnets/${operatorSubnetName}' }
        publicIPAddress: { id: outbound.id }
      }
    }]
  }
}
resource vm 'Microsoft.Compute/virtualMachines@2024-11-01' = {
  name: '${prefix}-operator'
  location: location
  tags: tags
  properties: {
    hardwareProfile: { vmSize: 'Standard_D2as_v4' }
    storageProfile: {
      imageReference: {
        publisher: 'MicrosoftWindowsServer'
        offer: 'WindowsServer'
        sku: '2025-datacenter-azure-edition'
        version: imageVersion
      }
      osDisk: {
        name: '${prefix}-operator-os'
        createOption: 'FromImage'
        diskSizeGB: 128
        caching: 'ReadWrite'
        managedDisk: { storageAccountType: 'StandardSSD_LRS' }
        deleteOption: 'Delete'
      }
    }
    osProfile: {
      computerName: 'sql-lab-operator'
      adminUsername: administratorName
      adminPassword: administratorPassword
      windowsConfiguration: { provisionVMAgent: true, enableAutomaticUpdates: true }
    }
    securityProfile: {
      securityType: 'TrustedLaunch'
      uefiSettings: { secureBootEnabled: true, vTpmEnabled: true }
    }
    networkProfile: { networkInterfaces: [{ id: nic.id, properties: { primary: true, deleteOption: 'Delete' } }] }
    diagnosticsProfile: { bootDiagnostics: { enabled: false } }
  }
}
resource bastion 'Microsoft.Network/bastionHosts@2025-01-01' = {
  name: '${prefix}-bastion'
  location: location
  tags: tags
  sku: { name: 'Developer' }
  properties: { virtualNetwork: { id: vnet.id } }
}

output operatorVmName string = vm.name
output operatorNicName string = nic.name
