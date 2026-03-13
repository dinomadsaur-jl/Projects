import termuxgui as tg

# Connect to the Termux:GUI plugin
conn = tg.Connection()
a = tg.Activity(conn)

# Create a simple button
tg.Button(a, "Hello Termux:GUI!")

# Keep the app running
tg.connection.loop()