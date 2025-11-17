from datetime import datetime, timedelta
import pytz
import os
import pandas as pd
import time
import pygooglenews
import argparse
import re
import requests
import json
from bs4 import BeautifulSoup
from language_map import get_language_for_region, get_all_languages_for_region, get_climate_impact_terms

# Import our smart handler
from smart_google_news_handler import smart_handler
def extract_results_with_strict_date_filter(results, hazard_name, lang_code, start_date, end_date, disaster_terms):
    filtered_entries = []

    if 'entries' not in results:
        return filtered_entries

    for entry in results['entries']:
        title = entry.get('title', '')
        link = entry.get('link', '')
        published = entry.get('published', '')
        source = entry.get('source', {}).get('title', '')
        summary = entry.get('summary', '')

        try:
            entry_date = datetime.strptime(published.split('T')[0], "%Y-%m-%d").date()
        except:
            continue

        if not (start_date <= entry_date <= end_date):
            continue

        if not any(term.lower() in (title + summary).lower() for term in disaster_terms):
            continue

        filtered_entries.append([
            title,
            link,
            entry_date.strftime("%Y-%m-%d"),
            source,
            summary,
            hazard_name,
            lang_code
        ])

    return filtered_entries

def run_monsoon_script(target_date=None, days_back=0, single_state=None, 
                       hazard_name=None, locations_dict=None, keywords_dict=None):
    """
    Run the disaster extraction script with flexible parameters.
    
    NEW FLEXIBLE MODE:
        hazard_name (str): Name of the hazard (e.g., "Cyclone", "Flood", "Heatwave")
        locations_dict (dict): Nested dictionary with structure:
            {
              "State Name": {
                "districts": {
                  "District Name": ["City1", "City2", ...]
                }
              }
            }
        keywords_dict (dict): Keywords by language:
            {
              "en": ["keyword1", "keyword2", ...],
              "hi": ["कीवर्ड1", "कीवर्ड2", ...]
            }
    
    OLD MONSOON MODE (backward compatible):
        target_date (str): Date in YYYY-MM-DD format
        days_back (int): Number of days to look back
        single_state (str): Process only this state
    """
    print("🧠 Initializing Smart Google News Handler...")
    
    # Determine operation mode
    flexible_mode = all([hazard_name, locations_dict, keywords_dict])
    
    if flexible_mode:
        print(f"🎯 FLEXIBLE MODE: Extracting {hazard_name} news")
        print(f"📍 States: {list(locations_dict.keys())}")
        print(f"🗣️  Keyword languages: {list(keywords_dict.keys())}")
    else:
        print(f"🌧️ LEGACY MODE: Extracting Monsoon news")
        hazard_name = "Monsoon"  # Default for legacy mode
    
    # Set date range based on parameters
    ist = pytz.timezone('Asia/Kolkata')
    
    if target_date:
        try:
            end_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            print(f"🗓️ Using specified target date: {end_date}")
        except ValueError:
            print(f"❌ Invalid date format: {target_date}. Using current date.")
            end_date = datetime.now(ist).date()
    else:
        end_date = datetime.now(ist).date()
        print(f"🗓️ Using current date: {end_date}")
    
    start_date = end_date - timedelta(days=days_back)
    print(f"🔍 STRICTLY filtering for articles between {start_date} and {end_date}")
    
    # Use broader search window but filter precisely afterward
    when_parameter = f'{max(days_back + 7, 7)}d'
    
    # Determine regions to process
    if flexible_mode:
        # Use locations from the provided dictionary
        regions_to_process = list(locations_dict.keys())
        print(f"🎯 Processing {len(regions_to_process)} states from locations dictionary")
    elif single_state:
        # Legacy single state mode
        states = [
            "andhra-pradesh", "arunachal-pradesh", "assam", "bihar", "chhattisgarh",
            "goa", "gujarat", "haryana", "himachal-pradesh", "jharkhand", "karnataka",
            "kerala", "madhya-pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
            "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil-nadu", 
            "telangana", "tripura", "uttar-pradesh", "uttarakhand", "west-bengal"
        ]
        union_territories = [
            "andaman-and-nicobar-islands", "chandigarh", 
            "dadra-and-nagar-haveli-and-daman-and-diu",
            "lakshadweep", "delhi", "puducherry", 
            "jammu-and-kashmir", "ladakh"
        ]
        
        if single_state in states or single_state in union_territories:
            regions_to_process = [single_state]
            print(f"🎯 Processing only: {single_state.replace('-', ' ').title()}")
        else:
            print(f"❌ Invalid state/UT: {single_state}")
            return
    else:
        # Legacy all states mode
        regions_to_process = [
            "andhra-pradesh", "arunachal-pradesh", "assam", "bihar", "chhattisgarh",
            "goa", "gujarat", "haryana", "himachal-pradesh", "jharkhand", "karnataka",
            "kerala", "madhya-pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
            "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil-nadu", 
            "telangana", "tripura", "uttar-pradesh", "uttarakhand", "west-bengal",
            "andaman-and-nicobar-islands", "chandigarh", 
            "dadra-and-nagar-haveli-and-daman-and-diu",
            "lakshadweep", "delhi", "puducherry", 
            "jammu-and-kashmir", "ladakh"
        ]
    
    # Clean up existing files for the target date range
    cleanup_existing_files_for_date_range(start_date, end_date, single_state, hazard_name)
    
    # Load newspaper database (keeping this functionality)
    newspaper_db = load_newspaper_database()
    
    # Process national-level sources only if not filtering to single state (legacy mode only)
    if not single_state and not flexible_mode:
        national_sources = get_national_newspapers(newspaper_db)
        national_entries = process_newspaper_sources(national_sources, "national", start_date, end_date)
        if national_entries:
            save_national_results(national_entries, end_date, hazard_name)

    # Print smart handler initialization stats
    print("🧠 Smart Handler Status:")
    print("   🔄 Adaptive delays enabled")
    print("   🛡️ Circuit breaker protection active")
    print("   🎯 Query optimization enabled")
    print("   📊 Pattern learning active")

    # Process each region
    for region in regions_to_process:
        # Normalize region name for processing
        if flexible_mode:
            # Convert "State Name" to "state-name" format
            region_slug = region.lower().replace(" ", "-")
            region_name = region
        else:
            # Already in "state-name" format
            region_slug = region
            region_name = region.replace("-", " ")
        
        print(f"\n===== Processing region: {region_name.title()} =====")
        
        # Get languages for this region
        if flexible_mode:
            # Map state name to languages using language_map.py
            region_languages = get_all_languages_for_region(region_slug)
            print(f"Languages for this region: {', '.join(region_languages)}")
        else:
            # Legacy mode
            region_languages = get_all_languages_for_region(region_slug)
            print(f"Languages for this region: {', '.join(region_languages)}")
        
        all_region_entries = []
        
        # Smart inter-language delay
        inter_language_delay = smart_handler.adaptive_delay()
        
        for lang_index, lang_code in enumerate(region_languages):
            print(f"\n--- Processing language: {lang_code} ({lang_index + 1}/{len(region_languages)}) ---")
            
            # Get keywords for this language
            if flexible_mode:
                # Use provided keywords
                disaster_terms = keywords_dict.get(lang_code, keywords_dict.get('en', []))
                if not disaster_terms:
                    print(f"⚠️ No keywords found for language {lang_code}, skipping")
                    continue
                print(f"🎯 Using {len(disaster_terms)} {hazard_name} terms for {lang_code}")
            else:
                # Legacy mode: use monsoon terms
                disaster_terms = get_climate_impact_terms(lang_code)
                print(f"🌧️ Using {len(disaster_terms)} monsoon terms for {lang_code}")
            
            print(f"📝 Sample terms: {disaster_terms[:3]}...")
            
            # Initialize Google News with this language
            gn = pygooglenews.GoogleNews(lang=lang_code, country='IN')
            
            # Create queries
            if flexible_mode:
                # Create queries for flexible mode
                queries = create_flexible_disaster_queries(
                    disaster_terms, 
                    region_name, 
                    hazard_name,
                    locations_dict.get(region, {}),
                    lang_code
                )
            else:
                # Legacy monsoon queries
                queries = create_smart_monsoon_queries(disaster_terms, region_name, lang_code)
            
            # Track query performance
            successful_queries = 0
            total_queries = len(queries)
            
            for query_index, query in enumerate(queries):
                print(f"🔍 Query {query_index + 1}/{total_queries}: {query[:60]}{'...' if len(query) > 60 else ''} | Language: {lang_code}")
                
                # Use smart search
                results = smart_handler.smart_search(
                    gn_instance=gn,
                    query=query,
                    when_parameter=when_parameter,
                    lang_code=lang_code,
                    region=region_slug,
                    max_retries=4
                )
                
                if not results or 'entries' not in results or not results['entries']:
                    print(f"⚠ No results found for this query in [{lang_code}].")
                    continue
                
                total_articles = len(results['entries'])
                print(f"✅ Found {total_articles} total articles for {region_name} in [{lang_code}]")
                
                # Extract with STRICT date filtering
                entries = extract_results_with_strict_date_filter(
                    results, hazard_name, lang_code, start_date, end_date, disaster_terms
                )
                
                filtered_count = len(entries)
                print(f"📅 STRICTLY filtered to {filtered_count} relevant {hazard_name} articles within date range")
                
                if filtered_count > 0:
                    successful_queries += 1
                    dates = [datetime.strptime(entry[2].split()[0], "%Y-%m-%d").date() 
                            for entry in entries]
                    print(f"📊 Dates in filtered articles: {sorted(set(dates))}")
                
                all_region_entries.extend(entries)
                
                # Smart inter-query delay
                query_delay = smart_handler.adaptive_delay()
                if query_index < total_queries - 1:
                    print(f"⏳ Smart delay: {query_delay:.1f}s before next query...")
                    time.sleep(query_delay)
            
            # Language processing summary
            success_rate = (successful_queries / total_queries * 100) if total_queries > 0 else 0
            print(f"📈 Language {lang_code} summary: {successful_queries}/{total_queries} queries successful ({success_rate:.1f}%)")
            
            # Smart inter-language delay
            if lang_index < len(region_languages) - 1:
                print(f"⏳ Inter-language delay: {inter_language_delay:.1f}s...")
                time.sleep(inter_language_delay)
            
            # Check region-specific newspapers
            region_newspapers = get_regional_newspapers(newspaper_db, region_slug)
            if region_newspapers:
                additional_entries = process_newspaper_sources(
                    region_newspapers, region_slug, start_date, end_date
                )
                if additional_entries:
                    all_region_entries.extend(additional_entries)
        
        # Save combined results for this region
        if all_region_entries:
            # Determine if this is a state or union territory
            states = [
                "andhra-pradesh", "arunachal-pradesh", "assam", "bihar", "chhattisgarh",
                "goa", "gujarat", "haryana", "himachal-pradesh", "jharkhand", "karnataka",
                "kerala", "madhya-pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
                "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil-nadu", 
                "telangana", "tripura", "uttar-pradesh", "uttarakhand", "west-bengal"
            ]
            region_type = 'states' if region_slug in states else 'union-territories'
            
            save_results(
                all_region_entries,
                region_type,
                region_slug,
                end_date,
                hazard_name
            )
        else:
            print(f"No {hazard_name} articles found for {region_name}")
        
        # Print smart handler statistics for this region
        stats = smart_handler.get_statistics()
        print(f"🧠 Smart Handler Stats for {region_name}:")
        print(f"   📊 Overall success rate: {stats['success_rate']:.1f}%")
        print(f"   🔄 Circuit breaker: {stats['circuit_breaker_state']}")
        print(f"   🚫 Banned patterns: {stats['banned_patterns']}")
    
    # Final pipeline statistics
    print(f"\n🎉 Pipeline completed! Final Smart Handler Statistics:")
    final_stats = smart_handler.get_statistics()
    print(f"📊 Total requests: {final_stats['total_requests']}")
    print(f"✅ Successful requests: {final_stats['successful_requests']}")
    print(f"📈 Overall success rate: {final_stats['success_rate']:.1f}%")
    print(f"🔄 Circuit breaker state: {final_stats['circuit_breaker_state']}")
    print(f"🚫 Banned query patterns: {final_stats['banned_patterns']}")
    
    # Cleanup sessions
    smart_handler.cleanup_sessions()

def create_flexible_disaster_queries(disaster_terms, region_name, hazard_name, 
                                     location_info, lang_code):
    """
    Create optimized queries for flexible disaster extraction.
    
    Args:
        disaster_terms: List of keywords in the specified language
        region_name: Name of the state/region
        hazard_name: Name of the hazard (e.g., "Cyclone", "Flood")
        location_info: Dictionary with districts and cities
        lang_code: Language code
    """
    if not disaster_terms:
        print(f"⚠️ No disaster terms found for language {lang_code}")
        return [f"{hazard_name} {region_name}"]
    
    print(f"🔤 Creating SMART queries from {len(disaster_terms)} terms for {lang_code}")
    
    queries = []
    
    # Strategy 1: Hazard + Region (priority queries)
    priority_terms = disaster_terms[:3]  # Top 3 terms
    for i, term in enumerate(priority_terms):
        if term.strip():
            query = f'"{term}" {region_name}'
            queries.append(query)
            print(f"   Priority query {i+1}: {query}")
    
    # Strategy 2: Hazard + Districts (if available)
    if 'districts' in location_info:
        districts = list(location_info['districts'].keys())
        for district in districts[:2]:  # Limit to 2 districts
            if disaster_terms:
                query = f'{disaster_terms[0]} {district}'
                queries.append(query)
                print(f"   District query: {query}")
    
    # Strategy 3: Combined impact terms
    if len(disaster_terms) >= 3:
        impact_query = f'({disaster_terms[0]} OR {disaster_terms[1]}) {region_name}'
        queries.append(impact_query)
        print(f"   Impact query: {impact_query}")
    
    # Strategy 4: Hazard name + primary terms (if different from disaster_terms)
    if hazard_name.lower() not in ' '.join(disaster_terms[:5]).lower():
        for term in disaster_terms[:2]:
            query = f'{hazard_name} {term} {region_name}'
            queries.append(query)
            print(f"   Hazard+term query: {query}")
    
    # Limit total queries based on environment
    is_local = os.environ.get('GITHUB_ACTIONS') != 'true'
    if is_local:
        queries = queries[:3]  # Very conservative for local
    else:
        queries = queries[:7]  # More for GitHub Actions
    
    # Optimize queries
    optimized_queries = []
    for query in queries:
        if query.count('OR') <= 4 and len(query) <= 200:
            optimized_queries.append(query)
        else:
            print(f"🔧 Skipping overly complex query: {query[:50]}...")
    
    print(f"📊 Created {len(optimized_queries)} optimized queries for {lang_code}")
    return optimized_queries
# ---------------------------------------------------------------------
# FIXED FUNCTION: Load the newspaper database safely
# ---------------------------------------------------------------------
def load_newspaper_database():
    """
    Loads the newspaper database from CSV file
    (list_of_newspaper_statewise - Sheet1.csv).

    Returns a pandas DataFrame with state, district, newspaper_name, link, language.
    """
    import pandas as pd
    import os

    db_path = "list_of_newspaper_statewise - Sheet1.csv"

    if not os.path.exists(db_path):
        print(f"❌ Newspaper database not found at: {db_path}")
        print("   Expected: list_of_newspaper_statewise - Sheet1.csv")
        return None

    try:
        df = pd.read_csv(db_path)
        print(f"✅ Loaded newspaper database with {len(df)} entries")
        return df
    except Exception as e:
        print(f"❌ Failed to load newspaper database: {e}")
        return None

 # Helper functions for monsoon.py (continued)
# Add these to the existing monsoon.py file

def create_smart_monsoon_queries(monsoon_terms, region_name, lang_code):
    """
    Create optimized queries for legacy monsoon mode.
    This function is kept for backward compatibility.
    """
    if not monsoon_terms:
        print(f"⚠️ No monsoon terms found for language {lang_code}")
        return [f"monsoon {region_name}"]
    
    print(f"🔤 Creating SMART queries from {len(monsoon_terms)} terms for {lang_code}")
    
    queries = []
    
    # Strategy 1: Priority terms
    priority_terms = monsoon_terms[:3]
    for i, term in enumerate(priority_terms):
        if term.strip():
            query = f'"{term}" {region_name}'
            queries.append(query)
            print(f"   Priority query {i+1}: {query}")
    
    # Strategy 2: Weather phenomena
    if len(monsoon_terms) >= 3:
        weather_query = f'({monsoon_terms[0]} OR {monsoon_terms[1]}) {region_name}'
        queries.append(weather_query)
        print(f"   Weather query: {weather_query}")
    
    # Strategy 3: Impact terms
    if len(monsoon_terms) >= 6:
        impact_terms = monsoon_terms[3:6]
        impact_query = f'({" OR ".join(impact_terms[:2])}) {region_name}'
        queries.append(impact_query)
        print(f"   Impact query: {impact_query}")
    
    # Limit based on environment
    is_local = os.environ.get('GITHUB_ACTIONS') != 'true'
    if is_local:
        queries = queries[:3]
    else:
        if len(monsoon_terms) >= 10:
            health_terms = monsoon_terms[8:10]
            health_query = f'({" OR ".join(health_terms)}) {region_name}'
            queries.append(health_query)
            print(f"   Health query: {health_query}")
        
        if len(monsoon_terms) >= 8:
            broad_terms = [
                monsoon_terms[0],
                monsoon_terms[3] if len(monsoon_terms) > 3 else monsoon_terms[1],
                monsoon_terms[7] if len(monsoon_terms) > 7 else monsoon_terms[-1]
            ]
            broad_query = f'({" OR ".join([term for term in broad_terms if term])}) {region_name}'
            queries.append(broad_query)
            print(f"   Broad query: {broad_query}")
    
    # Optimize
    optimized_queries = []
    for query in queries:
        if query.count('OR') <= 4 and len(query) <= 200:
            optimized_queries.append(query)
        else:
            print(f"🔧 Skipping overly complex query: {query[:50]}...")
    
    print(f"📊 Created {len(optimized_queries)} optimized queries for {lang_code}")
    return optimized_queries

def cleanup_existing_files_for_date_range(start_date, end_date, single_state=None, hazard_name="Monsoon"):
    """Remove existing files for the date range to avoid duplication"""
    base_path = "data"
    current_date = start_date
    deleted_count = 0
    
    while current_date <= end_date:
        year = current_date.year
        month = current_date.month
        day = current_date.day
        
        if single_state:
            # Only clean up for the specific state
            states = [
                "andhra-pradesh", "arunachal-pradesh", "assam", "bihar", "chhattisgarh",
                "goa", "gujarat", "haryana", "himachal-pradesh", "jharkhand", "karnataka",
                "kerala", "madhya-pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
                "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil-nadu", 
                "telangana", "tripura", "uttar-pradesh", "uttarakhand", "west-bengal"
            ]
            union_territories = [
                "andaman-and-nicobar-islands", "chandigarh", 
                "dadra-and-nagar-haveli-and-daman-and-diu",
                "lakshadweep", "delhi", "puducherry", 
                "jammu-and-kashmir", "ladakh"
            ]
            
            if single_state in states:
                region_type = "states"
            elif single_state in union_territories:
                region_type = "union-territories"
            else:
                continue
                
            path = f"{base_path}/{region_type}/{single_state}/{hazard_name}/{year}/{month:02d}/{day:02d}"
            if os.path.exists(path):
                for file in os.listdir(path):
                    if file.endswith('.csv'):
                        file_path = os.path.join(path, file)
                        try:
                            os.remove(file_path)
                            deleted_count += 1
                        except Exception as e:
                            print(f"Error deleting {file_path}: {e}")
        else:
            # Clean up all regions
            regions_info = [
                ("states", [
                    "andhra-pradesh", "arunachal-pradesh", "assam", "bihar", "chhattisgarh",
                    "goa", "gujarat", "haryana", "himachal-pradesh", "jharkhand", "karnataka",
                    "kerala", "madhya-pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
                    "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil-nadu", 
                    "telangana", "tripura", "uttar-pradesh", "uttarakhand", "west-bengal"
                ]),
                ("union-territories", [
                    "andaman-and-nicobar-islands", "chandigarh", 
                    "dadra-and-nagar-haveli-and-daman-and-diu",
                    "lakshadweep", "delhi", "puducherry", 
                    "jammu-and-kashmir", "ladakh"
                ]),
                ("national", ["all"])
            ]
            
            for region_type, regions in regions_info:
                for region_name in regions:
                    path = f"{base_path}/{region_type}/{region_name}/{hazard_name}/{year}/{month:02d}/{day:02d}"
                    if os.path.exists(path):
                        for file in os.listdir(path):
                            if file.endswith('.csv'):
                                file_path = os.path.join(path, file)
                                try:
                                    os.remove(file_path)
                                    deleted_count += 1
                                except Exception as e:
                                    print(f"Error deleting {file_path}: {e}")
        
        current_date += timedelta(days=1)
    
    if deleted_count > 0:
        print(f"🧹 Cleaned up {deleted_count} existing files for date range")

def save_results(all_entries, region_type, region_name, current_date, hazard_name="Monsoon"):
    """Save results to CSV file with hazard-specific path"""
    if not all_entries:
        return

    path = f"data/{region_type}/{region_name}/{hazard_name}/{current_date.year}/{current_date.strftime('%m')}/{current_date.strftime('%d')}"
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, 'results.csv')

    columns = ["Title", "Link", "Date", "Source", "Summary", "Term", "LanguageQueried"]
    df = pd.DataFrame(all_entries, columns=columns)

    # Remove duplicates based on URL
    if len(df) > 0:
        before_count = len(df)
        df = df.drop_duplicates(subset=['Link'])
        if before_count > len(df):
            print(f"ℹ️ Removed {before_count - len(df)} duplicate articles")
    
    # Perform final validation of dates before saving
    if 'Date' in df.columns and len(df) > 0:
        df['_DateCheck'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        df = df.dropna(subset=['_DateCheck'])
        df = df.drop(columns=['_DateCheck'])
        
    df.to_csv(file_path, mode='w', header=True, index=False)
    print(f"✅ CSV created for {hazard_name} in {region_name} with {len(df)} articles")

def save_national_results(all_entries, current_date, hazard_name="Monsoon"):
    """Save national-level results with hazard-specific path"""
    if not all_entries:
        return

    path = f"data/national/all/{hazard_name}/{current_date.year}/{current_date.strftime('%m')}/{current_date.strftime('%d')}"
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, 'results.csv')

    columns = ["Title", "Link", "Date", "Source", "Summary", "Term", "LanguageQueried"]
    df = pd.DataFrame(all_entries, columns=columns)

    # Remove duplicates based on URL
    if len(df) > 0:
        before_count = len(df)
        df = df.drop_duplicates(subset=['Link'])
        if before_count > len(df):
            print(f"ℹ️ Removed {before_count - len(df)} duplicate articles")
    
    # Perform final validation of dates before saving
    if 'Date' in df.columns and len(df) > 0:
        df['_DateCheck'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        df = df.dropna(subset=['_DateCheck'])
        df = df.drop(columns=['_DateCheck'])
        
    df.to_csv(file_path, mode='w', header=True, index=False)
    print(f"✅ CSV created for national {hazard_name} articles with {len(df)} articles")

# Keep all the existing helper functions from the original monsoon.py:
# - load_newspaper_database()
# - get_national_newspapers()
# - get_regional_newspapers()
# - extract_results_with_strict_date_filter()
# - is_monsoon_content_relevant() -> Rename to is_disaster_content_relevant()
# - process_newspaper_sources()
# - map_newspaper_language_to_code()
# - find_smart_monsoon_content()
# - extract_and_validate_newspaper_article()
# - extract_article_title()
# - extract_article_date_enhanced()
# - extract_article_summary_enhanced()
# - parse_date_string_enhanced()
# - detect_language_from_text()
# - extract_date_from_url()
# - convert_gmt_to_ist()

# NOTE: Keep ALL the existing helper functions from the original monsoon.py file.
# Only the functions above were modified or added.

# Add this to the end of monsoon.py (replacing the existing __main__ block)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run flexible disaster news article collection script')
    
    # Original parameters (backward compatibility)
    parser.add_argument('--date', type=str, help='Target date in YYYY-MM-DD format (default: current date)')
    parser.add_argument('--days-back', type=int, default=0, help='Number of days to look back from target date (default: 0)')
    parser.add_argument('--state', type=str, help='Process only this single state/UT (e.g., kerala, maharashtra, delhi)')
    parser.add_argument('--reset-smart-handler', action='store_true', help='Reset smart handler state for fresh start')
    
    # NEW PARAMETERS for flexible disaster extraction
    parser.add_argument('--hazard-name', type=str, help='Name of the hazard/disaster (e.g., "Cyclone", "Flood", "Heatwave")')
    parser.add_argument('--locations-json', type=str, help='JSON string with nested locations dictionary')
    parser.add_argument('--keywords-json', type=str, help='JSON string with language-specific keywords dictionary')
    
    args = parser.parse_args()
    
    if args.reset_smart_handler:
        smart_handler.reset_state()
        print("🔄 Smart handler state reset")
    
    # Determine operation mode
    flexible_mode = all([args.hazard_name, args.locations_json, args.keywords_json])
    
    if flexible_mode:
        print("🎯 Starting Flexible Disaster News Collection")
        print(f"📋 Hazard: {args.hazard_name}")
        
        # Parse JSON inputs
        try:
            locations_dict = json.loads(args.locations_json)
            keywords_dict = json.loads(args.keywords_json)
            
            print(f"📍 States: {list(locations_dict.keys())}")
            print(f"🗣️  Keyword languages: {list(keywords_dict.keys())}")
            
            # Validate locations structure
            for state, state_data in locations_dict.items():
                if 'districts' not in state_data:
                    print(f"⚠️ Warning: State '{state}' missing 'districts' key. Expected format:")
                    print('  {"State": {"districts": {"District": ["City1", "City2"]}}}')
            
            # Validate keywords structure
            if not keywords_dict:
                print("❌ Keywords dictionary is empty!")
                sys.exit(1)
                
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON format: {e}")
            print("\n📋 Example locations format:")
            print('  {"Telangana": {"districts": {"Warangal": ["Kazipet"], "Hyderabad": ["Hyderabad"]}}}')
            print("\n📋 Example keywords format:")
            print('  {"en": ["cyclone", "flood"], "hi": ["चक्रवात", "बाढ़"]}')
            import sys
            sys.exit(1)
        
        try:
            run_monsoon_script(
                target_date=args.date,
                days_back=args.days_back,
                single_state=None,  # Not used in flexible mode
                hazard_name=args.hazard_name,
                locations_dict=locations_dict,
                keywords_dict=keywords_dict
            )
            
            print("\n🎯 Final Smart Handler Report:")
            final_stats = smart_handler.get_statistics()
            print(f"📊 Success rate: {final_stats['success_rate']:.1f}%")
            print(f"🔄 Circuit breaker: {final_stats['circuit_breaker_state']}")
            if final_stats['per_region_stats']:
                print("📍 Top performing regions:")
                region_stats = sorted(final_stats['per_region_stats'].items(), 
                                    key=lambda x: x[1]['success_rate'], reverse=True)[:5]
                for region, stats in region_stats:
                    print(f"   {region}: {stats['success_rate']:.1f}% ({stats['requests']} requests)")
            
            print(f"✅ Flexible Disaster News Collection completed successfully!")
            
        except KeyboardInterrupt:
            print("\n⚠️ Collection interrupted by user")
            print("🧠 Smart handler statistics at interruption:")
            stats = smart_handler.get_statistics()
            print(f"📊 Processed {stats['total_requests']} requests with {stats['success_rate']:.1f}% success rate")
            smart_handler.cleanup_sessions()
        except Exception as e:
            print(f"❌ Error during collection: {e}")
            import traceback
            traceback.print_exc()
            print("🧠 Smart handler final statistics:")
            stats = smart_handler.get_statistics()
            print(f"📊 Processed {stats['total_requests']} requests with {stats['success_rate']:.1f}% success rate")
            smart_handler.cleanup_sessions()
            raise
    else:
        # Legacy monsoon mode
        print("🌧️ Starting Monsoon News Collection (Legacy Mode)")
        print(f"📅 Target date: {args.date if args.date else 'Current date'}")
        print(f"📅 Days back: {args.days_back}")
        if args.state:
            print(f"🎯 Single state mode: {args.state}")
        
        try:
            run_monsoon_script(
                target_date=args.date, 
                days_back=args.days_back, 
                single_state=args.state
            )
            
            # Print final smart handler statistics
            print("\n🎯 Final Smart Handler Report:")
            final_stats = smart_handler.get_statistics()
            print(f"📊 Success rate: {final_stats['success_rate']:.1f}%")
            print(f"🔄 Circuit breaker: {final_stats['circuit_breaker_state']}")
            if final_stats['per_region_stats']:
                print("📍 Top performing regions:")
                region_stats = sorted(final_stats['per_region_stats'].items(), 
                                    key=lambda x: x[1]['success_rate'], reverse=True)[:5]
                for region, stats in region_stats:
                    print(f"   {region}: {stats['success_rate']:.1f}% ({stats['requests']} requests)")
            
            print("✅ Smart Monsoon News Collection completed successfully!")
            
        except KeyboardInterrupt:
            print("\n⚠️ Collection interrupted by user")
            print("🧠 Smart handler statistics at interruption:")
            stats = smart_handler.get_statistics()
            print(f"📊 Processed {stats['total_requests']} requests with {stats['success_rate']:.1f}% success rate")
            smart_handler.cleanup_sessions()
        except Exception as e:
            print(f"❌ Error during collection: {e}")
            print("🧠 Smart handler final statistics:")
            stats = smart_handler.get_statistics()
            print(f"📊 Processed {stats['total_requests']} requests with {stats['success_rate']:.1f}% success rate")
            smart_handler.cleanup_sessions()
            raise
