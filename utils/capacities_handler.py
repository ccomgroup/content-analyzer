import requests
import os
import json

class CapacitiesHandler:
    def __init__(self, api_key):
        self.api_key = api_key
        self.space_id = os.getenv("CAPACITIES_SPACE_ID")
        self.base_url = "https://api.capacities.io"  # Removed /v1
        
        if not self.api_key:
            raise ValueError("Missing Capacities API key")
        if not self.space_id:
            raise ValueError("Missing CAPACITIES_SPACE_ID in environment variables")
            
        print(f"Initialized CapacitiesHandler with space_id: {self.space_id}")
        print(f"Using Capacities API URL: {self.base_url}")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def _upload_image(self, image_path):
        """Upload an image to Capacities"""
        if not os.path.exists(image_path):
            print(f"Warning: Image file not found at {image_path}")
            return None

        upload_endpoint = f"{self.base_url}/upload"
        
        try:
            # Prepare the multipart form data
            files = {
                'file': ('preview.png', open(image_path, 'rb'), 'image/png')
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            # Upload the image
            response = requests.post(
                upload_endpoint,
                headers=headers,
                files=files,
                timeout=30
            )

            if response.status_code in [200, 201]:
                result = response.json()
                return result.get('url')  # Get the URL of the uploaded image
            else:
                print(f"Image upload failed with status {response.status_code}: {response.text}")
                return None

        except Exception as e:
            print(f"Error uploading image: {str(e)}")
            return None
        finally:
            files['file'][1].close()

    def create_weblink(self, results):
        """Create a weblink in Capacities"""
        try:
            # Format content based on type
            content = self._format_content(results)
            image_url = None
            
            # Handle image upload based on type
            if results['type'] == 'youtube':
                # For YouTube, use the thumbnail URL directly
                image_url = results.get('thumbnail_url')
                print(f"Using YouTube thumbnail URL: {image_url}")
            elif results['type'] == 'github' and results.get('image_path'):
                # For GitHub, upload the generated image
                image_url = self._upload_image(results['image_path'])
                print(f"Using uploaded GitHub image URL: {image_url}")
            
            # Prepare the weblink data
            weblink_data = {
                "title": results.get('title', '') if results['type'] == 'youtube' else results.get('repo_name', ''),
                "url": results['url'],
                "content": content,
                "spaceId": self.space_id,
                "previewImageUrl": image_url,
                "type": "weblink"  # Added explicit type
            }
            
            # Debug print the request details
            endpoint = f"{self.base_url}/spaces/{self.space_id}/weblinks"  # Updated endpoint structure
            print(f"\nMaking request to: {endpoint}")
            print(f"Headers: {self.headers}")
            print(f"Data: {json.dumps(weblink_data, indent=2)}")
            
            # Create the weblink
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=weblink_data,
                timeout=30
            )
            
            print(f"\nResponse status: {response.status_code}")
            print(f"Response headers: {response.headers}")
            
            try:
                response_json = response.json()
                print(f"Response body: {json.dumps(response_json, indent=2)}")
            except:
                print(f"Raw response: {response.text}")
            
            if response.status_code not in [200, 201]:
                error_msg = f"Failed to create weblink: Status {response.status_code}"
                try:
                    error_json = response.json()
                    if isinstance(error_json, dict):
                        error_msg += f" - {error_json.get('message', error_json)}"
                except:
                    error_msg += f" - {response.text}"
                raise Exception(error_msg)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Network error: {str(e)}")
            raise Exception(f"Network error creating weblink: {str(e)}")
        except Exception as e:
            print(f"General error: {str(e)}")
            raise Exception(f"Error creating weblink: {str(e)}")

    def _format_content(self, results):
        """Format the results in markdown"""
        if results['type'] == 'youtube':
            # Format YouTube content
            content = f"""# Video Analysis

## Video Information
- **Title:** {results['title']}
- **Author:** {results['author']}
- **URL:** {results['url']}
- **Views:** {results['views']}
- **Length:** {results['length']} seconds
- **Published:** {results['publish_date']}

## Summary
{results.get('summary', 'No summary available')}

## Chapters
"""
            # Add chapters if available
            for chapter in results.get('chapters', []):
                content += f"\n### {chapter['title']} ({chapter['timestamp']})\n{chapter['summary']}\n"

            # Add tags and timestamp
            content += f"""
## Tags
{', '.join([f"#{tag}" for tag in results.get('tags', [])])}

---
Analyzed on: {results.get('processed_date', 'Date not available')}
"""

        elif results['type'] == 'github':
            # Format GitHub content
            content = f"""# Repository Analysis

## Repository Information
- **Name:** {results['repo_name']}
- **URL:** {results['url']}

## Summary
{results.get('summary', 'No summary available')}

## Full Content
{results.get('full_content', 'No content available')}

---
Analyzed on: {results.get('processed_date', 'Date not available')}
"""
        else:
            content = "Unsupported content type"

        return content