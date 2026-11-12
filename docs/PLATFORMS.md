# LocalMind Platform Interoperability & Support Matrix

> **Verification Policy:** "Evidence over assertion: every cell is marked based on reproducible evidence. No cell is marked verified without explicit proof."

---

## 1. Operating System & Platform Support Matrix

| OS / Platform | Architecture | Mode | Status | Verification Evidence / Command |
| :--- | :---: | :---: | :---: | :--- |
| **Windows 11 (23H2+)** | `x86_64` (`amd64`) | Kubernetes (Helm v3) | **Manually Verified** | Release `my-release` deployed in default namespace; all 7 pods running (`kubectl get pods`). E2E automated script passed. |
| **Windows 11 (23H2+)** | `x86_64` (`amd64`) | Docker Compose | **Manually Verified** | Compose stack with 7 microservices booted; unit tests pass in 2.55s (`pytest tests/unit/`). |
| **Ubuntu Linux 22.04 LTS** | `x86_64` (`amd64`) | Docker Compose + Helm/Kind | **CI-Verified** | GitHub Actions `.github/workflows/ci.yml` runs Docker Compose smoke test + `helm lint` + `kind` Kubernetes cluster deployment on every PR. |
| **Ubuntu Linux 24.04 LTS** | `x86_64` (`amd64`) | NVIDIA GPU Acceleration | **Manually Verified** | Tested with NVIDIA Container Toolkit (`--gpus all`), Ollama VRAM offloading to CUDA device. |
| **macOS (Apple Silicon M1/M2/M3/M4)** | `aarch64` (`arm64`) | Docker Compose + Native Ollama | **Manually Verified** | Multi-arch Docker images built via buildx (`linux/arm64`). Native Ollama with Metal GPU acceleration mapped via `host.docker.internal:11434`. |
| **macOS (Intel Core)** | `x86_64` | Docker Compose / CLI | **CI-Verified** | GitHub Actions macOS runner executes Python linting and unit test suite. |
| **Windows Server 2022** | `x86_64` | Kubernetes (Bare-Metal / AKS) | **Untested** | Helm chart manifests compliant with Kubernetes v1.28+, but bare-metal Windows node pools have not been executed in this test cycle. |
| **RHEL / Rocky Linux 9** | `x86_64` | Podman / Kubernetes | **Untested** | Podman rootless socket mappings not verified; standard Docker and containerd verified only. |

---

## 2. Hardware Acceleration Setup Guides

### 2.1 macOS Apple Silicon (Metal GPU Acceleration via Native Ollama)

On macOS, running Ollama inside a Docker container loses direct Apple Neural Engine / Metal GPU acceleration. For peak inference performance (35+ tokens/sec on M-series chips):

1. **Install native Ollama on macOS:**
   ```bash
   brew install ollama
   ollama serve
   ollama pull llama3.2:3b
   ollama pull nomic-embed-text
   ```
2. **Configure Docker Compose to use native host Ollama:**
   Set in `.env`:
   ```env
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   ```
   Docker Compose automatically routes requests to host macOS via the built-in `host.docker.internal` bridge.
3. **Disable the in-container Ollama container:**
   ```bash
   docker compose up -d db redis minio api ingestion web
   ```

---

### 2.2 Linux NVIDIA GPU Acceleration (CUDA / Tensor Cores)

To leverage an NVIDIA GPU on Ubuntu/Debian/RHEL:

1. **Install NVIDIA Container Toolkit:**
   ```bash
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
   && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
   && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
      sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
      sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
   sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```

2. **Verify GPU availability to Docker:**
   ```bash
   docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
   ```

3. **Enable GPU in LocalMind Docker Compose:**
   Add under the `ollama` service in `docker-compose.yml`:
   ```yaml
   deploy:
     resources:
       reservations:
         devices:
           - driver: nvidia
             count: all
             capabilities: [gpu]
   ```

4. **Enable GPU in Kubernetes (Helm):**
   Install using the Large profile:
   ```bash
   helm install localmind ./infra/helm/localmind -f ./infra/helm/localmind/values-large.yaml
   ```
   This automatically injects `resources.limits: nvidia.com/gpu: 1` and `nodeSelector: nvidia.com/gpu: "present"`.

---

## 3. Cross-Platform Configuration Artifacts

- **`.gitattributes`:** Enforces POSIX Line Feeds (`eol=lf`) for all shell scripts (`*.sh`), Dockerfiles, Python modules, and YAML manifests to prevent Windows CRLF syntax errors inside Linux containers.
- **`.editorconfig`:** Defines consistent cross-IDE indentation (4 spaces Python, 2 spaces Web/YAML, UTF-8 charset).
- **`extra_hosts: host.docker.internal:host-gateway`:** Enriched into `docker-compose.yml` so Linux Docker hosts resolve the host bridge identically to Docker Desktop on Windows/macOS.
- **Multi-Arch Docker Images:** Automated via GitHub Actions Buildx (`linux/amd64` and `linux/arm64`).

