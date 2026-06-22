#!/bin/bash

# Auth Service Driver - Smoke test and interaction harness
# This script verifies the auth-service is running and performs basic operations

set -e

API_URL="${API_URL:-http://localhost:3000}"
VERBOSE="${VERBOSE:-0}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
  echo -e "${BLUE}[driver]${NC} $1"
}

success() {
  echo -e "${GREEN}✓${NC} $1"
}

error() {
  echo -e "${RED}✗${NC} $1"
  return 1
}

warn() {
  echo -e "${YELLOW}⚠${NC} $1"
}

# Check if service is running
health_check() {
  log "Checking service health..."

  if response=$(curl -s -w "\n%{http_code}" "${API_URL}/health"); then
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
      success "Service is healthy (200)"
      [ "$VERBOSE" = "1" ] && echo "  Response: $body"
      return 0
    else
      error "Service returned HTTP $http_code"
      return 1
    fi
  else
    error "Could not reach service at $API_URL"
    return 1
  fi
}

# Test successful login
test_login_success() {
  log "Testing successful login..."

  response=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/login" \
    -H "Content-Type: application/json" \
    -d '{"email": "test@test.com", "password": "password123"}')

  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)

  if [ "$http_code" = "200" ] && echo "$body" | grep -q '"success":true'; then
    success "Login successful - returned 200 with success:true"
    [ "$VERBOSE" = "1" ] && echo "  Response: $body"
    return 0
  else
    error "Login failed - HTTP $http_code: $body"
    return 1
  fi
}

# Test blocked user
test_blocked_user() {
  log "Testing blocked user scenario..."

  response=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/login" \
    -H "Content-Type: application/json" \
    -d '{"email": "blocked@test.com", "password": "password123"}')

  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)

  if [ "$http_code" = "403" ] && echo "$body" | grep -q "blocked"; then
    success "Blocked user correctly returns 403"
    [ "$VERBOSE" = "1" ] && echo "  Response: $body"
    return 0
  else
    error "Blocked user scenario failed - HTTP $http_code: $body"
    return 1
  fi
}

# Test invalid password
test_invalid_password() {
  log "Testing invalid password..."

  response=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/login" \
    -H "Content-Type: application/json" \
    -d '{"email": "test@test.com", "password": "wrongpassword"}')

  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)

  if [ "$http_code" = "401" ] && echo "$body" | grep -q "Invalid"; then
    success "Invalid password correctly returns 401"
    [ "$VERBOSE" = "1" ] && echo "  Response: $body"
    return 0
  else
    error "Invalid password scenario failed - HTTP $http_code: $body"
    return 1
  fi
}

# Test missing credentials
test_missing_credentials() {
  log "Testing missing credentials..."

  response=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/login" \
    -H "Content-Type: application/json" \
    -d '{"email": "test@test.com"}')

  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)

  if [ "$http_code" = "400" ] && echo "$body" | grep -q "required"; then
    success "Missing credentials correctly returns 400"
    [ "$VERBOSE" = "1" ] && echo "  Response: $body"
    return 0
  else
    error "Missing credentials scenario failed - HTTP $http_code: $body"
    return 1
  fi
}

# Show logs from container
show_logs() {
  log "Last 10 log entries from container:"
  docker exec auth-service tail -10 logs/app.log 2>/dev/null || warn "Could not read logs from container"
}

# Break a user (block them)
break_user() {
  local email="${1:-test@test.com}"
  log "Breaking user: $email"

  if docker exec auth-service npm run break-user "$email" > /dev/null 2>&1; then
    success "User $email blocked"
    return 0
  else
    error "Could not block user $email"
    return 1
  fi
}

# Restore a user
restore_user() {
  local email="${1:-test@test.com}"
  log "Restoring user: $email"

  if docker exec auth-service npm run restore-user "$email" > /dev/null 2>&1; then
    success "User $email restored"
    return 0
  else
    error "Could not restore user $email"
    return 1
  fi
}

# Parse arguments and run commands
case "${1:-smoke}" in
  smoke)
    # Run all smoke tests
    log "Running smoke test suite..."
    if health_check && \
       test_login_success && \
       test_blocked_user && \
       test_invalid_password && \
       test_missing_credentials; then
      success "All smoke tests passed!"
      exit 0
    else
      error "Some tests failed"
      exit 1
    fi
    ;;
  health)
    health_check
    ;;
  login)
    # Test login with optional email/password
    email="${2:-test@test.com}"
    password="${3:-password123}"
    log "Testing login with $email..."
    response=$(curl -s -X POST "${API_URL}/login" \
      -H "Content-Type: application/json" \
      -d "{\"email\": \"$email\", \"password\": \"$password\"}")
    echo "$response"
    ;;
  logs)
    show_logs
    ;;
  break)
    break_user "${2:-test@test.com}"
    ;;
  restore)
    restore_user "${2:-test@test.com}"
    ;;
  verbose)
    # Re-run smoke tests with verbose output
    VERBOSE=1 "$0" smoke
    ;;
  *)
    echo "Auth Service Driver"
    echo ""
    echo "Usage: driver.sh [command] [args]"
    echo ""
    echo "Commands:"
    echo "  smoke              - Run all smoke tests (default)"
    echo "  health             - Check service health"
    echo "  login [email] [pw] - Test login with credentials"
    echo "  logs               - Show recent container logs"
    echo "  break [email]      - Block a user"
    echo "  restore [email]    - Restore a user"
    echo "  verbose            - Run smoke tests with verbose output"
    echo ""
    echo "Examples:"
    echo "  driver.sh smoke"
    echo "  driver.sh login admin@test.com adminpass"
    echo "  driver.sh break test@test.com"
    exit 1
    ;;
esac
