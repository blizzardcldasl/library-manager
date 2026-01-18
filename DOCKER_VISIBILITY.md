# Making Your Docker Image Public (Fork Repository)

## Understanding Repository vs Container Package Visibility

GitHub has two separate visibility settings:

1. **Repository Visibility** - Controls who can see your code repository
2. **Container Package Visibility** - Controls who can pull your Docker image

**Good News:** You can make your Docker image public even if your repository is a fork!

## Option 1: Make Container Package Public (Recommended)

The Docker image (container package) can be made public independently:

1. **Wait for the build to complete:**
   - Go to https://github.com/blizzardcldasl/library-manager/actions
   - Wait for the "Build and Push Docker Image" workflow to complete successfully

2. **Make the package public:**
   - Go to: https://github.com/blizzardcldasl/library-manager/pkgs/container/library-manager
   - Click "Package settings" (gear icon) in the top right
   - Scroll to "Danger Zone"
   - Click "Change visibility" (this is for the **package**, not the repo)
   - Select "Public"
   - Confirm

3. **Verify:**
   ```bash
   docker pull ghcr.io/blizzardcldasl/library-manager:latest
   ```

## Option 2: Detach Fork to Make Repository Public

If you want to make the **repository itself** public (not just the Docker image):

1. Go to your repository: https://github.com/blizzardcldasl/library-manager
2. Click **Settings** → **General**
3. Scroll to **Danger Zone**
4. Click **"Leave fork network"** or **"Detach from upstream"**
5. Wait for validation (may take a few minutes for large repos)
6. Refresh the page
7. Go back to **Settings** → **General** → **Danger Zone**
8. Click **"Change repository visibility"**
9. Select **Public**
10. Confirm

**Note:** Detaching from the fork network means:
- You can no longer easily sync with upstream changes
- You'll need to manually merge upstream changes
- The repository becomes a standalone repository

## Option 3: Use Docker Hub Instead

If you prefer Docker Hub over GitHub Container Registry:

1. **Create Docker Hub account** (if you don't have one)
2. **Update docker-compose.yml:**
   ```yaml
   image: blizzardcldasl/library-manager:latest
   ```

3. **Update GitHub Actions workflow** to push to Docker Hub:
   ```yaml
   - name: Log in to Docker Hub
     uses: docker/login-action@v3
     with:
       username: ${{ secrets.DOCKERHUB_USERNAME }}
       password: ${{ secrets.DOCKERHUB_TOKEN }}
   ```

4. **Add secrets to GitHub:**
   - Go to Settings → Secrets and variables → Actions
   - Add `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`

## Recommended Approach

**For most users:** Use Option 1 - make the container package public. This allows:
- ✅ Public Docker image (anyone can pull)
- ✅ Keep fork relationship (easy to sync with upstream)
- ✅ No need to detach from fork network
- ✅ Repository can remain as-is

The Docker image being public is what matters for users pulling it with `docker pull`.
