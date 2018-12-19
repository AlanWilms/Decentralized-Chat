import etcd
import sys
import time
import threading
import curses

from curses import textpad
from etcd_chat_lib import EtcdChatLib

class DecentralizedChat:

    # defines several class variables
    def __init__(self, screen):
        self.db = EtcdChatLib("172.31.92.266")
        self.db.add_endpoint("172.31.91.28")
        self.db.add_endpoint("172.31.93.186")
        self.db.add_endpoint("172.31.80.225")
        self.db.add_endpoint("172.31.84.98")
        self.username = None
        self.chatroom = None
        self.screen = screen
        self.window_width = curses.COLS
        self.window_height = curses.LINES
        self.box = None
        self.view = None

    # sets up the initial username and chat selection
    def setup(self):
        self.screen.immedok(True)
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        self.screen.addstr("  WELCOME TO DECENTRALIZED CHAT!  \n\n", curses.color_pair(1))

        self.print_status("Please type your username and then press ENTER.\n", False)
        self.clear_box()
        self.box.edit()
        self.username = (self.box.gather()).strip()
        self.clear_box()
        self.clear_status()

        chatroom_names = self.db.get_chatrooms() #"test1/test2/test3".split("/")
        num_rooms = len(chatroom_names)

        if num_rooms >= 1:
            if num_rooms == 1:
                self.screen.addstr(2, 1, "Here is the current room that you're a part of:\n")
            elif num_rooms > 1:
                self.screen.addstr(2, 1, "Here are the current rooms that you're a part of:\n")

            for i, name in enumerate(chatroom_names):
                self.screen.addstr(" [%d]: %s\n" % (i, name))
            self.screen.addstr(" [%d]: CREATE A NEW ROOM\n\n" % (num_rooms))

            self.print_status(" Please select a room by typing the associated number and then press ENTER.\n", False)
            self.clear_box()
            input = None
            while True:
                try:
                    self.box.edit()
                    input = int(self.box.gather())
                except ValueError: # is not a valid int
                    input = -1

                if input == num_rooms:
                    self.create_room(chatroom_names)
                    return
                elif input in range(0, num_rooms):
                    break
                else:
                    self.print_status(" Invalid option number, please try again.\n", True)
                    self.clear_box()
            self.clear_box()
            self.clear_status()
            selected_name = chatroom_names[input]

            if self.username not in self.db.get_members(selected_name):
                self.print_status(" Not currently a member of the selected group - WAITING FOR APPROVAL TO JOIN...", False)
                # requests until approval
                self.db.join_chatroom(self.username, selected_name)

            self.enter_room(selected_name)
        else:
            self.screen.addstr(2, 1, "No existing rooms - please create one! \n")
            self.create_room(chatroom_names)

    # prints status message, including instructions and error message (set highlight = True)
    # that are set one line above the textbox at the bottom
    def print_status(self, message, highlight):
        y, x = self.screen.getyx()
        self.screen.move(self.window_height - 4, 1);
        self.screen.clrtoeol()
        if highlight:
            self.screen.addstr(self.window_height - 4, 1, message, curses.color_pair(1))
        else:
            self.screen.addstr(self.window_height - 4, 1, message)
        self.screen.move(y, x)

    # clears the status message with clrtoel, which will prevent fragments of texts from
    # inadvertently being left behind when a smaller string supplants a larger one
    def clear_status(self):
        y, x = self.screen.getyx()
        self.screen.move(self.window_height - 4, 1)
        self.screen.clrtoeol()
        self.screen.move(y, x)

    # clears the text box on the bottom
    def clear_box(self):
        self.screen.move(self.window_height - 2, 2);
        self.screen.clrtoeol()
        textpad.rectangle(self.screen, self.window_height - 3, 0, self.window_height - 1, self.window_width - 2)
        win = curses.newwin(1, self.window_width-4, self.window_height - 2, 2)
        self.box = textpad.Textbox(win, True)

    # creates a brand new chatroom - the etcd_chat_lib handles duplicate names by throwing an
    # exception that is manifested here to the user as an error message
    def create_room(self, chatroom_names):
        self.print_status("Please enter the name for the new chatroom:", False)
        self.clear_box()
        while True:
            self.box.edit()
            name = (self.box.gather()).strip()
            self.clear_box()
            try:
                self.db.add_chatroom(self.username, name)
                self.print_status("Created %s..." % name, False)
                break
            except KeyError:
                self.print_status("Room name already taken, please enter a different one.", True)
        self.enter_room(name)

    # this prints messages from all users in the chatroom in the view window
    def print_message(self, username, message):
        self.view.addstr(" <%s> %s" % (username, message))
        self.view.addch("\n")

    # continually polls for new messages and new users by looking at differences in the metadata
    # between each poll. The former case is handled by an admin message that prompts the user
    # to enter the command into the textbox
    def poller(self):
        message_count = 0
        current_num_members = self.db.get_num_members(self.chatroom)
        while True:
            database_count = self.db.get_num_messages(self.chatroom)
            for index in range(message_count, database_count):
                username, message = self.db.recv(self.chatroom, index)
                self.print_message(username, message)
            message_count = database_count

            # check for new members joining
            new_num_members = self.db.get_num_members(self.chatroom)
            if new_num_members != current_num_members:
                all_members = self.db.get_members(self.chatroom)
                for index in range(current_num_members, new_num_members):
                    self.db.send(self.chatroom, "admin", "User %s would like to join! Please type \"!%s\" to accept" % (all_members[index], all_members[index]))
                current_num_members = new_num_members
            time.sleep(0.5)

    # called both when an existing room exists or after the creation of a new one
    # this also calls the polling thread
    def enter_room(self, name):
        self.chatroom = name
        self.screen.clear()
        self.screen.addstr(0, 0, "ROOM: %s" % name, curses.color_pair(1))
        self.clear_box()

        textpad.rectangle(self.screen, 3, 0, self.window_height - 7, self.window_width - 2)
        self.view = self.screen.subwin(self.window_height - 11, self.window_width - 4, 4, 1)
        self.view.scrollok(1)
        self.view.immedok(True)

        view = threading.Thread(target=self.poller, args=())
        view.daemon = True
        view.start()

        self.print_status("Type and press ENTER to send a message.", False)
        while True:
            self.box.edit()
            message = (self.box.gather()).strip()
            if len(message) > 0 and message[0] == "!":
                name = message[1:]
                if name in self.db.get_members(self.chatroom):
                    self.db.approve_member(name, self.chatroom)
                    self.db.send(self.chatroom, "admin", "User %s accepted by %s." % (name, self.username))
            else:
                self.db.send(self.chatroom, self.username, message)
            self.clear_box()
        self.screen.getch()

def main(screen):
    screen.clear()
    chat = DecentralizedChat(screen)
    chat.setup()

if __name__ == "__main__":
    curses.wrapper(main)
