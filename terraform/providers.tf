provider "aws" {
  region  = var.region
  profile = "research-account"

  default_tags {
    tags = {
      Project = "noisy-neighbor-research"
      Owner   = "elgin-brian"
    }
  }
}
