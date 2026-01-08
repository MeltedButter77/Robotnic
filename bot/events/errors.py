import discord


async def on_application_command_error(self, ctx, exception):
    if isinstance(exception.original, discord.Forbidden):
        await ctx.send("I require more permissions.")
    else:
        self.logger.error(f"ERROR in {__name__}\nContext: {ctx}\nException: {exception}")
        await ctx.send("Error, check logs. Type: on_application_command_error")