# Tenant Onboarding Guide

## Introduction
This guide explains how to onboard a new law firm (tenant) onto LocalMind.

## Steps
1. **Prepare Infrastructure**: Ensure K8s cluster (K3s for on-prem or EKS/GKE for cloud) is running.
2. **Execute Onboarding Script**:
   Run the onboarding script located in `infra/scripts/onboard_tenant.sh`:
   ```bash
   ./infra/scripts/onboard_tenant.sh <tenant_id>
   ```
3. **Verify Deployment**:
   ```bash
   kubectl get pods -n tenant-<tenant_id>
   ```
4. **Provide Access**: Provide the tenant administrator with their credentials and the URL to their dedicated instance.
