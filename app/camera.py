import tkinter as tk
from tkinter import ttk
from datetime import datetime
import random
import cv2
from PIL import Image, ImageTk
from cameraview import CameraDetailWindow
from helmet_detector import HelmetDetector

class SafetyDashboard:
    def __init__(self, username):
        self.username = username
        self.window = tk.Tk()
        self.window.title("Workplace Safety Monitoring System")
        self.window.attributes('-fullscreen', True)
        self.window.bind("<Escape>", lambda event: self.window.attributes('-fullscreen', False))
        
        # Color scheme - Modern Black, Grey, Yellow theme
        self.colors = {
            'bg_dark': '#000000',           # Pure black
            'bg_card': '#1a1a1a',          # Dark grey
            'bg_sidebar': '#0f0f0f',        # Very dark grey (almost black)
            'bg_header': '#111111',         # Slightly lighter than sidebar
            'accent_yellow': '#FFD700',     # Gold yellow
            'accent_yellow_bright': '#FFEB3B',  # Bright yellow
            'accent_yellow_dark': '#FFA000',    # Darker yellow
            'accent_green': '#4caf50',      # Keep green for success
            'accent_red': '#f44336',        # Keep red for danger
            'text_primary': '#FFFFFF',      # White
            'text_secondary': '#999999',     # Medium grey
            'text_tertiary': '#666666',      # Dark grey
            'border': '#333333',            # Dark grey border
            'border_light': '#444444'       # Lighter border
        }
        
        self.window.configure(bg=self.colors['bg_dark'])
        
        # Track scheduled callbacks for cleanup
        self._scheduled_callbacks = []
        self._updates_paused = False
        
        # Initialize helmet detector
        try:
            self.helmet_detector = HelmetDetector(confidence_threshold=0.5)
            self.detection_enabled = True
        except Exception as e:
            print(f"Helmet detector initialization error: {e}")
            self.helmet_detector = None
            self.detection_enabled = False
        
        # Track violations per zone
        self.zone_violations = {1: 0, 2: 0, 3: 0, 4: 0}
        
        # Initialize camera for Zone 1
        self.camera = None
        self.camera_running = False
        try:
            self.camera = cv2.VideoCapture(0)
            if self.camera.isOpened():
                self.camera_running = True
            else:
                self.camera = None
        except Exception as e:
            print(f"Camera initialization error: {e}")
            self.camera = None
        
        self.setup_ui()
        
        # Add camera initialization alerts after UI is set up
        if self.camera_running:
            self.add_alert("Camera initialized for Zone 1", "success")
        else:
            self.add_alert("Camera not available - Zone 1 will show placeholder", "warning")
        
        # Add helmet detector status alert
        if self.detection_enabled:
            self.add_alert("Helmet detection system initialized", "success")
        else:
            self.add_alert("Helmet detection not available - using simulation mode", "warning")
        
        self.update_stats()
        
        # Start camera feed update for Zone 1
        if self.camera_running:
            self.update_camera_feed()
        
    def setup_ui(self):
        # Header Bar - Modern design with yellow accent
        header = tk.Frame(self.window, bg=self.colors['bg_header'], height=70)
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)
        
        # Yellow accent line at top
        accent_line = tk.Frame(header, bg=self.colors['accent_yellow'], height=3)
        accent_line.pack(fill=tk.X, side=tk.TOP)
        
        # Header content
        header_left = tk.Frame(header, bg=self.colors['bg_header'])
        header_left.pack(side=tk.LEFT, padx=30, pady=15)
        
        title_label = tk.Label(header_left, text="🦺 Workplace Safety Monitor", 
                               font=("Segoe UI", 24, "bold"), 
                               bg=self.colors['bg_header'], 
                               fg=self.colors['text_primary'])
        title_label.pack(side=tk.LEFT)
        
        subtitle_label = tk.Label(header_left, text="• Real-Time Helmet Detection System", 
                                  font=("Segoe UI", 11), 
                                  bg=self.colors['bg_header'], 
                                  fg=self.colors['text_secondary'])
        subtitle_label.pack(side=tk.LEFT, padx=(15, 0))
        
        header_right = tk.Frame(header, bg=self.colors['bg_header'])
        header_right.pack(side=tk.RIGHT, padx=30, pady=15)
        
        user_label = tk.Label(header_right, text=f"👤 {self.username}", 
                             font=("Segoe UI", 13, "bold"), 
                             bg=self.colors['bg_header'], 
                             fg=self.colors['accent_yellow'])
        user_label.pack(side=tk.RIGHT, padx=(15, 0))
        
        time_label = tk.Label(header_right, text="", 
                             font=("Segoe UI", 12), 
                             bg=self.colors['bg_header'], 
                             fg=self.colors['text_secondary'])
        time_label.pack(side=tk.RIGHT)
        self.time_label = time_label
        self.update_time()
        
        # Main Container - More spacing for modern look
        main_container = tk.Frame(self.window, bg=self.colors['bg_dark'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Left Sidebar - Statistics - Modern card design
        sidebar = tk.Frame(main_container, bg=self.colors['bg_sidebar'], width=300)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        sidebar.pack_propagate(False)
        
        sidebar_title = tk.Label(sidebar, text="📊 LIVE STATISTICS", 
                                 font=("Segoe UI", 16, "bold"), 
                                 bg=self.colors['bg_sidebar'], 
                                 fg=self.colors['accent_yellow'])
        sidebar_title.pack(pady=(25, 20), padx=20)
        
        # Yellow divider line
        divider = tk.Frame(sidebar, bg=self.colors['accent_yellow'], height=2)
        divider.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Stats Cards
        self.stats_frame = tk.Frame(sidebar, bg=self.colors['bg_sidebar'])
        self.stats_frame.pack(fill=tk.BOTH, expand=True, padx=15)
        
        # Create stat cards - Updated colors
        self.stat_cards = {}
        stats = [
            ("🟢 Workers Compliant", "0", self.colors['accent_green']),
            ("🔴 Safety Violations", "0", self.colors['accent_red']),
            ("📹 Active Cameras", "4", self.colors['accent_yellow']),
            ("⏱️ Uptime", "0h 0m", self.colors['text_secondary'])
        ]
        
        for label_text, value_text, color in stats:
            self.create_stat_card(label_text, value_text, color)
        
        # Middle Section - Camera Grid - Modern layout
        camera_section = tk.Frame(main_container, bg=self.colors['bg_dark'])
        camera_section.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20))
        
        camera_title = tk.Label(camera_section, text="📷 MONITORING FEEDS", 
                               font=("Segoe UI", 16, "bold"), 
                               bg=self.colors['bg_dark'], 
                               fg=self.colors['accent_yellow'])
        camera_title.pack(pady=(0, 20))
        
        # Yellow divider line
        camera_divider = tk.Frame(camera_section, bg=self.colors['accent_yellow'], height=2)
        camera_divider.pack(fill=tk.X, pady=(0, 20))
        
        # Camera Grid (2x2) - Modern card design
        camera_grid = tk.Frame(camera_section, bg=self.colors['bg_dark'])
        camera_grid.pack(fill=tk.BOTH, expand=True)
        
        self.camera_frames = []
        for i in range(4):
            row = i // 2
            col = i % 2
            
            # Modern card frame with border
            cam_frame = tk.Frame(camera_grid, bg=self.colors['bg_card'], 
                                relief=tk.FLAT, borderwidth=1, 
                                highlightbackground=self.colors['border'],
                                highlightthickness=1)
            cam_frame.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")
            
            camera_grid.grid_rowconfigure(row, weight=1)
            camera_grid.grid_columnconfigure(col, weight=1)
            
            # Yellow accent bar at top of card
            accent_bar = tk.Frame(cam_frame, bg=self.colors['accent_yellow'], height=4)
            accent_bar.pack(fill=tk.X, side=tk.TOP)
            
            # Camera label with modern styling
            cam_label = tk.Label(cam_frame, text=f"Safe Zone {i+1}", 
                                font=("Segoe UI", 14, "bold"), 
                                bg=self.colors['bg_card'], 
                                fg=self.colors['accent_yellow'])
            cam_label.pack(pady=(15, 10))
            
            # Camera feed - use Canvas for Zone 1 (i==0), Frame for others
            if i == 0:
                # Zone 1 - real camera feed (using Canvas for proper image display)
                feed_canvas = tk.Canvas(cam_frame, bg='#000000', width=400, height=300, highlightthickness=0)
                feed_canvas.pack(padx=15, pady=(0, 15))
                feed_frame = feed_canvas
            else:
                # Other zones - placeholder
                feed_frame = tk.Frame(cam_frame, bg='#000000', width=400, height=300)
                feed_frame.pack(padx=15, pady=(0, 15))
            
            # Status indicator - Modern design
            status_frame = tk.Frame(cam_frame, bg=self.colors['bg_card'])
            status_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
            
            status_indicator = tk.Label(status_frame, text="●", 
                                       font=("Segoe UI", 18), 
                                       bg=self.colors['bg_card'], 
                                       fg=self.colors['accent_green'])
            status_indicator.pack(side=tk.LEFT)
            
            status_text = tk.Label(status_frame, text="All Workers Compliant", 
                                  font=("Segoe UI", 11), 
                                  bg=self.colors['bg_card'], 
                                  fg=self.colors['text_secondary'])
            status_text.pack(side=tk.LEFT, padx=12)
            
            camera_data = {
                'frame': cam_frame,
                'status': status_indicator,
                'text': status_text,
                'feed': feed_frame,
                'is_camera': i == 0,  # Mark Zone 1 as camera feed
                'zone_id': i + 1,  # Zone number (1-4)
                'zone_index': i     # Index (0-3)
            }
            
            # Make camera frame clickable
            def on_camera_click(event, zone=i+1):
                self.open_camera_detail(zone)
            
            cam_frame.bind("<Button-1>", on_camera_click)
            cam_frame.bind("<Enter>", lambda e: cam_frame.config(cursor="hand2"))
            cam_frame.bind("<Leave>", lambda e: cam_frame.config(cursor=""))
            
            # Make all child widgets also clickable
            for widget in [cam_label, feed_frame, status_frame, status_indicator, status_text]:
                widget.bind("<Button-1>", on_camera_click)
                widget.bind("<Enter>", lambda e: cam_frame.config(cursor="hand2"))
                widget.bind("<Leave>", lambda e: cam_frame.config(cursor=""))
            
            self.camera_frames.append(camera_data)
        
        # Right Sidebar - Alerts - Modern design
        alert_sidebar = tk.Frame(main_container, bg=self.colors['bg_sidebar'], width=340)
        alert_sidebar.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(0, 0))
        alert_sidebar.pack_propagate(False)
        
        alert_title = tk.Label(alert_sidebar, text="🚨 ALERT LOG", 
                              font=("Segoe UI", 16, "bold"), 
                              bg=self.colors['bg_sidebar'], 
                              fg=self.colors['accent_yellow'])
        alert_title.pack(pady=(25, 20), padx=20)
        
        # Yellow divider line
        alert_divider = tk.Frame(alert_sidebar, bg=self.colors['accent_yellow'], height=2)
        alert_divider.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Alert scrollable area - Improved scrollable container
        alert_container = tk.Frame(alert_sidebar, bg=self.colors['bg_sidebar'])
        alert_container.pack(fill=tk.BOTH, expand=True, padx=(15, 0), pady=(0, 15))
        
        alert_canvas = tk.Canvas(alert_container, bg=self.colors['bg_sidebar'], 
                                highlightthickness=0, bd=0)
        alert_scrollbar = ttk.Scrollbar(alert_container, orient="vertical", 
                                       command=alert_canvas.yview)
        alert_scrollable = tk.Frame(alert_canvas, bg=self.colors['bg_sidebar'])
        
        # Create window inside canvas first
        window_id = alert_canvas.create_window((0, 0), window=alert_scrollable, anchor="nw")
        
        # Configure scrolling functions
        def on_mousewheel(event):
            """Handle mouse wheel scrolling"""
            alert_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def configure_scroll_region(event=None):
            """Update canvas width and scroll region when frame changes"""
            canvas_width = alert_canvas.winfo_width()
            if canvas_width > 1:  # Only update if canvas is actually visible
                alert_canvas.itemconfig(window_id, width=canvas_width)
            alert_canvas.configure(scrollregion=alert_canvas.bbox("all"))
        
        # Bind mouse wheel to canvas
        alert_canvas.bind("<MouseWheel>", on_mousewheel)
        alert_canvas.bind("<Button-4>", lambda e: alert_canvas.yview_scroll(-1, "units"))
        alert_canvas.bind("<Button-5>", lambda e: alert_canvas.yview_scroll(1, "units"))
        
        # Bind events
        alert_scrollable.bind("<Configure>", configure_scroll_region)
        alert_canvas.bind("<Configure>", lambda e: configure_scroll_region())
        
        # Configure scrollbar
        alert_canvas.configure(yscrollcommand=alert_scrollbar.set)
        
        # Pack canvas and scrollbar
        alert_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        alert_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.alert_frame = alert_scrollable
        self.alert_canvas = alert_canvas
        self.all_alerts = []  # Store all alerts with zone info
        self._alerts_initialized = False  # Track if alerts have been initialized
        
        # Only add initial alerts if not restoring from detail view
        if not hasattr(self, '_restoring_alerts'):
            self.add_alert("System initialized", "info")
            self.add_alert("All cameras operational", "success")
        
    def create_stat_card(self, label, value, color):
        # Modern stat card with better styling
        card = tk.Frame(self.stats_frame, bg=self.colors['bg_card'], 
                       relief=tk.FLAT, borderwidth=1,
                       highlightbackground=self.colors['border'],
                       highlightthickness=1)
        card.pack(fill=tk.X, pady=10)
        
        # Yellow accent bar
        accent_bar = tk.Frame(card, bg=self.colors['accent_yellow'], height=3)
        accent_bar.pack(fill=tk.X, side=tk.TOP)
        
        label_widget = tk.Label(card, text=label, 
                                font=("Segoe UI", 11), 
                                bg=self.colors['bg_card'], 
                                fg=self.colors['text_secondary'],
                                anchor='w')
        label_widget.pack(padx=20, pady=(15, 8))
        
        value_widget = tk.Label(card, text=value, 
                               font=("Segoe UI", 28, "bold"), 
                               bg=self.colors['bg_card'], 
                               fg=color)
        value_widget.pack(padx=20, pady=(0, 15))
        
        self.stat_cards[label] = value_widget
        
    def add_alert(self, message, alert_type="info", zone_id=None):
        # Modern alert card design
        alert_frame = tk.Frame(self.alert_frame, bg=self.colors['bg_card'], 
                              relief=tk.FLAT, borderwidth=1,
                              highlightbackground=self.colors['border'],
                              highlightthickness=1)
        alert_frame.pack(fill=tk.X, pady=8, padx=5)
        
        # Color based on alert type
        colors_map = {
            'info': self.colors['text_secondary'],
            'success': self.colors['accent_green'],
            'warning': self.colors['accent_yellow'],
            'danger': self.colors['accent_red']
        }
        color = colors_map.get(alert_type, colors_map['info'])
        
        icon_map = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'danger': '🚨'
        }
        icon = icon_map.get(alert_type, 'ℹ️')
        
        time_str = datetime.now().strftime("%H:%M:%S")
        
        # Left accent bar
        accent_bar = tk.Frame(alert_frame, bg=color, width=4)
        accent_bar.pack(side=tk.LEFT, fill=tk.Y)
        
        alert_content = tk.Frame(alert_frame, bg=self.colors['bg_card'])
        alert_content.pack(fill=tk.X, padx=15, pady=12)
        
        icon_label = tk.Label(alert_content, text=icon, 
                             font=("Segoe UI", 16), 
                             bg=self.colors['bg_card'], 
                             fg=color)
        icon_label.pack(side=tk.LEFT, padx=(0, 12))
        
        text_frame = tk.Frame(alert_content, bg=self.colors['bg_card'])
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        message_label = tk.Label(text_frame, text=message, 
                                font=("Segoe UI", 11), 
                                bg=self.colors['bg_card'], 
                                fg=self.colors['text_primary'],
                                anchor='w', justify='left')
        message_label.pack(anchor='w')
        
        time_label = tk.Label(text_frame, text=time_str, 
                             font=("Segoe UI", 9), 
                             bg=self.colors['bg_card'], 
                             fg=self.colors['text_tertiary'],
                             anchor='w')
        time_label.pack(anchor='w', pady=(2, 0))
        
        # Store alert with zone info
        self.all_alerts.append({
            'message': message,
            'type': alert_type,
            'zone_id': zone_id,
            'time': time_str,
            'frame': alert_frame
        })
        
        # Auto-scroll to bottom and update scroll region
        self.alert_frame.update_idletasks()
        self.alert_canvas.update_idletasks()
        
        # Update scroll region
        bbox = self.alert_canvas.bbox("all")
        if bbox:
            self.alert_canvas.configure(scrollregion=bbox)
            # Scroll to bottom
            self.alert_canvas.yview_moveto(1.0)
    
    def update_camera_feed(self):
        """Update the camera feed for Zone 1"""
        # Check if window still exists and updates are not paused
        try:
            if not self.window.winfo_exists() or getattr(self, '_updates_paused', False):
                # Still schedule next update if window exists (for resuming)
                if self.window.winfo_exists():
                    callback_id = self.window.after(100, self.update_camera_feed)  # Check less frequently when paused
                    self._scheduled_callbacks.append(callback_id)
                return
        except:
            return
        
        if self.camera_running and self.camera is not None:
            try:
                ret, frame = self.camera.read()
                if ret:
                    # Run helmet detection if enabled
                    if self.detection_enabled and self.helmet_detector is not None:
                        try:
                            annotated_frame, detections, violation_count = self.helmet_detector.detect(frame)
                            # Update violation count for Zone 1
                            self.zone_violations[1] = violation_count
                            
                            # Update status indicator if violations detected
                            if len(self.camera_frames) > 0 and self.camera_frames[0]['is_camera']:
                                if violation_count > 0:
                                    self.camera_frames[0]['status'].config(fg=self.colors['accent_red'])
                                    self.camera_frames[0]['text'].config(
                                        text=f"{violation_count} Violation(s) Detected!",
                                        fg=self.colors['accent_red']
                                    )
                                else:
                                    self.camera_frames[0]['status'].config(fg=self.colors['accent_green'])
                                    self.camera_frames[0]['text'].config(
                                        text="All Workers Compliant",
                                        fg=self.colors['text_secondary']
                                    )
                            
                            # Use annotated frame (with bounding boxes)
                            frame = annotated_frame
                        except Exception as e:
                            print(f"Detection error: {e}")
                            # Continue with original frame if detection fails
                    
                    # Resize frame to fit the display
                    frame = cv2.resize(frame, (400, 300))
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    # Convert to PIL Image
                    image = Image.fromarray(frame_rgb)
                    # Convert to ImageTk
                    photo = ImageTk.PhotoImage(image=image)
                    
                    # Update Zone 1 feed (index 0) - using Canvas
                    if len(self.camera_frames) > 0 and self.camera_frames[0]['is_camera']:
                        try:
                            canvas = self.camera_frames[0]['feed']
                            canvas.delete("all")  # Clear previous image
                            canvas.create_image(200, 150, image=photo, anchor=tk.CENTER)
                            canvas.image = photo  # Keep a reference to prevent garbage collection
                        except:
                            return  # Widget destroyed, stop updating
            except Exception as e:
                # Camera errors are expected when switching windows
                pass
        
        # Schedule next update only if window exists
        try:
            if self.window.winfo_exists():
                callback_id = self.window.after(30, self.update_camera_feed)
                self._scheduled_callbacks.append(callback_id)
        except:
            pass
    
    def update_time(self):
        # Check if window still exists and updates are not paused
        try:
            if not self.window.winfo_exists() or getattr(self, '_updates_paused', False):
                # Still schedule next update if window exists (for resuming)
                if self.window.winfo_exists():
                    callback_id = self.window.after(1000, self.update_time)
                    self._scheduled_callbacks.append(callback_id)
                return
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.time_label.config(text=current_time)
        except:
            return
        
        # Schedule next update only if window exists
        try:
            if self.window.winfo_exists():
                callback_id = self.window.after(1000, self.update_time)
                self._scheduled_callbacks.append(callback_id)
        except:
            pass
    
    def update_stats(self):
        # Check if window still exists and updates are not paused
        try:
            if not self.window.winfo_exists() or getattr(self, '_updates_paused', False):
                # Still schedule next update if window exists (for resuming)
                if self.window.winfo_exists():
                    callback_id = self.window.after(5000, self.update_stats)
                    self._scheduled_callbacks.append(callback_id)
                return
        except:
            return
        
        try:
            # Use real detection data if available, otherwise simulate
            if self.detection_enabled:
                # Sum violations from all zones
                total_violations = sum(self.zone_violations.values())
                # Estimate compliant workers (for demo, assume 10 total - violations)
                compliant = max(0, 10 - total_violations)
                violations = total_violations
            else:
                # Simulate real-time updates if detection not available
                compliant = random.randint(8, 12)
                violations = random.randint(0, 2)
            
            if '🟢 Workers Compliant' in self.stat_cards:
                self.stat_cards['🟢 Workers Compliant'].config(text=str(compliant))
            if '🔴 Safety Violations' in self.stat_cards:
                self.stat_cards['🔴 Safety Violations'].config(text=str(violations))
            
            # Randomly update camera statuses
            for cam in self.camera_frames:
                try:
                    if random.random() < 0.1:  # 10% chance of violation
                        cam['status'].config(fg=self.colors['accent_red'])
                        cam['text'].config(text="Helmet Violation Detected!", 
                                          fg=self.colors['accent_red'])
                        zone_id = self.camera_frames.index(cam) + 1
                        self.add_alert(f"Safety violation detected in Safe Zone {zone_id}", "danger", zone_id=zone_id)
                    else:
                        cam['status'].config(fg=self.colors['accent_green'])
                        cam['text'].config(text="All Workers Compliant", 
                                          fg=self.colors['text_secondary'])
                except:
                    continue  # Widget destroyed, skip
            
            # Update stats colors to use yellow theme
            if '🟢 Workers Compliant' in self.stat_cards:
                self.stat_cards['🟢 Workers Compliant'].config(fg=self.colors['accent_green'])
            if '🔴 Safety Violations' in self.stat_cards:
                self.stat_cards['🔴 Safety Violations'].config(fg=self.colors['accent_red'])
            if '📹 Active Cameras' in self.stat_cards:
                self.stat_cards['📹 Active Cameras'].config(fg=self.colors['accent_yellow'])
            if '⏱️ Uptime' in self.stat_cards:
                self.stat_cards['⏱️ Uptime'].config(fg=self.colors['text_secondary'])
        except:
            return
        
        # Schedule next update only if window exists
        try:
            if self.window.winfo_exists():
                callback_id = self.window.after(5000, self.update_stats)
                self._scheduled_callbacks.append(callback_id)
        except:
            pass
    def open_camera_detail(self, zone_id):
        """Open a new window with detailed camera view and alerts"""
        # Pause updates (don't cancel, just pause)
        self._updates_paused = True
        
        # Cancel camera feed updates to free the camera
        for callback_id in self._scheduled_callbacks:
            try:
                self.window.after_cancel(callback_id)
            except:
                pass
        
        # Minimize dashboard window instead of destroying
        self.window.iconify()
        
        # Handle camera for Zone 1
        if zone_id == 1 and self.camera is not None:
            # Give a small delay to ensure camera updates are stopped
            self.window.update_idletasks()
            camera_to_pass = self.camera
            self.camera = None  # Prevent cleanup in run()
            self.camera_running = False  # Mark as not running in dashboard
        else:
            camera_to_pass = None
        
        # Open detail window, pass reference to dashboard
        detail_window = CameraDetailWindow(self.username, zone_id, camera_to_pass, self.all_alerts, self.colors, self)
        detail_window.run()

    # def open_camera_detail(self, zone_id):
    #     """Open a new window with detailed camera view and alerts"""
    #     # Pause updates (don't cancel, just pause)
    #     self._updates_paused = True
        
    #     # Cancel camera feed updates to free the camera
    #     for callback_id in self._scheduled_callbacks:
    #         try:
    #             self.window.after_cancel(callback_id)
    #         except:
    #             pass
        
    #     # Minimize dashboard window instead of destroying
    #     self.window.iconify()
        
    #     # Handle camera for Zone 1
    #     if zone_id == 1 and self.camera is not None:
    #         # Give a small delay to ensure camera updates are stopped
    #         self.window.update_idletasks()
    #         camera_to_pass = self.camera
    #         self.camera = None  # Prevent cleanup in run()
    #         self.camera_running = False  # Mark as not running in dashboard
    #     else:
    #         camera_to_pass = None
        
    #     # Open detail window, pass reference to dashboard
    #     detail_window = CameraDetailWindow(self.username, zone_id, camera_to_pass, self.all_alerts, self.colors, self)
    #     detail_window.run()
    
    def run(self):
        self.window.mainloop()
        # Cancel any remaining callbacks
        for callback_id in self._scheduled_callbacks:
            try:
                self.window.after_cancel(callback_id)
            except:
                pass
        # Clean up camera when window actually closes (not just minimized)
        # Only release if camera wasn't passed to detail window
        if self.camera is not None:
            try:
                self.camera.release()
            except:
                pass
            cv2.destroyAllWindows()

def open_safety_dashboard(username):
    dashboard = SafetyDashboard(username)
    dashboard.run()

