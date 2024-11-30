import requests
import os
import json

class CapacitiesHandler:
    def __init__(self, api_key):
        self.api_key = api_key
        self.space_id = os.getenv("CAPACITIES_SPACE_ID")
        self.base_url = "https://api.capacities.io"  # URL base correcta

    def create_weblink(self, results):
        """Create a weblink in Capacities using the REST API"""
        if not self.api_key or not self.space_id:
            raise ValueError("Missing Capacities credentials (API key or Space ID)")

        try:
            if results['type'] == 'github':
                # Format GitHub README content
                content = f"""# {results['info']['title']}

{results['readme']}

---
Repository URL: {results['info']['url']}
Analyzed on: {results.get('processed_date', 'Date not available')}"""

                # Create a shorter description from the README (using cleaned content)
                description_lines = results['readme'].split('\n')
                description = next((line for line in description_lines if line.strip()), "No description available")
                if len(description) > 997:  # Leave room for '...'
                    description = description[:997] + "..."
            else:
                # Handle YouTube content (existing code)
                description = f"""YouTube Video Analysis: {results['info']['title']}

Summary: {results.get('summary', 'No summary available')[:500]}...

Tags: {', '.join(self._generate_tags(results))}"""[:1000]
                content = self._format_content(results)

            # Prepare weblink data
            weblink_data = {
                "spaceId": self.space_id,
                "url": results['info']['url'],
                "titleOverwrite": results['info']['title'][:200],  # Limit title
                "descriptionOverwrite": description,
                "mdText": content
            }

            # Debug info
            print("\nSending request to Capacities:")
            endpoint = f"{self.base_url}/save-weblink"
            print(f"URL: {endpoint}")
            print(f"Space ID: {self.space_id}")

            # Make the API request
            response = requests.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "accept": "application/json"
                },
                json=weblink_data,
                timeout=30
            )

            # Handle response
            if response.status_code == 200:
                return {"status": "success", "url": response.json().get('url')}
            else:
                raise Exception(f"Capacities error ({response.status_code}): {response.text}")

        except Exception as e:
            raise Exception(f"Error creating weblink: {str(e)}")

    def _generate_tags(self, results):
        """Generate tags from the results"""
        # Clean and format tags
        tags = []
        for tag in results['tags']:
            # Remove numbers and special characters
            clean_tag = ''.join(c for c in tag if c.isalnum() or c.isspace())
            # Remove extra spaces and convert to lowercase
            clean_tag = clean_tag.strip().lower()
            if clean_tag:
                tags.append(clean_tag)
        
        # Add additional tags
        additional_tags = [
            'youtube-analysis',
            'video-summary',
            'content-analysis',
            results['info']['author'].lower().replace(' ', '-')
        ]
        tags.extend(additional_tags)
        
        # Remove duplicates and limit to 10 tags
        return list(set(tags))[:10]

    def _format_content(self, results):
        """Format the results in markdown"""
        content = f"""# YouTube Video Analysis

## Video Information
- **Title:** {results['info']['title']}
- **Channel:** {results['info']['author']}
- **Views:** {results['info']['views']:,}
- **Duration:** {results['info']['length']} seconds
- **Publish Date:** {results['info']['publish_date']}
- **Video URL:** {results.get('video_url', 'Not available')}

## Summary
{results.get('summary', 'No summary available')}

## Main Chapters
"""
        # Add chapters
        for chapter in results['chapters']['chapters'][:3]:
            content += f"\n- {chapter['timestamp']}: {chapter['title']}"

        # Add tags
        content += "\n\n## Tags\n"
        content += ", ".join([f"#{tag}" for tag in self._generate_tags(results)])

        # Add metadata
        content += f"\n\n---\nAnalyzed on: {results.get('processed_date', 'Date not available')}"

        return content 