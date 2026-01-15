#!/bin/bash

################################################################################
# Jetson Vision System - Docker Deployment Manager
# 
# This script manages Docker deployment for Jetson Vision System from miniPC
# Supports: build, deploy, test, monitor, stop, logs
#
# Usage:
#   ./jetson_docker.sh build    [--no-cache]
#   ./jetson_docker.sh deploy   [--prod]
#   ./jetson_docker.sh test     [--coverage]
#   ./jetson_docker.sh logs     [--follow]
#   ./jetson_docker.sh monitor
#   ./jetson_docker.sh stop
#   ./jetson_docker.sh restart
#   ./jetson_docker.sh status
#   ./jetson_docker.sh shell    [container-name]
#
# Environment Variables:
#   JETSON_HOST         - Jetson device hostname/IP
#   JETSON_USER         - SSH user for Jetson
#   DOCKER_REGISTRY     - Docker registry (default: local)
#   BUILD_VERSION       - Version tag for docker image
#   DEPLOYMENT_ENV      - Environment (dev, staging, prod)
#
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JETSON_DIR="${SCRIPT_DIR}"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Environment defaults
JETSON_HOST="${JETSON_HOST:-jetson-local.local}"
JETSON_USER="${JETSON_USER:-ubuntu}"
JETSON_PORT="${JETSON_PORT:-22}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-autobot}"
BUILD_VERSION="${BUILD_VERSION:-latest}"
DEPLOYMENT_ENV="${DEPLOYMENT_ENV:-dev}"
BUILD_NUMBER="${BUILD_NUMBER:-local}"

# Derived variables
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(cd "${PROJECT_ROOT}" && git rev-parse --short HEAD 2>/dev/null || echo "unknown")
IMAGE_NAME="${DOCKER_REGISTRY}/jetson-vision"
IMAGE_TAG="${IMAGE_NAME}:${BUILD_VERSION}"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Helper: SSH to Jetson
jetson_ssh() {
    ssh -p "${JETSON_PORT}" "${JETSON_USER}@${JETSON_HOST}" "$@"
}

# Helper: SCP to Jetson
jetson_scp() {
    scp -P "${JETSON_PORT}" "$@"
}

################################################################################
# BUILD: Build Docker image
################################################################################
build_image() {
    local no_cache=""
    
    [[ "$1" == "--no-cache" ]] && no_cache="--no-cache"
    
    log_info "Building Docker image: ${IMAGE_TAG}"
    log_info "Build date: ${BUILD_DATE}"
    log_info "VCS ref: ${VCS_REF}"
    
    # Build with build arguments for metadata
    docker build \
        ${no_cache} \
        --build-arg BUILD_DATE="${BUILD_DATE}" \
        --build-arg VCS_REF="${VCS_REF}" \
        --build-arg BUILD_VERSION="${BUILD_VERSION}" \
        -t "${IMAGE_TAG}" \
        -f "${JETSON_DIR}/Dockerfile" \
        "${JETSON_DIR}"
    
    log_success "Docker image built: ${IMAGE_TAG}"
    
    # Show image info
    docker images "${IMAGE_NAME}"
}

build_ci_image() {
    local no_cache=""
    
    [[ "$1" == "--no-cache" ]] && no_cache="--no-cache"
    
    log_info "Building CI/CD Docker image"
    
    docker build \
        ${no_cache} \
        --build-arg BUILD_DATE="${BUILD_DATE}" \
        --build-arg VCS_REF="${VCS_REF}" \
        --build-arg BUILD_VERSION="test-${BUILD_NUMBER}" \
        -t "${IMAGE_NAME}:test-${BUILD_NUMBER}" \
        -f "${JETSON_DIR}/Dockerfile.ci" \
        "${JETSON_DIR}"
    
    log_success "CI Docker image built"
}

################################################################################
# DEPLOY: Deploy to Jetson
################################################################################
deploy_to_jetson() {
    local env_flag=""
    [[ "$1" == "--prod" ]] && env_flag=".prod"
    
    log_info "Deploying Jetson Vision to: ${JETSON_HOST}"
    log_info "Environment: ${DEPLOYMENT_ENV}"
    
    # Check Jetson connectivity
    log_info "Checking Jetson connectivity..."
    if ! jetson_ssh "echo 'Connected'" > /dev/null 2>&1; then
        log_error "Cannot connect to Jetson at ${JETSON_HOST}"
        return 1
    fi
    log_success "Connected to Jetson"
    
    # Create remote app directory
    log_info "Setting up directories on Jetson..."
    jetson_ssh "mkdir -p /app/autobot-jetson/config /var/log/autobot/jetson"
    
    # SCP docker-compose file
    log_info "Copying docker-compose${env_flag}.yml to Jetson..."
    jetson_scp \
        "${JETSON_DIR}/docker-compose${env_flag}.yml" \
        "${JETSON_USER}@${JETSON_HOST}:/app/autobot-jetson/docker-compose.yml"
    
    # SCP .env if exists
    if [[ -f "${JETSON_DIR}/.env" ]]; then
        log_info "Copying .env to Jetson..."
        jetson_scp \
            "${JETSON_DIR}/.env" \
            "${JETSON_USER}@${JETSON_HOST}:/app/autobot-jetson/.env"
    fi
    
    # SCP application files
    log_info "Copying application files to Jetson..."
    jetson_scp -r \
        "${JETSON_DIR}"/*.py \
        "${JETSON_USER}@${JETSON_HOST}:/app/autobot-jetson/"
    
    jetson_scp -r \
        "${JETSON_DIR}/config" \
        "${JETSON_USER}@${JETSON_HOST}:/app/autobot-jetson/" 2>/dev/null || true
    
    jetson_scp \
        "${JETSON_DIR}/requirements.txt" \
        "${JETSON_USER}@${JETSON_HOST}:/app/autobot-jetson/"
    
    jetson_scp \
        "${JETSON_DIR}/Dockerfile" \
        "${JETSON_USER}@${JETSON_HOST}:/app/autobot-jetson/"
    
    # Build on Jetson
    log_info "Building Docker image on Jetson..."
    jetson_ssh "cd /app/autobot-jetson && \
               docker build \
                   --build-arg BUILD_DATE='${BUILD_DATE}' \
                   --build-arg VCS_REF='${VCS_REF}' \
                   --build-arg BUILD_VERSION='${BUILD_VERSION}' \
                   -t '${IMAGE_TAG}' \
                   -f Dockerfile ."
    
    # Stop existing container
    log_info "Stopping existing containers..."
    jetson_ssh "cd /app/autobot-jetson && \
               docker-compose down || true"
    
    # Deploy new container
    log_info "Starting new container..."
    jetson_ssh "cd /app/autobot-jetson && \
               docker-compose up -d"
    
    # Verify deployment
    sleep 5
    log_info "Verifying deployment..."
    jetson_ssh "docker-compose -f /app/autobot-jetson/docker-compose.yml ps"
    
    log_success "Jetson deployment complete!"
}

################################################################################
# TEST: Run CI/CD tests
################################################################################
run_tests() {
    local coverage=""
    [[ "$1" == "--coverage" ]] && coverage="--coverage"
    
    log_info "Running CI/CD tests in Docker"
    
    # Build CI image
    build_ci_image
    
    # Run tests
    log_info "Executing tests..."
    docker-compose \
        -f "${JETSON_DIR}/docker-compose.ci.yml" \
        -p "jetson-test-${BUILD_NUMBER}" \
        run --rm jetson-test
    
    log_info "Running linter..."
    docker-compose \
        -f "${JETSON_DIR}/docker-compose.ci.yml" \
        -p "jetson-test-${BUILD_NUMBER}" \
        run --rm jetson-lint
    
    log_info "Running security scan..."
    docker-compose \
        -f "${JETSON_DIR}/docker-compose.ci.yml" \
        -p "jetson-test-${BUILD_NUMBER}" \
        run --rm jetson-security
    
    log_info "Validating image..."
    docker-compose \
        -f "${JETSON_DIR}/docker-compose.ci.yml" \
        -p "jetson-test-${BUILD_NUMBER}" \
        run --rm jetson-validate
    
    log_success "All tests completed!"
}

################################################################################
# LOGS: View container logs
################################################################################
view_logs() {
    local follow=""
    [[ "$1" == "--follow" ]] && follow="-f"
    
    log_info "Fetching logs from Jetson..."
    
    jetson_ssh "docker logs ${follow} autobot-jetson-vision 2>&1"
}

view_local_logs() {
    log_info "Viewing local test results..."
    
    if [[ -d "test-results" ]]; then
        ls -lah test-results/
    fi
}

################################################################################
# MONITOR: Monitor container health
################################################################################
monitor_container() {
    log_info "Monitoring Jetson container..."
    
    jetson_ssh "docker stats autobot-jetson-vision --no-stream"
}

################################################################################
# STOP: Stop containers
################################################################################
stop_containers() {
    log_info "Stopping containers on Jetson..."
    
    jetson_ssh "docker-compose -f /app/autobot-jetson/docker-compose.yml down"
    
    log_success "Containers stopped"
}

################################################################################
# RESTART: Restart containers
################################################################################
restart_containers() {
    log_info "Restarting containers on Jetson..."
    
    jetson_ssh "docker-compose -f /app/autobot-jetson/docker-compose.yml restart"
    
    log_success "Containers restarted"
}

################################################################################
# STATUS: Check container status
################################################################################
check_status() {
    log_info "Checking container status on Jetson..."
    
    jetson_ssh "docker-compose -f /app/autobot-jetson/docker-compose.yml ps"
}

################################################################################
# SHELL: Execute shell in container
################################################################################
exec_shell() {
    local container="${1:-autobot-jetson-vision}"
    
    log_info "Executing shell in ${container}..."
    
    jetson_ssh "docker exec -it ${container} /bin/bash"
}

################################################################################
# CLEAN: Clean up Docker resources
################################################################################
cleanup() {
    log_warning "Cleaning up Docker resources..."
    
    log_info "Removing dangling images..."
    docker image prune -f
    
    log_info "Removing stopped containers..."
    docker container prune -f
    
    log_success "Cleanup complete"
}

################################################################################
# PUSH: Push image to registry
################################################################################
push_image() {
    log_info "Pushing image to registry..."
    
    docker push "${IMAGE_TAG}"
    
    log_success "Image pushed: ${IMAGE_TAG}"
}

################################################################################
# MAIN
################################################################################
main() {
    if [[ $# -lt 1 ]]; then
        cat << EOF
${GREEN}Jetson Vision Docker Deployment Manager${NC}

Usage: $0 <command> [options]

Commands:
  build              Build Docker image
  build-ci           Build CI/CD image
  deploy             Deploy to Jetson (dev environment)
  deploy --prod      Deploy to Jetson (production)
  test               Run CI/CD tests
  logs               View container logs
  logs --follow      Follow container logs in real-time
  monitor            Monitor container resources
  stop               Stop containers on Jetson
  restart            Restart containers on Jetson
  status             Check container status
  shell              Execute shell in container
  clean              Clean up Docker resources
  push               Push image to registry

Options:
  --no-cache         Build without cache
  --prod             Use production configuration
  --follow           Follow logs in real-time
  --coverage         Generate coverage report

Environment Variables:
  JETSON_HOST        Jetson hostname (default: jetson-local.local)
  JETSON_USER        SSH user (default: ubuntu)
  JETSON_PORT        SSH port (default: 22)
  BUILD_VERSION      Image version tag (default: latest)
  DEPLOYMENT_ENV     Environment: dev|staging|prod (default: dev)

Examples:
  $0 build
  $0 build --no-cache
  $0 test --coverage
  $0 deploy
  $0 deploy --prod
  $0 logs --follow
  $0 stop

EOF
        exit 1
    fi
    
    local command="$1"
    shift
    
    case "${command}" in
        build)
            build_image "$@"
            ;;
        build-ci)
            build_ci_image "$@"
            ;;
        deploy)
            deploy_to_jetson "$@"
            ;;
        test)
            run_tests "$@"
            ;;
        logs)
            view_logs "$@"
            ;;
        monitor)
            monitor_container
            ;;
        stop)
            stop_containers
            ;;
        restart)
            restart_containers
            ;;
        status)
            check_status
            ;;
        shell)
            exec_shell "$@"
            ;;
        clean)
            cleanup
            ;;
        push)
            push_image
            ;;
        *)
            log_error "Unknown command: ${command}"
            exit 1
            ;;
    esac
}

main "$@"
