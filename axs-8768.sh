
rm -f ~/.shortcuts/axs-8768 && cat > ~/.shortcuts/axs-8768 << 'EOF'
#!/data/data/com.termux/files/usr/bin/sh
echo "=== AXS Port 8768 Manager ==="

# Kill any existing axs process on port 8768
pkill -f "axs.*--port 8768" 2>/dev/null
sleep 1

# Start fresh
axs --port 8768 &
echo "✅ AXS restarted on port 8768"
echo ""
echo "Press ENTER to close"
read dummy
EOF

chmod +x ~/.shortcuts/axs-8768