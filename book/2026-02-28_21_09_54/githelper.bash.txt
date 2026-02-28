# ============================================
# COMPLETE GITHELPER INSTALL WITH AUTO-FIX REMOTE
# ============================================

echo "🗑️ Removing old githelper..."
rm -f ~/githelper.sh
sed -i '/alias githelper/d' ~/.bashrc 2>/dev/null
source ~/.bashrc 2>/dev/null
echo "✅ Old githelper removed"
echo ""

echo "📦 Installing new githelper with Auto-Fix Remote feature..."
echo ""

# Create the new githelper
cat > ~/githelper.sh << 'EOF'
#!/bin/bash
# 📱 GIT ALL-IN-ONE HELPER FOR MYDOCUMENTS/PROJECTS
# Version with Auto-Fix Remote URL

# Colors for better visibility
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Your projects folder path
PROJECTS_PATH="/storage/emulated/0/ MyDocuments/Projects"

# Your GitHub info
GITHUB_USER="dinomadsaur-jl"
GITHUB_EMAIL="dinomadsaur@gmail.com"
GITHUB_REPO="Projects"

# Function to auto-fix remote URL
auto_fix_remote() {
    if [ ! -d ".git" ]; then
        return
    fi
    
    # Check current remote
    current_remote=$(git remote get-url origin 2>/dev/null)
    if [ -z "$current_remote" ]; then
        return
    fi
    
    # Try to fetch and see if there's a redirect message
    fetch_output=$(git fetch 2>&1)
    
    if echo "$fetch_output" | grep -q "repository moved"; then
        echo -e "${YELLOW}⚠️ Remote repository has moved!${NC}"
        
        # Extract new URL from the message
        new_url=$(echo "$fetch_output" | grep "git@github.com:" | head -1 | awk '{print $NF}')
        
        if [ -n "$new_url" ]; then
            echo -e "${GREEN}✅ Found new URL: $new_url${NC}"
            echo -e "${YELLOW}Updating remote...${NC}"
            
            git remote set-url origin "$new_url"
            echo -e "${GREEN}✅ Remote updated to: $(git remote get-url origin)${NC}"
            
            # Also update GITHUB_REPO variable
            if [[ "$new_url" =~ github\.com[:/]([^/]+)/(.+)\.git ]]; then
                new_repo="${BASH_REMATCH[2]}"
                if [ -n "$new_repo" ] && [ "$new_repo" != "$GITHUB_REPO" ]; then
                    GITHUB_REPO="$new_repo"
                    echo -e "${GREEN}✅ Repo name updated to: $GITHUB_REPO${NC}"
                    
                    # Option to update the script permanently
                    echo -e "${YELLOW}Update githelper.sh permanently with new repo name? (y/n):${NC}"
                    read update_script
                    if [ "$update_script" = "y" ]; then
                        sed -i "s/GITHUB_REPO=\".*\"/GITHUB_REPO=\"$new_repo\"/" "$0"
                        echo -e "${GREEN}✅ githelper.sh updated permanently${NC}"
                    fi
                fi
            fi
            return 0
        fi
    fi
    return 1
}

# Function to check and fix remote before any git operation
check_and_fix_remote() {
    if [ ! -d ".git" ]; then
        return
    fi
    
    auto_fix_remote
}

# Function to draw line
draw_line() {
    echo -e "${CYAN}────────────────────────────────────────────────────${NC}"
}

# Function to show header
show_header() {
    clear
    echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     📱 GIT ALL-IN-ONE HELPER          ║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}MyDocuments/Projects${NC}                  ${CYAN}║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}GitHub:${NC} $GITHUB_USER/$GITHUB_REPO        ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
}

# Function to check if we're in the right folder
check_folder() {
    if [ ! -d "$PROJECTS_PATH" ]; then
        echo -e "${RED}❌ Projects folder not found at: $PROJECTS_PATH${NC}"
        echo -e "${YELLOW}Please enter the correct path:${NC}"
        read -r new_path
        PROJECTS_PATH="$new_path"
    fi
    cd "$PROJECTS_PATH" 2>/dev/null
    echo -e "${GREEN}✅ In projects folder: $(pwd)${NC}"
    return 0
}

# Function to show menu
show_menu() {
    show_header
    echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║              MAIN MENU                 ║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}1)${NC} 📊 Git Status                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}2)${NC} 📦 Full Push (add+commit+push)  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}3)${NC} ⚡ Quick Push (auto timestamp)   ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}4)${NC} 📥 Pull from GitHub            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}5)${NC} 📋 View Recent Commits         ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}6)${NC} ➕ Add Single File              ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}7)${NC} ↩️ Undo Last Commit             ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}8)${NC} 🌿 Branch Info                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}9)${NC} 📂 List All Files               ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}10)${NC} 📱 File Browser (Open in Acode) ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}11)${NC} 🔑 SSH Key Management          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}12)${NC} 🆕 Setup Git in This Folder    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${PURPLE}13)${NC} 🤖 Auto-Setup New Device       ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${PURPLE}14)${NC} 🔧 Fix Remote URL (Manual)     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${RED}0)${NC} 🚪 Exit                          ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Enter your choice [0-14]: ${NC}"
}

# Function for status (with auto-fix)
do_status() {
    echo -e "\n${CYAN}📊 GIT STATUS:${NC}"
    draw_line
    if [ ! -d ".git" ]; then
        echo -e "${RED}❌ Not a git repository. Run option 12 first.${NC}"
    else
        # Try to auto-fix remote first
        auto_fix_remote
        
        git status -s
        echo ""
        echo -e "${GREEN}🌿 Current branch: $(git branch --show-current 2>/dev/null)${NC}"
        echo -e "${GREEN}🔗 Remote: $(git remote get-url origin 2>/dev/null || echo 'Not set')${NC}"
    fi
}

# Function for full push (with auto-fix)
do_full_push() {
    echo -e "\n${CYAN}📦 FULL PUSH:${NC}"
    draw_line
    
    if [ ! -d ".git" ]; then
        echo -e "${RED}❌ Not a git repository. Run option 12 first.${NC}"
        return
    fi
    
    # Auto-fix remote before push
    auto_fix_remote
    
    git status -s
    echo ""
    echo -e "${YELLOW}Enter commit message:${NC}"
    read commit_msg
    if [ -z "$commit_msg" ]; then
        commit_msg="Update from phone $(date '+%Y-%m-%d %H:%M')"
        echo -e "${BLUE}Using default: $commit_msg${NC}"
    fi
    
    git add .
    git commit -m "$commit_msg"
    
    # Try push, if fails due to remote issue, fix and retry
    echo -e "${GREEN}☁️ Pushing to GitHub...${NC}"
    push_output=$(git push 2>&1)
    if echo "$push_output" | grep -q "repository moved"; then
        echo -e "${YELLOW}⚠️ Remote issue detected! Auto-fixing...${NC}"
        auto_fix_remote
        echo -e "${GREEN}✅ Retrying push...${NC}"
        git push
    else
        echo "$push_output"
    fi
    
    echo -e "\n${GREEN}✅ Done!${NC}"
}

# Function for quick push (with auto-fix)
do_quick_push() {
    echo -e "\n${CYAN}⚡ QUICK PUSH:${NC}"
    draw_line
    
    if [ ! -d ".git" ]; then
        echo -e "${RED}❌ Not a git repository. Run option 12 first.${NC}"
        return
    fi
    
    # Auto-fix remote before push
    auto_fix_remote
    
    git status -s
    commit_msg="Update $(date '+%Y-%m-%d %H:%M')"
    git add .
    git commit -m "$commit_msg"
    
    # Try push, if fails due to remote issue, fix and retry
    echo -e "${GREEN}☁️ Pushing to GitHub...${NC}"
    push_output=$(git push 2>&1)
    if echo "$push_output" | grep -q "repository moved"; then
        echo -e "${YELLOW}⚠️ Remote issue detected! Auto-fixing...${NC}"
        auto_fix_remote
        echo -e "${GREEN}✅ Retrying push...${NC}"
        git push
    else
        echo "$push_output"
    fi
    
    echo -e "\n${GREEN}✅ Quick push done!${NC}"
}

# Function for pull (with auto-fix)
do_pull() {
    echo -e "\n${CYAN}📥 PULLING FROM GITHUB:${NC}"
    draw_line
    
    if [ ! -d ".git" ]; then
        echo -e "${RED}❌ Not a git repository. Run option 12 first.${NC}"
        return
    fi
    
    # Auto-fix remote before pull
    auto_fix_remote
    
    pull_output=$(git pull 2>&1)
    if echo "$pull_output" | grep -q "repository moved"; then
        echo -e "${YELLOW}⚠️ Remote issue detected! Auto-fixing...${NC}"
        auto_fix_remote
        echo -e "${GREEN}✅ Retrying pull...${NC}"
        git pull
    else
        echo "$pull_output"
    fi
    
    echo -e "\n${GREEN}✅ Pull complete!${NC}"
}

# Manual fix remote function
do_fix_remote() {
    echo -e "\n${CYAN}🔧 MANUAL REMOTE FIX${NC}"
    draw_line
    
    if [ ! -d ".git" ]; then
        echo -e "${RED}❌ Not a git repository.${NC}"
        return
    fi
    
    echo -e "${YELLOW}Current remote:${NC}"
    git remote -v
    echo ""
    
    echo -e "${YELLOW}Enter new remote URL (or press Enter to auto-detect):${NC}"
    read new_url
    
    if [ -z "$new_url" ]; then
        # Try to auto-detect from GitHub
        echo -e "${BLUE}Attempting to auto-detect correct URL...${NC}"
        
        # Try fetching to get error message
        fetch_output=$(git fetch 2>&1)
        if echo "$fetch_output" | grep -q "git@github.com:"; then
            new_url=$(echo "$fetch_output" | grep "git@github.com:" | head -1 | awk '{print $NF}')
            echo -e "${GREEN}Found: $new_url${NC}"
        else
            # Default to known correct URL
            new_url="git@github.com:$GITHUB_USER/$GITHUB_REPO.git"
            echo -e "${BLUE}Using default: $new_url${NC}"
        fi
    fi
    
    echo -e "${YELLOW}Update remote to: $new_url ? (y/n):${NC}"
    read confirm
    
    if [ "$confirm" = "y" ]; then
        git remote set-url origin "$new_url"
        echo -e "${GREEN}✅ Remote updated!${NC}"
        git remote -v
    fi
}

# Function for recent commits
do_log() {
    echo -e "\n${CYAN}📋 RECENT COMMITS:${NC}"
    draw_line
    
    if [ ! -d ".git" ]; then
        echo -e "${RED}❌ Not a git repository. Run option 12 first.${NC}"
        return
    fi
    
    git log --oneline -15 --color
    echo ""
}

# Function for adding single file
do_add_single() {
    echo -e "\n${CYAN}➕ ADD SINGLE FILE:${NC}"
    draw_line
    
    if [ ! -d ".git" ]; then
        echo -e "${RED}❌ Not a git repository. Run option 12 first.${NC}"
        return
    fi
    
    echo -e "${YELLOW}Enter filename (or part of it):${NC}"
    read filename
    
    matches=$(git ls-files --modified --others --exclude-standard | grep -i "$filename")
    
    if [ -z "$matches" ]; then
        echo -e "${RED}No matching files found.${NC}"
    else
        echo -e "${GREEN}Matching files:${NC}"
        echo "$matches"
        echo ""
        echo -e "${YELLOW}Add all? (y/n):${NC}"
        read add_all
        
        if [ "$add_all" = "y" ]; then
            echo "$matches" | while read file; do
                git add "$file"
                echo -e "${GREEN}Added: $file${NC}"
            done
            echo -e "\n${GREEN}✅ Files added.${NC}"
        fi
    fi
}

# Function for undo last commit
do_undo() {
    echo -e "\n${CYAN}↩️ UNDO LAST COMMIT:${NC}"
    draw_line
    
    if [ ! -d ".git" ]; then
        echo -e "${RED}❌ Not a git repository. Run option 12 first.${NC}"
        return
    fi
    
    echo -e "${YELLOW}Last commit:${NC}"
    git log --oneline -1
    echo ""
    echo -e "${RED}Undo last commit? (keep changes) (y/n):${NC}"
    read confirm
    
    if [ "$confirm" = "y" ]; then
        git reset --soft HEAD~1
        echo -e "${GREEN}✅ Last commit undone.${NC}"
    fi
}

# Function for branch info
do_branch() {
    echo -e "\n${CYAN}🌿 BRANCH INFO:${NC}"
    draw_line
    
    if [ ! -d ".git" ]; then
        echo -e "${RED}❌ Not a git repository. Run option 12 first.${NC}"
        return
    fi
    
    git branch -a
    echo ""
    git remote -v
    echo ""
}

# Function for listing files
do_list() {
    echo -e "\n${CYAN}📂 PROJECT FILES:${NC}"
    draw_line
    
    echo -e "${YELLOW}Folders:${NC}"
    ls -d */ 2>/dev/null | sed 's/^/  📁 /'
    echo -e "\n${YELLOW}Scripts:${NC}"
    ls *.sh 2>/dev/null | sed 's/^/  ⚡ /'
    echo -e "\n${YELLOW}Python files:${NC}"
    ls *.py 2>/dev/null | sed 's/^/  🐍 /'
    echo -e "\n${YELLOW}HTML files:${NC}"
    ls *.html 2>/dev/null | sed 's/^/  🌐 /'
    echo -e "\n${YELLOW}Text files:${NC}"
    ls *.txt 2>/dev/null | sed 's/^/  📝 /'
    echo -e "\n${YELLOW}Other files:${NC}"
    ls -p | grep -v / | grep -v "\.sh$" | grep -v "\.py$" | grep -v "\.html$" | grep -v "\.txt$" | sed 's/^/  📄 /'
    echo ""
}

# FILE BROWSER FUNCTION
browse_files() {
    current_dir="$1"
    if [ -z "$current_dir" ]; then
        current_dir="$(pwd)"
    fi
    
    while true; do
        clear
        echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║     📂 FILE BROWSER - OPEN IN ACODE   ║${NC}"
        echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
        echo -e "${CYAN}║${NC} ${YELLOW}Current:${NC} $(basename "$current_dir")"
        echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
        
        # Parent option
        echo -e "${CYAN}║${NC} ${GREEN}[1]${NC} 📂 .. (Parent)"
        
        # List folders
        folders=()
        folder_idx=0
        while IFS= read -r folder; do
            folders+=("$folder")
            idx=$((folder_idx + 2))
            echo -e "${CYAN}║${NC} ${BLUE}[$idx]${NC} 📁 $folder"
            folder_idx=$((folder_idx + 1))
        done < <(ls -la "$current_dir" 2>/dev/null | grep '^d' | grep -v '\.$' | awk '{print $NF}' | sort)
        
        # List files
        files=()
        file_idx=0
        while IFS= read -r file; do
            files+=("$file")
            idx=$((folder_idx + file_idx + 2))
            
            # File icons
            if [[ "$file" == *.sh ]]; then icon="⚡"
            elif [[ "$file" == *.py ]]; then icon="🐍"
            elif [[ "$file" == *.html ]]; then icon="🌐"
            elif [[ "$file" == *.txt ]]; then icon="📝"
            elif [[ "$file" == *.md ]]; then icon="📖"
            elif [[ "$file" == *.json ]]; then icon="🔧"
            else icon="📄"
            fi
            
            echo -e "${CYAN}║${NC} ${PURPLE}[$idx]${NC} $icon $file"
            file_idx=$((file_idx + 1))
        done < <(ls -p "$current_dir" 2>/dev/null | grep -v / | sort)
        
        echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
        echo -e "${CYAN}║${NC} ${RED}[0]${NC} Back to main menu"
        echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${YELLOW}Enter number: ${NC}"
        read choice
        
        if [ "$choice" = "0" ]; then
            return
        elif [ "$choice" = "1" ]; then
            new_dir=$(dirname "$current_dir")
            [ "$new_dir" != "$current_dir" ] && current_dir="$new_dir"
        else
            idx=$((choice - 2))
            if [ $idx -lt ${#folders[@]} ]; then
                current_dir="$current_dir/${folders[$idx]}"
            else
                file_idx=$((idx - ${#folders[@]}))
                if [ $file_idx -ge 0 ] && [ $file_idx -lt ${#files[@]} ]; then
                    file_to_open="$current_dir/${files[$file_idx]}"
                    echo -e "${GREEN}Opening: ${files[$file_idx]}${NC}"
                    am start -n com.foxdebug.acode/.MainActivity -d "file://$file_to_open" 2>/dev/null
                    echo -e "${GREEN}✅ Opened in Acode${NC}"
                    echo ""
                    echo -e "${YELLOW}Press Enter to continue...${NC}"
                    read
                fi
            fi
        fi
    done
}

# File browser function
do_file_browser() {
    echo -e "\n${CYAN}📱 FILE BROWSER${NC}"
    draw_line
    browse_files "$(pwd)"
}

# SSH key management
do_ssh() {
    echo -e "\n${CYAN}🔑 SSH KEY MANAGEMENT${NC}"
    draw_line
    
    echo "1) Show SSH key"
    echo "2) Create new SSH key"
    echo "3) Test GitHub connection"
    echo "4) Back"
    echo ""
    echo -n "Choice: "
    read ssh_choice
    
    case $ssh_choice in
        1)
            if [ -f ~/.ssh/id_ed25519.pub ]; then
                echo -e "\n${GREEN}Your SSH key:${NC}"
                cat ~/.ssh/id_ed25519.pub
            else
                echo -e "${RED}No SSH key found${NC}"
            fi
            ;;
        2)
            ssh-keygen -t ed25519 -C "$GITHUB_EMAIL" -f ~/.ssh/id_ed25519 -N ""
            echo -e "${GREEN}✅ SSH key created${NC}"
            cat ~/.ssh/id_ed25519.pub
            ;;
        3)
            ssh -T git@github.com
            ;;
    esac
}

# Setup git in current folder
do_setup() {
    echo -e "\n${CYAN}🆕 SETUP GIT IN THIS FOLDER${NC}"
    draw_line
    
    if [ -d ".git" ]; then
        echo -e "${YELLOW}Already a git repo. Reinitialize? (y/n):${NC}"
        read reinit
        [ "$reinit" != "y" ] && return
        rm -rf .git
    fi
    
    git init
    git config user.name "$GITHUB_USER"
    git config user.email "$GITHUB_EMAIL"
    
    cat > .gitignore << 'IGNORE'
*.tmp
*.log
*.cache
.DS_Store
Thumbs.db
*.swp
__pycache__/
*.pyc
IGNORE
    
    echo -e "${GREEN}✅ Git initialized${NC}"
    echo -e "${YELLOW}Add remote? (y/n):${NC}"
    read add_remote
    
    if [ "$add_remote" = "y" ]; then
        git remote add origin "git@github.com:$GITHUB_USER/$GITHUB_REPO.git"
        echo -e "${GREEN}✅ Remote added${NC}"
    fi
    
    echo -e "${YELLOW}Create first commit? (y/n):${NC}"
    read first_commit
    
    if [ "$first_commit" = "y" ]; then
        git add .
        git commit -m "🎉 Initial commit"
        echo -e "${GREEN}✅ First commit created${NC}"
        
        echo -e "${YELLOW}Push to GitHub? (y/n):${NC}"
        read do_push
        if [ "$do_push" = "y" ]; then
            git branch -M main
            git push -u origin main
        fi
    fi
}

# Auto-setup new device
do_auto_setup() {
    echo -e "\n${PURPLE}🤖 AUTO-SETUP NEW DEVICE${NC}"
    draw_line
    
    cat > "$PROJECTS_PATH/setup_new_device.sh" << 'SETUP'
#!/bin/bash
# Auto setup script for new device

echo "🚀 Setting up GitHub repo on new device..."

# Install packages
pkg update -y && pkg install -y git openssh
termux-setup-storage

# Create projects folder
mkdir -p "/storage/emulated/0/MyDocuments/Projects"

# SSH key
ssh-keygen -t ed25519 -C "dinomadsaur@gmail.com" -f ~/.ssh/id_ed25519 -N ""
echo ""
echo "🔑 ADD THIS SSH KEY TO GITHUB:"
echo "═══════════════════════════════"
cat ~/.ssh/id_ed25519.pub
echo "═══════════════════════════════"
echo ""

read -p "✅ Added the key? (yes/no): " added

if [ "$added" = "yes" ]; then
    cd "/storage/emulated/0/MyDocuments/Projects" || exit
    git clone git@github.com:dinomadsaur-jl/Projects.git
    cd Projects || exit
    echo ""
    echo "✅ Setup complete!"
    echo "Run 'git status' to check."
fi
SETUP

    chmod +x "$PROJECTS_PATH/setup_new_device.sh"
    echo -e "${GREEN}✅ Setup script created at:${NC}"
    echo "$PROJECTS_PATH/setup_new_device.sh"
    echo ""
    echo -e "${YELLOW}Copy this script to new device and run: bash setup_new_device.sh${NC}"
}

# Main loop
while true; do
    check_folder >/dev/null 2>&1
    show_menu
    read choice
    
    case $choice in
        0) echo -e "${GREEN}👋 Goodbye!${NC}"; exit 0 ;;
        1) do_status ;;
        2) do_full_push ;;
        3) do_quick_push ;;
        4) do_pull ;;
        5) do_log ;;
        6) do_add_single ;;
        7) do_undo ;;
        8) do_branch ;;
        9) do_list ;;
        10) do_file_browser ;;
        11) do_ssh ;;
        12) do_setup ;;
        13) do_auto_setup ;;
        14) do_fix_remote ;;
        *) echo -e "${RED}Invalid choice${NC}" ;;
    esac
    
    echo -e "\n${BLUE}Press Enter to continue...${NC}"
    read
done
EOF

# Make it executable and add alias
chmod +x ~/githelper.sh
echo "alias githelper='bash ~/githelper.sh'" >> ~/.bashrc
source ~/.bashrc

echo ""
echo "✅✅✅ GITHELPER INSTALLED SUCCESSFULLY! ✅✅✅"
echo ""
echo "🚀 To run it, just type:"
echo "   githelper"
echo ""
echo "📱 NEW FEATURES:"
echo "   • 🤖 Auto-Fix Remote - automatically detects and fixes moved repositories"
echo "   • 📱 File Browser - navigate folders and open files in Acode"
echo "   • 🔧 Manual Remote Fix (Option 14)"
echo "   • Auto-detects when GitHub renames/moves your repo"
echo ""
echo "📍 Your projects folder: /storage/emulated/0/ MyDocuments/Projects"
echo "📦 GitHub repo: dinomadsaur-jl/Projects"
echo ""
echo "👉 Type 'githelper' to start!"