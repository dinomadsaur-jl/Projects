#!/bin/bash
echo "🚀 Setting up GitHub for dinomadsaur@gmail.com (username: dinomadsaur-jl)..."

# 1. Update Termux
echo "📦 Updating packages..."
pkg update -y && pkg upgrade -y

# 2. Install what we need
echo "🔧 Installing Git and SSH..."
pkg install git openssh -y

# 3. Allow storage access
echo "📁 Giving Termux access to your files..."
termux-setup-storage
echo "✅ Press ALLOW on your phone now!"
sleep 5

# 4. Make SSH key with YOUR email
echo "🔑 Creating your secret handshake..."
ssh-keygen -t ed25519 -C "dinomadsaur@gmail.com" -f ~/.ssh/id_ed25519 -N ""

# 5. Show the key
echo ""
echo "✅ HERE'S YOUR SECRET CODE - COPY EVERYTHING BELOW:"
echo "=================================================="
cat ~/.ssh/id_ed25519.pub
echo "=================================================="
echo ""

# 6. Open GitHub for you
echo "🌐 Opening GitHub in Chrome..."
am start -a android.intent.action.VIEW -d "https://github.com/settings/ssh/new" 2>/dev/null || echo "Please open: https://github.com/settings/ssh/new"

# 7. Wait for user
echo ""
echo "📱 STEP BY STEP IN GITHUB:"
echo "1️⃣ In 'Title' type: My Samsung Phone"
echo "2️⃣ In 'Key' paste the secret code from above"
echo "3️⃣ Click green 'Add SSH Key' button"
echo ""
echo "✅ DONE adding the key? Type 'yes' and press Enter:"
read ADDED_KEY

if [ "$ADDED_KEY" = "yes" ]; then
    echo "🔌 Testing connection to GitHub..."
    ssh -T git@github.com 2>&1 | grep -q "success" && echo "✅ Connected!" || echo "⚠️ If you see permission denied, the key wasn't copied right"
    
    # 8. Setup folders
    echo "📁 Creating projects folder in your Documents..."
    mkdir -p ~/storage/shared/Documents/GitHubProjects
    ln -sf ~/storage/shared/Documents/GitHubProjects ~/projects
    
    # 9. Configure Git with your info
    git config --global user.name "dinomadsaur-jl"
    git config --global user.email "dinomadsaur@gmail.com"
    
    echo ""
    echo "🎉🎉🎉 GITHUB IS READY! 🎉🎉🎉"
    echo ""
    echo "📂 Your projects are in: Documents/GitHubProjects"
    echo "   (Acode can open files from there!)"
    echo ""
    echo "🎯 QUICK TEST - Copy a project:"
    echo "   cd ~/projects"
    echo "   git clone git@github.com:dinomadsaur-jl/REPO-NAME.git"
    echo ""
    echo "📝 To save your code to GitHub later:"
    echo "   git add ."
    echo "   git commit -m 'what I changed'"
    echo "   git push"
    echo ""
    echo "⭐ Your GitHub page: https://github.com/dinomadsaur-jl"
else
    echo "❌ No problem! Run this script again when you're ready"
    echo "   Just copy and paste the same code again"



ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJ9X9s6utev9iSqH6Nh5plDADpbZ1JIqpbwy0GdleGkY dinomadsaur@gmail.com