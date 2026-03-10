#!/usr/bin/env python3
"""
Simple tkinter test for Termux:X11
No complex options - just the basics
"""

import os
import sys
import subprocess

# Try to connect to display :0 (Termux:X11 default)
DISPLAY = ":0"
os.environ['DISPLAY'] = DISPLAY

print("=" * 50)
print("SIMPLE TKINTER TEST FOR TERMUX:X11")
print("=" * 50)

# Step 1: Make sure DISPLAY is set
print(f"\n1. DISPLAY = {DISPLAY}")

# Step 2: Check if Termux:X11 is running
print("\n2. Checking if Termux:X11 server is running...")
try:
    # Try to see if any X server is listening
    result = subprocess.run(['xhost'], 
                          capture_output=True, 
                          text=True,
                          timeout=2)
    print("   ✓ X server is responding")
except FileNotFoundError:
    print("   ⚠ xhost not installed (not critical)")
except Exception as e:
    print(f"   ⚠ Cannot connect to display {DISPLAY}")
    print(f"   Error: {e}")
    print("\n   ❌ Termux:X11 is NOT running or not accessible")
    print("\n   SOLUTION:")
    print("   1. Open Termux:X11 app on your phone")
    print("   2. Keep it open in the background")
    print("   3. Run this script again")
    sys.exit(1)

# Step 3: Try tkinter
print("\n3. Testing tkinter...")
try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    print("   ✓ tkinter imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import tkinter: {e}")
    print("\n   SOLUTION:")
    print("   Run: pkg install python-tkinter")
    sys.exit(1)

# Step 4: Create a very simple window
print("\n4. Creating a simple window...")
print("   Look at your Termux:X11 app now!")

try:
    # Create root window - simplest possible
    root = tk.Tk()
    root.title("Termux:X11 Test")
    root.geometry("400x300")
    
    # Add a big label
    label = tk.Label(root, 
                    text="✅ TERMUX:X11 IS WORKING!\n\nClose this window to exit",
                    font=("Arial", 16),
                    fg="green")
    label.pack(expand=True, pady=50)
    
    # Add a button
    def show_message():
        messagebox.showinfo("Success", "Button clicked! tkinter works!")
    
    button = tk.Button(root, 
                      text="Click Me", 
                      command=show_message,
                      font=("Arial", 14),
                      bg="lightblue",
                      padx=20,
                      pady=10)
    button.pack()
    
    # Status
    status = tk.Label(root, 
                     text=f"Display: {DISPLAY} | PID: {os.getpid()}",
                     font=("Arial", 8),
                     fg="gray")
    status.pack(side="bottom", pady=5)
    
    print("\n   ✅ Window created! Check Termux:X11 app")
    print("   Close the window to exit")
    
    # Start the GUI
    root.mainloop()
    
    print("\n5. Window closed normally")
    
except Exception as e:
    print(f"\n   ❌ Error creating window: {e}")
    print("\n   TROUBLESHOOTING:")
    print("   1. Make sure Termux:X11 app is OPEN on your phone")
    print("   2. Try: export DISPLAY=:0")
    print("   3. Try: pkg install tk")
    print("   4. Restart Termux:X11 app")
    sys.exit(1)

print("\n" + "=" * 50)
print("✅ TEST COMPLETED SUCCESSFULLY")
print("=" * 50)