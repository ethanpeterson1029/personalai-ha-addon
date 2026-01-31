#!/usr/bin/env python3
"""
Personal AI Home Agent
Home Assistant Add-on version

Connects to Personal AI server via WebSocket and proxies commands to local HA.
"""

import asyncio
import aiohttp
import argparse
import os
import sys
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Configure logging for HA addon
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',  # Simple format for HA logs
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

VERSION = "1.0.0"

# Safe domains
SAFE_DOMAINS = {
    "light", "switch", "climate", "cover", "lock",
    "fan", "media_player", "scene", "vacuum", "input_boolean",
    "alarm_control_panel", "humidifier", "water_heater", "script",
    "automation", "input_select", "input_number", "input_text"
}


class HomeAgent:
    def __init__(
        self,
        server_url: str,
        agent_token: str,
        ha_url: str,
        ha_token: str,
        reconnect_delay: int = 5
    ):
        self.server_url = server_url.rstrip("/")
        self.agent_token = agent_token
        self.ha_url = ha_url.rstrip("/")
        self.ha_token = ha_token
        self.reconnect_delay = reconnect_delay
        
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False
        self._connected = False
    
    async def start(self):
        self._running = True
        self._session = aiohttp.ClientSession()
        
        logger.info("=" * 40)
        logger.info("Personal AI Agent v%s", VERSION)
        logger.info("=" * 40)
        
        # Test HA connection
        if not await self._test_ha_connection():
            logger.error("Cannot connect to Home Assistant")
            logger.error("This usually resolves itself - retrying...")
            await asyncio.sleep(10)
        
        # Main reconnection loop
        while self._running:
            try:
                await self._connect()
            except Exception as e:
                logger.error("Connection error: %s", e)
            
            if self._running:
                logger.info("Reconnecting in %ds...", self.reconnect_delay)
                await asyncio.sleep(self.reconnect_delay)
        
        await self._cleanup()
    
    async def stop(self):
        self._running = False
        if self._ws and not self._ws.closed:
            await self._ws.close()
    
    async def _cleanup(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _test_ha_connection(self) -> bool:
        try:
            async with self._session.get(
                f"{self.ha_url}/api/",
                headers={"Authorization": f"Bearer {self.ha_token}"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info("✓ Home Assistant %s", data.get('version', 'connected'))
                    return True
                logger.warning("HA returned status %d", resp.status)
                return False
        except Exception as e:
            logger.warning("HA test failed: %s", e)
            return False
    
    async def _connect(self):
        ws_url = f"{self.server_url}/api/v1/agent/ws?token={self.agent_token}"
        ws_url = ws_url.replace("https://", "wss://").replace("http://", "ws://")
        
        logger.info("Connecting to Personal AI...")
        
        try:
            self._ws = await self._session.ws_connect(
                ws_url,
                heartbeat=30,
                receive_timeout=60
            )
            
            # Handshake
            await self._ws.send_json({
                "type": "handshake",
                "agent_version": VERSION,
                "ha_url": "local"  # Don't expose internal URL
            })
            
            msg = await self._ws.receive_json()
            if msg.get("type") == "welcome":
                logger.info("✓ Connected to Personal AI!")
                self._connected = True
            else:
                logger.error("Unexpected response: %s", msg)
                return
            
            ping_task = asyncio.create_task(self._ping_loop())
            
            try:
                await self._message_loop()
            finally:
                ping_task.cancel()
                self._connected = False
                
        except aiohttp.WSServerHandshakeError as e:
            logger.error("Connection rejected: %s", e)
            if "4001" in str(e):
                logger.error("Invalid token - check your agent token in add-on config")
        except Exception as e:
            logger.error("WebSocket error: %s", e)
    
    async def _ping_loop(self):
        while self._connected:
            try:
                await self._ws.send_json({"type": "ping"})
                await asyncio.sleep(30)
            except:
                break
    
    async def _message_loop(self):
        async for msg in self._ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    pass
            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED):
                break
    
    async def _handle_message(self, data: Dict[str, Any]):
        msg_type = data.get("type")
        
        if msg_type == "pong":
            pass
        elif msg_type == "ha_command":
            request_id = data.get("request_id")
            command = data.get("command", {})
            
            logger.info("Command: %s", command.get('action', 'unknown'))
            result = await self._execute_ha_command(command)
            
            await self._ws.send_json({
                "type": "ha_response",
                "request_id": request_id,
                "result": result
            })
    
    async def _execute_ha_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        action = command.get("action")
        
        try:
            if action == "get_entities":
                return await self._get_all_entities()
            elif action == "get_state":
                return await self._get_entity_state(command.get("entity_id"))
            elif action == "call_service":
                domain = command.get("domain")
                service = command.get("service")
                
                if domain not in SAFE_DOMAINS:
                    return {"success": False, "error": f"Domain '{domain}' not allowed"}
                
                return await self._call_service(
                    domain, service,
                    command.get("entity_id"),
                    command.get("data", {})
                )
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error("Command error: %s", e)
            return {"success": False, "error": str(e)}
    
    async def _get_all_entities(self) -> Dict[str, Any]:
        try:
            async with self._session.get(
                f"{self.ha_url}/api/states",
                headers={"Authorization": f"Bearer {self.ha_token}"}
            ) as resp:
                if resp.status == 200:
                    states = await resp.json()
                    entities = {}
                    for entity in states:
                        entity_id = entity.get("entity_id", "")
                        if "." not in entity_id:
                            continue
                        domain = entity_id.split(".")[0]
                        if domain not in entities:
                            entities[domain] = []
                        entities[domain].append({
                            "entity_id": entity_id,
                            "state": entity.get("state"),
                            "name": entity.get("attributes", {}).get("friendly_name", entity_id)
                        })
                    return {"success": True, "entities": entities}
                return {"success": False, "error": f"HA returned {resp.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_entity_state(self, entity_id: str) -> Dict[str, Any]:
        try:
            async with self._session.get(
                f"{self.ha_url}/api/states/{entity_id}",
                headers={"Authorization": f"Bearer {self.ha_token}"}
            ) as resp:
                if resp.status == 200:
                    return {"success": True, "state": await resp.json()}
                return {"success": False, "error": f"HA returned {resp.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _call_service(self, domain: str, service: str, entity_id: Optional[str], data: Dict) -> Dict[str, Any]:
        try:
            service_data = {}
            if entity_id:
                service_data["entity_id"] = entity_id
            service_data.update(data)
            
            async with self._session.post(
                f"{self.ha_url}/api/services/{domain}/{service}",
                headers={
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                },
                json=service_data
            ) as resp:
                if resp.status == 200:
                    return {"success": True, "message": f"Called {domain}.{service}"}
                return {"success": False, "error": f"HA returned {resp.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--ha-url", required=True)
    parser.add_argument("--ha-token", required=True)
    args = parser.parse_args()
    
    agent = HomeAgent(
        server_url=args.server,
        agent_token=args.token,
        ha_url=args.ha_url,
        ha_token=args.ha_token
    )
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
