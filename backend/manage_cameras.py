"""
Database Management Script for User-Camera Assignments
Helps manage users and their camera access permissions
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "accounts.db")

def connect_db():
    """Connect to the database"""
    return sqlite3.connect(DB_PATH)

def list_users():
    """List all users with their assigned cameras"""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, username, email, created_at FROM users")
    users = cursor.fetchall()
    
    print("\n" + "="*80)
    print("ALL USERS AND THEIR CAMERA ASSIGNMENTS")
    print("="*80)
    
    for user in users:
        user_id, username, email, created_at = user
        print(f"\n👤 User ID: {user_id}")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print(f"   Created: {created_at}")
        
        # Get cameras for this user
        cursor.execute("""
            SELECT c.id, c.zone_id, c.name, c.type, c.is_active
            FROM cameras c
            INNER JOIN user_cameras uc ON c.id = uc.camera_id
            WHERE uc.user_id = ?
            ORDER BY c.zone_id
        """, (user_id,))
        cameras = cursor.fetchall()
        
        if cameras:
            print(f"   📷 Assigned Cameras ({len(cameras)}):")
            for cam in cameras:
                cam_id, zone_id, name, cam_type, is_active = cam
                status = "✅ Active" if is_active else "❌ Inactive"
                print(f"      - Zone {zone_id}: {name} ({cam_type}) {status}")
        else:
            print("   📷 No cameras assigned")
    
    print("\n" + "="*80 + "\n")
    conn.close()

def list_cameras():
    """List all available cameras"""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, zone_id, name, type, url, is_active FROM cameras ORDER BY zone_id")
    cameras = cursor.fetchall()
    
    print("\n" + "="*80)
    print("ALL CAMERAS IN SYSTEM")
    print("="*80)
    
    for cam in cameras:
        cam_id, zone_id, name, cam_type, url, is_active = cam
        status = "✅ Active" if is_active else "❌ Inactive"
        print(f"\n📷 Camera ID: {cam_id}")
        print(f"   Zone: {zone_id}")
        print(f"   Name: {name}")
        print(f"   Type: {cam_type}")
        print(f"   URL: {url if url else 'N/A'}")
        print(f"   Status: {status}")
        
        # Count how many users have access
        cursor.execute("SELECT COUNT(*) FROM user_cameras WHERE camera_id=?", (cam_id,))
        user_count = cursor.fetchone()[0]
        print(f"   👥 Assigned to {user_count} user(s)")
    
    print("\n" + "="*80 + "\n")
    conn.close()

def assign_camera(user_id, camera_id):
    """Assign a camera to a user"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT username FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        print(f"❌ Error: User ID {user_id} not found")
        conn.close()
        return
    
    # Check if camera exists
    cursor.execute("SELECT name FROM cameras WHERE id=?", (camera_id,))
    camera = cursor.fetchone()
    if not camera:
        print(f"❌ Error: Camera ID {camera_id} not found")
        conn.close()
        return
    
    # Assign camera
    try:
        cursor.execute("INSERT INTO user_cameras (user_id, camera_id) VALUES (?, ?)",
                     (user_id, camera_id))
        conn.commit()
        print(f"✅ Success: Assigned camera '{camera[0]}' to user '{user[0]}'")
    except sqlite3.IntegrityError:
        print(f"⚠️  Warning: Camera '{camera[0]}' already assigned to user '{user[0]}'")
    
    conn.close()

def remove_camera(user_id, camera_id):
    """Remove a camera from a user"""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM user_cameras WHERE user_id=? AND camera_id=?",
                 (user_id, camera_id))
    conn.commit()
    
    if cursor.rowcount > 0:
        print(f"✅ Success: Removed camera {camera_id} from user {user_id}")
    else:
        print(f"❌ Error: No assignment found for user {user_id} and camera {camera_id}")
    
    conn.close()

def assign_all_cameras(user_id):
    """Assign all active cameras to a user"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT username FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        print(f"❌ Error: User ID {user_id} not found")
        conn.close()
        return
    
    # Get all active cameras
    cursor.execute("SELECT id, name FROM cameras WHERE is_active=1")
    cameras = cursor.fetchall()
    
    assigned_count = 0
    for cam_id, cam_name in cameras:
        try:
            cursor.execute("INSERT INTO user_cameras (user_id, camera_id) VALUES (?, ?)",
                         (user_id, cam_id))
            assigned_count += 1
        except sqlite3.IntegrityError:
            pass  # Already assigned
    
    conn.commit()
    print(f"✅ Success: Assigned {assigned_count} camera(s) to user '{user[0]}'")
    conn.close()

def remove_all_cameras(user_id):
    """Remove all cameras from a user"""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM user_cameras WHERE user_id=?", (user_id,))
    conn.commit()
    
    print(f"✅ Success: Removed {cursor.rowcount} camera(s) from user {user_id}")
    conn.close()

def interactive_menu():
    """Interactive command-line menu"""
    while True:
        print("\n" + "="*80)
        print("📊 CAMERA ASSIGNMENT MANAGER")
        print("="*80)
        print("1. List all users and their cameras")
        print("2. List all cameras")
        print("3. Assign camera to user")
        print("4. Remove camera from user")
        print("5. Assign all cameras to user")
        print("6. Remove all cameras from user")
        print("0. Exit")
        print("="*80)
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == '1':
            list_users()
        elif choice == '2':
            list_cameras()
        elif choice == '3':
            user_id = input("Enter user ID: ").strip()
            camera_id = input("Enter camera ID: ").strip()
            try:
                assign_camera(int(user_id), int(camera_id))
            except ValueError:
                print("❌ Error: Invalid ID (must be a number)")
        elif choice == '4':
            user_id = input("Enter user ID: ").strip()
            camera_id = input("Enter camera ID: ").strip()
            try:
                remove_camera(int(user_id), int(camera_id))
            except ValueError:
                print("❌ Error: Invalid ID (must be a number)")
        elif choice == '5':
            user_id = input("Enter user ID: ").strip()
            try:
                assign_all_cameras(int(user_id))
            except ValueError:
                print("❌ Error: Invalid ID (must be a number)")
        elif choice == '6':
            user_id = input("Enter user ID: ").strip()
            try:
                remove_all_cameras(int(user_id))
            except ValueError:
                print("❌ Error: Invalid ID (must be a number)")
        elif choice == '0':
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == '__main__':
    print("\n🔧 Database Management Tool")
    print(f"📁 Database: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print("❌ Error: Database not found. Please start the backend server first.")
        exit(1)
    
    interactive_menu()
