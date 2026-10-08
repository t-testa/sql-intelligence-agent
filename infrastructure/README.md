# Azure templates — M2 preparation

These templates have not been deployed. They are a reviewable starting point, not evidence of
Azure readiness. `main.bicep` creates a new private foundation; `application.bicep` creates only
the authenticated private API after database bootstrap. No cloud frontend is deployed until
delegated Entra sign-in is implemented and tested.

`main.bicep` creates billable resources and one **resource-scoped Cognitive Services OpenAI User**
assignment. Do not deploy until the owner approves the resource group, region, cost and identity.
It never grants subscription Contributor/Owner. It creates no model deployment or Entra app
registration. The optional Key Vault remains inaccessible until its own private endpoint and
scoped access are separately reviewed.

See [DEPLOYMENT.md](../DEPLOYMENT.md) for the staged process, gates and cleanup. Compile locally:

```powershell
az bicep build --file infrastructure/main.bicep --outfile artifacts/main.json
az bicep build --file infrastructure/application.bicep --outfile artifacts/application.json
```

Resource schemas were checked against Microsoft's official
[Container Apps environment](https://learn.microsoft.com/en-us/azure/templates/microsoft.app/2024-03-01/managedenvironments),
[Container App](https://learn.microsoft.com/en-us/azure/templates/microsoft.app/2024-03-01/containerapps),
[Azure SQL](https://learn.microsoft.com/en-us/azure/templates/microsoft.sql/2023-08-01/servers) and
[Azure OpenAI account](https://learn.microsoft.com/en-us/azure/templates/microsoft.cognitiveservices/2023-05-01/accounts)
references. Bicep compilation does not verify regional capacity, quotas, runtime connectivity,
RBAC propagation, tenant policy or the full Entra user flow.
