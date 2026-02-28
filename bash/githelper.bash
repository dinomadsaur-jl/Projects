# ============================================
# COMPLETE GITHELPER INSTALLATION
# Fork first, then Config, then File, then History, then Branch, then Basic
# ============================================

echo "🗑️ Removing old githelper..."
rm -f ~/githelper.sh
sed -i '/alias githelper/d' ~/.bashrc 2>/dev/null
source ~/.bashrc 2>/dev/null
echo "✅ Old githelper removed"
echo ""

echo "📦 Installing complete githelper with reordered categories..."
echo ""

# Create the new githelper
cat > ~/githelper.sh << 'EOF'
#!/bin/bash
# 📱 COMPLETE GIT HELPER
# Beginner-friendly explanations – now with File before History

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Your paths
PROJECTS_PATH="/storage/emulated/0/ MyDocuments/Projects"
GITHUB_USER="dinomadsaur-jl"
GITHUB_EMAIL="dinomadsaur@gmail.com"
GITHUB_REPO="Projects"

# ============================================
# UTILITY FUNCTIONS
# ============================================

auto_fix_remote() {
    [ ! -d ".git" ] && return
    current_remote=$(git remote get-url origin 2>/dev/null)
    [ -z "$current_remote" ] && return
    fetch_output=$(git fetch 2>&1)
    if echo "$fetch_output" | grep -q "repository moved"; then
        echo -e "${YELLOW}⚠️ Remote repository has moved!${NC}"
        new_url=$(echo "$fetch_output" | grep "git@github.com:" | head -1 | awk '{print $NF}')
        if [ -n "$new_url" ]; then
            git remote set-url origin "$new_url"
            echo -e "${GREEN}✅ Remote updated to: $(git remote get-url origin)${NC}"
            if [[ "$new_url" =~ github\.com[:/]([^/]+)/(.+)\.git ]]; then
                new_repo="${BASH_REMATCH[2]}"
                if [ -n "$new_repo" ] && [ "$new_repo" != "$GITHUB_REPO" ]; then
                    GITHUB_REPO="$new_repo"
                    echo -e "${GREEN}✅ Repo name updated to: $GITHUB_REPO${NC}"
                    echo -e "${YELLOW}Update githelper.sh permanently? (y/n):${NC}"
                    read update_script
                    if [ "$update_script" = "y" ]; then
                        sed -i "s/GITHUB_REPO=\".*\"/GITHUB_REPO=\"$new_repo\"/" "$0"
                    fi
                fi
            fi
        fi
    fi
}

draw_line() { echo -e "${CYAN}────────────────────────────────────────────────────${NC}"; }

show_header() {
    clear
    echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║        📱 COMPLETE GIT HELPER         ║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}$(basename "$PROJECTS_PATH")${NC}                              ${CYAN}║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}GitHub:${NC} $GITHUB_USER/$GITHUB_REPO        ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
}

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

pause() {
    echo -e "\n${BLUE}Press Enter to continue...${NC}"
    read
}

# ============================================
# MENU (Fork, Config, File, History, Branch, Basic)
# ============================================

show_menu() {
    show_header
    echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          FORK OPERATIONS (1-3)         ║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${BLUE}1)${NC} 🍴 Add Upstream Remote         ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BLUE}2)${NC} 🔄 Sync Fork with Upstream     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BLUE}3)${NC} 📥 Fetch from Upstream         ${CYAN}║${NC}"
    
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║          CONFIGURATION (4-7)           ║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${WHITE}4)${NC} 🔧 Fix Remote URL (Manual)     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${WHITE}5)${NC} 🔑 SSH Key Management          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${WHITE}6)${NC} 🆕 Setup Git in This Folder    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${WHITE}7)${NC} 🤖 Auto-Setup New Device       ${CYAN}║${NC}"
    
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║          FILE OPERATIONS (8-12)        ║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}8)${NC} 📂 List All Files             ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}9)${NC} 📱 File Browser (Acode)       ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}10)${NC} 🧹 Clean Untracked Files     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}11)${NC} 📦 Stash Changes             ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${YELLOW}12)${NC} ➕ Add Single File           ${CYAN}║${NC}"
    
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║         HISTORY & SEARCH (13-18)       ║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}13)${NC} 📋 View Recent Commits        ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}14)${NC} 🔍 View Commit Details        ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}15)${NC} 🔎 Search in Commits          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}16)${NC} 📊 Compare Changes            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}17)${NC} ↩️ Undo/Revert Options        ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}18)${NC} 📊 Repo Statistics            ${CYAN}║${NC}"
    
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║         BRANCH OPERATIONS (19-24)      ║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${PURPLE}19)${NC} 🌿 Create New Branch           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${PURPLE}20)${NC} 🔀 Switch Branch               ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${PURPLE}21)${NC} 🔗 Merge Branch into Current   ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${PURPLE}22)${NC} 🔀 Merge Current into Main     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${PURPLE}23)${NC} 🗑️ Delete Branch               ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${PURPLE}24)${NC} 📋 List All Branches           ${CYAN}║${NC}"
    
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║         BASIC OPERATIONS (25-30)       ║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}25)${NC} 📊 Git Status                   ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}26)${NC} 📦 Full Push (add+commit+push) ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}27)${NC} ⚡ Quick Push (auto timestamp)  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}28)${NC} 📥 Pull from GitHub            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}29)${NC} 📡 Fetch Only (all remotes)    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}30)${NC} 📥 Fetch main into current     ${CYAN}║${NC}"
    
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${RED}0)${NC} 🚪 Exit                          ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Enter your choice [0-30]: ${NC}"
}

# ============================================
# FORK OPERATIONS (1-3)
# ============================================

do_add_upstream() {
    echo -e "\n${CYAN}🍴 ADD UPSTREAM REMOTE${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Connects your fork (your copy) of a project to the original repository.${NC}"
    echo -e "${YELLOW}Why: So you can later pull updates from the original project into your fork.${NC}"
    echo -e "${YELLOW}Git term: 'upstream' = the original repository you forked from.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    echo -e "${YELLOW}Current remotes (connections):${NC}"
    git remote -v
    echo ""
    echo -e "${YELLOW}Enter the URL of the original repository (e.g., git@github.com:original-owner/repo.git):${NC}"
    read upstream_url
    if [ -n "$upstream_url" ]; then
        git remote add upstream "$upstream_url"
        echo -e "${GREEN}✅ Upstream added! Now you can fetch updates from the original project.${NC}"
        git remote -v
    else
        echo -e "${YELLOW}Cancelled.${NC}"
    fi
}

do_sync_fork() {
    echo -e "\n${CYAN}🔄 SYNC FORK WITH UPSTREAM${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Downloads new changes from the original project (upstream) and combines them with your current branch.${NC}"
    echo -e "${YELLOW}Why: To keep your fork up-to-date with the latest developments.${NC}"
    echo -e "${YELLOW}Git term: This is a 'fetch' (download) followed by a 'merge' (combine).${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    if ! git remote | grep -q "upstream"; then
        echo -e "${RED}❌ No upstream remote found. Use option 1 first to add it.${NC}"
        return
    fi
    current_branch=$(git branch --show-current)
    echo -e "${YELLOW}Fetching updates from upstream...${NC}"
    git fetch upstream
    echo -e "${YELLOW}Now merging upstream/$current_branch into your current branch ($current_branch)...${NC}"
    echo -e "${YELLOW}Merging combines the downloaded changes with your work.${NC}"
    git merge upstream/$current_branch
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Your fork is now synced with the original project!${NC}"
        echo -e "${YELLOW}Push these updates to your GitHub fork? (y/n):${NC}"
        read push_updates
        [ "$push_updates" = "y" ] && git push origin $current_branch
    else
        echo -e "${RED}⚠️ Merge conflict – the same files were changed in both places. You'll need to resolve manually.${NC}"
    fi
}

do_fetch_upstream() {
    echo -e "\n${CYAN}📥 FETCH FROM UPSTREAM${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Downloads new changes from the original project but does NOT combine them yet.${NC}"
    echo -e "${YELLOW}Why: To see what's new before deciding to merge. Safe way to preview updates.${NC}"
    echo -e "${YELLOW}Git term: 'fetch' = download only; 'merge' = combine later.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    if ! git remote | grep -q "upstream"; then
        echo -e "${RED}❌ No upstream remote. Use option 1 first.${NC}"
        return
    fi
    git fetch upstream
    echo -e "${GREEN}✅ Updates fetched. Use option 2 (Sync Fork) to merge them when you're ready.${NC}"
}

# ============================================
# CONFIGURATION OPERATIONS (4-7)
# ============================================

do_fix_remote() {
    echo -e "\n${CYAN}🔧 MANUAL REMOTE FIX${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Changes the internet address that Git uses to connect to GitHub.${NC}"
    echo -e "${YELLOW}Why: If GitHub renamed your repository or you switched from HTTPS to SSH.${NC}"
    echo -e "${YELLOW}Git term: 'remote URL' = the address of your repository on GitHub.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    echo -e "${YELLOW}Current remote URL:${NC}"
    git remote -v
    echo ""
    echo -e "${YELLOW}Enter the new URL (or press Enter to cancel):${NC}"
    read new_url
    if [ -n "$new_url" ]; then
        git remote set-url origin "$new_url"
        echo -e "${GREEN}✅ Remote URL updated!${NC}"
        git remote -v
    else
        echo -e "${YELLOW}Cancelled.${NC}"
    fi
}

do_ssh() {
    echo -e "\n${CYAN}🔑 SSH KEY MANAGEMENT${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Helps you create and manage SSH keys – a secure way to connect to GitHub without typing a password every time.${NC}"
    echo -e "${YELLOW}Git term: SSH = Secure Shell, a protocol for secure communication.${NC}"
    while true; do
        echo ""
        echo "1) Show my public SSH key (to add to GitHub)"
        echo "2) Create a new SSH key"
        echo "3) Test connection to GitHub"
        echo "4) Back to main menu"
        echo ""
        read ssh_choice
        case $ssh_choice in
            1)
                if [ -f ~/.ssh/id_ed25519.pub ]; then
                    echo -e "${GREEN}Your public SSH key (copy this to GitHub):${NC}"
                    cat ~/.ssh/id_ed25519.pub
                else
                    echo -e "${RED}No SSH key found. Use option 2 to create one.${NC}"
                fi
                pause
                ;;
            2)
                ssh-keygen -t ed25519 -C "$GITHUB_EMAIL" -f ~/.ssh/id_ed25519 -N ""
                echo -e "${GREEN}✅ SSH key created!${NC}"
                echo -e "${YELLOW}Add this public key to GitHub (Settings → SSH keys):${NC}"
                cat ~/.ssh/id_ed25519.pub
                pause
                ;;
            3)
                ssh -T git@github.com
                pause
                ;;
            4) break ;;
            *) echo -e "${RED}Invalid choice${NC}"; pause ;;
        esac
    done
}

do_setup() {
    echo -e "\n${CYAN}🆕 SETUP GIT IN THIS FOLDER${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Turns the current folder into a Git repository.${NC}"
    echo -e "${YELLOW}Why: You need to do this once per project before using Git.${NC}"
    echo -e "${YELLOW}Git term: 'git init' creates a new repository.${NC}"
    if [ -d ".git" ]; then
        echo -e "${YELLOW}This folder is already a Git repo. Reinitialize (start over)? (y/n):${NC}"
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
__pycache__/
*.pyc
IGNORE
    echo -e "${GREEN}✅ Git initialized!${NC}"
    echo -e "${YELLOW}Add a remote connection to GitHub? (y/n):${NC}"
    read add_remote
    if [ "$add_remote" = "y" ]; then
        git remote add origin "git@github.com:$GITHUB_USER/$GITHUB_REPO.git"
        echo -e "${GREEN}✅ Remote added. Your local repo is now linked to GitHub.${NC}"
    fi
    echo -e "${YELLOW}Create your first commit? (y/n):${NC}"
    read first_commit
    if [ "$first_commit" = "y" ]; then
        git add .
        git commit -m "🎉 Initial commit"
        echo -e "${GREEN}✅ First commit created!${NC}"
    fi
}

do_auto_setup() {
    echo -e "\n${CYAN}🤖 AUTO-SETUP NEW DEVICE${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Creates a helper script that will set up Git on a brand new phone/device.${NC}"
    echo -e "${YELLOW}Why: To quickly get started on a new device without remembering all the steps.${NC}"
    cat > "$PROJECTS_PATH/setup_new_device.sh" << 'SETUP'
#!/bin/bash
echo "🚀 Setting up GitHub repo on new device..."
pkg update -y && pkg install -y git openssh
termux-setup-storage
mkdir -p "/storage/emulated/0/MyDocuments/Projects"
ssh-keygen -t ed25519 -C "dinomadsaur@gmail.com" -f ~/.ssh/id_ed25519 -N ""
echo ""
echo "🔑 ADD THIS SSH KEY TO GITHUB:"
cat ~/.ssh/id_ed25519.pub
echo ""
read -p "✅ Added the key? (yes/no): " added
if [ "$added" = "yes" ]; then
    cd "/storage/emulated/0/MyDocuments/Projects" || exit
    git clone git@github.com:dinomadsaur-jl/Projects.git
    echo "✅ Setup complete!"
fi
SETUP
    chmod +x "$PROJECTS_PATH/setup_new_device.sh"
    echo -e "${GREEN}✅ Setup script created at: $PROJECTS_PATH/setup_new_device.sh${NC}"
    echo -e "${YELLOW}Copy this script to new device and run: bash setup_new_device.sh${NC}"
}

# ============================================
# FILE OPERATIONS (8-12)
# ============================================

do_list_files() {
    echo -e "\n${CYAN}📂 PROJECT FILES${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Lists all files and folders in the current directory.${NC}"
    echo -e "${YELLOW}Why: To see what's in your project folder.${NC}"
    echo -e "${YELLOW}Folders:${NC}"
    ls -d */ 2>/dev/null | sed 's/^/  📁 /'
    echo -e "\n${YELLOW}Files:${NC}"
    ls -p | grep -v / | sed 's/^/  📄 /'
    echo ""
    echo -e "${GREEN}Total: $(ls -1 | wc -l) items${NC}"
}

do_file_browser() {
    echo -e "\n${CYAN}📱 FILE BROWSER (Open in Acode)${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Lets you select a file from the current folder and open it in the Acode editor.${NC}"
    echo -e "${YELLOW}Why: To quickly edit files without navigating manually.${NC}"
    echo -e "${YELLOW}Files in current folder:${NC}"
    ls -p | grep -v / | nl
    echo ""
    echo -e "${YELLOW}Enter the number of the file to open (or 0 to cancel):${NC}"
    read file_num
    [ "$file_num" = "0" ] && return
    file_to_open=$(ls -p | grep -v / | sed -n "${file_num}p")
    if [ -n "$file_to_open" ]; then
        am start -n com.foxdebug.acode/.MainActivity -d "file://$(pwd)/$file_to_open" 2>/dev/null
        echo -e "${GREEN}Opening $file_to_open in Acode...${NC}"
    else
        echo -e "${RED}Invalid selection.${NC}"
    fi
}

do_clean() {
    echo -e "\n${CYAN}🧹 CLEAN UNTRACKED FILES${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Removes files that Git isn't tracking yet.${NC}"
    echo -e "${YELLOW}Why: To clean up temporary files or build artifacts.${NC}"
    echo -e "${YELLOW}Git term: 'untracked' = files not added to Git.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    echo -e "${YELLOW}Untracked files:${NC}"
    git ls-files --others --exclude-standard
    echo ""
    echo "1) Dry run – show what would be deleted (safe)"
    echo "2) Delete untracked files"
    echo "3) Delete untracked files and directories"
    echo "4) Cancel"
    read clean_choice
    case $clean_choice in
        1) git clean -n ;;
        2) git clean -f; echo -e "${GREEN}✅ Files deleted.${NC}" ;;
        3) git clean -fd; echo -e "${GREEN}✅ Files and directories deleted.${NC}" ;;
        *) echo -e "${YELLOW}Cancelled.${NC}" ;;
    esac
}

do_stash() {
    echo -e "\n${CYAN}📦 STASH CHANGES${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Temporarily saves your uncommitted changes and cleans your working directory.${NC}"
    echo -e "${YELLOW}Why: To switch branches or pull updates without committing half-done work.${NC}"
    echo -e "${YELLOW}Git term: 'stash' = a stack of temporary saves.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    while true; do
        echo ""
        echo "1) Stash changes (save temporarily)"
        echo "2) List stashes"
        echo "3) Apply latest stash (keep stash)"
        echo "4) Pop latest stash (apply and remove)"
        echo "5) Drop a specific stash"
        echo "6) Back"
        echo ""
        read stash_choice
        case $stash_choice in
            1)
                echo -e "${YELLOW}Enter a description (optional):${NC}"; read msg
                [ -z "$msg" ] && git stash || git stash push -m "$msg"
                echo -e "${GREEN}✅ Changes stashed.${NC}"
                pause
                ;;
            2) git stash list; pause ;;
            3) git stash apply; echo -e "${GREEN}✅ Stash applied.${NC}"; pause ;;
            4) git stash pop; echo -e "${GREEN}✅ Stash popped (applied and removed).${NC}"; pause ;;
            5)
                echo -e "${YELLOW}Enter stash index (e.g., stash@{0}):${NC}"; read idx
                git stash drop "$idx"
                echo -e "${GREEN}✅ Stash dropped.${NC}"
                pause
                ;;
            6) break ;;
            *) echo -e "${RED}Invalid choice${NC}"; pause ;;
        esac
    done
}

do_add_single() {
    echo -e "\n${CYAN}➕ ADD SINGLE FILE${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Stages a specific file (prepares it for commit) and optionally commits/pushes it.${NC}"
    echo -e "${YELLOW}Why: When you only want to commit one file instead of all changes.${NC}"
    echo -e "${YELLOW}Git term: 'stage' = mark changes to be included in the next commit.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    echo -e "${YELLOW}Enter the filename:${NC}"
    read filename
    [ ! -f "$filename" ] && { echo -e "${RED}File not found.${NC}"; return; }
    git add "$filename"
    echo -e "${GREEN}✅ File staged.${NC}"
    echo -e "\n${YELLOW}Commit now? (y/n):${NC}"
    read commit_now
    if [ "$commit_now" = "y" ]; then
        echo -e "${YELLOW}Enter commit message:${NC}"
        read commit_msg
        git commit -m "$commit_msg"
        echo -e "${GREEN}✅ Committed.${NC}"
        echo -e "${YELLOW}Push to GitHub now? (y/n):${NC}"
        read push_now
        [ "$push_now" = "y" ] && git push
    fi
}

# ============================================
# HISTORY & SEARCH OPERATIONS (13-18)
# ============================================

do_log() {
    echo -e "\n${CYAN}📋 RECENT COMMITS${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Shows a list of the last 20 commits (snapshots) with short messages.${NC}"
    echo -e "${YELLOW}Why: To see what changes have been made recently and by whom.${NC}"
    echo -e "${YELLOW}Git term: 'commit' = a saved snapshot of your project.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    git log --oneline --decorate -20 --color
}

do_show_commit() {
    echo -e "\n${CYAN}🔍 VIEW COMMIT DETAILS${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Shows full details of a specific commit – what files changed, and the exact changes.${NC}"
    echo -e "${YELLOW}Why: To understand exactly what was modified in that commit.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    git log --oneline -10
    echo ""
    echo -e "${YELLOW}Enter the commit hash (the unique ID, or just the first few characters) – or press Enter to cancel:${NC}"
    read commit_hash
    [ -z "$commit_hash" ] && { echo -e "${YELLOW}Cancelled.${NC}"; return; }
    git show --stat "$commit_hash"
    echo -e "\n${YELLOW}Show the full changes (line-by-line)? (y/n):${NC}"
    read show_diff
    [ "$show_diff" = "y" ] && git show "$commit_hash"
}

do_search() {
    echo -e "\n${CYAN}🔎 SEARCH IN COMMITS${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Searches for a word or phrase in commit messages, in code changes, or in file contents.${NC}"
    echo -e "${YELLOW}Why: To find when a particular feature was added or a bug was fixed.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    echo -e "${YELLOW}Enter search term:${NC}"
    read search_term
    [ -z "$search_term" ] && { echo -e "${RED}No term entered.${NC}"; return; }
    echo -e "\n${CYAN}In commit messages:${NC}"
    git log --oneline --grep="$search_term" --color
    echo -e "\n${CYAN}In code changes (when the term was added/removed):${NC}"
    git log -S"$search_term" --oneline --color
    echo -e "\n${CYAN}In file content (limited to recent commits):${NC}"
    git grep "$search_term" $(git rev-list --all --max-count=20) 2>/dev/null | head -20
}

do_diff() {
    echo -e "\n${CYAN}📊 COMPARE CHANGES${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Shows differences between versions of files.${NC}"
    echo -e "${YELLOW}Why: To see what you've changed before committing, or to compare two commits.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    while true; do
        echo ""
        echo "1) Show changes you haven't staged yet (unstaged)"
        echo "2) Show changes you have staged (ready to commit)"
        echo "3) Compare the last commit with the one before it"
        echo "4) Compare any two commits"
        echo "5) Show the history of a specific file"
        echo "6) Back to main menu"
        echo ""
        read diff_choice
        case $diff_choice in
            1) git diff; pause ;;
            2) git diff --staged; pause ;;
            3) git diff HEAD~1 HEAD; pause ;;
            4)
                echo -e "${YELLOW}Enter first commit hash:${NC}"; read c1
                echo -e "${YELLOW}Enter second commit hash:${NC}"; read c2
                [ -n "$c1" ] && [ -n "$c2" ] && git diff "$c1" "$c2"
                pause
                ;;
            5)
                echo -e "${YELLOW}Enter filename:${NC}"; read fname
                [ -n "$fname" ] && git log -p -- "$fname"
                pause
                ;;
            6) break ;;
            *) echo -e "${RED}Invalid choice${NC}"; pause ;;
        esac
    done
}

do_undo() {
    echo -e "\n${CYAN}↩️ UNDO/REVERT OPTIONS${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Lets you undo or revert changes in different ways.${NC}"
    echo -e "${YELLOW}Git term: 'reset' moves the branch pointer, 'revert' creates a new commit that undoes changes.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    echo -e "${YELLOW}Last 5 commits:${NC}"
    git log --oneline -5
    echo ""
    echo "╔════════════════════════════════════════╗"
    echo "║         UNDO/REVERT OPTIONS            ║"
    echo "╠════════════════════════════════════════╣"
    echo "║ 1) Undo last commit (keep changes)    ║"
    echo "║    (moves HEAD back, changes remain)  ║"
    echo "║ 2) Undo last commit (discard changes) ║"
    echo "║    (dangerous: deletes changes)       ║"
    echo "║ 3) Revert to specific commit (safe)   ║"
    echo "║    (creates new commit that undoes)   ║"
    echo "║ 4) View files at a commit             ║"
    echo "║    (list files only)                   ║"
    echo "║ 5) Compare working copy with a commit ║"
    echo "║ 6) Back to main menu                  ║"
    echo "╚════════════════════════════════════════╝"
    echo ""
    read undo_choice
    case $undo_choice in
        1)
            git reset --soft HEAD~1
            echo -e "${GREEN}✅ Last commit undone. Your changes are now staged (ready to recommit).${NC}"
            git status -s
            ;;
        2)
            echo -e "\n${RED}⚠️  This will permanently DELETE all changes from the last commit!${NC}"
            echo -e "${YELLOW}Are you absolutely sure? (y/n):${NC}"
            read confirm
            [ "$confirm" = "y" ] && { git reset --hard HEAD~1; echo -e "${GREEN}✅ Last commit removed and changes discarded.${NC}"; }
            ;;
        3)
            echo -e "\n${YELLOW}Enter the commit hash you want to go back to (the state you want):${NC}"
            read target
            [ -z "$target" ] && return
            git show --oneline "$target"
            echo -e "\n${YELLOW}How do you want to go back?${NC}"
            echo "1) Create a new commit that undoes changes (safe – recommended)"
            echo "2) Hard reset to that commit (⚠️  DANGEROUS – deletes all later commits)"
            echo ""
            read revert_type
            case $revert_type in
                1)
                    git revert --no-commit "$target"..HEAD
                    echo -e "${YELLOW}Review the changes and commit the revert? (y/n):${NC}"
                    read cr
                    if [ "$cr" = "y" ]; then
                        git commit -m "Reverted to $target"
                        echo -e "${GREEN}✅ Revert commit created. History is preserved.${NC}"
                    else
                        git revert --abort
                        echo -e "${YELLOW}Revert cancelled.${NC}"
                    fi
                    ;;
                2)
                    echo -e "${RED}⚠️  This will DELETE all commits after $target. Type 'YES' to confirm:${NC}"
                    read confirm_reset
                    [ "$confirm_reset" = "YES" ] && { git reset --hard "$target"; echo -e "${GREEN}✅ Reset to $target. Later commits are gone.${NC}"; }
                    ;;
            esac
            ;;
        4)
            echo -e "\n${YELLOW}Enter commit hash to see its files:${NC}"; read view_commit
            [ -n "$view_commit" ] && git ls-tree --name-only -r "$view_commit"
            ;;
        5)
            echo -e "\n${YELLOW}Enter commit hash to compare with current working copy:${NC}"; read compare_commit
            [ -n "$compare_commit" ] && git diff "$compare_commit" --stat
            ;;
    esac
}

do_stats() {
    echo -e "\n${CYAN}📊 REPOSITORY STATISTICS${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Shows various numbers about your repository – commits, branches, contributors, etc.${NC}"
    echo -e "${YELLOW}Why: To get a quick overview of project activity.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    echo -e "${GREEN}Total commits:${NC} $(git rev-list --count HEAD 2>/dev/null || echo "N/A")"
    echo -e "${GREEN}Branches:${NC} $(git branch -a | wc -l)"
    echo -e "${GREEN}Current branch:${NC} $(git branch --show-current)"
    echo -e "${GREEN}Last commit:${NC} $(git log -1 --oneline)"
    echo -e "${GREEN}Tracked files:${NC} $(git ls-files | wc -l)"
    echo -e "\n${GREEN}Top contributors:${NC}"
    git shortlog -sn | head -10
}

# ============================================
# BRANCH OPERATIONS (19-24)
# ============================================

do_create_branch() {
    echo -e "\n${CYAN}🌿 CREATE NEW BRANCH${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Creates a new branch (separate line of development) and switches to it.${NC}"
    echo -e "${YELLOW}Why: To work on a new feature without affecting the main code.${NC}"
    echo -e "${YELLOW}Git term: 'branch' = a movable pointer to a commit.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    echo -e "${YELLOW}Current branch: $(git branch --show-current)${NC}"
    echo -e "${YELLOW}Enter new branch name:${NC}"
    read branch_name
    [ -z "$branch_name" ] && { echo -e "${YELLOW}Cancelled.${NC}"; return; }
    git checkout -b "$branch_name"
    echo -e "${GREEN}✅ Created and switched to branch '$branch_name'.${NC}"
    echo -e "${YELLOW}Push this branch to GitHub? (y/n):${NC}"
    read push_branch
    [ "$push_branch" = "y" ] && git push -u origin "$branch_name"
}

do_switch_branch() {
    echo -e "\n${CYAN}🔀 SWITCH BRANCH${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Switches to another existing branch.${NC}"
    echo -e "${YELLOW}Why: To move between different lines of development.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    git branch -a
    echo ""
    echo -e "${YELLOW}Enter the branch name to switch to:${NC}"
    read branch_name
    [ -z "$branch_name" ] && { echo -e "${YELLOW}Cancelled.${NC}"; return; }
    git checkout "$branch_name"
    echo -e "${GREEN}✅ Switched to branch '$branch_name'.${NC}"
}

do_merge_into_current() {
    echo -e "\n${CYAN}🔗 MERGE BRANCH INTO CURRENT${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Combines another branch's changes into your current branch.${NC}"
    echo -e "${YELLOW}Why: To bring updates from a feature branch back into main, or vice versa.${NC}"
    echo -e "${YELLOW}Git term: 'merge' = combine two branches.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    echo -e "${YELLOW}Current branch: $(git branch --show-current)${NC}"
    git branch
    echo ""
    echo -e "${YELLOW}Enter the name of the branch to merge INTO the current branch:${NC}"
    read merge_branch
    [ -z "$merge_branch" ] && { echo -e "${YELLOW}Cancelled.${NC}"; return; }
    git merge "$merge_branch"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Merge successful!${NC}"
        echo -e "${YELLOW}Push the merged changes? (y/n):${NC}"
        read push_merge
        [ "$push_merge" = "y" ] && git push
    else
        echo -e "${RED}⚠️ Merge conflict. The same files were changed in both branches; you'll need to resolve manually.${NC}"
    fi
}

do_merge_current_into_main() {
    echo -e "\n${CYAN}🔀 MERGE CURRENT BRANCH INTO MAIN${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Switches to the main branch, merges your current branch into it, and optionally switches back.${NC}"
    echo -e "${YELLOW}Why: To integrate a completed feature into the main codebase.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    current_branch=$(git branch --show-current)
    if [ "$current_branch" = "main" ] || [ "$current_branch" = "master" ]; then
        echo -e "${YELLOW}You are already on main/master. Use option 21 to merge another branch into it.${NC}"
        return
    fi
    echo -e "${YELLOW}Current branch: $current_branch${NC}"
    echo -e "${YELLOW}This will switch to main, merge $current_branch, then optionally return.${NC}"
    echo -e "${YELLOW}Proceed? (y/n):${NC}"
    read proceed
    [ "$proceed" != "y" ] && return
    # Determine main branch name
    if git show-ref --verify --quiet refs/heads/main; then
        main_branch="main"
    elif git show-ref --verify --quiet refs/heads/master; then
        main_branch="master"
    else
        echo -e "${RED}No main/master branch found.${NC}"
        return
    fi
    git checkout "$main_branch"
    git pull  # ensure main is up-to-date
    git merge "$current_branch"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Merged $current_branch into $main_branch.${NC}"
        echo -e "${YELLOW}Push $main_branch to GitHub? (y/n):${NC}"
        read push_main
        [ "$push_main" = "y" ] && git push
        echo -e "${YELLOW}Switch back to $current_branch? (y/n):${NC}"
        read back
        [ "$back" = "y" ] && git checkout "$current_branch"
    else
        echo -e "${RED}⚠️ Merge conflict. Resolve on $main_branch manually.${NC}"
    fi
}

do_delete_branch() {
    echo -e "\n${CYAN}🗑️ DELETE BRANCH${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Deletes a branch locally and optionally on GitHub.${NC}"
    echo -e "${YELLOW}Why: To clean up branches that are no longer needed.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    git branch
    echo ""
    echo -e "${YELLOW}Enter the branch name to delete:${NC}"
    read branch_name
    [ -z "$branch_name" ] && { echo -e "${YELLOW}Cancelled.${NC}"; return; }
    echo -e "${RED}Delete locally? (y/n):${NC}"
    read confirm
    [ "$confirm" = "y" ] && { git branch -d "$branch_name"; echo -e "${GREEN}✅ Deleted locally.${NC}"; }
    echo -e "${YELLOW}Delete from GitHub? (y/n):${NC}"
    read delete_remote
    [ "$delete_remote" = "y" ] && { git push origin --delete "$branch_name"; echo -e "${GREEN}✅ Deleted remotely.${NC}"; }
}

do_list_branches() {
    echo -e "\n${CYAN}📋 LIST ALL BRANCHES${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Shows all local and remote branches.${NC}"
    echo -e "${YELLOW}Why: To see what branches exist and which one you're on.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    echo -e "${GREEN}Local branches:${NC}"
    git branch
    echo -e "\n${GREEN}Remote branches (on GitHub):${NC}"
    git branch -r
}

# ============================================
# BASIC OPERATIONS (25-30)
# ============================================

do_status() {
    echo -e "\n${CYAN}📊 GIT STATUS${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Shows which files are changed, staged, or untracked.${NC}"
    echo -e "${YELLOW}Why: To see the current state of your working directory before committing.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository. Use option 6 to set one up.${NC}"; return; }
    auto_fix_remote
    git status -s
    echo ""
    echo -e "${GREEN}Current branch: $(git branch --show-current)${NC}"
    echo -e "${GREEN}Remote URL: $(git remote get-url origin 2>/dev/null || echo 'Not set')${NC}"
}

do_full_push() {
    echo -e "\n${CYAN}📦 FULL PUSH${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Adds all changes, creates a commit with your message, and pushes to GitHub.${NC}"
    echo -e "${YELLOW}Why: The standard way to upload your work.${NC}"
    echo -e "${YELLOW}Git terms: 'add' stages changes, 'commit' saves a snapshot, 'push' uploads to GitHub.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    auto_fix_remote
    git status -s
    echo ""
    echo -e "${YELLOW}Enter a commit message (describe what you changed):${NC}"
    read commit_msg
    [ -z "$commit_msg" ] && commit_msg="Update $(date '+%Y-%m-%d %H:%M')"
    git add .
    git commit -m "$commit_msg"
    git push
    echo -e "\n${GREEN}✅ Push complete.${NC}"
}

do_quick_push() {
    echo -e "\n${CYAN}⚡ QUICK PUSH${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Automatically adds all changes, commits with a timestamp, and pushes.${NC}"
    echo -e "${YELLOW}Why: For when you want to quickly save and upload without typing a message.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    auto_fix_remote
    commit_msg="Update $(date '+%Y-%m-%d %H:%M')"
    git add .
    git commit -m "$commit_msg"
    git push
    echo -e "\n${GREEN}✅ Quick push done.${NC}"
}

do_pull() {
    echo -e "\n${CYAN}📥 PULL FROM GITHUB${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Downloads changes from GitHub and merges them into your current branch.${NC}"
    echo -e "${YELLOW}Why: To get the latest updates from others.${NC}"
    echo -e "${YELLOW}Git term: 'pull' = fetch + merge.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    auto_fix_remote
    echo -e "${YELLOW}Pulling...${NC}"
    git pull
    echo -e "\n${GREEN}✅ Pull complete.${NC}"
}

do_fetch_all() {
    echo -e "\n${CYAN}📡 FETCH ONLY (all remotes)${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Downloads changes from GitHub but does NOT merge them.${NC}"
    echo -e "${YELLOW}Why: To see what's new without affecting your working files. Safe preview.${NC}"
    echo -e "${YELLOW}Git term: 'fetch' = download only.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    auto_fix_remote
    git fetch --all --prune
    echo -e "\n${GREEN}✅ Fetch complete. No changes were merged.${NC}"
}

do_fetch_main() {
    echo -e "\n${CYAN}📥 FETCH MAIN INTO CURRENT${NC}"
    draw_line
    echo -e "${YELLOW}What it does: Fetches updates from the remote main branch and optionally merges them into your current branch.${NC}"
    echo -e "${YELLOW}Why: To bring your feature branch up-to-date with the latest main code.${NC}"
    echo -e "${YELLOW}Git term: 'fetch' then optional 'merge'.${NC}"
    [ ! -d ".git" ] && { echo -e "${RED}❌ Not a git repository.${NC}"; return; }
    # Determine remote main branch name
    if git show-ref --verify --quiet refs/remotes/origin/main; then
        remote_main="origin/main"
    elif git show-ref --verify --quiet refs/remotes/origin/master; then
        remote_main="origin/master"
    else
        echo -e "${RED}Could not find remote main/master branch.${NC}"
        return
    fi
    current_branch=$(git branch --show-current)
    echo -e "${YELLOW}Current branch: $current_branch${NC}"
    echo -e "${YELLOW}Fetching from $remote_main...${NC}"
    git fetch origin $(basename "$remote_main"):$(basename "$remote_main") --prune
    echo ""
    echo -e "${CYAN}New commits on main:${NC}"
    git log HEAD.."$remote_main" --oneline --color
    echo ""
    echo -e "${YELLOW}Merge $remote_main into $current_branch? (y/n):${NC}"
    read merge_choice
    if [ "$merge_choice" = "y" ]; then
        git merge "$remote_main"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Merge successful. Your branch is now up-to-date with main.${NC}"
            echo -e "${YELLOW}Push? (y/n):${NC}"
            read push_choice
            [ "$push_choice" = "y" ] && git push
        else
            echo -e "${RED}⚠️ Merge conflict. Resolve manually.${NC}"
        fi
    else
        echo -e "${YELLOW}Fetch only – no merge performed. You can merge later.${NC}"
    fi
}

# ============================================
# MAIN LOOP
# ============================================

while true; do
    check_folder >/dev/null 2>&1
    show_menu
    read choice
    
    case $choice in
        0) echo -e "${GREEN}👋 Goodbye!${NC}"; exit 0 ;;
        # Fork
        1) do_add_upstream ;;
        2) do_sync_fork ;;
        3) do_fetch_upstream ;;
        # Config
        4) do_fix_remote ;;
        5) do_ssh ;;
        6) do_setup ;;
        7) do_auto_setup ;;
        # File
        8) do_list_files ;;
        9) do_file_browser ;;
        10) do_clean ;;
        11) do_stash ;;
        12) do_add_single ;;
        # History
        13) do_log ;;
        14) do_show_commit ;;
        15) do_search ;;
        16) do_diff ;;
        17) do_undo ;;
        18) do_stats ;;
        # Branch
        19) do_create_branch ;;
        20) do_switch_branch ;;
        21) do_merge_into_current ;;
        22) do_merge_current_into_main ;;
        23) do_delete_branch ;;
        24) do_list_branches ;;
        # Basic
        25) do_status ;;
        26) do_full_push ;;
        27) do_quick_push ;;
        28) do_pull ;;
        29) do_fetch_all ;;
        30) do_fetch_main ;;
        *) echo -e "${RED}Invalid choice${NC}" ;;
    esac
    
    pause
done
EOF

# Make it executable and add alias
chmod +x ~/githelper.sh
echo "alias githelper='bash ~/githelper.sh'" >> ~/.bashrc
source ~/.bashrc 2>/dev/null

echo ""
echo "✅✅✅ GITHELPER INSTALLED SUCCESSFULLY! ✅✅✅"
echo ""
echo "📱 MENU ORDER (File before History):"
echo "   • Fork (1-3)          - Upstream, Sync, Fetch"
echo "   • Configuration (4-7)  - Remote, SSH, Setup, Auto-Device"
echo "   • File Operations (8-12)"
echo "   • History & Search (13-18)"
echo "   • Branch Operations (19-24) – includes Merge Current into Main"
echo "   • Basic Operations (25-30)   – Status, Push, Pull, Fetch, Fetch main into current"
echo ""
echo "📍 Projects folder: $PROJECTS_PATH"
echo "📦 GitHub repo: $GITHUB_USER/$GITHUB_REPO"
echo ""
echo "👉 Type 'githelper' to start!"