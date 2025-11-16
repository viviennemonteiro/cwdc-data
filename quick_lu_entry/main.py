#!/usr/bin/env python3
"""
Quick Data Entry Application for Court Lockup Numbers
Requires: pip install pynput
"""

import os
import sys
import csv
import json
from datetime import datetime
import subprocess
import platform
from pynput import keyboard

class DataEntryApp:
    def __init__(self):
        self.data = []
        self.court_date = ""
        self.current_pdf_name = ""
        self.start_lockup = 1
        self.end_lockup = 1
        self.current_lockup = 1
        self.current_entry = {
            'lockup_number': 1,
            'race': 'Black or African-American',
            'age': '',
            'gender': 'Male'
        }
        self.races = ['Black or African-American', 'Hispanic or Latino', 'White']
        self.race_index = 0  # Default to Black
        self.pdf_complete = False
        self.should_quit = False
        self.pending_save = False  # Track if we're waiting for confirmation
        
        # Load or create settings
        self.settings = self.load_settings()
        
    def load_settings(self):
        """Load settings from file or create default settings"""
        settings_file = 'data_entry_settings.json'
        
        default_settings = {
            'hotkeys': {
                'race_black': 'b',
                'race_hispanic': 'h',
                'race_white': 'w',
                'race_none': 'n',
                'gender_toggle': 'g',
                'gender_none': 'x',
                'save_and_next': 'enter',
                'quit': 'q'
            },
            'defaults': {
                'race': 'Black or African-American',
                'gender': 'Male'
            }
        }
        
        # Try to load existing settings
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults in case new keys were added
                    for key in default_settings:
                        if key not in loaded_settings:
                            loaded_settings[key] = default_settings[key]
                    print(f"Loaded settings from {settings_file}")
                    return loaded_settings
            except Exception as e:
                print(f"Error loading settings: {e}")
                print("Using default settings")
        
        # Create default settings file
        with open(settings_file, 'w') as f:
            json.dump(default_settings, f, indent=2)
        print(f"Created default settings file: {settings_file}")
        
        return default_settings
        
    def open_pdf(self, pdf_path):
        """Open PDF on left half of screen"""
        try:
            system = platform.system()
            
            if system == 'Darwin':  # macOS
                subprocess.Popen(['open', pdf_path])
                print(f"PDF opened: {pdf_path}")
            elif system == 'Windows':
                os.startfile(pdf_path)
                print(f"PDF opened: {pdf_path}")
            else:  # Linux
                subprocess.Popen(['xdg-open', pdf_path])
                print(f"PDF opened: {pdf_path}")
                
            print("Please position the PDF window on the left half of your screen.")
            input("Press Enter when ready to continue...")
            
        except Exception as e:
            print(f"Error opening PDF: {e}")
            print("Please open the PDF manually on the left side of your screen.")
            input("Press Enter when ready to continue...")
    
    def setup(self):
        """Initial setup - get folder path with PDFs"""
        print("=" * 60)
        print("COURT LOCKUP DATA ENTRY SYSTEM")
        print("=" * 60)
        
        # Get folder path
        folder_path = input("\nEnter the path to the folder containing PDFs: ").strip().strip('"').strip("'")
        
        if not os.path.exists(folder_path):
            print(f"Error: Folder not found at {folder_path}")
            sys.exit(1)
        
        if not os.path.isdir(folder_path):
            print(f"Error: {folder_path} is not a folder")
            sys.exit(1)
        
        # Get all PDF files in folder
        pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            print("Error: No PDF files found in folder")
            sys.exit(1)
        
        pdf_files.sort()  # Sort alphabetically
        
        print(f"\nFound {len(pdf_files)} PDF file(s)")
        print("\n" + "=" * 60)
        print("HOTKEY REFERENCE")
        print("=" * 60)
        print("Race Selection:")
        print(f"  [{self.settings['hotkeys']['race_black'].upper()}] - Black or African-American (default)")
        print(f"  [{self.settings['hotkeys']['race_hispanic'].upper()}] - Hispanic or Latino")
        print(f"  [{self.settings['hotkeys']['race_white'].upper()}] - White")
        print(f"  [{self.settings['hotkeys']['race_none'].upper()}] - None")
        print("\nGender:")
        print(f"  [{self.settings['hotkeys']['gender_toggle'].upper()}] - Toggle between Male/Female (default: Male)")
        print(f"  [{self.settings['hotkeys']['gender_none'].upper()}] - None")
        print("\nAge:")
        print("  [0-9] - Enter age (type digits)")
        print("  [Backspace] - Delete last digit")
        print("\nNavigation:")
        print(f"  [Enter] - Save current entry and move to next")
        print(f"  [Up Arrow] - Go back to previous lockup number")
        print(f"  [Down Arrow] - Go forward to next lockup number")
        print(f"  [{self.settings['hotkeys']['quit'].upper()}] - Quit and save all data to CSV")
        print("=" * 60)
        print(f"\nSettings can be customized in: data_entry_settings.json")
        print("=" * 60)
        input("\nPress Enter to start data entry...")
        
        return folder_path, pdf_files
    
    def setup_pdf(self, pdf_path, pdf_name):
        """Setup for each individual PDF"""
        os.system('clear' if os.name == 'posix' else 'cls')
        print("=" * 60)
        print(f"PROCESSING: {pdf_name}")
        print("=" * 60)
        
        # Store the current PDF name (full name with extension)
        self.current_pdf_name = pdf_name
        
        # Open PDF
        self.open_pdf(pdf_path)
        
        # Get court date
        self.court_date = input("\nEnter court date (e.g., 2024-01-15): ").strip()
        
        # Get start lockup number
        while True:
            try:
                self.start_lockup = int(input("Enter START lockup number: "))
                if self.start_lockup > 0:
                    break
                print("Please enter a positive number.")
            except ValueError:
                print("Please enter a valid number.")
        
        # Get end lockup number
        while True:
            try:
                self.end_lockup = int(input("Enter END lockup number: "))
                if self.end_lockup >= self.start_lockup:
                    break
                print(f"End number must be >= start number ({self.start_lockup}).")
            except ValueError:
                print("Please enter a valid number.")
        
        # Initialize current lockup
        self.current_lockup = self.start_lockup
        self.current_entry = {
            'lockup_number': self.current_lockup,
            'race': 'Black or African-American',
            'age': '',
            'gender': 'Male'
        }
        self.pdf_complete = False
    
    def display_current_entry(self):
        """Display current entry status"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        # Check if current lockup has been entered
        is_entered = False
        for entry in self.data:
            if entry['lockup_number'] == self.current_lockup and entry['court_date'] == self.court_date and entry['file_name'] == self.current_pdf_name:
                is_entered = True
                break
        
        # ANSI color codes
        GREEN = '\033[92m'
        RED = '\033[91m'
        BLUE = '\x1b[34m'
        YELLOW = '\033[93m'
        MAGENTA = '\x1b[35m'
        CYAN = '\x1b[36m'
        RESET = '\033[0m'
        BOLD = '\033[1m'
        
        status_text = f"{GREEN}{BOLD}✓ ENTERED{RESET}" if is_entered else f"{RED}{BOLD}✗ NOT ENTERED{RESET}"
        
        print("=" * 60)
        print(f"LOCKUP NUMBER: {self.current_lockup} (Range: {self.start_lockup}-{self.end_lockup})")
        print(f"Status: {status_text}")
        print(f"Court Date: {self.court_date}")
        print("=" * 60)
        if self.current_entry['race'] == 'Black or African-American':
            race_display = ' 1 | Black or African-American'
        elif self.current_entry['race'] == 'Hispanic or Latino':
            race_display = '2 | Hispanic or Latino'
        elif self.current_entry['race'] == 'White':
            race_display = '3 | White'
        else: 
            race_display = 'NONE'
        print(f"\nRace: {BOLD}{race_display}{RESET}")
        print(f"Age: {f"{BOLD}{self.current_entry['age']}{RESET}" if self.current_entry['age'] else '(not entered)'}")
        if self.current_entry['gender'] == "Male":
            gender_display = f"{CYAN}{BOLD}{self.current_entry['gender']}{RESET}"
        elif self.current_entry['gender'] == "Female":
            gender_display = f"{MAGENTA}{BOLD}{self.current_entry['gender']}{RESET}"
        else:
            gender_display = "NONE"
        print(f"Gender: {gender_display}")
        print("\n" + "=" * 60)
        
        if self.pending_save:
            print(f"{YELLOW}{BOLD}⚠ WARNING: No age entered! Press Enter again to confirm.{RESET}")
            print("=" * 60)
        else:
            print("Press hotkeys to enter data | [Enter] to save | [Q] to quit")
            print("=" * 60)
        
        if self.pending_save:
            print(f"{YELLOW}{BOLD}⚠ WARNING: No age entered! Press Enter again to confirm.{RESET}")
            print("=" * 60)
        else:
            print("Press hotkeys to enter data | [Enter] to save | [Q] to quit")
            print("=" * 60)
    
    def save_current_entry(self):
        """Save current entry to data list"""
        # Check if age is missing and we haven't confirmed yet
        if not self.current_entry['age'] and not self.pending_save:
            self.pending_save = True
            self.display_current_entry()
            return True  # Don't advance yet
        
        # Reset pending save flag
        self.pending_save = False
        
        entry = {
            'file_name': self.current_pdf_name,
            'court_date': self.court_date,
            'lockup_number': self.current_lockup,
            'race': self.current_entry['race'],
            'age': self.current_entry['age'],
            'gender': self.current_entry['gender'],
            'entry_method': 'entry_app',
            'entry_date': datetime.today()
        }
        
        # Find if this lockup number already exists in data
        existing_index = None
        for i, e in enumerate(self.data):
            if e['lockup_number'] == self.current_lockup and e['court_date'] == self.court_date and e['file_name'] == self.current_pdf_name:
                existing_index = i
                break
        
        if existing_index is not None:
            # Update existing entry
            self.data[existing_index] = entry
        else:
            # Add new entry
            self.data.append(entry)
        
        # Move to next lockup
        if self.current_lockup < self.end_lockup:
            self.current_lockup += 1
            self.current_entry = {
                'lockup_number': self.current_lockup,
                'race': 'Black or African-American',
                'age': '',
                'gender': 'Male'
            }
            self.load_entry_if_exists()
            self.display_current_entry()
            return True
        else:
            print(f"\nCompleted lockup numbers {self.start_lockup}-{self.end_lockup}!")
            self.pdf_complete = True
            return False
    
    def go_to_previous(self):
        """Go back to previous lockup number"""
        if self.current_lockup > self.start_lockup:
            self.pending_save = False  # Reset confirmation when navigating
            self.current_lockup -= 1
            self.current_entry = {
                'lockup_number': self.current_lockup,
                'race': 'Black or African-American',
                'age': '',
                'gender': 'Male'
            }
            self.load_entry_if_exists()
            self.display_current_entry()
    
    def go_to_next(self):
        """Go forward to next lockup number (but not past the furthest entered)"""
        self.pending_save = False  # Reset confirmation when navigating
        
        # Find the highest lockup number that has been entered
        max_entered = self.start_lockup - 1
        for entry in self.data:
            if entry['court_date'] == self.court_date and entry['lockup_number'] > max_entered and entry['file_name'] == self.current_pdf_name:
                max_entered = entry['lockup_number']
        
        # Allow going to the next unentered lockup, but not beyond
        if self.current_lockup < min(max_entered + 1, self.end_lockup):
            self.current_lockup += 1
            self.current_entry = {
                'lockup_number': self.current_lockup,
                'race': 'Black or African-American',
                'age': '',
                'gender': 'Male'
            }
            self.load_entry_if_exists()
            self.display_current_entry()
    
    def load_entry_if_exists(self):
        """Load existing data for current lockup number if it exists"""
        for entry in self.data:
            if entry['lockup_number'] == self.current_lockup and entry['court_date'] == self.court_date and entry['file_name'] == self.current_pdf_name:
                self.current_entry['race'] = entry['race']
                self.current_entry['age'] = entry['age']
                self.current_entry['gender'] = entry['gender']
                break
    
    def save_to_csv(self):
        """Save all data to CSV file"""
        if not self.data:
            print("\nNo data to save.")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"lockup_data_{timestamp}.csv"
        
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['file_name', 'court_date', 'lockup_number', 'race', 'age', 'gender', 'entry_method', 'entry_date']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for entry in self.data:
                writer.writerow(entry)
        
        print(f"\nData saved to: {filename}")
        print(f"Total entries: {len(self.data)}")
    
    def on_press(self, key):
        """Handle key press events"""
        try:
            hotkeys = self.settings['hotkeys']
            
            # Handle alphanumeric keys
            if hasattr(key, 'char') and key.char:
                char = key.char.lower()
                
                # Race selection
                if char == hotkeys['race_black']:
                    self.current_entry['race'] = 'Black or African-American'
                    self.display_current_entry()
                elif char == hotkeys['race_hispanic']:
                    self.current_entry['race'] = 'Hispanic or Latino'
                    self.display_current_entry()
                elif char == hotkeys['race_white']:
                    self.current_entry['race'] = 'White'
                    self.display_current_entry()
                elif char == hotkeys['race_none']:
                    self.current_entry['race'] = 'None'
                    self.display_current_entry()
                
                # Gender
                elif char == hotkeys['gender_toggle']:
                    if self.current_entry['gender'] == 'Male':
                        self.current_entry['gender'] = 'Female'
                    elif self.current_entry['gender'] == 'Female':
                        self.current_entry['gender'] = 'Male'
                    else:  # If it was None, toggle to Male
                        self.current_entry['gender'] = 'Male'
                    self.display_current_entry()
                elif char == hotkeys['gender_none']:
                    self.current_entry['gender'] = 'None'
                    self.display_current_entry()
                
                # Age entry
                elif char.isdigit():
                    if len(self.current_entry['age']) < 3:
                        self.current_entry['age'] += char
                        self.pending_save = False  # Reset confirmation if user starts entering age
                        self.display_current_entry()
                
                # Quit
                elif char == hotkeys['quit']:
                    print("\nQuitting...")
                    self.should_quit = True
                    return False  # Stop listener
            
            # Handle special keys
            elif key == keyboard.Key.backspace:
                if self.current_entry['age']:
                    self.current_entry['age'] = self.current_entry['age'][:-1]
                    self.display_current_entry()
            
            elif key == keyboard.Key.up:
                self.go_to_previous()
            
            elif key == keyboard.Key.down:
                self.go_to_next()
            
            elif key == keyboard.Key.enter:
                self.save_current_entry()
                if self.pdf_complete:
                    return False  # Stop listener for this PDF
                    
        except AttributeError:
            pass
    
    def run(self):
        """Main application loop"""
        folder_path, pdf_files = self.setup()
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(folder_path, pdf_file)
            self.setup_pdf(pdf_path, pdf_file)
            self.display_current_entry()
            
            print("\nListening for hotkeys... (Make sure this terminal window is focused)")
            
            # Start keyboard listener for this PDF with suppression
            with keyboard.Listener(on_press=self.on_press, suppress=True) as listener:
                listener.join()
            
            # Check if user quit
            if self.should_quit:
                self.save_to_csv()
                return
            
            # PDF complete, show summary and continue to next
            print(f"Entries saved for {pdf_file}")
            if pdf_file != pdf_files[-1]:
                input("\nPress Enter to continue to next PDF...")
        
        # All PDFs processed
        print("\n" + "=" * 60)
        print("ALL PDFs PROCESSED!")
        print("=" * 60)
        self.save_to_csv()

if __name__ == "__main__":
    try:
        app = DataEntryApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        if app.data:
            print("Saving data...")
            app.save_to_csv()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)