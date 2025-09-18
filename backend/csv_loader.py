# backend/csv_loader.py
import csv
import os
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class CSVDataLoader:
    def __init__(self):
        self.data_dir = Path(__file__).parent / "data"
        self._cache = {}
        self.load_all_data()
    
    def load_csv(self, filename: str) -> List[Dict]:
        """Load CSV file and return as list of dictionaries"""
        filepath = self.data_dir / filename
        data = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                data = [row for row in reader]
            logger.info(f"✅ Loaded {len(data)} items from {filename}")
        except FileNotFoundError:
            logger.warning(f"❌ CSV file not found: {filename}")
            # Return empty list if file doesn't exist yet
            return []
        except Exception as e:
            logger.error(f"❌ Error loading {filename}: {e}")
            return []
        
        return data
    
    def load_all_data(self):
        """Load all CSV files into cache"""
        categories = ['politicians', 'celebrities', 'countries', 'games', 'stocks', 'crypto']
        
        for category in categories:
            filename = f"{category}.csv"
            self._cache[category] = self.load_csv(filename)
            logger.info(f"📁 Cached {len(self._cache[category])} {category}")
    
    def reload_data(self):
        """Reload all CSV data (useful for updates)"""
        logger.info("🔄 Reloading all CSV data...")
        self.load_all_data()
    
    def get_category_data(self, category: str) -> List[Dict]:
        """Get all data for a specific category"""
        return self._cache.get(category, [])
    
    def search_in_category(self, category: str, query: str, limit: int = 10) -> List[Dict]:
        """Search within a specific category"""
        data = self.get_category_data(category)
        if not data:
            return []
            
        query_lower = query.lower().strip()
        if len(query_lower) < 2:
            return []
        
        matches = []
        
        # First pass: exact matches and starts with
        for item in data:
            # Handle both 'Name' and 'name' column formats
            name = item.get('Name') or item.get('name', '')
            if not name:
                continue
            name_lower = name.lower()
            if name_lower == query_lower or name_lower.startswith(query_lower):
                # Ensure we have the search_term field for API compatibility
                if 'search_term' not in item:
                    item['search_term'] = name
                matches.append(item)
                if len(matches) >= limit:
                    break

        # Second pass: contains query (if we need more results)
        if len(matches) < limit:
            for item in data:
                if item not in matches:  # Avoid duplicates
                    name = item.get('Name') or item.get('name', '')
                    if not name:
                        continue
                    name_lower = name.lower()
                    if query_lower in name_lower:
                        # Ensure we have the search_term field for API compatibility
                        if 'search_term' not in item:
                            item['search_term'] = name
                        matches.append(item)
                        if len(matches) >= limit:
                            break
        
        return matches
    
    def search_all_categories(self, query: str, limit: int = 20) -> Dict[str, List[Dict]]:
        """Search across all categories"""
        if len(query.strip()) < 2:
            return {}
            
        results = {}
        per_category_limit = max(1, limit // 4)  # Distribute across 4 categories
        
        for category in self._cache.keys():
            matches = self.search_in_category(category, query, per_category_limit)
            if matches:
                results[category] = matches
        
        return results
    
    def get_random_suggestions(self, category: str, count: int = 10) -> List[Dict]:
        """Get random suggestions from a category (for homepage/discovery)"""
        import random
        data = self.get_category_data(category)
        if not data:
            return []
        
        return random.sample(data, min(count, len(data)))
    
    def get_all_categories(self) -> List[str]:
        """Get list of all available categories"""
        return list(self._cache.keys())
    
    def get_category_stats(self) -> Dict[str, int]:
        """Get count of items in each category"""
        return {category: len(data) for category, data in self._cache.items()}

# Global instance
csv_loader = CSVDataLoader()