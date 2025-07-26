Great! Below is a **complete CI/CD setup** to automate:

- Docker image build and push to **Docker Hub**
- Kubernetes manifests deployment to **DigitalOcean Kubernetes (DOKS)**
- Optional: force rollout if deployment already exists

**✅ Prerequisites**

1. **Source control**: GitHub (or GitLab/Bitbucket with tweaks)
2. **Docker Hub account**
3. **DigitalOcean account with DOKS cluster running**
4. **Secrets set in GitHub Actions** (go to your repo → Settings → Secrets and variables → Actions):

| **Secret Name** | **Description** |
| --- | --- |
| DOCKERHUB_USERNAME | Your Docker Hub username |
| DOCKERHUB_TOKEN | Docker Hub Personal Access Token |
| DIGITALOCEAN_KUBECONFIG | Base64 encoded kubeconfig file for your DOKS cluster |

To get the base64 kubeconfig:

```bash

cat ~/.kube/config | base64 -w 0
```

**✅ Directory Structure Assumed**

```csharp
api/
├── Dockerfile.k8s.staging
├── Dockerfile.cron.k8s
├── Dockerfile.celery_worker.k8s
├── Dockerfile.celery_api_queue.k8s
├── Dockerfile.celery_dashboard_queue.k8s
├── kubernetes/
│   └── base/
│       ├── configmaps/
│       ├── secrets/
│       ├── deployments/
│       ├── services/
│       └── cron/


```

**✅ GitHub Actions Workflow (.github/workflows/deploy.yml)**

```yaml
name: 🚀 CI/CD to DigitalOcean Kubernetes

on:
  push:
    branches:
      - main  # or your deployment branch

env:
  IMAGE_NAME: image_name
  DOCKERHUB_USERNAME: ${{ secrets.DOCKERHUB_USERNAME }}
  TAG: latest

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
    - name: 📥 Checkout Code
      uses: actions/checkout@v3

    - name: 🔐 Set up Docker credentials
      run: echo "${{ secrets.DOCKERHUB_TOKEN }}" | docker login -u $DOCKERHUB_USERNAME --password-stdin

    - name: 🔧 Set up Kubeconfig
      run: |
        echo "${{ secrets.DIGITALOCEAN_KUBECONFIG }}" | base64 --decode > $HOME/.kube/config

    - name: 🛠️ Build and Push Docker Images
      run: |
        declare -A files=(
          ["api"]="Dockerfile.k8s.staging"
          ["cron"]="Dockerfile.cron.k8s"
          ["celery_worker"]="Dockerfile.celery_worker.k8s"
          ["celery_api_queue"]="Dockerfile.celery_api_queue.k8s"
          ["celery_dashboard_queue"]="Dockerfile.celery_dashboard_queue.k8s"
        )
        for name in "${!files[@]}"; do
          dockerfile=${files[$name]}
          image="$DOCKERHUB_USERNAME/${IMAGE_NAME}_${name}:${TAG}"
          echo "🔨 Building $image from $dockerfile..."
          docker build -f $dockerfile -t $image .
          docker push $image
        done

    - name: 📦 Deploy Kubernetes manifests
      run: |
        for folder in configmaps secrets deployments services cron; do
          path="./api/kubernetes/base/$folder"
          if [ -d "$path" ]; then
            echo "📁 Applying $folder manifests..."
            kubectl apply -f "$path"
          fi
        done

    - name: 🔁 Rollout Restart Deployments
      run: |
        echo "♻️ Restarting all deployments in default namespace..."
        kubectl rollout restart deployment -n default || echo "⚠️ No deployments to restart"


```
**✅ How to Trigger CI/CD**

- Push to the main branch (or whichever branch is defined in on.push.branches)
- GitHub will:
  - Build each Dockerfile
  - Push the image to Docker Hub
  - Apply Kubernetes manifests to DigitalOcean Kubernetes
  - Rollout restart the deployments