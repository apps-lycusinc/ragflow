# RAGFlow Development Container Setup

This guide provides step-by-step instructions to set up and run the RAGFlow project using VS Code Dev Containers extension.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

1. **Visual Studio Code**: Download and install from [https://code.visualstudio.com/](https://code.visualstudio.com/)
2. **Docker**: Download and install from [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
3. **Dev Containers Extension**: Install the "Dev Containers" extension by Microsoft in VS Code

## Step-by-Step Setup Instructions

### Step 1: Install Dev Containers Extension

1. Open VS Code
2. Go to Extensions view (`Ctrl+Shift+X` or `Cmd+Shift+X`)
3. Search for "Dev Containers"
4. Install the "Dev Containers" extension by Microsoft (ms-vscode-remote.remote-containers)

### Step 2: Clone the Repository

```bash
git clone https://github.com/infiniflow/ragflow.git
cd ragflow
```

### Step 3: Open Project in Dev Container

1. Open VS Code in the project directory:
   ```bash
   code .
   ```

2. When VS Code opens, you should see a notification asking if you want to "Reopen in Container". Click **"Reopen in Container"**.

   **Alternative method if notification doesn't appear:**
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac) to open the Command Palette
   - Type "Dev Containers: Reopen in Container"
   - Select the command and press Enter

### Step 4: Container Build Process

The dev container will _**automatically**_:

1. **Build the development environment** using the configurations in `.devcontainer/`
2. **Install required features**:
   - Git
   - Node.js
   - Python 3.10
   - UV package manager
3. **Set up the workspace** with all necessary extensions
4. **Run post-creation setup** that includes:
   - Installing pipx and uv
   - Syncing Python dependencies
   - Setting up pre-commit hooks
   - Downloading required dependencies

This process may take several minutes on the first run as it needs to download and build the container images.

### Step 5: Verify Setup

Once the container is built and running, you should see:

1. **Terminal**: A bash terminal inside the container
2. **Extensions**: All development extensions automatically installed
3. **Port Forwarding**: The following ports are automatically forwarded:
   - 9200: Elasticsearch
   - 9201: OpenSearch
   - 6601: Kibana
   - 23817: Infinity Thrift
   - 23820: Infinity HTTP
   - 5432: PostgreSQL
   - 3306: MySQL
   - 9000: MinIO
   - 9001: MinIO Console
   - 6379: Redis
   - 9380: Server HTTP
   - 9385: Sandbox Executor Manager

### Step 6: Start Development

You can now start developing RAGFlow:

1. **Run the application** (follow the main project documentation for specific run commands)

2. **Access services**: Use `localhost` with the forwarded ports to access various services

## Development Workflow

### Working with the Container

- **File changes**: All file changes are automatically synced between your host machine and the container
- **Git operations**: Git is configured and ready to use inside the container
- **Extensions**: All recommended VS Code extensions are pre-installed
- **Python environment**: A Python 3.10 environment with UV package manager is ready to use

### Container Management

- **Rebuild container**: If you make changes to `.devcontainer/` files, rebuild using:
  - Command Palette (`Ctrl+Shift+P`) → "Dev Containers: Rebuild Container"

- **Stop container**: Close VS Code or use:
  - Command Palette (`Ctrl+Shift+P`) → "Dev Containers: Reopen Folder Locally"

## Troubleshooting

### Common Issues

1. **Docker not running**: Ensure Docker Desktop is running before opening the dev container
2. **Port conflicts**: If you have services running on the forwarded ports, stop them or modify the port configuration in `devcontainer.json`
3. **Build failures**: Try rebuilding the container with no cache:
   - Command Palette → "Dev Containers: Rebuild Without Cache"
4. **Permission errors on file save**: If you encounter permission errors when trying to save files from inside the dev container, you need to fix file ownership. Run the following command from your **host machine** in the root folder of the project:
   ```bash
   sudo chown -R $USER:$USER .
   ```
   This will recursively change ownership of all files and directories to your current user.

### Container Logs

To view container build logs and troubleshoot issues:
- Command Palette → "Dev Containers: Show Container Log"

## Configuration Files

The dev container setup uses these key files:

- **`.devcontainer/devcontainer.json`**: Main configuration file
- **`.devcontainer/Dockerfile`**: Container image definition
- **`.devcontainer/docker-compose.yml`**: Service orchestration
- **`.devcontainer/post_setup.sh`**: Post-creation setup script

## Additional Resources

- [RAGFlow Documentation](https://ragflow.io/docs/)
- [Dev Containers Documentation](https://code.visualstudio.com/docs/devcontainers/containers)
- [Docker Documentation](https://docs.docker.com/)
