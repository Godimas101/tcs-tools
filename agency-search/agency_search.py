#!/usr/bin/env python3
"""
Launch Library Agency Search Tool
Search through space agencies from The Space Devs Launch Library API
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
import json
import os
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Any

class AgencySearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 Launch Library Agency Search")
        self.root.geometry("900x700")
        
        # Data storage
        self.agencies = []
        self.filtered_agencies = []
        self.cache_file = "agencies.json"
        self.cache_max_age = timedelta(days=7)
        
        # Build UI
        self.build_ui()
        
        # Auto-load cache if it exists and is recent
        self.auto_load_cache()
    
    def build_ui(self):
        """Build the user interface"""
        
        # Top control panel
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        # Fetch button
        self.fetch_btn = ttk.Button(
            control_frame, 
            text="Fetch Agencies from API",
            command=self.fetch_agencies
        )
        self.fetch_btn.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = ttk.Label(
            control_frame,
            text="No data loaded",
            foreground="gray"
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # Search frame
        search_frame = ttk.Frame(self.root, padding="10")
        search_frame.pack(fill=tk.X)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        
        self.search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=50,
            font=("Arial", 11)
        )
        self.search_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            search_frame,
            text="🔍 Search in name, abbreviation, country, description",
            foreground="gray",
            font=("Arial", 9)
        ).pack(side=tk.LEFT, padx=5)
        
        # Results frame
        results_frame = ttk.LabelFrame(
            self.root,
            text="Results",
            padding="10"
        )
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollable text widget for results
        self.results_text = tk.Text(
            results_frame,
            wrap=tk.WORD,
            font=("Courier New", 10),
            bg="#f5f5f5"
        )
        
        scrollbar = ttk.Scrollbar(
            results_frame,
            orient=tk.VERTICAL,
            command=self.results_text.yview
        )
        self.results_text.configure(yscrollcommand=scrollbar.set)
        
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bottom button frame
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack(fill=tk.X)
        
        self.export_btn = ttk.Button(
            button_frame,
            text="Export Results to CSV",
            command=self.export_results,
            state=tk.DISABLED
        )
        self.export_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(
            button_frame,
            text="Clear Search",
            command=self.clear_search
        )
        self.clear_btn.pack(side=tk.LEFT, padx=5)
    
    def auto_load_cache(self):
        """Auto-load cached data if it exists and is recent"""
        if not os.path.exists(self.cache_file):
            return
        
        try:
            # Check cache age
            cache_time = datetime.fromtimestamp(os.path.getmtime(self.cache_file))
            age = datetime.now() - cache_time
            
            if age > self.cache_max_age:
                self.status_label.config(
                    text=f"Cache is {age.days} days old - click Fetch to update",
                    foreground="orange"
                )
                return
            
            # Load cache
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                self.agencies = json.load(f)
            
            self.filtered_agencies = self.agencies.copy()
            self.update_status()
            self.display_results()
            
        except Exception as e:
            print(f"Error loading cache: {e}")
    
    def fetch_agencies(self):
        """Fetch all agencies from the API with pagination"""
        self.status_label.config(text="Fetching agencies...", foreground="blue")
        self.fetch_btn.config(state=tk.DISABLED)
        self.root.update()
        
        all_agencies = []
        url = "https://ll.thespacedevs.com/2.3.0/agencies/?limit=100"
        page = 1
        
        try:
            while url:
                print(f"Fetching page {page}...")
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                results = data.get('results', [])
                all_agencies.extend(results)
                
                # Get next page URL
                url = data.get('next')
                page += 1
                
                self.status_label.config(
                    text=f"Fetching... {len(all_agencies)} agencies so far",
                    foreground="blue"
                )
                self.root.update()
            
            # Save to cache
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(all_agencies, f, indent=2, ensure_ascii=False)
            
            self.agencies = all_agencies
            self.filtered_agencies = all_agencies.copy()
            self.update_status()
            self.display_results()
            
            messagebox.showinfo(
                "Success",
                f"Successfully fetched {len(all_agencies)} agencies!"
            )
            
        except requests.RequestException as e:
            messagebox.showerror("Error", f"Failed to fetch agencies:\n{e}")
            self.status_label.config(text="Fetch failed", foreground="red")
        
        finally:
            self.fetch_btn.config(state=tk.NORMAL)
    
    def on_search_change(self, *args):
        """Called when search text changes - live search"""
        if not self.agencies:
            # No data loaded yet
            return
            
        query = self.search_var.get().lower().strip()
        
        print(f"Search triggered: '{query}'")  # Debug
        
        if not query:
            self.filtered_agencies = self.agencies.copy()
        else:
            self.filtered_agencies = [
                agency for agency in self.agencies
                if self.matches_query(agency, query)
            ]
        
        print(f"Found {len(self.filtered_agencies)} matches")  # Debug
        self.display_results()
    
    def matches_query(self, agency: Dict[str, Any], query: str) -> bool:
        """Check if agency matches search query"""
        # Search in name
        name = agency.get('name') or ''
        if query in name.lower():
            return True
        
        # Search in abbreviation
        abbrev = agency.get('abbrev') or ''
        if query in abbrev.lower():
            return True
        
        # Search in description (can be None)
        description = agency.get('description') or ''
        if query in description.lower():
            return True
        
        # Search in country names
        countries = agency.get('country', [])
        if countries:
            for country in countries:
                country_name = country.get('name') or ''
                if query in country_name.lower():
                    return True
        
        return False
    
    def display_results(self):
        """Display filtered results in the text widget"""
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        
        if not self.agencies:
            self.results_text.insert(tk.END, "No agencies loaded. Click 'Fetch Agencies from API' to load data.\n")
            self.export_btn.config(state=tk.DISABLED)
        elif not self.filtered_agencies:
            self.results_text.insert(tk.END, "No results found for your search.\n")
            self.export_btn.config(state=tk.DISABLED)
        else:
            self.results_text.insert(
                tk.END,
                f"Showing {len(self.filtered_agencies)} result(s):\n\n"
            )
            
            for i, agency in enumerate(self.filtered_agencies, 1):
                self.format_agency(agency, i)
            
            self.export_btn.config(state=tk.NORMAL)
        
        self.results_text.config(state=tk.DISABLED)
    
    def format_agency(self, agency: Dict[str, Any], index: int):
        """Format and display a single agency"""
        # Header line
        name = agency.get('name', 'Unknown')
        abbrev = agency.get('abbrev', 'N/A')
        agency_id = agency.get('id', 'N/A')
        
        # Get countries with detailed info
        countries = agency.get('country', [])
        country_parts = []
        for c in countries:
            country_name = c.get('name', '')
            alpha_2 = c.get('alpha_2_code', '')
            alpha_3 = c.get('alpha_3_code', '')
            if country_name:
                country_parts.append(f"{country_name} ({alpha_2}/{alpha_3})")
        country_str = ', '.join(country_parts) if country_parts else 'Unknown'
        
        self.results_text.insert(
            tk.END,
            f"{'─' * 80}\n",
            'separator'
        )
        
        self.results_text.insert(
            tk.END,
            f"{index}. {name}\n",
            'title'
        )
        
        self.results_text.insert(
            tk.END,
            f"   ID: {agency_id}  |  Abbrev: {abbrev}  |  Country: {country_str}\n\n",
            'info'
        )
        
        # Description
        description = agency.get('description', 'No description available.')
        if description:
            # Word wrap description
            words = description.split()
            lines = []
            current_line = "   "
            
            for word in words:
                if len(current_line) + len(word) + 1 <= 77:
                    current_line += word + " "
                else:
                    lines.append(current_line.rstrip() + "\n")
                    current_line = "   " + word + " "
            
            if current_line.strip():
                lines.append(current_line.rstrip() + "\n")
            
            self.results_text.insert(tk.END, ''.join(lines))
        
        self.results_text.insert(tk.END, "\n\n")
        
        # Configure tags for styling
        self.results_text.tag_config('separator', foreground='gray')
        self.results_text.tag_config('title', font=('Courier New', 10, 'bold'))
        self.results_text.tag_config('info', foreground='blue')
    
    def update_status(self):
        """Update the status label"""
        count = len(self.agencies)
        if count > 0:
            cache_time = datetime.fromtimestamp(os.path.getmtime(self.cache_file))
            age_str = cache_time.strftime("%Y-%m-%d %H:%M")
            self.status_label.config(
                text=f"✓ {count} agencies loaded (cached: {age_str})",
                foreground="green"
            )
        else:
            self.status_label.config(
                text="No data loaded",
                foreground="gray"
            )
    
    def export_results(self):
        """Export current filtered results to CSV"""
        if not self.filtered_agencies:
            messagebox.showwarning("No Data", "No results to export!")
            return
        
        # Ask for file location
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"agencies_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow(['ID', 'Name', 'Abbreviation', 'Country', 'Description'])
                
                # Data
                for agency in self.filtered_agencies:
                    countries = agency.get('country', [])
                    country_str = ', '.join([c.get('name', '') for c in countries]) if countries else ''
                    
                    writer.writerow([
                        agency.get('id', ''),
                        agency.get('name', ''),
                        agency.get('abbrev', ''),
                        country_str,
                        agency.get('description', '')
                    ])
            
            messagebox.showinfo(
                "Success",
                f"Exported {len(self.filtered_agencies)} agencies to:\n{filename}"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export:\n{e}")
    
    def clear_search(self):
        """Clear the search box"""
        self.search_var.set('')
        self.search_entry.focus()


def main():
    root = tk.Tk()
    app = AgencySearchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
