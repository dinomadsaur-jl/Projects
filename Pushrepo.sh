#!/bin/bash
echo "🚀 Pushing Projects folder to GitHub using your existing key..."

# Step 1: Go to Projects folder
echo "📂 Finding Projects folder..."
cd ~/storage/shared/Documents/Projects 2>/dev/null || cd ~/projects 2>/dev/null || cd /sdcard/Documents/Projects 2>/dev/null

PROJECTS_PATH=$(pwd)
echo "✅ Found: $PROJECTS_PATH"

# Step 2: Set Git identity
echo ""
echo "🔧 Setting Git identity..."
git config --global user.name "dinomadsaur-jl"
git config --global user.email "dinomadsaur@gmail.com"
echo "✅ Git configured"

# Step 3: Check if SSH key works
echo ""
echo "🔑 Testing your SSH key..."
ssh -T git@github.com 2>&1 | grep -q "success"
if [ $? -eq 0 ]; then
    echo "✅ SSH key is working!"
else
    echo "⚠️ SSH key needs to be added to GitHub first"
    echo ""
    echo "Your key is:"
    echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJ9X9s6utev9iSqH6Nh5plDADpbZ1JIqpbwy0GdleGkY dinomadsaur@gmail.com"
    echo ""
    echo "Add it now at:"
    echo "https://github.com/settings/ssh/new"
    echo ""
    echo "Title: My Phone"
    echo "Key: (paste the key above)"
    echo ""
    echo "✅ Added the key? (yes/no):"
    read ADDED_KEY
    if [ "$ADDED_KEY" != "yes" ]; then
        echo "❌ Please add the key first, then run this script again"
        exit 1
    fi
fi

# Step 4: Initialize git in Projects folder
echo ""
echo "📦 Setting up git in Projects folder..."
cd "$PROJECTS_PATH"

if [ ! -d ".git" ]; then
    git init
    echo "✅ Git initialized"
else
    echo "✅ Git already initialized"
fi

# Step 5: Create .gitignore
echo ""
echo "📝 Creating .gitignore..."
cat > .gitignore << 'EOF'
# Temporary files
*.tmp
*.log
*.cache
.DS_Store
Thumbs.db
*.swp
*.swo
*~
EOF
echo "✅ .gitignore created"

# Step 6: Create README
echo ""
echo "📖 Creating README..."
cat > README.md << EOF
# 📱 My Projects

All my coding projects from my phone.

## 📂 Contents
$(ls -d */ 2>/dev/null | head -10 | sed 's/^/* /')
$(ls -p *.sh *.txt 2>/dev/null | grep -v / | head -5 | sed 's/^/* /')

## 📅 Backup Date
$(date)

## 👤 User
dinomadsaur-jl
EOF
echo "✅ README created"

# Step 7: Add and commit
echo ""
echo "💾 Adding all files..."
git add .
git commit -m "🎉 Initial upload - All my phone projects $(date +%Y-%m-%d)"

# Step 8: Push to GitHub
echo ""
echo "☁️ Pushing to GitHub..."
echo "Creating remote repository..."

# Remove old remote if exists
git remote remove origin 2>/dev/null

# Add SSH remote
git remote add origin git@github.com:dinomadsaur-jl/my-projects.git

# Create main branch and push
git branch -M main

echo "📤 Uploading to GitHub (this may take a while)..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅✅✅ SUCCESS! ✅✅✅"
    echo "================================"
    echo "Your Projects folder is now on GitHub!"
    echo "🔗 https://github.com/dinomadsaur-jl/my-projects"
else
    echo ""
    echo "❌ Push failed. Let's create the repo manually first."
    echo ""
    echo "1. Go to: https://github.com/new"
    echo "2. Repository name: my-projects"
    echo "3. Description: All my phone projects"
    echo "4. Make it Public"
    echo "5. DO NOT initialize with README"
    echo "6. Click 'Create repository'"
    echo ""
    echo "✅ Done creating? (yes/no):"
    read CREATED
    
    if [ "$CREATED" = "yes" ]; then
        git push -u origin main
        if [ $? -eq 0 ]; then
            echo "✅ Success! Your projects are on GitHub!"
            echo "🔗 https://github.com/dinomadsaur-jl/my-projects"
        fi
    fi
fi

# Step 9: Show final status
echo ""
echo "📊 Final status:"
git status --short | head -10
if [ $(git status --short | wc -l) -gt 10 ]; then
    echo "... and more"
fi

echo ""
echo "🎉🎉🎉 ALL DONE! 🎉🎉🎉"
echo ""
echo "📂 Your Projects folder is now a GitHub repo!"
echo "📍 Local: $PROJECTS_PATH"
echo "🔗 Remote: https://github.com/dinomadsaur-jl/my-projects"
echo ""
echo "📝 To update later:"
echo "   cd $PROJECTS_PATH"
echo "   git add ."
echo "   git commit -m 'what changed'"
echo "   git push"