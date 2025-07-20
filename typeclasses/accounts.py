"""
Account

The Account represents the game "account" and each login has only one
Account object. An Account is what chats on default channels but has no
other in-game-world existence. Rather the Account puppets Objects (such
as Characters) in order to actually participate in the game world.


Guest

Guest accounts are simple low-level accounts that are created/deleted
on the fly and allows users to test the game without the commitment
of a full registration. Guest accounts are deactivated by default; to
activate them, add the following line to your settings file:

    GUEST_ENABLED = True

You will also need to modify the connection screen to reflect the
possibility to connect with a guest account. The setting file accepts
several more options for customizing the Guest account system.

"""

from evennia.accounts.accounts import DefaultAccount, DefaultGuest


class Account(DefaultAccount):
    """
    An Account is the actual OOC player entity. It doesn't exist in the game,
    but puppets characters.

    This is the base Typeclass for all Accounts. Accounts represent
    the person playing the game and tracks account info, password
    etc. They are OOC entities without presence in-game. An Account
    can connect to a Character Object in order to "enter" the
    game.

    Account Typeclass API:

    * Available properties (only available on initiated typeclass objects)

     - key (string) - name of account
     - name (string)- wrapper for user.username
     - aliases (list of strings) - aliases to the object. Will be saved to
            database as AliasDB entries but returned as strings.
     - dbref (int, read-only) - unique #id-number. Also "id" can be used.
     - date_created (string) - time stamp of object creation
     - permissions (list of strings) - list of permission strings
     - user (User, read-only) - django User authorization object
     - obj (Object) - game object controlled by account. 'character' can also
                     be used.
     - is_superuser (bool, read-only) - if the connected user is a superuser

    * Handlers

     - locks - lock-handler: use locks.add() to add new lock strings
     - db - attribute-handler: store/retrieve database attributes on this
                              self.db.myattr=val, val=self.db.myattr
     - ndb - non-persistent attribute handler: same as db but does not
                                  create a database entry when storing data
     - scripts - script-handler. Add new scripts to object with scripts.add()
     - cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
     - nicks - nick-handler. New nicks with nicks.add().
     - sessions - session-handler. Use session.get() to see all sessions connected, if any
     - options - option-handler. Defaults are taken from settings.OPTIONS_ACCOUNT_DEFAULT
     - characters - handler for listing the account's playable characters

    * Helper methods (check autodocs for full updated listing)

     - msg(text=None, from_obj=None, session=None, options=None, **kwargs)
     - execute_cmd(raw_string)
     - search(searchdata, return_puppet=False, search_object=False, typeclass=None,
                      nofound_string=None, multimatch_string=None, use_nicks=True,
                      quiet=False, **kwargs)
     - is_typeclass(typeclass, exact=False)
     - swap_typeclass(new_typeclass, clean_attributes=False, no_default=True)
     - access(accessing_obj, access_type='read', default=False, no_superuser_bypass=False, **kwargs)
     - check_permstring(permstring)
     - get_cmdsets(caller, current, **kwargs)
     - get_cmdset_providers()
     - uses_screenreader(session=None)
     - get_display_name(looker, **kwargs)
     - get_extra_display_name_info(looker, **kwargs)
     - disconnect_session_from_account()
     - puppet_object(session, obj)
     - unpuppet_object(session)
     - unpuppet_all()
     - get_puppet(session)
     - get_all_puppets()
     - is_banned(**kwargs)
     - get_username_validators(validator_config=settings.AUTH_USERNAME_VALIDATORS)
     - authenticate(username, password, ip="", **kwargs)
     - normalize_username(username)
     - validate_username(username)
     - validate_password(password, account=None)
     - set_password(password, **kwargs)
     - get_character_slots()
     - get_available_character_slots()
     - create_character(*args, **kwargs)
     - create(*args, **kwargs)
     - delete(*args, **kwargs)
     - channel_msg(message, channel, senders=None, **kwargs)
     - idle_time()
     - connection_time()

    * Hook methods

     basetype_setup()
     at_account_creation()

     > note that the following hooks are also found on Objects and are
       usually handled on the character level:

     - at_init()
     - at_first_save()
     - at_access()
     - at_cmdset_get(**kwargs)
     - at_password_change(**kwargs)
     - at_first_login()
     - at_pre_login()
     - at_post_login(session=None)
     - at_failed_login(session, **kwargs)
     - at_disconnect(reason=None, **kwargs)
     - at_post_disconnect(**kwargs)
     - at_message_receive()
     - at_message_send()
     - at_server_reload()
     - at_server_shutdown()
     - at_look(target=None, session=None, **kwargs)
     - at_post_create_character(character, **kwargs)
     - at_post_add_character(char)
     - at_post_remove_character(char)
     - at_pre_channel_msg(message, channel, senders=None, **kwargs)
     - at_post_chnnel_msg(message, channel, senders=None, **kwargs)

    """

    def at_post_login(self, session=None):
        """
        Called after the account is logged in.
        Show any stored request notifications.
        """
        super().at_post_login(session)
        
        # Check for stored notifications
        notifications = self.db.offline_request_notifications
        if notifications:
            # Show all stored notifications
            self.msg("\n|yStored Request Notifications:|n")
            for notification in notifications:
                self.msg(notification)
            self.msg("\n")  # Add a blank line after notifications
            
            # Clear the notifications
            self.db.offline_request_notifications = []


class Guest(DefaultGuest):
    """
    This class is used for guest logins. Unlike Accounts, Guests and their
    characters are deleted after disconnection.
    """

    def at_post_create(self):
        """
        Called when the guest account is first created.
        Guests always get a character created, regardless of AUTO_CREATE_CHARACTER_WITH_ACCOUNT setting.
        This mimics the default Evennia behavior for guest accounts.
        """
        super().at_post_create()
        
        # Clear any stale puppet references first
        self.db._last_puppet = None
        
        # Always create a character for guests (like AUTO_CREATE_CHARACTER_WITH_ACCOUNT = True)
        character, errors = self.create_character(key=self.key)
        if character:
            self.db._last_puppet = character
        else:
            # Log the error for debugging
            from evennia import logger
            logger.log_err(f"Failed to create character for guest {self.key}: {errors}")

    def at_post_disconnect(self, **kwargs):
        """
        Called just after user disconnects from this account.
        For guests, ensure both account and character are properly deleted.
        """
        from evennia import logger
        logger.log_info(f"Guest {self.key} disconnecting, cleaning up characters...")
        
        # Get characters BEFORE calling parent cleanup (which might delete the account)
        characters = list(self.characters)
        logger.log_info(f"Found {len(characters)} characters to delete: {[c.key for c in characters]}")
        
        # Delete characters first
        for character in characters:
            char_id = character.id
            char_key = character.key
            logger.log_info(f"Deleting character {char_key} (#{char_id})")
            
            # Check if character exists before deletion
            from evennia.objects.models import ObjectDB
            exists_before = ObjectDB.objects.filter(id=char_id).exists()
            logger.log_info(f"Character {char_key} exists before deletion: {exists_before}")
            
            # Check what might be referencing this character
            try:
                # Check if character is still connected/sessioned
                if hasattr(character, 'sessions') and character.sessions.all():
                    logger.log_info(f"Character {char_key} has active sessions: {[s for s in character.sessions.all()]}")
                
                # Check if account still references this character
                if hasattr(character, 'account') and character.account:
                    logger.log_info(f"Character {char_key} still has account: {character.account}")
                    if hasattr(character.account, 'db') and character.account.db._last_puppet == character:
                        logger.log_info(f"Account {character.account} has this character as _last_puppet")
                
                # Check for related objects that might prevent deletion
                from django.db import models
                from evennia.objects.models import ObjectDB
                related_objects = []
                
                # Specifically check what ObjectDB objects reference this character
                referencing_objects = ObjectDB.objects.filter(db_destination=character) | \
                                    ObjectDB.objects.filter(db_location=character) | \
                                    ObjectDB.objects.filter(db_home=character)
                
                if referencing_objects.exists():
                    logger.log_info(f"ObjectDB objects referencing character {char_key}:")
                    for obj in referencing_objects:
                        logger.log_info(f"  - {obj.db_key} (#{obj.id}) as destination={obj.db_destination==character}, location={obj.db_location==character}, home={obj.db_home==character}")
                
                # General check for all related objects
                for field in character._meta.get_fields():
                    if isinstance(field, models.ForeignKey) and field.related_model:
                        related_count = field.related_model.objects.filter(**{field.related_query_name(): character}).count()
                        if related_count > 0:
                            related_objects.append(f"{field.related_model.__name__}: {related_count}")
                
                if related_objects:
                    logger.log_info(f"Character {char_key} has related objects: {related_objects}")
                else:
                    logger.log_info(f"Character {char_key} has no related objects")
                        
            except Exception as ref_e:
                logger.log_err(f"Error checking character references: {ref_e}")
                import traceback
                logger.log_err(f"Reference check traceback: {traceback.format_exc()}")
            
            # Try to understand what would be deleted
            try:
                from django.db.models.deletion import Collector
                from django.db import DEFAULT_DB_ALIAS
                
                collector = Collector(using=DEFAULT_DB_ALIAS)
                collector.collect([character])
                logger.log_info(f"Deletion would affect: {dict(collector.data)}")
                
                # Check for protected relationships
                if hasattr(collector, 'protected') and collector.protected:
                    logger.log_err(f"Character {char_key} has protected relationships: {collector.protected}")
                elif hasattr(collector, 'dependencies') and collector.dependencies:
                    logger.log_info(f"Character {char_key} has dependencies: {collector.dependencies}")
                
            except Exception as collector_e:
                logger.log_err(f"Error analyzing deletion: {collector_e}")
            
            try:
                result = character.delete()
                logger.log_info(f"Character deletion returned: {result}")
            except Exception as e:
                logger.log_err(f"Character deletion failed with exception: {e}")
                import traceback
                logger.log_err(f"Traceback: {traceback.format_exc()}")
            
            # Check if character exists after deletion
            exists_after = ObjectDB.objects.filter(id=char_id).exists()
            logger.log_info(f"Character {char_key} exists after deletion: {exists_after}")
            
            if exists_after:
                logger.log_err(f"Character {char_key} still exists after delete() call!")
        
        # Clear any stale puppet references to prevent issues with reused guest names
        self.db._last_puppet = None
        
        # Then call parent cleanup to delete the account
        logger.log_info(f"Calling parent cleanup for guest {self.key}")
        super().at_post_disconnect(**kwargs)
