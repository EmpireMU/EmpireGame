# Simple site assets upload for admins
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid
import os
from datetime import datetime

# Import resize function from roster
from web.roster.views import resize_image
from PIL import Image, ImageOps
from PIL.Image import LANCZOS
import io

def resize_image_with_transparency(image_file, max_size):
    """Resize image while preserving transparency for logos/icons/emblems."""
    img = Image.open(image_file)
    
    # Resize while preserving the original mode (including transparency)
    img.thumbnail((max_size, max_size), LANCZOS)
    
    # Save as PNG to preserve transparency
    buffer = io.BytesIO()
    img.save(buffer, format='PNG', optimize=True)
    buffer.seek(0)
    return buffer

@staff_member_required
def upload_site_asset(request):
    if request.method == 'POST':
        if 'asset' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        asset_file = request.FILES['asset']
        asset_type = request.POST.get('type', 'logo')  # logo, icon, etc.
        custom_name = request.POST.get('custom_name', '')  # Optional custom filename
        
        # Validate file type
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
        ext = os.path.splitext(asset_file.name)[1].lower()
        if ext not in valid_extensions:
            return JsonResponse({'error': 'Invalid file type'}, status=400)
        
        # Determine if we should preserve transparency
        preserve_transparency = asset_type in ['logo', 'icon', 'emblem']
        
        # Use custom name if provided, otherwise use type + UUID
        if custom_name:
            filename = f"{custom_name}.png" if preserve_transparency else f"{custom_name}.jpg"
        else:
            filename = f"{asset_type}_{uuid.uuid4()}.png" if preserve_transparency else f"{asset_type}_{uuid.uuid4()}.jpg"
        
        # Resize the image (800px max)
        try:
            if preserve_transparency:
                # For logos/icons/emblems, preserve transparency
                compressed_buffer = resize_image_with_transparency(asset_file, 800)
            else:
                # For other assets, use white background like character images
                compressed_buffer = resize_image(asset_file, 800, good_quality=True)
            
            path = f"site_assets/{filename}"
            saved_path = default_storage.save(path, ContentFile(compressed_buffer.read()))
        except Exception as e:
            return JsonResponse({'error': f'Could not process image: {e}'}, status=400)
        
        url = default_storage.url(saved_path) if hasattr(default_storage, 'url') else f"/media/{saved_path}"
        
        # Extract the actual saved filename (Django may have modified it if file existed)
        actual_filename = os.path.basename(saved_path)
        
        return JsonResponse({
            'success': True,
            'filename': actual_filename,  # Return the actual saved filename
            'url': url,
            'path': saved_path
        })
    
    return render(request, 'website/upload_assets.html')

@staff_member_required
def manage_site_assets(request):
    """View to list and manage all site assets."""
    site_assets_dir = 'site_assets/'
    files = []
    
    try:
        # List all files in the site_assets directory
        directories, filenames = default_storage.listdir(site_assets_dir)
        
        for filename in filenames:
            file_path = os.path.join(site_assets_dir, filename)
            
            try:
                # Get file info
                file_size = default_storage.size(file_path)
                modified_time = default_storage.get_modified_time(file_path)
                url = default_storage.url(file_path) if hasattr(default_storage, 'url') else f"/media/{file_path}"
                
                # Determine file type
                ext = os.path.splitext(filename)[1].lower()
                is_image = ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
                
                files.append({
                    'filename': filename,
                    'path': file_path,
                    'url': url,
                    'size': file_size,
                    'size_kb': round(file_size / 1024, 1),
                    'modified': modified_time,
                    'is_image': is_image,
                    'extension': ext
                })
            except Exception as e:
                # Skip files that can't be read
                continue
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x['modified'], reverse=True)
        
    except Exception as e:
        # Directory might not exist yet
        pass
    
    return render(request, 'website/manage_assets.html', {'files': files})

@staff_member_required
@require_http_methods(["DELETE", "POST"])
@csrf_protect
def delete_site_asset(request):
    """Delete a site asset file."""
    try:
        if request.method == "POST":
            # Handle POST request with filename in body
            import json
            data = json.loads(request.body)
            filename = data.get('filename')
        else:
            # Handle DELETE request
            import json
            data = json.loads(request.body)
            filename = data.get('filename')
        
        if not filename:
            return JsonResponse({'error': 'No filename provided'}, status=400)
        
        # Ensure the file is in the site_assets directory (security check)
        file_path = os.path.join('site_assets/', filename)
        if not file_path.startswith('site_assets/'):
            return JsonResponse({'error': 'Invalid file path'}, status=400)
        
        # Check if file exists
        if not default_storage.exists(file_path):
            return JsonResponse({'error': 'File not found'}, status=404)
        
        # Delete the file
        default_storage.delete(file_path)
        
        return JsonResponse({
            'success': True,
            'message': f'File {filename} deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
