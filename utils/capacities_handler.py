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
            # Prepare a short description
            short_description = f"""YouTube Video Analysis: {results['info']['title']}

Summary: {results.get('summary', 'No summary available')[:500]}...

Tags: {', '.join(self._generate_tags(results))}"""[:1000]  # Limit to 1000 characters

            # Prepare data according to documentation
            weblink_data = {
                "spaceId": self.space_id,
                "url": results.get('video_url', ''),
                "titleOverwrite": f"Analysis: {results['info']['title']}"[:200],  # Limit title
                "descriptionOverwrite": short_description,
                "tags": self._generate_tags(results),
                "mdText": self._format_content(results)  # Complete content in markdown
            }

            # Configure headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            # Debug info
            print("\nSending request to Capacities:")
            endpoint = f"{self.base_url}/save-weblink"  # Endpoint correct according to docs
            print(f"URL: {endpoint}")
            print(f"Space ID: {self.space_id}")
            print(f"Headers: {headers}")
            print(f"Data: {json.dumps(weblink_data, indent=2)}")

            # Make the API request
            response = requests.post(
                endpoint,
                json=weblink_data,
                headers=headers,
                timeout=30
            )

            # Debug response
            print("\nCapacities response:")
            print(f"Status Code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print(f"Response: {response.text}")

            # Verify response
            if response.status_code == 400:
                raise Exception("Invalid request. Check the sent data")
            elif response.status_code == 401:
                raise Exception("Authentication error. Check your API key")
            elif response.status_code == 404:
                raise Exception("Resource not found. Check the URL")
            elif response.status_code == 429:
                raise Exception("Too many requests. Wait a moment")
            elif response.status_code not in [200, 201]:
                raise Exception(f"Capacities error ({response.status_code}): {response.text}")
            
            # Process response
            try:
                response_data = response.json()
                weblink_id = response_data.get('id')
                if weblink_id:
                    return {
                        "url": f"https://app.capacities.io/space/{self.space_id}/weblink/{weblink_id}",
                        "id": weblink_id
                    }
                else:
                    raise Exception("Weblink ID not received in the response")
            except json.JSONDecodeError:
                raise Exception(f"Error decoding JSON response: {response.text}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Connection error with Capacities: {str(e)}")
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