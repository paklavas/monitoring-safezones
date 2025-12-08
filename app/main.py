import tkinter as tk
from tkinter import messagebox
import sqlite3
import os
import page1

# ------------------------------
# Database setup
# ------------------------------
if not os.path.exists("accounts.db"):
    open("accounts.db", "w").close()

conn = sqlite3.connect("accounts.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    email TEXT NOT NULL
)
""")
conn.commit()

# ------------------------------
# Functions
# ------------------------------
def login():
    username = username_entry.get()
    password = password_entry.get()

    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = cursor.fetchone()

    if user:
        window.destroy()  # Close login window
        page1.open_safety_dashboard(username)  # Open safety monitoring dashboard
    else:
        messagebox.showerror("Login Failed", "Invalid username or password.")

def show_create_fields():
    """Switch UI to account creation mode."""
    login_button.pack_forget()
    create_account_button.pack_forget()

    # Email field - pack in correct order
    email_label.pack(fill=tk.X, pady=(0, 5))
    email_entry.pack(pady=(0, 30), ipady=8)
    email_frame.pack(fill=tk.X, pady=(0, 20), before=buttons_frame)
    
    # Buttons
    confirm_create_button.pack(fill=tk.X, pady=(0, 10))
    back_button.pack(fill=tk.X)

def create_account():
    new_username = username_entry.get()
    new_password = password_entry.get()
    new_email = email_entry.get()

    if not new_username or not new_password or not new_email:
        messagebox.showwarning("Error", "Please fill out all fields.")
        return

    try:
        cursor.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                       (new_username, new_password, new_email))
        conn.commit()
        messagebox.showinfo("Success", "Account created successfully!")
        reset_to_login()
    except sqlite3.IntegrityError:
        messagebox.showerror("Error", "Username already exists!")

def reset_to_login():
    """Reset the interface back to login mode."""
    email_frame.pack_forget()
    confirm_create_button.pack_forget()
    back_button.pack_forget()

    username_entry.delete(0, tk.END)
    password_entry.delete(0, tk.END)
    email_entry.delete(0, tk.END)

    login_button.pack(fill=tk.X, pady=(0, 10))
    create_account_button.pack(fill=tk.X)

# ------------------------------
# Color scheme - Matching dashboard theme
# ------------------------------
colors = {
    'bg_dark': '#000000',           # Pure black
    'bg_card': '#1a1a1a',          # Dark grey
    'accent_yellow': '#FFD700',     # Gold yellow
    'text_primary': '#FFFFFF',      # White
    'text_secondary': '#999999',     # Medium grey
    'border': '#333333',            # Dark grey border
    'entry_bg': '#2d2d2d',          # Entry field background
    'entry_fg': '#FFFFFF',          # Entry field text
    'entry_border': '#555555'       # Entry field border
}

# ------------------------------
# Main window
# ------------------------------
window = tk.Tk()
window.title("Login Window")
window.attributes('-fullscreen', True)
window.bind("<Escape>", lambda event: window.attributes('-fullscreen', False))
window.configure(bg=colors['bg_dark'])

# Main container for centering
main_container = tk.Frame(window, bg=colors['bg_dark'])
main_container.pack(fill=tk.BOTH, expand=True)

# Center frame for login card
center_frame = tk.Frame(main_container, bg=colors['bg_dark'])
center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

# Login card with modern design
login_card = tk.Frame(center_frame, bg=colors['bg_card'], 
                     relief=tk.FLAT, borderwidth=1,
                     highlightbackground=colors['border'],
                     highlightthickness=1)
login_card.pack(padx=40, pady=40)

# Yellow accent line at top
accent_line = tk.Frame(login_card, bg=colors['accent_yellow'], height=4)
accent_line.pack(fill=tk.X, side=tk.TOP)

# Content frame
content_frame = tk.Frame(login_card, bg=colors['bg_card'])
content_frame.pack(padx=50, pady=40)

# Title
title_label = tk.Label(content_frame, text="🦺 Workplace Safety Monitor", 
                      font=("Segoe UI", 24, "bold"), 
                      bg=colors['bg_card'], 
                      fg=colors['accent_yellow'])
title_label.pack(pady=(0, 10))

subtitle_label = tk.Label(content_frame, text="Sign in to continue", 
                         font=("Segoe UI", 12), 
                         bg=colors['bg_card'], 
                         fg=colors['text_secondary'])
subtitle_label.pack(pady=(0, 30))

# User icon
icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "user.png")
if os.path.exists(icon_path):
    user_icon = tk.PhotoImage(file=icon_path)
    user_icon = user_icon.subsample(2, 2)
    icon_label = tk.Label(content_frame, image=user_icon, bg=colors['bg_card'])
    icon_label.image = user_icon
    icon_label.pack(pady=(0, 30))
else:
    icon_label = tk.Label(content_frame, text="👤", 
                         font=("Segoe UI", 64), 
                         bg=colors['bg_card'], 
                         fg=colors['accent_yellow'])
    icon_label.pack(pady=(0, 30))

# Username field
username_label = tk.Label(content_frame, text="Username", 
                          font=("Segoe UI", 11), 
                          bg=colors['bg_card'], 
                          fg=colors['text_secondary'],
                          anchor='w')
username_label.pack(fill=tk.X, pady=(0, 5))

username_entry = tk.Entry(content_frame, 
                         font=("Segoe UI", 12),
                         bg=colors['entry_bg'],
                         fg=colors['entry_fg'],
                         insertbackground=colors['accent_yellow'],
                         relief=tk.FLAT,
                         borderwidth=1,
                         highlightbackground=colors['entry_border'],
                         highlightthickness=1,
                         highlightcolor=colors['accent_yellow'],
                         width=30)
username_entry.pack(pady=(0, 20), ipady=8)

# Password field
password_label = tk.Label(content_frame, text="Password", 
                          font=("Segoe UI", 11), 
                          bg=colors['bg_card'], 
                          fg=colors['text_secondary'],
                          anchor='w')
password_label.pack(fill=tk.X, pady=(0, 5))

password_entry = tk.Entry(content_frame, 
                         show="*",
                         font=("Segoe UI", 12),
                         bg=colors['entry_bg'],
                         fg=colors['entry_fg'],
                         insertbackground=colors['accent_yellow'],
                         relief=tk.FLAT,
                         borderwidth=1,
                         highlightbackground=colors['entry_border'],
                         highlightthickness=1,
                         highlightcolor=colors['accent_yellow'],
                         width=30)
password_entry.pack(pady=(0, 30), ipady=8)

# Buttons frame
buttons_frame = tk.Frame(content_frame, bg=colors['bg_card'])
buttons_frame.pack(fill=tk.X)

# Login button with yellow accent
login_button = tk.Button(buttons_frame, 
                        text="Login", 
                        command=login,
                        font=("Segoe UI", 12, "bold"),
                        bg=colors['accent_yellow'],
                        fg=colors['bg_dark'],
                        activebackground='#FFEB3B',
                        activeforeground=colors['bg_dark'],
                        relief=tk.FLAT,
                        borderwidth=0,
                        cursor="hand2",
                        padx=40,
                        pady=12)
login_button.pack(fill=tk.X, pady=(0, 10))

# Create account button
create_account_button = tk.Button(buttons_frame, 
                                  text="Create New Account", 
                                  command=show_create_fields,
                                  font=("Segoe UI", 11),
                                  bg=colors['bg_card'],
                                  fg=colors['text_primary'],
                                  activebackground=colors['entry_bg'],
                                  activeforeground=colors['text_primary'],
                                  relief=tk.FLAT,
                                  borderwidth=1,
                                  highlightbackground=colors['border'],
                                  highlightthickness=1,
                                  cursor="hand2",
                                  padx=40,
                                  pady=10)
create_account_button.pack(fill=tk.X)

# Hidden email and confirm fields
email_frame = tk.Frame(content_frame, bg=colors['bg_card'])
email_label = tk.Label(email_frame, text="Email", 
                      font=("Segoe UI", 11), 
                      bg=colors['bg_card'], 
                      fg=colors['text_secondary'],
                      anchor='w')
email_entry = tk.Entry(email_frame, 
                      font=("Segoe UI", 12),
                      bg=colors['entry_bg'],
                      fg=colors['entry_fg'],
                      insertbackground=colors['accent_yellow'],
                      relief=tk.FLAT,
                      borderwidth=1,
                      highlightbackground=colors['entry_border'],
                      highlightthickness=1,
                      highlightcolor=colors['accent_yellow'],
                      width=30)

confirm_create_button = tk.Button(buttons_frame, 
                                  text="Create Account", 
                                  command=create_account,
                                  font=("Segoe UI", 12, "bold"),
                                  bg=colors['accent_yellow'],
                                  fg=colors['bg_dark'],
                                  activebackground='#FFEB3B',
                                  activeforeground=colors['bg_dark'],
                                  relief=tk.FLAT,
                                  borderwidth=0,
                                  cursor="hand2",
                                  padx=40,
                                  pady=12)

back_button = tk.Button(buttons_frame, 
                       text="Back", 
                       command=reset_to_login,
                       font=("Segoe UI", 11),
                       bg=colors['bg_card'],
                       fg=colors['text_primary'],
                       activebackground=colors['entry_bg'],
                       activeforeground=colors['text_primary'],
                       relief=tk.FLAT,
                       borderwidth=1,
                       highlightbackground=colors['border'],
                       highlightthickness=1,
                       cursor="hand2",
                       padx=40,
                       pady=10)

window.mainloop()
