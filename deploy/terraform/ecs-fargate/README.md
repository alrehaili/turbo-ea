# Turbo EA on AWS ECS Fargate (Terraform)

Terraform counterpart of [`deploy/ecs-fargate/template.yaml`](../../ecs-fargate/template.yaml).
Guide: <https://docs.turbo-ea.org/admin/terraform/#aws-ecs-fargate>.

One Fargate task runs the edge nginx (8920, behind an Application Load
Balancer), the frontend (8080), the backend (8000) and the optional MCP
server (8001) as sidecars. The service keeps **one** task and replaces it
stop-then-start (`deployment_minimum_healthy_percent = 0`), so two backends
never run at once — at the price of one to two minutes of downtime per deploy.

## What you bring

- A VPC with at least two **public** subnets (load balancer) and two
  **private** subnets in different Availability Zones (task, EFS mount
  targets, RDS subnet group). The private subnets need a NAT gateway for
  image pulls from ghcr.io.
- An ACM certificate for the public hostname, in the same Region.
- Optionally a Route 53 hosted zone (`route53_zone_id`) for the alias
  record; otherwise create a CNAME to `alb_dns_name` yourself.

## What is created

Cluster (Container Insights), CloudWatch log group, execution + task IAM
roles, three security groups, EFS file system + two mount targets + access
point (uid/gid 1000, `/turbo-ea`), Secrets Manager secrets for `SECRET_KEY`
and the database password, ALB with HTTPS (TLS 1.3 policy) and an HTTP→HTTPS
redirect, target group on `/api/health`, task definition (2 vCPU / 4 GiB),
service (Fargate 1.4.0, ECS Exec enabled) and — by default — an RDS for
PostgreSQL instance (gp3, encrypted, private, deletion protection on).

## Bring your own database

```hcl
create_database      = false
db_host              = "turbo-ea.abcdefghij.eu-west-1.rds.amazonaws.com"
db_security_group_id = "sg-…"   # opens db_port from the task; or use the task_security_group_id output yourself
```

and `export TF_VAR_db_password='…'`.

If the existing database has no security group input, supply restricted
`db_egress_cidrs` instead, such as `["10.30.0.4/32"]`.

## Security and outbound integrations

The load balancer can only reach application tasks on TCP 8920. Tasks can reach
their database port, EFS on TCP 2049, and HTTPS on TCP 443. Restrict
`https_egress_cidrs` to approved destination networks or an egress proxy where
possible (the compatibility default allows HTTPS to any IPv4 address). SMTP,
LDAP and other ports need explicit `additional_egress_rules`; inventory those
integrations before upgrading. VPC DNS resolver traffic is handled by AWS and
does not require an unrestricted egress rule.

```hcl
additional_egress_rules = {
  smtp = { description = "Corporate SMTP relay", port = 587, cidr_ipv4 = "10.30.0.5/32" }
}
```

Secrets, CloudWatch logs and database Performance Insights use a rotating
customer-managed KMS key. The execution role can decrypt secrets only through
Secrets Manager; the log-service key grant is scoped to this workspace's log
group. Review key retention before destroying an installation: encrypted data
cannot be recovered after its key is deleted. RDS uses password authentication;
IAM database authentication is a documented scanner exception until the
application supports connection-time IAM tokens.

## Day two

- **Upgrade**: bump `image_tag`, `terraform apply`. The service stops the old
  task, starts the new one; the backend runs migrations at boot.
- **Shell into the backend**: `aws ecs execute-command --cluster <name>
  --task <id> --container backend --interactive --command sh`.
- **Backups**: EFS has AWS Backup enabled; RDS keeps
  `db_backup_retention_days` of automated backups. Back up the
  `secret_key_secret_arn` secret with the database — one is useless without
  the other.
- **Destroy**: set `db_deletion_protection = false` (and
  `db_skip_final_snapshot = true` if you really want no snapshot), apply,
  then `terraform destroy`.

## Inputs

| Name | Default | Notes |
|---|---|---|
| `region` | — | AWS Region |
| `name` | `turbo-ea` | Resource name prefix |
| `public_url` | — | `https://host`, no path |
| `image_tag` | — | Release to run, e.g. `2.141.0` |
| `image_repository` | `ghcr.io/vincentmakes/turbo-ea` | |
| `secret_key` | — | Sensitive; `openssl rand -base64 48` |
| `deploy_mcp` | `false` | MCP server sidecar at `/mcp` |
| `allowed_origins` / `embed_allowed_origins` | `[]` | CORS / iframe allow-lists |
| `nginx_trusted_proxies` | `""` | load balancer addresses whose `X-Forwarded-For` nginx trusts (usually the VPC CIDR), so the audit log records each user's own address |
| `db_pool_size` / `db_max_overflow` | `10` / `5` | Backend connection budget |
| `vpc_id`, `public_subnet_ids`, `private_subnet_ids` | — | Existing network |
| `certificate_arn` | — | ACM certificate |
| `route53_zone_id` | `null` | Optional alias record |
| `create_database` | `true` | RDS instance |
| `db_host`, `db_password`, `db_security_group_id` | `null` | Bring your own |
| `db_port`, `db_name`, `db_user` | `5432`, `turboea`, `turboea` | |
| `https_egress_cidrs` | `["0.0.0.0/0"]` | TCP 443 only; narrow where possible |
| `db_egress_cidrs` | `[]` | Required for an existing database without a security group input |
| `additional_egress_rules` | `{}` | Named objects with `description`, TCP `port` and restricted `cidr_ipv4` |
| `db_instance_class` | `db.t4g.micro` | |
| `db_engine_version` | `17` | Major version |
| `db_allocated_storage` | `20` | GiB, grows to 5× |
| `db_multi_az` | `false` | |
| `db_backup_retention_days` | `7` | |
| `db_deletion_protection` | `true` | |
| `db_skip_final_snapshot` | `false` | |
| `log_retention_days` | `30` | |
| `container_insights` | `true` | |
| `tags` | `{}` | Provider default tags |

## Outputs

`alb_dns_name`, `alb_zone_id`, `task_security_group_id`, `cluster_name`,
`service_name`, `task_definition_arn`, `efs_file_system_id`, `db_endpoint`,
`db_password_secret_arn`, `secret_key_secret_arn`.
