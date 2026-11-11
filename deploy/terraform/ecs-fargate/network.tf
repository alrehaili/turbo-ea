# Security groups. Unlike CloudFormation, a Terraform-managed group starts
# with no egress rule, so each one gets its own.

resource "aws_security_group" "alb" {
  name_prefix = "${var.name}-alb-"
  description = "Turbo EA load balancer"
  vpc_id      = var.vpc_id

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  description       = "Public HTTP entry point redirects to HTTPS"
  security_group_id = aws_security_group.alb.id
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  description       = "Public HTTPS entry point"
  security_group_id = aws_security_group.alb.id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "alb" {
  description                  = "Forward requests and health checks only to the application"
  security_group_id            = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = 8920
  to_port                      = 8920
  referenced_security_group_id = aws_security_group.task.id
}

resource "aws_security_group" "task" {
  name_prefix = "${var.name}-task-"
  description = "Turbo EA task"
  vpc_id      = var.vpc_id

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "task_from_alb" {
  description                  = "Application traffic and health checks from the load balancer"
  security_group_id            = aws_security_group.task.id
  ip_protocol                  = "tcp"
  from_port                    = 8920
  to_port                      = 8920
  referenced_security_group_id = aws_security_group.alb.id
}

# External IdPs, AI providers, image registries, Secrets Manager and CloudWatch
# use changing HTTPS destinations. Restrict the protocol/port; operators can
# narrow the destination CIDRs or use an egress proxy/VPC endpoints.
# Reviewed 2026-11-11; re-evaluate by 2027-02-11.
# trivy:ignore:AVD-AWS-0104:exp:2027-02-11
resource "aws_vpc_security_group_egress_rule" "task_https" {
  for_each = var.https_egress_cidrs

  description       = "HTTPS access to approved external services"
  security_group_id = aws_security_group.task.id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = each.value
}

resource "aws_vpc_security_group_egress_rule" "task_db" {
  count = var.create_database || var.db_security_group_id != null ? 1 : 0

  description                  = "PostgreSQL access only to the configured database security group"
  security_group_id            = aws_security_group.task.id
  ip_protocol                  = "tcp"
  from_port                    = var.db_port
  to_port                      = var.db_port
  referenced_security_group_id = var.create_database ? aws_security_group.db[0].id : var.db_security_group_id
}

resource "aws_vpc_security_group_egress_rule" "task_byo_db" {
  for_each = !var.create_database && var.db_security_group_id == null ? var.db_egress_cidrs : toset([])

  description       = "PostgreSQL access to the approved existing database network"
  security_group_id = aws_security_group.task.id
  ip_protocol       = "tcp"
  from_port         = var.db_port
  to_port           = var.db_port
  cidr_ipv4         = each.value
}

resource "aws_vpc_security_group_egress_rule" "task_efs" {
  description                  = "NFS access only to the application data volume"
  security_group_id            = aws_security_group.task.id
  ip_protocol                  = "tcp"
  from_port                    = 2049
  to_port                      = 2049
  referenced_security_group_id = aws_security_group.efs.id
}

resource "aws_vpc_security_group_egress_rule" "task_extra" {
  for_each = var.additional_egress_rules

  description       = each.value.description
  security_group_id = aws_security_group.task.id
  ip_protocol       = "tcp"
  from_port         = each.value.port
  to_port           = each.value.port
  cidr_ipv4         = each.value.cidr_ipv4
}

resource "aws_security_group" "efs" {
  name_prefix = "${var.name}-efs-"
  description = "Turbo EA EFS mount targets"
  vpc_id      = var.vpc_id

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "efs_from_task" {
  description                  = "NFS mount access from the Turbo EA task"
  security_group_id            = aws_security_group.efs.id
  ip_protocol                  = "tcp"
  from_port                    = 2049
  to_port                      = 2049
  referenced_security_group_id = aws_security_group.task.id
}

# Bring-your-own database: open its port from the task.
resource "aws_vpc_security_group_ingress_rule" "byo_db" {
  count = var.db_security_group_id == null ? 0 : 1

  description                  = "PostgreSQL connections from the Turbo EA task"
  security_group_id            = var.db_security_group_id
  ip_protocol                  = "tcp"
  from_port                    = var.db_port
  to_port                      = var.db_port
  referenced_security_group_id = aws_security_group.task.id
}
