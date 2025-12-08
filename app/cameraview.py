import tkinter as tk
from tkinter import ttk
from datetime import datetime
import cv2
from PIL import Image, ImageTk
from helmet_detector import HelmetDetector

class CameraDetailWindow:
    def __init__(self, username, zone_id, camera, all_alerts, colors, dashboard=None):
        self.username = username
        self.zone_id = zone_id
        self.camera = camera
        self.all_alerts = all_alerts
        self.colors = colors
        self.camera_to_return = camera  # Store camera to return to dashboard
        self.dashboard = dashboard  # Reference to dashboard window
        
        # Initialize helmet detector (use dashboard's detector if available, otherwise create new)
        if dashboard and hasattr(dashboard, 'helmet_detector') and dashboard.helmet_detector is not None:
            self.helmet_detector = dashboard.helmet_detector
            self.detection_enabled = dashboard.detection_enabled
        else:
            try:
                self.helmet_detector = HelmetDetector(confidence_threshold=0.5)
                self.detection_enabled = True
            except Exception as e:
                print(f"Helmet detector initialization error: {e}")
                self.helmet_detector = None
                self.detection_enabled = False
        
        self.window = tk.Toplevel()
        self.window.title(f"Safe Zone {zone_id} - Camera View")
        self.window.attributes('-fullscreen', True)
        self.window.bind("<Escape>", lambda event: self.window.destroy())
        self.window.configure(bg=self.colors['bg_dark'])
        
        # Initialize camera if not provided
        self.camera_running = False
        if self.camera is None:
            # Try to find an available camera
            camera_found = False
            for camera_index in range(3):  # Try camera indices 0, 1, 2
                try:
                    test_camera = cv2.VideoCapture(camera_index)
                    if test_camera.isOpened():
                        # Try to read a frame to verify it works
                        ret, frame = test_camera.read()
                        if ret and frame is not None:
                            self.camera = test_camera
                            self.camera_running = True
                            camera_found = True
                            print(f"Camera initialized for Zone {zone_id} using index {camera_index}")
                            break
                        else:
                            test_camera.release()
                    else:
                        test_camera.release()
                except Exception as e:
                    print(f"Error testing camera index {camera_index}: {e}")
                    try:
                        if 'test_camera' in locals():
                            test_camera.release()
                    except:
                        pass
            
            if not camera_found:
                print(f"Camera failed to initialize for Zone {zone_id}")
                self.camera = None
        else:
            # Camera was passed from dashboard
            # Verify it's still working
            try:
                if self.camera.isOpened():
                    # Try to read a frame to verify
                    ret, frame = self.camera.read()
                    if ret and frame is not None:
                        self.camera_running = True
                        print(f"Using camera from dashboard for Zone {zone_id} - verified working")
                    else:
                        print(f"Camera from dashboard not working, reinitializing...")
                        # Release old camera and try to get a new one
                        try:
                            self.camera.release()
                        except:
                            pass
                        self.camera = None
                        # Try to initialize new camera
                        for camera_index in range(3):
                            try:
                                new_camera = cv2.VideoCapture(camera_index)
                                if new_camera.isOpened():
                                    ret, frame = new_camera.read()
                                    if ret and frame is not None:
                                        self.camera = new_camera
                                        self.camera_running = True
                                        print(f"Reinitialized camera for Zone {zone_id} using index {camera_index}")
                                        break
                                    else:
                                        new_camera.release()
                                else:
                                    new_camera.release()
                            except:
                                pass
                else:
                    print(f"Camera from dashboard is not opened, reinitializing...")
                    self.camera = None
                    # Try to initialize new camera (same code as above)
                    for camera_index in range(3):
                        try:
                            new_camera = cv2.VideoCapture(camera_index)
                            if new_camera.isOpened():
                                ret, frame = new_camera.read()
                                if ret and frame is not None:
                                    self.camera = new_camera
                                    self.camera_running = True
                                    print(f"Initialized new camera for Zone {zone_id} using index {camera_index}")
                                    break
                                else:
                                    new_camera.release()
                            else:
                                new_camera.release()
                        except:
                            pass
            except Exception as e:
                print(f"Error verifying camera from dashboard: {e}")
                self.camera = None
                self.camera_running = False
        
        self.setup_ui()
        
        # Track scheduled callbacks for cleanup
        self._scheduled_callbacks = []
        
        # Start camera feed update
        self._camera_update_id = None
        if self.camera_running:
            # Wait a bit for UI to be ready before starting camera feed
            print(f"Starting camera feed for Zone {zone_id}, camera_running={self.camera_running}, camera={self.camera}")
            self.window.after(200, self.update_camera_feed)  # Increased delay to ensure UI is ready
        else:
            # Show message if camera not available
            self.feed_label.config(text="Camera not available", 
                                  fg="white", 
                                  font=("Segoe UI", 20))
    
    def setup_ui(self):
        # Header Bar
        header = tk.Frame(self.window, bg=self.colors.get('bg_header', '#111111'), height=70)
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)
        
        # Yellow accent line at top
        accent_line = tk.Frame(header, bg=self.colors['accent_yellow'], height=3)
        accent_line.pack(fill=tk.X, side=tk.TOP)
        
        # Header content
        header_bg = self.colors.get('bg_header', '#111111')
        header_left = tk.Frame(header, bg=header_bg)
        header_left.pack(side=tk.LEFT, padx=30, pady=15)
        
        title_label = tk.Label(header_left, text=f"📷 Safe Zone {self.zone_id} - Live Camera Feed", 
                               font=("Segoe UI", 24, "bold"), 
                               bg=header_bg, 
                               fg=self.colors['accent_yellow'])
        title_label.pack(side=tk.LEFT)
        
        header_right = tk.Frame(header, bg=header_bg)
        header_right.pack(side=tk.RIGHT, padx=30, pady=15)
        
        # Back button
        back_button = tk.Button(header_right, 
                               text="← Back", 
                               command=self.go_back,
                               font=("Segoe UI", 12, "bold"),
                               bg=self.colors['accent_yellow'],
                               fg=self.colors['bg_dark'],
                               activebackground='#FFEB3B',
                               activeforeground=self.colors['bg_dark'],
                               relief=tk.FLAT,
                               borderwidth=0,
                               cursor="hand2",
                               padx=20,
                               pady=8)
        back_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        user_label = tk.Label(header_right, text=f"👤 {self.username}", 
                             font=("Segoe UI", 13, "bold"), 
                             bg=header_bg, 
                             fg=self.colors['accent_yellow'])
        user_label.pack(side=tk.RIGHT, padx=(15, 0))
        
        # Main Container
        main_container = tk.Frame(self.window, bg=self.colors['bg_dark'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Left side - Camera Feed (large)
        camera_section = tk.Frame(main_container, bg=self.colors['bg_dark'])
        camera_section.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20))
        
        camera_title = tk.Label(camera_section, text="📹 LIVE FEED", 
                               font=("Segoe UI", 16, "bold"), 
                               bg=self.colors['bg_dark'], 
                               fg=self.colors['accent_yellow'])
        camera_title.pack(pady=(0, 15))
        
        # Yellow divider line
        camera_divider = tk.Frame(camera_section, bg=self.colors['accent_yellow'], height=2)
        camera_divider.pack(fill=tk.X, pady=(0, 20))
        
        # Camera feed frame with card design
        cam_card = tk.Frame(camera_section, bg=self.colors['bg_card'], 
                           relief=tk.FLAT, borderwidth=1,
                           highlightbackground=self.colors['border'],
                           highlightthickness=1)
        cam_card.pack(fill=tk.BOTH, expand=True)
        
        # Yellow accent bar at top of card
        accent_bar = tk.Frame(cam_card, bg=self.colors['accent_yellow'], height=4)
        accent_bar.pack(fill=tk.X, side=tk.TOP)
        
        # Camera feed container - use Frame with Label instead of Canvas for better image handling
        feed_container = tk.Frame(cam_card, bg='#000000')
        feed_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Use Label for image display (better for PhotoImage references)
        self.feed_label = tk.Label(feed_container, bg='#000000', anchor=tk.CENTER)
        self.feed_label.pack(fill=tk.BOTH, expand=True)
        
        # Keep references to all photo images to prevent garbage collection
        self.photo_references = []  # Keep list of all photos to prevent garbage collection
        self.current_photo = None  # Initialize current photo reference
        
        # Status indicator at bottom
        status_frame = tk.Frame(cam_card, bg=self.colors['bg_card'])
        status_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        self.status_indicator = tk.Label(status_frame, text="●", 
                                       font=("Segoe UI", 20), 
                                       bg=self.colors['bg_card'], 
                                       fg=self.colors['accent_green'])
        self.status_indicator.pack(side=tk.LEFT)
        
        self.status_text = tk.Label(status_frame, text="All Workers Compliant", 
                                    font=("Segoe UI", 12), 
                                    bg=self.colors['bg_card'], 
                                    fg=self.colors['text_secondary'])
        self.status_text.pack(side=tk.LEFT, padx=15)
        
        # Right side - Alerts for this zone
        alert_sidebar = tk.Frame(main_container, bg=self.colors['bg_sidebar'], width=400)
        alert_sidebar.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(0, 0))
        alert_sidebar.pack_propagate(False)
        
        alert_title = tk.Label(alert_sidebar, text=f"🚨 ALERTS - Zone {self.zone_id}", 
                              font=("Segoe UI", 16, "bold"), 
                              bg=self.colors['bg_sidebar'], 
                              fg=self.colors['accent_yellow'])
        alert_title.pack(pady=(25, 20), padx=20)
        
        # Yellow divider line
        alert_divider = tk.Frame(alert_sidebar, bg=self.colors['accent_yellow'], height=2)
        alert_divider.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Alert scrollable area
        alert_container = tk.Frame(alert_sidebar, bg=self.colors['bg_sidebar'])
        alert_container.pack(fill=tk.BOTH, expand=True, padx=(15, 0), pady=(0, 15))
        
        alert_canvas = tk.Canvas(alert_container, bg=self.colors['bg_sidebar'], 
                                highlightthickness=0, bd=0)
        alert_scrollbar = ttk.Scrollbar(alert_container, orient="vertical", 
                                       command=alert_canvas.yview)
        alert_scrollable = tk.Frame(alert_canvas, bg=self.colors['bg_sidebar'])
        
        # Create window inside canvas
        window_id = alert_canvas.create_window((0, 0), window=alert_scrollable, anchor="nw")
        
        # Configure scrolling functions
        def on_mousewheel(event):
            """Handle mouse wheel scrolling"""
            alert_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def configure_scroll_region(event=None):
            """Update canvas width and scroll region when frame changes"""
            canvas_width = alert_canvas.winfo_width()
            if canvas_width > 1:
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
        
        # Filter and display alerts for this zone
        self.display_zone_alerts()
    
    def display_zone_alerts(self):
        """Display alerts filtered by zone_id"""
        zone_alerts = [alert for alert in self.all_alerts 
                      if alert.get('zone_id') == self.zone_id or alert.get('zone_id') is None]
        
        if not zone_alerts:
            # Show message if no alerts
            no_alerts_label = tk.Label(self.alert_frame, 
                                      text="No alerts for this zone yet", 
                                      font=("Segoe UI", 12), 
                                      bg=self.colors['bg_sidebar'], 
                                      fg=self.colors['text_secondary'])
            no_alerts_label.pack(pady=20)
        else:
            # Display each alert
            for alert_data in zone_alerts:
                self.add_alert_display(alert_data['message'], alert_data['type'], alert_data['time'])
    
    def add_alert_display(self, message, alert_type="info", time_str=""):
        """Add an alert to the display"""
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
        
        if time_str:
            time_label = tk.Label(text_frame, text=time_str, 
                                 font=("Segoe UI", 9), 
                                 bg=self.colors['bg_card'], 
                                 fg=self.colors['text_tertiary'],
                                 anchor='w')
            time_label.pack(anchor='w', pady=(2, 0))
        
        # Update scroll region
        self.alert_frame.update_idletasks()
        self.alert_canvas.update_idletasks()
        bbox = self.alert_canvas.bbox("all")
        if bbox:
            self.alert_canvas.configure(scrollregion=bbox)
            self.alert_canvas.yview_moveto(1.0)
    
    def update_camera_feed(self):
        """Update the camera feed"""
        # Check if window still exists
        try:
            if not self.window.winfo_exists():
                return
        except:
            return
        
        if self.camera_running and self.camera is not None:
            try:
                # Verify camera is still opened
                if not self.camera.isOpened():
                    print(f"Camera not opened, trying to reinitialize...")
                    # Try to reinitialize
                    for camera_index in range(3):
                        try:
                            new_camera = cv2.VideoCapture(camera_index)
                            if new_camera.isOpened():
                                ret, frame = new_camera.read()
                                if ret and frame is not None:
                                    self.camera.release()
                                    self.camera = new_camera
                                    print(f"Reinitialized camera with index {camera_index}")
                                    break
                                else:
                                    new_camera.release()
                            else:
                                new_camera.release()
                        except:
                            pass
                    else:
                        # No camera found, stop trying
                        self.camera_running = False
                        return
                
                ret, frame = self.camera.read()
                if not ret:
                    print(f"Camera read failed: ret={ret}")
                elif frame is None:
                    print(f"Camera returned None frame")
                elif ret and frame is not None:
                    print(f"Camera frame read successfully: shape={frame.shape}")
                    try:
                        # Run helmet detection if enabled (before resizing for better accuracy)
                        if self.detection_enabled and self.helmet_detector is not None:
                            try:
                                annotated_frame, detections, violation_count = self.helmet_detector.detect(frame)
                                
                                # Update status indicator
                                if violation_count > 0:
                                    self.status_indicator.config(fg=self.colors['accent_red'])
                                    self.status_text.config(
                                        text=f"{violation_count} Violation(s) Detected!",
                                        fg=self.colors['accent_red']
                                    )
                                    # Add alert if violation detected (throttle to avoid spam)
                                    if not hasattr(self, '_last_violation_alert') or \
                                       (datetime.now() - self._last_violation_alert).seconds > 5:
                                        self.dashboard.add_alert(
                                            f"Safety violation detected in Safe Zone {self.zone_id}",
                                            "danger",
                                            zone_id=self.zone_id
                                        )
                                        self._last_violation_alert = datetime.now()
                                else:
                                    self.status_indicator.config(fg=self.colors['accent_green'])
                                    self.status_text.config(
                                        text="All Workers Compliant",
                                        fg=self.colors['text_secondary']
                                    )
                                
                                # Use annotated frame (with bounding boxes)
                                frame = annotated_frame
                            except Exception as e:
                                print(f"Detection error in detail view: {e}")
                                # Continue with original frame if detection fails
                        
                        # Get label size - use update_idletasks to ensure size is calculated
                        self.feed_label.update_idletasks()
                        label_width = self.feed_label.winfo_width()
                        label_height = self.feed_label.winfo_height()
                        
                        # If label not ready yet, use default size
                        if label_width <= 1 or label_height <= 1:
                            label_width = 800
                            label_height = 600
                        
                        # Calculate aspect ratio
                        frame_height, frame_width = frame.shape[:2]
                        if frame_width == 0 or frame_height == 0:
                            # Invalid frame, skip
                            pass
                        else:
                            label_aspect = label_width / label_height
                            frame_aspect = frame_width / frame_height
                            
                            if label_aspect > frame_aspect:
                                # Label is wider, fit to height
                                new_height = label_height - 40
                                new_width = int(new_height * frame_aspect)
                            else:
                                # Label is taller, fit to width
                                new_width = label_width - 40
                                new_height = int(new_width / frame_aspect)
                            
                            # Ensure minimum size
                            if new_width < 100:
                                new_width = 100
                            if new_height < 100:
                                new_height = 100
                            
                            # Resize frame
                            frame = cv2.resize(frame, (new_width, new_height))
                            # Convert BGR to RGB
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            # Convert to PIL Image
                            image = Image.fromarray(frame_rgb)
                            # Convert to ImageTk
                            photo = ImageTk.PhotoImage(image=image)
                            
                            # Keep reference in list to prevent garbage collection
                            # Keep last 2 photos to ensure previous one stays alive during update
                            if len(self.photo_references) >= 2:
                                self.photo_references.pop(0)
                            self.photo_references.append(photo)
                            
                            # Update label with new image - Label widget handles PhotoImage better
                            old_photo = self.current_photo  # Keep old reference alive
                            self.current_photo = photo  # Set new reference
                            self.feed_label.config(image=photo)
                            self.feed_label.image = photo  # Critical: keep reference on label
                    except Exception as e:
                        print(f"Error updating canvas: {e}")
                        # Continue trying even if one frame fails
                        pass
                else:
                    # Camera read failed, but keep trying
                    pass
            except Exception as e:
                print(f"Camera read error: {e}")
                # Camera errors are expected when switching windows, but keep trying
                pass
        
        # Schedule next update only if window exists
        try:
            if self.window.winfo_exists():
                self._camera_update_id = self.window.after(30, self.update_camera_feed)
                self._scheduled_callbacks.append(self._camera_update_id)
        except:
            pass
    
    def go_back(self):
        """Go back to the dashboard"""
        # Mark that we're going back, so don't cleanup camera
        self._cleanup_needed = False
        
        # Stop all scheduled callbacks
        for callback_id in self._scheduled_callbacks:
            try:
                self.window.after_cancel(callback_id)
            except:
                pass
        self._scheduled_callbacks.clear()
        
        if hasattr(self, '_camera_update_id') and self._camera_update_id is not None:
            try:
                self.window.after_cancel(self._camera_update_id)
            except:
                pass
        
        # Close detail window
        self.window.destroy()
        
        # Restore dashboard if it exists
        if self.dashboard is not None:
            try:
                # Restore camera if it was Zone 1
                if self.zone_id == 1 and self.camera_to_return is not None:
                    self.dashboard.camera = self.camera_to_return
                    self.dashboard.camera_running = True
                
                # Update alerts in dashboard
                self.dashboard.all_alerts = self.all_alerts
                
                # Add return message
                self.dashboard.add_alert("Returned to dashboard", "info")
                
                # Resume updates
                self.dashboard._updates_paused = False
                
                # Restore window
                self.dashboard.window.deiconify()
                self.dashboard.window.lift()
                self.dashboard.window.focus_force()
                
                # Restart camera feed if Zone 1
                if self.zone_id == 1 and self.camera_to_return is not None:
                    self.dashboard.update_camera_feed()
            except Exception as e:
                print(f"Error restoring dashboard: {e}")
                # Fallback: recreate dashboard if restore fails
                self._recreate_dashboard()
        else:
            # Fallback: recreate dashboard if no reference
            self._recreate_dashboard()
    
    def _recreate_dashboard(self):
        """Fallback: recreate dashboard if restore failed"""
        alerts_to_restore = self.all_alerts.copy()
        camera_to_restore = self.camera_to_return
        zone_id = self.zone_id
        username = self.username
        
        # Recreate the dashboard
        from camera import SafetyDashboard
        dashboard = SafetyDashboard(username)
        
        # Mark that we're restoring alerts to prevent duplicate initialization
        dashboard._restoring_alerts = True
        
        # Restore camera if it was Zone 1
        if zone_id == 1 and camera_to_restore is not None:
            dashboard.camera = camera_to_restore
            dashboard.camera_running = True
            dashboard.update_camera_feed()
        
        # Clear initial alerts
        for widget in dashboard.alert_frame.winfo_children():
            widget.destroy()
        
        # Restore all alerts
        dashboard.all_alerts = alerts_to_restore
        
        # Re-add all alerts
        for alert_data in alerts_to_restore:
            dashboard.add_alert(alert_data['message'], alert_data['type'], alert_data.get('zone_id'))
        
        # Add return message
        dashboard.add_alert("Returned to dashboard", "info")
        
        dashboard.run()
    
    def run(self):
        self.window.mainloop()
        # Cancel any remaining callbacks
        for callback_id in self._scheduled_callbacks:
            try:
                self.window.after_cancel(callback_id)
            except:
                pass
        # Clean up camera when window closes (only if not going back)
        if self.camera is not None:
            if not hasattr(self, '_cleanup_needed') or self._cleanup_needed:
                try:
                    self.camera.release()
                except:
                    pass
                cv2.destroyAllWindows()

