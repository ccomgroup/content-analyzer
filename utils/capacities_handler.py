import requests
import os
import json

class CapacitiesHandler:
    def __init__(self, api_key):
        self.api_key = api_key
        self.space_id = os.getenv("CAPACITIES_SPACE_ID")
        self.base_url = "https://api.capacities.io"
        
        if not self.api_key:
            raise ValueError("Missing Capacities API key")
        if not self.space_id:
            raise ValueError("Missing CAPACITIES_SPACE_ID in environment variables")
            
        print(f"Initialized CapacitiesHandler with space_id: {self.space_id}")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def create_weblink(self, results):
        """Create a weblink in Capacities"""
        if not results:
            raise ValueError("No results provided")

        # Get the URL based on the content type
        if results['type'] == 'youtube':
            url = results.get('info', {}).get('webpage_url') or results.get('info', {}).get('url')
            if not url:
                raise ValueError("No URL found in YouTube results")
            title = results.get('info', {}).get('title', '')
            description = results.get('summary', '')
            tags = results.get('tags', [])
            
        elif results['type'] == 'github':
            url = results.get('url')
            if not url:
                raise ValueError("No URL found in GitHub results")
            title = results.get('repo_name', '')
            description = results.get('summary', '')
            tags = ["github", "repository", "documentation"]
        else:
            raise ValueError(f"Unsupported content type: {results['type']}")

        # Prepare request body according to API docs
        request_body = {
            "space": self.space_id,
            "source": {
                "type": "url",
                "value": url
            },
            "metadata": {
                "title": title,
                "description": description,
                "tags": tags,
                "content": description
            }
        }

        # Log debugging information
        print("\nCapacities API Debug Information:")
        print(f"Space ID: {self.space_id}")
        print(f"Base URL: {self.base_url}")
        print("Headers:", json.dumps(self.headers, indent=2))
        print("Request body:", json.dumps(request_body, indent=2))

        # Make the API request to the correct endpoint
        endpoint = f"{self.base_url}/v1/spaces/{self.space_id}/weblinks"
        print(f"Full endpoint URL: {endpoint}")

        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=request_body,
                timeout=30
            )

            # Log the response
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
            print(f"Response Body: {response.text}")

            # Check if request was successful
            if response.status_code in [200, 201]:
                try:
                    return response.json()
                except Exception as e:
                    print(f"Error parsing response JSON: {e}")
                    return {"url": url}
            else:
                error_msg = f"API request failed with status {response.status_code}"
                if response.text:
                    error_msg += f": {response.text}"
                raise Exception(error_msg)

        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error while calling Capacities API: {str(e)}")

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
        # Get chapters list, handling both old and new formats
        chapters_list = results['chapters']
        if isinstance(chapters_list, dict) and 'chapters' in chapters_list:
            chapters_list = chapters_list['chapters']
            
        # Add chapters
        for chapter in chapters_list[:3]:
            content += f"\n- {chapter['timestamp']}: {chapter['title']}"

        # Add tags
        content += "\n\n## Tags\n"
        content += ", ".join([f"#{tag}" for tag in self._generate_tags(results)])

        # Add metadata
        content += f"\n\n---\nAnalyzed on: {results.get('processed_date', 'Date not available')}"

        return content