#!/usr/bin/env python3
"""
Diagnostic Script for Google News Issues
Helps identify why articles aren't being found
"""

import pygooglenews
from datetime import datetime, timedelta
import sys

def test_google_news_queries():
    """Test various query patterns to see what returns results"""
    
    print("\n" + "="*80)
    print("🔍 GOOGLE NEWS DIAGNOSTIC TOOL")
    print("="*80)
    
    # Test queries
    test_queries = [
        "Cyclone Montha",
        "Cyclone Mocha",  # Check if spelling is different
        "Montha cyclone",
        "Montha",
        "West Bengal cyclone October 2025",
        "West Bengal heavy rain October",
        "Andhra Pradesh cyclone October 2025",
        "India cyclone October 2025",
    ]
    
    # Test with different country codes
    countries = {
        'IN': 'India',
        'US': 'United States', 
        'GB': 'United Kingdom'
    }
    
    print("\n📊 Testing queries across different regions...\n")
    
    results_found = []
    
    for country_code, country_name in countries.items():
        print(f"\n{'='*80}")
        print(f"Testing with country: {country_name} ({country_code})")
        print('='*80)
        
        try:
            gn = pygooglenews.GoogleNews(lang='en', country=country_code)
        except Exception as e:
            print(f"❌ Could not initialize Google News for {country_code}: {e}")
            continue
        
        for query in test_queries:
            try:
                # Try 30-day window
                search_results = gn.search(query, when='30d')
                
                if search_results and 'entries' in search_results:
                    count = len(search_results['entries'])
                    
                    if count > 0:
                        print(f"✅ '{query}' - Found {count} results")
                        results_found.append({
                            'query': query,
                            'country': country_code,
                            'count': count,
                            'results': search_results['entries'][:3]  # Store first 3
                        })
                    else:
                        print(f"⚠️  '{query}' - 0 results")
                else:
                    print(f"❌ '{query}' - No response")
                    
            except Exception as e:
                print(f"❌ '{query}' - Error: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("📋 SUMMARY")
    print("="*80)
    
    if results_found:
        print(f"\n✅ Found articles with {len(results_found)} query/country combinations:\n")
        
        for item in results_found:
            print(f"Query: '{item['query']}' in {item['country']}: {item['count']} results")
            for entry in item['results'][:2]:
                print(f"  - {entry.title}")
            print()
        
        print("\n💡 RECOMMENDATIONS:")
        print("="*80)
        
        # Analyze what worked
        successful_queries = [item['query'] for item in results_found]
        successful_countries = list(set([item['country'] for item in results_found]))
        
        print(f"\n1. ✅ Working queries:")
        for q in list(set(successful_queries)):
            print(f"   - '{q}'")
        
        print(f"\n2. ✅ Working country codes: {', '.join(successful_countries)}")
        
        print(f"\n3. 📝 Update your configuration:")
        print(f"   Use one of the working query patterns above")
        print(f"   The pipeline will automatically try multiple countries")
        
        # Check dates
        print(f"\n4. 📅 Check article dates:")
        for item in results_found[:1]:
            if item['results']:
                entry = item['results'][0]
                if hasattr(entry, 'published'):
                    print(f"   Sample article date: {entry.published}")
                    print(f"   Make sure your date range includes this!")
    else:
        print("\n❌ No articles found with any query or country combination")
        print("\n💡 TROUBLESHOOTING:")
        print("="*80)
        print("\n1. Verify the event name:")
        print("   - Is it 'Cyclone Montha' or 'Cyclone Mocha'?")
        print("   - Check Google News manually: https://news.google.com/")
        print("\n2. Try broader searches:")
        print("   - Just location + month (e.g., 'West Bengal October 2025')")
        print("   - Remove specific cyclone name")
        print("\n3. Check if event actually occurred:")
        print("   - Verify dates are correct")
        print("   - Check if media covered the event")
        print("\n4. Try different time windows:")
        print("   - Try when='7d', when='14d', when='30d'")

def test_specific_article():
    """Test if we can find a specific known article"""
    print("\n" + "="*80)
    print("🔍 TESTING SPECIFIC ARTICLE")
    print("="*80)
    
    # The article we know exists
    article_title = "Weakened cyclone Montha to bring heavy rains"
    article_date = "October 30, 2025"
    
    print(f"\nKnown article:")
    print(f"  Title: {article_title}")
    print(f"  Date: {article_date}")
    print(f"  Source: The Hindu")
    
    queries_to_try = [
        "Montha West Bengal",
        "Montha heavy rain",
        "cyclone Montha weak",
        "Montha India",
        "West Bengal cyclone rain",
    ]
    
    print(f"\nTrying to find this article with various queries...\n")
    
    found = False
    
    for country_code in ['IN', 'US', 'GB']:
        if found:
            break
            
        try:
            gn = pygooglenews.GoogleNews(lang='en', country=country_code)
            
            for query in queries_to_try:
                results = gn.search(query, when='30d')
                
                if results and 'entries' in results:
                    for entry in results['entries']:
                        if 'Montha' in entry.title and 'Bengal' in entry.title:
                            print(f"✅ FOUND with query '{query}' in country {country_code}!")
                            print(f"   Title: {entry.title}")
                            print(f"   Link: {entry.link}")
                            print(f"   Published: {entry.published}")
                            found = True
                            break
                
                if found:
                    break
        except:
            pass
    
    if not found:
        print("❌ Could not find the specific article through Google News API")
        print("\nThis could mean:")
        print("  1. The article is too recent (not yet indexed)")
        print("  2. Google News API has indexing delays")
        print("  3. The article is region-locked")
        print("\n💡 Solution: Use the specific link method instead of Google News search")

if __name__ == "__main__":
    test_google_news_queries()
    test_specific_article()
    
    print("\n" + "="*80)
    print("✅ DIAGNOSTIC COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("1. Use the working queries/countries identified above")
    print("2. If no queries work, rely on specific links")
    print("3. Consider that the event might not be well-indexed in Google News yet")
    print("="*80 + "\n")