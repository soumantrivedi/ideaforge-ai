# GitHub Actions Workflows

## Docker Publish and PR Workflow

The `docker-publish-and-pr.yml` workflow automatically:

1. **Builds Docker Images**: Builds both backend and frontend Docker images
2. **Publishes to GHCR**: Pushes images to GitHub Container Registry (ghcr.io)
3. **Tests Deployment**: Starts services and verifies they're healthy
4. **Checks Logs**: Scans docker logs for errors
5. **Creates PR**: Automatically creates a pull request if everything passes

### Triggers

- Manual trigger via `workflow_dispatch`
- Push to `main` or `develop` branches
- Changes to backend, frontend, or Docker files

### Requirements

- GitHub token with `contents:write`, `packages:write`, and `pull-requests:write` permissions
- Docker images will be published to: `ghcr.io/<owner>/<repo>/backend` and `ghcr.io/<owner>/<repo>/frontend`

### Usage

1. Push changes to trigger the workflow, or
2. Go to Actions tab → "Build, Publish Docker Images, and Create PR" → Run workflow

### Output

- Docker images tagged with: branch name, SHA, and `latest` (for default branch)
- Pull request with deployment details and verification results
