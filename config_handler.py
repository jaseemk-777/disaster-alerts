"""
Configuration Handler for Global Hazard News Extraction Pipeline
Handles user input for hazard specifications, keywords, locations, newspapers, and links
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re


class HazardConfig:
    """Configuration class for hazard news extraction"""
    
    def __init__(self):
        self.disaster_id = None
        self.hazard_names = {}
        self.keywords = {}
        self.locations = {}
        self.newspapers = {}
        self.specific_links = []
        self.languages = []
        self.country_codes = ['IN']  # Default to India only
        self.start_date = None
        self.end_date = None
        
    @classmethod
    def from_user_input(cls, interactive=True):
        """Create configuration from user input"""
        config = cls()
        
        if interactive:
            print("\n" + "="*80)
            print("🌍 GLOBAL HAZARD NEWS EXTRACTION PIPELINE")
            print("="*80)
            
            # Get disaster ID
            config.disaster_id = input("\n📝 Enter Disaster ID (e.g., '2025-cyclone-montha'): ").strip()
            if not config.disaster_id:
                raise ValueError("Disaster ID is required")
            
            # Get date range
            config._get_date_range_input()
            
            # Get hazard names
            config._get_hazard_names_input()
            
            # Get keywords
            config._get_keywords_input()
            
            # Get locations
            config._get_locations_input()
            
            # Get newspapers
            config._get_newspapers_input()
            
            # Get specific links
            config._get_specific_links_input()
            
            # Get country codes
            config._get_country_codes_input()
            
            # Extract unique languages
            config._extract_languages()
            
        return config
    
    @classmethod
    def from_json_file(cls, filepath):
        """Load configuration from JSON file"""
        config = cls()
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        config.disaster_id = data.get('disaster_id')
        config.hazard_names = data.get('hazard_names', {})
        config.keywords = data.get('keywords', {})
        config.locations = data.get('locations', {})
        config.newspapers = data.get('newspapers', {})
        config.specific_links = data.get('specific_links', [])
        config.country_codes = data.get('country_codes', ['IN'])  # Default to India
        
        # Parse dates
        if 'start_date' in data:
            config.start_date = datetime.strptime(data['start_date'], '%d/%m/%Y').date()
        if 'end_date' in data:
            config.end_date = datetime.strptime(data['end_date'], '%d/%m/%Y').date()
        
        config._extract_languages()
        
        return config
    
    def _get_date_range_input(self):
        """Get date range from user"""
        print("\n📅 DATE RANGE")
        
        date_format_msg = "Enter date in DD/MM/YYYY format"
        
        while True:
            start_str = input(f"Start date ({date_format_msg}): ").strip()
            try:
                self.start_date = datetime.strptime(start_str, '%d/%m/%Y').date()
                break
            except ValueError:
                print("❌ Invalid date format. Please use DD/MM/YYYY")
        
        while True:
            end_str = input(f"End date ({date_format_msg}, press Enter for same as start): ").strip()
            if not end_str:
                self.end_date = self.start_date
                break
            try:
                self.end_date = datetime.strptime(end_str, '%d/%m/%Y').date()
                if self.end_date >= self.start_date:
                    break
                else:
                    print("❌ End date must be after or equal to start date")
            except ValueError:
                print("❌ Invalid date format. Please use DD/MM/YYYY")
        
        print(f"✅ Date range: {self.start_date.strftime('%d/%m/%Y')} to {self.end_date.strftime('%d/%m/%Y')}")
    
    def _get_hazard_names_input(self):
        """Get hazard names in multiple languages"""
        print("\n🌪️ HAZARD NAMES")
        print("Enter hazard names in multiple languages (JSON format)")
        print("Example: {\"en\": [\"Cyclone Montha\"], \"hi\": [\"चक्रवात मोंथा\"]}")
        print("Or provide file path to JSON file")
        
        user_input = input("Hazard names (JSON or file path): ").strip()
        
        if os.path.isfile(user_input):
            with open(user_input, 'r', encoding='utf-8') as f:
                self.hazard_names = json.load(f)
        else:
            try:
                self.hazard_names = json.loads(user_input)
            except json.JSONDecodeError:
                print("❌ Invalid JSON format. Using English default.")
                hazard_name = input("Enter hazard name in English: ").strip()
                self.hazard_names = {"en": [hazard_name]}
        
        print(f"✅ Loaded hazard names in {len(self.hazard_names)} languages")
    
    def _get_keywords_input(self):
        """Get keywords in multiple languages"""
        print("\n🔑 KEYWORDS")
        print("Enter keywords in multiple languages (JSON format)")
        print("Or provide file path to JSON file")
        print("Press Enter to use default monsoon keywords")
        
        user_input = input("Keywords (JSON/file path/Enter for default): ").strip()
        
        if not user_input:
            # Use default keywords from language_map
            from language_map import get_climate_impact_terms
            self.keywords = {}
            for lang_code in ['en', 'hi', 'te', 'ta', 'ml', 'kn', 'bn', 'gu', 'mr', 'or', 'pa']:
                self.keywords[lang_code] = get_climate_impact_terms(lang_code)
            print(f"✅ Using default monsoon keywords in {len(self.keywords)} languages")
        elif os.path.isfile(user_input):
            with open(user_input, 'r', encoding='utf-8') as f:
                self.keywords = json.load(f)
            print(f"✅ Loaded keywords from file in {len(self.keywords)} languages")
        else:
            try:
                self.keywords = json.loads(user_input)
                print(f"✅ Loaded keywords in {len(self.keywords)} languages")
            except json.JSONDecodeError:
                print("❌ Invalid JSON format. Using default monsoon keywords.")
                from language_map import get_climate_impact_terms
                self.keywords = {"en": get_climate_impact_terms("en")}
    
    def _get_locations_input(self):
        """Get hierarchical location data"""
        print("\n📍 LOCATIONS")
        print("Enter locations (JSON format with hierarchy)")
        print("Example: {\"Andhra Pradesh\": {\"districts\": {\"Visakhapatnam\": [\"Visakhapatnam\"]}}}")
        print("Or provide file path to JSON file")
        print("Press Enter to skip location-specific filtering")
        
        user_input = input("Locations (JSON/file path/Enter to skip): ").strip()
        
        if not user_input:
            self.locations = {}
            print("⚠️ No specific locations provided. Will search broadly.")
        elif os.path.isfile(user_input):
            with open(user_input, 'r', encoding='utf-8') as f:
                self.locations = json.load(f)
            print(f"✅ Loaded locations from file")
        else:
            try:
                self.locations = json.loads(user_input)
                print(f"✅ Loaded locations")
            except json.JSONDecodeError:
                print("❌ Invalid JSON format. Skipping location filtering.")
                self.locations = {}
    
    def _get_newspapers_input(self):
        """Get newspaper sources"""
        print("\n📰 NEWSPAPERS")
        print("Enter newspapers by language (JSON format)")
        print("Example: {\"en\": [{\"name\": \"The Hindu\", \"link\": \"https://thehindu.com\"}]}")
        print("Or provide file path to JSON file")
        print("Press Enter to skip newspaper-specific searches")
        
        user_input = input("Newspapers (JSON/file path/Enter to skip): ").strip()
        
        if not user_input:
            self.newspapers = {}
            print("⚠️ No newspapers provided. Will use broad searches only.")
        elif os.path.isfile(user_input):
            with open(user_input, 'r', encoding='utf-8') as f:
                self.newspapers = json.load(f)
            print(f"✅ Loaded newspapers from file")
        else:
            try:
                self.newspapers = json.loads(user_input)
                print(f"✅ Loaded newspapers")
            except json.JSONDecodeError:
                print("❌ Invalid JSON format. Skipping newspaper-specific searches.")
                self.newspapers = {}
    
    def _get_specific_links_input(self):
        """Get specific article links"""
        print("\n🔗 SPECIFIC LINKS")
        print("Enter specific article URLs (comma-separated or JSON array)")
        print("Or provide file path to text/JSON file")
        print("Press Enter to skip")
        
        user_input = input("Links (comma-separated/JSON/file/Enter to skip): ").strip()
        
        if not user_input:
            self.specific_links = []
            print("⚠️ No specific links provided.")
        elif os.path.isfile(user_input):
            with open(user_input, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content.startswith('['):
                    self.specific_links = json.loads(content)
                else:
                    self.specific_links = [line.strip() for line in content.split('\n') if line.strip()]
            print(f"✅ Loaded {len(self.specific_links)} specific links from file")
        else:
            if user_input.startswith('['):
                try:
                    self.specific_links = json.loads(user_input)
                except json.JSONDecodeError:
                    print("❌ Invalid JSON format")
                    self.specific_links = []
            else:
                self.specific_links = [link.strip() for link in user_input.split(',') if link.strip()]
            print(f"✅ Loaded {len(self.specific_links)} specific links")
    
    def _get_country_codes_input(self):
        """Get Google News country codes"""
        print("\n🌍 GOOGLE NEWS COUNTRY CODES")
        print("Specify which countries to search (e.g., IN for India, US for USA, GB for UK)")
        print("Enter comma-separated codes or press Enter for default (IN only)")
        print("Common codes: IN (India), US (USA), GB (UK), AU (Australia), CA (Canada)")
        
        user_input = input("Country codes (comma-separated or Enter for IN): ").strip().upper()
        
        if not user_input:
            self.country_codes = ['IN']
            print("✅ Using default: IN (India)")
        else:
            codes = [code.strip() for code in user_input.split(',') if code.strip()]
            if codes:
                self.country_codes = codes
                print(f"✅ Using country codes: {', '.join(self.country_codes)}")
            else:
                self.country_codes = ['IN']
                print("⚠️ Invalid input. Using default: IN (India)")
    
    def _extract_languages(self):
        """Extract unique languages from all inputs"""
        lang_set = set()
        
        # From hazard names
        lang_set.update(self.hazard_names.keys())
        
        # From keywords
        lang_set.update(self.keywords.keys())
        
        # From newspapers
        lang_set.update(self.newspapers.keys())
        
        # Ensure 'en' is always included
        lang_set.add('en')
        
        self.languages = sorted(list(lang_set))
        print(f"\n🌐 Languages detected: {', '.join(self.languages)}")
    
    def get_all_locations_flat(self) -> List[str]:
        """Get flattened list of all locations"""
        locations = []
        
        for state, state_data in self.locations.items():
            locations.append(state)
            
            if 'districts' in state_data:
                for district, cities in state_data['districts'].items():
                    locations.append(district)
                    locations.extend(cities)
        
        return locations
    
    def get_location_hierarchy(self) -> List[Tuple[str, str, str]]:
        """Get location hierarchy as (state, district, city) tuples"""
        hierarchy = []
        
        for state, state_data in self.locations.items():
            if 'districts' in state_data:
                for district, cities in state_data['districts'].items():
                    for city in cities:
                        hierarchy.append((state, district, city))
        
        return hierarchy
    
    def save_to_file(self, filepath):
        """Save configuration to JSON file"""
        config_dict = {
            'disaster_id': self.disaster_id,
            'hazard_names': self.hazard_names,
            'keywords': self.keywords,
            'locations': self.locations,
            'newspapers': self.newspapers,
            'specific_links': self.specific_links,
            'country_codes': self.country_codes,
            'start_date': self.start_date.strftime('%d/%m/%Y'),
            'end_date': self.end_date.strftime('%d/%m/%Y')
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Configuration saved to {filepath}")
    
    def validate(self) -> bool:
        """Validate configuration"""
        errors = []
        
        if not self.disaster_id:
            errors.append("Disaster ID is required")
        
        if not self.hazard_names:
            errors.append("At least one hazard name is required")
        
        if not self.start_date:
            errors.append("Start date is required")
        
        if not self.end_date:
            errors.append("End date is required")
        
        if self.end_date < self.start_date:
            errors.append("End date must be after or equal to start date")
        
        if errors:
            print("\n❌ Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True
    
    def print_summary(self):
        """Print configuration summary"""
        print("\n" + "="*80)
        print("📋 CONFIGURATION SUMMARY")
        print("="*80)
        print(f"\n🆔 Disaster ID: {self.disaster_id}")
        print(f"📅 Date Range: {self.start_date.strftime('%d/%m/%Y')} to {self.end_date.strftime('%d/%m/%Y')}")
        print(f"\n🌐 Languages: {', '.join(self.languages)}")
        print(f"🌍 Country Codes: {', '.join(self.country_codes)}")
        
        print(f"\n🌪️ Hazard Names:")
        for lang, names in self.hazard_names.items():
            print(f"  {lang}: {', '.join(names)}")
        
        print(f"\n🔑 Keywords: {sum(len(kw) for kw in self.keywords.values())} total across {len(self.keywords)} languages")
        
        if self.locations:
            total_locations = len(self.get_all_locations_flat())
            print(f"\n📍 Locations: {total_locations} total")
            for state in list(self.locations.keys())[:3]:
                print(f"  - {state}")
            if len(self.locations) > 3:
                print(f"  ... and {len(self.locations) - 3} more")
        else:
            print(f"\n📍 Locations: No specific filtering")
        
        if self.newspapers:
            total_newspapers = sum(len(papers) for papers in self.newspapers.values())
            print(f"\n📰 Newspapers: {total_newspapers} total across {len(self.newspapers)} languages")
        else:
            print(f"\n📰 Newspapers: No specific newspaper filtering")
        
        if self.specific_links:
            print(f"\n🔗 Specific Links: {len(self.specific_links)} URLs")
        else:
            print(f"\n🔗 Specific Links: None provided")
        
        print("\n" + "="*80)


def load_config_interactive():
    """Interactive configuration loading"""
    print("\n🔧 How would you like to provide configuration?")
    print("1. Interactive input (step-by-step)")
    print("2. Load from JSON file")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == '2':
        filepath = input("Enter path to JSON configuration file: ").strip()
        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            print("Falling back to interactive input...")
            choice = '1'
        else:
            config = HazardConfig.from_json_file(filepath)
    
    if choice == '1':
        config = HazardConfig.from_user_input(interactive=True)
    
    if config.validate():
        config.print_summary()
        
        # Ask if user wants to save configuration
        save_choice = input("\n💾 Save this configuration to file? (y/n): ").strip().lower()
        if save_choice == 'y':
            save_path = f"config_{config.disaster_id.replace('/', '-')}.json"
            config.save_to_file(save_path)
        
        return config
    else:
        raise ValueError("Invalid configuration")


if __name__ == "__main__":
    # Test the configuration handler
    config = load_config_interactive()
    print("\n✅ Configuration loaded successfully!")