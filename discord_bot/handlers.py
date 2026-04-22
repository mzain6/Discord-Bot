import discord

async def ensure_job_channel(guild, channel_name, create=False):
    """Gets the target job channel by name, creating it if requested."""
    for channel in guild.text_channels:
        if channel.name == channel_name:
            return channel
            
    if create:
        try:
            new_channel = await guild.create_text_channel(channel_name)
            return new_channel
        except discord.errors.Forbidden:
            print(f"Missing permissions to create channel '{channel_name}' in '{guild.name}'")
            return None
    return None

async def post_job_to_channels(channel, summary_msg):
    """Posts the formatted job summary to the channel and returns the message object."""
    return await channel.send(summary_msg)

async def create_job_thread(message, title, auto_archive_duration=60):
    """Creates a thread from the provided message."""
    thread = await message.create_thread(
        name=title,
        auto_archive_duration=auto_archive_duration
    )
    return thread

async def post_thread_details(thread, details_msg):
    """Posts full job details inside the newly created thread."""
    await thread.send(details_msg)
