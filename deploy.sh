#!/bin/bash

# Telegram Query Bridge - Deployment Script
# Production deployment automation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "Please don't run this script as root!"
    fi
}

# Check Docker installation
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    success "Docker and Docker Compose are available"
}

# Check environment file
check_env() {
    if [[ ! -f ".env" ]]; then
        warning ".env file not found. Creating from template..."
        if [[ -f "production.env" ]]; then
            cp production.env .env
            warning "Please edit .env file with your production values before continuing!"
            read -p "Press Enter to continue after editing .env file..."
        else
            error "No production.env template found!"
        fi
    fi
    
    success "Environment file found"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p ssl
    mkdir -p backups
    mkdir -p telegram_service/session
    
    success "Directories created"
}

# Set proper permissions
set_permissions() {
    log "Setting proper permissions..."
    
    chmod +x deploy.sh
    chmod -R 755 logs/
    chmod -R 755 ssl/
    chmod -R 755 backups/
    chmod -R 755 telegram_service/session/
    
    success "Permissions set"
}

# Build Docker images
build_images() {
    log "Building Docker images..."
    
    docker-compose build --no-cache
    
    success "Docker images built successfully"
}

# Start services
start_services() {
    log "Starting services..."
    
    # Stop any existing services
    docker-compose down
    
    # Start services
    docker-compose up -d
    
    success "Services started"
}

# Wait for services to be healthy
wait_for_services() {
    log "Waiting for services to be healthy..."
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log "Health check attempt $attempt/$max_attempts"
        
        # Check Python service
        if curl -f http://localhost:8000/health &>/dev/null; then
            success "Python service is healthy"
        else
            warning "Python service not ready yet..."
        fi
        
        # Check Node.js service
        if curl -f http://localhost:3000/health &>/dev/null; then
            success "Node.js service is healthy"
        else
            warning "Node.js service not ready yet..."
        fi
        
        # Check Web Manager
        if curl -f http://localhost:9000/health &>/dev/null; then
            success "Web Manager is healthy"
        else
            warning "Web Manager not ready yet..."
        fi
        
        # If all services are healthy, break
        if curl -f http://localhost:8000/health &>/dev/null && \
           curl -f http://localhost:3000/health &>/dev/null && \
           curl -f http://localhost:9000/health &>/dev/null; then
            success "All services are healthy!"
            break
        fi
        
        sleep 10
        ((attempt++))
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        error "Services failed to become healthy within expected time"
    fi
}

# Setup SSL certificates (Let's Encrypt)
setup_ssl() {
    log "Setting up SSL certificates..."
    
    if command -v certbot &> /dev/null; then
        # Use Let's Encrypt if domain is configured
        if grep -q "yourdomain.com" .env; then
            warning "Domain not configured in .env. Skipping SSL setup."
        else
            log "Requesting SSL certificates..."
            # certbot commands would go here
            warning "SSL setup requires manual configuration"
        fi
    else
        warning "Certbot not found. SSL certificates not generated."
        warning "You can set up SSL manually or use self-signed certificates for testing."
    fi
}

# Setup monitoring
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Create Prometheus config if not exists
    if [[ ! -f "prometheus.yml" ]]; then
        cat > prometheus.yml << EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'telegram-bridge-python'
    static_configs:
      - targets: ['python-service:8000']
    
  - job_name: 'telegram-bridge-node'
    static_configs:
      - targets: ['node-service:3000']
    
  - job_name: 'telegram-bridge-manager'
    static_configs:
      - targets: ['web-manager:9000']
EOF
        success "Prometheus configuration created"
    fi
}

# Setup backup cron job
setup_backup() {
    log "Setting up backup cron job..."
    
    # Create backup script
    cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/telegram_bridge"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.tar.gz"

# Create backup
tar -czf "$BACKUP_FILE" \
    telegram_service/session/ \
    logs/ \
    .env \
    docker-compose.yml

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
EOF
    
    chmod +x backup.sh
    
    # Add to crontab (runs daily at 2 AM)
    (crontab -l 2>/dev/null; echo "0 2 * * * $(pwd)/backup.sh") | crontab -
    
    success "Backup cron job configured"
}

# Display deployment information
show_info() {
    log "Deployment completed successfully!"
    echo
    echo "=== Service URLs ==="
    echo "🌐 Web Manager: http://localhost:9000"
    echo "🔗 Node.js API: http://localhost:3000"
    echo "🐍 Python Service: http://localhost:8000"
    echo "📊 Grafana: http://localhost:3001 (admin/admin123)"
    echo "📈 Prometheus: http://localhost:9090"
    echo
    echo "=== Useful Commands ==="
    echo "📋 View logs: docker-compose logs -f"
    echo "🔄 Restart services: docker-compose restart"
    echo "🛑 Stop services: docker-compose down"
    echo "📊 Check status: docker-compose ps"
    echo "🔧 Scale services: docker-compose up -d --scale node-service=3"
    echo
    echo "=== Configuration Files ==="
    echo "⚙️ Environment: .env"
    echo "🐳 Docker Compose: docker-compose.yml"
    echo "🔐 SSL: ssl/ directory"
    echo "💾 Backups: backups/ directory"
    echo
    success "Telegram Query Bridge is now running in production mode!"
}

# Main deployment function
main() {
    log "Starting Telegram Query Bridge deployment..."
    
    check_root
    check_docker
    check_env
    create_directories
    set_permissions
    build_images
    start_services
    wait_for_services
    setup_ssl
    setup_monitoring
    setup_backup
    show_info
}

# Handle script arguments
case "${1:-}" in
    "build")
        build_images
        ;;
    "start")
        start_services
        ;;
    "stop")
        docker-compose down
        ;;
    "restart")
        docker-compose restart
        ;;
    "logs")
        docker-compose logs -f
        ;;
    "status")
        docker-compose ps
        ;;
    "backup")
        ./backup.sh
        ;;
    *)
        main
        ;;
esac
