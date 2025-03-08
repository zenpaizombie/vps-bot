import os
import subprocess
import asyncio
import discord
from discord.ext import commands

# Configuration
ALLOWED_CHANNEL_IDS = [123456789012345678]  # Replace with your allowed channel IDs
ALLOWED_ROLE_IDS = [987654321098765432]     # Replace with your allowed role IDs
TOKEN = "YOUR_DISCORD_BOT_TOKEN"            # Replace with your Discord bot token

# Supported OS options
SUPPORTED_OS = {
    "ubuntu": "https://releases.ubuntu.com/22.04/ubuntu-22.04.3-live-server-amd64.iso",
    "debian": "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-12.1.0-amd64-netinst.iso",
    "centos": "http://isoredirect.centos.org/centos/7/isos/x86_64/CentOS-7-x86_64-DVD-2009.iso",
    "fedora": "https://download.fedoraproject.org/pub/fedora/linux/releases/38/Server/x86_64/iso/Fedora-Server-dvd-x86_64-38-1.6.iso",
}

# Track VPS instances
vps_instances = {}

# Initialize the bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

def fake_neofetch(os_name: str, ram: int, cpu: int):
    """
    Generates a fake neofetch output with custom RAM and CPU values.
    """
    return f"""
    OS: {os_name.capitalize()}
    Host: Fake VPS
    Kernel: 6.2.0-36-generic
    Uptime: 0 min
    CPU: Fake CPU ({cpu} cores)
    Memory: {ram}MB / {ram}MB
    """

def generate_tmate_session():
    """
    Creates a Docker container and sets up a tmate SSH session inside it.
    Returns the SSH connection string.
    """
    print("Creating Docker container...")

    container_name = "vps_container"

    try:
        # Pull Ubuntu image if not available
        subprocess.run(["docker", "pull", "ubuntu"], check=True)

        # Remove existing container if it exists
        subprocess.run(["docker", "rm", "-f", container_name], check=False)

        # Run a new Ubuntu container in detached mode with tmate installed
        subprocess.run(
            ["docker", "run", "-d", "--name", container_name, "--privileged", "ubuntu", "sleep", "infinity"],
            check=True
        )

        # Install tmate inside the container
        subprocess.run(
            ["docker", "exec", container_name", "apt", "update"], check=True
        )
        subprocess.run(
            ["docker", "exec", container_name, "apt", "install", "-y", "tmate"], check=True
        )

        # Start tmate session inside the container
        subprocess.run(
            ["docker", "exec", "-d", container_name, "tmate", "-S", "/tmp/tmate.sock", "new-session", "-d"],
            check=True
        )
        subprocess.run(
            ["docker", "exec", container_name, "tmate", "-S", "/tmp/tmate.sock", "wait", "tmate-ready"],
            check=True
        )

        # Retrieve SSH connection
        result = subprocess.run(
            ["docker", "exec", container_name, "tmate", "-S", "/tmp/tmate.sock", "display", "-p", "#{tmate_ssh}"],
            capture_output=True, text=True, check=True
        )

        ssh_connection = result.stdout.strip()
        return ssh_connection if ssh_connection else "❌ Failed to retrieve tmate SSH session."

    except subprocess.CalledProcessError as e:
        return f"❌ Docker/tmate error: {e}"

async def cleanup_vps(vps_id: int, timeout: int):
    """
    Function to automatically delete a VPS after a specified timeout.
    """
    await asyncio.sleep(timeout)
    if vps_id in vps_instances:
        vps_instances[vps_id].terminate()
        del vps_instances[vps_id]
        print(f"VPS {vps_id} has been deleted.")

@bot.event
async def on_ready():
    print(f"Bot is ready. Logged in as {bot.user}")

@bot.command(name="deploy")
async def deploy_vps(ctx, os_name: str, ram: int, cpu: int, timeout: int = None):
    """
    Discord command to deploy a VPS.
    """
    if ctx.channel.id not in ALLOWED_CHANNEL_IDS:
        await ctx.send("❌ This command is not allowed in this channel.")
        return

    if not any(role.id in ALLOWED_ROLE_IDS for role in ctx.author.roles):
        await ctx.send("❌ You do not have permission to use this command.")
        return

    if os_name not in SUPPORTED_OS:
        await ctx.send(f"❌ Unsupported OS. Available options: {', '.join(SUPPORTED_OS.keys())}")
        return

    if ram < 512 or ram > 16384:
        await ctx.send("❌ Invalid RAM amount. Please specify a value between 512 and 16384 MB.")
        return
    if cpu < 1 or cpu > 16:
        await ctx.send("❌ Invalid CPU count. Please specify a value between 1 and 16 cores.")
        return

    await ctx.send(f"🚀 Deploying VPS with OS: {os_name}, RAM: {ram}MB, CPU: {cpu} cores...")
    try:
        neofetch_output = fake_neofetch(os_name, ram, cpu)
        await ctx.send(f"```{neofetch_output}```")

        ssh_connection = generate_tmate_session()
        if "❌" in ssh_connection:
            await ctx.send(ssh_connection)
            return

        await ctx.author.send(f"🔑 Your VPS SSH connection:\n```{ssh_connection}```")
        await ctx.send("📩 Check your DMs for the SSH connection details!")

        if timeout:
            vps_id = len(vps_instances) + 1
            vps_instances[vps_id] = None  
            asyncio.create_task(cleanup_vps(vps_id, timeout))
            await ctx.send(f"⏳ VPS {vps_id} will be deleted in {timeout} seconds.")
    except Exception as e:
        await ctx.send(f"❌ Failed to deploy VPS: {e}")

@bot.command(name="status")
async def vps_status(ctx, vps_id: int):
    """
    Discord command to check the status of a VPS.
    """
    if vps_id not in vps_instances:
        await ctx.send(f"❌ VPS {vps_id} not found.")
        return

    await ctx.send(f"✅ VPS {vps_id} is running.")

if __name__ == "__main__":
    bot.run(TOKEN)
