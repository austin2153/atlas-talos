output "talosconfig" {
  description = "Talos client configuration — use with talosctl --talosconfig"
  value       = data.talos_client_configuration.this.talos_config
  sensitive   = true
}

output "kubeconfig" {
  description = "Kubernetes client configuration — use with kubectl --kubeconfig"
  value       = talos_cluster_kubeconfig.this.kubeconfig_raw
  sensitive   = true
}

output "post_apply_instructions" {
  description = "Run these commands after apply to refresh kubectl access"
  value       = <<-EOT
    terraform output -raw kubeconfig > ~/.kube/atlas-talos.kubeconfig
    terraform output -raw talosconfig > ~/.talos/atlas-talos.talosconfig
    KUBECONFIG=~/.kube/config:~/.kube/atlas-talos.kubeconfig kubectl config view --flatten > ~/.kube/config-merged && mv ~/.kube/config-merged ~/.kube/config
    kubectl config use-context admin@atlas
  EOT
}
