# Noisy Neighbor Research

Undergraduate thesis research repository: **"Effectiveness of Cgroups Isolation Configuration in Mitigating *Noisy Neighbor* in Container-Based Environments"**.

This research empirically tests whether CPU and memory limitation based on **cgroups v2** in Docker Engine (without orchestrators like Kubernetes) can prevent one aggressive container from degrading the performance of other containers on the same host.

---

## Repository Structure

```text
noisy-neighbor-research/
├── README.md
├── .gitignore
├── .gitattributes                  # forces LF on Linux scripts
├── terraform/
│   ├── versions.tf                 # Terraform and provider versions (locked)
│   ├── providers.tf                # AWS provider, default tags
│   ├── variables.tf                # variables declaration
│   ├── terraform.tfvars.example    # variable values template
│   ├── data.tf                     # Ubuntu 22.04 AMI and AZ
│   ├── network.tf                  # VPC, subnets, IGW, route table
│   ├── security.tf                 # Security Groups
│   ├── keypair.tf                  # key pair from local public key
│   ├── compute.tf                  # Target Node and Attacker Node EC2 instances
│   ├── budget.tf                   # AWS Budget alarm
│   ├── outputs.tf                  # IP and SSH commands
│   └── user_data/
│       ├── target_node.sh          # Docker 27.x, cgroups v2, swap off, sysstat, psutil
│       └── attacker_node.sh        # JRE, JMeter 5.6.3, Python
├── scripts/
│   ├── deploy.ps1                  # terraform apply + wait for bootstrap
│   └── destroy.ps1                 # pull results then terraform destroy
├── apps/                           # aggressor, victim
├── jmeter/                         # .jmx test plans
└── results/                        # experiment results (Git ignored)
```

---

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.6.0
- [AWS CLI](https://aws.amazon.com/cli/) v2 and an AWS account with credentials configured (`aws configure`)
- OpenSSH client (`ssh`, `scp`, `ssh-keygen`)
- PowerShell (for `deploy.ps1` and `destroy.ps1`)

---

## Quick Start

> [!WARNING]
> The `terraform apply` command **provisions paid resources on AWS**. Do not forget to `destroy` when you are done.

### 1. Create SSH key pair (one-time)

```powershell
ssh-keygen -t ed25519 -f $HOME\.ssh\noisy-neighbor
```

Only the `.pub` file is used by Terraform. Never commit the private key file.

### 2. Prepare variables

```powershell
Copy-Item terraform\terraform.tfvars.example terraform\terraform.tfvars
```

Fill in `terraform/terraform.tfvars`:

| Variable | Description |
|---|---|
| `allowed_ssh_cidr` | Your public IP suffixed with `/32`. `0.0.0.0/0` is rejected by validation |
| `budget_email` | Recipient email for AWS Budget notifications |
| `region` | Default is `ap-southeast-2` |

### 3. Local validation

```powershell
cd terraform
terraform init
terraform validate
```

### 4. Deploy to AWS

```powershell
cd ..\scripts
.\deploy.ps1
```

The script runs `terraform apply`, then waits for the `/var/log/bootstrap-done` flag on both nodes. If `/var/log/bootstrap-failed` appears, check `/var/log/bootstrap.log` on the respective node.

### 5. Run the experiment

This stage waits for the applications and automation scripts to be created. The planned flow is: a pilot study, followed by 80 randomized sessions in a single `terraform apply` run using `tmux` on the Attacker Node.

### 6. Pull results and destroy infrastructure

```powershell
.\destroy.ps1
```

The script pulls `~/results` from the Attacker Node to `results/<timestamp>/`, then asks you to type `destroy`. If the pull fails or the results folder is empty, the `destroy` is aborted so data is not lost. Afterwards, check the AWS Console (EC2, EBS, Elastic IP) to ensure no leftover resources remain.

---