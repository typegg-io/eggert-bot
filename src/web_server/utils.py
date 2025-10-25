import asyncio

import discord

from utils.logging import log


def get_nwpm_role_name(nwpm):
    """Get the role name for a given nWPM value."""
    if nwpm is None:
        return None
    if nwpm >= 250:
        return "250+"
    lower_bound = int((nwpm // 10) * 10)
    upper_bound = lower_bound + 9
    return f"{lower_bound}-{upper_bound}"


async def update_nwpm_role(self, guild: discord.Guild, discord_id: int, nwpm: float):
    """Update a given user's nWPM role."""
    member = guild.get_member(discord_id)
    if not member:
        return

    role_name = self.get_nwpm_role_name(nwpm)
    if not role_name:
        return

    new_role = discord.utils.get(guild.roles, name=role_name)
    current_roles = [role for role in member.roles if role in self.nwpm_roles]

    if len(current_roles) == 1 and current_roles[0] == new_role:
        return

    if current_roles:
        await member.remove_roles(*current_roles, reason="Updating nWPM role")
        await asyncio.sleep(0.5)

    await member.add_roles(new_role, reason="Assigning nWPM role")
    log(f"Assigned {role_name} role to {member.name}")
    await asyncio.sleep(1)
