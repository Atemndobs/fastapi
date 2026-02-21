#!/bin/bash
set -e

# Deployment script for FastAPI RFP Scraper
# Usage: ./deploy.sh [version]
# Example: ./deploy.sh v0.1.3

# Configuration (no sensitive data - uses SSH config and Docker Hub login)
IMAGE_NAME="atemndobs/fastapi-amd64"
SERVER_ALIAS="zkm3"
CONTAINER_NAME="fastapi"
CONTAINER_PORT="2222:80"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get version from argument or auto-increment
if [ -n "$1" ]; then
    VERSION="$1"
else
    # Get latest version from Docker Hub and increment
    LATEST=$(docker images ${IMAGE_NAME} --format "{{.Tag}}" | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1)
    if [ -z "$LATEST" ]; then
        VERSION="v0.1.0"
    else
        # Increment patch version
        MAJOR=$(echo $LATEST | cut -d'.' -f1)
        MINOR=$(echo $LATEST | cut -d'.' -f2)
        PATCH=$(echo $LATEST | cut -d'.' -f3)
        PATCH=$((PATCH + 1))
        VERSION="${MAJOR}.${MINOR}.${PATCH}"
    fi
fi

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Deploying ${IMAGE_NAME}:${VERSION}${NC}"
echo -e "${YELLOW}========================================${NC}"

# Step 1: Build for AMD64
echo -e "\n${GREEN}[1/4] Building Docker image for linux/amd64...${NC}"
docker buildx build --platform linux/amd64 -t ${IMAGE_NAME}:${VERSION} --push .

if [ $? -ne 0 ]; then
    echo -e "${RED}Build failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Build and push complete${NC}"

# Step 2: Clean up server
echo -e "\n${GREEN}[2/4] Cleaning up server...${NC}"
ssh ${SERVER_ALIAS} "docker system prune -f" || true
echo -e "${GREEN}✓ Server cleanup complete${NC}"

# Step 3: Pull new image on server
echo -e "\n${GREEN}[3/4] Pulling new image on server...${NC}"
ssh ${SERVER_ALIAS} "docker pull ${IMAGE_NAME}:${VERSION}"

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to pull image on server!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Image pulled${NC}"

# Step 4: Deploy container
echo -e "\n${GREEN}[4/4] Deploying container...${NC}"
ssh ${SERVER_ALIAS} "docker rm -f ${CONTAINER_NAME} 2>/dev/null || true"
ssh ${SERVER_ALIAS} "docker run -d --name ${CONTAINER_NAME} -p ${CONTAINER_PORT} ${IMAGE_NAME}:${VERSION}"

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to start container!${NC}"
    exit 1
fi

# Wait for container to start
sleep 3

# Verify deployment
echo -e "\n${GREEN}Verifying deployment...${NC}"
CONTAINER_STATUS=$(ssh ${SERVER_ALIAS} "docker ps --filter name=${CONTAINER_NAME} --format '{{.Status}}'")
if [[ $CONTAINER_STATUS == *"Up"* ]]; then
    echo -e "${GREEN}✓ Container is running${NC}"
else
    echo -e "${RED}Container is not running!${NC}"
    ssh ${SERVER_ALIAS} "docker logs ${CONTAINER_NAME} --tail 20"
    exit 1
fi

# Test endpoint
echo -e "\n${GREEN}Testing RFP endpoint...${NC}"
RESPONSE=$(ssh ${SERVER_ALIAS} "curl -s -o /dev/null -w '%{http_code}' -X POST 'http://localhost:2222/api/v1/rfp/rfps_by_url' -H 'Content-Type: application/json' -d '{\"url\":\"https://www.rfpmart.com/web-design-and-development-rfp-government-contract.html\",\"limit\":1,\"skip\":0}'")

if [ "$RESPONSE" == "200" ]; then
    echo -e "${GREEN}✓ RFP endpoint responding (HTTP 200)${NC}"
else
    echo -e "${YELLOW}⚠ RFP endpoint returned HTTP ${RESPONSE}${NC}"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment complete!${NC}"
echo -e "${GREEN}Image: ${IMAGE_NAME}:${VERSION}${NC}"
echo -e "${GREEN}Server: ${SERVER_ALIAS}${NC}"
echo -e "${GREEN}========================================${NC}"

# Show container info
echo -e "\n${YELLOW}Container status:${NC}"
ssh ${SERVER_ALIAS} "docker ps --filter name=${CONTAINER_NAME} --format 'table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'"
