"""
Commands for the bulletin board system.

This module contains commands for interacting with the bulletin board system,
allowing characters to read and post messages on various boards.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia.utils.evtable import EvTable
from evennia.utils.utils import list_to_string
from evennia.utils.search import search_script
from evennia import create_script
from evennia.locks.lockhandler import LockException
from typeclasses.boards import BulletinBoardScript
from evennia.utils import logger
from evennia.scripts.models import ScriptDB

def find_board(board_name, debug_to=None):
    """Helper function to find a board by name, case-insensitive."""
    # Try direct script search first
    boards = search_script(board_name, typeclass=BulletinBoardScript)
        
    if boards:
        return boards[0]

    # No direct match - fall back to case-insensitive lookup via ScriptDB
    db_board = ScriptDB.objects.filter(
        db_typeclass_path="typeclasses.boards.BulletinBoardScript",
        db_key__iexact=board_name
    ).first()
    return db_board

class CmdBoard(MuxCommand):
    """
    |cBulletin Board System|n
    
    Usage:
        |wboard|n - List your subscribed boards
        |wboard/all|n - List all available boards
        |wboard <board>|n - View posts on a specific board
        |wboard <board>/<post #>|n - Read a specific post
        |wboard/post <board>=<title>/<text>|n - Create a new post
        |wboard/edit <board>/<post #>=<text>|n - Edit a post
        |wboard/delete <board>/<post #>|n - Delete a post
        |wboard/search <text>|n - Search posts
        |wboard/archive <board>|n - View archived posts on a board
        |wboard/sub <board>|n - Subscribe to a board
        |wboard/unsub <board>|n - Unsubscribe from a board
        |wboard/markread <board>|n - Mark all posts on a board as read
        
    Examples:
        board
        board/all
        board announcements
        board announce/1
        board/post announce=Welcome!/Welcome to the game!
        board/sub announce
        board/markread announce
    """
    
    key = "board"
    aliases = ["boards", "bb", "bbs"]
    locks = "cmd:all()"
    help_category = "Communication"
    
    def get_help(self, caller, cmdset):
        """
        Return help text, customized based on caller's permissions.
        
        Args:
            caller: The object requesting help
            cmdset: The cmdset this command belongs to
            
        Returns:
            str: The help text
        """
        # Get base help text from docstring
        help_text = super().get_help(caller, cmdset)
        
        # Add admin commands if caller has Admin permissions
        if caller.check_permstring("Admin"):
            help_text += """
    
    |yAdmin Commands:|n
        |wboard/pin <board>/<post #>|n - Pin a post to the top
        |wboard/unpin <board>/<post #>|n - Unpin a post
        |wboard/new <name>|n - Create a new board
        |wboard/config <board>=<lockstring>|n - Configure board permissions
        |wboard/destroy <board>|n - Delete a board
        |wboard/access <board>/<type>=<lockstring>|n - Set board access rules
        
    Access Types for /access:
        read - Who can read posts
        write - Who can make posts
        admin - Who can manage the board
        
    Admin Examples:
        board/pin announce/5
        board/new announcements
        board/config announce=read:all();write:perm(Builder)
        board/access announce/read=all()
        board/access announce/write=perm(Builder)
        board/destroy oldboard
            """
        
        return help_text
    
    def func(self):
        """Handle board commands."""
        caller = self.caller
        
        if not self.args and not self.switches:
            # List subscribed boards by default
            boards = ScriptDB.objects.filter(db_typeclass_path="typeclasses.boards.BulletinBoardScript")
            subscribed = [b for b in boards if caller in b.db.subscribers]
            
            if not subscribed:
                caller.msg("You are not subscribed to any boards. Use |wboard/all|n to see all available boards.")
                return
                
            table = EvTable("|wBoard|n", "|wUnread|n", "|wLatest Post|n", align="l", width=78)
            for board in subscribed:
                # Use cached summary for performance
                summary = board.get_cached_summary(caller)
                if summary:
                    unread = summary["unread"]
                    unread_str = f"|g{unread}|n" if unread > 0 else "-"
                    latest = summary["latest"]
                    table.add_row(board.key, unread_str, latest)
            caller.msg("|wYour Subscribed Boards:|n")
            caller.msg(str(table))
            return
        
        if "all" in self.switches:
            # List all boards
            boards = ScriptDB.objects.filter(db_typeclass_path="typeclasses.boards.BulletinBoardScript")
            boards = list(boards)  # Convert QuerySet to list
            
            if not boards:
                caller.msg("No bulletin boards have been created yet.")
                return
                
            table = EvTable("|wBoard|n", "|wUnread|n", "|wLatest Post|n", align="l", width=78)
            for board in boards:
                if board.access(caller, "read"):
                    # Use cached summary for performance
                    summary = board.get_cached_summary(caller)
                    if summary:
                        unread = summary["unread"]
                        unread_str = f"|g{unread}|n" if unread > 0 else "-"
                        latest = summary["latest"]
                        table.add_row(board.key, unread_str, latest)
            caller.msg("|wAll Available Boards:|n")
            caller.msg(str(table))
            return
            
        if not self.switches:
            # Reading a board or post
            if "/" in self.args:
                # Reading specific post
                board_name, post_num = self.args.split("/", 1)
                try:
                    post_num = int(post_num)
                except ValueError:
                    caller.msg("Post number must be a number.")
                    return
                    
                # Find board by name
                board = find_board(board_name)
                if not board:
                    caller.msg(f"Board '{board_name}' not found.")
                    return
                
                if not board.access(caller, "read"):
                    caller.msg("You don't have permission to read that board.")
                    return
                    
                posts = board.get_posts(caller)
                if not posts:
                    caller.msg("No posts found.")
                    return
                    
                if post_num < 1 or post_num > len(posts):
                    caller.msg("Invalid post number.")
                    return
                    
                post, is_unread = posts[post_num - 1]
                
                # Mark as read
                board.mark_read(caller, post)
                
                # Format post
                header = f"|wPost {post_num} on {board.key}|n"
                if hasattr(post, 'pinned') and post.pinned:
                    header = f"|y[PINNED]|n {header}"
                divider = "-" * len(header)
                caller.msg(f"{header}\n{divider}")
                caller.msg(f"|wTitle:|n {post.header}")
                caller.msg(f"|wPosted by:|n {post.senders[0].key}")
                caller.msg(f"|wDate:|n {post.date_created.strftime('%Y-%m-%d %H:%M')}")
                
                # Show edit info if post was edited
                if hasattr(post, 'last_edited') and post.last_edited:
                    edited_by = post.edited_by.key if hasattr(post, 'edited_by') and post.edited_by else "Unknown"
                    caller.msg(f"|wLast edited:|n {post.last_edited.strftime('%Y-%m-%d %H:%M')} by {edited_by}")
                    
                caller.msg(f"\n{post.message}")
                return
                
            else:
                # Viewing a board
                board = find_board(self.args)
                if not board:
                    caller.msg(f"Board '{self.args}' not found.")
                    return
                
                if not board.access(caller, "read"):
                    caller.msg("You don't have permission to read that board.")
                    return
                    
                # Check if we're viewing archived posts
                include_archived = "archive" in self.switches
                posts = board.get_posts(caller, include_archived)
                if not posts:
                    status = "archived" if include_archived else ""
                    caller.msg(f"No {status} posts found.")
                    return
                    
                table = EvTable(
                    "|w#|n", "|wTitle|n", "|wAuthor|n", "|wDate|n",
                    align="l", width=78
                )
                for i, (post, is_unread) in enumerate(posts, 1):
                    marker = "|g*|n " if is_unread else "  "
                    date = post.date_created.strftime("%Y-%m-%d")
                    flags = []
                    if hasattr(post, 'pinned') and post.pinned:
                        flags.append("|y[P]|n")
                    if hasattr(post, 'last_edited') and post.last_edited:
                        flags.append("|w[E]|n")
                    flag_str = " ".join(flags) + " " if flags else ""
                    table.add_row(
                        f"{i}",
                        f"{marker}{flag_str}{post.header}",
                        post.senders[0].key,
                        date
                    )
                header = f"Posts on {board.key}"
                if include_archived:
                    header = f"Archived {header}"
                divider = "-" * len(header)
                caller.msg(f"{header}\n{divider}")
                caller.msg(str(table))
                return
                
        elif "post" in self.switches:
            # Disallow guest accounts from posting
            if caller.account.is_typeclass("typeclasses.accounts.Guest"):
                caller.msg("Guest accounts cannot post to boards.")
                return
            if not self.args or "=" not in self.args:
                caller.msg("Usage: board/post <board>=<title>/<text>")
                return
                
            board_name, post_text = self.args.split("=", 1)
            if "/" not in post_text:
                caller.msg("Usage: board/post <board>=<title>/<text>")
                return
                
            title, text = post_text.split("/", 1)
            
            # Find board
            board = find_board(board_name)
            if not board:
                caller.msg(f"Board '{board_name}' not found.")
                return
            
            if not board.access(caller, "write"):
                caller.msg("You don't have permission to post on that board.")
                return
                
            post = board.create_post(caller, title.strip(), text.strip())
            if post:
                caller.msg("Posted successfully.")
            else:
                caller.msg("Failed to post message.")
                
        elif "edit" in self.switches:
            if not self.args or "=" not in self.args:
                caller.msg("Usage: board/edit <board>/<post #>=<text>")
                return
                
            post_ref, text = self.args.split("=", 1)
            if "/" not in post_ref:
                caller.msg("Usage: board/edit <board>/<post #>=<text>")
                return
                
            board_name, post_num = post_ref.split("/", 1)
            try:
                post_num = int(post_num)
            except ValueError:
                caller.msg("Post number must be a number.")
                return
                
            # Find board
            board = find_board(board_name)
            if not board:
                caller.msg(f"Board '{board_name}' not found.")
                return
            
            posts = board.get_posts(caller)
            if not posts:
                caller.msg("No posts found.")
                return
                
            if post_num < 1 or post_num > len(posts):
                caller.msg("Invalid post number.")
                return
                
            post, _ = posts[post_num - 1]
            
            if board.edit_post(caller, post, text.strip()):
                caller.msg("Post edited successfully.")
            else:
                caller.msg("You don't have permission to edit that post.")
                
        elif "new" in self.switches:
            if not caller.check_permstring("Developer"):
                caller.msg("Only developers can create new boards.")
                return
                
            if not self.args:
                caller.msg("Usage: board/new <name>")
                return
                
            board_name = self.args.strip()  # Don't force lowercase
            
            # Check if board exists
            existing = [b for b in search_script("", typeclass="typeclasses.boards.BulletinBoardScript") 
                       if b.key.lower() == board_name.lower()]
            if existing:
                caller.msg(f"A board named '{board_name}' already exists.")
                return
                
            try:
                board = create_script(
                    "typeclasses.boards.BulletinBoardScript",
                    key=board_name
                )
                
                if board:
                    board.save()
                    caller.msg(f"Created board '{board_name}'.")
                else:
                    caller.msg("Failed to create board.")
            except Exception as e:
                caller.msg(f"Error creating board: {e}")
                
        elif "config" in self.switches:
            if not caller.locks.check_lockstring(caller, "perm(Admin)"):
                caller.msg("You don't have permission to configure boards.")
                return
                
            if not self.args or "=" not in self.args:
                caller.msg("Usage: board/config <board>=<lockstring>")
                return
                
            board_name, lockstring = self.args.split("=", 1)
            board = find_board(board_name)
            if not board:
                caller.msg(f"Board '{board_name}' not found.")
                return
            
            try:
                board.locks.add(lockstring.strip())
                caller.msg("Lock(s) updated.")
            except LockException as e:
                caller.msg(f"Error setting lock: {str(e)}")
                
        elif "destroy" in self.switches:
            if not caller.check_permstring("Developer"):
                caller.msg("Only developers can destroy boards.")
                return
                
            board = find_board(self.args)
            if not board:
                caller.msg(f"Board '{self.args}' not found.")
                return
            
            board.delete()
            caller.msg(f"Deleted board '{self.args}'.")
            
        elif "delete" in self.switches:
            if not self.args or "/" not in self.args:
                caller.msg("Usage: board/delete <board>/<post #>")
                return
                
            board_name, post_num = self.args.split("/", 1)
            try:
                post_num = int(post_num)
            except ValueError:
                caller.msg("Post number must be a number.")
                return
                
            board = find_board(board_name)
            if not board:
                caller.msg(f"Board '{board_name}' not found.")
                return
            
            posts = board.get_posts(caller)
            if not posts:
                caller.msg("No posts found.")
                return
                
            if post_num < 1 or post_num > len(posts):
                caller.msg("Invalid post number.")
                return
                
            post, _ = posts[post_num - 1]
            
            if board.delete_post(caller, post):
                caller.msg("Post deleted.")
            else:
                caller.msg("You don't have permission to delete that post.")
                
        elif "pin" in self.switches or "unpin" in self.switches:
            if not self.args or "/" not in self.args:
                caller.msg("Usage: board/pin <board>/<post #>")
                return
                
            board_name, post_num = self.args.split("/", 1)
            try:
                post_num = int(post_num)
            except ValueError:
                caller.msg("Post number must be a number.")
                return
                
            boards = [b for b in search_script("", typeclass=BulletinBoardScript) if b.key == board_name]
            if not boards:
                caller.msg(f"Board '{board_name}' not found.")
                return
            board = boards[0]
            
            posts = board.get_posts(caller)
            if not posts:
                caller.msg("No posts found.")
                return
                
            if post_num < 1 or post_num > len(posts):
                caller.msg("Invalid post number.")
                return
                
            post, _ = posts[post_num - 1]
            pin = "pin" in self.switches
            if board.pin_post(caller, post, pin):
                action = "pinned" if pin else "unpinned"
                caller.msg(f"Post {action}.")
            else:
                caller.msg("You don't have permission to pin/unpin posts.")
                
        elif "search" in self.switches:
            if not self.args:
                caller.msg("Usage: board/search <text>")
                return
                
            search_text = self.args.lower()
            results = []
            
            # Search all boards the character can read
            for board in search_script("", typeclass=BulletinBoardScript):
                if board.access(caller, "read"):
                    for post, _ in board.get_posts(caller):
                        if (search_text in post.header.lower() or 
                            search_text in post.message.lower()):
                            results.append((board, post))
                            
            if not results:
                caller.msg("No matching posts found.")
                return
                
            table = EvTable(
                "|wBoard|n", "|wPost|n", "|wAuthor|n", "|wDate|n",
                align="l", width=78
            )
            for board, post in results:
                date = post.date_created.strftime("%Y-%m-%d")
                flags = []
                if hasattr(post, 'pinned') and post.pinned:
                    flags.append("|y[P]|n")
                if hasattr(post, 'last_edited') and post.last_edited:
                    flags.append("|w[E]|n")
                flag_str = " ".join(flags) + " " if flags else ""
                table.add_row(
                    board.key,
                    f"{flag_str}{post.header}",
                    post.senders[0].key,
                    date
                )
            caller.msg("|wSearch Results:|n")
            caller.msg(str(table))
            
        elif "sub" in self.switches:
            if not self.args:
                caller.msg("Usage: board/sub <board>")
                return
                
            boards = [b for b in search_script("", typeclass=BulletinBoardScript) if b.key == self.args]
            if not boards:
                caller.msg(f"Board '{self.args}' not found.")
                return
            board = boards[0]
            
            if board.subscribe(caller):
                caller.msg(f"Subscribed to board '{board.key}'.")
            else:
                caller.msg("You don't have permission to subscribe to that board.")
                
        elif "unsub" in self.switches:
            if not self.args:
                caller.msg("Usage: board/unsub <board>")
                return
                
            boards = [b for b in search_script("", typeclass=BulletinBoardScript) if b.key == self.args]
            if not boards:
                caller.msg(f"Board '{self.args}' not found.")
                return
            board = boards[0]
            
            if board.unsubscribe(caller):
                caller.msg(f"Unsubscribed from board '{board.key}'.")
            else:
                caller.msg("You weren't subscribed to that board.")
                
        elif "access" in self.switches:
            if not self.args or "/" not in self.args or "=" not in self.args:
                caller.msg("Usage: board/access <board>/<type>=<lockstring>")
                return
                
            board_name, rest = self.args.split("/", 1)
            access_type, lockstring = rest.split("=", 1)
            
            board = find_board(board_name)
            if not board:
                caller.msg(f"Board '{board_name}' not found.")
                return
            
            if board.set_access(access_type.strip(), lockstring.strip(), caller):
                caller.msg(f"Set {access_type} access for board '{board_name}'.")
            else:
                caller.msg("Failed to set access. Check your permissions and syntax.")
                
        elif "markread" in self.switches:
            if not self.args:
                caller.msg("Usage: board/markread <board>")
                return
                
            board_name = self.args.strip()
            board = find_board(board_name)
            if not board:
                caller.msg(f"Board '{board_name}' not found.")
                return
            
            if not board.access(caller, "read"):
                caller.msg("You don't have permission to mark all posts on that board as read.")
                return
            
            marked_count = board.mark_all_read(caller)
            if marked_count > 0:
                caller.msg(f"Marked {marked_count} post{'s' if marked_count != 1 else ''} as read on board '{board_name}'.")
            else:
                caller.msg(f"No unread posts found on board '{board_name}'.")
                
        else:
            caller.msg("Invalid command usage. Please refer to the help text for correct usage.") 