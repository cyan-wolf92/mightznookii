# Import modules
import sys
from zoneinfo import ZoneInfo
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, ChatCommand
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.twitch import Twitch
from twitchAPI.helper import first
import asyncio
import random
import os
import time
import threading
from pathlib import Path 
import json
from datetime import datetime, timezone, timedelta

sys.path.append(str(Path(__file__).resolve().parents[1]))
from twitch_bot_utils.Events import Events
from twitch_bot_utils.Helpers import Helpers
from twitch_bot_utils.Main_Commands import Commands
from twitch_bot_utils.Packs import Packs
from twitch_bot_utils.Streamer import Streamer
import twitch_bot_utils.app_secret as app_secret
import secret

class MightzNookii:
    def __init__(self):
        # Set up constants
        self.APP_ID = app_secret.APP_ID
        self.APP_SECRET = app_secret.APP_SECRET
        self.USER_SCOPE = app_secret.SCOPE
        self.token = None

        self.STREAMER = Streamer(
            DIR=secret.DIR,
            TARGET_CHANNEL=secret.TARGET_CHANNEL,
            STREAMER='Nookii',
            PRONOUNS=[''],
            TIME_ZONE=ZoneInfo(secret.TZ)
            )

        self.HELPERS = Helpers(
            STREAMER=self.STREAMER
        )
        
        self.streamData = None 
        
        # Initialize the timed message tick counter
        self.tick_speed = 1
        self.timed_message_bool = False
        self.TIMED_MESSAGE_TICK = 0       

        self.bot = None
        self.EVENTS = None
        self.CMDS = None

    # Check Live Status Helper
    def is_live(self):
        return self.HELPERS.GET_STREAM_DATA() != None

    # Explodinate command
    async def explodinate_command(self, cmd: ChatCommand):
        if self.HELPERS.HAS_SPECIAL_ACCESS(cmd.user, '!explodinate'):
            num = random.randint(0,2)
            if num == 0:
                await cmd.send(f"/me {cmd.parameter} spontaneously explodinates D:")
            elif num == 1:
                await cmd.reply(f"/me {cmd.parameter} was smited by W.U.F.F.")
            elif num == 2:
                await cmd.reply(f"/me {cmd.parameter} has poofed... and no one knows why D:")
        else:
            await cmd.reply(self.HELPERS.GET_ACCESS_DENIED_MSG())        
            
    # Mega bap command
    async def mega_bap_command(self, cmd: ChatCommand):
        if self.HELPERS.HAS_SPECIAL_ACCESS(cmd.user, '!megabap'):
            for _ in range(10):
                await cmd.send(f"/me {cmd.user.display_name} baps {cmd.parameter}! 🐾")
        else:
            await cmd.reply(self.HELPERS.GET_ACCESS_DENIED_MSG())        
            
    async def timed_messages(self):
        time.sleep(0.25) # delay to let live boolean register
        
        if (self.is_live()):
            self.timed_message_bool = True
            print('timed messages loop starting...')
            while self.timed_message_bool:
                
                # Increment the tick counter
                self.TIMED_MESSAGE_TICK += 1
                
                # Check the tick counter for the desired time to send the message'
                # You can add as many of these as you want
                match self.TIMED_MESSAGE_TICK: 
                    case 3600:
                        await self.HELPERS.TIMED_TOKEN_REFRESH()
        
                # Reset the tick counter if it exceeds the the very last check
                if self.TIMED_MESSAGE_TICK > 3600:
                    self.TIMED_MESSAGE_TICK = 0
                # Sleep the thread for 1 second before incrementing the tick
                time.sleep(1/self.tick_speed)
                
                if (self.is_live() == False):
                    print(f'\n\n========\nis_live : {self.is_live()}\n tick  reset\n=====')
                    self.TIMED_MESSAGE_TICK = 0
                    self.timed_message_bool = False
        time.sleep(10)

    # command to mannually set the tick mid-stream
    async def tick_set_command(self, cmd: ChatCommand):
        if self.HELPERS.HAS_SPECIAL_ACCESS(cmd.user, '!settick'):    
            if cmd.parameter.isnumeric():
                self.TIMED_MESSAGE_TICK = int(cmd.parameter)
            else:
                await cmd.reply(f"/me Error: Invalid Entry")
        else:
            await cmd.reply(self.HELPERS.GET_ACCESS_DENIED_MSG())

    async def set_tickspeed_command(self, cmd: ChatCommand):
        if self.HELPERS.HAS_SPECIAL_ACCESS(cmd.user, '!settickspeed'):    
            if cmd.parameter.isnumeric():
                self.tick_speed = int(cmd.parameter)
            else:
                await cmd.reply(f"/me Error: Invalid Entry")
        else:
            await cmd.reply(self.HELPERS.GET_ACCESS_DENIED_MSG())

    def timed_messages_thread_function(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.timed_messages())

    # Status debugging command
    async def status_command(self, cmd: ChatCommand):
        if self.HELPERS.HAS_SPECIAL_ACCESS(cmd.user, '!status'):
            await cmd.send(f"/me Aquata is currently {"live" if self.is_live else "offline"}")
            print(f"===== STATUS DATA =====\n\u2003LIVE STATUS: {self.is_live}\n===== END STATUS DATA =====")
        else:
            await cmd.reply(self.HELPERS.GET_ACCESS_DENIED_MSG())
            
    # Set timed message boolean command
    async def set_timed_message_boolean_command(self, cmd: ChatCommand):
        if self.HELPERS.HAS_SPECIAL_ACCESS(cmd.user, 'setliveboolean'):
            try:
                self.timed_message_bool = cmd.parameter.capitalize()
                await cmd.reply(f"/me timed_message_bool sucessfully set to {self.timed_message_bool}")
            except:
                await cmd.reply(f"/me Error: Invalid Entry")
        else:
            await cmd.reply(self.HELPERS.GET_ACCESS_DENIED_MSG())

    # Get Active Mods Helper
    async def get_active_mods(self):
        mods = [ x async for x in Twitch.get_moderators(self.bot, self.STREAMER.BROADCASTER.id) ]    
        chatters = await Twitch.get_chatters(self.bot, self.STREAMER.BROADCASTER.id, self.STREAMER.BROADCASTER.id)
        active_mods = [ mod for mod in mods if mod in [chatter for chatter in chatters.data]]

        mod_list = [mod for mod in active_mods]
        print(mod_list)

    # Debug data Command
    async def debug_data_command(self, cmd: ChatCommand):
        if self.HELPERS.HAS_SPECIAL_ACCESS(cmd.user, '!debugdata'):
            try:
                debug_start = "===== DEBUG DATA ====="
                debug_end = "===== END DEBUG DATA ====="
                data_str = f'\u2003STATUS: {self.is_live()}'
                
                data_str = self.EVENTS.event_append_debug_data(data_str)
                
                def add_to_data_str(title, var=None):
                    nonlocal data_str
                    if var != None:
                        try: 
                            data_str = f'\u2003{data_str}\n\u2003\u2003{title}: {var}'
                        except Exception as e: 
                            data_str = f'\u2003{data_str}\n\u2003\u2003{title}: {e}'
                    else:
                        data_str = f'\u2003{data_str}\n\n\u2003{title}'

                if self.is_live():
                    add_to_data_str('**** TIMED MESSAGES ****') # heading
                    add_to_data_str('TICK', self.TIMED_MESSAGE_TICK)
                    add_to_data_str('TIMED MESSAGE BOOLEAN', self.timed_message_bool)
                    
                    add_to_data_str('**** STREAM DATA ****') # heading
                    add_to_data_str('UPTIME', await self.CMDS.uptime_command(cmd, False))
                    add_to_data_str('ID', self.HELPERS.GET_STREAM_DATA()["id"])
                    add_to_data_str('LANGUAGE', self.HELPERS.GET_STREAM_DATA()["language"])
                    add_to_data_str('TAGS', self.HELPERS.GET_STREAM_DATA()["tags"])
                    
                    add_to_data_str('**** GAME DATA ****') # heading
                    add_to_data_str('GAME NAME', self.HELPERS.GET_STREAM_DATA()["game_name"])
                    add_to_data_str('GAME ID', self.HELPERS.GET_STREAM_DATA()["game_id"])
                    
                    add_to_data_str('**** VIEWER DATA ****') # heading
                    add_to_data_str('VIEWER COUNT', self.HELPERS.GET_STREAM_DATA()["viewer_count"])
                    add_to_data_str('ACTIVE MODS', 'NOT YET IMPLEMENTED')
                    add_to_data_str('CHATTERS', 'NOT YET IMPLEMENTED')

                print(f"{debug_start}\n\u2003{data_str.replace("    ", "").strip()}\n{debug_end}")
                self.STREAMER.LOGS.send_logs(f"\n{debug_start}\n\u2003{data_str.replace("    ", "").strip()}\n{debug_end}")
                await cmd.send(f"/me Succesfully Printed to Logs")
            except Exception as e:
                self.STREAMER.LOGS.send_logs(e)
                await cmd.send(f"/me Action Failed")
        else:
            await cmd.reply(self.HELPERS.GET_ACCESS_DENIED_MSG())

    # Print ready message
    print('Bot Ready')

# Bot setup function
    async def run_bot(self):
        # Authenticate application
        self.bot = await Twitch(self.APP_ID, self.APP_SECRET)
        self.STREAMER.set_broadcaster(await first(self.bot.get_users(logins=self.STREAMER.TARGET_CHANNEL)))
        auth = UserAuthenticator(self.bot, self.USER_SCOPE)
        self.token, refresh_token = await auth.authenticate()
        await self.bot.set_user_authentication(self.token, self.USER_SCOPE, refresh_token)

        # Initialize chat class
        chat = await Chat(self.bot)

        self.STREAMER.set_tokens(self.token, refresh_token)
        self.STREAMER.set_bot(self.bot)

        self.EVENTS = Events(
            STREAMER=self.STREAMER,
            timed_msg_thread=self.timed_messages_thread_function,
            Helpers=self.HELPERS)

        # Register events
        chat.register_event(ChatEvent.READY, self.EVENTS.on_ready)
        chat.register_event(ChatEvent.MESSAGE, self.EVENTS.on_message)
    
        self.CMDS = Commands(
            STREAMER=self.STREAMER,
            instagram='https://www.instagram.com/mightznookiiz/',
            bsky='https://bsky.app/profile/mightznookiiz.bsky.social',
            Helpers=self.HELPERS)

        # Register commands
        PACKS = Packs(chat, self.CMDS, self.HELPERS)
        
        # Chat commands
        PACKS.register_required()
        PACKS.register_main_chat(extras=['nom', 'uppies', 'time'])
                
        # Links commands
        PACKS.register_links(['insta', 'bsky'])

        # Percentage/Chance commands
        PACKS.register_main_percentage_based(extras=[])

        # Counter commands
        PACKS.register_main_counters(extras=['goodgirl', 'goodboy', 'pretty', 'nuts', 'short', 'sus'])
        
        # Systems commands
        PACKS.register_system('quotes')
        PACKS.register_system('tips')
        
        # Moderator Commands
        self.HELPERS.REGISTER(chat, ['so'], self.CMDS.shoutout_command)
        
        # Admin Commands
        chat.register_command('settick', self.tick_set_command)
        chat.register_command('status', self.status_command)
        chat.register_command('debugdata', self.debug_data_command)
        chat.register_command('setliveboolean', self.EVENTS.set_live_boolean_command)
        chat.register_command('timedmsgforce', self.set_timed_message_boolean_command)
        chat.register_command('cansendmsg', self.EVENTS.set_can_send_msg_command)
        chat.register_command('explodinate', self.explodinate_command)
        chat.register_command('megabap', self.mega_bap_command)

        cmds_list = PACKS.construct_cmds_list(extras=[])
        self.CMDS.set_commands_list(cmds_list)

        # Start the chat bot
        chat.start()

        try:
            input('Press ENTER to stop\n')
        finally:
            chat.stop()
            await self.bot.close()

if __name__ == "__main__":
    Bot = MightzNookii()
    bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bot_loop)
    bot_loop.run_until_complete((Bot.run_bot()))
    bot_loop.close()