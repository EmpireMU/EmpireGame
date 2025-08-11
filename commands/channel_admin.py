"""
Channel administration commands.

Commands for managing channel settings like colours, descriptions, etc.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia import CmdSet
from evennia import search_object
from evennia.comms.models import ChannelDB


class CmdChannelColour(MuxCommand):
    """
    Set the colour of a channel name.
    
    Usage:
        channelcolour <channel>=<colour>
        channelcolour <channel>              - View current colour
        channelcolour/list                   - List all channels and their colours
        channelcolour/reset <channel>        - Reset channel to default white colour
        
    Colour codes:
        r - bright red          R - dark red
        g - bright green        G - dark green  
        b - bright blue         B - dark blue
        c - bright cyan         C - dark cyan
        y - bright yellow       Y - dark yellow
        m - bright magenta      M - dark magenta
        w - bright white        W - dark white (grey)
        x - black               X - dark grey
        
    Examples:
        channelcolour public=g               - Make public channel green
        channelcolour ooc=c                  - Make OOC channel cyan  
        channelcolour gossip=y               - Make gossip channel yellow
        channelcolour public                 - View public channel's current colour
        channelcolour/list                   - List all channels and colours
        channelcolour/reset public           - Reset public to default white
        
    Only administrators can modify channel colours.
    """
    
    key = "channelcolour"
    aliases = ["chcolour", "channelcolor", "chcolor"]
    locks = "cmd:perm(Admin)"
    help_category = "Channels"
    switch_options = ("list", "reset")
    
    def func(self):
        """Execute the command."""
        if "list" in self.switches:
            self.list_channel_colours()
            return
            
        if "reset" in self.switches:
            self.reset_channel_colour()
            return
            
        if not self.args:
            self.msg("Usage: channelcolour <channel>=<colour> or channelcolour/list")
            return
            
        if "=" in self.args:
            # Setting a colour
            channel_name, colour_code = [part.strip() for part in self.args.split("=", 1)]
            self.set_channel_colour(channel_name, colour_code)
        else:
            # Viewing current colour
            self.view_channel_colour(self.args.strip())
    
    def set_channel_colour(self, channel_name, colour_code):
        """Set the colour for a channel."""
        # Find the channel
        channels = ChannelDB.objects.filter(db_key__iexact=channel_name)
        if not channels:
            self.msg(f"Channel '{channel_name}' not found.")
            return
        channel = channels[0]
            
        # Validate and set the colour
        if channel.set_channel_colour(colour_code):
            # Show a preview of what the channel name will look like
            preview = channel.channel_prefix().rstrip()
            self.msg(f"Set {channel.key} channel colour to '{colour_code}'. Preview: {preview}")
            
            # Notify channel subscribers if they're online
            try:
                online_subscribers = [sub for sub in channel.subscriptions.all() 
                                    if hasattr(sub, 'sessions') and sub.sessions.count()]
                if online_subscribers:
                    notification = f"Channel colour changed to: {preview}"
                    channel.msg(notification, senders=[self.caller])
            except AttributeError:
                # Some channel types may not support subscription notifications
                pass
        else:
            self.msg(f"Invalid colour code '{colour_code}'. Use: r, g, b, c, y, m, w, x (bright) or R, G, B, C, Y, M, W, X (dark)")
    
    def view_channel_colour(self, channel_name):
        """View the current colour of a channel."""
        channels = ChannelDB.objects.filter(db_key__iexact=channel_name)
        if not channels:
            self.msg(f"Channel '{channel_name}' not found.")
            return
        channel = channels[0]
            
        colour_code = channel.get_channel_colour()
        preview = channel.channel_prefix().rstrip()
        self.msg(f"Channel '{channel.key}' colour: '{colour_code}' - Preview: {preview}")
    
    def reset_channel_colour(self):
        """Reset a channel to default white colour."""
        if not self.args:
            self.msg("Usage: channelcolour/reset <channel>")
            return
            
        channel_name = self.args.strip()
        channels = ChannelDB.objects.filter(db_key__iexact=channel_name)
        if not channels:
            self.msg(f"Channel '{channel_name}' not found.")
            return
        channel = channels[0]
            
        channel.set_channel_colour("w")
        preview = channel.channel_prefix().rstrip()
        self.msg(f"Reset {channel.key} channel colour to default white. Preview: {preview}")
    
    def list_channel_colours(self):
        """List all channels and their current colours."""
        from evennia.utils.evtable import EvTable
        
        channels = ChannelDB.objects.all()
        if not channels:
            self.msg("No channels found.")
            return
            
        table = EvTable("|wChannel|n", "|wColour Code|n", "|wPreview|n", 
                       border="header", align="l")
        
        for channel in channels:
            colour_code = channel.get_channel_colour()
            preview = channel.channel_prefix().rstrip()
            table.add_row(channel.key, colour_code, preview)
            
        self.msg("|wChannel Colours:|n")
        self.msg(str(table))
        
        # Show colour reference
        self.msg("\n|wColour Reference:|n")
        self.msg("r=|rbright red|n, g=|gbright green|n, b=|bbright blue|n, c=|cbright cyan|n, y=|ybright yellow|n, m=|mbright magenta|n, w=|wbright white|n, x=|xblack|n")
        self.msg("Uppercase versions (R,G,B,C,Y,M,W,X) are darker variants.")


class ChannelAdminCmdSet(CmdSet):
    """
    Command set for channel administration.
    """
    
    key = "ChannelAdmin"
    
    def at_cmdset_creation(self):
        """Add channel admin commands."""
        self.add(CmdChannelColour()) 