resource "kubernetes_manifest" "inference_worker_scaledobject" {
  manifest = {
    apiVersion = "keda.sh/v1alpha1"
    kind       = "ScaledObject"
    metadata = {
      name      = "inference-worker"
      namespace = kubernetes_namespace.inference.metadata[0].name
    }
    spec = {
      scaleTargetRef = {
        name = "inference-worker"
      }
      minReplicaCount = 2
      maxReplicaCount = 6
      pollingInterval = 15
      cooldownPeriod  = 120
      triggers = [
        {
          type = "kafka"
          metadata = {
            bootstrapServers = data.terraform_remote_state.platform.outputs.msk_bootstrap_brokers
            consumerGroup    = "inference-worker-group"
            topic            = "inference-request"
            lagThreshold     = "20"
            offsetResetPolicy = "latest"
            tls              = "enable"
          }
        }
      ]
    }
  }

  depends_on = [
    kubernetes_namespace.inference,
    kubernetes_config_map.inference_config,
  ]
}
