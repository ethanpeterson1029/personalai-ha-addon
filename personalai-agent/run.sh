#!/usr/bin/with-contenv bashio
# ==============================================================================
# Personal AI Agent - Home Assistant Add-on
# Connects your HA to Personal AI cloud service
# ==============================================================================

# Get config values
SERVER_URL=$(bashio::config 'server_url')
AGENT_TOKEN=$(bashio::config 'agent_token')

# Get HA supervisor token (automatically provided by HA)
HA_TOKEN="${SUPERVISOR_TOKEN}"
HA_URL="http://supervisor/core"

bashio::log.info "Starting Personal AI Agent..."
bashio::log.info "Server: ${SERVER_URL}"
bashio::log.info "Home Assistant: ${HA_URL}"

# Validate config
if [ -z "${AGENT_TOKEN}" ]; then
    bashio::log.error "Agent token not configured!"
    bashio::log.error "Get your token from Personal AI → Settings → Home Assistant"
    exit 1
fi

# Run the agent
exec python3 /agent.py \
    --server "${SERVER_URL}" \
    --token "${AGENT_TOKEN}" \
    --ha-url "${HA_URL}" \
    --ha-token "${HA_TOKEN}"
