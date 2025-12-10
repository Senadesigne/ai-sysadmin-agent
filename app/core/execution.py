import asyncio
import logging
import re
from typing import Optional, Tuple

# Attempt imports, but anticipate missing dependencies if user hasn't installed them yet
try:
    import asyncssh
    HAS_ASYNCSSH = True
except ImportError:
    HAS_ASYNCSSH = False

try:
    from netmiko import ConnectHandler
    HAS_NETMIKO = True
except ImportError:
    HAS_NETMIKO = False

logger = logging.getLogger(__name__)

# Security: List of dangerous commands to block
BLACKLISTED_COMMANDS = [
    r"rm\s+-rf",
    r"mkfs",
    r"dd\s+if=",
    r":(){:|:&};:",  # Fork bomb
    r">\s*/dev/sda",
    r"mv\s+/*\s+/dev/null",
    r"shutdown",
    r"reboot",
    r"init\s+0",
]

def validate_command(command: str) -> Tuple[bool, str]:
    """
    Validates if a command is safe to execute.
    Returns (is_safe, reason).
    """
    if not command or not command.strip():
        return False, "Empty command"

    for pattern in BLACKLISTED_COMMANDS:
        if re.search(pattern, command):
            return False, f"Command contains blacklisted pattern: {pattern}"

    return True, "Safe"

class ConnectionManager:
    """
    Manages connections to remote servers via SSH (Linux) or Netmiko (Network).
    """
    
    def __init__(self, private_key_path: str = None):
        self.private_key_path = private_key_path

    async def execute_ssh_command(self, 
                                host: str, 
                                username: str, 
                                command: str, 
                                port: int = 22) -> str:
        """
        Executes a command on a Linux server using asyncssh.
        """
        if not HAS_ASYNCSSH:
            return "Error: asyncssh library is not installed."
            
        is_safe, reason = validate_command(command)
        if not is_safe:
            raise ValueError(f"Security Alert: {reason}")

        try:
            async with asyncssh.connect(host, username=username, port=port, client_keys=[self.private_key_path], known_hosts=None) as conn:
                result = await conn.run(command)
                if result.exit_status != 0:
                    return f"Error (Exit Code {result.exit_status}):\n{result.stderr}"
                return result.stdout
        except Exception as e:
            logger.error(f"SSH Connection failed: {e}")
            return f"Connection Failed: {str(e)}"

    async def execute_netmiko_command(self, 
                                    host: str, 
                                    username: str, 
                                    command: str, 
                                    device_type: str = 'cisco_ios',
                                    port: int = 22) -> str:
        """
        Executes a command on network devices using Netmiko.
        """
        if not HAS_NETMIKO:
            return "Error: Netmiko library is not installed."

        is_safe, reason = validate_command(command)
        if not is_safe:
            raise ValueError(f"Security Alert: {reason}")
            
        # Netmiko is blocking, so we run it in a thread executor
        def _run_netmiko():
            try:
                # Note: Netmiko usually requires a password or key. 
                # Integrating with key might depend on device support.
                # Use use_keys=True and key_file
                connection_params = {
                    'device_type': device_type,
                    'host': host,
                    'username': username,
                    'port': port,
                    'use_keys': True,
                    'key_file': self.private_key_path,
                    # 'ssh_config_file': '~/.ssh/config', # Optional
                }
                
                with ConnectHandler(**connection_params) as net_connect:
                    return net_connect.send_command(command)
            except Exception as e:
                return f"Netmiko Failed: {str(e)}"

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _run_netmiko)

    async def execute(self, device, command: str) -> str:
        """
        Main entry point. Dispatches based on device OS family.
        """
        if not self.private_key_path:
             return "Error: SSH Private Key not configured."

        if device.os_family == 'linux':
            return await self.execute_ssh_command(
                host=device.ip_address,
                username=device.ssh_user,
                port=device.ssh_port,
                command=command
            )
        elif device.os_family in ['network_ios', 'cisco_ios', 'junos']:
             return await self.execute_netmiko_command(
                host=device.ip_address,
                username=device.ssh_user,
                port=device.ssh_port,
                command=command,
                device_type='cisco_ios' # Defaulting to cisco_ios for now, map properly later
            )
        else:
            return f"Unsupported OS Family: {device.os_family}"
