provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project = "noisy-neighbor-research"
      Owner   = "elgin-brian"
    }
  }
}
