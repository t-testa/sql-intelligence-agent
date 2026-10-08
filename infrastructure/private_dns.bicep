// Second stage: foundation outputs supply the generated internal domain/IP.
targetScope = 'resourceGroup'
param environmentDefaultDomain string
param environmentStaticIp string
param applicationVnetId string

resource environmentDns 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: environmentDefaultDomain
  location: 'global'
}
resource environmentDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: environmentDns
  name: 'application-network'
  location: 'global'
  properties: { registrationEnabled: false, virtualNetwork: { id: applicationVnetId } }
}
resource environmentDnsRecords 'Microsoft.Network/privateDnsZones/A@2020-06-01' = [for record in ['@', '*']: {
  parent: environmentDns
  name: record
  properties: { ttl: 300, aRecords: [{ ipv4Address: environmentStaticIp }] }
}]
