#!/bin/bash

# Make this script executable if it isn't already
if [ ! -x "$0" ]; then
    echo "Making script executable..."
    chmod +x "$0"
    exec "$0" "$@"
    exit
fi

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for better UI
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to display banner
show_banner() {
    clear
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}                    _auto_ Python File Runner${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}Working directory:${NC} $SCRIPT_DIR"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}\n"
}

# Function to find all _auto_ files
find_auto_files() {
    # Find Python files starting with _auto_
    files=()
    while IFS= read -r -d '' file; do
        files+=("$file")
    done < <(find . -maxdepth 1 -name "_auto_*.py" -type f -print0 | sort -z)
    
    # Return the count
    echo ${#files[@]}
}

# Function to display file list with numbers
display_files() {
    echo -e "${BLUE}Available _auto_ Python files:${NC}\n"
    for i in "${!files[@]}"; do
        filename=$(basename "${files[$i]}")
        if [ -x "${files[$i]}" ]; then
            echo -e "  ${GREEN}$((i+1)).${NC} $filename ${GREEN}(executable)${NC}"
        else
            echo -e "  ${YELLOW}$((i+1)).${NC} $filename"
        fi
    done
    echo ""
}

# Function to make files executable if requested
make_executable() {
    local file_num=$1
    if [ -n "$file_num" ] && [ "$file_num" -ge 1 ] && [ "$file_num" -le ${#files[@]} ]; then
        local selected_file="${files[$((file_num-1))]}"
        if [ ! -x "$selected_file" ]; then
            chmod +x "$selected_file"
            echo -e "${GREEN}✓ Made executable:${NC} $(basename "$selected_file")"
        else
            echo -e "${YELLOW}Already executable:${NC} $(basename "$selected_file")"
        fi
    fi
}

# Function to run selected files
run_files() {
    local choices=("$@")
    local success=0
    local failed=0
    
    echo -e "\n${PURPLE}Starting execution...${NC}\n"
    
    for choice in "${choices[@]}"; do
        if [ "$choice" -ge 1 ] && [ "$choice" -le ${#files[@]} ]; then
            local selected_file="${files[$((choice-1))]}"
            local filename=$(basename "$selected_file")
            
            echo -e "${CYAN}▶ Running:${NC} $filename"
            echo -e "${YELLOW}────────────────────────────────────────────────${NC}"
            
            # Make sure it's executable
            if [ ! -x "$selected_file" ]; then
                chmod +x "$selected_file"
            fi
            
            # Run the Python file
            if python3 "$selected_file"; then
                echo -e "\n${GREEN}✓ Completed:${NC} $filename"
                ((success++))
            else
                echo -e "\n${RED}✗ Failed:${NC} $filename (exit code: $?)"
                ((failed++))
            fi
            echo -e "${YELLOW}────────────────────────────────────────────────${NC}\n"
        fi
    done
    
    # Show summary
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Execution Summary:${NC}"
    echo -e "  ${GREEN}✓ Successful:${NC} $success"
    echo -e "  ${RED}✗ Failed:${NC} $failed"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
}

# Main menu function
show_menu() {
    while true; do
        show_banner
        
        local file_count=$(find_auto_files)
        
        if [ $file_count -eq 0 ]; then
            echo -e "${RED}No _auto_*.py files found in:${NC}"
            echo -e "$SCRIPT_DIR\n"
            echo -e "${YELLOW}Options:${NC}"
            echo "  1. Refresh (check again)"
            echo "  2. Exit"
            echo ""
            read -p "Choose option [1-2]: " choice
            
            case $choice in
                1) continue ;;
                2) echo -e "\n${GREEN}Goodbye!${NC}\n"; exit 0 ;;
                *) echo -e "${RED}Invalid option${NC}"; sleep 1 ;;
            esac
            continue
        fi
        
        display_files
        
        echo -e "${YELLOW}Options:${NC}"
        echo "  • Enter numbers separated by spaces (e.g., '1 3 5') to run specific files"
        echo "  • Enter 'a' to run ALL files"
        echo "  • Enter 'm' to make a file executable"
        echo "  • Enter 'r' to refresh the list"
        echo "  • Enter 'q' to quit"
        echo ""
        
        read -p "Your choice: " user_input
        
        case $user_input in
            q|Q)
                echo -e "\n${GREEN}Goodbye!${NC}\n"
                exit 0
                ;;
            r|R)
                continue
                ;;
            a|A)
                # Run all files
                choices=()
                for i in "${!files[@]}"; do
                    choices+=($((i+1)))
                done
                run_files "${choices[@]}"
                echo -e "\nPress Enter to continue..."
                read
                ;;
            m|M)
                # Make a file executable
                read -p "Enter file number to make executable: " file_num
                if [[ "$file_num" =~ ^[0-9]+$ ]]; then
                    make_executable "$file_num"
                else
                    echo -e "${RED}Invalid input${NC}"
                fi
                sleep 1
                ;;
            *)
                # Parse numbers from input
                choices=()
                valid=true
                for num in $user_input; do
                    if [[ "$num" =~ ^[0-9]+$ ]] && [ "$num" -ge 1 ] && [ "$num" -le ${#files[@]} ]; then
                        choices+=($num)
                    else
                        echo -e "${RED}Invalid number: $num${NC}"
                        valid=false
                    fi
                done
                
                if [ "$valid" = true ] && [ ${#choices[@]} -gt 0 ]; then
                    run_files "${choices[@]}"
                    echo -e "\nPress Enter to continue..."
                    read
                else
                    echo -e "${RED}Invalid selection${NC}"
                    sleep 1
                fi
                ;;
        esac
    done
}

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed or not in PATH${NC}"
    exit 1
fi

# Start the menu
show_menu