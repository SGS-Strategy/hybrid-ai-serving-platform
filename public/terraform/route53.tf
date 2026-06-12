# Route 53 Resolver Inbound Endpoint
# - 온프레미스에서 VPC 내부 DNS 조회가 필요한 경우 활성화
# - 현재 구조: Edge → VPN → Internal ALB (DNS 조회 불필요)
# - 활성화 필요 시: 아래 주석 해제 후 apply
#
# [도메인 생기면 할 것 - Route 53 Public Hosted Zone 방식]
# - 현재는 Edge .env에 ALB DNS 주소를 직접 박아두는 방식 사용
#   (API_URL=http://internal-k8s-....elb.amazonaws.com/infer)
# - ALB가 재생성될 때마다 주소가 바뀌어 Edge .env를 수동으로 수정해야 하는 번거로움 있음
# - 도메인 생기면 아래 순서로 고정 주소 설정 가능:
#   1. Route 53 Public Hosted Zone 생성
#   2. api.도메인.com → ALB DNS CNAME 레코드 추가
#   3. Edge .env에 API_URL=http://api.도메인.com/infer 고정
#   → 이후 ALB 재생성돼도 Route 53 레코드만 업데이트하면 되고 Edge 쪽은 수정 불필요
# - Internal ALB는 퍼블릭 DNS로 조회해도 프라이빗 IP(10.0.x.x)가 반환되므로
#   VPN 연결 없이는 접근 불가 → 별도 보안 설정 없이 VPN이 게이트 역할 수행
# - Resolver Inbound Endpoint(이 파일)는 위 구조에서 불필요 (비활성 유지)
#
# resource "aws_security_group" "resolver_inbound" {
#   name        = "${var.project_name}-resolver-inbound-sg"
#   description = "Allow DNS from on-prem sites (Private Cloud + Edge) to the Route 53 Inbound Resolver"
#   vpc_id      = aws_vpc.main.id
#
#   dynamic "ingress" {
#     for_each = length(concat(var.private_cloud_cidrs, var.edge_network_cidrs)) > 0 ? [1] : []
#     content {
#       description = "DNS UDP from on-prem sites"
#       from_port   = 53
#       to_port     = 53
#       protocol    = "udp"
#       cidr_blocks = concat(var.private_cloud_cidrs, var.edge_network_cidrs)
#     }
#   }
#
#   dynamic "ingress" {
#     for_each = length(concat(var.private_cloud_cidrs, var.edge_network_cidrs)) > 0 ? [1] : []
#     content {
#       description = "DNS TCP from on-prem sites"
#       from_port   = 53
#       to_port     = 53
#       protocol    = "tcp"
#       cidr_blocks = concat(var.private_cloud_cidrs, var.edge_network_cidrs)
#     }
#   }
#
#   egress {
#     from_port   = 0
#     to_port     = 0
#     protocol    = "-1"
#     cidr_blocks = ["0.0.0.0/0"]
#   }
#
#   tags = merge(local.common_tags, {
#     Name = "${var.project_name}-resolver-inbound-sg"
#   })
# }
#
# resource "aws_route53_resolver_endpoint" "inbound" {
#   name      = "${var.project_name}-inbound-resolver"
#   direction = "INBOUND"
#
#   security_group_ids = [aws_security_group.resolver_inbound.id]
#
#   dynamic "ip_address" {
#     for_each = slice(aws_subnet.eks_private[*].id, 0, 2)
#     content {
#       subnet_id = ip_address.value
#     }
#   }
#
#   tags = merge(local.common_tags, {
#     Name = "${var.project_name}-inbound-resolver"
#   })
# }
