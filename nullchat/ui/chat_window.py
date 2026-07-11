import time
import tkinter as tk
import secrets
from pathlib import Path
from tkinter import messagebox


from nullchat.protocol.consumer import PlaintextEvent
from nullchat.protocol.room_manager import create_room, join_room

C_SIDEBAR_BG = "#B8B8B8"
C_SIDEBAR_SELECTED = "#909090"
C_HEADER_BG = "#C0C0C0"
C_MAIN_BG = "#FFFFFF"
C_INPUT_BG = "#B8B8B8"
C_BUBBLE_IN = "#E0E0E0"
C_BUBBLE_OUT = "#999999"
C_TEXT_FG = "#000000"

class ChatWindow(tk.Tk):
    def __init__(self, consumer, engine, bus, my_peer_id, registry, chat_store):
        super().__init__()
        self.title("NullChat")
        self.geometry("850x550")
        self.configure(bg=C_MAIN_BG)

        self.consumer = consumer
        self.engine = engine
        self.bus = bus
        self.my_peer_id = my_peer_id
        self.registry = registry

        self.current_room_id = None
        self.chat_store = chat_store

        self.sidebar = tk.Frame(self, bg=C_SIDEBAR_BG, width=240)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        self.main_area = tk.Frame(self, bg=C_MAIN_BG)
        self.main_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_sidebar()
        self._build_main_area()

        self.after(100, self._poll_backend)

    def _build_sidebar(self):
        for widget in self.sidebar.winfo_children():
            widget.destroy() # clear sidebar

        header_frame = tk.Frame(self.sidebar, bg=C_SIDEBAR_BG, pady=10, padx=10)
        header_frame.pack(fill=tk.X)

        title_frame = tk.Frame(header_frame, bg=C_SIDEBAR_BG)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(title_frame, text="💬 NullChat", font=("Segoe UI", 16, "bold"),
                 bg=C_SIDEBAR_BG, fg=C_TEXT_FG).pack(side=tk.LEFT)

        # create/join buttons
        btn_frame = tk.Frame(header_frame, bg=C_SIDEBAR_BG)
        btn_frame.pack(fill=tk.X)

        tk.Button( # create room button
            btn_frame, text="✨ Create Room", font=("Segoe UI", 9, "bold"),
            bg="#333333", fg="#FFFFFF", relief=tk.FLAT, padx=6, pady=2,
            command=self._create_room
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))

        tk.Button( # join room button
            btn_frame, text="🔗 Join Room", font=("Segoe UI", 9, "bold"),
            bg="#333333", fg="#FFFFFF", relief=tk.FLAT, padx=6, pady=2,
            command=self._join_room
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))

        active_rooms = (
            self.registry.get_all_rooms()
            if hasattr(self.registry, "get_all_rooms")
            else []
        )

        if self.current_room_id and self.current_room_id not in active_rooms:
            active_rooms.insert(0, self.current_room_id)

        if not active_rooms:
            tk.Label(self.sidebar, text="No active rooms.",
                     bg=C_SIDEBAR_BG, pady=20).pack()

        for room_id in active_rooms:
            is_selected = (room_id == self.current_room_id) # highlight the selected room
            bg_color = C_SIDEBAR_SELECTED if is_selected else C_SIDEBAR_BG

            contact_frame = tk.Frame(self.sidebar, bg=bg_color, pady=10, padx=10)
            contact_frame.pack(fill=tk.X) 

            def make_callback(rid):
                return lambda e: self._select_room(rid)

            icon = tk.Label(contact_frame, text="💬", font=("Segoe UI", 16),
                            bg=bg_color, fg=C_TEXT_FG)
            icon.pack(side=tk.LEFT, padx=(0, 10))
            icon.bind("<Button-1>", make_callback(room_id))

            name = tk.Label(contact_frame, text=f"Room ID: {room_id}",
                            font=("Segoe UI", 11, "bold"),
                            bg=bg_color, fg=C_TEXT_FG)
            name.pack(side=tk.LEFT, expand=True, fill=tk.X)
            name.bind("<Button-1>", make_callback(room_id))

    def _build_main_area(self):
        self.header_frame = tk.Frame(self.main_area, bg=C_HEADER_BG, pady=15, padx=15)
        self.header_frame.pack(fill=tk.X)

        def _on_delete_current_room(): # delete button confirmation screen
            if not self.current_room_id:
                return
            if messagebox.askyesno("Delete Room", f"Delete room {self.current_room_id}?"):
                self._delete_room(self.current_room_id) 

        # delete button
        self.delete_btn = tk.Button(
            self.header_frame, text="🗑️ Delete", font=("Segoe UI", 9, "bold"),
            bg="#AA0000", fg="#FFFFFF", relief=tk.FLAT, padx=8, pady=4,
            command=_on_delete_current_room
        )
        
        self.chat_title = tk.Label(
            self.header_frame,
            text="Join or create a room to start messaging!",
            font=("Segoe UI", 12, "bold"),
            bg=C_HEADER_BG,
            fg=C_TEXT_FG,
        )
        self.chat_title.pack(side=tk.LEFT)

        self.chat_canvas = tk.Canvas(self.main_area, bg=C_MAIN_BG, highlightthickness=0)
        self.chat_canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.chat_frame = tk.Frame(self.chat_canvas, bg=C_MAIN_BG)
        self.chat_canvas.create_window((0, 0), window=self.chat_frame,
                                    anchor="nw", width=540)

        self.suggestion_frame = tk.Frame(self.main_area, bg=C_MAIN_BG)
        self.suggestion_frame.pack(anchor="w", padx=20)

        input_container = tk.Frame(self.main_area, bg=C_INPUT_BG, pady=15, padx=15)
        input_container.pack(fill=tk.X, side=tk.BOTTOM)

        self.entry = tk.Entry(input_container, font=("Segoe UI", 12), relief=tk.FLAT)
        self.entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                        padx=(0, 15), ipady=10)

        self.entry.bind("<KeyRelease>", self._on_type) # autocomplete suggestions
        self.entry.bind("<Return>", lambda event: self._on_send()) # send message
        self.entry.bind("<Tab>", self._on_tab) # accept autocomplete suggestion

        tk.Button(
            input_container, text="➤", font=("Segoe UI", 14),
            bg="#000000", fg="#FFFFFF", relief=tk.FLAT,
            padx=15, pady=2, command=self._on_send
        ).pack(side=tk.RIGHT)
     
    def _create_room(self):
        chat_key = secrets.token_hex(32) # generates a chat key for the user, 32 bytes, 64 hex

        peer_public_key = self.my_peer_id

        room_id, crypto = create_room(chat_key, peer_public_key, self.registry) # room_id for the backend verification
        self.consumer.register_room(room_id, crypto)

        self.registry.add_room(room_id) 
        self.registry.map_chat_key(chat_key, room_id)

        popup = tk.Toplevel(self) # popup window
        popup.title("Encrypted Chat Created")
        popup.geometry("450x180")
        popup.configure(bg=C_MAIN_BG)
        popup.transient(self)
        popup.grab_set() # freezes

        tk.Label(
            popup,
            text="Share this chat key:",
            bg=C_MAIN_BG,
            font=("Segoe UI", 12, "bold")
        ).pack(pady=(20, 5))

        key_entry = tk.Entry(popup, font=("Consolas", 10), justify="center")
        key_entry.insert(0, chat_key)
        key_entry.config(state="readonly")
        key_entry.pack(fill=tk.X, padx=20, pady=5, ipady=5)

        def copy_key():
            self.clipboard_clear()
            self.clipboard_append(chat_key)
            copy_btn.config(text="Copied!")
            popup.after(1500, lambda: copy_btn.config(text="Copy Chat Key"))

        copy_btn = tk.Button(
            popup, text="Copy Chat Key", bg="#0066CC", fg="#FFFFFF",
            relief=tk.FLAT, padx=15, pady=5, command=copy_key
        )
        copy_btn.pack(pady=10)

        tk.Button(
            popup, text="OK", bg="#E0E0E0", fg="#000000",
            relief=tk.FLAT, padx=25, pady=5, command=popup.destroy
        ).pack()

        self._select_room(room_id)

    def _join_room(self):
        dialog = tk.Toplevel(self) # popup window
        dialog.title("Join Encrypted Chat")
        dialog.geometry("400x200") 
        dialog.transient(self) # stay at the top level

        tk.Label(dialog, text="Enter the chat key:", pady=20).pack()
        
        # textbox entry
        entry = tk.Entry(dialog, width=50)
        entry.pack(pady=10, padx=20)
        entry.focus_set() # for UX, cursor is in the entry box

        def on_submit():
            chat_key = entry.get()
            dialog.destroy()
            
            if not chat_key:
                return

            peer_public_key = self.my_peer_id
            room_id = self.registry.lookup_room_id(chat_key)
            
            if not room_id:
                messagebox.showerror("Error", "No room found for that chat key.")
                return

            crypto = join_room(room_id, chat_key, peer_public_key, self.registry)
            self.consumer.register_room(room_id, crypto)
            self.registry.add_room(room_id) 
            self._select_room(room_id)

        tk.Button(dialog, text="Join", command=on_submit).pack(pady=10)
        
        self.wait_window(dialog)

    def _select_room(self, room_id):
        self.current_room_id = room_id
        self.chat_title.config(text=f"Room ID: {room_id}")
        self.delete_btn.pack(side=tk.RIGHT) 
        self._build_sidebar()
        self._refresh_messages()

    def _refresh_messages(self): # when navigating between chatrooms
        for widget in self.chat_frame.winfo_children():
            widget.destroy()

        crypto = self.consumer.get_crypto(self.current_room_id)
        history = self.chat_store.load_history(crypto, self.current_room_id) 

        for event in history:
            incoming = (event.sender_id != self.my_peer_id)
            self._add_message(event.sender_id, event.text, incoming=incoming)

    def _add_message(self, sender, text, incoming=True): # helper for _on_send
        row_frame = tk.Frame(self.chat_frame, bg=C_MAIN_BG)
        row_frame.pack(fill=tk.X, pady=5)

        bubble_bg = C_BUBBLE_IN if incoming else C_BUBBLE_OUT # sender/receiver chat bubble color
        anchor = "w" if incoming else "e" # left/right chat bubble alignment

        if incoming: # show sender name
            tk.Label(row_frame, text=sender, font=("Segoe UI", 9, "bold"),
                     bg=C_MAIN_BG, fg=C_TEXT_FG).pack(anchor=anchor, padx=5)

        tk.Label( # create chat bubble
            row_frame, text=text, bg=bubble_bg, fg=C_TEXT_FG,
            font=("Segoe UI", 10), wraplength=350,
            justify=tk.LEFT, padx=15, pady=10
        ).pack(anchor=anchor)

    def _on_send(self):
        if not self.current_room_id: # is user in a room
            messagebox.showwarning("No Room", "Please create or join a room first!")
            return

        text = self.entry.get().strip() 
        if not text:
            return

        try:
            payload = text.encode("utf-8")
            self.bus.send(self.my_peer_id, payload)

            self.entry.delete(0, tk.END) # delete in entry box

            for widget in self.suggestion_frame.winfo_children(): # clear autocomplete suggestions
                widget.destroy()

            self._add_message("Me", text, incoming=False) # create message

            event = PlaintextEvent(
                room_id=self.current_room_id,
                sender_id=self.my_peer_id,
                timestamp=time.time(),  
                text=text,
            )

            crypto = self.consumer.get_crypto(self.current_room_id)
            self.chat_store.append(crypto, event)

        except Exception as e:
            print(f"Failed to send message: {e}")

    def _poll_backend(self):
        events = self.consumer.poll_ui_events()

        for event in events:
            crypto = self.consumer.get_crypto(event.room_id)
            self.chat_store.append(crypto, event)

            if event.room_id == self.current_room_id:
                self._add_message(event.sender_id, event.text, incoming=True)

        self.after(500, self._poll_backend)

    def _on_tab(self, event): # for autocomplete
        draft = self.entry.get() # reads text
        if not draft:
            return "break"

        words = draft.split(" ")
        if not words[-1]:
            return "break"

        suggestions = self.engine.suggest(words[-1])
        if suggestions:
            self._apply_suggestion(suggestions[0])

        return "break"

    def _on_type(self, event): # for autocomplete
        if event.keysym in ("Return", "BackSpace", "Tab"):
            return

        for widget in self.suggestion_frame.winfo_children():
            widget.destroy()

        draft = self.entry.get()
        words = draft.split(" ")

        if not words[-1]:
            return

        suggestions = self.engine.suggest(words[-1])

        if suggestions:
            tk.Label(
                self.suggestion_frame,
                text="Suggestions:",
                bg=C_MAIN_BG,
                fg="#888888",
                font=("Segoe UI", 10),
            ).pack(side=tk.LEFT)

            for word in suggestions[:3]: # clickable suggestions
                lbl = tk.Label(
                    self.suggestion_frame,
                    text=word,
                    bg="#E0F0FF",
                    fg="#0066CC",
                    font=("Segoe UI", 10, "bold"),
                    cursor="hand2",
                    padx=6,
                    pady=2,
                )
                lbl.pack(side=tk.LEFT, padx=6) # horizontal display of suggestions
                lbl.bind("<Button-1>", lambda e, w=word: self._apply_suggestion(w))

    def _apply_suggestion(self, selected_word): # helper for autocomplete
        draft = self.entry.get()
        words = draft.split(" ")
        words[-1] = selected_word

        new_text = " ".join(words) + " "

        self.entry.delete(0, tk.END)
        self.entry.insert(0, new_text)
        self.entry.icursor(tk.END) # move cursor to end of text

        for widget in self.suggestion_frame.winfo_children():
            widget.destroy() # clear suggestions

    def _delete_room(self, room_id):
        # remove from registry
        if room_id in self.registry._rooms:
            self.registry._rooms.remove(room_id)

        # remove chat key mapping
        keys_to_delete = [k for k, r in self.registry._key_to_room.items() if r == room_id]
        for k in keys_to_delete:
            del self.registry._key_to_room[k]
        self.registry.save_keys()

        # remove crypto
        if hasattr(self.consumer, "_room_keys"):
            self.consumer._room_keys.pop(room_id, None)

        # delete chat history file
        history_file = Path.home() / ".nullchat" / "chats" / f"{room_id}.jsonl"
        if history_file.exists():
            history_file.unlink()

        if self.current_room_id == room_id:
            self.current_room_id = None
            for widget in self.chat_frame.winfo_children():
                widget.destroy()
            self.chat_title.config(text="Join or create a room to start messaging!")
            self.delete_btn.pack_forget()

        self._build_sidebar()   