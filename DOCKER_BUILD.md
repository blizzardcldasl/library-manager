# Docker Build Instructions

## Automatic Build (GitHub Actions)

This repository includes a GitHub Actions workflow that automatically builds and pushes Docker images to GitHub Container Registry (GHCR) when you push to the `main` branch.

**Image Location:** `ghcr.io/blizzardcldasl/library-manager:latest`

### How It Works

1. **Automatic on Push** - When you push to `main`, the workflow builds and pushes the image
2. **Manual Trigger** - You can also trigger it manually from GitHub Actions tab
3. **Multi-Architecture** - Builds for both `linux/amd64` and `linux/arm64`

### Making the Image Public

**Important:** The container package visibility is separate from repository visibility. You can make the Docker image public even if your repository is a fork.

By default, GitHub Container Registry images are private. To make it public:

1. Wait for the GitHub Actions workflow to build the image first (check Actions tab)
2. Go to https://github.com/blizzardcldasl/library-manager/pkgs/container/library-manager
3. Click "Package settings" (gear icon) in the top right
4. Scroll to "Danger Zone" section
5. Click "Change visibility"
6. Select "Public"
7. Confirm

**Note:** If you see "cannot change visibility of a fork" error, you're likely trying to change the repository visibility, not the container package. The container package can be made public independently. If the package doesn't exist yet, wait for the GitHub Actions workflow to complete first.

## Manual Build

If you want to build locally:

```bash
# Build the image
docker build -t ghcr.io/blizzardcldasl/library-manager:latest .

# Tag with version
docker tag ghcr.io/blizzardcldasl/library-manager:latest ghcr.io/blizzardcldasl/library-manager:0.9.0-beta.27-fork.1

# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u blizzardcldasl --password-stdin

# Push to registry
docker push ghcr.io/blizzardcldasl/library-manager:latest
docker push ghcr.io/blizzardcldasl/library-manager:0.9.0-beta.27-fork.1
```

### Getting a GitHub Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Name it (e.g., "Docker Push")
4. Select scope: `write:packages`
5. Generate and copy the token
6. Use it as `GITHUB_TOKEN` environment variable

## Testing the Build

```bash
# Build locally
docker build -t library-manager-test .

# Run locally
docker run -d \
  --name library-manager-test \
  -p 5757:5757 \
  -v /path/to/audiobooks:/audiobooks \
  -v ./data:/data \
  library-manager-test

# Test
curl http://localhost:5757
```

## Using the Image

Once the image is built and pushed:

```bash
# Pull and run
docker run -d \
  --name library-manager \
  -p 5757:5757 \
  -v /path/to/audiobooks:/audiobooks \
  -v library-manager-data:/data \
  ghcr.io/blizzardcldasl/library-manager:latest
```

Or with docker-compose (already configured in `docker-compose.yml`):

```bash
docker-compose up -d
```

## Troubleshooting

### Image Not Found
- Make sure the image is public (see "Making the Image Public" above)
- Check that the workflow ran successfully in GitHub Actions

### Permission Denied
- Ensure you're logged in: `docker login ghcr.io`
- Check that your GitHub token has `write:packages` permission

### Build Fails
- Check GitHub Actions logs for errors
- Verify Dockerfile syntax
- Ensure all dependencies are in requirements.txt
