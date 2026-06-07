resource "kubernetes_namespace" "inference" {
  metadata {
    name = "inference"
  }

  depends_on = [aws_eks_node_group.workloads]
}

resource "kubernetes_config_map" "inference_config" {
  metadata {
    name      = "inference-config"
    namespace = kubernetes_namespace.inference.metadata[0].name
  }

  data = {
    BOOTSTRAP_SERVERS = aws_msk_cluster.main.bootstrap_brokers
  }

  depends_on = [aws_msk_cluster.main]
}

resource "helm_release" "aws_load_balancer_controller" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  version    = "1.13.4"
  namespace  = "kube-system"

  values = [
    yamlencode({
      clusterName = aws_eks_cluster.main.name
      region      = var.aws_region
      vpcId       = aws_vpc.main.id
      serviceAccount = {
        create = true
        name   = "aws-load-balancer-controller"
        annotations = {
          "eks.amazonaws.com/role-arn" = aws_iam_role.aws_load_balancer_controller.arn
        }
      }
    })
  ]

  depends_on = [
    aws_eks_node_group.workloads,
    aws_iam_role_policy_attachment.aws_load_balancer_controller,
  ]
}
