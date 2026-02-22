cat > ~/githelper.sh << 'EOF'
#!/bin/bash
# 📱 GIT ALL-IN-ONE HELPER FOR MYDOCUMENTS/PROJECTS

# Colors for better visibility
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Your projects folder path
PROJECTS_PATH="/storage/emulated/0/ MyDocuments/Projects"

# Function to check if we're in the right folder
check_folder() {
    if [ ! -d "$PROJECTS_PATH" ]; then
        echo -e "${RED}❌ Projects folder not found at: $PROJECTS_PATH${NC}"
        echo -e "${YELLOW}Please check the path and update the script.${NC}"
        return 1
    fi
    cd "$PROJECTS_PATH"
    echo -e "${GREEN}✅ In projects folder: $(pwd)${NC}"
    return 0
}

# Function to show menu
show_menu() {
    clear
    echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     📱 GIT ALL-IN-ONE HELPER          ║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}MyDocuments/Projects${NC}                  ${CYAN}║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}1)${NC} Status - see what's changed        ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}2)${NC} Add + Commit + Push (all in one)   ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}3)${NC} Quick Push (with auto timestamp)   ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}4)${NC} Pull latest from GitHub           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}5)${NC} View recent commits               ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}6)${NC} Add single file                   ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}7)${NC} Undo last commit                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}8)${NC} Show branch info                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}9)${NC} List all files                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}10)${NC} Open in Acode                     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}11)${NC} Fix SSH key                      ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}12)${NC} Setup new repo                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}0)${NC} Exit                              ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Enter your choice [0-12]: ${NC}"
}

# Function for status
do_status() {
    echo -e "\n${CYAN}📊 GIT STATUS:${NC}"
    git status -s
    if [ $? -ne 0 ]; then
        echo -e "${RED}Not a git repository. Run option 12 first.${NC}"
    fi
    echo ""
}

# Function for add+commit+push
do_full_push() {
    echo -e "\n${CYAN}📦 FULL PUSH:${NC}"
    
    # Show changes
    git status -s
    echo ""
    
    # Get commit message
    echo -e "${YELLOW}Enter commit message:${NC}"
    read commit_msg
    if [ -z "$commit_msg" ]; then
        commit_msg="Update from phone $(date '+%Y-%m-%d %H:%M')"
        echo -e "${BLUE}Using default: $commit_msg${NC}"
    fi
    
    # Add all
    echo -e "\n${GREEN}➕ Adding all changes...${NC}"
    git add .
    
    # Commit
    echo -e "${GREEN}💾 Committing...${NC}"
    git commit -m "$commit_msg"
    
    # Push
    echo -e "${GREEN}☁️ Pushing to GitHub...${NC}"
    git push
    
    echo -e "\n${GREEN}✅ Done!${NC}"
}

# Function for quick push (auto timestamp)
do_quick_push() {
    echo -e "\n${CYAN}⚡ QUICK PUSH:${NC}"
    
    # Show changes
    git status -s
    
    # Auto commit message with timestamp
    commit_msg="Update $(date '+%Y-%m-%d %H:%M')"
    
    # Add all
    echo -e "${GREEN}➕ Adding all changes...${NC}"
    git add .
    
    # Commit
    echo -e "${GREEN}💾 Committing: $commit_msg${NC}"
    git commit -m "$commit_msg"
    
    # Push
    echo -e "${GREEN}☁️ Pushing to GitHub...${NC}"
    git push
    
    echo -e "\n${GREEN}✅ Quick push done!${NC}"
}

# Function for pull
do_pull() {
    echo -e "\n${CYAN}📥 PULLING FROM GITHUB:${NC}"
    git pull
    echo -e "\n${GREEN}✅ Pull complete!${NC}"
}

# Function for recent commits
do_log() {
    echo -e "\n${CYAN}📋 RECENT COMMITS:${NC}"
    git log --oneline -15 --color
    echo ""
}

# Function for adding single file
do_add_single() {
    echo -e "\n${CYAN}➕ ADD SINGLE FILE:${NC}"
    echo -e "${YELLOW}Enter filename (or part of it):${NC}"
    read filename
    
    # Find matching files
    matches=$(git ls-files --modified --others --exclude-standard | grep -i "$filename")
    
    if [ -z "$matches" ]; then
        echo -e "${RED}No matching modified/untracked files found.${NC}"
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
            echo -e "\n${GREEN}✅ Files added. Don't forget to commit!${NC}"
        fi
    fi
}

# Function for undo last commit
do_undo() {
    echo -e "\n${CYAN}↩️ UNDO LAST COMMIT:${NC}"
    echo -e "${YELLOW}Last commit:${NC}"
    git log --oneline -1
    echo ""
    echo -e "${RED}Undo last commit? (keep changes) (y/n):${NC}"
    read confirm
    
    if [ "$confirm" = "y" ]; then
        git reset --soft HEAD~1
        echo -e "${GREEN}✅ Last commit undone. Changes are staged.${NC}"
    fi
}

# Function for branch info
do_branch() {
    echo -e "\n${CYAN}🌿 BRANCH INFO:${NC}"
    git branch -a
    echo ""
    git remote -v
    echo ""
}

# Function for listing files
do_list() {
    echo -e "\n${CYAN}📂 PROJECT FILES:${NC}"
    echo -e "${YELLOW}Folders:${NC}"
    ls -d */ 2>/dev/null | sed 's/^/  📁 /'
    echo -e "\n${YELLOW}Scripts:${NC}"
    ls *.sh 2>/dev/null | sed 's/^/  📄 /'
    echo -e "\n${YELLOW}Text files:${NC}"
    ls *.txt 2>/dev/null | sed 's/^/  📝 /'
    echo ""
}

# Function for opening in Acode
do_acode() {
    echo -e "\n${CYAN}📱 OPENING IN ACODE:${NC}"
    echo -e "${YELLOW}Enter folder name to open (or press Enter for current):${NC}"
    read folder
    
    if [ -z "$folder" ]; then
        am start -n com.foxdebug.acode/.MainActivity -d "file://$(pwd)" 2>/dev/null
    else
        if [ -d "$folder" ]; then
            am start -n com.foxdebug.acode/.MainActivity -d "file://$(pwd)/$folder" 2>/dev/null
        else
            echo -e "${RED}Folder not found: $folder${NC}"
        fi
    fi
    echo -e "${GREEN}✅ Acode should open now${NC}"
}

# Function for fixing SSH
do_fix_ssh() {
    echo -e "\n${CYAN}🔑 SSH KEY FIX:${NC}"
    echo -e "${YELLOW}Your SSH key:${NC}"
    cat ~/.ssh/id_ed25519.pub 2>/dev/null || echo "No SSH key found"
    echo ""
    echo -e "${BLUE}1) Copy the key above${NC}"
    echo -e "${BLUE}2) Go to: https://github.com/settings/ssh/new${NC}"
    echo -e "${BLUE}3) Title: My Phone${NC}"
    echo -e "${BLUE}4) Paste key and save${NC}"
    echo ""
    echo -e "${YELLOW}Test connection:${NC}"
    ssh -T git@github.com
    echo ""
}

# Function for setting up new repo
do_setup() {
    echo -e "\n${CYAN}🆕 SETUP NEW REPO:${NC}"
    
    # Initialize git if needed
    if [ ! -d ".git" ]; then
        git init
        echo -e "${GREEN}✅ Git initialized${NC}"
    fi
    
    # Set user
    git config user.name "dinomadsaur-jl"
    git config user.email "dinomadsaur@gmail.com"
    
    # Create .gitignore
    cat > .gitignore << 'IGNORE'
*.tmp
*.log
*.cache
.DS_Store
Thumbs.db
*.swp
*.swo
*~
__pycache__/
*.pyc
IGNORE
    echo -e "${GREEN}✅ .gitignore created${NC}"
    
    # Check remote
    if git remote -v | grep -q origin; then
        echo -e "${YELLOW}Remote already exists:${NC}"
        git remote -v
    else
        echo -e "${YELLOW}Add remote? (y/n):${NC}"
        read add_remote
        if [ "$add_remote" = "y" ]; then
            git remote add origin git@github.com:dinomadsaur-jl/my-projects.git
            echo -e "${GREEN}✅ Remote added${NC}"
        fi
    fi
    
    # First commit if needed
    if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
        echo -e "${YELLOW}Create first commit? (y/n):${NC}"
        read first_commit
        if [ "$first_commit" = "y" ]; then
            git add .
            git commit -m "🎉 Initial commit"
            echo -e "${GREEN}✅ First commit created${NC}"
        fi
    fi
}

# Main loop
while true; do
    # Check if we can access projects folder
    if [ ! -d "$PROJECTS_PATH" ]; then
        echo -e "${RED}❌ Cannot find Projects folder at:${NC}"
        echo "$PROJECTS_PATH"
        echo ""
        echo -e "${YELLOW}Please enter the correct path:${NC}"
        read new_path
        PROJECTS_PATH="$new_path"
    else
        cd "$PROJECTS_PATH" 2>/dev/null
    fi
    
    show_menu
    read choice
    
    case $choice in
        0) 
            echo -e "${GREEN}👋 Goodbye!${NC}"
            exit 0
            ;;
        1) do_status ;;
        2) do_full_push ;;
        3) do_quick_push ;;
        4) do_pull ;;
        5) do_log ;;
        6) do_add_single ;;
        7) do_undo ;;
        8) do_branch ;;
        9) do_list ;;
        10) do_acode ;;
        11) do_fix_ssh ;;
        12) do_setup ;;
        *) 
            echo -e "${RED}Invalid choice! Press Enter to continue...${NC}"
            read
            ;;
    esac
    
    echo -e "\n${BLUE}Press Enter to return to menu...${NC}"
    read
done
EOF

# Make it executable
chmod +x ~/githelper.sh

# Create easy alias
echo "alias githelper='bash ~/githelper.sh'" >> ~/.bashrc
source ~/.bashrc

echo "✅ GIT ALL-IN-ONE HELPER INSTALLED!"
echo ""
echo "🚀 To run it, just type:"
echo "   githelper"
echo ""
echo "📱 Or run directly:"
echo "   bash ~/githelper.sh"