variable "TAG" {
  default = "latest"
}

group "default" {
  targets = ["app"]
}

target "app" {
  dockerfile = "Dockerfile.full"
  tags = ["rotki-agpl:${TAG}"]
  platforms = ["linux/amd64", "linux/arm64"]
  cache-from = [
    "type=gha,scope=frontend",
    "type=gha,scope=backend",
  ]
  cache-to = [
    "type=gha,mode=max,scope=frontend",
    "type=gha,mode=max,scope=backend",
  ]
}
